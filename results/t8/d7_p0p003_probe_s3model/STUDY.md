# OSD 候选集学习（OSD-CS）

- 配置：`results\m4_surface\m4_rotated_surface_code_circuit_level_d7_s3__d7__circuit_level__p0p003\config.json`
- 检查点：`results\m4_surface\m4_rotated_surface_code_circuit_level_d7_s3__d7__circuit_level__p0p003\model_state.pt`
- 测试集：1024 shots（seed [303]）
- 先验插值强度：1.0

## 1. 逐解码器

| decoder | logical errors | LER | s.e. | syndrome 一致率 |
|---|---:|---:|---:|---:|
| mwpm | 2 | 0.00195 | 0.00138 | 1.0000 |
| bp | 156 | 0.15234 | 0.01123 | 0.3379 |
| bp_osd_cs0 | 187 | 0.18262 | 0.01207 | 1.0000 |
| bp_osd_cs4 | 128 | 0.12500 | 0.01033 | 1.0000 |
| bp_gnn | 123 | 0.12012 | 0.01016 | 0.3584 |
| bp_gnn_osd_cs0 | 182 | 0.17773 | 0.01195 | 1.0000 |
| bp_gnn_osd_cs4 | 102 | 0.09961 | 0.00936 | 1.0000 |

## 2. 配对检验（McNemar，双侧）

| A | B | A 错 B 对 | A 对 B 错 | z | p (normal) | p (exact) |
|---|---|---:|---:|---:|---:|---:|
| bp | bp_osd_cs0 | 53 | 84 | -2.65 | 0.0081 | 0.0101 |
| bp_osd_cs0 | bp_osd_cs4 | 86 | 27 | 5.55 | 0.0000 | 0.0000 |
| bp | bp_osd_cs4 | 97 | 69 | 2.17 | 0.0298 | 0.0358 |
| bp_gnn | bp_gnn_osd_cs0 | 56 | 115 | -4.51 | 0.0000 | 0.0000 |
| bp_gnn_osd_cs0 | bp_gnn_osd_cs4 | 94 | 14 | 7.70 | 0.0000 | 0.0000 |
| bp_gnn | bp_gnn_osd_cs4 | 83 | 62 | 1.74 | 0.0812 | 0.0964 |
| bp_osd_cs0 | bp_gnn_osd_cs0 | 106 | 101 | 0.35 | 0.7282 | 0.7811 |
| bp_osd_cs4 | bp_gnn_osd_cs4 | 88 | 62 | 2.12 | 0.0338 | 0.0409 |

## 3. 未收敛子集（BP+GNN 未收敛的 shot）

- 未收敛 shot 数：657 / 1024

| decoder | 未收敛子集上的逻辑错误 |
|---|---:|
| mwpm | 2 |
| bp | 130 |
| bp_osd_cs0 | 161 |
| bp_osd_cs4 | 115 |
| bp_gnn | 123 |
| bp_gnn_osd_cs0 | 182 |
| bp_gnn_osd_cs4 | 102 |
