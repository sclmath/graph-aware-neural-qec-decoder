# 交接说明（HANDOFF）

- **交接时间**：2026-10-18 下午（本地收口版，第五次刷新）
- **交接时仓库状态**：HEAD = `b56a1ef`（2026-10-18 上午收口提交）；工作区干净；`pytest` **72 项全过**（Python 3.12.1，约 10 s）
- **交付状态**：第一阶段 P0/P1（T1-T11、T17、T18）全部完成，出口标准 1-6 已在本地核验；D1 暂不接远端，本地 Git bundle + SHA256 快照见 `docs/DELIVERY_LOCAL.md`
- **夜间任务结果（2026-10-17 19:11 → 10-18 00:39，5.46 h）**：`session4_seeds.ps1 -Stage all -ShutdownAfter` 的 7 个槽里 **6 个全绿**——`grid` 30/30（208.5 min）、`postprocess`、`probes` ×6、`probes-extra` ×3、`ablation` ×2、`aggregate`；`extra` 的 HGP 部分**入口用错**（`graph_qec.m2`，应为 `graph_qec.m4`），已于 2026-10-18 08:21-08:48 修复并补跑完成。**关机按计划执行**（00:38:59 发出，08:18:45 已重新开机）。
- **当前后台任务**：无（08:48 全部收尾）。
- **本地收口记录**：`docs/DELIVERY_LOCAL.md`；快照写入 `artifacts/delivery/`（本地目录，不入库）。
- **关机守卫**：两种做法（无人值守选一种即可）——
  1. `scripts\session4_seeds.ps1 -ShutdownAfter`：整条链跑完后自己执行 `shutdown.exe /s /t 300`（**已实测成功**）；
  2. `scripts\shutdown_when_done.ps1 -Watch`：以 detached 进程守望本仓库的 python 进程（2026-10-16 用过一次）。
  - 取消：300 s 宽限内 `shutdown /a`，或杀守望进程（PID 见 `results/logs/shutdown_watch.log`）。用守望模式前必须让 `results/logs/shutdown_issued.flag` 不存在（本环境拒绝 `Remove-Item`，按仓库惯例用 `git clean -f -- results/logs/shutdown_issued.flag`）；日期参数整体加引号（`'"2026-10-18 23:30"'`）。
- **交付目标**：第一阶段成果（CPU-only）。范围、出口标准与优先级定义见 `docs/ROADMAP_TODO.md` 第 0 与 2.0 节；第二阶段（GPU）为未来展望，不排期
- **本文内容**：最新状态 + 下一步工作包（第 3 节）+ 环境入口与操作纪律（第 2、4 节）

---

## 1. 接手前必读

| 文件 | 读它解决什么问题 |
|---|---|
| `docs/ROADMAP_TODO.md` | 交付范围（第 0 节）、优先级定义（2.0 节）、待办 T1-T18、CPU 算力预算实测（第 1 节） |
| `README.md` 第 9-15 节 | 各里程碑的**唯一口径**结论与数字 |
| `docs/BP_IMPLEMENTATION.md` | BP 算法规范、批量化设计、随码距的实测 µs/shot（决定扫描能开到多大） |
| `results/m5/GNN_PERF.md` | GNN 前向实测成本与 T5 的遗留问题（未达标的优化目标） |
| `results/m5/ENGINEERING_TABLE.md` | 全部已测量的延迟/吞吐/内存/迭代数（由脚本生成，勿手改） |
| `results/m4/THRESHOLD.md` | 阈值估计现状（BP 系线路级阈值在 0.003 以下；MWPM 0.005-0.008） |
| `results/t8/D7_MODEL_SEEDS.md`、`results/t9/SURFACE_D3_MULTISEED.md` | 模型种子口径的 OSD-CS 探针与表面码消融的 3-seed 汇总（种子是重复单位） |

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

## 3. 下一步工作包

> P0 与 P1（T1-T11、T17、T18）已全部完成，交付出口标准 1-6 全部达成；**T6 的 30/30 点与三项单 seed 补点已于 2026-10-18 收口**。剩下的只有 P2 强化项（T12-T15，不做仍可交付）与三项待决策（D1-D3）。

### WP1 · T6 补满 30 点 + 收口（**已完成，2026-10-18**）

- **30/30 点**：最后 6 点（d=5/d=7 p=0.002 × 3 seeds）由 `session4_seeds.ps1 -Stage grid` 于 2026-10-17 19:11→22:40 跑完（208.5 min）；全网格累计壁钟约 24 h。
- **收口脚本已重生成**：`results/t10/{MULTISEED.md,surface_sweep_mean.json}`、`results/m4/THRESHOLD.md`、`results/m5/ENGINEERING_TABLE.md`。
- **结论**：d=5 噪声率轴出现低端拐点（p=0.003 峰值 **−43.4%**，p=0.002 回落到 −37.4%）；d=7 单调下降（−38.2% → −9.9%，峰值在区间下沿）；OSD-0 在 10 个点全部更差（+10.4% ~ +60.5%）。T6 表格与阈值结论已写入 `FINAL_REPORT` §4.6/§4.7 与 `README` 第 9-15 节。
- **重放命令**：`pwsh -File scripts\session4_seeds.ps1 -Stage all`（幂等；全部输出存在时各槽秒级跳过）。


### WP2 · 剩下的单 seed 结论（P2，未解决问题 7 的剩余部分）

- 已完成：T9 repetition 消融、T8 d=7 OSD-CS 探针（每点 3 份测试集）、T8 repetition d=3 研究、M2 旗舰表（都是 3 seeds / 98304 shots 量级：`results/{m2/HEADLINE_MULTISEED.md,t8/D7_MULTISEED.md,t8/REPETITION_D3_MULTISEED.md,t9/REPETITION_D3_MULTISEED.md}`）；
- 本轮还补了两处：表面码 d=3 线路级 p=0.005 的锚点（−18.2% 单 seed → **−29.0% ± 2.4%**，3 seeds）与 T8 repetition 研究；`scripts/m2_headline_multiseed.py` 现在对任意 M2/M4 配置通用（`--base-config` / `--out-dir` / `--output`，配套 `scripts/m2_headline_seeds.ps1 -BaseConfig -OutDir`）
- **本轮又撤回了两个单 seed 结论**（都属「小差异」型）：T9/T8 的「λ=4 上 DEM 先验与学习先验打平」→ +0.00055 ± 0.00043（不可区分）；M2 旗舰表的 bp vs bp_gnn → −0.00028 ± 0.00035（符号翻转）。这说明**凡结论涉及 <0.001 量级的差异，必须 3 seeds**；
- **仍属单 seed**：T8 的 repetition/表面码 d=3 两个 OSD-CS 研究（效应量大，优先级低）、表面码 d=3→d=5 的码容量迁移（−12%，未做多种子）、T10 的 repetition d=5 先验强度复核（未做）；
- **2026-10-18 起不再是单 seed**：HGP 跨尺寸迁移（3 seeds，但**结论被推翻**，见下）、M3 跨码距迁移（3 seeds，稳健）、4.8.1 表面码全部 5 条臂（3 seeds）、T8 的 d=7 探针（3 个模型 seed）；
- 做法可直接复用本轮的两个工具：`scripts/t9_feature_ablation.py --seed-offset N --merge`（消融）与 `scripts/t9_multiseed.py --prefix <系列>`（跨 seed 汇总）。

**已完成（`probes` 槽，2026-10-17 夜间）**：6 次模型种子探针（6.5-9.5 min/次）→ `results/t8/D7_MODEL_SEEDS.md`（`scripts/t8_d7_model_seeds.py`；与只换测试集的 `D7_MULTISEED.md` 分口径）。
- OSD-0 相对 `bp_gnn` 恶化 **+43.0%±14.0% / +34.7%±12.2% / +15.8%±2.4%**（p=0.003/0.005/0.008，3 个模型 seed 全部同号）
- OSD-CS 对 OSD-0 的修补 **−41.7%±3.8% / −26.2%±1.1% / −14.9%±1.8%**（9 个 (p, seed) 组合全部成立）
- 但 **CS 相对 `bp_gnn` 的净增益只有 p=0.003 有方向**（−15.7%±13.3%，n.s.），p≥0.005 归零 → **旧口径的 −34.9%/−11.6%/−1.9% 是单模型效应**
- 另补 d=7 p=0.01 的 3 份测试集（cs4 比 `bp_gnn` 差 +8.4%）

**迁移多种子（`extra` 槽，2026-10-18 上午补跑）**：
- **M3 跨码距 d=3→d=5 稳健**：−66.3% / −68.0% / −71.0%（三个种子同号）
- **HGP 跨尺寸迁移不稳健**：−11.4% / +4.9% / +12.5%（均值 **+2.0% ± 7.1%**）→ **单 seed 的 −11% 已撤回**
- **HGP 源域** [[13,1,3]]：−3.1% / −5.9% / −9.7%（同号，效应小）


**验收**：相关表格全部标注 shots、seed 数与跨 seed 标准误；迁移结论必须给出 3 seeds 的配对 Δ（种子是重复单位，不复用 pooled 口径）。

### WP3 · P2 强化项 T12-T15（不做仍可交付）

T12 真零样本迁移（移除边特征里的 p）、T13 多噪声率训练课程、T14 HGP 换种子码 + 跨族迁移、T15 精确机制映射 + 每边一次建图。详见 `docs/ROADMAP_TODO.md` 第 2.2 节，合计 11-17 人日。

### WP4 · 交付收口（每次改动后都做）

1. `pytest -q`（期望 72 passed）；
2. `scripts/run_all.ps1`（端到端 smoke，约 18 s）；
3. 表格/图全部由脚本生成，`docs/FINAL_REPORT.md` 里的数字与 `results/` 一致；
4. 提交时 `git add` 指定路径，避免把正在跑的结果目录写进提交。

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

| 编号 | 事项 | 结论 |
|---|---|---|
| D1 | 远端仓库 | **已决（2026-10-18）：暂不绑定远端**；本地交付用 Git bundle + SHA256 快照备份，CI 首跑继续挂起，不阻塞本地收口 |
| D2 | LICENSE | **已决（2026-10-18）：暂不声明**；当前仅本地/内部使用，对外分发前再定 MIT / Apache-2.0 |
| D3 | 参考文献 PDF | **已决（2026-10-18）：保持不入库**；按 manifest + `scripts/download_references.py` 重建，不启用 Git LFS |
| D4 | T6 低噪声端补点 | **已决（2026-10-17）：做**；30/30 点已完成，LER-p 曲线低端拐点证据已写入报告 |

## 6. 接手检查清单

- [x] `git log --oneline -1` 确认在 `b56a1ef` 或其后的本地收口提交
- [x] `pytest -q`：72 passed（约 10 s）
- [x] `Get-Process python` 确认没有遗留的后台进程；`results/logs/session4.log` 末行应为 `session4 finished`（其中 00:38 的 HGP 失败记录是历史，已修复补跑）
- [x] `pwsh -File scripts\session4_seeds.ps1 -Stage all -DryRun` 预演：`grid plan` 显示 **0 pending / 30 points**，各槽均为 `skip (result exists)`
- [x] `.\scripts\run_all.ps1 -SkipTests`：全绿，本地实测约 21 s
- [x] 读 `docs/ROADMAP_TODO.md` 第 0 与 2.0 节、`docs/FINAL_REPORT.md` 第 4.6/4.8 节与第 7 节
- [x] 读第 4 节的 12 条纪律（尤其 batch、结果目录、跨 seed 口径三条）
- [x] 确认 D1-D4 的决策状态（第 5 节）
