# M4 结果目录索引

| 路径 | 内容 |
|---|---|
| `GRAPH_STRUCTURE.md` / `graph_structure.json` | 跨码族图结构对比（repetition / 表面码 / 两个 HGP 码） |
| `surface_sweep.csv` / `surface_sweep.json` | 旋转表面码基线扫描（MWPM / Union-Find / BP / BP+OSD，多噪声率 × d=3,5） |
| `SURFACE_BASELINE_TABLE.md` | 表面码基线表的去重整理 |
| `THRESHOLD.md` | 阈值估计（由 `scripts/threshold_estimate.py` 生成） |
| `../m4_threshold/surface_sweep.{json,csv}` | 码容量阈值扫描（d=3/5，p=0.01–0.12，各 16384 shots） |
| `hgp_rep3x3_to_hgp_hamming7x7/` | HGP 跨尺寸迁移（由 `scripts/m4_transfer.py` 生成） |

代码与配置：`src/graph_qec/codes/hgp.py`（HGP 构造与 DEM）、`src/graph_qec/m4_pipeline.py` + `m4.py`（DEM 级管线与 CLI）、`scripts/m4_graph_structure.py`、`scripts/m4_surface_sweep.py`、`configs/m4_*.json`。

表面码与 HGP 的学习重加权结果分别在 `results/m4_surface/`、`results/m4_surface_cc/`、`results/m4_hgp/`。

> Union-Find 重跑细节见 `docs/T18_UNION_FIND_ANALYSIS.md`；实验总述见 `docs/M4_HGP_AND_SURFACE.md`；完整数字以 `docs/FINAL_REPORT.md` 为准。本文件只做目录导航。
