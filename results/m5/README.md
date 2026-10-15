# M5 结果目录索引

| 路径 | 内容 |
|---|---|
| `QUANTIZATION.md` / `quantization.json` | GNN float32 vs 动态 int8：模型大小、单 shot 推理延迟、机制后验质量、以及接回 BP 后的 LER |
| `../docs/M5_ENGINEERING.md` | 向量化 BP 的设计、加速比与等价性测试；GPU 项的限制与迁移方案 |
| `../docs/BP_CORRECTNESS_FIX.md` | 向量化过程中发现的两个 BP 正确性缺陷及其对 M1–M3 结论的影响 |

> **注意**：`GNN_MWPM.md`、`gnn_mwpm.json`、`gnn_mwpm_cc/` 是"逐 shot 重建 DEM 再跑 MWPM"的**原型**输出，其数字**不可用**——控制实验（用 DEM 自己的先验重建）已经把 MWPM 从 0.0439 退化到 0.0679，说明重建丢掉了 Stim 的超边分解，M4/M5 报告只把它当作失败模式记录（见 `docs/M5_ENGINEERING.md` 第 5 节）。

## M5+：学习后验 → MWPM（保分解 + 相对重加权），2026-10-14

- 模块 `src/graph_qec/m5.py`；脚本 `scripts/m5_gnn_mwpm_decomposed.py`；测试 `tests/test_m5_decomposed_mwpm.py`（13 项）；报告 `docs/M5_DECOMPOSED_MWPM.md`
- 数据：`results/m5/gnn_mwpm_decomposed_cc/`（码容量 d=3，8192 shots）、`results/m5/gnn_mwpm_decomposed_cl/`（线路级 d=3，4096 shots）

修掉原型三个缺陷：丢掉 Stim `^` 分解、LLR 符号接反、逐机制概率原样代换（Stim 会按分量摊薄概率，必须用保尺度相对重加权）。
重写路径与基线**逐 shot 一致**（455/455、64/64，`mwpm_shift_zero.matches_baseline = true`）；原型路径的劣化被定量复现（588/455、73/64，边数 43 vs 35、106 vs 78）。
学习后验接 MWPM **无 LER 收益**：码容量 455 → 最好 451（s=0.75）、满强度 498；线路级 64 → 最好 63（s=0.25）、满强度 91。同配置下学习先验接 BP 仍为 -17%（185 → 153）。
逐 shot 重建匹配图约 2.8–2.9 ms/shot，比整条 BP+GNN 管线慢一个数量级以上。
