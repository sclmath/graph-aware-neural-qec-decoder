# T9 · 图特征组合消融

- 配置：`results\m4_surface\m4_learned_basis_rotated_surface_code_circuit_level_d3__d3__circuit_level__p0p005\config.json`；测试集 32768 shots
- 做法：把对应特征列**置零**后用同一 seed 重训，架构不变，因此比较的是该组特征携带的**信息量**

| 消融臂 | 机制 AUC | bp_gnn LER | 逻辑错误 | Δ LER（相对 all） |
|---|---:|---:|---:|---:|
| all | 0.9924 | 0.03864 | 1266 | +0.00000 |
| no_variable_geometry | 0.9917 | 0.03952 | 1295 | +0.00089 |
| no_check_features | 0.9922 | 0.04041 | 1324 | +0.00177 |
| no_check_geometry | 0.9928 | 0.02780 | 911 | -0.01083 |
| no_edge_degree | 0.9922 | 0.03937 | 1290 | +0.00073 |
| prior_only | 0.9920 | 0.06891 | 2258 | +0.03027 |
