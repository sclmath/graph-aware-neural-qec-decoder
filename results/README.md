# 结果目录

本目录保存当前版本实验的原始运行记录、汇总表与图表。目录中的多数 Markdown 由脚本生成；正式结论和统计口径以 [`docs/FINAL_REPORT.md`](../docs/FINAL_REPORT.md) 为准，复现命令见 [`docs/REPRODUCIBILITY.md`](../docs/REPRODUCIBILITY.md)。只有进入技术报告或人工索引的当前汇总才作为正式结果引用。

## 人工维护的索引

- 本文件
- [`m3/README.md`](m3/README.md)
- [`m4/README.md`](m4/README.md)
- [`m5/README.md`](m5/README.md)

除上述文件外，`results/**/*.md` 均由脚本生成，请勿手工编辑。需要改变统计口径时，应修改生成脚本并重跑。

## 目录导航

| 目录 | 内容 | 主要生成入口 |
|---|---|---|
| `m1/` | 经典基线 benchmark | `graph_qec.m1` |
| `m2/` | GNN 重加权 headline 与多种子 | `graph_qec.m2`、`scripts/summarize_m2.py` |
| `m3/` | 混合解码器、噪声/码距迁移、失败分析 | `graph_qec.m3`、`scripts/summarize_m3.py` |
| `m4/` | 表面码基线、图结构、阈值 | `scripts/m4_surface_sweep.py`、`scripts/threshold_estimate.py` |
| `m4_surface/`、`m4_surface_cc/`、`m4_hgp/` | 表面码与 HGP 的学习重加权和迁移 | `graph_qec.m4`、`scripts/m4_transfer.py` |
| `m5/` | CPU 工程性能、GNN 优化、量化、MWPM 对照 | `scripts/engineering_table.py` 等 |
| `t8/` | OSD-CS 探针与多种子汇总 | `scripts/t8_*` |
| `t9/` | 图特征与候选规模消融 | `scripts/t9_*` |
| `t10/` | 表面码多噪声率、多码距多种子汇总 | `scripts/t10_multiseed_stats.py` |
| `logs/` | 运行日志 | 各驱动脚本 |
| `smoke/` | 端到端 smoke 临时产物（不入库） | `scripts/run_all.ps1` |

## 优先阅读的汇总文件

- [`m2/HEADLINE_MULTISEED.md`](m2/HEADLINE_MULTISEED.md)：repetition d=3 旗舰表的多种子结果。
- [`m2/SUMMARY.md`](m2/SUMMARY.md)：M2 运行汇总。
- [`m3/FAILURE_ANALYSIS.md`](m3/FAILURE_ANALYSIS.md)：M3 失败模式归因。
- [`m4/THRESHOLD.md`](m4/THRESHOLD.md)：阈值估计。
- [`m5/ENGINEERING_TABLE.md`](m5/ENGINEERING_TABLE.md)：CPU 工程性能表。
- [`t8/D7_MODEL_SEEDS.md`](t8/D7_MODEL_SEEDS.md)：d=7 OSD-CS 模型种子口径。
- [`t9/SURFACE_D3_MULTISEED.md`](t9/SURFACE_D3_MULTISEED.md)：表面码 d=3 消融多种子汇总。
- [`t10/MULTISEED.md`](t10/MULTISEED.md)：关键 surface-code 结论的多种子统计。

## 生成与校验规则

1. 新实验先写配置，再产生原始 JSON/CSV，最后由汇总脚本生成 Markdown。
2. 文件名相同的 `SUMMARY.md`、`STUDY.md`、`ABLATION.md` 是不同运行的模板化输出，不代表内容重复。
3. 图表与表格必须能由仓库内脚本重建；无法重建的中间文件不应作为正式证据。
4. 提交前检查生成文件 diff，确认只是预期配置或统计口径变化带来的差异。
