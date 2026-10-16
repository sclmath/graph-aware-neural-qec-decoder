# T8 · OSD 候选集学习（OSD-CS / combination sweep）

- 配置：`results\m4_surface\m4_rotated_surface_code_circuit_level_d7_s1__d7__circuit_level__p0p003\config.json`
- 检查点：`results\m4_surface\m4_rotated_surface_code_circuit_level_d7_s1__d7__circuit_level__p0p003\model_state.pt`
- 测试集：1024 shots（seed [301]）
- 先验插值强度：1.0

## 1. 逐解码器

| decoder | logical errors | LER | s.e. | syndrome 一致率 |
|---|---:|---:|---:|---:|
| mwpm | 3 | 0.00293 | 0.00169 | 1.0000 |
| bp | 156 | 0.15234 | 0.01123 | 0.3779 |
| bp_osd_cs0 | 182 | 0.17773 | 0.01195 | 1.0000 |
| bp_osd_cs4 | 129 | 0.12598 | 0.01037 | 1.0000 |
| bp_gnn | 84 | 0.08203 | 0.00858 | 0.6221 |
| bp_gnn_osd_cs0 | 98 | 0.09570 | 0.00919 | 1.0000 |
| bp_gnn_osd_cs4 | 52 | 0.05078 | 0.00686 | 1.0000 |

## 2. 配对检验（McNemar，双侧）

| A | B | A 错 B 对 | A 对 B 错 | z | p (normal) | p (exact) |
|---|---|---:|---:|---:|---:|---:|
| bp | bp_osd_cs0 | 64 | 90 | -2.10 | 0.0362 | 0.0436 |
| bp_osd_cs0 | bp_osd_cs4 | 74 | 21 | 5.44 | 0.0000 | 0.0000 |
| bp | bp_osd_cs4 | 96 | 69 | 2.10 | 0.0356 | 0.0426 |
| bp_gnn | bp_gnn_osd_cs0 | 51 | 65 | -1.30 | 0.1936 | 0.2273 |
| bp_gnn_osd_cs0 | bp_gnn_osd_cs4 | 56 | 10 | 5.66 | 0.0000 | 0.0000 |
| bp_gnn | bp_gnn_osd_cs4 | 67 | 35 | 3.17 | 0.0015 | 0.0020 |
| bp_osd_cs0 | bp_gnn_osd_cs0 | 141 | 57 | 5.97 | 0.0000 | 0.0000 |
| bp_osd_cs4 | bp_gnn_osd_cs4 | 109 | 32 | 6.48 | 0.0000 | 0.0000 |

## 3. 未收敛子集（BP+GNN 未收敛的 shot）

- 未收敛 shot 数：387 / 1024

| decoder | 未收敛子集上的逻辑错误 |
|---|---:|
| mwpm | 2 |
| bp | 103 |
| bp_osd_cs0 | 103 |
| bp_osd_cs4 | 80 |
| bp_gnn | 84 |
| bp_gnn_osd_cs0 | 98 |
| bp_gnn_osd_cs4 | 52 |
