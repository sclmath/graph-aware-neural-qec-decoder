# M3 修正后重跑结果索引（`results/m3_fixed/`）

本目录是 `docs/BP_CORRECTNESS_FIX.md` 所述修正之后重跑的 M3 结果，与 `results/m3/`（修正前）**并存**，便于直接对照。

| 路径 | 内容 |
|---|---|
| `m3_learned_basis_repetition_circuit_level_d3__d3__circuit_level__p0p01/` | 同分布 headline（含修正后的 `model_state.pt`） |
| `..._from_d3__to_d3__circuit_level__p0p*/` | 噪声外推（p=0.003/0.005/0.008/0.02，各 32768 shots） |
| `..._from_d3__to_d5__circuit_level__p0p01/` | 跨码距迁移（repetition d=3 → d=5，8192 shots） |
| `m2_d5_eval_fixed/` | M2 遗留的 d=5 同分布评测（修正后） |
| `FAILURE_ANALYSIS.md` / `failure_analysis.json` | OSD-0 回退的逐 shot 归因 + McNemar（修正后） |
| `recal_lowp/`、`recal_highp/` | 先验强度重标定（修正后：验证集扫描几乎平坦，说明修正前的"有害区间"是缺陷产物） |
| `SUMMARY.md` / `sweep.csv` | 自动汇总 |

**修正后的核心结论**：d=3 repetition 上学习先验无显著收益（`bp` 0.00943 vs `bp_gnn` 0.00952，z=-0.77, p=0.44）；d=5 上收益巨大（d=3 训练模型迁移到 d=5：0.05078 → 0.01709，-66%）。
