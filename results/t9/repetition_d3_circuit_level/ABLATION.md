# 图特征组合消融

- 配置：`configs\m2_learned_basis_repetition_circuit_level_d3.json`；测试集 32768 shots
- 做法：把对应特征列**置零**后用同一 seed 重训，架构不变，因此比较的是该组特征携带的**信息量**

| 消融臂 | 机制 AUC | bp_gnn LER | 逻辑错误 | Δ LER（相对 all） |
|---|---:|---:|---:|---:|
| all | 0.9905 | 0.00952 | 312 | +0.00000 |
| no_check_features | 0.9924 | 0.00943 | 309 | -0.00009 |
| no_variable_geometry | 0.9894 | 0.00964 | 316 | +0.00012 |
| no_check_geometry | 0.9924 | 0.00955 | 313 | +0.00003 |
| no_edge_degree | 0.9880 | 0.00943 | 309 | -0.00009 |
| prior_only | 0.9857 | 0.02371 | 777 | +0.01419 |
