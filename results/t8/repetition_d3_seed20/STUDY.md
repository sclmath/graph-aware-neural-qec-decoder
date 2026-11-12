# OSD 候选集学习（OSD-CS）

- 配置：`results\m2\m2_learned_basis_repetition_circuit_level_d3_s20__d3__circuit_level__p0p01\config.json`
- 检查点：`results\m2\m2_learned_basis_repetition_circuit_level_d3_s20__d3__circuit_level__p0p01\model_state.pt`
- 测试集：32768 shots（seed [321, 322]）
- 先验插值强度：1.0

## 1. 逐解码器

| decoder | logical errors | LER | s.e. | syndrome 一致率 |
|---|---:|---:|---:|---:|
| mwpm | 247 | 0.00754 | 0.00048 | 1.0000 |
| bp | 359 | 0.01096 | 0.00058 | 0.9894 |
| bp_osd_cs0 | 365 | 0.01114 | 0.00058 | 1.0000 |
| bp_osd_cs4 | 272 | 0.00830 | 0.00050 | 1.0000 |
| bp_gnn | 360 | 0.01099 | 0.00058 | 0.9908 |
| bp_gnn_osd_cs0 | 383 | 0.01169 | 0.00059 | 1.0000 |
| bp_gnn_osd_cs4 | 278 | 0.00848 | 0.00051 | 1.0000 |

## 2. 配对检验（McNemar，双侧）

| A | B | A 错 B 对 | A 对 B 错 | z | p (normal) | p (exact) |
|---|---|---:|---:|---:|---:|---:|
| bp | bp_osd_cs0 | 71 | 77 | -0.49 | 0.6219 | 0.6812 |
| bp_osd_cs0 | bp_osd_cs4 | 128 | 35 | 7.28 | 0.0000 | 0.0000 |
| bp | bp_osd_cs4 | 132 | 45 | 6.54 | 0.0000 | 0.0000 |
| bp_gnn | bp_gnn_osd_cs0 | 50 | 73 | -2.07 | 0.0381 | 0.0469 |
| bp_gnn_osd_cs0 | bp_gnn_osd_cs4 | 159 | 54 | 7.19 | 0.0000 | 0.0000 |
| bp_gnn | bp_gnn_osd_cs4 | 125 | 43 | 6.33 | 0.0000 | 0.0000 |
| bp_osd_cs0 | bp_gnn_osd_cs0 | 25 | 43 | -2.18 | 0.0290 | 0.0385 |
| bp_osd_cs4 | bp_gnn_osd_cs4 | 7 | 13 | -1.34 | 0.1797 | 0.2632 |

## 3. 未收敛子集（BP+GNN 未收敛的 shot）

- 未收敛 shot 数：300 / 32768

| decoder | 未收敛子集上的逻辑错误 |
|---|---:|
| mwpm | 84 |
| bp | 175 |
| bp_osd_cs0 | 183 |
| bp_osd_cs4 | 92 |
| bp_gnn | 179 |
| bp_gnn_osd_cs0 | 202 |
| bp_gnn_osd_cs4 | 97 |
