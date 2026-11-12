# 图特征组合消融

- 配置：`results\m4_surface\m4_learned_basis_rotated_surface_code_circuit_level_d3__d3__circuit_level__p0p005\config.json`；测试集 32768 shots
- 做法：把对应特征列**置零**后用同一 seed 重训，架构不变，因此比较的是该组特征携带的**信息量**

| 消融臂 | 机制 AUC | bp_gnn LER | 逻辑错误 | Δ LER（相对 all） |
|---|---:|---:|---:|---:|
| all | 0.9931 | 0.03455 | 1132 | +0.00000 |
| no_check_features | 0.9932 | 0.02972 | 974 | -0.00482 |
| no_variable_geometry | 0.9933 | 0.02615 | 857 | -0.00839 |
| no_check_geometry | 0.9934 | 0.03174 | 1040 | -0.00281 |
| no_edge_degree | 0.9930 | 0.03439 | 1127 | -0.00015 |
| prior_only | 0.9921 | 0.06616 | 2168 | +0.03162 |
