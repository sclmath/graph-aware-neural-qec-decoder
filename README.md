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

## 9. 核心结果

第一阶段在 CPU-only 环境完成了 repetition code、旋转表面码 d=3/5/7 与两个小型 HGP 码的实验。五条核心结论：

1. **机制判别很容易，但机制边际本身换不来精度。** GNN 把机制后验 AUC 从 0.62 提到 0.99 以上；在 d=3 repetition 上，把同一份预测接进 BP 没有显著 LER 收益（3 seeds 配对 Δ = −0.00028 ± 0.00035），稳定收益是降低 BP 迭代次数。
2. **学习先验的收益在 BP 强度“中等”时最大。** 表面码线路级 5 个噪声率 × 3 seeds 的 30/30 点显示：码距轴为 d=3 −29.0% ± 2.4% → d=5 −37.1% → d=7 −25.1%，峰值在 d=5；噪声率轴上 d=5 在 p=0.003 达到 −43.4%，d=7 单调下降。
3. **真正的杠杆是候选基质量，而不是逐机制边际。** OSD-0 在 10 个表面码点全部有害；换成 OSD-CS(λ) 后，表面码 d=3 的 `bp_gnn_osd_cs8` 达到 0.01913（相对 `bp` −52%），但 CS 相对 `bp_gnn` 的净增益只在 d=7 p=0.003 有方向（−15.7% ± 13.3%，n.s.）。
4. **Union-Find 基线已修复。** 原实现缺少 peeling，表面码 d=3 码容量 LER 为 0.06311；重写为忠实加权 Union-Find 后为 0.00214（= MWPM），10 个扫描点比值为 1.00–1.41×。
5. **图结构决定解码器可用性。** 线路级表面码 DEM 是稠密超图（d=3/d=5 check 度最大 48/80），HGP 不可匹配（`matchable=False`），MWPM / Union-Find 对其不可用，BP 系是唯一通用选择。

> 完整数字、统计口径、适用范围、计算成本与未解决问题见 `docs/FINAL_REPORT.md`。

## 10. 交付状态

- **P0/P1 全部完成**：T1–T11、T17、T18；出口标准 1–6 已在本地核验。
- **本地收口**：`pytest` 72 项全过；端到端 smoke 通过；T6 网格 0 pending / 30 points。
- **远端状态**：D1 暂不绑定远端，CI 首跑挂起；本地使用 Git bundle + SHA256 快照备份。
- **交付范围**：repetition code；旋转表面码 d=3/5/7；HGP [[13,1,3]]、[[58,16,3]]；code-capacity 与 circuit-level 噪声；CPU 延迟/吞吐/内存对比。
- **不交付**：GPU 数字、d=9、时序编码器、端到端可微 BP、32768 shots × 3 seeds 的 d=7 大规模扫描。

## 11. 文档导航

| 需要什么 | 去哪里 |
|---|---|
| 文档职责与唯一事实源 | `docs/INDEX.md` |
| 完整技术报告与所有数字 | `docs/FINAL_REPORT.md` |
| 未完成任务、优先级、工时 | `docs/ROADMAP_TODO.md` |
| 环境、验证入口、已知坑 | `docs/HANDOFF.md` |
| 本地交付快照与恢复 | `docs/DELIVERY_LOCAL.md` |
| 里程碑实现细节 | `docs/M0`–`docs/M5` |
| OSD-CS 专题 | `docs/T8_OSD_CANDIDATE_SET.md` |
| Union-Find 专题 | `docs/T18_UNION_FIND_ANALYSIS.md` |
| BP 算法规范 | `docs/BP_IMPLEMENTATION.md` |
| 文献综述与文献表 | `docs/references/LITERATURE_REVIEW.md`、`docs/references/references.md` |
| 实验结果与生成物 | `results/README.md` |

## 12. 完成标准

1. 基线解码器可在固定配置下复现。
2. 混合解码器至少在一个噪声区间改善精度、延迟或内存权衡，并给出配对检验。
3. 所有图表可由脚本自动生成。
4. 代码包含测试、日志、配置和失败案例分析。
5. 报告清楚说明适用范围、计算成本和未解决问题。
