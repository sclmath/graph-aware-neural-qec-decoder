# OSD 候选集学习（OSD-CS）

- 配置：`configs\m3_learned_basis_repetition_circuit_level_d3.json`
- 检查点：`results\m3\m3_learned_basis_repetition_circuit_level_d3__d3__circuit_level__p0p01\model_state.pt`
- 测试集：32768 shots（seed [301, 302]）
- 先验插值强度：1.0

## 1. 逐解码器

| decoder | logical errors | LER | s.e. | syndrome 一致率 |
|---|---:|---:|---:|---:|
| mwpm | 217 | 0.00662 | 0.00045 | 1.0000 |
| bp | 309 | 0.00943 | 0.00053 | 0.9899 |
| bp_osd_cs0 | 331 | 0.01010 | 0.00055 | 1.0000 |
| bp_osd_cs2 | 285 | 0.00870 | 0.00051 | 1.0000 |
| bp_osd_cs4 | 247 | 0.00754 | 0.00048 | 1.0000 |
| bp_osd_cs6 | 281 | 0.00858 | 0.00051 | 1.0000 |
| bp_osd_cs8 | 280 | 0.00854 | 0.00051 | 1.0000 |
| bp_gnn | 312 | 0.00952 | 0.00054 | 0.9912 |
| bp_gnn_osd_cs0 | 333 | 0.01016 | 0.00055 | 1.0000 |
| bp_gnn_osd_cs2 | 270 | 0.00824 | 0.00050 | 1.0000 |
| bp_gnn_osd_cs4 | 249 | 0.00760 | 0.00048 | 1.0000 |
| bp_gnn_osd_cs6 | 278 | 0.00848 | 0.00051 | 1.0000 |
| bp_gnn_osd_cs8 | 280 | 0.00854 | 0.00051 | 1.0000 |

## 2. 配对检验（McNemar，双侧）

| A | B | A 错 B 对 | A 对 B 错 | z | p (normal) | p (exact) |
|---|---|---:|---:|---:|---:|---:|
| bp | bp_osd_cs0 | 70 | 92 | -1.73 | 0.0839 | 0.0987 |
| bp_osd_cs0 | bp_osd_cs2 | 97 | 51 | 3.78 | 0.0002 | 0.0002 |
| bp_osd_cs0 | bp_osd_cs4 | 126 | 42 | 6.48 | 0.0000 | 0.0000 |
| bp_osd_cs0 | bp_osd_cs6 | 163 | 113 | 3.01 | 0.0026 | 0.0031 |
| bp_osd_cs0 | bp_osd_cs8 | 162 | 111 | 3.09 | 0.0020 | 0.0024 |
| bp | bp_osd_cs2 | 74 | 50 | 2.16 | 0.0311 | 0.0384 |
| bp | bp_osd_cs4 | 107 | 45 | 5.03 | 0.0000 | 0.0000 |
| bp | bp_osd_cs6 | 103 | 75 | 2.10 | 0.0358 | 0.0427 |
| bp | bp_osd_cs8 | 105 | 76 | 2.16 | 0.0311 | 0.0371 |
| bp_gnn | bp_gnn_osd_cs0 | 67 | 88 | -1.69 | 0.0916 | 0.1079 |
| bp_gnn_osd_cs0 | bp_gnn_osd_cs2 | 106 | 43 | 5.16 | 0.0000 | 0.0000 |
| bp_gnn_osd_cs0 | bp_gnn_osd_cs4 | 125 | 41 | 6.52 | 0.0000 | 0.0000 |
| bp_gnn_osd_cs0 | bp_gnn_osd_cs6 | 121 | 66 | 4.02 | 0.0001 | 0.0001 |
| bp_gnn_osd_cs0 | bp_gnn_osd_cs8 | 116 | 63 | 3.96 | 0.0001 | 0.0001 |
| bp_gnn | bp_gnn_osd_cs2 | 107 | 65 | 3.20 | 0.0014 | 0.0017 |
| bp_gnn | bp_gnn_osd_cs4 | 105 | 42 | 5.20 | 0.0000 | 0.0000 |
| bp_gnn | bp_gnn_osd_cs6 | 92 | 58 | 2.78 | 0.0055 | 0.0069 |
| bp_gnn | bp_gnn_osd_cs8 | 91 | 59 | 2.61 | 0.0090 | 0.0111 |
| bp_osd_cs0 | bp_gnn_osd_cs0 | 16 | 18 | -0.34 | 0.7316 | 0.8642 |
| bp_osd_cs2 | bp_gnn_osd_cs2 | 48 | 33 | 1.67 | 0.0956 | 0.1193 |
| bp_osd_cs4 | bp_gnn_osd_cs4 | 4 | 6 | -0.63 | 0.5271 | 0.7539 |
| bp_osd_cs6 | bp_gnn_osd_cs6 | 81 | 78 | 0.24 | 0.8119 | 0.8740 |
| bp_osd_cs8 | bp_gnn_osd_cs8 | 81 | 81 | 0.00 | 1.0000 | 1.0000 |

## 3. 未收敛子集（BP+GNN 未收敛的 shot）

- 未收敛 shot 数：288 / 32768

| decoder | 未收敛子集上的逻辑错误 |
|---|---:|
| mwpm | 83 |
| bp | 147 |
| bp_osd_cs0 | 172 |
| bp_osd_cs2 | 123 |
| bp_osd_cs4 | 88 |
| bp_osd_cs6 | 103 |
| bp_osd_cs8 | 102 |
| bp_gnn | 154 |
| bp_gnn_osd_cs0 | 175 |
| bp_gnn_osd_cs2 | 112 |
| bp_gnn_osd_cs4 | 91 |
| bp_gnn_osd_cs6 | 120 |
| bp_gnn_osd_cs8 | 122 |
