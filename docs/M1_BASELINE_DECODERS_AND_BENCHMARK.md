# M1：经典基线解码器与 Benchmark

> **⚠ 2026-10-13 晚更新：本文档的 BP 系数字已被推翻。**
> `bp` / `bp_osd` 使用了有缺陷的 min-sum 实现（见 `docs/BP_CORRECTNESS_FIX.md`），修正后
> d=3 circuit-level 上 `bp` 0.01587 → **0.01294**（与 Union-Find 打平）、`bp_osd` 0.01782 → 0.01489，
> 码容量下 `bp` 与 MWPM 完全一致。修正后的结果在 `results/m1_fixed/`，MWPM / Union-Find 的数字不受影响。


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

`UnionFindDecoder` 直接解析分解 DEM 的 graphlike component：

- 单 detector target 连接到虚拟 boundary；
- 双 detector target 形成内部边；
- 权重为 `log((1-p)/p)`；
- 保留每个 component 的 observable fault mask；
- 按权重增长并合并奇偶性为奇的 cluster。

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

M1 只实现 OSD-0；更高阶 OSD combination sweep 留给 M3 的混合解码器扩展。

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

执行日期：2026-10-03（Asia/Shanghai）。测试结果：

```text
13 passed in 0.82s
```

### 7.1 Code-capacity，4096 shots，p=0.01

| Decoder | Logical errors | LER | Mean per-shot | Throughput | RSS delta | Python peak |
|---|---:|---:|---:|---:|---:|---:|
| MWPM | 2 | 0.00048828125 | 0.0335 us | 29,871,645 shot/s | 24 KiB | 118,764 B |
| Union-Find | 2 | 0.00048828125 | 15.222 us | 65,695 shot/s | 49 KiB | 119,008 B |
| BP | 2 | 0.00048828125 | 15.861 us | 63,049 shot/s | 152 KiB | 140,320 B |
| BP+OSD-0 | 2 | 0.00048828125 | 14.340 us | 69,736 shot/s | 78 KiB | 194,302 B |

该低噪声设置下四种解码器的 LER 相同。MWPM 使用原生 C++ batch 实现，延迟明显最低。

### 7.2 Circuit-level，4096 shots，p=0.01

| Decoder | Logical errors | LER | Mean per-shot | Throughput | RSS delta | Python peak |
|---|---:|---:|---:|---:|---:|---:|
| MWPM | 39 | 0.009521 | 0.1906 us | 5,247,649 shot/s | 0 KiB* | 118,456 B |
| Union-Find | 53 | 0.012939 | 35.422 us | 28,231 shot/s | 29 KiB | 117,144 B |
| BP | 65 | 0.015869 | 235.141 us | 4,253 shot/s | 1.14 MiB | 1,035,455 B |
| BP+OSD-0 | 73 | 0.017822 | 209.445 us | 4,775 shot/s | 1.21 MiB | 1,562,276 B |

\* MWPM 的 RSS delta 为 0，表示执行期间没有观察到新的 working-set page；其绝对 peak RSS 仍记录在 JSON 中。

BP/BP+OSD 的诊断：

- BP convergence：4003/4096 = 97.73%；
- BP syndrome consistency：97.73%；
- BP+OSD OSD 触发：93/4096 = 2.27%；
- BP+OSD syndrome consistency：100%；
- 平均 OSD rank：8。

本设置下 BP 的原始 LER 低于当前 OSD-0，主要因为单独 BP 在未收敛 shot 上仍直接输出 posterior 硬判决，而 BP+OSD 强制 syndrome 一致，且 OSD-0 当前尚未做候选组合搜索。两者标准误约 0.002，差异不构成最终算法结论。M3 会研究更高阶 OSD、候选剪枝和 GNN 重加权。

## 8. 验收结论

M1 的四个经典解码器、统一配置、LER/延迟/内存 benchmark、CSV/JSON 结果输出和回归测试均已完成。结果产物位于 `results/m1/`，并已验证相同配置下四个 decoder 的 prediction SHA-256 可重复。
