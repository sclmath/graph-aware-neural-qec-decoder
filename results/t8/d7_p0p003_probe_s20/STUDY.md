# T8 · OSD 候选集学习（OSD-CS / combination sweep）

- 配置：`results\m4_surface\m4_rotated_surface_code_circuit_level_d7_s1__d7__circuit_level__p0p003\config.json`
- 检查点：`results\m4_surface\m4_rotated_surface_code_circuit_level_d7_s1__d7__circuit_level__p0p003\model_state.pt`
- 测试集：1024 shots（seed [321]）
- 先验插值强度：1.0

## 1. 逐解码器

| decoder | logical errors | LER | s.e. | syndrome 一致率 |
|---|---:|---:|---:|---:|
| mwpm | 0 | 0.00000 | 0.00000 | 1.0000 |
| bp | 175 | 0.17090 | 0.01176 | 0.3320 |
| bp_osd_cs0 | 224 | 0.21875 | 0.01292 | 1.0000 |
| bp_osd_cs4 | 146 | 0.14258 | 0.01093 | 1.0000 |
| bp_gnn | 102 | 0.09961 | 0.00936 | 0.5850 |
| bp_gnn_osd_cs0 | 105 | 0.10254 | 0.00948 | 1.0000 |
| bp_gnn_osd_cs4 | 72 | 0.07031 | 0.00799 | 1.0000 |

## 2. 配对检验（McNemar，双侧）

| A | B | A 错 B 对 | A 对 B 错 | z | p (normal) | p (exact) |
|---|---|---:|---:|---:|---:|---:|
| bp | bp_osd_cs0 | 52 | 101 | -3.96 | 0.0001 | 0.0001 |
| bp_osd_cs0 | bp_osd_cs4 | 96 | 18 | 7.31 | 0.0000 | 0.0000 |
| bp | bp_osd_cs4 | 105 | 76 | 2.16 | 0.0311 | 0.0371 |
| bp_gnn | bp_gnn_osd_cs0 | 67 | 70 | -0.26 | 0.7977 | 0.8644 |
| bp_gnn_osd_cs0 | bp_gnn_osd_cs4 | 45 | 12 | 4.37 | 0.0000 | 0.0000 |
| bp_gnn | bp_gnn_osd_cs4 | 71 | 41 | 2.83 | 0.0046 | 0.0059 |
| bp_osd_cs0 | bp_gnn_osd_cs0 | 169 | 50 | 8.04 | 0.0000 | 0.0000 |
| bp_osd_cs4 | bp_gnn_osd_cs4 | 116 | 42 | 5.89 | 0.0000 | 0.0000 |

## 3. 未收敛子集（BP+GNN 未收敛的 shot）

- 未收敛 shot 数：425 / 1024

| decoder | 未收敛子集上的逻辑错误 |
|---|---:|
| mwpm | 0 |
| bp | 115 |
| bp_osd_cs0 | 146 |
| bp_osd_cs4 | 107 |
| bp_gnn | 102 |
| bp_gnn_osd_cs0 | 105 |
| bp_gnn_osd_cs4 | 72 |
