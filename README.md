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

## 9. 实验阶段与当前状态

### M0：环境与数据链路（已完成）

- Stim 与 PyMatching 环境；repetition code 跑通；detector error model 生成；固定随机种子的样本生成流程
- 产出：`artifacts/m0/`、`docs/M0_ENVIRONMENT_AND_DATA_PIPELINE.md`

### M1：经典基线（已完成）

统一 LER / 延迟 / 吞吐 / 内存测试框架与 JSON 配置格式，四个基线解码器全部可用（repetition d=3，p=0.01，4096 shots）：

| decoder | code-capacity LER | circuit-level LER | circuit-level µs/shot |
|---|---:|---:|---:|
| mwpm | 0.00049 | **0.00952** | 0.1 |
| union_find | 0.00049 | 0.01294 | 33.4 |
| bp | 0.00049 | 0.01294 | 2.3 |
| bp_osd | 0.00049 | 0.01489 | 3.9 |

- 码容量下四个解码器完全一致；线路级下 MWPM 仍是最强基线，BP 与 Union-Find 打平
- 产出：`results/m1/`、`docs/M1_BASELINE_DECODERS_AND_BENCHMARK.md`

### M2：GNN 重加权（已完成）

- detector graph 二分图特征（variable / check / edge 三类特征），模型输出逐机制后验
- 机制层面判别能力从 AUC 0.62 提升到 0.99 以上
- 学习 logits 通过固定的转换函数接入 BP 先验（LLR 约定见 `docs/M2_GNN_REWEIGHTING.md`）；把同一份预测用作 OSD-0 候选基排序则无改善，这一负结果直接指向 M3 与交付清单中的候选集学习（T8）
- 产出：`src/graph_qec/graph_features.py`、`src/graph_qec/models/`、`src/graph_qec/m2*.py`、`configs/m2_*.json`、`results/m2/`、`scripts/summarize_m2.py`、`scripts/plot_m2_results.py`

### M3：混合解码器与失效边界（已完成主体）

同分布 headline（repetition d=3，circuit-level p=0.01，32768 shots）：

| decoder | logical errors | LER | s.e. | syndrome 一致 | 收敛率 | 平均迭代 | µs/shot |
|---|---:|---:|---:|---:|---:|---:|---:|
| mwpm | 217 | **0.00662** | 0.00045 | - | - | - | 0.1 |
| bp | 309 | 0.00943 | 0.00053 | 0.9899 | 0.9899 | 0.707 | 1.9 |
| bp_osd | 331 | 0.01010 | 0.00055 | 1.0000 | 0.9899 | 0.707 | 4.0 |
| bp_gnn | 312 | 0.00952 | 0.00054 | 0.9912 | 0.9912 | 0.557 | 1.8 |
| bp_gnn_osd | 333 | 0.01016 | 0.00055 | 1.0000 | 0.9912 | 0.557 | 2.6 |
| bp_gnn_osd_learned_order | 317 | 0.00967 | 0.00054 | 1.0000 | 0.9912 | 0.557 | 3.0 |
| osd_gnn | 319 | 0.00974 | 0.00054 | 1.0000 | 0.9899 | 0.707 | 135.1 |

结论与边界：

1. **d=3 repetition 上学习先验无显著收益**（`bp` 0.00943 vs `bp_gnn` 0.00952，McNemar z=-0.77，p=0.44），但平均迭代从 0.707 降到 0.557；
2. **OSD-0 回退换不来免费的 syndrome 一致**：在 288 个未收敛 shot 上 67 修好 / 88 弄坏（z=-1.69，p=0.092），且不存在「只救不伤」的触发阈值，只有一条陡峭的 LER–一致性 Pareto 前沿；
3. **把 OSD 排序换成学习 logits 有正收益**（`bp_gnn_osd` 0.01016 vs `bp_gnn_osd_learned_order` 0.00967，z=+2.26，p=0.024）；
4. **强度自标定**：在目标分布验证集上重选先验插值强度，最优值落在 0.75-1.00，扫描曲线平坦（d=3 上收益本身很小）；
5. **跨码距迁移有效**：d=3 训练的模型直接用于 d=5，`bp` 0.05078 → `bp_gnn` **0.01709（-66%）**，机制后验 AUC 0.9876；
6. 机制后验在噪声偏移下保持校准：AUC 0.973-0.998，log loss 始终低于 DEM 先验。
- 产出：`results/m3/`、`docs/M3_HYBRID_DECODER.md`

### M4：旋转表面码与 HGP（已完成主体）

- **旋转表面码支持**：`rotated_surface_code` 家族下 MWPM / Union-Find / BP / BP+OSD / BP+GNN 全链路可用
- **小型 HGP 码构造**：`src/graph_qec/codes/hgp.py`（Tillich-Zémor 超图积、辛配对逻辑算符基、code-capacity DEM、检测器坐标嵌入），两个码 [[13,1,3]] 与 [[58,16,3]]
- **图结构对比**：线路级表面码 DEM 是稠密超图（d=3/d=5 的 check 度最大 48/80，平均 23.5/41.7，4-圈 1956/26046）；HGP 不可匹配（`matchable=False`），MWPM / Union-Find 对其完全不可用
- **学习重加权的跨码族表现**：
  - 表面码 d=3 线路级 p=0.005：`bp` 0.04007 → `bp_gnn` **0.03278（-18%）**，平均迭代 -40%，单 shot 延迟 1.85× 更快
  - 表面码 d=5 线路级 p=0.005：`bp` 0.10352 → `bp_gnn` **0.06445（-38%）**，平均迭代 -43%，单 shot 延迟 1.78× 更快（增益随码距增长）
  - HGP [[13,1,3]] p=0.05：`bp` 0.03601 → `bp_gnn` 0.03491（-3%），迭代 -30%
  - HGP 跨尺寸迁移（[[13,1,3]] → [[58,16,3]]）：`bp` 0.39487 → `bp_gnn` 0.34967（-11%），自训练可达 -27%
  - 表面码 d=3 → d=5（码容量 p=0.05）：`bp` 0.13806 → `bp_gnn` 0.12152（-12%）
  - 规律：**BP 越弱（DEM 越大、收敛率越低），学习先验收益越大**；d=3 repetition 上无显著差异
- 产出：`results/m4/`、`results/m4_surface/`、`results/m4_surface_cc/`、`results/m4_hgp/`、`docs/M4_HGP_AND_SURFACE.md`

### M5：工程优化（已完成）

- **向量化 BP**（`src/graph_qec/decoders/bp_engine.py`）：约 **100×** 加速（repetition d=3 205 → 1.9 µs/shot；表面码 d=3 18.5 ms → 0.54 ms/shot），使 d=5/d=7 扫描在 CPU 上可行；实现规范与等价性保证见 `docs/BP_IMPLEMENTATION.md`
- **GNN 动态 int8 量化**：权重压缩 3.72×、精度无损、CPU 无加速；量化后 GNN 前向成为管线瓶颈（这也是交付清单中 T5 的动机）
- **学习后验接入 MWPM（保 Stim 分解 + 相对重加权）**：`mwpm_rebuilt` 与零强度相对重加权都与基线逐 shot 一致，说明「保结构 + 保尺度换概率」零副作用；而直接重建 DEM（丢失 `^` 分解）会让 MWPM 从 455 退化到 588，定量说明分解必须保留。学习后验接 MWPM **无 LER 收益**（码容量 455 → 最好 451、满强度 498；线路级 64 → 最好 63、满强度 91），同配置下学习先验接 BP 仍有 -17%——即「逐机制边际在 BP 里能兑现、在 MWPM 边权里兑现不了」
- 产出：`results/m5/`、`docs/M5_ENGINEERING.md`、`docs/M5_DECOMPOSED_MWPM.md`、`docs/BP_IMPLEMENTATION.md`

## 10. 交付范围

本次交付为**第一阶段成果**：在 CPU-only 环境下完成上述码族、噪声模型与统计规模下的全部实验、代码与报告。范围与出口标准见 `docs/ROADMAP_TODO.md`。

需要 GPU 或属于新研究方向的内容作为**未来展望**记录，不纳入本次交付：GPU 批处理与量化迁移、d=7 的 32768 shots x 3 seeds 大规模扫描、GPU 延迟/显存/吞吐对比、d=9、时序编码器、端到端可微 BP。

## 11. 交付物

- 可复现代码仓库（含 CI）
- 配置文件驱动的数据生成、训练和解码脚本
- 基线与混合解码器实现
- 单元测试和端到端 smoke test
- LER-p 曲线与阈值估计
- CPU 延迟、吞吐、内存对比表
- HGP 码与表面码的图结构对比、跨码族/跨码距迁移报告
- 技术报告与局限性说明

## 12. 最小可行版本

下列条目构成最小可行版本，全部落在交付范围内：

| 条目 | 状态 |
|---|---|
| Repetition code 与表面码 d=3、5、7 | rep d=3/5 与表面码 d=3 已完成；d=5/d=7 表面码在交付清单 T6 |
| Code-capacity 与 circuit-level noise | 已完成 |
| MWPM 与 BP+OSD 基线 | 已完成 |
| GNN 边权重预测 | 已完成 |
| 至少一个噪声外推实验 | 已完成（噪声率外推 4 点 + 跨码距 d=3→d=5） |
| 单 shot 延迟与峰值内存测试 | CPU 部分已完成；完整对比表见 T11 |

## 13. 计算资源

交付阶段在 CPU-only 环境完成，实测预算见 `docs/ROADMAP_TODO.md` 第 1 节。后续若引入 GPU，其主要价值是大规模统计（32768 shots x 3 seeds 的 d=7 扫描）、更大的训练 batch，以及 GPU 延迟与显存的实测对比。

## 14. 风险与应对

| 风险 | 应对 |
|---|---|
| 神经解码器无法超过经典基线 | 以精度、延迟和内存的 Pareto 改进为目标；明确报告适用区间 |
| 端到端训练不稳定 | 先完成 BP 重加权和候选排序，再尝试端到端模型 |
| 模型无法外推到更大码距 | 分析局部性、图结构和噪声归一化，并明确报告失败边界 |
| HGP 码阈值较低、仿真成本高 | 先从小规模结构化码和 code-capacity 模型开始 |
| OSD 后处理成为延迟瓶颈 | 使用候选剪枝、稀疏矩阵和并行批处理优化 |
| 统计功效不足 | 每结论不少于 3 个 seed，表格显式标注 shots 与 seed 数 |

## 15. 完成标准

1. 基线解码器可在固定配置下复现。
2. 混合解码器至少在一个噪声区间改善精度、延迟或内存权衡，且给出配对检验。
3. 所有图表可由脚本自动生成。
4. 代码包含测试、日志、配置和失败案例分析。
5. 报告清楚说明适用范围、计算成本和未解决问题。