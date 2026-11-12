# OSD 候选集学习（OSD-CS）

- 配置：`results\m4_surface\m4_rotated_surface_code_circuit_level_d7_s1__d7__circuit_level__p0p008\config.json`
- 检查点：`results\m4_surface\m4_rotated_surface_code_circuit_level_d7_s1__d7__circuit_level__p0p008\model_state.pt`
- 测试集：1024 shots（seed [321]）
- 先验插值强度：1.0

## 1. 逐解码器

| decoder | logical errors | LER | s.e. | syndrome 一致率 |
|---|---:|---:|---:|---:|
| mwpm | 59 | 0.05762 | 0.00728 | 1.0000 |
| bp | 362 | 0.35352 | 0.01494 | 0.0098 |
| bp_osd_cs0 | 406 | 0.39648 | 0.01529 | 1.0000 |
| bp_osd_cs4 | 385 | 0.37598 | 0.01514 | 1.0000 |
| bp_gnn | 310 | 0.30273 | 0.01436 | 0.0557 |
| bp_gnn_osd_cs0 | 391 | 0.38184 | 0.01518 | 1.0000 |
| bp_gnn_osd_cs4 | 306 | 0.29883 | 0.01430 | 1.0000 |

## 2. 配对检验（McNemar，双侧）

| A | B | A 错 B 对 | A 对 B 错 | z | p (normal) | p (exact) |
|---|---|---:|---:|---:|---:|---:|
| bp | bp_osd_cs0 | 134 | 178 | -2.49 | 0.0127 | 0.0148 |
| bp_osd_cs0 | bp_osd_cs4 | 70 | 49 | 1.93 | 0.0542 | 0.0663 |
| bp | bp_osd_cs4 | 155 | 178 | -1.26 | 0.2075 | 0.2279 |
| bp_gnn | bp_gnn_osd_cs0 | 100 | 181 | -4.83 | 0.0000 | 0.0000 |
| bp_gnn_osd_cs0 | bp_gnn_osd_cs4 | 117 | 32 | 6.96 | 0.0000 | 0.0000 |
| bp_gnn | bp_gnn_osd_cs4 | 143 | 139 | 0.24 | 0.8117 | 0.8583 |
| bp_osd_cs0 | bp_gnn_osd_cs0 | 187 | 172 | 0.79 | 0.4286 | 0.4600 |
| bp_osd_cs4 | bp_gnn_osd_cs4 | 234 | 155 | 4.01 | 0.0001 | 0.0001 |

## 3. 未收敛子集（BP+GNN 未收敛的 shot）

- 未收敛 shot 数：967 / 1024

| decoder | 未收敛子集上的逻辑错误 |
|---|---:|
| mwpm | 59 |
| bp | 352 |
| bp_osd_cs0 | 389 |
| bp_osd_cs4 | 370 |
| bp_gnn | 310 |
| bp_gnn_osd_cs0 | 391 |
| bp_gnn_osd_cs4 | 306 |
