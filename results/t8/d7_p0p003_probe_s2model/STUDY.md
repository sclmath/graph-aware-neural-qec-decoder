# OSD 候选集学习（OSD-CS）

- 配置：`results\m4_surface\m4_rotated_surface_code_circuit_level_d7_s2__d7__circuit_level__p0p003\config.json`
- 检查点：`results\m4_surface\m4_rotated_surface_code_circuit_level_d7_s2__d7__circuit_level__p0p003\model_state.pt`
- 测试集：1024 shots（seed [302]）
- 先验插值强度：1.0

## 1. 逐解码器

| decoder | logical errors | LER | s.e. | syndrome 一致率 |
|---|---:|---:|---:|---:|
| mwpm | 1 | 0.00098 | 0.00098 | 1.0000 |
| bp | 157 | 0.15332 | 0.01126 | 0.3232 |
| bp_osd_cs0 | 222 | 0.21680 | 0.01288 | 1.0000 |
| bp_osd_cs4 | 131 | 0.12793 | 0.01044 | 1.0000 |
| bp_gnn | 101 | 0.09863 | 0.00932 | 0.4434 |
| bp_gnn_osd_cs0 | 166 | 0.16211 | 0.01152 | 1.0000 |
| bp_gnn_osd_cs4 | 109 | 0.10645 | 0.00964 | 1.0000 |

## 2. 配对检验（McNemar，双侧）

| A | B | A 错 B 对 | A 对 B 错 | z | p (normal) | p (exact) |
|---|---|---:|---:|---:|---:|---:|
| bp | bp_osd_cs0 | 55 | 120 | -4.91 | 0.0000 | 0.0000 |
| bp_osd_cs0 | bp_osd_cs4 | 101 | 10 | 8.64 | 0.0000 | 0.0000 |
| bp | bp_osd_cs4 | 98 | 72 | 1.99 | 0.0461 | 0.0549 |
| bp_gnn | bp_gnn_osd_cs0 | 53 | 118 | -4.97 | 0.0000 | 0.0000 |
| bp_gnn_osd_cs0 | bp_gnn_osd_cs4 | 86 | 29 | 5.32 | 0.0000 | 0.0000 |
| bp_gnn | bp_gnn_osd_cs4 | 72 | 80 | -0.65 | 0.5164 | 0.5703 |
| bp_osd_cs0 | bp_gnn_osd_cs0 | 145 | 89 | 3.66 | 0.0003 | 0.0003 |
| bp_osd_cs4 | bp_gnn_osd_cs4 | 91 | 69 | 1.74 | 0.0820 | 0.0966 |

## 3. 未收敛子集（BP+GNN 未收敛的 shot）

- 未收敛 shot 数：570 / 1024

| decoder | 未收敛子集上的逻辑错误 |
|---|---:|
| mwpm | 1 |
| bp | 105 |
| bp_osd_cs0 | 154 |
| bp_osd_cs4 | 103 |
| bp_gnn | 101 |
| bp_gnn_osd_cs0 | 166 |
| bp_gnn_osd_cs4 | 109 |
