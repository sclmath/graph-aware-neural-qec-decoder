"""Bipartite message-passing network over the detector graph.

The network consumes the same bipartite structure that BP uses: one check node
per detector, one variable node per DEM error mechanism. Check nodes receive the
per-shot syndrome, so the network can predict syndrome-conditioned marginals
``P(e_i = 1 | syndrome)`` for every error mechanism. Those logits are consumed
by M2 as a learned reweighting of the BP prior.
"""

from __future__ import annotations

import numpy as np
import torch
import torch.nn.functional as F
from torch import nn

from ..graph_features import GraphTensor


def graph_to_tensors(
    graph: GraphTensor,
    *,
    device: torch.device | str = "cpu",
) -> dict[str, torch.Tensor]:
    """Converts a :class:`GraphTensor` into torch tensors on one device."""

    return {
        "variable_features": torch.as_tensor(graph.variable_features, dtype=torch.float32, device=device),
        "check_features": torch.as_tensor(graph.check_features, dtype=torch.float32, device=device),
        "edge_index": torch.as_tensor(
            np.stack([graph.edge_checks, graph.edge_variables]), dtype=torch.int64, device=device
        ),
        "edge_features": torch.as_tensor(graph.edge_features, dtype=torch.float32, device=device),
    }


class _MessageMLP(nn.Module):
    def __init__(self, input_size: int, hidden_size: int, dropout: float) -> None:
        super().__init__()
        self.layers = nn.Sequential(
            nn.Linear(input_size, hidden_size),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_size, hidden_size),
        )

    def forward(self, inputs: torch.Tensor) -> torch.Tensor:
        return self.layers(inputs)


class BipartiteSyndromeGNN(nn.Module):
    """Stacked bipartite message passing with a per-variable logit head."""

    def __init__(
        self,
        *,
        variable_feature_dim: int,
        check_feature_dim: int,
        edge_feature_dim: int,
        hidden_size: int = 64,
        num_layers: int = 4,
        dropout: float = 0.0,
    ) -> None:
        super().__init__()
        if num_layers < 1:
            raise ValueError("num_layers must be positive")
        self.hidden_size = int(hidden_size)
        self.num_layers = int(num_layers)
        self.variable_encoder = _MessageMLP(variable_feature_dim, hidden_size, dropout)
        self.check_encoder = _MessageMLP(check_feature_dim + 1, hidden_size, dropout)
        self.check_to_variable = _MessageMLP(2 * hidden_size + edge_feature_dim, hidden_size, dropout)
        self.variable_to_check = _MessageMLP(2 * hidden_size + edge_feature_dim, hidden_size, dropout)
        self.variable_update = _MessageMLP(2 * hidden_size, hidden_size, dropout)
        self.check_update = _MessageMLP(2 * hidden_size + 1, hidden_size, dropout)
        self.readout = nn.Linear(hidden_size, 1)
        # Reusable aggregation buffers, keyed by message direction. Plain dict so
        # it never shows up in state_dict(); see ``_aggregate`` for the contract.
        self._aggregate_cache: dict[str, torch.Tensor] = {}

    @staticmethod
    def _message(
        mlp: "_MessageMLP",
        part_a: torch.Tensor,
        part_b: torch.Tensor,
        static_edge: torch.Tensor | None = None,
    ) -> torch.Tensor:
        """Computes ``mlp(cat([part_a, part_b, edge_features]))`` without building the concat.

        The first linear layer is split into its three feature blocks. The
        edge-feature block does not depend on the shot, so the caller hoists it
        out of the batch dimension; only the two node-state gathers stay on the
        per-shot path.
        """

        first = mlp.layers[0]
        weight = first.weight
        hidden = weight.shape[0]
        pre_activation = F.linear(part_a, weight[:, :hidden], first.bias)
        pre_activation = pre_activation + F.linear(part_b, weight[:, hidden : 2 * hidden])
        if static_edge is not None:
            pre_activation = pre_activation + static_edge
        result = pre_activation
        for layer in mlp.layers[1:]:
            result = layer(result)
        return result

    @staticmethod
    def _edge_projection(mlp: "_MessageMLP", edge_features: torch.Tensor) -> torch.Tensor:
        """Precomputes the edge-feature contribution of the first linear layer."""

        weight = mlp.layers[0].weight
        return F.linear(edge_features, weight[:, 2 * weight.shape[0] :])

    def _aggregate(self, messages: torch.Tensor, index: torch.Tensor, size: int, key: str) -> torch.Tensor:
        """Mean-sums ``messages`` per node, reusing one buffer per direction.

        Under ``torch.no_grad()`` the returned tensor is owned by the cache and
        valid until the next call with the same ``key``; callers consume it
        immediately. With autograd enabled a fresh tensor is returned instead.
        """

        shape = (messages.shape[0], size, messages.shape[2])
        if torch.is_grad_enabled():
            # Training needs the pre-update aggregate value for the backward pass,
            # so the buffer cannot be recycled in place there.
            aggregated = messages.new_zeros(*shape)
            aggregated.index_add_(1, index, messages)
            return aggregated
        cached = self._aggregate_cache.get(key)
        if cached is None or cached.shape != shape:
            cached = messages.new_zeros(*shape)
            self._aggregate_cache[key] = cached
        else:
            cached.zero_()
        cached.index_add_(1, index, messages)
        return cached

    def forward(
        self,
        *,
        variable_features: torch.Tensor,
        check_features: torch.Tensor,
        syndrome: torch.Tensor,
        edge_index: torch.Tensor,
        edge_features: torch.Tensor,
        return_embeddings: bool = False,
    ) -> torch.Tensor | tuple[torch.Tensor, torch.Tensor]:
        edge_checks = edge_index[0]
        edge_variables = edge_index[1]
        batches = syndrome.shape[0]
        num_variables = variable_features.shape[0]
        num_checks = check_features.shape[0]

        variable_state = self.variable_encoder(variable_features).unsqueeze(0).expand(batches, -1, -1)
        check_state = self.check_encoder(
            torch.cat(
                [
                    check_features.unsqueeze(0).expand(batches, -1, -1),
                    syndrome.unsqueeze(-1),
                ],
                dim=-1,
            )
        )

        variable_degree = (
            torch.bincount(edge_variables, minlength=num_variables).clamp(min=1).to(syndrome.dtype)
        )
        check_degree = torch.bincount(edge_checks, minlength=num_checks).clamp(min=1).to(syndrome.dtype)

        # The split-linear fast path needs plain ``nn.Linear`` layers: dynamic
        # quantization replaces them with modules whose ``weight`` is a callable
        # rather than a tensor, and those must go through their own forward.
        fast_path = all(
            isinstance(mlp.layers[0], nn.Linear)
            for mlp in (self.check_to_variable, self.variable_to_check)
        )
        if fast_path:
            edge_for_c2v = self._edge_projection(self.check_to_variable, edge_features).unsqueeze(0)
            edge_for_v2c = self._edge_projection(self.variable_to_check, edge_features).unsqueeze(0)
        else:
            expanded_edges = edge_features.unsqueeze(0).expand(batches, -1, -1)

        for _ in range(self.num_layers):
            # The two message passes share the same gathers.
            check_at_edges = check_state[:, edge_checks, :]
            variable_at_edges = variable_state[:, edge_variables, :]

            if fast_path:
                check_messages = self._message(
                    self.check_to_variable, check_at_edges, variable_at_edges, edge_for_c2v
                )
            else:
                check_messages = self.check_to_variable(
                    torch.cat([check_at_edges, variable_at_edges, expanded_edges], dim=-1)
                )
            variable_aggregate = self._aggregate(
                check_messages, edge_variables, num_variables, "c2v"
            ) / variable_degree.view(1, -1, 1)

            if fast_path:
                variable_messages = self._message(
                    self.variable_to_check, variable_at_edges, check_at_edges, edge_for_v2c
                )
            else:
                variable_messages = self.variable_to_check(
                    torch.cat([variable_at_edges, check_at_edges, expanded_edges], dim=-1)
                )
            check_aggregate = self._aggregate(
                variable_messages, edge_checks, num_checks, "v2c"
            ) / check_degree.view(1, -1, 1)

            variable_state = variable_state + self.variable_update(
                torch.cat([variable_state, variable_aggregate], dim=-1)
            )
            check_state = check_state + self.check_update(
                torch.cat([check_state, check_aggregate, syndrome.unsqueeze(-1)], dim=-1)
            )

        logits = self.readout(variable_state).squeeze(-1)
        if return_embeddings:
            return logits, variable_state
        return logits


@torch.no_grad()
def predict_logits(
    model: BipartiteSyndromeGNN,
    tensors: dict[str, torch.Tensor],
    detections: np.ndarray,
    *,
    batch_size: int = 512,
) -> np.ndarray:
    """Runs batched inference and returns ``(shots, num_variables)`` logits."""

    model.eval()
    device = tensors["variable_features"].device
    detections = np.ascontiguousarray(detections, dtype=np.float32)
    outputs: list[np.ndarray] = []
    for start in range(0, detections.shape[0], batch_size):
        batch = torch.as_tensor(
            detections[start : start + batch_size], dtype=torch.float32, device=device
        )
        logits = model(syndrome=batch, **tensors)
        outputs.append(logits.detach().cpu().numpy().astype(np.float64))
    if not outputs:
        return np.zeros((0, tensors["variable_features"].shape[0]), dtype=np.float64)
    return np.concatenate(outputs, axis=0)
