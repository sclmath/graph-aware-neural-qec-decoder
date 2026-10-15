# M3 result summary

Source: `results\m3_fixed`

Source checkpoint: repetition_code d=3 r=3 circuit_level p=0.01

## In-distribution reference (source noise rate)

| experiment | shots | decoders |
|---|---|---|
| m3_learned_basis_repetition_circuit_level_d3 d3 p=0.01 | 32768 | mwpm, bp, bp_osd, bp_gnn, bp_gnn_osd, bp_gnn_osd_learned_order, osd_gnn |

## Noise-rate extrapolation (same code, different physical error rate)

Test logical error rate:

| physical_error_rate | shots | mwpm | bp | bp_osd | bp_gnn | bp_gnn_osd |
|---|---|---|---|---|---|---|
| 0.003 | 32768 | 0.00082 | 0.00104 | 0.00107 | 0.00098 | 0.00113 |
| 0.005 | 32768 | 0.00174 | 0.00266 | 0.00287 | 0.00259 | 0.00278 |
| 0.008 | 32768 | 0.00485 | 0.00601 | 0.00638 | 0.00592 | 0.00632 |
| 0.02 | 32768 | 0.02554 | 0.03445 | 0.03839 | 0.03424 | 0.03638 |

Syndrome consistency rate:

| target | mwpm | bp | bp_osd | bp_gnn | bp_gnn_osd |
|---|---|---|---|---|---|
| d3 p=0.003 | - | 0.9991 | 1.0000 | 0.9992 | 1.0000 |
| d3 p=0.005 | - | 0.9972 | 1.0000 | 0.9976 | 1.0000 |
| d3 p=0.008 | - | 0.9938 | 1.0000 | 0.9951 | 1.0000 |
| d3 p=0.02 | - | 0.9660 | 1.0000 | 0.9700 | 1.0000 |

## Code-distance extrapolation (same noise model and code family)

Test logical error rate:

| distance | shots | mwpm | bp | bp_osd | bp_gnn | bp_gnn_osd |
|---|---|---|---|---|---|---|
| 5 | 8192 | 0.00134 | 0.05078 | 0.06299 | 0.01709 | 0.02356 |

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

### d3 circuit_level p=0.003 (results\m3_fixed\m3_learned_basis_repetition_circuit_level_d3__from_d3__to_d3__circuit_level__p0p003)

- graph: 8 detectors, 21 mechanisms, 34 edges; test shots: 32768 (seeds [301, 302])
- reweight strength fixed at 1.00

| decoder | logical errors | LER | s.e. | syndrome consistency | convergence | mean iterations | OSD rate | us/shot |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| mwpm | 27 | 0.00082 | 0.00016 | - | - | - | - | 0.1 |
| bp | 34 | 0.00104 | 0.00018 | 0.9991 | 0.9991 | 0.156 | - | 2.6 |
| bp_osd | 35 | 0.00107 | 0.00018 | 1.0000 | 0.9991 | 0.156 | 0.0009 | 2.9 |
| bp_gnn | 32 | 0.00098 | 0.00017 | 0.9992 | 0.9992 | 0.119 | - | 2.2 |
| bp_gnn_osd | 37 | 0.00113 | 0.00019 | 1.0000 | 0.9992 | 0.119 | 0.0008 | 2.3 |

### d3 circuit_level p=0.005 (results\m3_fixed\m3_learned_basis_repetition_circuit_level_d3__from_d3__to_d3__circuit_level__p0p005)

- graph: 8 detectors, 21 mechanisms, 34 edges; test shots: 32768 (seeds [301, 302])
- reweight strength fixed at 1.00

| decoder | logical errors | LER | s.e. | syndrome consistency | convergence | mean iterations | OSD rate | us/shot |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| mwpm | 57 | 0.00174 | 0.00023 | - | - | - | - | 0.2 |
| bp | 87 | 0.00266 | 0.00028 | 0.9972 | 0.9972 | 0.294 | - | 4.5 |
| bp_osd | 94 | 0.00287 | 0.00030 | 1.0000 | 0.9972 | 0.294 | 0.0028 | 5.7 |
| bp_gnn | 85 | 0.00259 | 0.00028 | 0.9976 | 0.9976 | 0.229 | - | 4.0 |
| bp_gnn_osd | 91 | 0.00278 | 0.00029 | 1.0000 | 0.9976 | 0.229 | 0.0024 | 4.6 |

### d3 circuit_level p=0.008 (results\m3_fixed\m3_learned_basis_repetition_circuit_level_d3__from_d3__to_d3__circuit_level__p0p008)

- graph: 8 detectors, 21 mechanisms, 34 edges; test shots: 32768 (seeds [301, 302])
- reweight strength fixed at 1.00

| decoder | logical errors | LER | s.e. | syndrome consistency | convergence | mean iterations | OSD rate | us/shot |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| mwpm | 159 | 0.00485 | 0.00038 | - | - | - | - | 0.2 |
| bp | 197 | 0.00601 | 0.00043 | 0.9938 | 0.9938 | 0.519 | - | 7.9 |
| bp_osd | 209 | 0.00638 | 0.00044 | 1.0000 | 0.9938 | 0.519 | 0.0062 | 9.2 |
| bp_gnn | 194 | 0.00592 | 0.00042 | 0.9951 | 0.9951 | 0.391 | - | 3.6 |
| bp_gnn_osd | 207 | 0.00632 | 0.00044 | 1.0000 | 0.9951 | 0.391 | 0.0049 | 4.4 |

### d3 circuit_level p=0.02 (results\m3_fixed\m3_learned_basis_repetition_circuit_level_d3__from_d3__to_d3__circuit_level__p0p02)

- graph: 8 detectors, 21 mechanisms, 34 edges; test shots: 32768 (seeds [301, 302])
- reweight strength fixed at 1.00

| decoder | logical errors | LER | s.e. | syndrome consistency | convergence | mean iterations | OSD rate | us/shot |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| mwpm | 837 | 0.02554 | 0.00087 | - | - | - | - | 0.4 |
| bp | 1129 | 0.03445 | 0.00101 | 0.9660 | 0.9660 | 1.782 | - | 19.0 |
| bp_osd | 1258 | 0.03839 | 0.00106 | 1.0000 | 0.9660 | 1.782 | 0.0340 | 31.5 |
| bp_gnn | 1122 | 0.03424 | 0.00100 | 0.9700 | 0.9700 | 1.428 | - | 11.7 |
| bp_gnn_osd | 1192 | 0.03638 | 0.00103 | 1.0000 | 0.9700 | 1.428 | 0.0300 | 18.9 |

### d5 circuit_level p=0.01 (results\m3_fixed\m3_learned_basis_repetition_circuit_level_d3__from_d3__to_d5__circuit_level__p0p01)

- graph: 24 detectors, 101 mechanisms, 182 edges; test shots: 8192 (seeds [301])
- reweight strength fixed at 1.00

| decoder | logical errors | LER | s.e. | syndrome consistency | convergence | mean iterations | OSD rate | us/shot |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| mwpm | 11 | 0.00134 | 0.00040 | - | - | - | - | 0.9 |
| bp | 416 | 0.05078 | 0.00243 | 0.8795 | 0.8795 | 5.467 | - | 336.7 |
| bp_osd | 516 | 0.06299 | 0.00268 | 1.0000 | 0.8795 | 5.467 | 0.1205 | 416.0 |
| bp_gnn | 140 | 0.01709 | 0.00143 | 0.9634 | 0.9634 | 1.889 | - | 31.8 |
| bp_gnn_osd | 193 | 0.02356 | 0.00168 | 1.0000 | 0.9634 | 1.889 | 0.0366 | 58.8 |

