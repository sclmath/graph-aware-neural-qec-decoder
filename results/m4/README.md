# M4 结果目录索引

| 路径 | 内容 |
|---|---|
| `GRAPH_STRUCTURE.md` / `graph_structure.json` | 跨码族图结构对比（repetition / 表面码 / 两个 HGP 码） |
| `surface_sweep.csv` | 旋转表面码基线扫描（MWPM / Union-Find / BP / BP+OSD，多噪声率 × d=3,5） |
| `hgp_rep3x3_to_hgp_hamming7x7/` | HGP 跨尺寸迁移（由 `scripts/m4_transfer.py` 生成） |

代码与配置：`src/graph_qec/codes/hgp.py`（HGP 构造与 DEM）、`src/graph_qec/m4_pipeline.py` + `m4.py`（DEM 级管线与 CLI）、`scripts/m4_graph_structure.py`、`scripts/m4_surface_sweep.py`、`configs/m4_*.json`。
## 已知问题

`surface_sweep.json` 中的 `union_find` 列**不可用**：该解码器缺少标准 Union-Find 的 peeling 步骤，在表面码上 LER 远高于 MWPM（d=3 码容量 p=0.01：0.06311 vs 0.00214；d=5：0.22607-0.47565）。因此 `SURFACE_BASELINE_TABLE.md` 不含该列。修复计划见 `docs/ROADMAP_TODO.md`（T18）。

| `THRESHOLD.md` | 阈值估计（由 `scripts/threshold_estimate.py` 从 `surface_sweep.json` 与 `../m4_threshold/surface_sweep.json` 生成）：MWPM 码容量 0.05 < p_th < 0.08 |
| `../m4_threshold/surface_sweep.{json,csv}` | 码容量阈值扫描（d=3/5，p=0.01-0.12，各 16384 shots），专为阈值定位扩展的高噪声率区间 |

实验总述见 `docs/M4_HGP_AND_SURFACE.md`。

表面码与 HGP 的学习重加权结果分别在 `results/m4_surface/`（线路级 d=3）、`results/m4_surface_cc/`（码容量 d=3 与 d=5 迁移）、`results/m4_hgp/`（两个 HGP 码）。

基线扫描明细：`SURFACE_BASELINE_TABLE.md`（由 `surface_sweep.json` 去重整理）。
