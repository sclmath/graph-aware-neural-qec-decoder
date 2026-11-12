# OSD 候选集学习（OSD-CS）

- 配置：`results\m4_surface\m4_rotated_surface_code_circuit_level_d7_s1__d7__circuit_level__p0p005\config.json`
- 检查点：`results\m4_surface\m4_rotated_surface_code_circuit_level_d7_s1__d7__circuit_level__p0p005\model_state.pt`
- 测试集：1024 shots（seed [321]）
- 先验插值强度：1.0

## 1. 逐解码器

| decoder | logical errors | LER | s.e. | syndrome 一致率 |
|---|---:|---:|---:|---:|
| mwpm | 8 | 0.00781 | 0.00275 | 1.0000 |
| bp | 260 | 0.25391 | 0.01360 | 0.1221 |
| bp_osd_cs0 | 291 | 0.28418 | 0.01409 | 1.0000 |
| bp_osd_cs4 | 241 | 0.23535 | 0.01326 | 1.0000 |
| bp_gnn | 175 | 0.17090 | 0.01176 | 0.2900 |
| bp_gnn_osd_cs0 | 219 | 0.21387 | 0.01281 | 1.0000 |
| bp_gnn_osd_cs4 | 164 | 0.16016 | 0.01146 | 1.0000 |

## 2. 配对检验（McNemar，双侧）

| A | B | A 错 B 对 | A 对 B 错 | z | p (normal) | p (exact) |
|---|---|---:|---:|---:|---:|---:|
| bp | bp_osd_cs0 | 104 | 135 | -2.01 | 0.0449 | 0.0521 |
| bp_osd_cs0 | bp_osd_cs4 | 89 | 39 | 4.42 | 0.0000 | 0.0000 |
| bp | bp_osd_cs4 | 141 | 122 | 1.17 | 0.2414 | 0.2670 |
| bp_gnn | bp_gnn_osd_cs0 | 72 | 116 | -3.21 | 0.0013 | 0.0016 |
| bp_gnn_osd_cs0 | bp_gnn_osd_cs4 | 79 | 24 | 5.42 | 0.0000 | 0.0000 |
| bp_gnn | bp_gnn_osd_cs4 | 95 | 84 | 0.82 | 0.4110 | 0.4549 |
| bp_osd_cs0 | bp_gnn_osd_cs0 | 186 | 114 | 4.16 | 0.0000 | 0.0000 |
| bp_osd_cs4 | bp_gnn_osd_cs4 | 171 | 94 | 4.73 | 0.0000 | 0.0000 |

## 3. 未收敛子集（BP+GNN 未收敛的 shot）

- 未收敛 shot 数：727 / 1024

| decoder | 未收敛子集上的逻辑错误 |
|---|---:|
| mwpm | 8 |
| bp | 222 |
| bp_osd_cs0 | 239 |
| bp_osd_cs4 | 206 |
| bp_gnn | 175 |
| bp_gnn_osd_cs0 | 219 |
| bp_gnn_osd_cs4 | 164 |
