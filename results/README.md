# Results 索引

> **除本文件与 `results/m{3,4,5}/README.md` 外，`results/**/*.md` 均为脚本生成的实验输出，请勿手工编辑。**
> 需要改变口径时，修改对应生成脚本并重跑；最终结论与数字以 `docs/FINAL_REPORT.md` 为准。

| 目录 | 内容 | 生成/入口 |
|---|---|---|
| `m1/` | 经典基线 benchmark | `graph_qec.m1` |
| `m2/` | GNN 重加权 headline 与多种子 | `graph_qec.m2`、`scripts/summarize_m2.py` |
| `m3/` | 混合解码器、噪声/码距迁移、失效分析 | `graph_qec.m3`、`scripts/summarize_m3.py` |
| `m4/` | 表面码基线、图结构、阈值 | `scripts/m4_surface_sweep.py`、`scripts/threshold_estimate.py` |
| `m4_surface/`、`m4_surface_cc/`、`m4_hgp/` | 表面码与 HGP 的学习重加权与迁移 | `graph_qec.m4`、`scripts/m4_transfer.py` |
| `m5/` | CPU 工程性能、GNN 优化、量化、MWPM 对照 | `scripts/engineering_table.py` 等 |
| `t8/` | OSD-CS 探针与多种子汇总 | `scripts/t8_*` |
| `t9/` | 图特征 / top-k 消融 | `scripts/t9_*` |
| `t10/` | T6 30/30 点跨 seed 汇总 | `scripts/t10_multiseed_stats.py` |
| `logs/` | 运行日志 | 各驱动脚本 |
| `smoke/` | 端到端 smoke 临时产物（gitignore） | `scripts/run_all.ps1` |

## 人工维护的索引

- `results/m3/README.md`
- `results/m4/README.md`
- `results/m5/README.md`

这些文件只做目录导航；结论与数字以 `docs/FINAL_REPORT.md` 和对应专题文档为准。
