# M5: float32 versus dynamic int8 GNN inference

Checkpoint: `results\m3\m3_learned_basis_repetition_circuit_level_d3__d3__circuit_level__p0p01\model_state.pt`  
Test shots: 16384, batch size 1024, best of 3 runs.

| model | parameters (MB) | inference (s) | us/shot | mechanism log loss |
|---|---:|---:|---:|---:|
| float32 | 0.0612 | 0.520 | 31.73 | 0.01497 |
| int8 (dynamic) | 0.0165 | 0.672 | 40.99 | 0.01497 |

- speedup (float / int8): 0.77x
- parameter compression: 3.72x
- mechanism sign agreement: 1.0000 (max |logit delta| 0.438)

| decoder | logical errors | LER | syndrome consistency |
|---|---:|---:|---:|
| float32 | 145 | 0.00885 | 0.9917 |
| int8 | 145 | 0.00885 | 0.9917 |
| bp_no_prior | 144 | 0.00879 | 0.9907 |
