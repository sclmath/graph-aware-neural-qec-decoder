# M0：环境与数据链路

## 1. 阶段目标

M0 建立后续所有基线和模型共用的数据契约：

- 使用 Stim 生成 repetition-code memory 线路；
- 支持 `code_capacity` 与 `circuit_level` 两类噪声配置；
- 从原始 detector error model 联合采样 syndrome、logical observable 和 error mechanism 标签；
- 从可分解 DEM 构建 PyMatching 图并执行真实解码 smoke test；
- 使用固定随机种子，并对配置、样本、线路和 DEM 计算 SHA-256；
- 通过 JSON 配置和 CLI 生成可复现实验产物。

## 2. 环境

本机使用的隔离环境为项目根目录下的 `.venv`。核心版本在生成时写入每个 artifact 的 `manifest.json`。

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

当前 M0 直接依赖：

| 组件 | 版本 |
|---|---:|
| Python | 3.12.1 |
| Stim | 1.16.0 |
| PyMatching | 2.4.0 |
| NumPy | 2.5.3 |
| pytest | 9.1.1 |

## 3. 噪声映射

`code_capacity` 仅使用 `before_round_data_depolarization=p`，即只有数据比特发生退极化噪声。

`circuit_level` 对以下四个位置统一施加噪声率 `p`：

- `after_clifford_depolarization`
- `before_round_data_depolarization`
- `before_measure_flip_probability`
- `after_reset_flip_probability`

这种映射使 M0 的配置格式可以从 repetition code 平滑扩展到后续 surface code。

## 4. 执行

```powershell
.\.venv\Scripts\python.exe -m graph_qec.m0 `
  --config configs\m0_repetition_code_capacity.json `
           configs\m0_repetition_circuit_level.json `
  --output-dir artifacts\m0
```

每个配置输出一个独立目录：

```text
artifacts/m0/<artifact-name>/
├── circuit.stim
├── detector_error_model.dem
├── detector_error_model.decomposed.dem
├── samples.npz
└── manifest.json
```

`samples.npz` 包含：

- `detections`：形状 `(shots, num_detectors)`；
- `observables`：形状 `(shots, num_observables)`；
- `error_mechanisms`：形状 `(shots, num_dem_errors)`，供 M2 监督学习使用。

## 5. 验证

```powershell
.\.venv\Scripts\python.exe -m pytest
```

测试覆盖配置校验、线路维度、固定种子、机制标签、artifact 哈希校验，以及两类噪声 DEM 的 PyMatching 解码。

## 6. 验收结果

数据和测试结果记录在该文件末尾的“复现记录”中。M0 只有同时满足以下条件才视为完成：

1. 两类噪声配置均可生成 artifact；
2. 固定配置重复运行得到相同样本哈希；
3. 原始 DEM 与分解 DEM 均成功生成；
4. PyMatching 能读取分解 DEM 并批量解码；
5. 测试全部通过且 manifest 哈希复核通过。

## 7. 复现记录

执行日期：2026-10-03（Asia/Shanghai）。

测试结果：

```text
7 passed in 0.47s
```

正式 artifact：

| 噪声模型 | DEM error 数 | detector 数 | shots | PyMatching 逻辑错误 | LER |
|---|---:|---:|---:|---:|---:|
| code_capacity | 9 | 8 | 4096 | 2 | 0.00048828125 |
| circuit_level | 21 | 8 | 4096 | 39 | 0.009521484375 |

固定种子复核时，重新生成的 `samples`、`circuit` 和 `detector_error_model` 字段与已保存 manifest 完全一致。关键样本哈希为：

| 噪声模型 | configuration SHA-256 | detection SHA-256 |
|---|---|---|
| code_capacity | `efda914374558b905c96c2053ad894c82dd968232efd3d744ca85c1ff31dcc78` | `af161fefcc35746b7385380c41a358aea7679b35d4589dbfee05f64664599e00` |
| circuit_level | `a0c559fb599cc15d2884e10249900a58d454c656066cc4a42a57d4f6c36a73b1` | `2040e1221eb153e233d4d2c32c40f6a1f782186cbe863a6b70fb1a1503bf3245` |

所有 artifact 均位于 `artifacts/m0/`，且已通过 manifest 哈希复核。M0 可以冻结作为后续 M1 基线的数据接口。
