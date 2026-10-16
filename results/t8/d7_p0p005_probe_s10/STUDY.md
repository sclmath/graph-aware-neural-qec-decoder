# T8 · OSD 候选集学习（OSD-CS / combination sweep）

- 配置：`results\m4_surface\m4_rotated_surface_code_circuit_level_d7_s1__d7__circuit_level__p0p005\config.json`
- 检查点：`results\m4_surface\m4_rotated_surface_code_circuit_level_d7_s1__d7__circuit_level__p0p005\model_state.pt`
- 测试集：1024 shots（seed [311]）
- 先验插值强度：1.0

## 1. 逐解码器

| decoder | logical errors | LER | s.e. | syndrome 一致率 |
|---|---:|---:|---:|---:|
| mwpm | 9 | 0.00879 | 0.00292 | 1.0000 |
| bp | 258 | 0.25195 | 0.01357 | 0.1133 |
| bp_osd_cs0 | 334 | 0.32617 | 0.01465 | 1.0000 |
| bp_osd_cs4 | 277 | 0.27051 | 0.01388 | 1.0000 |
| bp_gnn | 201 | 0.19629 | 0.01241 | 0.2832 |
| bp_gnn_osd_cs0 | 237 | 0.23145 | 0.01318 | 1.0000 |
| bp_gnn_osd_cs4 | 183 | 0.17871 | 0.01197 | 1.0000 |

## 2. 配对检验（McNemar，双侧）

| A | B | A 错 B 对 | A 对 B 错 | z | p (normal) | p (exact) |
|---|---|---:|---:|---:|---:|---:|
| bp | bp_osd_cs0 | 83 | 159 | -4.89 | 0.0000 | 0.0000 |
| bp_osd_cs0 | bp_osd_cs4 | 92 | 35 | 5.06 | 0.0000 | 0.0000 |
| bp | bp_osd_cs4 | 113 | 132 | -1.21 | 0.2248 | 0.2501 |
| bp_gnn | bp_gnn_osd_cs0 | 89 | 125 | -2.46 | 0.0139 | 0.0165 |
| bp_gnn_osd_cs0 | bp_gnn_osd_cs4 | 81 | 27 | 5.20 | 0.0000 | 0.0000 |
| bp_gnn | bp_gnn_osd_cs4 | 112 | 94 | 1.25 | 0.2098 | 0.2362 |
| bp_osd_cs0 | bp_gnn_osd_cs0 | 192 | 95 | 5.73 | 0.0000 | 0.0000 |
| bp_osd_cs4 | bp_gnn_osd_cs4 | 174 | 80 | 5.90 | 0.0000 | 0.0000 |

## 3. 未收敛子集（BP+GNN 未收敛的 shot）

- 未收敛 shot 数：734 / 1024

| decoder | 未收敛子集上的逻辑错误 |
|---|---:|
| mwpm | 9 |
| bp | 223 |
| bp_osd_cs0 | 280 |
| bp_osd_cs4 | 239 |
| bp_gnn | 201 |
| bp_gnn_osd_cs0 | 237 |
| bp_gnn_osd_cs4 | 183 |
