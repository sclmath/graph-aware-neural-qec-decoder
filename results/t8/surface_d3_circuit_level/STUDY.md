# T8 · OSD 候选集学习（OSD-CS / combination sweep）

- 配置：`results\m4_surface\m4_learned_basis_rotated_surface_code_circuit_level_d3__d3__circuit_level__p0p005\config.json`
- 检查点：`results\m4_surface\m4_learned_basis_rotated_surface_code_circuit_level_d3__d3__circuit_level__p0p005\model_state.pt`
- 测试集：32768 shots（seed [301, 302, 303, 304]）
- 先验插值强度：1.0

## 1. 逐解码器

| decoder | logical errors | LER | s.e. | syndrome 一致率 |
|---|---:|---:|---:|---:|
| mwpm | 555 | 0.01694 | 0.00071 | 1.0000 |
| bp | 1313 | 0.04007 | 0.00108 | 0.9026 |
| bp_osd_cs0 | 1414 | 0.04315 | 0.00112 | 1.0000 |
| bp_osd_cs2 | 1044 | 0.03186 | 0.00097 | 1.0000 |
| bp_osd_cs4 | 904 | 0.02759 | 0.00090 | 1.0000 |
| bp_osd_cs6 | 834 | 0.02545 | 0.00087 | 1.0000 |
| bp_osd_cs8 | 821 | 0.02505 | 0.00086 | 1.0000 |
| bp_gnn | 1132 | 0.03455 | 0.00101 | 0.9536 |
| bp_gnn_osd_cs0 | 1323 | 0.04037 | 0.00109 | 1.0000 |
| bp_gnn_osd_cs2 | 869 | 0.02652 | 0.00089 | 1.0000 |
| bp_gnn_osd_cs4 | 689 | 0.02103 | 0.00079 | 1.0000 |
| bp_gnn_osd_cs6 | 641 | 0.01956 | 0.00077 | 1.0000 |
| bp_gnn_osd_cs8 | 627 | 0.01913 | 0.00076 | 1.0000 |

## 2. 配对检验（McNemar，双侧）

| A | B | A 错 B 对 | A 对 B 错 | z | p (normal) | p (exact) |
|---|---|---:|---:|---:|---:|---:|
| bp | bp_osd_cs0 | 451 | 552 | -3.19 | 0.0014 | 0.0016 |
| bp_osd_cs0 | bp_osd_cs2 | 549 | 179 | 13.71 | 0.0000 | 0.0000 |
| bp_osd_cs0 | bp_osd_cs4 | 760 | 250 | 16.05 | 0.0000 | 0.0000 |
| bp_osd_cs0 | bp_osd_cs6 | 819 | 239 | 17.83 | 0.0000 | 0.0000 |
| bp_osd_cs0 | bp_osd_cs8 | 835 | 242 | 18.07 | 0.0000 | 0.0000 |
| bp | bp_osd_cs2 | 619 | 350 | 8.64 | 0.0000 | 0.0000 |
| bp | bp_osd_cs4 | 709 | 300 | 12.88 | 0.0000 | 0.0000 |
| bp | bp_osd_cs6 | 701 | 222 | 15.77 | 0.0000 | 0.0000 |
| bp | bp_osd_cs8 | 709 | 217 | 16.17 | 0.0000 | 0.0000 |
| bp_gnn | bp_gnn_osd_cs0 | 266 | 457 | -7.10 | 0.0000 | 0.0000 |
| bp_gnn_osd_cs0 | bp_gnn_osd_cs2 | 565 | 111 | 17.46 | 0.0000 | 0.0000 |
| bp_gnn_osd_cs0 | bp_gnn_osd_cs4 | 763 | 129 | 21.23 | 0.0000 | 0.0000 |
| bp_gnn_osd_cs0 | bp_gnn_osd_cs6 | 812 | 130 | 22.22 | 0.0000 | 0.0000 |
| bp_gnn_osd_cs0 | bp_gnn_osd_cs8 | 836 | 140 | 22.28 | 0.0000 | 0.0000 |
| bp_gnn | bp_gnn_osd_cs2 | 506 | 243 | 9.61 | 0.0000 | 0.0000 |
| bp_gnn | bp_gnn_osd_cs4 | 542 | 99 | 17.50 | 0.0000 | 0.0000 |
| bp_gnn | bp_gnn_osd_cs6 | 553 | 62 | 19.80 | 0.0000 | 0.0000 |
| bp_gnn | bp_gnn_osd_cs8 | 558 | 53 | 20.43 | 0.0000 | 0.0000 |
| bp_osd_cs0 | bp_gnn_osd_cs0 | 794 | 703 | 2.35 | 0.0187 | 0.0200 |
| bp_osd_cs2 | bp_gnn_osd_cs2 | 584 | 409 | 5.55 | 0.0000 | 0.0000 |
| bp_osd_cs4 | bp_gnn_osd_cs4 | 475 | 260 | 7.93 | 0.0000 | 0.0000 |
| bp_osd_cs6 | bp_gnn_osd_cs6 | 406 | 213 | 7.76 | 0.0000 | 0.0000 |
| bp_osd_cs8 | bp_gnn_osd_cs8 | 386 | 192 | 8.07 | 0.0000 | 0.0000 |

## 3. 未收敛子集（BP+GNN 未收敛的 shot）

- 未收敛 shot 数：1521 / 32768

| decoder | 未收敛子集上的逻辑错误 |
|---|---:|
| mwpm | 209 |
| bp | 606 |
| bp_osd_cs0 | 576 |
| bp_osd_cs2 | 341 |
| bp_osd_cs4 | 251 |
| bp_osd_cs6 | 257 |
| bp_osd_cs8 | 252 |
| bp_gnn | 764 |
| bp_gnn_osd_cs0 | 955 |
| bp_gnn_osd_cs2 | 501 |
| bp_gnn_osd_cs4 | 321 |
| bp_gnn_osd_cs6 | 273 |
| bp_gnn_osd_cs8 | 259 |
