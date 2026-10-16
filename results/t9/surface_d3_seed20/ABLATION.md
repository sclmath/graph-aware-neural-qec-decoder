# T9 · 图特征组合消融

- 配置：`results\m4_surface\m4_learned_basis_rotated_surface_code_circuit_level_d3__d3__circuit_level__p0p005\config.json`；测试集 32768 shots
- 做法：把对应特征列**置零**后用同一 seed 重训，架构不变，因此比较的是该组特征携带的**信息量**

| 消融臂 | 机制 AUC | bp_gnn LER | 逻辑错误 | Δ LER（相对 all） |
|---|---:|---:|---:|---:|
| all | 0.9927 | 0.02826 | 926 | +0.00000 |
| no_variable_geometry | 0.9915 | 0.03235 | 1060 | +0.00409 |
