# GNN 前向性能

- **版本日期**：2026-11-12
- **代码**：`src/graph_qec/models/bipartite_gnn.py`
- **测试**：`tests/test_gnn_forward_equivalence.py`
- **复现**：`.\.venv\Scripts\python.exe scripts\probe_cpu_budget.py --distances 3 --gnn-distances 5 7 --json results\m5\cpu_budget.json`

## 1. 当前性能

CPU 实测，单一进程固定线程数：

| d | edges | batch | 前向 µs/shot | 峰值 RSS | 训练单步 |
|---:|---:|---:|---:|---:|---:|
| 5 | 5,814 | 128 | 7,767 | 1,152 MB | - |
| 5 | 5,814 | 512 | 8,901 | 2,763 MB | 2.47 s |
| 7 | 20,196 | 64 | 27,668 | 1,426 MB | - |
| 7 | 20,196 | 256 | 35,256 | 4,494 MB | 4.29 s |

repetition d=3（34 edges，M2/M3 管线，batch 1024）：32.4 µs/shot。

## 2. 当前实现要点

1. 消息 MLP 的第一层按 `variable / check / edge` 三个特征块分别做线性投影，避免构造拼接后的中间张量。
2. 边特征投影与 shot 无关，按层预计算一次。
3. 两个方向的节点 gather 与聚合缓冲在推理阶段复用。
4. `__init__` 与 `state_dict` 保持稳定，已有 checkpoint 可直接加载。

## 3. 数值等价性

与测试中的参考前向函数逐 shot 比较：

| d | edges | batch | max &#124;Δ logits&#124; |
|---:|---:|---:|---:|
| 5 | 5,814 | 64 | 2.4e-07 |
| 5 | 5,814 | 256 | 2.4e-07 |
| 7 | 20,196 | 64 | 2.4e-07 |
| 7 | 20,196 | 256 | 3.0e-07 |

差异来自 float32 点积求和顺序，属于舍入噪声。

## 4. 当前瓶颈

- d=7 前向仍为数十毫秒/shot，未达到 10 ms/shot 目标。
- 主要成本来自逐边 gather 与 `index_add_` 的内存流量；`(shots, edges, hidden)` 激活在 d=7/batch 256 下单层约 1.3 GB。
- 小 batch 下中间张量同时驻留，峰值 RSS 较高。

后续需要按边分块、稀疏矩阵乘或更紧凑的消息 MLP 结构降低内存与延迟；方向见 [`docs/ROADMAP.md`](../../docs/ROADMAP.md)。
