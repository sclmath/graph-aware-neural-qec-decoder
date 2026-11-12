# 图特征组合消融

- 配置：`configs\m2_learned_basis_repetition_circuit_level_d3.json`；测试集 32768 shots
- 做法：把对应特征列**置零**后用同一 seed 重训，架构不变，因此比较的是该组特征携带的**信息量**

| 消融臂 | 机制 AUC | bp_gnn LER | 逻辑错误 | Δ LER（相对 all） |
|---|---:|---:|---:|---:|
| no_check_features | 0.9834 | 0.00977 | 320 | +0.00043 |
| no_variable_geometry | 0.9827 | 0.01254 | 411 | +0.00320 |
| no_check_geometry | 0.9807 | 0.01004 | 329 | +0.00070 |
| no_edge_degree | 0.9831 | 0.00931 | 305 | -0.00003 |
| prior_only | 0.9801 | 0.02231 | 731 | +0.01297 |
| all | 0.9836 | 0.00934 | 306 | +0.00000 |
