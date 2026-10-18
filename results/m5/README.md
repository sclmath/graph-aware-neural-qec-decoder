# M5 结果目录索引（`results/m5/`）

| 路径 | 内容 |
|---|---|
| `ENGINEERING_TABLE.md` | CPU 工程性能表（T11），由 `scripts/engineering_table.py` 自动生成 |
| `GNN_PERF.md` | GNN 前向优化（T5）：profile、改动、等价性与优化前后成本 |
| `QUANTIZATION.md` / `quantization.json` | GNN float32 vs 动态 int8 |
| `cpu_budget.json` | CPU 预算实测（向量化 BP 与 GNN） |
| `GNN_MWPM.md` / `gnn_mwpm.json` / `gnn_mwpm_cc/` | 重建 DEM 的 MWPM 对照（反例） |
| `gnn_mwpm_decomposed_cc/`、`gnn_mwpm_decomposed_cl/` | 保分解 + 相对重加权的正式结果 |

> 工程解释见 `docs/M5_ENGINEERING.md`；MWPM 对照细节见 `docs/M5_DECOMPOSED_MWPM.md`；BP 规范见 `docs/BP_IMPLEMENTATION.md`；完整数字以 `docs/FINAL_REPORT.md` 为准。本文件只做目录导航。
