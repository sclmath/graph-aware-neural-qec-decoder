# 第一阶段本地交付记录（LOCAL CLOSEOUT）

- **日期**：2026-10-18（Asia/Shanghai）
- **仓库**：`D:\work2026\BuChou\Projects_BuChou\01_graph_aware_neural_qec_decoder`
- **收口前基线**：`b56a1ef`（2026-10-18 08:51，T6 30/30 收口提交）
- **本地标签**：`phase1-local-20261018`
- **交付状态**：第一阶段 P0/P1（T1-T11、T17、T18）全部完成；P2（T12-T15、T8 learning-to-rank）为可选后续，不阻塞交付。
- **远端策略**：D1 暂不绑定远端；本地交付不依赖 GitHub Actions。`.github/workflows/ci.yml` 保留，远端首跑挂起。

## 1. 本地验证

| 项目 | 结果 |
|---|---|
| 回归测试 | `pytest -q`：**72 passed**，3 个弃用警告；全量 smoke 内 6.4 s，单独运行 10.3 s（Python 3.12.1 / CPU-only torch） |
| 端到端 smoke | 全量 `scripts\run_all.ps1`：5 个步骤全部 exit 0，合计 26.3 s（单测 7.3 s、M0 0.8 s、M1 1.1 s、CPU 探针 17.0 s、M2 汇总 0.1 s）；`-SkipTests` 约 20.7 s |
| T6/T8/T9 完整性 | `scripts\session4_seeds.ps1 -Stage all -DryRun`：`grid plan: 0 pending / 30 points`；其余槽均为 `skip (result exists)` |
| 工作区 | 收口前 `git status --short` 为空；`HEAD = b56a1ef` |
| CI | 配置存在；因 D1 暂不接远端，未执行远端首次运行 |

> `run_all.ps1` 的临时产物写入 `results/smoke/`，该目录已在 `.gitignore` 中；本次验证后未留下脏文件。

## 2. 交付物入口

- 技术报告：`docs/FINAL_REPORT.md`
- 交接说明：`docs/HANDOFF.md`
- 范围与待办：`docs/ROADMAP_TODO.md`
- 多 seed 汇总：`results/t10/MULTISEED.md`
- 阈值估计：`results/m4/THRESHOLD.md`
- CPU 工程性能表：`results/m5/ENGINEERING_TABLE.md`
- 模型种子口径的 d=7 OSD-CS 探针：`results/t8/D7_MODEL_SEEDS.md`
- 表面码 d=3 消融（3 seeds）：`results/t9/SURFACE_D3_MULTISEED.md`

## 3. 本地快照

收口提交完成后生成以下本地文件（目录 `artifacts/delivery/` 已加入 `.gitignore`，不重复入库）：

```text
artifacts/delivery/qec-decoder-phase1-20261018.bundle   # git bundle --all
artifacts/delivery/qec-decoder-phase1-20261018.zip      # git archive <tag>
artifacts/delivery/SHA256SUMS.txt                       # 上述文件的 SHA256
```

恢复/校验：

```powershell
# 校验 bundle 完整性
git bundle verify .\artifacts\delivery\qec-decoder-phase1-20261018.bundle

# 从 bundle 恢复完整历史
git clone .\artifacts\delivery\qec-decoder-phase1-20261018.bundle ..\qec-decoder-restore
git -C ..\qec-decoder-restore log --oneline -1

# 校验归档与摘要
Get-FileHash .\artifacts\delivery\qec-decoder-phase1-20261018.bundle -Algorithm SHA256
Get-FileHash .\artifacts\delivery\qec-decoder-phase1-20261018.zip -Algorithm SHA256
Get-Content .\artifacts\delivery\SHA256SUMS.txt
```

> 参考文献 PDF（129.7 MB）按 `.gitignore` 不入库；需要离线复现时运行 `scripts/download_references.py`，manifest 与校验文件已入库。

## 4. 本地收口决策

| 编号 | 决策 |
|---|---|
| D1 | 暂不绑定远端；使用本地 Git bundle + SHA256 快照。CI 首跑挂起，不阻塞本地交付。 |
| D2 | 暂不声明 LICENSE；当前仅本地/内部使用，对外分发前再定 MIT / Apache-2.0。 |
| D3 | 参考文献 PDF 保持不入库；按 `docs/references/references_pdfs/manifest.*` 重建，不启用 Git LFS。 |

## 5. 剩余可选工作

这些项不影响本次交付，按价值排序：

| 项目 | 人日 | CPU 算力 | 说明 |
|---|---:|---:|---|
| 统计补强 | 1-2 | 1-3 h | T8 表面码 d=3 OSD-CS、d=3→d=5 码容量迁移、T10 repetition d=5 先验强度复核 |
| T8 learning-to-rank | 3-5 | 2-3 h | 对应 `FINAL_REPORT` 未解决问题第 1 条 |
| T12 真零样本迁移 | 2 | 1 h | 移除边特征中的 p |
| T13 多噪声率训练课程 | 1-2 | 1 h | 与 T12 可共用改动 |
| T14 HGP 换种子码 + 跨族迁移 | 3-5 | 2 h | 依赖 HGP 码生成器 |
| T15 精确机制映射 + 每边一次建图 | 5-8 | 0.5 h | 最大工程项；涉及 PyMatching 图接口 |

## 6. 复现入口

```powershell
$env:PYTHONPATH = "src"; $env:PYTHONUTF8 = "1"

# 回归 + 端到端 smoke
.\.venv\Scripts\python.exe -m pytest -q
.\scripts\run_all.ps1

# T6 网格计划（应为 0 pending / 30 points）
.\.venv\Scripts\python.exe scripts\t6_surface_grid.py --print-plan

# 数值表重新生成
.\.venv\Scripts\python.exe scripts\t10_multiseed_stats.py --results-dir results\m4_surface --output-dir results\t10
.\.venv\Scripts\python.exe scripts\engineering_table.py
```
