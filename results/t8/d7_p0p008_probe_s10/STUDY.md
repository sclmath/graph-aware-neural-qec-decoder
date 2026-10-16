# T8 · OSD 候选集学习（OSD-CS / combination sweep）

- 配置：`results\m4_surface\m4_rotated_surface_code_circuit_level_d7_s1__d7__circuit_level__p0p008\config.json`
- 检查点：`results\m4_surface\m4_rotated_surface_code_circuit_level_d7_s1__d7__circuit_level__p0p008\model_state.pt`
- 测试集：1024 shots（seed [311]）
- 先验插值强度：1.0

## 1. 逐解码器

| decoder | logical errors | LER | s.e. | syndrome 一致率 |
|---|---:|---:|---:|---:|
| mwpm | 56 | 0.05469 | 0.00711 | 1.0000 |
| bp | 349 | 0.34082 | 0.01481 | 0.0137 |
| bp_osd_cs0 | 412 | 0.40234 | 0.01532 | 1.0000 |
| bp_osd_cs4 | 374 | 0.36523 | 0.01505 | 1.0000 |
| bp_gnn | 308 | 0.30078 | 0.01433 | 0.0537 |
| bp_gnn_osd_cs0 | 365 | 0.35645 | 0.01497 | 1.0000 |
| bp_gnn_osd_cs4 | 310 | 0.30273 | 0.01436 | 1.0000 |

## 2. 配对检验（McNemar，双侧）

| A | B | A 错 B 对 | A 对 B 错 | z | p (normal) | p (exact) |
|---|---|---:|---:|---:|---:|---:|
| bp | bp_osd_cs0 | 132 | 195 | -3.48 | 0.0005 | 0.0006 |
| bp_osd_cs0 | bp_osd_cs4 | 107 | 69 | 2.86 | 0.0042 | 0.0051 |
| bp | bp_osd_cs4 | 156 | 181 | -1.36 | 0.1732 | 0.1910 |
| bp_gnn | bp_gnn_osd_cs0 | 116 | 173 | -3.35 | 0.0008 | 0.0010 |
| bp_gnn_osd_cs0 | bp_gnn_osd_cs4 | 109 | 54 | 4.31 | 0.0000 | 0.0000 |
| bp_gnn | bp_gnn_osd_cs4 | 146 | 148 | -0.12 | 0.9071 | 0.9535 |
| bp_osd_cs0 | bp_gnn_osd_cs0 | 220 | 173 | 2.37 | 0.0177 | 0.0202 |
| bp_osd_cs4 | bp_gnn_osd_cs4 | 215 | 151 | 3.35 | 0.0008 | 0.0010 |

## 3. 未收敛子集（BP+GNN 未收敛的 shot）

- 未收敛 shot 数：969 / 1024

| decoder | 未收敛子集上的逻辑错误 |
|---|---:|
| mwpm | 56 |
| bp | 338 |
| bp_osd_cs0 | 398 |
| bp_osd_cs4 | 365 |
| bp_gnn | 308 |
| bp_gnn_osd_cs0 | 365 |
| bp_gnn_osd_cs4 | 310 |
