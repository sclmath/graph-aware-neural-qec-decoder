# T8 · OSD 候选集学习（OSD-CS / combination sweep）

- 配置：`results\m2\m2_learned_basis_repetition_circuit_level_d3_s10__d3__circuit_level__p0p01\config.json`
- 检查点：`results\m2\m2_learned_basis_repetition_circuit_level_d3_s10__d3__circuit_level__p0p01\model_state.pt`
- 测试集：32768 shots（seed [311, 312]）
- 先验插值强度：1.0

## 1. 逐解码器

| decoder | logical errors | LER | s.e. | syndrome 一致率 |
|---|---:|---:|---:|---:|
| mwpm | 231 | 0.00705 | 0.00046 | 1.0000 |
| bp | 338 | 0.01031 | 0.00056 | 0.9897 |
| bp_osd_cs0 | 350 | 0.01068 | 0.00057 | 1.0000 |
| bp_osd_cs4 | 253 | 0.00772 | 0.00048 | 1.0000 |
| bp_gnn | 306 | 0.00934 | 0.00053 | 0.9928 |
| bp_gnn_osd_cs0 | 300 | 0.00916 | 0.00053 | 1.0000 |
| bp_gnn_osd_cs4 | 299 | 0.00912 | 0.00053 | 1.0000 |

## 2. 配对检验（McNemar，双侧）

| A | B | A 错 B 对 | A 对 B 错 | z | p (normal) | p (exact) |
|---|---|---:|---:|---:|---:|---:|
| bp | bp_osd_cs0 | 74 | 86 | -0.95 | 0.3428 | 0.3846 |
| bp_osd_cs0 | bp_osd_cs4 | 134 | 37 | 7.42 | 0.0000 | 0.0000 |
| bp | bp_osd_cs4 | 131 | 46 | 6.39 | 0.0000 | 0.0000 |
| bp_gnn | bp_gnn_osd_cs0 | 70 | 64 | 0.52 | 0.6042 | 0.6660 |
| bp_gnn_osd_cs0 | bp_gnn_osd_cs4 | 72 | 71 | 0.08 | 0.9334 | 1.0000 |
| bp_gnn | bp_gnn_osd_cs4 | 71 | 64 | 0.60 | 0.5469 | 0.6057 |
| bp_osd_cs0 | bp_gnn_osd_cs0 | 137 | 87 | 3.34 | 0.0008 | 0.0010 |
| bp_osd_cs4 | bp_gnn_osd_cs4 | 76 | 122 | -3.27 | 0.0011 | 0.0013 |

## 3. 未收敛子集（BP+GNN 未收敛的 shot）

- 未收敛 shot 数：235 / 32768

| decoder | 未收敛子集上的逻辑错误 |
|---|---:|
| mwpm | 80 |
| bp | 125 |
| bp_osd_cs0 | 112 |
| bp_osd_cs4 | 84 |
| bp_gnn | 127 |
| bp_gnn_osd_cs0 | 121 |
| bp_gnn_osd_cs4 | 120 |
