# M1：经典基线解码器与 Benchmark

## 1. 阶段目标

M1 建立后续 GNN 重加权和混合解码器必须共同使用的经典基线：

- MWPM；
- Union-Find；
- 置信传播 BP；
- BP + OSD-0；
- 统一的 LER、延迟、吞吐和内存测试框架；
- 固化可校验的 JSON 实验配置格式。

## 2. 统一接口

所有解码器实现 `graph_qec.decoders.Decoder`：

```python
result = decoder.decode_batch(detections)
result.predictions   # shape=(shots, num_observables)
result.corrections   # BP/BP+OSD 提供显式 error-mechanism correction
result.diagnostics   # 迭代次数、收敛率、OSD 触发率、图规模等
```

统一接口保证后续 GNN 重加权模块可以替换或包裹任意经典解码器，而不改变 benchmark 和数据管线。

## 3. 解码器实现

### 3.1 MWPM

`MWPMDecoder` 从 Stim 的可分解 DEM 构建 PyMatching `Matching`，使用原生 `decode_batch()` 作为精度和延迟主基线。

### 3.2 Union-Find

`UnionFindDecoder` 直接解析分解 DEM 的 graphlike component，并实现 **Delfosse–Nickerson 的加权 Union-Find**（2026-10-15 重写，见 `docs/T18_UNION_FIND_ANALYSIS.md`）：

- 单 detector target 连接到虚拟 boundary；双 detector target 形成内部边；权重为 `log((1-p)/p)`；保留每个 component 的 observable fault mask；
- **half-edge 生长**：每个缺陷是 parity 为 1 的 cluster，前沿按权重逐半条边推进；两条前沿在同一条边上相遇即融合（因此簇会在中途相遇，而不是等一方先撞到 boundary 后冻结）；
- 簇的缺陷数为偶或触到 boundary 即冻结；融合后重新变奇的簇会解冻并从延迟的前沿继续；
- 对生长出的边集 ε' 跑 **erasure peeling（带 syndrome 翻转）**；peeling 若停在 2-core 上，则用该 core 最小生成森林上的 T-join 收尾。

这里不直接使用 PyMatching 合并后的 `edges()`，因为平行边合并只保留部分 `fault_ids`，会给 Union-Find 引入不必要的 logical-label 丢失。

### 3.3 BP

`BPDecoder` 在原始 DEM 的 Tanner 图上运行 normalized min-sum BP：

$$H e = s,\qquad L e = \ell.$$

每个 DEM `error` instruction 是一个变量，因此原始 DEM 的 hyperedge 不会被拆成相互独立的边。支持参数：

- `max_iterations`；
- `min_sum_scaling`；
- `damping`。

BP 达到 syndrome 一致时立即停止。若未收敛，仍输出当前最优硬判决；因此单独 BP 的部分 shot 可能不满足 syndrome 约束，这一过程指标会明确记录在 `syndrome_consistency_rate` 中。

### 3.4 BP + OSD

`BPOSDDecoder` 仅在 BP 未收敛的 shot 上执行 OSD-0：

1. 按 BP posterior 的可靠性对校验矩阵列排序；
2. 对二进制矩阵执行 GF(2) Gauss-Jordan 消元；
3. 固定非 pivot 位，求解 pivot 位；
4. 输出满足 syndrome 约束的 correction。

M1 只实现 OSD-0；更高阶 OSD（OSD-λ / combination sweep）见 `docs/ROADMAP_TODO.md`（T8）。

## 4. 固化的实验配置

每个 M1 配置使用固定 `schema_version`：

```json
{
  "schema_version": 1,
  "name": "m1_repetition_circuit_level",
  "experiment": {
    "name": "repetition",
    "seed": 20261003,
    "code": {"family": "repetition_code", "distance": 3, "rounds": 3},
    "noise": {"model": "circuit_level", "physical_error_rate": 0.01},
    "sampling": {"shots": 4096}
  },
  "benchmark": {
    "decoders": ["mwpm", "union_find", "bp", "bp_osd"],
    "warmup_runs": 1,
    "timed_runs": 5,
    "max_shots": 4096
  },
  "decoder_parameters": {
    "bp": {"max_iterations": 32, "min_sum_scaling": 0.75, "damping": 0.0},
    "bp_osd": {"max_iterations": 32, "min_sum_scaling": 0.75, "damping": 0.0, "osd_order": 0}
  }
}
```

配置在载入时进行类型、范围和 decoder 名称校验，并计算稳定 SHA-256。配置对应文件位于 `configs/m1_*.json`。

## 5. Benchmark 指标

每个 decoder 输出：

- `logical_errors` 和 `logical_error_rate`；
- LER 的二项分布标准误；
- 固定 batch 的 latency 原始 runs、mean total time 和 mean per-shot time；
- throughput；
- 独立内存测量中的 process peak RSS、RSS delta 和 Python `tracemalloc` peak；
- prediction SHA-256；
- decoder 原生诊断量；
- BP/BP+OSD 的 syndrome 一致 shot 数与比率。

延迟测量包含 warmup，但排除数据生成和内存采样。内存测量单独执行一次，避免采样线程和 `tracemalloc` 污染延迟数据。

## 6. 执行与验证

```powershell
.\.venv\Scripts\python.exe -m graph_qec.m1 `
  --config configs\m1_repetition_code_capacity.json `
           configs\m1_repetition_circuit_level.json `
  --output-dir results\m1

.\.venv\Scripts\python.exe -m pytest
```

测试覆盖：

- DEM 校验矩阵、observable 矩阵和 prior 解析；
- MWPM 与 Union-Find batch 输出和固定种子复现；
- BP correction 维度及 non-convergence 记录；
- BP+OSD syndrome 一致性；
- benchmark 配置 round-trip；
- 四解码器 benchmark smoke test。

## 7. 实测结果

执行环境：Windows / Python 3.12 / CPU-only（Intel i5-12400）。回归测试：`pytest` 全绿。

### 7.1 Code-capacity，4096 shots，p=0.01

| Decoder | Logical errors | LER | Mean per-shot | Throughput | RSS delta | Python peak |
|---|---:|---:|---:|---:|---:|---:|
| MWPM | 2 | 0.000488 | 0.030 us | 33,673,134 shot/s | 20 KiB | 104,127 B |
| Union-Find | 2 | 0.000488 | 6.468 us | 154,608 shot/s | 28 KiB | 103,152 B |
| BP | 2 | 0.000488 | 0.310 us | 3,222,659 shot/s | 52 KiB | 1,143,487 B |
| BP+OSD-0 | 2 | 0.000488 | 0.287 us | 3,490,889 shot/s | 44 KiB | 1,143,359 B |

该低噪声设置下四种解码器的 LER 相同。MWPM 使用原生 C++ batch 实现，延迟明显最低。

### 7.2 Circuit-level，4096 shots，p=0.01

| Decoder | Logical errors | LER | Mean per-shot | Throughput | RSS delta | Python peak |
|---|---:|---:|---:|---:|---:|---:|
| MWPM | 39 | 0.009521 | 0.138 us | 7,268,855 shot/s | 36 KiB | 104,211 B |
| Union-Find | 37 | 0.009033 | 10.677 us | 93,656 shot/s | 36 KiB | 103,855 B |
| BP | 53 | 0.012939 | 2.334 us | 428,478 shot/s | 1.88 MiB | 5,592,025 B |
| BP+OSD-0 | 61 | 0.014893 | 3.868 us | 258,507 shot/s | 1.97 MiB | 5,591,913 B |

\* `RSS delta` 是执行期间 working set 的峰值增量，量级在数十 KiB 时可视为分配抖动；各解码器的绝对 peak RSS 记录在 `benchmark.json` 中。

BP/BP+OSD 的诊断：

- BP 收敛：4043/4096 = 98.71%；
- BP syndrome 一致率：98.71%；
- BP+OSD 的 OSD 触发：53/4096 = 1.29%；
- BP+OSD syndrome 一致率：100%。

本设置下 BP 的原始 LER 低于当前 OSD-0，主要因为单独 BP 在未收敛 shot 上仍直接输出 posterior 硬判决，而 BP+OSD 强制 syndrome 一致，且 OSD-0 当前尚未做候选组合搜索。两者标准误约 0.002，差异不构成算法结论。更高阶 OSD、候选剪枝与 GNN 重加权见 `docs/M3_HYBRID_DECODER.md` 与 `docs/ROADMAP_TODO.md`（T8）。

## 8. 验收结论

M1 的四个经典解码器、统一配置、LER/延迟/内存 benchmark、CSV/JSON 结果输出和回归测试均已完成。结果产物位于 `results/m1/`，并已验证相同配置下四个 decoder 的 prediction SHA-256 可重复。
