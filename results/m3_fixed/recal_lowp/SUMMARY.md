# M3 learned-prior strength recalibration under noise shift

| target p | selected strength | decoder | logical errors | LER | s.e. | syndrome consistency |
|---:|---:|---|---:|---:|---:|---:|
| 0.003 | 0.75 | bp | 34 | 0.00104 | 0.00018 | 0.9991 |
| 0.003 | 0.75 | bp_gnn_recalibrated | 32 | 0.00098 | 0.00017 | 0.9992 |
| 0.003 | 0.75 | bp_gnn_osd_recalibrated | 37 | 0.00113 | 0.00019 | 1.0000 |
| 0.005 | 1.00 | bp | 87 | 0.00266 | 0.00028 | 0.9972 |
| 0.005 | 1.00 | bp_gnn_recalibrated | 85 | 0.00259 | 0.00028 | 0.9976 |
| 0.005 | 1.00 | bp_gnn_osd_recalibrated | 91 | 0.00278 | 0.00029 | 1.0000 |
