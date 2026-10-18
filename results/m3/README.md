# M3 结果目录索引（`results/m3/`）

| 路径 | 内容 |
|---|---|
| `m3_learned_basis_repetition_circuit_level_d3__d3__circuit_level__p0p01/` | 同分布 headline（含 `model_state.pt`） |
| `..._from_d3__to_d3__circuit_level__p0p*/` | 噪声外推（p=0.003/0.005/0.008/0.02，各 32768 shots） |
| `..._from_d3__to_d5__circuit_level__p0p01/` | 跨码距迁移（repetition d=3 → d=5，8192 shots） |
| `m2_d5_eval/` | repetition d=5 的同分布评测（使用 M2 保存的 d=5 checkpoint，4096 shots） |
| `FAILURE_ANALYSIS.md` / `failure_analysis.json` | OSD-0 回退的逐 shot 归因 + McNemar 配对检验 |
| `OSD_TRIGGER_POLICY.md` / `osd_trigger_policy.json` | OSD-0 触发阈值扫描（LER–一致性权衡） |
| `recal_lowp/`、`recal_highp/` | 先验强度在目标分布验证集上的重标定 |
| `SUMMARY.md` / `sweep.csv` | 自动汇总（`scripts/summarize_m3.py`、`scripts/plot_m3_results.py`） |
| `figures/` | 5 张图：噪声外推、码距外推、LER–延迟 Pareto、LES–一致性权衡、强度重标定 |

> 方法与结论见 `docs/M3_HYBRID_DECODER.md`；完整数字以 `docs/FINAL_REPORT.md` 为准。本文件只做目录导航。
