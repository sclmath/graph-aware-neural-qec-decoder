# T8 · OSD 候选集学习（OSD-CS / combination sweep）

- 配置：`results\m4_surface\m4_rotated_surface_code_circuit_level_d7_s3__d7__circuit_level__p0p008\config.json`
- 检查点：`results\m4_surface\m4_rotated_surface_code_circuit_level_d7_s3__d7__circuit_level__p0p008\model_state.pt`
- 测试集：1024 shots（seed [303]）
- 先验插值强度：1.0

## 1. 逐解码器

| decoder | logical errors | LER | s.e. | syndrome 一致率 |
|---|---:|---:|---:|---:|
| mwpm | 44 | 0.04297 | 0.00634 | 1.0000 |
| bp | 377 | 0.36816 | 0.01507 | 0.0244 |
| bp_osd_cs0 | 436 | 0.42578 | 0.01545 | 1.0000 |
| bp_osd_cs4 | 372 | 0.36328 | 0.01503 | 1.0000 |
| bp_gnn | 305 | 0.29785 | 0.01429 | 0.0566 |
| bp_gnn_osd_cs0 | 368 | 0.35938 | 0.01499 | 1.0000 |
| bp_gnn_osd_cs4 | 304 | 0.29688 | 0.01428 | 1.0000 |

## 2. 配对检验（McNemar，双侧）

| A | B | A 错 B 对 | A 对 B 错 | z | p (normal) | p (exact) |
|---|---|---:|---:|---:|---:|---:|
| bp | bp_osd_cs0 | 131 | 190 | -3.29 | 0.0010 | 0.0012 |
| bp_osd_cs0 | bp_osd_cs4 | 108 | 44 | 5.19 | 0.0000 | 0.0000 |
| bp | bp_osd_cs4 | 169 | 164 | 0.27 | 0.7841 | 0.8265 |
| bp_gnn | bp_gnn_osd_cs0 | 131 | 194 | -3.49 | 0.0005 | 0.0006 |
| bp_gnn_osd_cs0 | bp_gnn_osd_cs4 | 132 | 68 | 4.53 | 0.0000 | 0.0000 |
| bp_gnn | bp_gnn_osd_cs4 | 158 | 157 | 0.06 | 0.9551 | 1.0000 |
| bp_osd_cs0 | bp_gnn_osd_cs0 | 239 | 171 | 3.36 | 0.0008 | 0.0009 |
| bp_osd_cs4 | bp_gnn_osd_cs4 | 221 | 153 | 3.52 | 0.0004 | 0.0005 |

## 3. 未收敛子集（BP+GNN 未收敛的 shot）

- 未收敛 shot 数：966 / 1024

| decoder | 未收敛子集上的逻辑错误 |
|---|---:|
| mwpm | 43 |
| bp | 366 |
| bp_osd_cs0 | 423 |
| bp_osd_cs4 | 364 |
| bp_gnn | 304 |
| bp_gnn_osd_cs0 | 367 |
| bp_gnn_osd_cs4 | 303 |
