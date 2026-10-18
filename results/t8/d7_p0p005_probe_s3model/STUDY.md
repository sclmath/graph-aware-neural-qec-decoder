# T8 · OSD 候选集学习（OSD-CS / combination sweep）

- 配置：`results\m4_surface\m4_rotated_surface_code_circuit_level_d7_s3__d7__circuit_level__p0p005\config.json`
- 检查点：`results\m4_surface\m4_rotated_surface_code_circuit_level_d7_s3__d7__circuit_level__p0p005\model_state.pt`
- 测试集：1024 shots（seed [303]）
- 先验插值强度：1.0

## 1. 逐解码器

| decoder | logical errors | LER | s.e. | syndrome 一致率 |
|---|---:|---:|---:|---:|
| mwpm | 8 | 0.00781 | 0.00275 | 1.0000 |
| bp | 279 | 0.27246 | 0.01391 | 0.1152 |
| bp_osd_cs0 | 329 | 0.32129 | 0.01459 | 1.0000 |
| bp_osd_cs4 | 249 | 0.24316 | 0.01341 | 1.0000 |
| bp_gnn | 192 | 0.18750 | 0.01220 | 0.1787 |
| bp_gnn_osd_cs0 | 288 | 0.28125 | 0.01405 | 1.0000 |
| bp_gnn_osd_cs4 | 211 | 0.20605 | 0.01264 | 1.0000 |

## 2. 配对检验（McNemar，双侧）

| A | B | A 错 B 对 | A 对 B 错 | z | p (normal) | p (exact) |
|---|---|---:|---:|---:|---:|---:|
| bp | bp_osd_cs0 | 102 | 152 | -3.14 | 0.0017 | 0.0020 |
| bp_osd_cs0 | bp_osd_cs4 | 104 | 24 | 7.07 | 0.0000 | 0.0000 |
| bp | bp_osd_cs4 | 154 | 124 | 1.80 | 0.0720 | 0.0818 |
| bp_gnn | bp_gnn_osd_cs0 | 79 | 175 | -6.02 | 0.0000 | 0.0000 |
| bp_gnn_osd_cs0 | bp_gnn_osd_cs4 | 112 | 35 | 6.35 | 0.0000 | 0.0000 |
| bp_gnn | bp_gnn_osd_cs4 | 107 | 126 | -1.24 | 0.2132 | 0.2382 |
| bp_osd_cs0 | bp_gnn_osd_cs0 | 184 | 143 | 2.27 | 0.0234 | 0.0268 |
| bp_osd_cs4 | bp_gnn_osd_cs4 | 165 | 127 | 2.22 | 0.0262 | 0.0302 |

## 3. 未收敛子集（BP+GNN 未收敛的 shot）

- 未收敛 shot 数：841 / 1024

| decoder | 未收敛子集上的逻辑错误 |
|---|---:|
| mwpm | 8 |
| bp | 247 |
| bp_osd_cs0 | 294 |
| bp_osd_cs4 | 232 |
| bp_gnn | 192 |
| bp_gnn_osd_cs0 | 288 |
| bp_gnn_osd_cs4 | 211 |
