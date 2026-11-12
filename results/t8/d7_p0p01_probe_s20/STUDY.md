# OSD 候选集学习（OSD-CS）

- 配置：`results\m4_surface\m4_rotated_surface_code_circuit_level_d7_s1__d7__circuit_level__p0p01\config.json`
- 检查点：`results\m4_surface\m4_rotated_surface_code_circuit_level_d7_s1__d7__circuit_level__p0p01\model_state.pt`
- 测试集：1024 shots（seed [321]）
- 先验插值强度：1.0

## 1. 逐解码器

| decoder | logical errors | LER | s.e. | syndrome 一致率 |
|---|---:|---:|---:|---:|
| mwpm | 103 | 0.10059 | 0.00940 | 1.0000 |
| bp | 401 | 0.39160 | 0.01525 | 0.0020 |
| bp_osd_cs0 | 437 | 0.42676 | 0.01546 | 1.0000 |
| bp_osd_cs4 | 425 | 0.41504 | 0.01540 | 1.0000 |
| bp_gnn | 346 | 0.33789 | 0.01478 | 0.0205 |
| bp_gnn_osd_cs0 | 434 | 0.42383 | 0.01544 | 1.0000 |
| bp_gnn_osd_cs4 | 388 | 0.37891 | 0.01516 | 1.0000 |

## 2. 配对检验（McNemar，双侧）

| A | B | A 错 B 对 | A 对 B 错 | z | p (normal) | p (exact) |
|---|---|---:|---:|---:|---:|---:|
| bp | bp_osd_cs0 | 153 | 189 | -1.95 | 0.0516 | 0.0583 |
| bp_osd_cs0 | bp_osd_cs4 | 83 | 71 | 0.97 | 0.3336 | 0.3755 |
| bp | bp_osd_cs4 | 170 | 194 | -1.26 | 0.2084 | 0.2280 |
| bp_gnn | bp_gnn_osd_cs0 | 138 | 226 | -4.61 | 0.0000 | 0.0000 |
| bp_gnn_osd_cs0 | bp_gnn_osd_cs4 | 114 | 68 | 3.41 | 0.0007 | 0.0008 |
| bp_gnn | bp_gnn_osd_cs4 | 156 | 198 | -2.23 | 0.0256 | 0.0292 |
| bp_osd_cs0 | bp_gnn_osd_cs0 | 200 | 197 | 0.15 | 0.8803 | 0.9201 |
| bp_osd_cs4 | bp_gnn_osd_cs4 | 224 | 187 | 1.83 | 0.0680 | 0.0756 |

## 3. 未收敛子集（BP+GNN 未收敛的 shot）

- 未收敛 shot 数：1003 / 1024

| decoder | 未收敛子集上的逻辑错误 |
|---|---:|
| mwpm | 103 |
| bp | 397 |
| bp_osd_cs0 | 433 |
| bp_osd_cs4 | 421 |
| bp_gnn | 346 |
| bp_gnn_osd_cs0 | 434 |
| bp_gnn_osd_cs4 | 388 |
