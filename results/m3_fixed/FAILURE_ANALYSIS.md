# M3 failure analysis: OSD-0 fallback versus the learned prior

Source: `configs\m3_learned_basis_repetition_circuit_level_d3.json`
Checkpoint: `results\m3_fixed\m3_learned_basis_repetition_circuit_level_d3__d3__circuit_level__p0p01\model_state.pt`
Test shots: 32768 (reweight strength 1.00)

| decoder | logical errors | LER | syndrome consistency |
|---|---:|---:|---:|
| bp | 309 | 0.00943 | 0.9899 |
| bp_gnn | 312 | 0.00952 | 0.9912 |
| bp_osd | 331 | 0.01010 | 1.0000 |
| bp_gnn_osd | 333 | 0.01016 | 1.0000 |
| bp_gnn_osd_learned_order | 317 | 0.00967 | 1.0000 |

Under the learned prior, 99.12% of shots converge inside BP (288 non-converged).

On the 288 non-converged shots:

| decoder | logical errors in subgroup |
|---|---:|
| bp | 147 |
| bp_gnn | 154 |
| bp_osd | 172 |
| bp_gnn_osd | 175 |
| bp_gnn_osd_learned_order | 159 |

OSD-0 effect inside that subgroup: 155 flips (67 rescued, 88 broken, 87 still wrong).

| comparison | only A | only B | McNemar z | p (normal) | p (exact) |
|---|---:|---:|---:|---:|---:|
| bp vs bp_gnn (32768 shots) | 6 | 9 | -0.77 | 0.439 | 0.607 |
| bp_gnn vs bp_gnn_osd (32768 shots) | 67 | 88 | -1.69 | 0.0916 | 0.108 |
| bp_osd vs bp_gnn_osd (32768 shots) | 16 | 18 | -0.34 | 0.732 | 0.864 |
| bp_gnn_osd vs bp_gnn_osd_learned_order (32768 shots) | 33 | 17 | 2.26 | 0.0237 | 0.0328 |
| bp_gnn vs bp_gnn_osd (288 shots) | 67 | 88 | -1.69 | 0.0916 | 0.108 |
