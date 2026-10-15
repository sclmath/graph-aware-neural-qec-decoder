# GNN 前向优化（T5）

日期：2026-10-15
代码：`src/graph_qec/models/bipartite_gnn.py`
测试：`tests/test_gnn_forward_equivalence.py`（4 项）
复现：`.\.venv\Scripts\python.exe scripts\probe_cpu_budget.py --distances 3 --gnn-distances 5 7 --json results\m5\cpu_budget.json`

## 1. 优化前 profile（表面码 d=7，20196 edges，batch 128，`torch.profiler`）

| 算子 | 占比 | 调用数 |
|---|---:|---:|
| `aten::cat` | 31.1% | 13 |
| `aten::addmm` | 22.8% | 29 |
| `aten::index` | 12.9% | 12 |
| `aten::copy_` | 12.0% | 31 |
| `aten::index_add_` | 11.0% | 6 |
| `aten::clamp_min` | 6.6% | 14 |

代价分为三类：每个消息 MLP 前的三段 `cat`（把 `(shots, edges, 2h+E)` 拼出来）、逐 shot 的节点状态 gather、以及按边聚合的 `index_add_`。

## 2. 三项改动

1. **拆掉消息 MLP 的 `cat`**：第一层线性层按三个特征块拆开做，`[x_a | x_b | f_e] W^T` 改为 `x_a W_a^T + x_b W_b^T + f_e W_e^T`；
2. **把边特征项提出 batch 维**：`f_e W_e^T` 与 shot 无关，改为每层只算一次 `(E, h)`，不再对每个 shot 重复展开并相加；
3. **两个方向的 gather 复用**：`check_state[edge_checks]` 与 `variable_state[edge_variables]` 在两层消息之间不变，改为每层各算一次；同时为聚合结果按方向复用缓冲（仅在 `torch.no_grad()` 下复用，训练时仍分配新张量，否则会破坏反向传播）。

`__init__` 与 `state_dict` 结构完全不变，已有 checkpoint 可直接加载。

## 3. 数值等价性

与未优化实现（保留在 `tests/test_gnn_forward_equivalence.py::reference_forward`）逐 shot 比较：

| d | edges | batch | max &#124;Δ logits&#124; |
|---:|---:|---:|---:|
| 5 | 5,814 | 64 | 2.4e-07 |
| 5 | 5,814 | 256 | 2.4e-07 |
| 7 | 20,196 | 64 | 2.4e-07 |
| 7 | 20,196 | 256 | 3.0e-07 |

差异来自三个点积的求和顺序不同，量级为 float32 舍入噪声。交付结果的复核：用优化后的模型重跑 M2 headline（repetition d=3，circuit-level p=0.01，32768 shots），得到 `bp_gnn` **312 个错误 / LER 0.00952**，与优化前逐位一致。

## 4. 优化前后对比（`scripts/probe_cpu_budget.py`，同机同线程数）

| d | edges | batch | 前向 µs/shot（前 → 后） | 加速 | 峰值 RSS（前 → 后） | 训练单步（前 → 后） |
|---:|---:|---:|---:|---:|---:|---:|
| 5 | 5,814 | 128 | 9,452 → **7,767** | 1.22× | 701 → 1,152 MB | - |
| 5 | 5,814 | 512 | 10,667 → **8,901** | 1.20× | 1,285 → 2,763 MB | 2.61 → 2.47 s |
| 7 | 20,196 | 64 | 33,666 → **27,668** | 1.22× | 1,382 → 1,426 MB | - |
| 7 | 20,196 | 256 | 39,188 → **35,256** | 1.11× | 2,947 → 4,494 MB | 4.65 → 4.29 s |

repetition d=3（34 edges，M2/M3 管线，batch 1024）：GNN 前向 37.0 → **32.4 µs/shot**。

**结论与遗留**：

- 延迟收益为 **1.11-1.22×**，低于 T5 设定的「d=7 前向 ≤ 10 ms/shot」目标（当前 27.7 ms/shot @ batch 64）。瓶颈已不在 `cat`，而在逐边 gather 与 `index_add_` 的内存流量（`(shots, edges, hidden)` 张量在 d=7/batch 256 下单层即达 1.3 GB）；
- 小 batch 下的峰值 RSS 反而升高（d=7/batch 256：2.9 → 4.5 GB，d=5/batch 512：1.3 → 2.8 GB），因为拆分后的中间张量比单个 `cat` 结果更早地同时驻留；**训练侧的内存与时间都改善**（d=7 训练单步 4.65 → 4.29 s）；
- 后续若要继续压低 d=7 的 GNN 成本，需要改变计算结构而不是省分配：按边分块（edge blocking）逐块完成消息传递、把消息传递写成稀疏矩阵乘、或把隐藏维度与消息 MLP 中间宽度解耦（当前 `2h+E → h` 的第一层是主要工作量）。这些属于后续工作，见 `docs/ROADMAP_TODO.md`。