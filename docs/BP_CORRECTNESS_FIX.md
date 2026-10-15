# BP 正确性修正（M5 前置）：两个标量实现缺陷及其对 M1–M3 结论的影响

日期：2026-10-13（晚）
影响范围：`src/graph_qec/decoders/bp.py`、所有 BP 系解码器结果（M1/M2/M3 的 `bp`、`bp_osd`、`bp_gnn`、`bp_gnn_osd`、`osd_gnn`）

## 1. 背景

本轮为了做 M4（表面码 + HGP）与大码距 sweep，发现标量 BP 实现约 10–20 ms/shot，无法支撑 32768-shot × 多解码器的实验。于是写了逐 shot 向量化的等价实现（`src/graph_qec/decoders/bp_engine.py`），并用「引擎 vs 标量」逐 shot 一致性测试来锁死语义。**一致性测试立刻失败**，追查后确认是标量实现的两个缺陷，而不是引擎的问题。

## 2. 缺陷一：check-to-variable 消息没有把自己排除干净

标量实现（修正前）：

```python
magnitudes = np.abs(incoming)
order = np.argsort(magnitudes, kind="stable")
smallest = int(order[0])
min_excluding = magnitudes.copy()
min_excluding[smallest] = magnitudes[int(order[1])]      # 只修了 argmin 那一项
new_messages = self.min_sum_scaling * signs_excluding * min_excluding
```

对除 argmin 之外的位置，`min_excluding[j]` 仍然是 `|m_j|` 本身，也就是**把变量自己的幅度原样回传**（标准 min-sum 要求 `min_{k≠j}|m_k|`）。后果：

- 度 2 的 check 上两条消息幅度都等于 `max(|m_0|,|m_1|)`，等于把「最大值」灌回去，形成自增强；
- 度 ≥3 的 check 上更是完全偏离 min-sum；
- 与教科书写法在随机消息上**15% 的条目不一致**（最大偏差 ~2.0 LLR）。

修正：

```python
min1 = float(magnitudes[smallest]);  min2 = float(magnitudes[int(order[1])])
min_excluding = np.full_like(magnitudes, min1)
min_excluding[smallest] = min2        # 其余位置一律用全局最小
```

## 3. 缺陷二：先验覆盖没有进入后验

`_decode_shot(syndrome, prior_llr=...)` 只在初始化 variable-to-check 消息时用了 `prior_llr`，后验却写死成 DEM 先验：

```python
posterior = self.prior_llr.copy()      # 修正前：忽略 prior_llr 覆盖
```

修正：

```python
posterior = prior_log_odds.copy()      # 修正后：使用有效先验
```

这正是 M2 的「学习先验」路径：学习到的 LLR 只影响第一轮消息，不影响判决所依据的后验。缺陷一和缺陷二叠加，恰好让 `bp_gnn` 在**已经失真的**基线上看起来改善了 20%。

## 4. 修正前后的直接对比（repetition d=3，circuit-level p=0.01，32768 test shots）

| decoder | 修正前 logical errors (LER) | 修正后 logical errors (LER) |
|---|---:|---:|
| mwpm | 217 (0.00662) | 217 (0.00662) |
| bp | 404 (0.01233) | **309 (0.00943)** |
| bp_osd | 407 (0.01242) | 331 (0.01010) |
| bp_gnn | 323 (0.00986) | 312 (0.00952) |
| bp_gnn_osd | 407 (0.01242) | 333 (0.01016) |
| bp_gnn_osd_learned_order | 403 (0.01230) | 317 (0.00967) |
| osd_gnn | 495 (0.01511) | 319 (0.00974) |

> 两列的数字**来自不同的标签集**（同一批 test shots、同一 DEM），可直接比较；MWPM 不受影响，是天然的对照。

## 5. 对结论的影响（必须如实记录）

1. **M2 的核心主张不成立**。修正前「学习先验使 BP 的 LER 降低 20%（0.01233 → 0.00986）」是解码器缺陷的产物。修正后 `bp` 0.00943 vs `bp_gnn` 0.00952，配对检验 **6 修好 / 9 弄坏，z = -0.77，p = 0.44**——**没有可测收益**。
2. **「低于训练噪声率时学习先验转为有害」也不成立**（M3 第 5 节的失败边界是假的）。修正后 d=3 的噪声外推：

   | 目标 p | mwpm | bp | bp_osd | bp_gnn | bp_gnn_osd |
   |---:|---:|---:|---:|---:|---:|
   | 0.003 | 27 | 34 | 35 | **32** | 37 |
   | 0.005 | 57 | 87 | 94 | **85** | 91 |
   | 0.008 | 159 | 197 | 209 | **194** | 207 |
   | 0.020 | 837 | 1129 | 1258 | **1122** | 1192 |
   （逻辑错误数，各 32768 shots）——每个噪声率上 `bp_gnn` 都**略好**，量级 0–3%，全部在噪声内，且不再有灾难性劣化。强度重标定也随之失效：p=0.003 的验证集扫描在 s=0/0.25/0.5/0.75/1.0 上给出 19/19/19/19/19 个错误（修正前为 21/21/19/19/48）。
3. **d=5 上学习先验仍然有效，而且是大幅有效**。修正后 d=3 训练的模型直接迁移到 repetition d=5 p=0.01：`bp` 0.05078 (416) → `bp_gnn` **0.01709 (140)，-66%**；配对/规模上远超噪声。这与 d=3 的零收益形成清晰对照：**DEM 越大、越退化，BP 自身越弱，学习先验越有价值**；在 d=3 上正确 BP 已经接近 MWPM，学习先验无从发挥。
4. **OSD-0 回退仍然有害**：修正后 d=3 上 `bp_gnn` 0.00952 → `bp_gnn_osd` 0.01016（67 救 / 88 伤，z=-1.69, p=0.09），d=5 传递场景同样变差（0.01709 → 0.02356）。M3 关于「一致性不免费」的定性结论保留，但显著性从 z=-6.13 降到 z=-1.69。
5. **「学习 logits 用于 OSD 排序」现在有微弱正收益**：d=3 上 `bp_gnn_osd_learned_order` 相对 `bp_gnn_osd` 为 33 修好 / 17 弄坏（z=2.26, p=0.023）。
6. **性能提升约两个数量级**：d=3 repetition 从 205 µs/shot 降到 ~1.9 µs/shot（约 107×），surface d=3 circuit-level 从 18.5 ms/shot 降到 0.54 ms/shot（约 34×）。整条 M3 headline 管线从 259 s 降到 55 s。这直接解除了 M4/M5 大样本 sweep 的算力瓶颈。

## 6. 现在的正确性保障

- `src/graph_qec/decoders/bp_engine.py`：逐 shot 向量化的 normalized min-sum（含自适应 shot 切块与收敛 shot 的压缩），是 `decode_batch` 的唯一实现；
- `BPDecoder._decode_shot` 保留为标量参考实现，`tests/test_batched_bp.py` 断言两者在 corrections / iterations / converged / syndrome_distance 上**逐 shot 完全一致**，后验 LLR 在 1e-12 内一致（高 check 度时浮点求和顺序不同，偏差 ~1e-15）；
- 同一测试文件还固定了 min-sum 的自排除语义（度 3 check 上最大幅度不得回传给自身）与度 1 check 的 20× 上限；
- `tests/test_batched_bp.py::test_batched_osd_fallback_restores_syndrome_consistency` 保证 OSD 回退仍然给出满足 syndrome 的 correction。

## 6.1 M1 基线也被修正（repetition，4096 shots）

| 场景 | decoder | 修正前 | 修正后 |
|---|---|---:|---:|
| d=3 circuit-level | mwpm | 0.00952 (39) | 0.00952 (39) |
| d=3 circuit-level | union_find | 0.01294 (53) | 0.01294 (53) |
| d=3 circuit-level | bp | 0.01587 (65) | **0.01294 (53)** |
| d=3 circuit-level | bp_osd | 0.01782 (73) | **0.01489 (61)** |
| d=3 code-capacity | bp | 0.00073 (3) | **0.00049 (2)**，与 MWPM 相同 |

修正后 BP 在 circuit-level 上从"比 Union-Find 差 23%"变成**与 Union-Find 打平**，在 code-capacity 上与 MWPM 完全一致。修正后的 M1 结果在 `results/m1_fixed/`，修正前在 `results/m1/`。

## 7. 修正后的结果落在哪里

| 目录 | 内容 |
|---|---|
| `results/m3_fixed/` | 修正后重跑的 M3 headline、噪声外推 4 点、d3→d5 传递、强度重标定、失效归因（与 `results/m3/` 的修正前版本并存，便于对照） |
| `results/m4/`、`results/m4_surface/`、`results/m4_hgp/` | M4 表面码与 HGP 的结果（全部使用修正后的解码器） |

`results/m3/`、`results/m2/` 中的数字是**修正前**的，只应作为历史对照；`docs/M2_GNN_REWEIGHTING.md` 与 `docs/M3_HYBRID_DECODER.md` 顶部已加注说明。
