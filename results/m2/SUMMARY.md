# M2 result summary

Source: `results\m2`

| experiment | code | noise | p | selected strength | test shots | mechanism accuracy | test log loss |
|---|---|---|---|---|---|---|---|
| m2_learned_basis_repetition_circuit_level_d3 | repetition_code d=3 r=3 | circuit_level | 0.01 | 1.00 | 32768 | 0.9965 | 0.01440 |
| m2_repetition_circuit_level_d3 | repetition_code d=3 r=3 | circuit_level | 0.01 | 1.00 | 32768 | 0.9965 | 0.01440 |

## m2_learned_basis_repetition_circuit_level_d3

- graph: 8 detectors, 21 error mechanisms, 34 edges
- splits: train 16384 / validation 8192 / test 32768 shots
- training: 15297 parameters, 15 epochs, best validation log loss 0.01515
- noise model circuit_level at p=0.01, distance 3

| decoder | logical errors | LER | s.e. | convergence | mean iterations | syndrome consistency | us/shot |
|---|---:|---:|---:|---:|---:|---:|---:|
| mwpm | 217 | 0.00662 | 0.00045 | - | - | - | 0.1 |
| union_find | 318 | 0.00970 | 0.00054 | - | - | - | 37.8 |
| bp | 404 | 0.01233 | 0.00061 | 0.9810 | 1.011 | 0.9810 | 198.4 |
| bp_osd | 407 | 0.01242 | 0.00061 | 0.9810 | 1.011 | 1.0000 | 210.0 |
| osd_bp | 407 | 0.01242 | 0.00061 | 0.9810 | 1.011 | 1.0000 | 541.9 |
| osd_gnn | 495 | 0.01511 | 0.00067 | 0.9810 | 1.011 | 1.0000 | 355.0 |

Validation sweep:

| strength | LER | mean iterations | convergence |
|---:|---:|---:|---:|
| 0.0 | 0.01404 | 1.102 | 0.9784 |
| 1.0 | 0.01147 | 0.938 | 0.9841 |

## m2_repetition_circuit_level_d3

- graph: 8 detectors, 21 error mechanisms, 34 edges
- splits: train 16384 / validation 8192 / test 32768 shots
- training: 15297 parameters, 15 epochs, best validation log loss 0.01515
- noise model circuit_level at p=0.01, distance 3

| decoder | logical errors | LER | s.e. | convergence | mean iterations | syndrome consistency | us/shot |
|---|---:|---:|---:|---:|---:|---:|---:|
| mwpm | 217 | 0.00662 | 0.00045 | - | - | - | 0.1 |
| union_find | 318 | 0.00970 | 0.00054 | - | - | - | 38.5 |
| bp | 404 | 0.01233 | 0.00061 | 0.9810 | 1.011 | 0.9810 | 196.3 |
| bp_osd | 407 | 0.01242 | 0.00061 | 0.9810 | 1.011 | 1.0000 | 201.8 |
| bp_gnn | 323 | 0.00986 | 0.00055 | 0.9858 | 0.863 | 0.9858 | 172.3 |

Validation sweep:

| strength | LER | mean iterations | convergence |
|---:|---:|---:|---:|
| 0.0 | 0.01404 | 1.102 | 0.9784 |
| 0.25 | 0.01379 | 1.094 | 0.9783 |
| 0.5 | 0.01428 | 1.053 | 0.9795 |
| 0.75 | 0.01208 | 0.869 | 0.9861 |
| 1.0 | 0.01147 | 0.938 | 0.9841 |

