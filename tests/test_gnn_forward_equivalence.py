"""Equivalence tests for the optimized bipartite GNN forward pass.

The forward pass splits the first linear layer of each message MLP into three
feature blocks and hoists the shot-independent edge-feature block out of the
batch dimension, and it reuses the two node-state gathers for both message
directions. This test pins that optimization against a straightforward
reference implementation of the same computation.
"""

from __future__ import annotations

import numpy as np
import torch

from graph_qec.circuits import build_rotated_surface_code_circuit
from graph_qec.config import ExperimentConfig
from graph_qec.decoders.dem import DEMSystem
from graph_qec.graph_features import build_graph_tensor
from graph_qec.models import BipartiteSyndromeGNN, graph_to_tensors


def reference_forward(model, *, variable_features, check_features, syndrome, edge_index, edge_features):
    """The unoptimized computation: one concatenation per message pass."""

    edge_checks = edge_index[0]
    edge_variables = edge_index[1]
    batches = syndrome.shape[0]
    num_variables = variable_features.shape[0]
    num_checks = check_features.shape[0]

    variable_state = model.variable_encoder(variable_features).unsqueeze(0).expand(batches, -1, -1)
    check_state = model.check_encoder(
        torch.cat(
            [check_features.unsqueeze(0).expand(batches, -1, -1), syndrome.unsqueeze(-1)], dim=-1
        )
    )
    variable_degree = (
        torch.bincount(edge_variables, minlength=num_variables).clamp(min=1).to(syndrome.dtype)
    )
    check_degree = torch.bincount(edge_checks, minlength=num_checks).clamp(min=1).to(syndrome.dtype)

    for _ in range(model.num_layers):
        messages = model.check_to_variable(
            torch.cat(
                [
                    check_state[:, edge_checks, :],
                    variable_state[:, edge_variables, :],
                    edge_features.unsqueeze(0).expand(batches, -1, -1),
                ],
                dim=-1,
            )
        )
        aggregate = messages.new_zeros(messages.shape[0], num_variables, messages.shape[2])
        aggregate.index_add_(1, edge_variables, messages)
        variable_aggregate = aggregate / variable_degree.view(1, -1, 1)

        messages = model.variable_to_check(
            torch.cat(
                [
                    variable_state[:, edge_variables, :],
                    check_state[:, edge_checks, :],
                    edge_features.unsqueeze(0).expand(batches, -1, -1),
                ],
                dim=-1,
            )
        )
        aggregate = messages.new_zeros(messages.shape[0], num_checks, messages.shape[2])
        aggregate.index_add_(1, edge_checks, messages)
        check_aggregate = aggregate / check_degree.view(1, -1, 1)

        variable_state = variable_state + model.variable_update(
            torch.cat([variable_state, variable_aggregate], dim=-1)
        )
        check_state = check_state + model.check_update(
            torch.cat([check_state, check_aggregate, syndrome.unsqueeze(-1)], dim=-1)
        )

    return model.readout(variable_state).squeeze(-1)


def _fixture(distance: int, batch: int = 16):
    config = ExperimentConfig(
        name="gnn_equivalence",
        seed=20261015,
        family="rotated_surface_code",
        distance=distance,
        rounds=distance,
        noise_model="code_capacity",
        physical_error_rate=0.05,
        shots=1,
    )
    circuit = build_rotated_surface_code_circuit(config)
    graph = build_graph_tensor(
        DEMSystem.from_detector_error_model(circuit.detector_error_model(decompose_errors=True))
    )
    tensors = graph_to_tensors(graph)
    torch.manual_seed(11)
    model = BipartiteSyndromeGNN(
        variable_feature_dim=graph.variable_feature_dim,
        check_feature_dim=graph.check_feature_dim,
        edge_feature_dim=graph.edge_feature_dim,
        hidden_size=16,
        num_layers=2,
        dropout=0.0,
    ).eval()
    static = {
        "variable_features": tensors["variable_features"],
        "check_features": tensors["check_features"],
        "edge_index": tensors["edge_index"],
        "edge_features": tensors["edge_features"],
    }
    generator = torch.Generator().manual_seed(5)
    syndrome = (torch.rand(batch, graph.num_checks, generator=generator) < 0.05).to(torch.float32)
    return model, graph, static, syndrome


def test_forward_matches_reference_implementation() -> None:
    model, _graph, static, syndrome = _fixture(distance=3)
    with torch.no_grad():
        expected = reference_forward(model, syndrome=syndrome, **static)
        actual = model(syndrome=syndrome, **static)
    assert actual.shape == expected.shape
    assert float((actual - expected).abs().max()) < 1e-5


def test_forward_is_deterministic_across_repeated_calls() -> None:
    model, _graph, static, syndrome = _fixture(distance=3)
    with torch.no_grad():
        first = model(syndrome=syndrome, **static)
        second = model(syndrome=syndrome, **static)
    assert torch.equal(first, second)


def test_cached_aggregation_buffers_are_reused_under_no_grad() -> None:
    model, graph, static, syndrome = _fixture(distance=3, batch=4)
    model._aggregate_cache.clear()
    with torch.no_grad():
        model(syndrome=syndrome, **static)
    sizes = {key: tuple(value.shape) for key, value in model._aggregate_cache.items()}
    assert sizes["c2v"] == (4, graph.num_variables, 16)
    assert sizes["v2c"] == (4, graph.num_checks, 16)


def test_forward_with_embeddings_returns_hidden_states() -> None:
    model, graph, static, syndrome = _fixture(distance=3, batch=4)
    with torch.no_grad():
        logits, embeddings = model(syndrome=syndrome, return_embeddings=True, **static)
    assert logits.shape == (4, graph.num_variables)
    assert embeddings.shape == (4, graph.num_variables, 16)
    assert np.all(np.isfinite(logits.numpy()))

def test_forward_falls_back_for_non_linear_message_layers() -> None:
    """Dynamic quantization replaces ``nn.Linear``; the forward must still work."""

    model, graph, static, syndrome = _fixture(distance=3, batch=4)
    model.eval()
    with torch.no_grad():
        expected = model(syndrome=syndrome, **static)
    quantized = torch.ao.quantization.quantize_dynamic(model, {torch.nn.Linear}, dtype=torch.qint8)
    with torch.no_grad():
        actual = quantized(syndrome=syndrome, **static)
    assert actual.shape == expected.shape
    assert float((actual - expected).abs().max()) < 0.5
    assert np.all(np.isfinite(actual.numpy()))
