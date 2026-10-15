# T8 · OSD 候选集学习（OSD-CS / combination sweep）

- 配置：`results\m4_surface\m4_rotated_surface_code_circuit_level_d7_s1__d7__circuit_level__p0p005\config.json`
- 检查点：`results\m4_surface\m4_rotated_surface_code_circuit_level_d7_s1__d7__circuit_level__p0p005\model_state.pt`
- 测试集：1024 shots（seed [301]）
- 先验插值强度：1.0

## 1. 逐解码器

| decoder | logical errors | LER | s.e. | syndrome 一致率 |
|---|---:|---:|---:|---:|
| mwpm | 15 | 0.01465 | 0.00375 | 1.0000 |
| bp | 226 | 0.22070 | 0.01296 | 0.1289 |
| bp_osd_cs0 | 280 | 0.27344 | 0.01393 | 1.0000 |
| bp_osd_cs4 | 238 | 0.23242 | 0.01320 | 1.0000 |
| bp_gnn | 169 | 0.16504 | 0.01160 | 0.3154 |
| bp_gnn_osd_cs0 | 187 | 0.18262 | 0.01207 | 1.0000 |
| bp_gnn_osd_cs4 | 135 | 0.13184 | 0.01057 | 1.0000 |

## 2. 配对检验（McNemar，双侧）

| A | B | A 错 B 对 | A 对 B 错 | z | p (normal) | p (exact) |
|---|---|---:|---:|---:|---:|---:|
| bp | bp_osd_cs0 | 84 | 138 | -3.62 | 0.0003 | 0.0004 |
| bp_osd_cs0 | bp_osd_cs4 | 85 | 43 | 3.71 | 0.0002 | 0.0003 |
| bp | bp_osd_cs4 | 115 | 127 | -0.77 | 0.4405 | 0.4796 |
| bp_gnn | bp_gnn_osd_cs0 | 77 | 95 | -1.37 | 0.1699 | 0.1947 |
| bp_gnn_osd_cs0 | bp_gnn_osd_cs4 | 73 | 21 | 5.36 | 0.0000 | 0.0000 |
| bp_gnn | bp_gnn_osd_cs4 | 102 | 68 | 2.61 | 0.0091 | 0.0112 |
| bp_osd_cs0 | bp_gnn_osd_cs0 | 181 | 88 | 5.67 | 0.0000 | 0.0000 |
| bp_osd_cs4 | bp_gnn_osd_cs4 | 173 | 70 | 6.61 | 0.0000 | 0.0000 |

## 3. 未收敛子集（BP+GNN 未收敛的 shot）

- 未收敛 shot 数：701 / 1024

| decoder | 未收敛子集上的逻辑错误 |
|---|---:|
| mwpm | 15 |
| bp | 188 |
| bp_osd_cs0 | 228 |
| bp_osd_cs4 | 201 |
| bp_gnn | 169 |
| bp_gnn_osd_cs0 | 187 |
| bp_gnn_osd_cs4 | 135 |
