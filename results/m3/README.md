# M3 结果目录索引

| 路径 | 内容 |
|---|---|
| `SUMMARY.md` / `sweep.csv` | 自动汇总（迁移评测矩阵、机制后验标定、逐次运行明细），由 `scripts/summarize_m3.py` 生成 |
| `figures/` | 5 张图：噪声外推、码距外推、LER–延迟 Pareto、LER–一致性 Pareto、强度重标定，由 `scripts/plot_m3_results.py` 生成 |
| `m3_learned_basis_repetition_circuit_level_d3__d3__circuit_level__p0p01/` | 同分布 headline（d=3, p=0.01, 32768 shots，含 `model_state.pt`） |
| `m3_..._from_d3__to_d3__circuit_level__p0p*/` | 噪声外推（p=0.003 / 0.005 / 0.008 / 0.02，各 32768 shots） |
| `m3_transfer_d3_to_d5_8192shots/` | 码距外推（d=3 训练 → d=5，8192 shots） |
| `m2_learned_basis_repetition_circuit_level_d5_eval/` | M2 遗留的 d=5 评测补跑（用 M2 保存的 d=5 checkpoint） |
| `FAILURE_ANALYSIS.md` / `failure_analysis.json` | OSD-0 回退的逐 shot 归因 + McNemar 配对检验（p=0.01） |
| `FAILURE_ANALYSIS_p0p003.md` / `failure_analysis_p0p003.json` | 失效区（p=0.003）的同一套归因与配对检验 |
| `OSD_TRIGGER_POLICY.md` / `osd_trigger_policy.json` | OSD-0 触发阈值扫描（d=3，LER–一致性 Pareto） |
| `OSD_TRIGGER_POLICY_D5.md` / `osd_trigger_policy_d5.json` | 同一扫描在 d=5 上的复现 |
| `recal_lowp/`、`recal_highp/`、`recal_d5/` | 先验强度重标定（目标分布验证集选强度后重测） |
| `logs/` | 各后台任务的 stdout/stderr |

设计与结论说明见 `docs/M3_HYBRID_DECODER.md`。
