# M3 failure analysis: OSD-0 fallback versus the learned prior

Source: `configs\m3_learned_basis_repetition_circuit_level_d3.json`
Checkpoint: `results\m3\m3_learned_basis_repetition_circuit_level_d3__d3__circuit_level__p0p01\model_state.pt`
Test shots: 32768 (reweight strength 1.00)

| decoder | logical errors | LER | syndrome consistency |
|---|---:|---:|---:|
| bp | 43 | 0.00131 | 0.9982 |
| bp_gnn | 80 | 0.00244 | 0.9965 |
| bp_osd | 46 | 0.00140 | 1.0000 |
| bp_gnn_osd | 112 | 0.00342 | 1.0000 |
| bp_gnn_osd_learned_order | 66 | 0.00201 | 1.0000 |

Under the learned prior, 99.65% of shots converge inside BP (116 non-converged).

On the 116 non-converged shots:

| decoder | logical errors in subgroup |
|---|---:|
| bp | 17 |
| bp_gnn | 62 |
| bp_osd | 17 |
| bp_gnn_osd | 94 |
| bp_gnn_osd_learned_order | 48 |

OSD-0 effect inside that subgroup: 58 flips (13 rescued, 45 broken, 49 still wrong).

| comparison | only A | only B | McNemar z | p (normal) | p (exact) |
|---|---:|---:|---:|---:|---:|
| bp vs bp_gnn (32768 shots) | 9 | 46 | -4.99 | 6.07e-07 | 4.34e-07 |
| bp_gnn vs bp_gnn_osd (32768 shots) | 13 | 45 | -4.20 | 2.65e-05 | 3.01e-05 |
| bp_osd vs bp_gnn_osd (32768 shots) | 20 | 86 | -6.41 | 1.45e-10 | 6.19e-11 |
| bp_gnn_osd vs bp_gnn_osd_learned_order (32768 shots) | 48 | 2 | 6.51 | 7.75e-11 | 2.27e-12 |
| bp_gnn vs bp_gnn_osd (116 shots) | 13 | 45 | -4.20 | 2.65e-05 | 3.01e-05 |
