# 交接说明（HANDOFF）

- **交接时间**：2026-10-18 下午（本地收口 + Phase 1 文档整理）
- **交接时仓库状态**：HEAD = 本地收口提交（2026-10-18，`git log -1` 可查）；工作区干净；`pytest` **72 项全过**（Python 3.12.1，约 10 s）
- **交付状态**：第一阶段 P0/P1（T1-T11、T17、T18）全部完成，出口标准 1-6 已在本地核验；D1 暂不接远端，本地 Git bundle + SHA256 快照见 `docs/DELIVERY_LOCAL.md`
- **最近一次全链结果**：2026-10-17/18 的 `session4_seeds.ps1 -Stage all` 已完成并修复 HGP 入口；详细记录见 `docs/archive/COMPLETED_TASKS.md` 与 `results/logs/session4.log`。
- **当前后台任务**：无（08:48 全部收尾）。
- **本地收口记录**：`docs/DELIVERY_LOCAL.md`；快照写入 `artifacts/delivery/`（本地目录，不入库）。
- **关机守卫**：两种做法（无人值守选一种即可）——
  1. `scripts\session4_seeds.ps1 -ShutdownAfter`：整条链跑完后自己执行 `shutdown.exe /s /t 300`（**已实测成功**）；
  2. `scripts\shutdown_when_done.ps1 -Watch`：以 detached 进程守望本仓库的 python 进程（2026-10-16 用过一次）。
  - 取消：300 s 宽限内 `shutdown /a`，或杀守望进程（PID 见 `results/logs/shutdown_watch.log`）。用守望模式前必须让 `results/logs/shutdown_issued.flag` 不存在（本环境拒绝 `Remove-Item`，按仓库惯例用 `git clean -f -- results/logs/shutdown_issued.flag`）；日期参数整体加引号（`'"2026-10-18 23:30"'`）。
- **交付目标**：第一阶段成果（CPU-only）。范围、出口标准与优先级定义见 `docs/ROADMAP_TODO.md` 第 0 与 2.0 节；第二阶段（GPU）为未来展望，不排期
- **本文内容**：最新状态、环境入口、已知坑与下一步；任务和决策的主源分别在 `docs/ROADMAP_TODO.md` §2.2 与 §6.2。

---

## 1. 接手前必读

| 文件 | 读它解决什么问题 |
|---|---|
| `docs/INDEX.md` | 文档地图、唯一事实源与维护规则 |
| `docs/FINAL_REPORT.md` | 科学结论、LER、阈值、延迟、统计口径与未解决问题 |
| `docs/ROADMAP_TODO.md` | 未完成任务（T12–T15、T8-LTR）、优先级、工时与未来展望 |
| `docs/archive/COMPLETED_TASKS.md` | T1–T11、T17、T18 的完成历史与原始验收信息 |
| `docs/DELIVERY_LOCAL.md` | 本地交付快照、校验值与恢复方式 |
| `docs/BP_IMPLEMENTATION.md` | BP 算法规范、批量化设计与实测 µs/shot |
| `results/m5/GNN_PERF.md` | GNN 前向实测成本与 T5 遗留问题 |
| `results/m5/ENGINEERING_TABLE.md` | 全部已测量的延迟/吞吐/内存/迭代数（生成物，勿手改） |
| `results/m4/THRESHOLD.md` | 阈值估计现状 |
| `results/t8/D7_MODEL_SEEDS.md`、`results/t9/SURFACE_D3_MULTISEED.md` | 模型种子口径的 OSD-CS 探针与表面码消融汇总 |

## 2. 环境与验证入口

```powershell
# 0) 环境：CPU-only torch（torch.cuda.is_available() == False），i5-12400 / 16 GB
$env:PYTHONPATH = "src"; $env:PYTHONUTF8 = "1"

# 1) 回归测试（期望 72 passed，约 10 s）
.\.venv\Scripts\python.exe -m pytest -q

# 2) 端到端 smoke（本地实测约 26 s 全绿，含单测；-SkipTests 约 21 s。产出写进 results/smoke/，已在 .gitignore 中）
.\scripts\run_all.ps1              # 加 -SkipTests 可跳过单测；加 -Full 会跑 M2 训练与 M3 扫描

# 3) CPU 预算实测（决定新实验规模时先跑它，约 40 s）
.\.venv\Scripts\python.exe scripts\probe_cpu_budget.py --distances 3 --gnn-distances 5 7 --json results\m5\cpu_budget.json

# 4) 工程性能表重新生成
.\.venv\Scripts\python.exe scripts\engineering_table.py

# 5) 夜间续跑链（Session 4）：T6 残点 + T8/T9 种子补点 + 迁移多种子 + 表格重生成
pwsh -File scripts\session4_seeds.ps1 -Stage all -DryRun     # 预演：只打印将执行的命令，不跑实验
Start-Process -WindowStyle Hidden pwsh -ArgumentList '-NoProfile','-File','scripts\session4_seeds.ps1','-Stage','all'
# 末尾加 '-ShutdownAfter' 可在整条链跑完后自动关机（300 s 宽限，shutdown /a 可取消）
```

## 3. 当前状态与下一步

> P0 与 P1（T1–T11、T17、T18）已全部完成，出口标准 1–6 已在本地核验；当前没有阻塞项。已完成任务的详细叙事见 `docs/archive/COMPLETED_TASKS.md`。

### 3.1 剩余可选工作

1. **统计补强（1–2 人日 + 1–3 h CPU）**：T8 表面码 d=3 OSD-CS 补 3 seeds；表面码 d=3→d=5 码容量迁移补 3 seeds；T10 repetition d=5 先验强度复核。当前仍属单 seed 的范围见 `docs/FINAL_REPORT.md` §7 第 7 条。
2. **P2 强化项**：T12、T13、T14、T15 与 T8 learning-to-rank，见 `docs/ROADMAP_TODO.md` §2.2；合计 14–22 人日 + 6.5–7.5 h CPU（含 T8-LTR 估算）。
3. **推荐顺序**：统计补强 → T12/T13 → T8-LTR → T14 → T15。

### 3.2 每次改动后的验证

```powershell
$env:PYTHONPATH = "src"; $env:PYTHONUTF8 = "1"
.\.venv\Scripts\python.exe -m pytest -q
.\scripts\run_all.ps1
```

根因分析与历史命令见 `docs/FINAL_REPORT.md` §8 与 `docs/archive/COMPLETED_TASKS.md`。

## 4. 已知坑与操作纪律

1. **batch 大小**：表面码 d=5/d=7 训练必须 `batch_size=128`。1024 时逐边激活在 16 GB 上内存耗尽，进程被系统**静默杀死**（日志里没有 traceback，只在输出目录为空时才看得出来）。长跑后用 `Get-Process python` 与输出目录是否增长来确认存活。
2. **结果目录不可覆盖**：M2/M3/M4 的 CLI 在目标目录已存在时抛 `FileExistsError`。删除方式：已跟踪用 `git rm -r -q -f <dir>`，未跟踪用 `git clean -fdq -- <dir>`（先 `git clean -nd` 预演）。本环境的策略**拒绝** PowerShell 的 `Remove-Item -Recurse`。
3. **噪声率在 JSON 里的路径是 `experiment.noise.physical_error_rate`**，不是 `experiment.physical_error_rate`。改错路径会让不同 p 跑出**完全相同**的数字（已踩过一次，靠"p=0.001 与 p=0.01 结果逐位相同"才发现）。
4. **不要在 `results/*.json` 里做含反斜杠的路径替换**（`results\m3_fixed\` → `results\m3\` 会破坏 JSON 转义）。要改目录名就替换纯名字（`m3_fixed` → `m3`），改完用 Python 全量 `json.loads` 校验。
5. **torch 动态量化会把 `nn.Linear` 换成 `weight` 为可调用对象的模块**，GNN 前向的快路径对非 `nn.Linear` 层会自动回退到 concat 实现（`tests/test_gnn_forward_equivalence.py::test_forward_falls_back_for_non_linear_message_layers` 锁定）。不要删掉这个分支——删掉会让 `scripts/m5_quantization.py` 崩溃。
6. ~~**交付范围内不得引用 `union_find` 的表面码数字**（T18）~~ **已于 2026-10-15 解除**：Union-Find 重写后表面码比值 1.00-1.41× MWPM，`results/m4/surface_sweep.json` 的该列可安全引用。
7. **耗时预算先看实测**：BP 在表面码线路级为 d=3 242 µs/shot、d=5 8.1 ms/shot、d=7 46.9 ms/shot、d=9 127.9 ms/shot（`docs/BP_IMPLEMENTATION.md` 第 4 节）；GNN 前向 d=5 7.8 ms/shot、d=7 27.7-35.3 ms/shot（`results/m5/GNN_PERF.md`）。开新实验前先用 `scripts/probe_cpu_budget.py` 标定。
8. **提交时排除进行中的结果目录**（`git add` 指定路径，或确认目录为空），避免把半成品写进交付。
9. **统计纪律**：任何百分比结论都要给 shots、seed 数与标准误；2048 shots 的标准误约 0.005-0.008，只够给方向。
10. **长跑一律用 detached 进程**：`Start-Process -WindowStyle Hidden`（`scripts/session3_seeds.ps1 -Chain A|B|C|D` 就是模板）。会话/窗口退出会带走前台子进程——2026-10-16 12:00 的「意外退出」就是这样丢掉了三条链的各一半进度。
11. **脚本必须可续跑**：T6 网格是「结果目录存在即跳过」，T9 消融用 `--merge` 把同一 seed 的多次测量合并进一个 `ablation.json`（`--merge` 的写入口径在 2026-10-16 修过一次，务必保留 `"rows": merged_rows` 这一处）。重放任何长跑命令都是安全的。
12. **跨 seed 的推断口径**：种子是重复单位。把各 seed 的 shot 直接求和（pooled）会把种子间散布（32768 shots 下 ±15%）当成二项噪声、高估显著性——见 `scripts/t9_multiseed.py` 里「跨 seed 配对」与「合并口径」两张表。只有「多份独立测试集 × 同一模型」的场景（如 d=7 OSD-CS 探针）才适合 pooled 口径，且必须在文档里写明它不含模型种子方差。
13. **HGP（DEM-level / M4 码族）必须用 `graph_qec.m4`，不能用 `graph_qec.m2`**——后者在 `build_circuit` 处报 `'hgp_rep3x3' is a detector-error-model-level code family (M4); it has no Stim circuit`（2026-10-18 00:38 的四条 HGP 命令因此全失败）。失败留下的**空结果目录**会让重跑抛 `FileExistsError`，先用 `git clean -fdq -- <dir>` 清掉。
14. **`session4_seeds.ps1 -ShutdownAfter` 已实测**（19:11 启动 → 00:38:59 发出关机 → 00:44 关机）：无人值守优先用它；`-DryRun` 可先预演整条链。若改守望模式，先删 `results/logs/shutdown_issued.flag`，且等 python 进程起来后再启动守望。

## 5. 决策事项

D1–D3 已于 2026-10-18 在本地收口时决定：**暂不接远端**（本地 Git bundle + SHA256 快照）、**暂不声明 LICENSE**（仅本地/内部使用）、**参考文献 PDF 不入库**（按 manifest 重建）。D4 的 T6 低噪声补点已完成。

> 决策主源见 `docs/ROADMAP_TODO.md` §6.2；本地快照与校验值见 `docs/DELIVERY_LOCAL.md`。

## 6. 接手检查清单

- [x] `git log --oneline -1` 确认在本地收口提交或其后的文档整理提交
- [x] `pytest -q`：72 passed（约 10 s）
- [x] `Get-Process python` 确认没有遗留的后台进程；`results/logs/session4.log` 末行应为 `session4 finished`（其中 00:38 的 HGP 失败记录是历史，已修复补跑）
- [x] `pwsh -File scripts\session4_seeds.ps1 -Stage all -DryRun` 预演：`grid plan` 显示 **0 pending / 30 points**，各槽均为 `skip (result exists)`
- [x] `.\scripts\run_all.ps1 -SkipTests`：全绿，本地实测约 21 s
- [x] 读 `docs/ROADMAP_TODO.md` 第 0 与 2.0 节、`docs/FINAL_REPORT.md` 第 4.6/4.8 节与第 7 节
- [x] 读第 4 节的 12 条纪律（尤其 batch、结果目录、跨 seed 口径三条）
- [x] 确认 D1-D4 的决策状态（第 5 节）
