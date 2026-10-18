# 文档索引与唯一事实源

- **更新日期**：2026-10-18
- **用途**：说明每个 Markdown 文档的职责、阅读顺序和维护规则，避免同一结论在多个文件里各自演化。

## 1. 唯一事实源

| 内容 | 唯一事实源 | 其他文档怎么写 |
|---|---|---|
| 科学结论、LER、阈值、延迟、统计口径 | `docs/FINAL_REPORT.md` | 只写摘要并链接，不复制完整表格 |
| 未完成任务、优先级、工时估算 | `docs/ROADMAP_TODO.md` §2.2–3 | 只链接，不另排一份任务表 |
| 当前环境、验证入口、已知坑 | `docs/HANDOFF.md` | 可引用命令，但不要改写参数 |
| 本地交付快照与校验值 | `docs/DELIVERY_LOCAL.md` | 只链接 |
| 里程碑实现细节 | `docs/M0`–`M5` | 保留方法与实现，结果摘要链接 FINAL_REPORT |
| BP 算法规范与等价性 | `docs/BP_IMPLEMENTATION.md` | 性能数字优先引用本文 |
| OSD-CS 专题 | `docs/T8_OSD_CANDIDATE_SET.md` | FINAL_REPORT 只做摘要 |
| Union-Find 专题 | `docs/T18_UNION_FIND_ANALYSIS.md` | FINAL_REPORT 只做摘要 |
| 文献元数据 | `docs/references/references.md` | 其他文档只引用 R 编号 |
| 文献综述 | `docs/references/LITERATURE_REVIEW.md` | 不复制完整文献表 |
| PDF 清单 | `docs/references/references_pdfs/README.md` | 由脚本生成 |
| 实验结果 | `results/**` | **除 `results/README.md` 与 `results/m{3,4,5}/README.md` 外均为脚本生成，勿手改** |

## 2. 推荐阅读顺序

1. `README.md`：项目目标、研究问题、模型方案、5 条核心结论。
2. `docs/FINAL_REPORT.md`：完整结果、适用范围、计算成本、未解决问题。
3. `docs/HANDOFF.md`：环境、验证入口、已知坑、当前状态。
4. `docs/ROADMAP_TODO.md`：未完成任务、优先级、工时。
5. `docs/archive/COMPLETED_TASKS.md`：需要历史细节时查看已完成任务。
6. `docs/M0`–`M5`：按里程碑查看实现细节。
7. `docs/T8_OSD_CANDIDATE_SET.md`、`docs/T18_UNION_FIND_ANALYSIS.md`、`docs/BP_IMPLEMENTATION.md`：专题深入。
8. `results/README.md`：结果目录与生成物索引。
9. `docs/references/`：文献综述、完整文献表与 PDF 清单。

## 3. 文档职责

| 文档 | 职责 | 不应包含 |
|---|---|---|
| `README.md` | 项目介绍、快速导航、核心结论 | 完整实验表、任务清单、重复的复现命令 |
| `docs/FINAL_REPORT.md` | 第一阶段技术报告与数字主源 | 逐日任务流水、编辑器操作细节 |
| `docs/ROADMAP_TODO.md` | 未完成任务、优先级、工时与未来展望 | 已完成任务的完整历史叙事 |
| `docs/HANDOFF.md` | 当前环境、验证、坑、下一步 | 重复的任务描述与完整结果表 |
| `docs/DELIVERY_LOCAL.md` | 本地交付快照、校验值、恢复方式 | 重复的决策表与任务表 |
| `docs/archive/COMPLETED_TASKS.md` | T1–T11、T17、T18 的完成历史 | 当前任务状态 |
| `docs/M0`–`M5` | 里程碑实现与实验细节 | 与 FINAL_REPORT 完全相同的完整结果表 |
| `docs/BP_IMPLEMENTATION.md` | BP 算法规范、批量化与等价性 | 项目级交付范围 |
| `docs/T8_OSD_CANDIDATE_SET.md` | OSD-CS 方法与实验 | 其他里程碑的完整背景 |
| `docs/T18_UNION_FIND_ANALYSIS.md` | Union-Find 失效分析与修复 | 其他基线结果 |
| `docs/HARDWARE_REQUIREMENTS.md` | 未来 GPU/云方案 | 第一阶段已完成结果 |
| `results/README.md` | 结果目录索引与生成物说明 | 实验结论 |
| `docs/references/` | 文献综述、元数据、PDF 清单 | 项目实验结论 |

## 4. 维护规则

1. 新数字先写入 `docs/FINAL_REPORT.md`，再在其他文档写摘要和链接。
2. 任务状态只改 `docs/ROADMAP_TODO.md`；完成后的详细叙事追加到 `docs/archive/COMPLETED_TASKS.md`。
3. 决策只改 `docs/ROADMAP_TODO.md` §6.2 与 `docs/HANDOFF.md` §5；`DELIVERY_LOCAL.md` 只记录快照。
4. `results/**/*.md` 除 `results/README.md` 与 `results/m{3,4,5}/README.md` 外由脚本生成；需要改口径时改生成脚本并重跑，不手工编辑结果表。
5. 新增 Markdown 文件时，同步更新本索引。
