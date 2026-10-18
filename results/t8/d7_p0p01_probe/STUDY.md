# T8 · OSD 候选集学习（OSD-CS / combination sweep）

- 配置：`results\m4_surface\m4_rotated_surface_code_circuit_level_d7_s1__d7__circuit_level__p0p01\config.json`
- 检查点：`results\m4_surface\m4_rotated_surface_code_circuit_level_d7_s1__d7__circuit_level__p0p01\model_state.pt`
- 测试集：1024 shots（seed [301]）
- 先验插值强度：1.0

## 1. 逐解码器

| decoder | logical errors | LER | s.e. | syndrome 一致率 |
|---|---:|---:|---:|---:|
| mwpm | 95 | 0.09277 | 0.00907 | 1.0000 |
| bp | 389 | 0.37988 | 0.01517 | 0.0049 |
| bp_osd_cs0 | 442 | 0.43164 | 0.01548 | 1.0000 |
| bp_osd_cs4 | 429 | 0.41895 | 0.01542 | 1.0000 |
| bp_gnn | 355 | 0.34668 | 0.01487 | 0.0273 |
| bp_gnn_osd_cs0 | 397 | 0.38770 | 0.01523 | 1.0000 |
| bp_gnn_osd_cs4 | 378 | 0.36914 | 0.01508 | 1.0000 |

## 2. 配对检验（McNemar，双侧）

| A | B | A 错 B 对 | A 对 B 错 | z | p (normal) | p (exact) |
|---|---|---:|---:|---:|---:|---:|
| bp | bp_osd_cs0 | 155 | 208 | -2.78 | 0.0054 | 0.0063 |
| bp_osd_cs0 | bp_osd_cs4 | 76 | 63 | 1.10 | 0.2702 | 0.3088 |
| bp | bp_osd_cs4 | 164 | 204 | -2.09 | 0.0371 | 0.0419 |
| bp_gnn | bp_gnn_osd_cs0 | 144 | 186 | -2.31 | 0.0208 | 0.0239 |
| bp_gnn_osd_cs0 | bp_gnn_osd_cs4 | 73 | 54 | 1.69 | 0.0918 | 0.1098 |
| bp_gnn | bp_gnn_osd_cs4 | 156 | 179 | -1.26 | 0.2089 | 0.2293 |
| bp_osd_cs0 | bp_gnn_osd_cs0 | 239 | 194 | 2.16 | 0.0306 | 0.0344 |
| bp_osd_cs4 | bp_gnn_osd_cs4 | 231 | 180 | 2.52 | 0.0119 | 0.0136 |

## 3. 未收敛子集（BP+GNN 未收敛的 shot）

- 未收敛 shot 数：996 / 1024

| decoder | 未收敛子集上的逻辑错误 |
|---|---:|
| mwpm | 95 |
| bp | 381 |
| bp_osd_cs0 | 433 |
| bp_osd_cs4 | 422 |
| bp_gnn | 355 |
| bp_gnn_osd_cs0 | 397 |
| bp_gnn_osd_cs4 | 378 |
