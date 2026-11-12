# 文档索引与维护规则

- **更新日期**：2026-11-12
- **用途**：说明文档职责、唯一事实源、推荐阅读顺序和生成物边界，避免同一内容在多个文件里重复演化。

## 1. 唯一事实源

| 内容 | 唯一事实源 | 其他文档怎么写 |
|---|---|---|
| 项目概览、能力边界、快速入口 | `README.md` | 只做简短摘要 |
| 科学结论、LER、阈值、延迟、统计口径 | [`FINAL_REPORT.md`](FINAL_REPORT.md) | 只摘要并链接，不复制完整表格 |
| 环境、安装、测试、全量实验命令 | [`REPRODUCIBILITY.md`](REPRODUCIBILITY.md) | 只给最短入口，不另维护命令清单 |
| 当前限制、证据缺口、未来方向 | [`ROADMAP.md`](ROADMAP.md) | 只链接，不再维护第二份计划 |
| 里程碑实现细节 | `M0`–`M5` 文档 | 保留方法与实现，结果统一链接技术报告 |
| BP 算法规范 | [`BP_IMPLEMENTATION.md`](BP_IMPLEMENTATION.md) | 性能数字优先引用技术报告或本文 |
| OSD-CS 专题 | [`OSD_CANDIDATE_SET.md`](OSD_CANDIDATE_SET.md) | 技术报告只做摘要 |
| 加权 Union-Find | [`UNION_FIND.md`](UNION_FIND.md) | 技术报告只做摘要 |
| MWPM 边权重重加权 | [`MWPM_REWEIGHTING.md`](MWPM_REWEIGHTING.md) | 技术报告只做摘要 |
| 文献元数据 | [`references/references.md`](references/references.md) | 其他文档只引用 R 编号 |
| 文献综述 | [`references/LITERATURE_REVIEW.md`](references/LITERATURE_REVIEW.md) | 不复制完整文献表 |
| PDF 下载清单 | [`references/references_pdfs/README.md`](references/references_pdfs/README.md) | 由脚本生成 |
| 实验结果与生成物 | `results/**` | 除人工 `README.md` 外均由脚本生成，不手改 |
| 许可证 | [`../LICENSE`](../LICENSE) | README 只提供摘要和链接 |

## 2. 推荐阅读顺序

1. [`README.md`](../README.md)：项目定位、当前实现、快速开始和核心发现。
2. [`FINAL_REPORT.md`](FINAL_REPORT.md)：完整方法、结果、适用范围、计算成本和开放问题。
3. [`REPRODUCIBILITY.md`](REPRODUCIBILITY.md)：环境、测试、实验和结果再生成。
4. [`ROADMAP.md`](ROADMAP.md)：当前限制与后续研究方向。
5. [`M0`](M0_ENVIRONMENT_AND_DATA_PIPELINE.md)–[`M5`](M5_ENGINEERING.md)：按里程碑查看实现细节。
6. [`BP_IMPLEMENTATION.md`](BP_IMPLEMENTATION.md)、[`OSD_CANDIDATE_SET.md`](OSD_CANDIDATE_SET.md)、[`UNION_FIND.md`](UNION_FIND.md)、[`MWPM_REWEIGHTING.md`](MWPM_REWEIGHTING.md)：专题深入。
7. [`results/README.md`](../results/README.md)：结果目录、人工索引与生成物边界。
8. [`references/`](references/)：文献综述、元数据与 PDF 清单。

## 3. 文档职责

| 文档 | 职责 | 不应包含 |
|---|---|---|
| `README.md` | 公开入口、能力边界、快速开始、核心发现摘要 | 完整实验结果表、长跑命令、本地机器状态 |
| `docs/FINAL_REPORT.md` | 正式技术报告与数字主源 | 逐日开发流水、机器专属路径 |
| `docs/REPRODUCIBILITY.md` | 环境、命令、长跑与结果再生成 | 科学结论的完整论证 |
| `docs/ROADMAP.md` | 限制、证据缺口、未来方向与贡献入口 | 已完成任务的流水账 |
| [`M0`](M0_ENVIRONMENT_AND_DATA_PIPELINE.md)–[`M5`](M5_ENGINEERING.md) | 里程碑目标、实现和关键决策 | 与其他文档重复的完整结果表 |
| `docs/BP_IMPLEMENTATION.md` | BP 定义、批量化、正确性与性能 | 项目级交付范围 |
| `docs/OSD_CANDIDATE_SET.md` | OSD-CS 方法与当前结果 | 其他专题的完整背景 |
| `docs/UNION_FIND.md` | 加权 Union-Find 算法与当前结果 | 其他基线结果 |
| `docs/MWPM_REWEIGHTING.md` | 学习后验与 MWPM 边权重 | 其他专题的完整背景 |
| `results/**/README.md` | 结果目录导航与生成口径 | 新科学结论 |
| `docs/references/` | 文献综述、元数据、BibTeX 与 PDF 清单 | 项目实验结论 |

## 4. 维护规则

1. 新科学数字先写入 `docs/FINAL_REPORT.md`，再同步 README 摘要；其他文档不得各自演化数字。
2. 新命令或参数只写入 `docs/REPRODUCIBILITY.md`；其他文档只链接。
3. 新计划、限制或未来方向只写入 `docs/ROADMAP.md`。
4. `results/**/*.md` 除人工 `README.md` 外由脚本生成。需要改口径时修改生成脚本并重跑，不手改生成结果。
5. 新增人工维护的 Markdown 文件时，同步更新本索引；临时交接、机器快照和内部排期不进入公开文档树。
6. 提交前至少执行一次链接检查与 `pytest -q`；涉及结果图表的改动还需重跑对应生成脚本并检查 diff。
