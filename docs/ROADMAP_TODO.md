# ROADMAP / TODO：未完成内容盘点与工期估算

- **盘点日期**：2026-10-15
- **仓库状态**：本地 git 已初始化（分支 `main`，暂无远程）
- **已完成基线**：M0、M1、M2 完成；M3、M4 主体完成；M5 工程化完成；`pytest` **57 项全过**（8.8 s）
- **机器现状**：Intel i5-12400（6C/12T）/ 16 GB / **CPU-only torch**（`torch.cuda.is_available() == False`）
- **估算前提**：1 名熟悉本仓库的研究者；**编码工时（人日）与算力壁钟（天）分列**；`+GPU` 表示需另配 1×24 GB 设备
- **总量**：P0+P1（核心）约 **31-44 人日**；含 P2/P3 全部非研究项约 **63-93 人日**（不含 `A8`）

> 用法：完成一项后勾选复选框，并把产物路径补到该项的「验收」行。**未验证的结论不得写入报告**。

---

## 0. 已完成基线（不重复计入工期）

| 里程碑 | 状态 | 主要产出 |
|---|---|---|
| M0 环境与数据链路 | 完成 | `artifacts/m0/`、`docs/M0_ENVIRONMENT_AND_DATA_PIPELINE.md` |
| M1 经典基线 | 完成（BP 数字已被修正后重跑取代） | `results/m1_fixed/`、`docs/M1_BASELINE_DECODERS_AND_BENCHMARK.md` |
| M2 GNN 重加权 | 完成（先验收益结论经 BP 修正后收窄） | `results/m2/`、`docs/M2_GNN_REWEIGHTING.md` |
| M3 混合解码器 | 主体完成（含 BP 缺陷修正与全量重跑） | `results/m3_fixed/`、`docs/M3_HYBRID_DECODER.md` |
| M4 表面码 + HGP | 主体完成 | `results/m4*/`、`docs/M4_HGP_AND_SURFACE.md` |
| M5 工程优化 | 工程侧完成（GPU 项受硬件限制未做） | `results/m5/`、`docs/M5_ENGINEERING.md`、`docs/M5_DECOMPOSED_MWPM.md` |
| 向量化 BP | 完成（约 100x 加速 + 两个正确性缺陷修正） | `src/graph_qec/decoders/bp_engine.py`、`docs/BP_CORRECTNESS_FIX.md` |

---

## 1. 未完成清单

### A. 科学实验缺口（主线）

- [ ] **A1 · d=5 线路级与 d=7 的学习重加权 + LER-延迟 Pareto**　（P1）
  - 依据：`README.md` 第 9 节「待补」；`docs/M4_HGP_AND_SURFACE.md` 第 8 节第 2 条
  - 现状：表面码线路级只做了 d=3（`results/m4_surface/`）；d=5 只有基线扫描与码容量迁移；d=7 完全缺失
  - 依赖：B2（无 GPU 时必须削减 test shots，并如实标注统计力不足）
  - 工作量：编码 1-2 人日；算力 +GPU 1-2 d / 纯 CPU 5-10 d
  - 验收：`results/m4_surface/` 补齐 d=5/d=7 的 `bp` vs `bp_gnn` 对照表 + `pareto_ler_latency` 图

- [ ] **A2 · 阈值估计（threshold）**　（P1）
  - 依据：`README.md` 8.1「阈值估计」；当前仅有 LER-p 曲线，无码距交叉拟合
  - 依赖：A1
  - 工作量：编码 0.5 人日；算力并入 A1
  - 验收：`results/m4/threshold.md` + 阈值拟合图（含拟合区间与置信说明）

- [ ] **A3 · OSD 候选集学习：OSD-λ / OSD-CS / learning-to-rank**　（P1）
  - 依据：`docs/M2_GNN_REWEIGHTING.md` 第 8 节、`docs/M3_HYBRID_DECODER.md` 第 11 节、`docs/M4_HGP_AND_SURFACE.md` 第 8 节第 5 条
  - 现状：只有 OSD-0；三条独立证据链（M2 排序 +22%、M3 无 Pareto 窗口、M5 MWPM 边权无收益）都指向「学习目标应从逐机制边际改为候选基质量」
  - 依赖：无（纯自研）
  - 工作量：编码 8-12 人日；算力 1-2 d
  - 验收：新增 decoder 名称 + 单测 + 与 `bp`/`bp_gnn`/`bp_gnn_osd` 的配对检验表
  - 备注：**全项目最高性价比的未做实验**，建议在 B2 之后立刻排期

- [ ] **A4 · 真正的零样本迁移（移除边特征中的 p）**　（P2）
  - 依据：`docs/M3_HYBRID_DECODER.md` 第 6 节「口径说明」
  - 工作量：编码 2 人日；算力 1 d
  - 验收：`results/m3_fixed/zero_shot/`（无 p 特征模型的跨噪声率对照）

- [ ] **A5 · 多噪声率训练课程**　（P2）
  - 依据：`docs/M3_HYBRID_DECODER.md` 第 11 节第 3 条
  - 工作量：编码 1-2 人日；算力 1 d
  - 验收：p 在 [0.003, 0.02] 混合训练 vs 单点训练的对照表

- [ ] **A6 · 多种子统计稳健性（不少于 3 个 seed）**　（P1）
  - 依据：现有结论多为单种子（`seed20261003`）；`results/m5/gnn_mwpm_decomposed_*` 的「451 vs 455」、HGP 的「-3%」均落在噪声内
  - 依赖：A1 的算力预算
  - 工作量：编码 1 人日；算力 +GPU 3-4 d / 纯 CPU 1-2 周
  - 验收：对 3-4 个最关键结论给出多种子均值 ± 标准误与配对检验

- [ ] **A7 · 时序编码器（syndrome history 的 1D 卷积 / 轻量 Transformer）**　（P3）
  - 依据：`README.md` 5.3 明确要求；全仓无任何 `conv1d` / 序列模型实现
  - 工作量：编码 10-15 人日；算力 2-3 d
  - 验收：模型、训练脚本、有/无时序编码器消融表

- [ ] **A8 · 端到端 / 可微 BP**　（P3，研究性，不计入总量）
  - 依据：`docs/M2_GNN_REWEIGHTING.md` 第 8 节下一步第 3 条
  - 工作量：15-20 人日；结果高度不确定，**建议不纳入承诺排期**

- [ ] **A9 · HGP 更换实用种子码 + 表面码到 HGP 的同噪声跨族迁移**　（P2）
  - 依据：`docs/M4_HGP_AND_SURFACE.md` 第 8 节第 5 条
  - 工作量：编码 3-5 人日；算力 1-2 d
  - 验收：不少于 3 个 HGP 码的参数字与跨族迁移对照

- [ ] **A10 · 结构化量子 LDPC（非 HGP）支持**　（P3）
  - 依据：`README.md` 3.1 列出该码族；`src/graph_qec/codes/` 目前只有 `hgp.py`
  - 工作量：编码 10-15 人日（可复用 `hgp.py` 的 GF(2)/CSS 工具）；算力 2-3 d
  - 验收：至少 1 个非 HGP 的 qLDPC 码走通 BP / BP+GNN 全链路

- [ ] **A11 · 消融补全：图特征组合 + top-k 候选规模**　（P1）
  - 依据：`README.md` 7.2 列出 7 类消融，当前仅「有/无 GNN」「有/无 OSD」「浮点/量化」有数据
  - 依赖：A3（top-k 需要候选集机制）、B2（CPU/GPU 消融）
  - 工作量：编码 3 人日；算力 1 d

- [ ] **A12 · 补噪声率 p = 0.001 / 0.002**　（P0）
  - 依据：`README.md` 3.2 列出 0.001-0.01；实际扫描为 0.003-0.02
  - 工作量：编码 0.2 人日；算力 0.2 d

### B. 工程与性能缺口

- [ ] **B1 · GNN 前向优化（当前 166 µs/shot，已是全管线瓶颈）**　（P0）
  - 依据：`docs/M5_ENGINEERING.md` 第 3 节结论——向量化后 BP 仅 1.9 µs/shot，瓶颈转移到 GNN
  - 手段：`index_select` + 预分配缓冲、减少逐边 MLP、消息传递改稀疏矩阵乘
  - 工作量：编码 2-3 人日；算力 0.5 d；预期 3-10 倍
  - 验收：`results/m5/GNN_PERF.md`（优化前后 µs/shot + 端到端管线延迟）

- [ ] **B2 · GPU 批处理（全项目瓶颈项）**　（P0）
  - 依据：`docs/M5_ENGINEERING.md` 第 4 节；本机 `torch.cuda.is_available() == False`
  - 内容：`bp_engine` 活动集合切片改 `torch.Tensor`、边聚合改 `index_add_`/`torch.sparse`；GNN 改 `device=`；量化迁 `torchao`
  - 依赖：**需先解决 GPU 获取**（决策项 D1）；A1/A2/A6/B5 全部压在它后面
  - 工作量：编码 8-12 人日；算力 1-2 d（含环境）
  - 验收：`docs/M5_GPU.md`——CPU/GPU 延迟与吞吐对照 + 等价性测试（与 NumPy 引擎逐 shot 一致）

- [ ] **B3 · 精确的原始与分解机制对应 + 每边一次建图**　（P2）
  - 依据：`docs/M5_DECOMPOSED_MWPM.md` 第 6 节第 1-2 条
  - 现状：映射覆盖 262/286（91.6%）靠启发式；逐 shot 重建匹配图 2.8-2.9 ms/shot
  - 工作量：编码 5-8 人日；算力 0.5 d
  - 备注：PyMatching 2.4 公开接口不支持只换边权（`decode(z, weights=...)` 被静默忽略），需走 `MatchingGraph` / `decode_to_edges_array` 或自实现

- [ ] **B4 · 量化 API 迁移（`torch.ao.quantization` 改 `torchao`）**　（P2）
  - 依据：`docs/M5_ENGINEERING.md` 第 4 节第 3 条（现 API 已 deprecated，2026-10 后移除）
  - 工作量：编码 1-2 人日（并入 B2 一并做）

- [ ] **B5 · 完整工程性能表**　（P1）
  - 依据：`README.md` 8.2 要求单 shot 延迟 / batch throughput / CPU-GPU / 峰值内存与显存 / BP 迭代 / OSD 候选规模 / 参数量
  - 依赖：B2（GPU 项）
  - 工作量：编码 2 人日；算力 0.5 d
  - 验收：`results/m5/ENGINEERING_TABLE.md`（缺失项须显式标注「不可测 + 原因」）

### C. 交付物与仓库工程

- [x] **C1 · 初始化 git 仓库 + 忽略策略**　（P0，2026-10-15 完成）
  - 产出：`git init -b main`、`.gitignore`、`.gitattributes`
  - 决策：`results/`、`artifacts/` **入库**（实测仅 2.13 MB / 0.02 MB，无需 LFS）；`docs/references/references_pdfs/*.pdf` **不入库**（129.7 MB，第三方版权，可由 `scripts/download_references.py` 重建）
  - 待办：`LICENSE` 尚未确定（见决策项 D3）

- [ ] **C2 · CI（GitHub Actions 跑 57 项测试）**　（P0）
  - 工作量：编码 0.5 人日
  - 验收：`.github/workflows/ci.yml` 首次运行通过

- [ ] **C3 · 文档同步**　（P0）
  - 具体过时项：`docs/HARDWARE_REQUIREMENTS.md` 开头仍称「仓库当前尚未包含可运行代码」；`README.md` 第 9 节仍写「M4 进行中」；`results/m4_surface/` 缺 `SUMMARY.md`（其他结果目录都有）
  - 工作量：编码 1 人日
  - 验收：三项均已修正，且 README 进度段与各里程碑文档结论一致

- [ ] **C4 · 最终技术报告（集成 M0-M5 + 局限性 + 复现说明）**　（P1）
  - 依据：`README.md` 交付物「技术报告与局限性说明」、完成标准第 5 条
  - 工作量：3-5 人日；依赖主线收敛（A3/A6/C3）
  - 验收：`docs/FINAL_REPORT.md`，含适用范围、计算成本、未解决问题三节

- [ ] **C5 · 一键复现总脚本 + 端到端 smoke**　（P0）
  - 现状：`scripts/run_m3_*.ps1`、`run_m4_m5_sequence.ps1` 为分段脚本，无总入口
  - 工作量：编码 1-2 人日；算力 0.5 d
  - 验收：`scripts/run_all.ps1` 在小规模模式下全绿

---

## 2. 工时汇总

| 层次 | 编号 | 人日 | 算力壁钟 | 说明 |
|---|---|---|---|---|
| **P0 先做（无外部依赖或阻塞他项）** | B1、B2、A12、C2、C3、C5 | 12.7-18.7 | 1-3 d | B2 需先解决设备 |
| **P1 论文核心必做** | A1、A2、A3、A6、A11、B5、C4 | 18.5-25.5 | 5-9 d（+GPU） | 决定叙事完整性 |
| **P0+P1 小计** | | **31-44** | 约 6-12 d | 单人 **1.5-2 个月**（GPU 到位） |
| P2 强化叙事 | A4、A5、A9、B3、B4 | 12-19 | 2.5-4 d | |
| P3 扩展/可选 | A7、A10 | 20-30 | 4-6 d | |
| **全部非研究项合计** | | **63-93** | | 单人 **3-4.5 个月** |
| 研究性（不计入） | A8 | 15-20 | 不确定 | 高风险 |

> 更正记录：初次口头估算（2026-10-15）给出「52-76 人日」，为分档口算偏乐观所致；逐项求和后修正为 **63-93 人日**。差异集中在 C4（3-5）、B3（5-8）、A7（10-15）、A10（10-15）。

**无 GPU 的影响**：A1 / A2 / A6 / B5 的算力壁钟将从约 6-12 d 膨胀到 **3-5 周**（表面码线路级 d=5 的 BP 实测 11.9 ms/shot，d=7 按边数外推约 40-80 ms/shot）。

---

## 3. 关键路径与依赖

```
[关键路径]
决定 GPU 方案 --> B2 GPU 批处理 --> A1 d=5/d=7 学习重加权 --> A2 阈值
                        |--> B5 工程性能表
                        |--> A6 多种子稳健性

[可并行且无依赖]
B1 GNN 前向优化 --+
C2 CI ------------+
C3 文档同步 ------+--> 均可在第 1 周完成
C5 一键复现 ------+
A12 补 p 点 ------+

[主线叙事]
A3 OSD 候选集学习 / learning-to-rank --> A11 消融 --> C4 最终报告
```

**GPU 决策项（P0，需拍板）**，三种走法：
1. 租云 GPU 实例（`docs/HARDWARE_REQUIREMENTS.md` 第 6 节已有云部署方案）——不占本地预算，按需付费；
2. 本机维持 CPU-only：接受 3-5 周算力壁钟，并把 A1/A2/A6 明确标注为「小样本、统计力不足」；
3. 把 GPU 项整体移出范围，报告里如实写为限制（当前 M5 已是这种处理）。

---

## 4. 风险

| 风险 | 影响 | 应对 |
|---|---|---|
| **B2 无法落地** | A1/A2/A6/B5 全部停摆，报告只能声明 d=7 不可及 | 先做决策项 D1，或转向「CPU 可及范围内把统计力做扎实」（A6 + A3） |
| **统计功效不足被当成结论** | 审阅者可直接否掉 M4/M5 的百分比结论 | A6 优先于 A7/A10 等新功能 |
| **主线叙事缺 A3** | 「学习信息用不上」这一系列否定结果缺少建设性出口 | A3 排为 P1 首位 |
| 逐 shot 重建匹配图 2.8 ms/shot | 任何 MWPM 边权方案都没有工程可行性 | B3 后半段必须先解决，否则不再投入 MWPM 方向 |
| 无远程仓库 | 本地磁盘故障即丢失全部结果 | C1 已完成初始化；建议尽快补远端（决策项 D2） |

---

## 5. 待确认的决策项

- [ ] **D1 · GPU 方案**：租云 / 保持 CPU-only / 移出范围（决定第 3 节关键路径）
- [ ] **D2 · 远端仓库**：是否绑定 GitHub（私有）或其他远端，用于备份与协作
- [ ] **D3 · 许可证**：`LICENSE` 未确定（学术项目常见 MIT / Apache-2.0 / 暂不声明）
- [ ] **D4 · 参考文献 PDF 策略确认**：当前不入库（可由 `scripts/download_references.py` 重建）；若要求离线自洽可改用 Git LFS
- [ ] **D5 · A8（端到端/可微 BP）是否纳入承诺范围**

---

## 6. 建议执行顺序

1. **第 1 周**（零外部依赖，先把交付标准补齐）：C2 -> C3 -> C5 -> A12 -> B1
2. **第 2-4 周**（拿到 GPU 后）：B2 -> A1 -> A2 -> B5
3. **第 5-7 周**：A3 -> A11 -> A6（把结论钉在统计显著上）
4. **第 8-10 周**：按投入产出排序 A4 -> A5 -> A9 -> A7 -> A10
5. **收尾**：C4 最终报告（依赖 A3/A6/C3 收敛）

---

## 7. 变更记录

| 日期 | 变更 |
|---|---|
| 2026-10-15 | 初版：基于 M0-M5 文档、`README.md`、`results/` 全量核对建立未完成清单；完成 C1 本地 git 初始化（`main` 分支，`.gitignore` + `.gitattributes`）；修正总工时估算为 63-93 人日 |