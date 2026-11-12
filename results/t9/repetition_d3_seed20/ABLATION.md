# 图特征组合消融

- 配置：`configs\m2_learned_basis_repetition_circuit_level_d3.json`；seed offset 20；测试集 32768 shots
- 做法：把对应特征列**置零**后用同一 seed 重训，架构不变，因此比较的是该组特征携带的**信息量**

| 消融臂 | 机制 AUC | bp_gnn LER | 逻辑错误 | Δ LER（相对 all） |
|---|---:|---:|---:|---:|
| all | 0.9856 | 0.01099 | 360 | +0.00000 |
| no_check_features | 0.9850 | 0.01105 | 362 | +0.00006 |
| no_variable_geometry | 0.9856 | 0.01105 | 362 | +0.00006 |
| no_check_geometry | 0.9850 | 0.01105 | 362 | +0.00006 |
| no_edge_degree | 0.9841 | 0.01047 | 343 | -0.00052 |
| prior_only | 0.9840 | 0.02371 | 777 | +0.01272 |
