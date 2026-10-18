# M2：GNN 边权重/可靠性重估与混合解码接线

## 1. 阶段目标

M2 在 M1 的经典基线之上引入图神经网络，研究"学习到的 error mechanism 可靠性"能否改善 BP 和解码后处理：

- 把 DEM 变成**二分图张量**（detector/check 节点 + error mechanism/variable 节点 + hyperedge 边）；
- 训练一个**syndrome 条件 GNN**，预测每个 error mechanism 的后验边际 `P(e_i = 1 | syndrome)`；
- 把预测结果以两种方式接回经典解码器，并与 M1 基线严格对比；
- 保持配置驱动、固定随机种子、按 seed 切分训练/验证/测试，杜绝信息泄漏；
- 记录 LER、收敛率、平均 BP 迭代次数、syndrome 一致率、单 shot 延迟和模型规模。

> 结论摘要：d=3 repetition 上学习先验没有显著 LER 收益，但平均迭代 −21%；大图上的收益见 M3/M4。完整结论见 §8，数字主源见 `docs/FINAL_REPORT.md` §4.3。

## 2. 图表示

`graph_qec.graph_features.build_graph_tensor` 从 `DEMSystem` 构建固定拓扑的二分图。设计原则：

1. **不拆 hyperedge**：一个 DEM `error` instruction 仍是一个 variable 节点，与 M1 BP 的变量定义完全一致，因此学习到的可靠性可以直接回填到同一个 BP 实现；
2. **只用图自身的确定性特征**：特征由 DEM、码几何（Stim detector 坐标）和 per-shot syndrome 决定，不引入任何训练集统计量，保证跨码距/跨噪声率可重算；
3. **per-shot 动态输入只有 syndrome**，其余特征在整轮实验中保持静态，便于批处理。

Variable 节点特征（6 维）：

| 特征 | 含义 |
|---|---|
| `prior_log_odds` | DEM 先验 `log((1-p)/p)`，裁剪到 ±30 |
| `prior_probability` | DEM 先验概率 |
| `hyperedge_size` | 该 mechanism 触及的 detector 数（即变量度） |
| `observable_count` | 该 mechanism 触发的 logical observable 数 |
| `detector_index_mean` | 触发的 detector 归一化平均下标（近似空间位置） |
| `detector_time_mean` | 触发的 detector 归一化平均时间坐标 |

Check 节点特征（3 维）：`degree_norm`（归一化度数）、`detector_index`、`detector_time`；per-shot 时再拼接 syndrome bit。

Edge 特征（3 维）：`prior_log_odds_scaled`、`inverse_variable_degree`、`inverse_check_degree`。

## 3. 模型

`graph_qec.models.BipartiteSyndromeGNN` 是一个堆叠的二分消息传递网络：

1. variable/check 节点分别由 MLP 编码（check 编码器输入包含 syndrome bit）；
2. 每层按 `check -> variable` 和 `variable -> check` 两个方向计算带边特征的消息，用 `index_add_` 按节点聚合，并按度数做均值归一化；
3. 聚合消息经残差 MLP 更新节点状态，check 状态每层重新注入 syndrome；
4. 读出层对每个 variable 输出一个 logit，即该机制 `P(e_i = 1 | syndrome)` 的对数几率。

规模（本阶段配置 `hidden_size=32`、`num_layers=3`）：约 15k 参数，CPU 单机即可训练。

## 4. 训练

- 监督信号：M0 数据管线保存的 `error_mechanisms`（当期 shot 实际发生的 DEM error instruction），损失为 `BCEWithLogitsLoss`；
- 切分：`train_seeds` / `validation_seeds` / `test_seeds` 完全不相交，每个 split 由多个 seed 的 shot 拼接；
- 选择：每个 epoch 后在 validation split 上计算 log loss，保留最佳 checkpoint（写入 `model_state.pt`）；
- 确定性：`torch.manual_seed(training.seed)`，shuffle 使用 `numpy.random.default_rng(training.seed)`；
- 可复现性：split 的 detection SHA-256、配置 SHA-256、模型规模和训练历史全部写入 `results.json`。

## 5. 两种接线方式

### 5.1 学习先验插值（`bp_gnn`）

`combined_logits(base, learned, s) = base + s * (learned - base)`，`s=0` 退化为 M1 的 BP 基线，`s=1` 完全使用学习到的边际作为 BP 先验。`s` 在 validation split 上按 (LER, 平均迭代次数) 选择。

### 5.2 学习到的 OSD 候选基（`osd_bp` / `osd_gnn`）

`BPOSDDecoder` 现在支持两个可选覆盖：

- `prior_llr`：覆盖 BP 先验；
- `osd_ordering_llr`：只覆盖 OSD-0 的列可靠性排序（决定 pivot 集合即候选基），不改变 BP 动力学。

由此得到两个对照：`osd_bp`（BP 后验排序 + 强制 OSD）和 `osd_gnn`（学习边际排序 + 强制 OSD）。强制 OSD 的意义在于：repetition code 上 BP 的失效模式不是"不收敛"，而是**收敛到错误解**（M1 已记录 97.7% 收敛率但 LER 仍高于 MWPM），因此只在未收敛时触发 OSD 无法改善。

## 6. 实验配置

配置位于 `configs/`：

| 配置 | 码 | 噪声 | 训练/验证/测试 shots | 模型 | 训练 |
|---|---|---|---|---|---|
| `m2_repetition_circuit_level_d3.json` | repetition d=3 r=3 | circuit-level p=0.01 | 16384 / 8192 / 32768 | h=32, L=3 | 15 epoch, batch 1024 |
| `m2_learned_basis_repetition_circuit_level_d3.json` | repetition d=3 r=3 | circuit-level p=0.01 | 16384 / 8192 / 32768 | h=32, L=3 | 15 epoch, batch 1024 |
| `m2_learned_basis_repetition_circuit_level_d5.json` | repetition d=5 r=5 | circuit-level p=0.01 | 16384 / 8192 / 4096 | h=32, L=3 | 12 epoch, batch 1024 |

执行方式：

```powershell
.\.venv\Scripts\python.exe -m graph_qec.m2 `
  --config configs\m2_repetition_circuit_level_d3.json `
           configs\m2_learned_basis_repetition_circuit_level_d3.json `
           configs\m2_learned_basis_repetition_circuit_level_d5.json `
  --output-dir results\m2

.\.venv\Scripts\python.exe scripts\summarize_m2.py --results-dir results\m2
.\.venv\Scripts\python.exe scripts\plot_m2_results.py --results-dir results\m2
```

## 7. 结果

### 7.1 边权重/可靠性预测质量（d=3，circuit-level，测试集 32768 shots）

GNN 只在 train split 上训练，validation split 选 checkpoint，测试集完全来自另外两个 seed。

| 指标 | 静态 DEM 先验 | syndrome 条件 GNN |
|---|---:|---:|
| error mechanism log loss | 0.07894 | **0.01440** |
| ROC AUC（机制是否触发） | 0.6197 | **0.9905** |
| 二分类准确率 | 0.98438（全零预测器） | 0.99647 |

机制触发率仅 1.56%，因此"全零"就能拿到 98.44% 的准确率；GNN 的价值体现在 log loss 与 AUC 上：AUC 从 0.62 提升到 0.99，说明模型确实学到了 syndrome 条件的机制后验，而不只是复述先验。

### 7.2 方案一：用学习到的边际替换 BP 先验（`bp_gnn`）

测试集 32768 shots，学习先验强度 s=1.0（validation split 选出）：

| Decoder | 逻辑错误 | LER | 标准误 | BP 收敛率 | 平均迭代 | syndrome 一致率 | 单 shot 延迟 |
|---|---:|---:|---:|---:|---:|---:|---:|
| MWPM | 217 | **0.00662** | 0.00045 | - | - | - | 0.1 µs |
| Union-Find | 318 | 0.00970 | 0.00054 | - | - | - | 32.0 µs |
| BP | 309 | 0.00943 | 0.00053 | 0.9899 | 0.707 | 0.9899 | 1.8 µs |
| BP+OSD-0 | 331 | 0.01010 | 0.00055 | 0.9899 | 0.707 | 1.0000 | 2.9 µs |
| **BP+GNN prior（`bp_gnn`）** | 312 | 0.00952 | 0.00054 | **0.9912** | **0.557** | 0.9912 | **1.3 µs** |

- LER 上 `bp_gnn` 与 `bp` 没有可测差异（0.00952 vs 0.00943，McNemar z=-0.77，p=0.44）；两者都落后于 Union-Find（0.00970 相近，差异在噪声内）与 MWPM（0.00662）；
- 学习先验的价值体现在收敛行为上：平均迭代 0.707 → 0.557（-21%），收敛率 0.9899 → 0.9912，含 GNN 前向的端到端单 shot 延迟反而更低（1.8 → 1.3 µs，GNN 前向本身 32 µs/shot 在 batch 下摊薄）；
- 结论：**在 d=3 repetition 上，正确的 BP 已经接近该码距的可达精度，学习先验没有 LER 发挥空间**；收益要到 BP 明显退化的大图（d=5 及更大码距、表面码线路级）才兑现，见 `docs/M3_HYBRID_DECODER.md` 第 7、8 节与 `docs/M4_HGP_AND_SURFACE.md`。

validation split 上的插值扫描（8192 shots）：

| reweight strength s | 0.0（DEM 先验） | 0.25 | 0.5 | 0.75 | 1.0（学习先验） |
|---|---:|---:|---:|---:|---:|
| validation LER | 0.01135 | 0.01135 | 0.01086 | 0.01086 | **0.01086** |
| 平均迭代 | 0.752 | 0.693 | 0.605 | 0.600 | **0.599** |

LER 随强度单调不增后进入平台，迭代次数随强度单调下降，因此 s=1.0 被选中。曲线在 s ≥ 0.5 后接近平坦，说明 LER 对强度不敏感，而迭代次数对强度敏感——这也是后续把强度当作「延迟调参」而非「精度调参」的依据。

### 7.3 方案二：用学习到的可靠性排序 OSD-0 候选基（`osd_bp` / `osd_gnn`）

测试集同为 32768 shots，强制所有 shot 走 OSD-0：

| Decoder | 逻辑错误 | LER | 标准误 | syndrome 一致率 | 单 shot 延迟 |
|---|---:|---:|---:|---:|---:|
| BP+OSD-0（仅未收敛触发） | 331 | 0.01010 | 0.00055 | 1.0 | 2.9 µs |
| `osd_bp`（强制 OSD，BP 后验排序） | 331 | 0.01010 | 0.00055 | 1.0 | 123.1 µs |
| `osd_gnn`（强制 OSD，学习边际排序） | 319 | **0.00974** | 0.00054 | 1.0 | 116.3 µs |

- 强制 OSD 对已收敛 shot 没有额外收益（`osd_bp` 与 `bp_osd` 完全一致），但把延迟推高到 123 µs/shot；
- 换用学习边际做排序后，`osd_gnn` 相对 `osd_bp` 略有改善（0.01010 → 0.00974），方向与 M3 的配对检验一致（`bp_gnn_osd_learned_order` 相对 `bp_gnn_osd`：33 修好 / 17 弄坏，z=+2.26，p=0.024）；
- 结论：学习边际在「候选基排序」用途上有可用信息，但幅度远小于其在「BP 先验」上的效果（后者在 d=5 上为 -66%），而且强制 OSD 的延迟代价不可接受。把学习目标直接改成候选集质量（OSD-λ / OSD-CS / learning-to-rank）是更直接的路径，见 `docs/ROADMAP_TODO.md`（T8）。

### 7.4 d=5 与 code-capacity 配置

`configs/m2_learned_basis_repetition_circuit_level_d5.json` 与 `configs/m2_repetition_code_capacity_d5.json` 提供 d=5 与字容量训练入口。d=5 的 checkpoint 已训练并保存在 `results/m2/m2_learned_basis_repetition_circuit_level_d5__d5__circuit_level__p0p01__train_only/model_state.pt`，其同分布评测在 `results/m3/m2_d5_eval/`（见 `docs/M3_HYBRID_DECODER.md` 第 8 节）：

```powershell
.\.venv\Scripts\python.exe -m graph_qec.m2 `
  --config configs\m2_learned_basis_repetition_circuit_level_d5.json `
  --output-dir results\m2
```

## 8. 结论与失败模式

1. **图特征与模型侧的核心结论成立**：机制层面的判别能力从 AUC 0.62 提升到 0.99，log loss 从 0.0789 降到 0.0144；模型学到的是 syndrome 条件的机制后验，而不是复述 DEM 先验（触发率仅 1.56%，因此准确率指标本身不具判别力）。
2. **BP 在该设置下的失效模式不是不收敛**（收敛率 98.99%），而是**收敛到错误解**；MWPM（0.00662）明显优于所有 BP 系解码器（0.00943-0.01010），Union-Find（0.00970）与 BP 相当。这决定了 OSD 只在未收敛时触发无法改善精度。
3. **学习边际的用途有明确分工**：作为 BP 先验只改善收敛（迭代 -21%）而不改善 d=3 的 LER；作为 OSD 候选基排序有小幅正向效果（z=+2.26）。逐机制边际回答的是「每个机制是否发生」，而候选基选择需要的是「哪些位构成可解的基」，两者不是同一个学习问题。
4. **符号约定是易错点**：GNN 头用 `BCEWithLogitsLoss` 训练，输出是 `log P(e=1)/P(e=0)`；BP 先验 LLR 的约定相反。两种约定之间的转换被固化为 `learned_logits_to_llr` 并有单测覆盖，任何新增的接线方式都必须经过该函数。
5. **工程约束**：d=3 的完整训练 + 评测约 1 分钟；随着码距上升，BP 评测成本迅速增加（表面码线路级 d=5 为 8.1 ms/shot、d=7 为 46.9 ms/shot，见 `docs/BP_IMPLEMENTATION.md` 第 4 节），因此 d≥5 的评测需要向量化 BP（已完成）与有意控制的 shot 规模（见 `docs/ROADMAP_TODO.md` 第 1 节）。

### 后续工作

- **候选集学习**：把学习目标从逐机制边际改为候选基/残差排序（OSD-λ / OSD-CS / learning-to-rank），见 `docs/ROADMAP_TODO.md`（T8）；
- **扩大统计量**：多噪声率与多码距扫描、配对检验、不少于 3 个 seed，见 T6、T10；
- **真零样本迁移**：移除边特征中的物理噪声率，检验跨噪声率的真正零样本能力，见 T12；
- **端到端 / 可微 BP**：让 BP 的迭代次数或 check-to-variable 消息带可学习偏置，直接优化 LER 而非机制 BCE，见 T15 之后的未来展望项。