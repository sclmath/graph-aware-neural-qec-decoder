# M3 result summary

Source: `results\m3`

Source checkpoint: repetition_code d=3 r=3 circuit_level p=0.01

## In-distribution reference (source noise rate)

| experiment | shots | decoders |
|---|---|---|
| m3_learned_basis_repetition_circuit_level_d3 d3 p=0.01 | 32768 | mwpm, bp, bp_osd, bp_gnn, bp_gnn_osd, bp_gnn_osd_learned_order, osd_gnn |

## Noise-rate extrapolation (same code, different physical error rate)

Test logical error rate:

| physical_error_rate | shots | mwpm | bp | bp_osd | bp_gnn | bp_gnn_osd |
|---|---|---|---|---|---|---|
| 0.003 | 32768 | 0.00082 | 0.00131 | 0.00140 | 0.00244 | 0.00342 |
| 0.005 | 32768 | 0.00174 | 0.00375 | 0.00360 | 0.00482 | 0.00336 |
| 0.008 | 32768 | 0.00485 | 0.00797 | 0.00824 | 0.00626 | 0.00760 |
| 0.02 | 32768 | 0.02554 | 0.04147 | 0.04282 | 0.03497 | 0.03680 |

Syndrome consistency rate:

| target | mwpm | bp | bp_osd | bp_gnn | bp_gnn_osd |
|---|---|---|---|---|---|
| d3 p=0.003 | - | 0.9982 | 1.0000 | 0.9965 | 1.0000 |
| d3 p=0.005 | - | 0.9947 | 1.0000 | 0.9935 | 1.0000 |
| d3 p=0.008 | - | 0.9875 | 1.0000 | 0.9903 | 1.0000 |
| d3 p=0.02 | - | 0.9352 | 1.0000 | 0.9513 | 1.0000 |

## Code-distance extrapolation (same noise model and code family)

Test logical error rate:

| distance | shots | mwpm | bp | bp_gnn | bp_gnn_osd |
|---|---|---|---|---|---|
| 5 | 8192 | 0.00134 | 0.06567 | 0.05420 | 0.07910 |

## Other checkpoints and transfer axes

| source | target | shots | decoders |
|---|---|---:|---|
| d5 p=0.01 | d5 circuit_level p=0.01 | 4096 | mwpm, bp, bp_osd, bp_gnn, bp_gnn_osd |

## Mechanism-posterior calibration under distribution shift

| target | shots | learned log loss | DEM-prior log loss | learned AUC | DEM-prior AUC | mechanism accuracy |
|---|---:|---:|---:|---:|---:|---:|
| d3->d3 p=0.003 | 32768 | 0.00238 | 0.02966 | 0.9977 | 0.6280 | 0.9994 |
| d3->d3 p=0.005 | 32768 | 0.00511 | 0.04552 | 0.9952 | 0.6248 | 0.9989 |
| d3->d3 p=0.008 | 32768 | 0.00994 | 0.06665 | 0.9935 | 0.6192 | 0.9977 |
| d3->d3 p=0.02 | 32768 | 0.04900 | 0.13538 | 0.9730 | 0.6237 | 0.9864 |
| d3->d5 p=0.01 | 8192 | 0.02552 | 0.05231 | 0.9876 | 0.6585 | 0.9922 |
| d5->d5 p=0.01 | 4096 | 0.01824 | 0.05142 | 0.9884 | 0.6647 | 0.9923 |

## Per-run detail

### d3 circuit_level p=0.003 (results\m3\m3_learned_basis_repetition_circuit_level_d3__from_d3__to_d3__circuit_level__p0p003)

- graph: 8 detectors, 21 mechanisms, 34 edges; test shots: 32768 (seeds [301, 302])
- reweight strength fixed at 1.00

| decoder | logical errors | LER | s.e. | syndrome consistency | convergence | mean iterations | OSD rate | us/shot |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| mwpm | 27 | 0.00082 | 0.00016 | - | - | - | - | 0.1 |
| bp | 43 | 0.00131 | 0.00020 | 0.9982 | 0.9982 | 0.186 | - | 78.9 |
| bp_osd | 46 | 0.00140 | 0.00021 | 1.0000 | 0.9982 | 0.186 | 0.0018 | 97.1 |
| bp_gnn | 80 | 0.00244 | 0.00027 | 0.9965 | 0.9965 | 0.251 | - | 81.5 |
| bp_gnn_osd | 112 | 0.00342 | 0.00032 | 1.0000 | 0.9965 | 0.251 | 0.0035 | 84.5 |

### d3 circuit_level p=0.005 (results\m3\m3_learned_basis_repetition_circuit_level_d3__from_d3__to_d3__circuit_level__p0p005)

- graph: 8 detectors, 21 mechanisms, 34 edges; test shots: 32768 (seeds [301, 302])
- reweight strength fixed at 1.00

| decoder | logical errors | LER | s.e. | syndrome consistency | convergence | mean iterations | OSD rate | us/shot |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| mwpm | 57 | 0.00174 | 0.00023 | - | - | - | - | 0.1 |
| bp | 123 | 0.00375 | 0.00034 | 0.9947 | 0.9947 | 0.378 | - | 186.9 |
| bp_osd | 118 | 0.00360 | 0.00033 | 1.0000 | 0.9947 | 0.378 | 0.0053 | 119.8 |
| bp_gnn | 158 | 0.00482 | 0.00038 | 0.9935 | 0.9935 | 0.414 | - | 123.0 |
| bp_gnn_osd | 110 | 0.00336 | 0.00032 | 1.0000 | 0.9935 | 0.414 | 0.0065 | 155.1 |

### d3 circuit_level p=0.008 (results\m3\m3_learned_basis_repetition_circuit_level_d3__from_d3__to_d3__circuit_level__p0p008)

- graph: 8 detectors, 21 mechanisms, 34 edges; test shots: 32768 (seeds [301, 302])
- reweight strength fixed at 1.00

| decoder | logical errors | LER | s.e. | syndrome consistency | convergence | mean iterations | OSD rate | us/shot |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| mwpm | 159 | 0.00485 | 0.00038 | - | - | - | - | 0.3 |
| bp | 261 | 0.00797 | 0.00049 | 0.9875 | 0.9875 | 0.737 | - | 242.7 |
| bp_osd | 270 | 0.00824 | 0.00050 | 1.0000 | 0.9875 | 0.737 | 0.0125 | 234.1 |
| bp_gnn | 205 | 0.00626 | 0.00044 | 0.9903 | 0.9903 | 0.656 | - | 175.4 |
| bp_gnn_osd | 249 | 0.00760 | 0.00048 | 1.0000 | 0.9903 | 0.656 | 0.0097 | 174.0 |

### d3 circuit_level p=0.02 (results\m3\m3_learned_basis_repetition_circuit_level_d3__from_d3__to_d3__circuit_level__p0p02)

- graph: 8 detectors, 21 mechanisms, 34 edges; test shots: 32768 (seeds [301, 302])
- reweight strength fixed at 1.00

| decoder | logical errors | LER | s.e. | syndrome consistency | convergence | mean iterations | OSD rate | us/shot |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| mwpm | 837 | 0.02554 | 0.00087 | - | - | - | - | 0.7 |
| bp | 1359 | 0.04147 | 0.00110 | 0.9352 | 0.9352 | 2.798 | - | 744.5 |
| bp_osd | 1403 | 0.04282 | 0.00112 | 1.0000 | 0.9352 | 2.798 | 0.0648 | 679.7 |
| bp_gnn | 1146 | 0.03497 | 0.00101 | 0.9513 | 0.9513 | 2.318 | - | 600.6 |
| bp_gnn_osd | 1206 | 0.03680 | 0.00104 | 1.0000 | 0.9513 | 2.318 | 0.0487 | 574.4 |

### d5 circuit_level p=0.01 (results\m3\m3_transfer_d3_to_d5_8192shots)

- graph: 24 detectors, 101 mechanisms, 182 edges; test shots: 8192 (seeds [301])
- reweight strength fixed at 1.00

| decoder | logical errors | LER | s.e. | syndrome consistency | convergence | mean iterations | OSD rate | us/shot |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| mwpm | 11 | 0.00134 | 0.00040 | - | - | - | - | 0.4 |
| bp | 538 | 0.06567 | 0.00274 | 0.6539 | 0.6539 | 12.526 | - | 10762.9 |
| bp_gnn | 444 | 0.05420 | 0.00250 | 0.6477 | 0.6477 | 12.936 | - | 12506.6 |
| bp_gnn_osd | 648 | 0.07910 | 0.00298 | 1.0000 | 0.6477 | 12.936 | 0.3523 | 11821.4 |

