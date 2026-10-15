# Incomplete M2 run (training only)

The GNN for repetition_code d=5, circuit-level p=0.01 was trained (12 epochs,
best validation log loss 0.02001) and the checkpoint was written as
`model_state.pt`. The decoder evaluation (validation sweep + test benchmark)
was aborted for time on this CPU-only machine, so `results.json` is absent.

Re-run with:

```powershell
.\\.venv\\Scripts\\python.exe -m graph_qec.m2 `
  --config configs\\m2_learned_basis_repetition_circuit_level_d5.json `
  --output-dir results\\m2
```
