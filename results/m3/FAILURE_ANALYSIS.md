# M3 failure analysis: OSD-0 fallback versus the learned prior

Source: `configs\m3_learned_basis_repetition_circuit_level_d3.json`
Checkpoint: `results\m3\m3_learned_basis_repetition_circuit_level_d3__d3__circuit_level__p0p01\model_state.pt`
Test shots: 32768 (reweight strength 1.00)

| decoder | logical errors | LER | syndrome consistency |
|---|---:|---:|---:|
| bp | 404 | 0.01233 | 0.9810 |
| bp_gnn | 323 | 0.00986 | 0.9858 |
| bp_osd | 407 | 0.01242 | 1.0000 |
| bp_gnn_osd | 407 | 0.01242 | 1.0000 |
| bp_gnn_osd_learned_order | 403 | 0.01230 | 1.0000 |

Under the learned prior, 98.58% of shots converge inside BP (464 non-converged).

On the 464 non-converged shots:

| decoder | logical errors in subgroup |
|---|---:|
| bp | 160 |
| bp_gnn | 173 |
| bp_osd | 175 |
| bp_gnn_osd | 257 |
| bp_gnn_osd_learned_order | 253 |

OSD-0 effect inside that subgroup: 188 flips (52 rescued, 136 broken, 121 still wrong).

| comparison | only A | only B | McNemar z | p (normal) | p (exact) |
|---|---:|---:|---:|---:|---:|
| bp vs bp_gnn (32768 shots) | 113 | 32 | 6.73 | 1.74e-11 | 8.5e-12 |
| bp_gnn vs bp_gnn_osd (32768 shots) | 52 | 136 | -6.13 | 8.99e-10 | 7.44e-10 |
| bp_osd vs bp_gnn_osd (32768 shots) | 116 | 116 | 0.00 | 1 | 1 |
| bp_gnn_osd vs bp_gnn_osd_learned_order (32768 shots) | 60 | 56 | 0.37 | 0.71 | 0.781 |
| bp_gnn vs bp_gnn_osd (464 shots) | 52 | 136 | -6.13 | 8.99e-10 | 7.44e-10 |
