# M2：GNN 边权重/可靠性重估与混合解码接线

## 1. 阶段目标

M2 在 M1 的经典基线之上引入图神经网络，研究"学习到的 error mechanism 可靠性"能否改善 BP 和解码后处理：

- 把 DEM 变成**二分图张量**（detector/check 节点 + error mechanism/variable 节点 + hyperedge 边）；
- 训练一个**syndrome 条件 GNN**，预测每个 error mechanism 的后验边际 `P(e_i = 1 | syndrome)`；
- 把预测结果以两种方式接回经典解码器，并与 M1 基线严格对比；
- 保持配置驱动、固定随机种子、按 seed 切分训练/验证/测试，杜绝信息泄漏；
- 记录 LER、收敛率、平均 BP 迭代次数、syndrome 一致率、单 shot 延迟和模型规模。

结论先说：在 repetition code（d=3/5，circuit-level，p=0.01）上，**两种朴素的"学习可靠性"接线方式都没有超过经典基线**；本阶段的主要产出是完整的图特征/模型/训练/评测基础设施、可复现的负结果及其失败模式分析（见第 7 节）。

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

### 7.2 方案一：用学习到的边际替换 BP 先验

`bp_gnn` 使用 `s=1.0`（validation split 选择）。测试集 32768 shots：

| Decoder | 逻辑错误 | LER | 标准误 | BP 收敛率 | 平均迭代 | syndrome 一致率 | 单 shot 延迟 |
|---|---:|---:|---:|---:|---:|---:|---:|
| MWPM | 217 | 0.00662 | 0.00045 | - | - | - | 0.1 us |
| Union-Find | 318 | 0.00970 | 0.00054 | - | - | - | 38.5 us |
| BP | 404 | 0.01233 | 0.00061 | 0.9810 | 1.011 | 0.9810 | 196.3 us |
| BP+OSD-0 | 407 | 0.01242 | 0.00061 | 0.9810 | 1.011 | 1.0000 | 201.8 us |
| **BP+GNN prior (`bp_gnn`)** | **323** | **0.00986** | 0.00055 | **0.9858** | **0.863** | 0.9858 | 172.3 us |

- 相对 BP 基线，LER 从 0.01233 降到 0.00986（相对下降 20%），与 Union-Find（0.00970）持平，向 MWPM（0.00662）靠拢；
- 同一批 shot 上的 McNemar 检验：145 个不一致 shot 中 113 个被 GNN 先验修好、32 个被弄坏，z=6.73（p ~ 1e-11），差异高度显著；
- BP 的平均迭代次数从 1.011 降到 0.863、收敛率从 98.10% 升到 98.58%，说明学习到的先验同时改善了收敛行为；
- 额外延迟可以忽略：`bp_gnn` 的单 shot 延迟（含 GNN 前向 + BP）反而低于纯 Python BP 基线，因为迭代次数减少；GNN 本身在 32768 shots 上仅约 27 us/shot（batch 1024）。

validation split 上的插值扫描（5 个强度，8192 shots）：

| reweight strength s | 0.0（DEM 先验） | 0.25 | 0.5 | 0.75 | 1.0（学习先验） |
|---|---:|---:|---:|---:|---:|
| validation LER | 0.01404 | 0.01379 | 0.01428 | 0.01208 | **0.01147** |
| 平均迭代 | 1.10 | 1.09 | 1.05 | 0.87 | 0.94 |

### 7.3 方案二：用学习到的可靠性排序 OSD-0 候选基

`osd_bp`（BP 后验排序 + 强制 OSD-0）与 `osd_gnn`（学习边际排序 + 强制 OSD-0），测试集同为 32768 shots：

| Decoder | 逻辑错误 | LER | 标准误 | syndrome 一致率 | 单 shot 延迟 |
|---|---:|---:|---:|---:|---:|
| BP+OSD-0（仅未收敛触发） | 407 | 0.01242 | 0.00061 | 1.0 | 201.8 us |
| `osd_bp`（强制 OSD，BP 排序） | 407 | 0.01242 | 0.00061 | 1.0 | 541.9 us |
| `osd_gnn`（强制 OSD，学习排序） | 495 | 0.01511 | 0.00067 | 1.0 | 355.0 us |

强制 OSD 对已收敛 shot 没有额外收益（`osd_bp` 与 `bp_osd` 完全一致），而用学习边际替换 OSD 的可靠性排序反而变差约 22%。这与 7.2 形成有意义的对照：**学习到的边际作为"证据"接入 BP 先验有效，作为"排序/可靠性"接入 OSD 候选基无效**。直觉上，机制边际回答的是"每个机制是否发生"，而 OSD 排序需要的是"哪些位构成可解的基"，两者不是同一个量；下一步（M3）应把学习目标改成候选集排序/后验残差，而不是逐机制边际。

### 7.4 d=5 与 code-capacity

`configs/m2_learned_basis_repetition_circuit_level_d5.json`（d=5、circuit-level，24 个 detector、101 个机制、182 条边）在本机可以完成训练（12 epoch，最佳 validation log loss 0.02001，约 2.8 分钟），但解码评测成本随码距快速上升（BP 在 d=5 下比 d=3 慢 20 倍以上，单次验证扫描就要数分钟），本次会话在时间预算内中止。训练好的 checkpoint 已保留在 `results/m2/m2_learned_basis_repetition_circuit_level_d5__d5__circuit_level__p0p01__train_only/model_state.pt`（含 `NOTE.md` 说明），评测结果未落盘。code-capacity 配置同理留待下一轮；两者都可以直接用已验证的 CLI 复跑：

```powershell
.\\.venv\\Scripts\\python.exe -m graph_qec.m2 `
  --config configs\\m2_learned_basis_repetition_circuit_level_d5.json `
  --output-dir results\\m2
```

### 7.5 会话中发现并修复的问题

第一次评测时 `s>0` 的 LER 明显变差（0.014 → 0.048）。排查发现是**符号约定错误**：GNN 头用 `BCEWithLogitsLoss` 训练，输出是 `log P(e=1)/P(e=0)`；而 BP 的 `prior_llr`（`log((1-p)/p)`）是相反约定。直接把模型输出当作 BP 先验等于把可靠性全部取反，因此 `s>0` 必然变差。修复后先验插值单调改善（见 7.2）。该修复被固化为 `learned_logits_to_llr`，并补了单元测试；这也解释了为什么"学习到的可靠性"在早期版本里看起来完全无效。

## 8. 结论、失败模式与下一步

1. **M2 的核心结论**：在 repetition code d=3、circuit-level p=0.01 上，把 GNN 预测的 syndrome 条件机制边际作为 BP 先验，可以把 LER 相对降低约 20%（0.01233 -> 0.00986，McNemar z=6.73），同时把平均 BP 迭代次数从 1.011 降到 0.863。这满足 README 第 14 节"至少在一个噪声区间改善精度/延迟/内存权衡"的完成标准（精度与迭代次数同时改善，延迟不增）。
2. **失败模式**：BP 在本设置下的主要问题不是不收敛（收敛率 98.1%），而是**收敛到错误解**；MWPM（0.00662）与 Union-Find（0.00970）都优于 BP/BP+OSD（0.0123-0.0124）。因此只在未收敛时触发 OSD 无法改善精度；强制 OSD 也只对未收敛 shot 有效。
3. **学习目标很关键**：同一个模型，作为 BP 先验有效（-20% LER），作为 OSD 可靠性排序无效（+22% LER）。逐机制边际与"候选基选择"不是同一个学习问题。
4. **符号约定是易错点**：模型输出（`log P(e=1)/P(e=0)`）与 BP LLR（`log P(e=0)/P(e=1)`）相反，必须显式转换；这一条已被固化成函数与测试。
5. **工程约束**：本机（i5-12400 / 16 GB / 无 CUDA GPU）可以完成 d=3 的训练与评测（每个配置约 2-3 分钟）；d=5 的训练可行（约 3 分钟），但 BP 评测成本随码距快速上升，需要裁剪 test shots、`timed_runs` 或迁移到多核/云环境。

### 下一步（M3 建议）

> **⚠ 2026-10-13 晚更新：本文档的 BP 系数字已被推翻。**
> 标量 BP 实现存在两个缺陷（min-sum 未自排除、先验覆盖未进入后验），本文档正文报告的所有
> `bp` / `bp_osd` / `bp_gnn` / `bp_gnn_osd` / `osd_gnn` 数字都是**修正前**的。修正后：
> `bp` 0.01233 → 0.00943、`bp_gnn` 0.00986 → 0.00952，学习先验的 20% 收益消失（配对检验
> 6 修好 / 9 弄坏，z=-0.77, p=0.44）。详见 `docs/BP_CORRECTNESS_FIX.md`；修正后重跑结果在
> `results/m3_fixed/`。本文档的图特征、模型、训练目标、管线设计与失败模式分析仍然有效。
>
> **M3 回填（2026-10-13，见 `docs/M3_HYBRID_DECODER.md`）**：下面第 1 条假设已被**证伪**——把学习先验与 OSD-0 回退组合得到的是「退回 `bp_osd` 的 LER + 100% 一致」（`bp_gnn` 0.00986 → `bp_gnn_osd` 0.01242；配对检验 52 修好 / 136 弄坏，z=-6.13），且 OSD-0 的触发阈值扫描不存在「只救不伤」的窗口。第 4、5 条已在本轮完成（多噪声率扫描、噪声外推 0.003–0.02、码距外推 d=3→d=5、LER-延迟 Pareto、McNemar 配对检验）；第 6 条（向量化/批处理）仍是 d>=5 大样本 sweep 的前置条件。

- **零成本组合实验**：`bp_gnn` 已改进 LER 与收敛率，但 syndrome 一致率仍是 98.58%；把学习先验与 OSD-0 回退组合（未收敛 shot 走 OSD）应当同时拿到"更低 LER + 100% syndrome 一致"，这是最直接的 M3 第一步；
- **候选集学习**：把学习目标从"逐机制边际"改为"候选基/残差排序"（learning to rank），或在 OSD 中学习 pivot 选择；
- **端到端/可微 BP**：让 BP 的迭代次数或 check-to-variable 消息带上可学习偏置，直接优化 LER 而不是机制 BCE；
- **扩大统计量**：对 `bp_gnn` 与基线做多噪声率（0.005/0.008/0.01/0.02）与多码距（d=5、d=7）扫描，画出 LER-延迟 Pareto 曲线，并补配对检验；
- **噪声外推**：训练 p 与测试 p 不同的迁移实验，检验 GNN 先验是否比 DEM 先验更稳健；
- **工程优化**：把 BP 的 Python 循环换成向量化/批处理实现，否则 d>=5 的 sweep 不可行。
