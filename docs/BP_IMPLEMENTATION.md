# BP 实现规范与批量化

版本日期：2026-11-12
适用范围：`src/graph_qec/decoders/bp.py`、`src/graph_qec/decoders/bp_engine.py`，以及所有 BP 系解码器（`bp`、`bp_osd`、`bp_gnn`、`bp_gnn_osd`、`osd_bp`、`osd_gnn`）

## 1. 算法定义

对 DEM 的每一个 `error` instruction 定义一个变量（不拆 hyperedge），构成 `H @ e = syndrome` 的二元线性系统，在该 Tanner 图上跑归一化 min-sum BP：

| 组成 | 规范 |
|---|---|
| 先验 | `prior_llr = log((1-p)/p)`，`p` 取 DEM 概率或学习后验（可由调用方覆盖） |
| check 更新 | 符号为其余入边符号之积，幅度为**排除自身**后的最小幅度：`min1` 用于 argmin 位置，其余位置一律取 `min1`（度 1 的 check 使用 20.0 的幅度上限） |
| 归一化 | 每轮消息乘以 `min_sum_scaling`（默认 0.75） |
| damping | 可选，`damping` 默认 0.0 |
| 后验 | `posterior = 有效先验 + Σ 入边消息`，判决取 posterior 的符号 |
| 收敛 | 后验硬判决的 syndrome 与输入一致即收敛，提前退出 |
| 迭代上限 | 默认 32 |

两条容易被忽略但必须成立的语义：

1. **自排除**：度 2 的 check 上不得把变量自身幅度回传（否则形成自增强），度 ≥3 时必须是严格的「除自身外的最小值」；
2. **先验进入后验**：`prior_llr` 覆盖必须同时作用于第一轮消息与最终判决所用的后验。这两条语义由 `tests/test_batched_bp.py` 直接固定。

## 2. 批量化设计（`bp_engine.py`）

标量实现按 shot 在 Python 里遍历 Tanner 图，成本约 10-20 ms/shot，无法支撑多噪声率 × 多码距的扫描。`BatchedMinSumBP` 用 NumPy 段操作对 shot 维做向量化：

- 边按 check 分组（行主序天然连续）与按 variable 分组（`argsort` 排列）各存一份，variable 侧用 `reduceat` 求和，check 侧用带 padding 的 `(shots, checks, max_degree)` 张量做 min1/min2 自排除；
- 每轮迭代后把已收敛的 shot 从活动集合中压缩掉（gather/scatter），因此容易收敛的 shot 只跑一两轮；
- 自适应 shot 切块（默认 4M 元素预算）限制内存峰值：repetition d=3 一次吃完 32768 shot，表面码按几千 shot 分块。

## 3. 正确性保障

| 测试 | 断言 |
|---|---|
| `test_batched_bp.py`（引擎 vs 标量参考实现） | corrections / iterations / converged / syndrome_distance **逐 shot 完全一致**，后验 LLR 差异 ≤ 1e-12（高 check 度时为浮点求和顺序差异，量级 1e-15） |
| 同一文件 | min-sum 自排除语义（度 3 check 上最大幅度不得回传给自身）与度 1 check 的幅度上限 |
| `test_batched_bp.py::test_batched_osd_fallback_restores_syndrome_consistency` | OSD 回退给出满足 syndrome 的 correction |

## 4. 性能

工程侧（repetition d=3 circuit-level，32768 shots）：

| 场景 | 标量实现 | 向量化实现 | 加速 |
|---|---:|---:|---:|
| repetition d=3 circuit-level | 205 µs/shot | **1.9 µs/shot** | ~107× |
| repetition d=5 circuit-level | ~11 ms/shot | ~0.5 ms/shot | ~20× |
| surface d=3 circuit-level（564 edges） | 18.5 ms/shot | **0.54 ms/shot** | ~34× |
| surface d=3 code-capacity（98 edges） | ~3 ms/shot | 4.4 µs/shot | ~600× |

表面码线路级随码距的实测标度与收敛率（circuit-level p=0.005，`max_iterations=32`）：

| d | detectors | mechanisms | edges | max check deg | µs/shot | 收敛率 | 平均迭代 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 3 | 24 | 286 | 744 | 63 | 242 | 0.888 | 4.49 |
| 5 | 120 | 1953 | 5814 | 82 | 8,100 | 0.535 | 16.80 |
| 7 | 336 | 6602 | 20196 | 91 | 46,854 | 0.109 | 29.14 |
| 9 | 720 | 14,966 | 46,960 | 91 | 127,877 | 0.000 | 32.00 |

代价随 check 度增长而非线性，主要来源是收敛率下降（未收敛 shot 需要跑满迭代上限）。该表由 `scripts/probe_cpu_budget.py` 生成，是噪声率与码距扫描的预算依据；平台与规模建议见 [`ROADMAP.md`](ROADMAP.md)。

## 5. 结果落点

| 目录 | 内容 |
|---|---|
| `results/m1/` | 经典基线（BP 系解码器） |
| `results/m2/` | GNN 重加权的同分布评测 |
| `results/m3/` | 混合解码器 headline、噪声外推、跨码距迁移、强度重标定、失效归因 |
| `results/m4/`、`results/m4_surface/`、`results/m4_surface_cc/`、`results/m4_hgp/` | 旋转表面码与 HGP 的图结构对比与重加权评测 |
| `results/m5/` | 量化、MWPM 边权重、CPU 预算实测 |
