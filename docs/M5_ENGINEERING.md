# M5：工程优化（向量化 BP、量化推理、GPU 现状）

日期：2026-10-13
前置：`docs/BP_IMPLEMENTATION.md`

## 1. 目标（来自 README 的 M5 定义）

- GPU 批处理和量化推理；
- 完成完整 benchmark；
- 输出技术报告和复现说明。

本阶段完成：**向量化 BP** 与 **GNN 动态 int8 量化**。GPU 部分不在交付范围内（交付环境为 CPU-only），见第 4 节。

## 2. 向量化 BP（`src/graph_qec/decoders/bp_engine.py`）

设计：把标量实现里"逐 shot 走一遍 Tanner 图"的 Python 循环换成按 shot 维向量化的 NumPy 实现：

- 边按 check 分组（行主序天然连续）与按 variable 分组（`argsort` 排列）各存一份，用 `reduceat` 做 variable 侧求和、用带 padding 的 `(shots, checks, max_degree)` 张量做 check 侧的 min1/min2 自排除；
- 每轮迭代后把已收敛的 shot 从活动集合中**压缩掉**（gather/scatter），因此容易收敛的 shot（repetition d=3 上 98%）只跑一两轮；
- 自适应 shot 切块（默认 4M 元素预算）以限制内存峰值：d=3 repetition 一次吃完 32768 shot，表面码按几千 shot 分块。

实测加速约 20–600×（按图规模）；d=3 repetition 从 205 µs/shot 降到 1.9 µs/shot。逐场景数字、内存预算与解锁的扫描规模见 `docs/BP_IMPLEMENTATION.md` §4。

等价性（`tests/test_batched_bp.py`）：对 repetition 与表面码两种 DEM，标量参考实现与向量化引擎在 corrections / iterations / converged / syndrome_distance 上**逐 shot 完全一致**，后验 LLR 差异 ≤ 1e-12（高 check 度时为浮点求和顺序差异，量级 1e-15）。

## 3. GNN 动态 int8 量化

`scripts/m5_quantization.py` 用 d=3 repetition 的 M3 checkpoint 在 16384 test shots 上对比 float32 与 `torch.ao.quantization.quantize_dynamic(..., dtype=torch.qint8)`（最优 3 轮）：

| 模型 | 权重 (MB) | 推理 (s) | µs/shot | 机制后验 log loss | 与 float 的符号一致率 |
|---|---:|---:|---:|---:|---:|
| float32 | 0.0612 | 0.520 | 31.73 | 0.01497 | - |
| int8（动态） | **0.0165** | 0.672 | 40.99 | 0.01496 | 0.99995 |

| decoder | logical errors | LER | syndrome 一致 |
|---|---:|---:|---:|
| bp_gnn（float32 先验） | 145 | 0.00885 | 0.9917 |
| bp_gnn（int8 先验） | 145 | 0.00885 | 0.9917 |
| bp（无先验） | 144 | 0.00879 | 0.9907 |

结论：

- **量化几乎无损**：权重压缩 **3.72×**，机制后验 log loss 与接回 BP 后的 LER 完全不变（logit 最大偏差 0.44，机制符号一致率 0.99995）；
- **但 CPU 上是负加速（0.77×）**：动态量化的反量化开销抵消了更便宜的矩阵乘，且当前规模（34 条边、hidden 32）本来就偏小；
- 工程观察：**向量化之后，GNN 前向成了整条管线的瓶颈（d=3 repetition 31.7 µs/shot @ batch 1024），而 BP 只要 1.9 µs/shot**。因此要优化的是 GNN 的形状（减少每边的 MLP 计算、预分配缓冲、或把消息传递改成稀疏矩阵乘），而不是 BP；表面码 d=7 上 GNN 前向与 BP 同量级（优化后 35 ms/shot @ batch 256，BP 为 47 ms/shot，见 `docs/BP_IMPLEMENTATION.md` 第 4 节与 `results/m5/GNN_PERF.md`）。
- 该小节的数字与 `docs/M3_HYBRID_DECODER.md` 第 3 节的同分布结论一致：d=3 repetition 上学习先验没有可测的 LER 收益。

## 4. GPU 现状与迁移路径

交付环境为 CPU-only：PyTorch 是 CPU-only 构建（`torch 2.14.1+cpu`，`torch.cuda.is_available() == False`），因此 GPU 批处理与量化推理对比不在交付范围内，本文档不给出任何 GPU 数字。需要 GPU 时的迁移路径：

1. 向量化 BP 的 shot 维天然可搬到 GPU：把 `bp_engine` 里的活动集合切片换成 `torch.Tensor`，边聚合用 `index_add_` / `torch.sparse` 的稀疏矩阵-向量乘；
2. GNN 前向已经是 `(shots, edges, hidden)` 的批量张量，改 `device=` 即可；主要成本在 `torch.cat` 的临时张量，可先做 `index_select` + 预分配缓冲；
3. 量化对比需要把 `torch.ao.quantization.quantize_dynamic` 换成 `torchao`（当前 torch 版本的动态量化 API 已标记为 deprecated，2026-10 后 `torch.ao.quantization` 会被移除）。

GPU 的延迟、吞吐与峰值显存对比属于后续工作，见 `docs/ROADMAP_TODO.md` 第 7 节。

## 5. 把学习后验喂给 MWPM 的对照实验

逐 shot 用学习后验重建 DEM 会丢掉 Stim 的 `^` 分解，MWPM 因此从 0.0439 退化到 0.0679；这属于实现问题，不能用来评价学习后验。保分解 + 相对重加权的完整阶梯实验、映射覆盖率与结论见 `docs/M5_DECOMPOSED_MWPM.md`。

## 6. 结论

1. **向量化 BP 是本阶段最有价值的工程项**：约两个数量级加速（实现规范与等价性保证见 `docs/BP_IMPLEMENTATION.md`）；
2. 量化收益见第 3 节；GNN 在整条管线里通常只占 10–30% 的时间（表面码上因为提前收敛省下 BP 迭代，GNN 反而"免费"），所以量化的主要意义在显存/内存而非吞吐；
3. GPU 项不在交付范围内；若引入 GPU，迁移方案见第 4 节。
