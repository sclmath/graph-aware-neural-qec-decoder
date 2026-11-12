# OSD 候选集学习（OSD-CS）

- 配置：`results\m4_surface\m4_rotated_surface_code_circuit_level_d7_s1__d7__circuit_level__p0p01\config.json`
- 检查点：`results\m4_surface\m4_rotated_surface_code_circuit_level_d7_s1__d7__circuit_level__p0p01\model_state.pt`
- 测试集：1024 shots（seed [311]）
- 先验插值强度：1.0

## 1. 逐解码器

| decoder | logical errors | LER | s.e. | syndrome 一致率 |
|---|---:|---:|---:|---:|
| mwpm | 101 | 0.09863 | 0.00932 | 1.0000 |
| bp | 422 | 0.41211 | 0.01538 | 0.0020 |
| bp_osd_cs0 | 459 | 0.44824 | 0.01554 | 1.0000 |
| bp_osd_cs4 | 439 | 0.42871 | 0.01547 | 1.0000 |
| bp_gnn | 322 | 0.31445 | 0.01451 | 0.0156 |
| bp_gnn_osd_cs0 | 384 | 0.37500 | 0.01513 | 1.0000 |
| bp_gnn_osd_cs4 | 343 | 0.33496 | 0.01475 | 1.0000 |

## 2. 配对检验（McNemar，双侧）

| A | B | A 错 B 对 | A 对 B 错 | z | p (normal) | p (exact) |
|---|---|---:|---:|---:|---:|---:|
| bp | bp_osd_cs0 | 166 | 203 | -1.93 | 0.0541 | 0.0608 |
| bp_osd_cs0 | bp_osd_cs4 | 87 | 67 | 1.61 | 0.1070 | 0.1255 |
| bp | bp_osd_cs4 | 178 | 195 | -0.88 | 0.3787 | 0.4074 |
| bp_gnn | bp_gnn_osd_cs0 | 128 | 190 | -3.48 | 0.0005 | 0.0006 |
| bp_gnn_osd_cs0 | bp_gnn_osd_cs4 | 88 | 47 | 3.53 | 0.0004 | 0.0005 |
| bp_gnn | bp_gnn_osd_cs4 | 148 | 169 | -1.18 | 0.2382 | 0.2613 |
| bp_osd_cs0 | bp_gnn_osd_cs0 | 248 | 173 | 3.66 | 0.0003 | 0.0003 |
| bp_osd_cs4 | bp_gnn_osd_cs4 | 258 | 162 | 4.68 | 0.0000 | 0.0000 |

## 3. 未收敛子集（BP+GNN 未收敛的 shot）

- 未收敛 shot 数：1008 / 1024

| decoder | 未收敛子集上的逻辑错误 |
|---|---:|
| mwpm | 101 |
| bp | 418 |
| bp_osd_cs0 | 457 |
| bp_osd_cs4 | 439 |
| bp_gnn | 322 |
| bp_gnn_osd_cs0 | 384 |
| bp_gnn_osd_cs4 | 343 |
