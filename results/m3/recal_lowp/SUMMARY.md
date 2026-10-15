# M3 learned-prior strength recalibration under noise shift

| target p | selected strength | decoder | logical errors | LER | s.e. | syndrome consistency |
|---:|---:|---|---:|---:|---:|---:|
| 0.003 | 0.75 | bp | 43 | 0.00131 | 0.00020 | 0.9982 |
| 0.003 | 0.75 | bp_gnn_recalibrated | 34 | 0.00104 | 0.00018 | 0.9986 |
| 0.003 | 0.75 | bp_gnn_osd_recalibrated | 34 | 0.00104 | 0.00018 | 1.0000 |
| 0.005 | 0.75 | bp | 123 | 0.00375 | 0.00034 | 0.9947 |
| 0.005 | 0.75 | bp_gnn_recalibrated | 93 | 0.00284 | 0.00029 | 0.9962 |
| 0.005 | 0.75 | bp_gnn_osd_recalibrated | 98 | 0.00299 | 0.00030 | 1.0000 |
