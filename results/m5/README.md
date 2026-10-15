# M5 结果目录索引（`results/m5/`）

| 路径 | 内容 |
|---|---|
| `GNN_PERF.md` | GNN 前向优化（T5）：profile、三项改动、数值等价性、优化前后 µs/shot 与峰值 RSS |
| `QUANTIZATION.md` / `quantization.json` | GNN float32 vs 动态 int8：模型大小、单 shot 推理延迟、机制后验质量，以及接回 BP 后的 LER |
| `CPU_BUDGET.md` 对应的 `cpu_budget.json` | CPU 预算实测（向量化 BP 与 GNN 在 d=3/5/7/9 的 µs/shot、收敛率、峰值 RSS、训练单步成本），由 `scripts/probe_cpu_budget.py` 生成 |
| `gnn_mwpm.json` / `GNN_MWPM.md` / `gnn_mwpm_cc/` | 把学习后验直接接进 MWPM 的**对照实验**：逐 shot 重建 DEM 会丢掉 Stim 的 `^` 分解，MWPM 从 0.0439 退化到 0.0679（用 DEM 自己的概率重建也会退化），因此该路径的 LER 数字只用于说明分解必须保留（见 `docs/M5_ENGINEERING.md` 第 5 节） |
| `gnn_mwpm_decomposed_cc/`、`gnn_mwpm_decomposed_cl/` | 保分解 + 相对重加权的正式结果（码容量 d=3 / 线路级 d=3） |
| `../docs/M5_ENGINEERING.md` | 向量化 BP 的设计与加速比、int8 量化、GPU 迁移路径 |
| `../docs/M5_DECOMPOSED_MWPM.md` | 学习后验接入 MWPM 的阶梯式对照与结论 |
| `../docs/BP_IMPLEMENTATION.md` | BP 算法规范、批量化设计与等价性保证 |