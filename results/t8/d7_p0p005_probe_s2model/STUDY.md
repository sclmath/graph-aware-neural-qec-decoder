# T8 · OSD 候选集学习（OSD-CS / combination sweep）

- 配置：`results\m4_surface\m4_rotated_surface_code_circuit_level_d7_s2__d7__circuit_level__p0p005\config.json`
- 检查点：`results\m4_surface\m4_rotated_surface_code_circuit_level_d7_s2__d7__circuit_level__p0p005\model_state.pt`
- 测试集：1024 shots（seed [302]）
- 先验插值强度：1.0

## 1. 逐解码器

| decoder | logical errors | LER | s.e. | syndrome 一致率 |
|---|---:|---:|---:|---:|
| mwpm | 12 | 0.01172 | 0.00336 | 1.0000 |
| bp | 265 | 0.25879 | 0.01369 | 0.1182 |
| bp_osd_cs0 | 308 | 0.30078 | 0.01433 | 1.0000 |
| bp_osd_cs4 | 271 | 0.26465 | 0.01379 | 1.0000 |
| bp_gnn | 202 | 0.19727 | 0.01244 | 0.1855 |
| bp_gnn_osd_cs0 | 290 | 0.28320 | 0.01408 | 1.0000 |
| bp_gnn_osd_cs4 | 220 | 0.21484 | 0.01283 | 1.0000 |

## 2. 配对检验（McNemar，双侧）

| A | B | A 错 B 对 | A 对 B 错 | z | p (normal) | p (exact) |
|---|---|---:|---:|---:|---:|---:|
| bp | bp_osd_cs0 | 96 | 139 | -2.81 | 0.0050 | 0.0060 |
| bp_osd_cs0 | bp_osd_cs4 | 76 | 39 | 3.45 | 0.0006 | 0.0007 |
| bp | bp_osd_cs4 | 124 | 130 | -0.38 | 0.7066 | 0.7538 |
| bp_gnn | bp_gnn_osd_cs0 | 80 | 168 | -5.59 | 0.0000 | 0.0000 |
| bp_gnn_osd_cs0 | bp_gnn_osd_cs4 | 110 | 40 | 5.72 | 0.0000 | 0.0000 |
| bp_gnn | bp_gnn_osd_cs4 | 113 | 131 | -1.15 | 0.2492 | 0.2764 |
| bp_osd_cs0 | bp_gnn_osd_cs0 | 183 | 165 | 0.96 | 0.3346 | 0.3622 |
| bp_osd_cs4 | bp_gnn_osd_cs4 | 180 | 129 | 2.90 | 0.0037 | 0.0044 |

## 3. 未收敛子集（BP+GNN 未收敛的 shot）

- 未收敛 shot 数：834 / 1024

| decoder | 未收敛子集上的逻辑错误 |
|---|---:|
| mwpm | 12 |
| bp | 230 |
| bp_osd_cs0 | 267 |
| bp_osd_cs4 | 242 |
| bp_gnn | 202 |
| bp_gnn_osd_cs0 | 290 |
| bp_gnn_osd_cs4 | 220 |
