# Graph-Aware Neural QEC Decoder

## 1. 项目概述

构建面向表面码、量子 LDPC 码和 HGP 码的图感知混合解码器。项目将量子纠错解码建模为带噪声图上的推断与组合优化问题，结合置信传播、匹配或 OSD，以及图神经网络，研究逻辑错误率、解码延迟和内存占用之间的权衡。

## 2. 研究问题

1. 如何把 decoder error model 和 Tanner 图结构编码为适合图神经网络处理的特征？
2. 学习到的边权重和候选误差集能否减少 BP 迭代次数与 OSD 搜索规模？
3. 混合解码器能否在不同噪声率、码距和码族之间保持稳健？
4. 神经网络推理的 GPU 加速是否能在可接受的精度下降低单 shot 延迟？
5. HGP 码与表面码的图结构差异如何影响解码器的泛化能力？

## 3. 研究范围

### 3.1 纠错码

- Repetition code
- Rotated surface code：d=3、5、7，扩展目标为 d=9
- 小型 HGP 码
- 结构化量子 LDPC 码及其 Tanner 图
- 不同基矩阵生成的 HGP 码族

### 3.2 噪声模型

- Code-capacity noise
- Circuit-level depolarizing noise
- Detector error model
- 噪声率扫描：0.001、0.002、0.003、0.005、0.008、0.01
- 训练集与测试集之间的噪声率偏差
- 测量错误和跨轮次关联

### 3.3 技术栈

- Python
- Stim：量子线路采样和 detector error model
- PyMatching：MWPM 基线
- PyTorch：GNN、时序模型和多任务训练
- 支持 BP+OSD 的量子 LDPC 解码库
- NumPy、SciPy、Matplotlib、pandas
- CPU/GPU profiling 工具

## 4. 输入表示

每个解码样本表示为检测事件图或 Tanner 图：

- 节点：detector event、check node 或 stabilizer measurement
- 边：可能的 error mechanism
- 节点特征：syndrome bit、时间坐标、测量类型、check 类型
- 边特征：错误概率、空间距离、时间距离、error type、所属 stabilizer
- 全局特征：code distance、物理噪声率、线路深度、码族
- 时序特征：最近若干轮 syndrome history

## 5. 模型方案

### 5.1 保守混合架构

`BP -> GNN 边权重重估 -> BP 重跑 -> OSD 后处理`

该方案保留 syndrome 一致性约束，避免纯神经网络输出无效 correction。

### 5.2 图编码器

- 使用消息传递网络编码 detector graph 或 Tanner graph
- 学习 error mechanism 的可靠性分数
- 输出候选误差集和边权重
- 探索局部感受野与可扩展性设计

### 5.3 时序编码器

- 使用一维卷积或轻量 Transformer 处理 syndrome history
- 建模测量错误和跨轮次关联
- 控制序列长度以避免推理延迟过高

### 5.4 解码输出

- 逻辑 observable parity 预测
- 候选误差机制排序
- 根据候选集合运行 BP+OSD 或小规模组合优化
- 输出最终 correction 和置信度
- 保证输出满足 syndrome 约束

## 6. 训练目标

采用多任务损失：

- 错误机制预测：二分类交叉熵
- 逻辑翻转预测：observable parity 分类
- BP 收敛预测：判断是否需要进入 OSD
- 候选排序：learning to rank
- 稀疏性正则：限制 OSD 候选规模

训练数据必须按随机种子、噪声率、码距和码族进行切分，严格避免测试信息泄漏。

## 7. 基线与消融

### 7.1 基线

- MWPM
- Union-Find 或快速匹配解码器
- BP
- BP+OSD
- 纯 GNN 解码器
- BP+GNN 混合解码器

### 7.2 消融实验

- 有/无 GNN 重加权
- 有/无时序编码器
- 不同 top-k 候选规模
- 有/无 OSD
- 不同图特征组合
- CPU 与 GPU 推理对比
- 浮点与量化推理对比

## 8. 评价指标

### 8.1 解码性能

- Logical error rate versus physical error rate
- 阈值估计
- 不同码距下的 error suppression
- 逻辑翻转率
- 噪声偏差下的性能下降

### 8.2 工程性能

- 单 shot 延迟
- Batch decoding throughput
- CPU/GPU 延迟
- 峰值内存和显存
- BP 平均迭代次数
- OSD 平均候选集大小
- 模型参数量

### 8.3 理论分析

- 混合解码器与图割、匹配、最小权解码的关系
- 候选剪枝对解码复杂度的影响
- 不同码族的结构敏感性
- 模型失效区间

## 9. 实验阶段

当前进度（2026-10-13 晚）：M0、M1、M2 已完成，M3 主体完成（`docs/M3_HYBRID_DECODER.md`），
M4 进行中（表面码 + HGP，`docs/M4_HGP_AND_SURFACE.md`），M5 的 BP 工程化已完成
（向量化 BP，约 100× 加速，见 `docs/BP_CORRECTNESS_FIX.md`）。

> **重要更正（2026-10-13）**：标量 BP 存在两个缺陷（min-sum 未自排除、先验覆盖未进入后验），
> M1–M3 报告过的所有 BP 系数字都已被修正后重跑取代，学习先验在 d=3 上的 20% 收益**不成立**。
> 详见 `docs/BP_CORRECTNESS_FIX.md`，修正后结果在 `results/m3_fixed/`。

### M0：环境与数据链路（已完成）

- 完成 Stim 和 PyMatching 环境
- 跑通 repetition code
- 生成 detector error model
- 建立固定随机种子的样本生成流程

### M1：经典基线（已完成）

- 完成 MWPM、Union-Find、BP 和 BP+OSD
- 建立 LER、延迟和内存测试框架
- 固化实验配置格式

### M2：GNN 重加权（已完成，2026-10-12）

- 实现 detector graph 二分图特征（variable/check/edge 三类特征，见 `docs/M2_GNN_REWEIGHTING.md`）
- 训练 syndrome 条件 GNN 预测 error mechanism 后验边际（机制 AUC 0.62 -> 0.99）
- 把预测 LLR 接入 BP 先验：d=3 circuit-level 上 LER 0.01233 -> 0.00986（-20%），平均迭代 1.011 -> 0.863
- 把预测可靠性接入 OSD-0 候选基：无改善（0.01242 -> 0.01511），已记录失败模式
- 产出：`src/graph_qec/graph_features.py`、`src/graph_qec/models/`、`src/graph_qec/m2*.py`、`configs/m2_*.json`、`results/m2/`、`scripts/summarize_m2.py`、`scripts/plot_m2_results.py`

### M3：混合解码器（主体完成，2026-10-13）

已完成：

- `bp_gnn_osd` = 学习先验接 BP + 未收敛 shot 走 OSD-0 回退（并新增 `bp_gnn_osd_learned_order`）
- 迁移评测框架 `src/graph_qec/m3_pipeline.py` / `m3.py`：加载 checkpoint，在不同噪声率/噪声模型/码距上评测，不重新训练
- 噪声外推（d=3，p=0.01 → 0.003/0.005/0.008/0.02）、码距外推（d=3 → d=5）、d=3 与 d=5 的 LER–延迟 Pareto
- 逐 shot 失效归因与 McNemar 配对检验（`scripts/m3_failure_analysis.py`）
- 先验强度自标定修复（`scripts/m3_strength_recalibration.py`）：在目标分布验证集上重选强度后，四个噪声率上相对 DEM 先验 BP 降低 16%–24%，且 `bp_gnn_osd` 保持 100% syndrome 一致
- 结果：`results/m3/SUMMARY.md`、`results/m3/sweep.csv`、`results/m3/figures/`、`docs/M3_HYBRID_DECODER.md`

关键结论：OSD-0 回退**不能**顺便换来 syndrome 一致（52 修好 / 136 弄坏，z=-6.13），且不存在「只救不伤」的触发阈值，只有一条陡峭的 LER–一致性 Pareto 前沿；学习先验的收益在 p < 训练噪声率时转为有害（根本原因是尺度失配而非排序失准，AUC 仍有 0.97+），用目标分布验证集重选插值强度即可修复；d=3 训练的模型可直接迁移到 d=5（LER -17%）。

待补：d=7 外推（本机 BP 延迟约 11 ms/shot @ d=5，d=7 需 GPU 批处理）、OSD 触发策略与候选集学习（OSD-λ / OSD-CS / learning-to-rank）。

### M4：HGP 和量子 LDPC 扩展（主体完成，2026-10-13）

已完成：

- **旋转表面码支持**：`configs/m4_*.json` + `circuits.py` 的 `rotated_surface_code` 家族，MWPM / Union-Find / BP / BP+OSD / BP+GNN 全链路可用
- **小型 HGP 码构造**：`src/graph_qec/codes/hgp.py`（Tillich-Zémor 超图积、辛配对逻辑算符基、code-capacity DEM、检测器坐标嵌入），两个码：[[13,1,3]] 与 [[58,16,3]]
- **图结构对比**：`results/m4/GRAPH_STRUCTURE.md`——线路级表面码 DEM 是稠密超图（check 度最大 48/80、平均 23.5/41.7），HGP 不可匹配（`matchable=False`）
- **学习重加权的跨码族表现**：
  - 表面码 d=3 线路级 p=0.005：`bp` 0.04007 → `bp_gnn` **0.03278（-18%）**，迭代 -40%，单 shot 延迟 1.85× 更快
  - HGP [[13,1,3]] p=0.05：`bp` 0.03601 → `bp_gnn` 0.03491（-3%），迭代 -30%
  - 规律：**BP 越弱（DEM 越大越退化），学习先验收益越大**；d=3 repetition 上则无显著差异
- 结果：`results/m4/`、`results/m4_surface/`、`results/m4_hgp/`、`docs/M4_HGP_AND_SURFACE.md`

### M5：工程优化与报告（部分完成，2026-10-13）

已完成：

- **向量化 BP**（`src/graph_qec/decoders/bp_engine.py`）：约 **100×** 加速（d=3 repetition 205 → 1.9 µs/shot；表面码 d=3 18.5 ms → 0.54 ms/shot），并顺带发现并修正两个正确性缺陷——详见 `docs/BP_CORRECTNESS_FIX.md`
- **GNN 动态 int8 量化**：权重压缩 3.72×、精度无损、CPU 无加速；量化后 GNN 前向（166 µs/shot）已成为管线瓶颈
- 技术报告：`docs/BP_CORRECTNESS_FIX.md`、`docs/M4_HGP_AND_SURFACE.md`、`docs/M5_ENGINEERING.md`

- **学习后验 → MWPM（保分解 + 相对重加权）**：`src/graph_qec/m5.py` + `scripts/m5_gnn_mwpm_decomposed.py`，修掉 M5 第 5 节原型的三个缺陷（丢掉 Stim `^` 分解、LLR 符号接反、逐机制概率原样代换）；`mwpm_rebuilt` 与零强度相对重加权都与基线**逐 shot 一致**，原型路径的劣化被定量复现（+29% / +14%）。学习后验接 MWPM **无 LER 收益**（码容量 455 → 最好 451、满强度 498；线路级 64 → 最好 63、满强度 91），而同配置下学习先验接 BP 仍是 -17%——即"逐机制边际在 BP 里能兑现、在 MWPM 边权里兑现不了"。详见 `docs/M5_DECOMPOSED_MWPM.md`

待补：**GPU 批处理**（本机为 CPU-only torch 构建，`torch.cuda.is_available() == False`，无法在本机给出 GPU 数字；迁移方案见 `docs/M5_ENGINEERING.md` 第 4 节）

## 10. 交付物

- 可复现代码仓库
- 配置文件驱动的数据生成、训练和解码脚本
- 基线与混合解码器实现
- 单元测试和端到端 smoke test
- LER 曲线与阈值图
- 延迟、吞吐、内存对比表
- HGP 码和表面码的对比报告
- 技术报告与局限性说明

## 11. 最小可行版本

- Repetition code 和 surface code d=3、5、7
- Code-capacity 与 circuit-level noise
- MWPM 和 BP+OSD 基线
- GNN 边权重预测
- 至少一个噪声外推实验
- 单 shot 延迟和峰值内存测试

## 12. 计算资源

建议使用单张 16-24 GB GPU。基础实验应支持小规模 CPU 回退，完整实验允许长时间 GPU 训练。

## 13. 风险与应对

| 风险 | 应对 |
|---|---|
| 神经解码器无法超过经典基线 | 以精度、延迟和内存的 Pareto 改进为目标 |
| 端到端训练不稳定 | 先完成 BP 重加权和候选排序，再尝试端到端模型 |
| 模型无法外推到更大码距 | 分析局部性、图结构和噪声归一化，并明确报告失败边界 |
| HGP 码阈值较低、仿真成本高 | 先从小规模结构化码和 code-capacity 模型开始 |
| OSD 后处理成为延迟瓶颈 | 使用候选剪枝、稀疏矩阵和并行批处理优化 |

## 14. 完成标准

1. 基线解码器可在固定配置下复现。
2. 混合解码器至少在一个噪声区间改善精度、延迟或内存权衡。
3. 所有图表可由脚本自动生成。
4. 代码包含测试、日志、配置和失败案例分析。
5. 报告清楚说明适用范围、计算成本和未解决问题。


