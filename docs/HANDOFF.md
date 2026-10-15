# 交接说明（HANDOFF）

- **交接时间**：2026-10-15
- **交接时仓库状态**：HEAD = `994a889`，工作区 clean，`pytest` **62 项全过**，追踪文件 296 个
- **交付目标**：第一阶段成果（CPU-only）。范围、出口标准与优先级定义见 `docs/ROADMAP_TODO.md` 第 0 与 2.0 节；第二阶段（GPU）为未来展望，不排期
- **本文内容**：把上一轮汇报的「建议的下一步」展开成 4 个可执行工作包（第 3 节），并固化环境入口、耗时预算与操作纪律（第 2、4 节）

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

# 1) 回归测试（期望 62 passed，约 6 s）
.\.venv\Scripts\python.exe -m pytest -q

# 2) 端到端 smoke（期望 18 s 全绿；产出写进 results/smoke/，已在 .gitignore 中）
.\scripts\run_all.ps1              # 加 -SkipTests 可跳过单测；加 -Full 会跑 M2 训练与 M3 扫描

# 3) CPU 预算实测（决定新实验规模时先跑它，约 40 s）
.\.venv\Scripts\python.exe scripts\probe_cpu_budget.py --distances 3 --gnn-distances 5 7 --json results\m5\cpu_budget.json

# 4) 工程性能表重新生成
.\.venv\Scripts\python.exe scripts\engineering_table.py
```

## 3. 下一步工作包

### WP1 · T6 补齐表面码 d=5 / d=7 学习重加权（P1，算力密集，建议先做）

**已有**：表面码 d=5 线路级 p=0.005 单点（2048 shots、1 seed）：`bp` 0.10352 → `bp_gnn` **0.06445（-38%）**，迭代 -43%，延迟 1.78× 更快；对照 d=3 的 -18%，**增益随码距增长**（`docs/M4_HGP_AND_SURFACE.md` 第 7.4 节）。

**待做**：把单点扩成曲线。

| 步 | 内容 | 配置改动 | 实测耗时（单点） |
|---|---|---|---|
| WP1a | d=5 线路级 p=0.003 与 p=0.008，各 1 seed | 复制 `configs/m4_rotated_surface_code_circuit_level_d5.json`，改 `experiment.name` 与 `experiment.noise.physical_error_rate` | 训练 18 min + 评测 5 min |
| WP1b | d=7 线路级 p=0.005，1 seed | 用 `configs/m4_rotated_surface_code_circuit_level_d7.json`（batch 需 ≤128，epochs 2） | 训练约 25 min + 评测约 10 min |
| WP1c | 补齐 5 个噪声率 × 3 seeds | 在每个配置上追加 seed 变体：改 `training.seed`（7/17/27）与 `splits.test_seeds`（301/302/303） | d=5 约 1.2 h/点，d=7 约 2 h/点 |

**命令模板**（M2 管线；注意 M4 的 `graph_qec.m4` 只支持 code_capacity 的 DEM 级码族，表面码线路级必须走 M2）：

```powershell
$py = ".\.venv\Scripts\python.exe"
Start-Process -FilePath $py -ArgumentList @('-m','graph_qec.m2',
  '--config','configs\m4_rotated_surface_code_circuit_level_d5.json',
  '--output-dir','results\m4_surface') -WorkingDirectory $PWD -WindowStyle Hidden `
  -RedirectStandardOutput 'results\logs\t6_surface_d5.out.log' `
  -RedirectStandardError  'results\logs\t6_surface_d5.err.log'
```

**验收**：`results/m4_surface/` 中出现 d=5 与 d=7 的 LER-p 曲线数据（含 3 seeds 的均值 ± 标准误）；`docs/M4_HGP_AND_SURFACE.md` 增补对应小节；`results/m5/ENGINEERING_TABLE.md` 重新生成。

**注意**：p=0.005 之外的噪声率需要**重新训练**（GNN 的边特征含 p，跨噪声率评测属于 M3 的迁移路径，不是同分布结果）；若要测迁移，用 `graph_qec.m3 --target-physical-error-rate`，但必须在文档里标明是迁移而非同分布。

### WP2 · T8 OSD 候选集学习（P1，纯 CPU，性价比最高）

**动机（三条独立证据指向同一结论）**：M2 用学习边际做 OSD 排序无改善；M3 的 OSD-0 回退在 d=3 上 67 修好/88 弄坏、且 288 个未收敛 shot 的残余重量全为 1（不存在只救不伤的阈值窗口）；M5 把学习后验接进 MWPM 无 LER 收益。共同的解释是：**逐机制边际回答「每个机制是否发生」，而候选基选择需要「哪些位构成可解的基」**。

**做法建议**：先实现 OSD-λ（combination sweep），再考虑 learning-to-rank；在 `src/graph_qec/m2_config.py` 的 `SUPPORTED_BENCHMARK_DECODERS` 注册新解码器名，加单测，与 `bp`/`bp_gnn`/`bp_gnn_osd` 做 McNemar 配对检验。

**验收**：新增解码器 + 单测 + 对照表（至少 d=3 repetition 与表面码 d=3 两个配置）；`docs/M3_HYBRID_DECODER.md` 增补小节。

### WP3 · T18 修正 Union-Find 的 peeling（P1，路线已定案）

`src/graph_qec/decoders/union_find.py` 的 `_decode_shot` 只累加合并边的 `fault_mask`，**缺少标准 Union-Find 的 peeling 步骤**，因此在表面码上失效（d=3 码容量 p=0.01：0.06311 vs MWPM 0.00214；d=5 为 0.226-0.476）。

**已定路线：修实现，不降级**（2026-10-15 决策，记录于 `docs/ROADMAP_TODO.md` 第 6.1 节）。不采用「把 Union-Find 限定为 repetition code 专用基线」的路线，因此它保持 P1。

**待做**：在 `_decode_shot` 中加入标准 Union-Find 的 peeling——簇内对生成树自叶向根剥离，只保留真正的 correction。改完必须重跑 `results/m1/`（repetition）与表面码扫描，并更新受影响的文档数字（`README.md`、M1 文档、`results/m4/SURFACE_BASELINE_TABLE.md`——该表当前不含 union_find 列）。工作量 8-12 人日。

**验收**：新增测试断言表面码 d=3 码容量 p=0.01 的 Union-Find LER 与 MWPM 同量级；所有引用了 Union-Find 的表格重新生成。

### WP4 · T10 多种子统计稳健性（P1，依赖 WP1）

- 对 4 个关键结论给出 3 seeds 的均值 ± 标准误与配对检验：d=5/d=7 表面码的 `bp` vs `bp_gnn`、HGP 跨尺寸迁移、MWPM 边权结论；
- 另需补：**repetition d=5 的先验强度在目标分布验证集上复核**（当前 `results/m3/m2_d5_eval/` 沿用源配置上限 1.00，未在 d=5 验证集上重选）。

**验收**：相关表格全部标注 shots 与 seed 数，并给出标准误。

## 4. 已知坑与操作纪律

1. **batch 大小**：表面码 d=5/d=7 训练必须 `batch_size=128`。1024 时逐边激活在 16 GB 上内存耗尽，进程被系统**静默杀死**（日志里没有 traceback，只在输出目录为空时才看得出来）。长跑后用 `Get-Process python` 与输出目录是否增长来确认存活。
2. **结果目录不可覆盖**：M2/M3/M4 的 CLI 在目标目录已存在时抛 `FileExistsError`。删除方式：已跟踪用 `git rm -r -q -f <dir>`，未跟踪用 `git clean -fdq -- <dir>`（先 `git clean -nd` 预演）。本环境的策略**拒绝** PowerShell 的 `Remove-Item -Recurse`。
3. **噪声率在 JSON 里的路径是 `experiment.noise.physical_error_rate`**，不是 `experiment.physical_error_rate`。改错路径会让不同 p 跑出**完全相同**的数字（已踩过一次，靠"p=0.001 与 p=0.01 结果逐位相同"才发现）。
4. **不要在 `results/*.json` 里做含反斜杠的路径替换**（`results\m3_fixed\` → `results\m3\` 会破坏 JSON 转义）。要改目录名就替换纯名字（`m3_fixed` → `m3`），改完用 Python 全量 `json.loads` 校验。
5. **torch 动态量化会把 `nn.Linear` 换成 `weight` 为可调用对象的模块**，GNN 前向的快路径对非 `nn.Linear` 层会自动回退到 concat 实现（`tests/test_gnn_forward_equivalence.py::test_forward_falls_back_for_non_linear_message_layers` 锁定）。不要删掉这个分支——删掉会让 `scripts/m5_quantization.py` 崩溃。
6. **交付范围内不得引用 `union_find` 的表面码数字**（T18）；`results/m4/README.md` 与 `docs/ROADMAP_TODO.md` 已声明。
7. **耗时预算先看实测**：BP 在表面码线路级为 d=3 242 µs/shot、d=5 8.1 ms/shot、d=7 46.9 ms/shot、d=9 127.9 ms/shot（`docs/BP_IMPLEMENTATION.md` 第 4 节）；GNN 前向 d=5 7.8 ms/shot、d=7 27.7-35.3 ms/shot（`results/m5/GNN_PERF.md`）。开新实验前先用 `scripts/probe_cpu_budget.py` 标定。
8. **提交时排除进行中的结果目录**（`git add` 指定路径，或确认目录为空），避免把半成品写进交付。
9. **统计纪律**：任何百分比结论都要给 shots、seed 数与标准误；2048 shots 的标准误约 0.005-0.008，只够给方向。

## 5. 未决事项（需决策）

| 编号 | 事项 | 影响 |
|---|---|---|
| D1 | 是否绑定远端仓库（GitHub 私有等） | **阻塞 T1 的 CI 首次运行**；当前无远端，本地磁盘故障即丢全部结果 |
| D2 | `LICENSE` 未确定 | 交付物缺一项 |
| D3 | 参考文献 PDF 策略（当前不入库，可由 `scripts/download_references.py` 重建） | 若要求离线自洽需改用 Git LFS |
| — | 是否启动 d=7（WP1b） | 单点约 35 min，3 seeds 全网格约 10 h |

## 6. 接手检查清单

- [ ] `git log --oneline -1` 确认在 `994a889` 或其后
- [ ] `pytest -q` 期望 62 passed
- [ ] `.\scripts\run_all.ps1 -SkipTests` 期望 18 s 全绿
- [ ] 读 `docs/ROADMAP_TODO.md` 第 0 与 2.0 节，确认交付范围与优先级定义
- [ ] 读第 4 节的 9 条纪律（尤其 batch 与结果目录两条）
- [ ] 确认 D1-D3 的决策状态（第 5 节）