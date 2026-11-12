# OSD 候选集学习（OSD-CS）

- 配置：`results\m4_surface\m4_rotated_surface_code_circuit_level_d7_s1__d7__circuit_level__p0p003\config.json`
- 检查点：`results\m4_surface\m4_rotated_surface_code_circuit_level_d7_s1__d7__circuit_level__p0p003\model_state.pt`
- 测试集：1024 shots（seed [311]）
- 先验插值强度：1.0

## 1. 逐解码器

| decoder | logical errors | LER | s.e. | syndrome 一致率 |
|---|---:|---:|---:|---:|
| mwpm | 1 | 0.00098 | 0.00098 | 1.0000 |
| bp | 169 | 0.16504 | 0.01160 | 0.3525 |
| bp_osd_cs0 | 191 | 0.18652 | 0.01217 | 1.0000 |
| bp_osd_cs4 | 119 | 0.11621 | 0.01001 | 1.0000 |
| bp_gnn | 86 | 0.08398 | 0.00867 | 0.5879 |
| bp_gnn_osd_cs0 | 104 | 0.10156 | 0.00944 | 1.0000 |
| bp_gnn_osd_cs4 | 53 | 0.05176 | 0.00692 | 1.0000 |

## 2. 配对检验（McNemar，双侧）

| A | B | A 错 B 对 | A 对 B 错 | z | p (normal) | p (exact) |
|---|---|---:|---:|---:|---:|---:|
| bp | bp_osd_cs0 | 46 | 68 | -2.06 | 0.0394 | 0.0487 |
| bp_osd_cs0 | bp_osd_cs4 | 89 | 17 | 6.99 | 0.0000 | 0.0000 |
| bp | bp_osd_cs4 | 102 | 52 | 4.03 | 0.0001 | 0.0001 |
| bp_gnn | bp_gnn_osd_cs0 | 51 | 69 | -1.64 | 0.1003 | 0.1203 |
| bp_gnn_osd_cs0 | bp_gnn_osd_cs4 | 58 | 7 | 6.33 | 0.0000 | 0.0000 |
| bp_gnn | bp_gnn_osd_cs4 | 65 | 32 | 3.35 | 0.0008 | 0.0010 |
| bp_osd_cs0 | bp_gnn_osd_cs0 | 140 | 53 | 6.26 | 0.0000 | 0.0000 |
| bp_osd_cs4 | bp_gnn_osd_cs4 | 102 | 36 | 5.62 | 0.0000 | 0.0000 |

## 3. 未收敛子集（BP+GNN 未收敛的 shot）

- 未收敛 shot 数：422 / 1024

| decoder | 未收敛子集上的逻辑错误 |
|---|---:|
| mwpm | 1 |
| bp | 104 |
| bp_osd_cs0 | 122 |
| bp_osd_cs4 | 77 |
| bp_gnn | 86 |
| bp_gnn_osd_cs0 | 104 |
| bp_gnn_osd_cs4 | 53 |
