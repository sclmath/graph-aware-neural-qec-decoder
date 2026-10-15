# M4 结果目录索引

| 路径 | 内容 |
|---|---|
| `GRAPH_STRUCTURE.md` / `graph_structure.json` | 跨码族图结构对比（repetition / 表面码 / 两个 HGP 码） |
| `surface_sweep.csv` | 旋转表面码基线扫描（MWPM / Union-Find / BP / BP+OSD，多噪声率 × d=3,5） |
| `hgp_rep3x3_to_hgp_hamming7x7/` | HGP 跨尺寸迁移（由 `scripts/m4_transfer.py` 生成） |

代码与配置：`src/graph_qec/codes/hgp.py`（HGP 构造与 DEM）、`src/graph_qec/m4_pipeline.py` + `m4.py`（DEM 级管线与 CLI）、`scripts/m4_graph_structure.py`、`scripts/m4_surface_sweep.py`、`configs/m4_*.json`。
## Union-Find 列（2026-10-15 重跑）

`union_find` 列已由重写后的加权 Union-Find 重新生成（脚本 `scripts/t18_rerun.ps1`，日志 `results/logs/t18_rerun.log`）。修复前的旧实现缺少 peeling，在表面码上比 MWPM 差 29-600×；现在是 **1.00-1.41×**：

| 配置 | MWPM | Union-Find | 比值 |
|---|---:|---:|---:|
| d=3 码容量（p=0.01/0.02/0.05） | 0.00214 / 0.00916 / 0.04877 | 0.00214 / 0.00916 / 0.04877 | 1.00 |
| d=3 线路级（p=0.003/0.005/0.008） | 0.00610 / 0.01599 / 0.04089 | 0.00610 / 0.01685 / 0.04126 | 1.00-1.05 |
| d=5 码容量（p=0.01/0.02/0.05） | 0.00037 / 0.00262 / 0.04016 | 0.00049 / 0.00354 / 0.04517 | 1.12-1.35 |
| d=5 线路级（p=0.005） | 0.01416 | 0.02002 | 1.41 |

`SURFACE_BASELINE_TABLE.md` 仍只列 MWPM/BP/BP+OSD（保持历史口径），但 `surface_sweep.json` 的 `union_find` 列现在可安全引用。

| `THRESHOLD.md` | 阈值估计（由 `scripts/threshold_estimate.py` 从 `surface_sweep.json` 与 `../m4_threshold/surface_sweep.json` 生成）：MWPM 码容量 0.05 < p_th < 0.08 |
| `../m4_threshold/surface_sweep.{json,csv}` | 码容量阈值扫描（d=3/5，p=0.01-0.12，各 16384 shots），专为阈值定位扩展的高噪声率区间 |

实验总述见 `docs/M4_HGP_AND_SURFACE.md`。

表面码与 HGP 的学习重加权结果分别在 `results/m4_surface/`（线路级 d=3）、`results/m4_surface_cc/`（码容量 d=3 与 d=5 迁移）、`results/m4_hgp/`（两个 HGP 码）。

基线扫描明细：`SURFACE_BASELINE_TABLE.md`（由 `surface_sweep.json` 去重整理）。
