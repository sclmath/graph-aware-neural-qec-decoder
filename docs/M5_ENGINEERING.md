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

| 场景 | 标量实现 | 向量化实现 | 加速 |
|---|---:|---:|---:|
| repetition d=3 circuit-level（32768 shots） | 205 µs/shot | **1.9 µs/shot** | ~107× |
| repetition d=5 circuit-level | ~11 ms/shot | ~0.5 ms/shot | ~20× |
| surface d=3 circuit-level（564 edges） | 18.5 ms/shot | **0.54 ms/shot** | ~34× |
| surface d=3 code-capacity（98 edges） | ~3 ms/shot | 4.4 µs/shot | ~600× |

解锁的后果：M3 headline 整条管线降到 55 s；M4 的多噪声率 / 多码距扫描从"算力不可及"变成分钟级；BP 从"比 MWPM 慢 2000 倍"变成"慢 2–5 倍"。

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

## 5. 把学习后验喂给 MWPM 的对照实验（`scripts/m5_gnn_mwpm.py`）

M4 的结论之一是对**可匹配码**应该修正 MWPM 的边权重而不是 BP 的先验。本节记录把学习后验直接接进 MWPM 的对照实验（`results/m5/gnn_mwpm_cc/`），结论是**反例**，而反例的原因具有方法论意义：

做法是"逐 shot 用学习到的机制后验概率重建 DEM，再建匹配图解码"。结果：

| decoder | LER（d=3 表面码，码容量 p=0.05，4096 shots） |
|---|---:|
| mwpm（stim 分解后的 DEM） | 0.0527 |
| mwpm + GNN 后验（重建 DEM） | 0.3130 |
| bp + GNN 先验 | 0.0581 |

这看起来是"学习后验毁了 MWPM"，但**控制实验**证明它是实现问题而不是科学结论：用**相同的重建代码但喂回 DEM 自己的先验概率**，MWPM 同样从 0.0439 退化到 **0.0679**——重建本身就把匹配图弄坏了。

原因：重建 DEM 时每个机制被写成一条 `error(p) D... L...`，于是 **Y 误差变成 4-detector 超边**（翻转 2 个 X-check + 2 个 Z-check），而 PyMatching 只能处理图状（≤2 detector）误差。Stim 的 `decompose_errors=True` 会用 `^` 把这类机制拆成两条 graphlike 指令并保留相关性，重写会丢掉这个分解，匹配图因此缺边。

正确的做法是把学习后验映射到 **Stim 分解后的指令**上（而不是重写原始 DEM）。该路径的完整实现与对照实验见 `docs/M5_DECOMPOSED_MWPM.md`。

## 6. 结论

1. **向量化 BP 是本阶段最有价值的工程项**：约两个数量级加速（实现规范与等价性保证见 `docs/BP_IMPLEMENTATION.md`）；
2. 量化收益见第 3 节；GNN 在整条管线里通常只占 10–30% 的时间（表面码上因为提前收敛省下 BP 迭代，GNN 反而"免费"），所以量化的主要意义在显存/内存而非吞吐；
3. GPU 项不在交付范围内；若引入 GPU，迁移方案见第 4 节。
