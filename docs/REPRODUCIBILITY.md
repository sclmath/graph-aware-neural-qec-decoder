# 复现指南

- **适用范围**：第一阶段 CPU-only 实验、测试、结果汇总与文档再生成
- **正式结论**：以 [`FINAL_REPORT.md`](FINAL_REPORT.md) 为准
- **结果维护**：`results/**/*.md` 除人工目录索引外均由脚本生成，不手工修改数字

本文是仓库中环境、命令和长跑流程的唯一事实源。README、技术报告、里程碑和结果索引只保留最短入口，不复制完整命令。

## 1. 环境要求

- Python 3.10 或 3.12（CI 覆盖这两个版本）
- Windows PowerShell 或 PowerShell 7（仓库中的长跑与 smoke 脚本以 `.ps1` 提供）
- CPU-only 可完成测试、smoke 与第一阶段实验
- 训练 GNN 需要 PyTorch；GPU 不是第一阶段复现的前提

### 1.1 安装依赖

Windows PowerShell：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev,ml,analysis]"

$env:PYTHONPATH = "src"
$env:PYTHONUTF8 = "1"
```

Linux/macOS：

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev,ml,analysis]"
export PYTHONPATH=src
export PYTHONUTF8=1
```

如需严格控制为 CPU-only torch，可先使用 PyTorch 官方 CPU wheel 索引安装 `torch`，再安装本项目：

```bash
python -m pip install --index-url https://download.pytorch.org/whl/cpu torch
python -m pip install -e ".[dev,ml,analysis]"
```

## 2. 快速验证

```powershell
# 单元测试
.\.venv\Scripts\python.exe -m pytest -q

# 端到端 smoke：单测 + M0 + M1 + CPU 探针 + M2 汇总
pwsh -File .\scripts\run_all.ps1

# 跳过单测、只检查数据与脚本链路
pwsh -File .\scripts\run_all.ps1 -SkipTests

# 追加 M2 训练与 M3 扫描，耗时明显增加
pwsh -File .\scripts\run_all.ps1 -Full
```

smoke 的临时产物写入 `results/smoke/`，该目录不入库，可随时删除并重建。

## 3. 核心实验

以下命令均从仓库根目录执行，并假定已设置 `PYTHONPATH=src`。

### 3.1 经典基线与表面码扫描

```powershell
# M1 基线 benchmark
.\.venv\Scripts\python.exe -m graph_qec.m1 `
  --config configs\m1_repetition_circuit_level.json `
  --output-dir results\m1

# 重建加权 Union-Find 基线与表面码扫描
pwsh -File .\scripts\t18_rerun.ps1
```

### 3.2 GNN 重加权与迁移

```powershell
# 示例：repetition d=3 同分布训练与评测
.\.venv\Scripts\python.exe -m graph_qec.m2 `
  --config configs\m2_learned_basis_repetition_circuit_level_d3.json `
  --output-dir results\m2

# 汇总与绘图
.\.venv\Scripts\python.exe scripts\summarize_m2.py --results-dir results\m2
.\.venv\Scripts\python.exe scripts\plot_m2_results.py --results-dir results\m2
```

其他噪声率、码距和迁移配置位于 `configs/m2_*.json`、`configs/m3_*.json` 与 `configs/m4_*.json`。

### 3.3 表面码 d=5/d=7 网格

```powershell
.\.venv\Scripts\python.exe scripts\t6_surface_grid.py --print-plan
.\.venv\Scripts\python.exe scripts\t6_surface_grid.py --budget-minutes 720
```

网格支持断点续跑：已有结果会被跳过。统计口径见 [`FINAL_REPORT.md`](FINAL_REPORT.md) §4.6。

### 3.4 多种子汇总与阈值

```powershell
.\.venv\Scripts\python.exe scripts\t10_multiseed_stats.py `
  --results-dir results\m4_surface --output-dir results\t10

.\.venv\Scripts\python.exe scripts\threshold_estimate.py `
  --inputs results\t10\surface_sweep_mean.json results\m4\surface_sweep.json results\m4_threshold\surface_sweep.json `
  --output results\m4\THRESHOLD.md
```

### 3.5 OSD-CS 与消融

```powershell
.\.venv\Scripts\python.exe scripts\t8_osd_cs_study.py `
  --config <run>\config.json `
  --checkpoint <run>\model_state.pt `
  --sweeps 0 2 4 6 8 `
  --output-dir results\t8\<tag>

.\.venv\Scripts\python.exe scripts\t8_d7_multiseed.py `
  --json results\t8\d7_multiseed.json `
  --output results\t8\D7_MULTISEED.md

.\.venv\Scripts\python.exe scripts\t9_multiseed.py `
  --results-dir results\t9 --prefix surface_d3 `
  --output results\t9\SURFACE_D3_MULTISEED.md
```

方法说明见 [`OSD_CANDIDATE_SET.md`](OSD_CANDIDATE_SET.md)。

### 3.6 工程性能表

```powershell
.\.venv\Scripts\python.exe scripts\probe_cpu_budget.py `
  --distances 3 --gnn-distances 5 7 `
  --json results\m5\cpu_budget.json

.\.venv\Scripts\python.exe scripts\engineering_table.py
```

### 3.7 长跑链

`scripts/session4_seeds.ps1` 串联表面码网格、OSD-CS、消融、迁移多种子与表格重生成，适合无人值守运行：

```powershell
# 先预演，确认计划
pwsh -File scripts\session4_seeds.ps1 -Stage all -DryRun

# 实跑
pwsh -File scripts\session4_seeds.ps1 -Stage all
```

长跑前应确认磁盘空间、随机种子和输出目录。脚本会跳过已有结果，但仍建议先运行 `-DryRun`。

## 4. 文献数据

参考文献 PDF 不纳入 Git；元数据、BibTeX 和下载清单在 `docs/references/`。重新下载：

```powershell
.\.venv\Scripts\python.exe scripts\download_references.py `
  --references docs\references\references.md `
  --output docs\references\references_pdfs
```

下载需要网络访问，并受论文来源和第三方版权约束。

## 5. 结果与文档再生成

- 原始运行目录、JSON/CSV 与图表写入 `results/`。
- 汇总 Markdown 由 `scripts/summarize_*.py`、`scripts/t*_multiseed.py`、`scripts/threshold_estimate.py` 等生成。
- 修改统计口径时，先改生成脚本，再重跑并检查 diff；不要手工改生成文件中的数字。
- 正式结论发生变化时，先更新 [`FINAL_REPORT.md`](FINAL_REPORT.md)，再从报告同步 README 摘要。

## 6. 可重复性说明

- 配置中的训练种子、切分种子、噪声率、码距和 shots 应随结果一起保留。
- 跨 seed 推断应使用 seed 间实测散布，不应把所有 shots 直接合并后按二项分布计算显著性。
- 不同硬件上的绝对延迟不可直接比较；性能结论应同时记录 CPU/GPU 型号、batch 大小与测量方式。
- 第一阶段的结果基于有限 shots，部分配置仍为单 seed；具体证据强度见技术报告 §7。
