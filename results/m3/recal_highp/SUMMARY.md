# M3 learned-prior strength recalibration under noise shift

| target p | selected strength | decoder | logical errors | LER | s.e. | syndrome consistency |
|---:|---:|---|---:|---:|---:|---:|
| 0.008 | 1.00 | bp | 197 | 0.00601 | 0.00043 | 0.9938 |
| 0.008 | 1.00 | bp_gnn_recalibrated | 194 | 0.00592 | 0.00042 | 0.9951 |
| 0.008 | 1.00 | bp_gnn_osd_recalibrated | 207 | 0.00632 | 0.00044 | 1.0000 |
| 0.02 | 1.00 | bp | 1129 | 0.03445 | 0.00101 | 0.9660 |
| 0.02 | 1.00 | bp_gnn_recalibrated | 1122 | 0.03424 | 0.00100 | 0.9700 |
| 0.02 | 1.00 | bp_gnn_osd_recalibrated | 1192 | 0.03638 | 0.00103 | 1.0000 |
