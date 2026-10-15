# M3 learned-prior strength recalibration under noise shift

| target p | selected strength | decoder | logical errors | LER | s.e. | syndrome consistency |
|---:|---:|---|---:|---:|---:|---:|
| 0.008 | 0.75 | bp | 261 | 0.00797 | 0.00049 | 0.9875 |
| 0.008 | 0.75 | bp_gnn_recalibrated | 200 | 0.00610 | 0.00043 | 0.9920 |
| 0.008 | 0.75 | bp_gnn_osd_recalibrated | 210 | 0.00641 | 0.00044 | 1.0000 |
| 0.02 | 1.00 | bp | 1359 | 0.04147 | 0.00110 | 0.9352 |
| 0.02 | 1.00 | bp_gnn_recalibrated | 1146 | 0.03497 | 0.00101 | 0.9513 |
| 0.02 | 1.00 | bp_gnn_osd_recalibrated | 1206 | 0.03680 | 0.00104 | 1.0000 |
