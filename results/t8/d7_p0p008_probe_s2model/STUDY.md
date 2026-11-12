# OSD 候选集学习（OSD-CS）

- 配置：`results\m4_surface\m4_rotated_surface_code_circuit_level_d7_s2__d7__circuit_level__p0p008\config.json`
- 检查点：`results\m4_surface\m4_rotated_surface_code_circuit_level_d7_s2__d7__circuit_level__p0p008\model_state.pt`
- 测试集：1024 shots（seed [302]）
- 先验插值强度：1.0

## 1. 逐解码器

| decoder | logical errors | LER | s.e. | syndrome 一致率 |
|---|---:|---:|---:|---:|
| mwpm | 45 | 0.04395 | 0.00641 | 1.0000 |
| bp | 355 | 0.34668 | 0.01487 | 0.0166 |
| bp_osd_cs0 | 426 | 0.41602 | 0.01540 | 1.0000 |
| bp_osd_cs4 | 381 | 0.37207 | 0.01510 | 1.0000 |
| bp_gnn | 344 | 0.33594 | 0.01476 | 0.0312 |
| bp_gnn_osd_cs0 | 392 | 0.38281 | 0.01519 | 1.0000 |
| bp_gnn_osd_cs4 | 347 | 0.33887 | 0.01479 | 1.0000 |

## 2. 配对检验（McNemar，双侧）

| A | B | A 错 B 对 | A 对 B 错 | z | p (normal) | p (exact) |
|---|---|---:|---:|---:|---:|---:|
| bp | bp_osd_cs0 | 125 | 196 | -3.96 | 0.0001 | 0.0001 |
| bp_osd_cs0 | bp_osd_cs4 | 102 | 57 | 3.57 | 0.0004 | 0.0004 |
| bp | bp_osd_cs4 | 142 | 168 | -1.48 | 0.1398 | 0.1555 |
| bp_gnn | bp_gnn_osd_cs0 | 160 | 208 | -2.50 | 0.0123 | 0.0142 |
| bp_gnn_osd_cs0 | bp_gnn_osd_cs4 | 122 | 77 | 3.19 | 0.0014 | 0.0017 |
| bp_gnn | bp_gnn_osd_cs4 | 173 | 176 | -0.16 | 0.8724 | 0.9148 |
| bp_osd_cs0 | bp_gnn_osd_cs0 | 229 | 195 | 1.65 | 0.0987 | 0.1089 |
| bp_osd_cs4 | bp_gnn_osd_cs4 | 215 | 181 | 1.71 | 0.0875 | 0.0971 |

## 3. 未收敛子集（BP+GNN 未收敛的 shot）

- 未收敛 shot 数：992 / 1024

| decoder | 未收敛子集上的逻辑错误 |
|---|---:|
| mwpm | 45 |
| bp | 349 |
| bp_osd_cs0 | 419 |
| bp_osd_cs4 | 377 |
| bp_gnn | 344 |
| bp_gnn_osd_cs0 | 392 |
| bp_gnn_osd_cs4 | 347 |
