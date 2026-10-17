# 交接说明（HANDOFF）

- **交接时间**：2026-10-17 上午（第三次刷新；上一轮夜间任务已收尾，本批结果尚未提交）
- **交接时仓库状态**：HEAD = 2026-10-16 下午的多种子提交；`pytest` **72 项全过**（2026-10-17 08:41 复核）；
  工作区剩：T6 网格 **24/30 点**的 8 个结果目录（`results/m4_surface/`，未提交）与若干日志改动（`git status --short` 可见）
- **正在运行的后台任务**：**无**。2026-10-16 的 `scripts/session3_seeds.ps1 -Chain D` 已跑完计划内的 8 个点（d=7 p=0.008 的 s2/s3、d=5 p=0.01 ×3、d=7 p=0.01 ×3），21:13 因 480 min 预算到时停止；关机守望随后按条件关机。**下一批实验（T6 残点 6 个 + 三组种子补点）等 2026-10-17 晚间命令**，用 `scripts/session4_seeds.ps1` 一条命令跑完，见第 3 节 WP1
- **关机守卫**：两种做法（无人值守选一种即可）——
  1. `scripts\session4_seeds.ps1 -ShutdownAfter`：整条链跑完后自己执行 `shutdown.exe /s /t 300`，不需要守望进程；
  2. `scripts\shutdown_when_done.ps1 -Watch`：以 detached 进程守望本仓库的 python 进程（2026-10-16 用过一次，正常触发）；
  - 取消方式：关机指令有 300 s 宽限，期间 `shutdown /a` 即可；或 `Stop-Process -Id <watcher pid>`。要用守望模式，先确保 `results/logs/shutdown_issued.flag` 不存在（本环境拒绝 PowerShell 的 `Remove-Item`，按仓库惯例用 `git clean -f -- results/logs/shutdown_issued.flag`；该文件已于 2026-10-17 上午清掉）。
  - 注意：日期参数必须整体加引号传给 `Start-Process`（`'"2026-10-16 23:30"'`），否则空格会把参数拆开、把截止时间变成已过期而**立即关机**——2026-10-16 21:06 踩过一次（已 `shutdown /a` 中止），脚本现已内置「拒绝过去的截止时间」防呆。
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
| `results/m4/THRESHOLD.md` | 阈值估计现状（只有 MWPM 码容量给出了区间） |

## 2. 环境与验证入口

```powershell
# 0) 环境：CPU-only torch（torch.cuda.is_available() == False），i5-12400 / 16 GB
$env:PYTHONPATH = "src"; $env:PYTHONUTF8 = "1"

# 1) 回归测试（期望 72 passed，约 8-13 s）
.\.venv\Scripts\python.exe -m pytest -q

# 2) 端到端 smoke（期望 18 s 全绿；产出写进 results/smoke/，已在 .gitignore 中）
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

> P0 与 P1（T1-T11、T17、T18）已全部完成，交付出口标准 1-6 全部达成。剩下的都是「把 P1 的残点补满」与「P2 强化」。

### WP1 · T6 补满 30 点 + 收口（**24/30 已落盘；余 6 点排在 2026-10-17 晚间**）

**已跑 24 点**（`results/m4_surface/`）：d=5 p ∈ {0.003, 0.005, 0.008, 0.01} × 3 seeds（8192 test shots/seed）、
d=7 p ∈ {0.003, 0.005, 0.008, 0.01} × 3 seeds（4096/seed）。其中最近 8 个点由 `session3_seeds.ps1 -Chain D` 在 2026-10-16 夜间补上。

**上一轮**（`session3_seeds.ps1 -Chain D`，2026-10-16 12:43 启动，预算 480 min）：按计划跑完 8 个点后于 21:13 收尾。网格按「结果目录存在即跳过」续跑，重复执行命令是安全的。

**跑完后的收口动作（三步，均为秒级）**：

```powershell
$env:PYTHONPATH = "src"; $env:PYTHONUTF8 = "1"
.\.venv\Scripts\python.exe scripts\t10_multiseed_stats.py --results-dir results\m4_surface --output-dir results\t10
.\.venv\Scripts\python.exe scripts\threshold_estimate.py --inputs results\t10\surface_sweep_mean.json results\m4\surface_sweep.json results\m4_threshold\surface_sweep.json --output results\m4\THRESHOLD.md
.\.venv\Scripts\python.exe scripts\engineering_table.py
```

注意：2026-10-16 补的**表面码 d=3 线路级 p=0.005 的 s10/s20** 两个运行也在 `results/m4_surface/` 里，重跑 `t10_multiseed_stats.py` 会自动把 d=3 那一格从 1 seed 变成 3 seeds（`results/t10/surface_sweep_mean.json` 与 `results/m4/THRESHOLD.md` 因此都要一起重生成，4.7 的阈值结论要复核一遍）。


**2026-10-17 晚间窗口（12 h，无人值守）**：`p=0.002` 已获批（D4 已决），与三项单 seed 补齐一起排成一条链 `scripts/session4_seeds.ps1`（幂等、按「输出已存在即跳过」续跑；日志 `results/logs/session4.log`）：

| 槽 | 内容 | 机器时间 | 依据（均为实测） |
|---|---|---|---|
| `grid` | T6 残点 6 个：d=5/d=7 p=0.002 × 3 seeds | **3.2-3.8 h** | 训练 ~17 min/点（与 p 无关）+ 评测随 BP 平均迭代缩放；同点跨 seed ±30% |
| `postprocess` | `t10_multiseed_stats` → `threshold_estimate` → `engineering_table` | < 1 min | 上一轮实测 0.1 min |
| `probes` | T8 d=7 OSD-CS 探针升级为「模型 + 数据都换」：p ∈ {0.003,0.005,0.008} × {s2,s3}（6 次） | 约 1 h | 单次探针 8-13 min（chainA/B 日志） |
| `probes-extra` | T8 d=7 p=0.01 探针 × 3 份测试集（新噪声率点） | 约 12 min | 同上 |
| `ablation` | 表面码 d=3 剩余 3 条臂 × {s10,s20}（`--merge` 进已有 `ablation.json`） | 约 0.7 h | repetition 同款 3.5 min/次，表面码估 5-8 min/次 |
| `extra` | M3 跨码距 d=3→d=5 多种子 + HGP 跨尺寸迁移多种子（源模型换 seed 重训、目标测试集同步换 seed） | 约 0.6 h | rep3x3 训练 617 s/seed、迁移 183 s、M3 迁移 31 s |
| `aggregate` | 重生成 `results/t8/{D7_MULTISEED,D7_MODEL_SEEDS}.md`、`results/t9/SURFACE_D3_MULTISEED.md`、`results/m5/ENGINEERING_TABLE.md` | < 1 min | — |

合计 **约 5.5-6.5 h**，12 h 窗口留 ~5 h 余量（吸收波动与一次失败重跑）。执行与预演见第 2 节第 5 项。

**跑完后的收口（人工，1-1.5 h）**：§4.6 表补 p=0.01/p=0.002 两行、去掉 d=7 p=0.008 的单 seed 标注；§4.7 阈值复核（低端多一个点）；
T8 第 4 条换成模型种子口径（新增 `D7_MODEL_SEEDS.md`）；4.8.1 表面码表升级到 3 seeds；同步 README 第 9-15 节与 `docs/ROADMAP_TODO.md` 的 T6/T10 条目；最后 `pytest` + `run_all.ps1` + 提交。

### WP2 · 剩下的单 seed 结论（P2，未解决问题 7 的剩余部分）

- 已完成：T9 repetition 消融、T8 d=7 OSD-CS 探针（每点 3 份测试集）、T8 repetition d=3 研究、M2 旗舰表（都是 3 seeds / 98304 shots 量级：`results/{m2/HEADLINE_MULTISEED.md,t8/D7_MULTISEED.md,t8/REPETITION_D3_MULTISEED.md,t9/REPETITION_D3_MULTISEED.md}`）；
- 本轮还补了两处：表面码 d=3 线路级 p=0.005 的锚点（−18.2% 单 seed → **−29.0% ± 2.4%**，3 seeds）与 T8 repetition 研究；`scripts/m2_headline_multiseed.py` 现在对任意 M2/M4 配置通用（`--base-config` / `--out-dir` / `--output`，配套 `scripts/m2_headline_seeds.ps1 -BaseConfig -OutDir`）
- **本轮又撤回了两个单 seed 结论**（都属「小差异」型）：T9/T8 的「λ=4 上 DEM 先验与学习先验打平」→ +0.00055 ± 0.00043（不可区分）；M2 旗舰表的 bp vs bp_gnn → −0.00028 ± 0.00035（符号翻转）。这说明**凡结论涉及 <0.001 量级的差异，必须 3 seeds**；
- **仍属单 seed**：HGP 跨尺寸迁移、跨码距迁移（d=3 → d=5）、4.8.1 表面码表里除 `all`/`no_variable_geometry` 之外的三条臂、T8 的 repetition/表面码 d=3 两个 OSD-CS 研究（效应量大，优先级低）；**其中前三项已排进 2026-10-17 晚间的 `session4_seeds.ps1`**；
- 做法可直接复用本轮的两个工具：`scripts/t9_feature_ablation.py --seed-offset N --merge`（消融）与 `scripts/t9_multiseed.py --prefix <系列>`（跨 seed 汇总）。

**已升级为脚本（`probes` 槽）**：T8 的 d=7 OSD-CS 探针原本是「3 份独立测试集 × 同一个 checkpoint」（只压 LER 估计误差）。
T6 网格跑完 d=7 的 s2/s3 后会留下它们各自的 `model_state.pt`，`session4_seeds.ps1` 会用它们把探针升级成「模型 + 数据都换」
（6 次，约 1 h）；汇总脚本是本轮新写的 `scripts/t8_d7_model_seeds.py` → `results/t8/D7_MODEL_SEEDS.md`
（种子是重复单位：给逐 seed Δ 与跨 seed 均值 ± SE；只换测试集的旧口径 `D7_MULTISEED.md` 保持不变、不混口径）。

```powershell
# 单点等价命令（脚本内部就是这么调的）
$run = 'results\m4_surface\m4_rotated_surface_code_circuit_level_d7_s2__d7__circuit_level__p0p008'
.\.venv\Scripts\python.exe scripts\t8_osd_cs_study.py --config $run\config.json --checkpoint $run\model_state.pt `
    --sweeps 0 4 --test-shots 1024 --output-dir results\t8\d7_p0p008_probe_s2model
.\.venv\Scripts\python.exe scripts\t8_d7_model_seeds.py --probe-root results\t8 --output results\t8\D7_MODEL_SEEDS.md
```

```powershell
$run = 'results\m4_surface\m4_rotated_surface_code_circuit_level_d7_s2__d7__circuit_level__p0p008'
.\.venv\Scripts\python.exe scripts\t8_osd_cs_study.py --config $run\config.json --checkpoint $run\model_state.pt `
    --sweeps 0 4 --test-shots 1024 --output-dir results\t8\d7_p0p008_probe_s2model
```

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

## 5. 未决事项（需决策）

| 编号 | 事项 | 影响 |
|---|---|---|
| D1 | 是否绑定远端仓库（GitHub 私有等） | **阻塞 T1 的 CI 首次运行**；当前无远端，本地磁盘故障即丢全部结果 |
| D2 | `LICENSE` 未确定 | 交付物缺一项 |
| D3 | 参考文献 PDF 策略（当前不入库，可由 `scripts/download_references.py` 重建） | 若要求离线自洽需改用 Git LFS |
| D4 | ~~T6 低噪声端 p=0.002 × {d=5, d=7} × 3 seeds 是否要做~~ **已决（2026-10-17）：做**，排在当晚 12 h 窗口的第一槽 | 约 3.5 h；做完 T6 网格即 30/30 完整，LER-p 曲线低端有拐点证据 |

## 6. 接手检查清单

- [ ] `git log --oneline -1` 确认在本轮（2026-10-17 上午）的提交或其后
- [ ] `pytest -q` 期望 72 passed（约 8 s）
- [ ] `Get-Process python` 确认没有遗留的后台进程；看 `results/logs/session4.log` 末行确认续跑链状态
- [ ] `pwsh -File scripts\session4_seeds.ps1 -Stage all -DryRun` 预演一遍：应打印 6 个待补点与各槽命令
- [ ] `.\scripts\run_all.ps1 -SkipTests` 期望 18 s 全绿
- [ ] 读 `docs/ROADMAP_TODO.md` 第 0 与 2.0 节、`docs/FINAL_REPORT.md` 第 4.6/4.8 节与第 7 节
- [ ] 读第 4 节的 12 条纪律（尤其 batch、结果目录、跨 seed 口径三条）
- [ ] 确认 D1-D4 的决策状态（第 5 节）
