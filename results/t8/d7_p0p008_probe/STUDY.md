# OSD 候选集学习（OSD-CS）

- 配置：`results\m4_surface\m4_rotated_surface_code_circuit_level_d7_s1__d7__circuit_level__p0p008\config.json`
- 检查点：`results\m4_surface\m4_rotated_surface_code_circuit_level_d7_s1__d7__circuit_level__p0p008\model_state.pt`
- 测试集：1024 shots（seed [301]）
- 先验插值强度：1.0

## 1. 逐解码器

| decoder | logical errors | LER | s.e. | syndrome 一致率 |
|---|---:|---:|---:|---:|
| mwpm | 50 | 0.04883 | 0.00673 | 1.0000 |
| bp | 363 | 0.35449 | 0.01495 | 0.0254 |
| bp_osd_cs0 | 427 | 0.41699 | 0.01541 | 1.0000 |
| bp_osd_cs4 | 389 | 0.37988 | 0.01517 | 1.0000 |
| bp_gnn | 311 | 0.30371 | 0.01437 | 0.0703 |
| bp_gnn_osd_cs0 | 351 | 0.34277 | 0.01483 | 1.0000 |
| bp_gnn_osd_cs4 | 295 | 0.28809 | 0.01415 | 1.0000 |

## 2. 配对检验（McNemar，双侧）

| A | B | A 错 B 对 | A 对 B 错 | z | p (normal) | p (exact) |
|---|---|---:|---:|---:|---:|---:|
| bp | bp_osd_cs0 | 118 | 182 | -3.70 | 0.0002 | 0.0003 |
| bp_osd_cs0 | bp_osd_cs4 | 99 | 61 | 3.00 | 0.0027 | 0.0033 |
| bp | bp_osd_cs4 | 155 | 181 | -1.42 | 0.1561 | 0.1725 |
| bp_gnn | bp_gnn_osd_cs0 | 108 | 148 | -2.50 | 0.0124 | 0.0146 |
| bp_gnn_osd_cs0 | bp_gnn_osd_cs4 | 104 | 48 | 4.54 | 0.0000 | 0.0000 |
| bp_gnn | bp_gnn_osd_cs4 | 143 | 127 | 0.97 | 0.3302 | 0.3613 |
| bp_osd_cs0 | bp_gnn_osd_cs0 | 223 | 147 | 3.95 | 0.0001 | 0.0001 |
| bp_osd_cs4 | bp_gnn_osd_cs4 | 232 | 138 | 4.89 | 0.0000 | 0.0000 |

## 3. 未收敛子集（BP+GNN 未收敛的 shot）

- 未收敛 shot 数：952 / 1024

| decoder | 未收敛子集上的逻辑错误 |
|---|---:|
| mwpm | 50 |
| bp | 356 |
| bp_osd_cs0 | 417 |
| bp_osd_cs4 | 381 |
| bp_gnn | 311 |
| bp_gnn_osd_cs0 | 351 |
| bp_gnn_osd_cs4 | 295 |
