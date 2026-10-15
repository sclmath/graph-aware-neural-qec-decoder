# M5：工程优化（向量化 BP、量化推理、GPU 现状）

日期：2026-10-13
前置：`docs/BP_CORRECTNESS_FIX.md`

## 1. 目标（来自 README 的 M5 定义）

- GPU 批处理和量化推理；
- 完成完整 benchmark；
- 输出技术报告和复现说明。

本轮的可执行部分：**向量化 BP**（已完成，且顺带修掉两个正确性缺陷）与 **GNN 动态 int8 量化**；GPU 部分受本机硬件限制，见第 4 节。

## 2. 向量化 BP（`src/graph_qec/decoders/bp_engine.py`）

设计：把标量实现里"逐 shot 走一遍 Tanner 图"的 Python 循环换成按 shot 维向量化的 NumPy 实现：

- 边按 check 分组（行主序天然连续）与按 variable 分组（`argsort` 排列）各存一份，用 `reduceat` 做 variable 侧求和、用带 padding 的 `(shots, checks, max_degree)` 张量做 check 侧的 min1/min2 自排除；
- 每轮迭代后把已收敛的 shot 从活动集合中**压缩掉**（gather/scatter），因此容易收敛的 shot（repetition d=3 上 98%）只跑一两轮；
- 自适应 shot 切块（默认 4M 元素预算）以限制内存峰值：d=3 repetition 一次吃完 32768 shot，表面码按几千 shot 分块。

| 场景 | 修正前 | 修正后（向量化） | 加速 |
|---|---:|---:|---:|
| repetition d=3 circuit-level（32768 shots） | 205 µs/shot | **1.9 µs/shot** | ~107× |
| repetition d=5 circuit-level | ~11 ms/shot | ~0.5 ms/shot | ~20× |
| surface d=3 circuit-level（564 edges） | 18.5 ms/shot | **0.54 ms/shot** | ~34× |
| surface d=3 code-capacity（98 edges） | ~3 ms/shot | 4.4 µs/shot | ~600× |

解锁的后果：M3 headline 整条管线从 259 s 降到 55 s；M4 的多噪声率 / 多码距扫描从"算力不可及"变成分钟级；BP 从"比 MWPM 慢 2000 倍"变成"慢 2–5 倍"。

等价性（`tests/test_batched_bp.py`）：对 repetition 与表面码两种 DEM，修正后的标量参考实现与向量化引擎在 corrections / iterations / converged / syndrome_distance 上**逐 shot 完全一致**，后验 LLR 差异 ≤ 1e-12（高 check 度时为浮点求和顺序差异，量级 1e-15）。

## 3. GNN 动态 int8 量化

`scripts/m5_quantization.py` 用 d=3 repetition 的 M3 checkpoint 在 16384 test shots 上对比 float32 与 `torch.ao.quantization.quantize_dynamic(..., dtype=torch.qint8)`（最优 3 轮）：

| 模型 | 权重 (MB) | 推理 (s) | µs/shot | 机制后验 log loss | 与 float 的符号一致率 |
|---|---:|---:|---:|---:|---:|
| float32 | 0.0612 | 2.729 | 166.57 | 0.01497 | - |
| int8（动态） | **0.0165** | 2.721 | 166.07 | 0.01497 | 0.99995 |

| decoder | logical errors | LER | syndrome 一致 |
|---|---:|---:|---:|
| bp_gnn（float32 先验） | 145 | 0.00885 | 0.9917 |
| bp_gnn（int8 先验） | 145 | 0.00885 | 0.9917 |
| bp（无先验） | 144 | 0.00879 | 0.9907 |

结论：

- **量化几乎无损**：权重压缩 **3.72×**，机制后验 log loss 与接回 BP 后的 LER 完全不变（logit 最大偏差 0.44，机制符号一致率 0.99995）；
- **但 CPU 上没有加速（1.00×）**：动态量化的反量化开销抵消了更便宜的矩阵乘，且当前规模（34 条边、hidden 32）本来就偏小；
- 本轮最重要的工程观察：**向量化之后，GNN 前向（166 µs/shot）成了整条管线的瓶颈，而 BP 只要 1.9 µs/shot**。也就是说 M5 之后要优化的是 GNN 的形状（减少每边的 MLP 计算、预分配缓冲、或把消息传递改成稀疏矩阵乘），而不是 BP。
- 该小节的数字也再次印证了 `docs/BP_CORRECTNESS_FIX.md` 的结论：`bp` 144 个错误 vs `bp_gnn` 145 个，d=3 repetition 上学习先验没有收益。

## 4. GPU 现状（重要限制）

本机 PyTorch 为 **CPU-only 构建**（`torch 2.14.1+cpu`，`torch.cuda.is_available() == False`），因此 M5 的"GPU 批处理与量化推理对比"**无法在本机执行**，本轮不做任何 GPU 数字的声明。可在有 GPU 的机器上执行的迁移路径：

1. 向量化 BP 的 shot 维天然可搬到 GPU：把 `bp_engine` 里的活动集合切片换成 `torch.Tensor`，边聚合用 `index_add_` / `torch.sparse` 的稀疏矩阵-向量乘；
2. GNN 前向已经是 `(shots, edges, hidden)` 的批量张量，改 `device=` 即可；主要成本在 `torch.cat` 的临时张量，可先做 `index_select` + 预分配缓冲；
3. 量化对比需要重跑第 3 节的脚本并把 `torch.ao.quantization.quantize_dynamic` 换成 `torchao`（当前 torch 版本的动态量化 API 已标记为 deprecated，2026-10 后 `torch.ao.quantization` 会被移除）。

## 5. 尝试与失败模式：把学习后验喂给 MWPM（`scripts/m5_gnn_mwpm.py`）

M4 的结论之一是对**可匹配码**应该修正 MWPM 的边权重而不是 BP 的先验，本轮做了原型（`results/m5/gnn_mwpm_cc/`），结果是**反例**，而且反例的原因很有教育意义：

做法是"逐 shot 用学习到的机制后验概率重建 DEM，再建匹配图解码"。结果：

| decoder | LER（d=3 表面码，码容量 p=0.05，4096 shots） |
|---|---:|
| mwpm（stim 分解后的 DEM） | 0.0527 |
| mwpm + GNN 后验（重建 DEM） | 0.3130 |
| bp + GNN 先验 | 0.0581 |

看起来"学习后验毁了 MWPM"，但**控制实验**证明这是实现问题而不是科学结论：用**相同的重建代码但喂回 DEM 自己的先验概率**，MWPM 从 0.0439 退化到 **0.0679**——即重建本身就把匹配图弄坏了。

原因：重建 DEM 时把每个机制写成一条 `error(p) D... L...`，于是 **Y 误差变成 4-detector 超边**（翻转 2 个 X-check + 2 个 Z-check），而 PyMatching 只能处理图状（≤2 detector）误差。Stim 的 `decompose_errors=True` 会用 `^` 把这类机制拆成两条边并保留相关性，我的重写丢掉了这个分解，匹配图因此缺边。

要做对，必须把学习后验映射到 **stim 分解后的指令**上（而不是重写原始 DEM），这是一项有界但需要细致实现的后续工作，本轮因时间预算停在这里，不给出任何"学习后验对 MWPM 有害"的结论。

## 6. 结论

1. **向量化 BP 是 M5 最有价值的一项**：约两个数量级加速，同时暴露并修正了两个正确性缺陷（见 `docs/BP_CORRECTNESS_FIX.md`）；
2. 量化收益见第 3 节；GNN 在整条管线里通常只占 10–30% 的时间（表面码上因为提前收敛省下 BP 迭代，GNN 反而"免费"），所以量化的主要意义在显存/内存而非吞吐；
3. GPU 项因硬件缺失顺延，方案已在第 4 节列明。
