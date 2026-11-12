# 学习后验与 MWPM 边权重

- **版本日期**：2026-11-12
- **代码**：`src/graph_qec/m5.py`、`scripts/m5_gnn_mwpm_decomposed.py`
- **测试**：`tests/test_m5_decomposed_mwpm.py`（13 项）
- **结果**：`results/m5/gnn_mwpm_decomposed_cc/`、`results/m5/gnn_mwpm_decomposed_cl/`

## 1. 目标

对可匹配码，评估学习到的 error mechanism 后验能否作为 MWPM matching graph 的边权修正，同时保持 Stim DEM 的结构与概率尺度。

## 2. 实现约定

### 2.1 保留 Stim 的 `^` 分解

PyMatching 只处理 detector 数 ≤2 的边。直接从未分解 DEM 重建匹配图会改变超边结构；当前实现在 Stim 分解后的 error instruction 上工作，并逐条保留 detector pieces。

### 2.2 固定 LLR 约定

项目使用 `llr = log((1-p)/p)`，对应 `p = sigmoid(-llr)`。`graph_qec.m5.log_odds_to_probabilities` 固化该换算，并由单测覆盖。

### 2.3 相对重加权

Stim 分解会重新分配机制概率，因此不能把父机制概率直接代入每条分解指令。当前实现使用相对偏移：

```text
llr_j = log((1 - p_j) / p_j) + shift[parent(j)]
shift = strength * (learned_llr - prior_llr)
```

`strength=0` 时完整复原当前 DEM 的概率与结构。

## 3. 处理流程

1. `error_instructions(dem)` 解析 flattened error instructions，并保留 `^` 分解。
2. `rewrite_probabilities(dem, p)` 重写概率，targets 原样复制。
3. `map_decomposed_to_raw(raw_dem, matching_dem)` 将分解指令映射回原始机制；候选按 detector/observable 支撑包含关系选择，取支撑最小者，并以先验概率距离打破并列。
4. `apply_relative_shift(...)` 应用相对重加权。
5. `matching_from_probabilities(...)` 构建逐 shot 匹配图。

## 4. 结构一致性校验

码容量 d=3，8192 shots；线路级 d=3，4096 shots。

| 解码器 | 码容量错误 | 线路级错误 |
|---|---:|---:|
| `mwpm` | 455 | 64 |
| `mwpm_rebuilt` | 455 | 64 |
| `mwpm_shift_zero` | 455 | 64 |
| `mwpm_map_prior_absolute` | 455 | 71 |
| `mwpm_naive_raw` | 588 | 73 |

`mwpm_rebuilt` 与 `mwpm_shift_zero` 均与 `mwpm` 逐 shot 一致，说明当前重写路径保持结构和尺度。

## 5. 学习后验结果

相对重加权强度扫描：

| strength | 0 | 0.25 | 0.5 | 0.75 | 1.0 |
|---|---:|---:|---:|---:|---:|
| 码容量 d=3 错误 | 455 | 455 | 455 | **451** | 498 |
| 线路级 d=3 错误 | 64 | **63** | 67 | 74 | 91 |

同配置下 BP 路径的结果：

| decoder | 码容量错误 | 线路级错误 |
|---|---:|---:|
| `bp` | 464 | 185 |
| `bp_gnn` | 496 | **153（−17%）** |

映射质量：

| 配置 | 原始机制 | 分解指令 | 唯一映射 | 无候选 | 最大概率偏差 |
|---|---:|---:|---:|---:|---:|
| 码容量 d=3 | 53 | 53 | 100% | 0 | 0 |
| 线路级 d=3 | 219 | 286 | 91.6% | 24 | 0.0174 |

## 6. 结论

1. 当前实现能够保持 Stim DEM 结构与概率尺度，零强度下与 MWPM 基线逐 shot 一致。
2. 学习后验作为 MWPM 边权修正没有稳定 LER 收益：码容量最优为 455 → 451，线路级为 64 → 63；满强度均变差。
3. 同一份学习后验接入 BP 时，线路级从 185 降到 153（−17%）。逐机制边际的信息可以在 BP 中兑现，在当前 MWPM 边权重接口中不能稳定兑现。
4. 线路级映射覆盖 262/286（91.6%），24 条指令无候选并按零位移处理，64 条通过包含性启发式确定父机制。
5. 逐 shot 重建匹配图约 2.8–2.9 ms/shot，高于完整 BP+GNN 管线约 0.12 ms/shot 的成本。

## 7. 后续工作

- 用 `circuit.explain_detector_error_model_errors()` 与集合求解实现原始机制到分解指令的精确映射。
- 改为一次建图、逐 shot 只更新边权，避免重复解析与建图。
- 将学习目标从逐机制边际改为候选基排序或 OSD-CS。
