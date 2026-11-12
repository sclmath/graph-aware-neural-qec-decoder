# Graph-Aware Neural QEC Decoder

面向表面码、HGP 码与量子 LDPC 码的图感知混合解码器研究仓库。项目把量子纠错解码建模为带噪图上的推断与组合优化问题，研究置信传播（BP）、匹配、OSD 与图神经网络（GNN）之间的组合方式，并同时报告逻辑错误率、解码延迟与内存开销。

当前仓库包含第一阶段 CPU-only 实验的代码、配置、测试、结果和完整技术报告。阶段范围与后续方向见 [研究路线图](docs/ROADMAP.md)。

## 当前实现

| 维度 | 已实现 |
|---|---|
| 码族 | repetition code；旋转表面码 d=3/5/7；HGP [[13,1,3]]、[[58,16,3]] |
| 噪声 | code-capacity、circuit-level depolarizing、detector error model |
| 经典解码 | MWPM、加权 Union-Find、BP、BP+OSD |
| 混合解码 | GNN 边权重重估、学习先验接入 BP、OSD-0 / OSD-CS 后处理 |
| 工程评测 | CPU 单 shot 延迟、吞吐、峰值内存、BP 迭代数与 OSD 触发率 |
| 统计 | 多种子配对分析、McNemar 检验、LER-p 曲线与阈值估计 |

尚未实现或未纳入第一阶段交付：结构化量子 LDPC（非 HGP）、d=9 实验、GPU 性能数字、时序编码器和端到端可微 BP。详见 [路线图](docs/ROADMAP.md#2-当前限制与证据缺口)。

## 核心发现

1. **机制判别容易，但机制边际本身不保证 LER 收益。** GNN 将 error mechanism 后验 AUC 从 0.62 提升到 0.99 以上；在 d=3 repetition 上，将同一预测接入 BP 没有显著 LER 改善，稳定收益是降低 BP 迭代次数。
2. **学习先验的收益在 BP 强度中等时最大。** 表面码线路级 5 个噪声率 × 3 seeds 的 30/30 点显示：码距轴为 d=3 −29.0% ± 2.4%、d=5 −37.1%、d=7 −25.1%，峰值出现在 d=5。
3. **真正的杠杆是候选基质量。** OSD-0 在 10 个表面码点全部有害；改为 OSD-CS(λ) 后，表面码 d=3 的 `bp_gnn_osd_cs8` 达到 0.01913（相对 `bp` −52%），但 CS 相对 `bp_gnn` 的额外增益只在 d=7 低噪声端出现方向性证据。
4. **加权 Union-Find 达到可用基线。** 表面码 d=3 code-capacity LER 与 MWPM 逐位一致，10 个扫描点相对 MWPM 为 1.00–1.41×；所有 correction 均满足 syndrome 约束。
5. **图结构决定解码器可用性。** 线路级表面码 DEM 是稠密超图；HGP 码不可匹配，MWPM / Union-Find 不可用，BP 系是通用选择。

完整数字、统计口径、适用范围和失败案例以 [第一阶段技术报告](docs/FINAL_REPORT.md) 为准。

## 快速开始

要求 Python 3.10+。CPU-only 环境即可运行测试和 smoke；训练 GNN 需要 PyTorch。

```powershell
# Windows PowerShell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev,ml,analysis]"

$env:PYTHONPATH = "src"
$env:PYTHONUTF8 = "1"
.\.venv\Scripts\python.exe -m pytest -q
pwsh -File .\scripts\run_all.ps1
```

Linux/macOS 的创建虚拟环境、安装与 smoke 方式见 [复现指南](docs/REPRODUCIBILITY.md)。若需要严格的 CPU-only torch，请先按 PyTorch 官方 CPU wheel 索引安装 `torch`，再安装本项目依赖。

## 仓库结构

```text
src/graph_qec/         核心实现：码构造、数据管线、模型与解码器
configs/               可复现实验配置
scripts/               实验、汇总、绘图与维护脚本
tests/                 单元测试与回归测试
docs/                  技术报告、复现指南、里程碑与专题文档
results/               实验结果与自动生成报告
```

## 文档导航

| 需要什么 | 文档 |
|---|---|
| 文档职责、阅读顺序与维护规则 | [docs/INDEX.md](docs/INDEX.md) |
| 完整技术报告与所有正式数字 | [docs/FINAL_REPORT.md](docs/FINAL_REPORT.md) |
| 环境、测试、全量实验与结果再生成 | [docs/REPRODUCIBILITY.md](docs/REPRODUCIBILITY.md) |
| 当前限制、证据缺口与后续方向 | [docs/ROADMAP.md](docs/ROADMAP.md) |
| M0–M5 实现细节 | [M0](docs/M0_ENVIRONMENT_AND_DATA_PIPELINE.md) · [M1](docs/M1_BASELINE_DECODERS_AND_BENCHMARK.md) · [M2](docs/M2_GNN_REWEIGHTING.md) · [M3](docs/M3_HYBRID_DECODER.md) · [M4](docs/M4_HGP_AND_SURFACE.md) · [M5](docs/M5_ENGINEERING.md) |
| BP 算法规范 | [docs/BP_IMPLEMENTATION.md](docs/BP_IMPLEMENTATION.md) |
| OSD-CS 专题 | [docs/OSD_CANDIDATE_SET.md](docs/OSD_CANDIDATE_SET.md) |
| 加权 Union-Find | [docs/UNION_FIND.md](docs/UNION_FIND.md) |
| MWPM 边权重重加权 | [docs/MWPM_REWEIGHTING.md](docs/MWPM_REWEIGHTING.md) |
| 文献综述与元数据 | [综述](docs/references/LITERATURE_REVIEW.md) · [文献表](docs/references/references.md) |
| 结果目录与生成物 | [results/README.md](results/README.md) |

## 复现与结果维护

- 测试和快速验证：`pytest -q`、`pwsh -File scripts/run_all.ps1`。
- 完整实验、长跑与表格再生成命令统一收录在 [docs/REPRODUCIBILITY.md](docs/REPRODUCIBILITY.md)，其他文档只链接，不复制命令。
- `results/**/*.md` 除少量 `README.md` 外均由脚本生成；修改统计口径时应改生成脚本并重跑，而不是手改结果文件。
- 科学结论只写入 [docs/FINAL_REPORT.md](docs/FINAL_REPORT.md)，README 仅保留摘要。

## 适用范围

本仓库的实验结论主要基于单机 CPU 环境、小到中等码距和有限 shots。它适合复现混合解码器的方法与趋势，不应直接外推为 GPU 吞吐、大规模实时解码或硬件部署结论。使用具体数字前，请同时阅读技术报告中的统计口径和限制说明。

## 许可证

本项目采用 [MIT License](LICENSE)。
