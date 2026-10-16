# M2 result summary

Source: `results\m2`

| experiment | code | noise | p | selected strength | test shots | mechanism accuracy | test log loss |
|---|---|---|---|---|---|---|---|
| m2_learned_basis_repetition_circuit_level_d3 | repetition_code d=3 r=3 | circuit_level | 0.01 | 1.00 | 32768 | 0.9965 | 0.01440 |
| m2_learned_basis_repetition_circuit_level_d3_s10 | repetition_code d=3 r=3 | circuit_level | 0.01 | 1.00 | 32768 | 0.9924 | 0.02126 |
| m2_learned_basis_repetition_circuit_level_d3_s20 | repetition_code d=3 r=3 | circuit_level | 0.01 | 1.00 | 32768 | 0.9964 | 0.01539 |
| m2_repetition_circuit_level_d3 | repetition_code d=3 r=3 | circuit_level | 0.01 | 1.00 | 32768 | 0.9965 | 0.01441 |

## m2_learned_basis_repetition_circuit_level_d3

- graph: 8 detectors, 21 error mechanisms, 34 edges
- splits: train 16384 / validation 8192 / test 32768 shots
- training: 15297 parameters, 15 epochs, best validation log loss 0.01515
- noise model circuit_level at p=0.01, distance 3

| decoder | logical errors | LER | s.e. | convergence | mean iterations | syndrome consistency | us/shot |
|---|---:|---:|---:|---:|---:|---:|---:|
| mwpm | 217 | 0.00662 | 0.00045 | - | - | - | 0.1 |
| union_find | 318 | 0.00970 | 0.00054 | - | - | - | 31.9 |
| bp | 309 | 0.00943 | 0.00053 | 0.9899 | 0.707 | 0.9899 | 1.7 |
| bp_osd | 331 | 0.01010 | 0.00055 | 0.9899 | 0.707 | 1.0000 | 2.9 |
| osd_bp | 331 | 0.01010 | 0.00055 | 0.9899 | 0.707 | 1.0000 | 123.1 |
| osd_gnn | 319 | 0.00974 | 0.00054 | 0.9899 | 0.707 | 1.0000 | 116.3 |

Validation sweep:

| strength | LER | mean iterations | convergence |
|---:|---:|---:|---:|
| 0.0 | 0.01135 | 0.752 | 0.9890 |
| 1.0 | 0.01086 | 0.599 | 0.9902 |

## m2_learned_basis_repetition_circuit_level_d3_s10

- graph: 8 detectors, 21 error mechanisms, 34 edges
- splits: train 16384 / validation 8192 / test 32768 shots
- training: 15297 parameters, 15 epochs, best validation log loss 0.02159
- noise model circuit_level at p=0.01, distance 3

| decoder | logical errors | LER | s.e. | convergence | mean iterations | syndrome consistency | us/shot |
|---|---:|---:|---:|---:|---:|---:|---:|
| mwpm | 231 | 0.00705 | 0.00046 | - | - | - | 0.1 |
| union_find | 245 | 0.00748 | 0.00048 | - | - | - | 11.2 |
| bp | 338 | 0.01031 | 0.00056 | 0.9897 | 0.717 | 0.9897 | 2.9 |
| bp_osd | 350 | 0.01068 | 0.00057 | 0.9897 | 0.717 | 1.0000 | 4.8 |
| osd_bp | 350 | 0.01068 | 0.00057 | 0.9897 | 0.717 | 1.0000 | 164.1 |
| osd_gnn | 332 | 0.01013 | 0.00055 | 0.9897 | 0.717 | 1.0000 | 149.7 |

Validation sweep:

| strength | LER | mean iterations | convergence |
|---:|---:|---:|---:|
| 0.0 | 0.01050 | 0.737 | 0.9894 |
| 1.0 | 0.00952 | 0.513 | 0.9929 |

## m2_learned_basis_repetition_circuit_level_d3_s20

- graph: 8 detectors, 21 error mechanisms, 34 edges
- splits: train 16384 / validation 8192 / test 32768 shots
- training: 15297 parameters, 15 epochs, best validation log loss 0.01604
- noise model circuit_level at p=0.01, distance 3

| decoder | logical errors | LER | s.e. | convergence | mean iterations | syndrome consistency | us/shot |
|---|---:|---:|---:|---:|---:|---:|---:|
| mwpm | 247 | 0.00754 | 0.00048 | - | - | - | 0.2 |
| union_find | 274 | 0.00836 | 0.00050 | - | - | - | 11.1 |
| bp | 359 | 0.01096 | 0.00058 | 0.9894 | 0.728 | 0.9894 | 3.2 |
| bp_osd | 365 | 0.01114 | 0.00058 | 0.9894 | 0.728 | 1.0000 | 5.1 |
| osd_bp | 365 | 0.01114 | 0.00058 | 0.9894 | 0.728 | 1.0000 | 165.6 |
| osd_gnn | 351 | 0.01071 | 0.00057 | 0.9894 | 0.728 | 1.0000 | 150.5 |

Validation sweep:

| strength | LER | mean iterations | convergence |
|---:|---:|---:|---:|
| 0.0 | 0.01123 | 0.776 | 0.9880 |
| 1.0 | 0.01086 | 0.607 | 0.9899 |

## m2_repetition_circuit_level_d3

- graph: 8 detectors, 21 error mechanisms, 34 edges
- splits: train 16384 / validation 8192 / test 32768 shots
- training: 15297 parameters, 15 epochs, best validation log loss 0.01516
- noise model circuit_level at p=0.01, distance 3

| decoder | logical errors | LER | s.e. | convergence | mean iterations | syndrome consistency | us/shot |
|---|---:|---:|---:|---:|---:|---:|---:|
| mwpm | 217 | 0.00662 | 0.00045 | - | - | - | 0.1 |
| union_find | 318 | 0.00970 | 0.00054 | - | - | - | 33.6 |
| bp | 309 | 0.00943 | 0.00053 | 0.9899 | 0.707 | 0.9899 | 1.8 |
| bp_osd | 331 | 0.01010 | 0.00055 | 0.9899 | 0.707 | 1.0000 | 2.8 |
| bp_gnn | 312 | 0.00952 | 0.00054 | 0.9912 | 0.557 | 0.9912 | 1.6 |

Validation sweep:

| strength | LER | mean iterations | convergence |
|---:|---:|---:|---:|
| 0.0 | 0.01135 | 0.752 | 0.9890 |
| 0.25 | 0.01135 | 0.693 | 0.9893 |
| 0.5 | 0.01086 | 0.605 | 0.9902 |
| 0.75 | 0.01086 | 0.600 | 0.9902 |
| 1.0 | 0.01086 | 0.599 | 0.9902 |

