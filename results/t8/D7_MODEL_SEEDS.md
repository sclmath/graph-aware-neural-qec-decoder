# T8 · d=7 OSD-CS 探针（模型 + 数据都换）

由 `scripts/t8_d7_model_seeds.py` 自动生成，勿手改。

**口径**：每个目录 = 一个**模型 seed 自己的 checkpoint**，评测用**该 seed 自己的**
1024-shot 测试集（模型 seed 偏移同时移动 `training.seed` 与全部 split seed）。
种子是重复单位，因此下表给逐 seed Δ 与**跨 seed 均值 ± SE**；不把不同 seed 的 shot
求和（那会把模型间散布当成二项噪声）。对照：只换测试集的口径见
`results/t8/D7_MULTISEED.md`（`scripts/t8_d7_multiseed.py`）。

## p = 0.003　（3 个模型 seed：s1, s2, s3；每 seed 1024 shots）

| 模型 seed | 目录 | bp | bp_gnn | `bp_gnn_osd_cs0` | `bp_gnn_osd_cs4` | 未收敛 shot |
|---|---|---:|---:|---:|---:|---:|
| s1 | `d7_p0p003_probe` | 0.15234 | 0.08203 | 0.09570 | 0.05078 | 387 |
| s2 | `d7_p0p003_probe_s2model` | 0.15332 | 0.09863 | 0.16211 | 0.10645 | 570 |
| s3 | `d7_p0p003_probe_s3model` | 0.15234 | 0.12012 | 0.17773 | 0.09961 | 657 |

### 跨 seed 配对（种子是重复单位）

ΔLER = LER(A) − LER(B)，**负值表示 A 更好**；相对一列以该配对的 B 为基准。

| 配对 | 逐 seed ΔLER | 跨 seed 均值 ± SE | 相对 B |
|---|---|---:|---:|
| `bp_gnn` − `bp_gnn_osd_cs0` | -0.01367 / -0.06348 / -0.05762 | -0.04492 ± 0.01572 | -30.9% |
| `bp_gnn_osd_cs0` − `bp_gnn_osd_cs4` | +0.04492 / +0.05566 / +0.07812 | +0.05957 ± 0.00978 | +69.6% |
| `bp_gnn` − `bp_gnn_osd_cs4` | +0.03125 / -0.00781 / +0.02051 | +0.01465 ± 0.01165 | +17.1% |
| `bp` − `bp_gnn_osd_cs4` | +0.10156 / +0.04688 / +0.05273 | +0.06706 ± 0.01734 | +78.3% |

### 每个 seed 的配对 McNemar（单份 1024-shot 测试集，仅供方向）

| 模型 seed | 配对 | 只 A 错 | 只 B 错 | z |
|---|---|---:|---:|---:|
| s1 | `bp_gnn` vs `bp_gnn_osd_cs0` | 51 | 65 | +1.30 |
| s1 | `bp_gnn_osd_cs0` vs `bp_gnn_osd_cs4` | 56 | 10 | -5.66 |
| s1 | `bp_gnn` vs `bp_gnn_osd_cs4` | 67 | 35 | -3.17 |
| s2 | `bp_gnn` vs `bp_gnn_osd_cs0` | 53 | 118 | +4.97 |
| s2 | `bp_gnn_osd_cs0` vs `bp_gnn_osd_cs4` | 86 | 29 | -5.32 |
| s2 | `bp_gnn` vs `bp_gnn_osd_cs4` | 72 | 80 | +0.65 |
| s3 | `bp_gnn` vs `bp_gnn_osd_cs0` | 56 | 115 | +4.51 |
| s3 | `bp_gnn_osd_cs0` vs `bp_gnn_osd_cs4` | 94 | 14 | -7.70 |
| s3 | `bp_gnn` vs `bp_gnn_osd_cs4` | 83 | 62 | -1.74 |

## p = 0.005　（3 个模型 seed：s1, s2, s3；每 seed 1024 shots）

| 模型 seed | 目录 | bp | bp_gnn | `bp_gnn_osd_cs0` | `bp_gnn_osd_cs4` | 未收敛 shot |
|---|---|---:|---:|---:|---:|---:|
| s1 | `d7_p0p005_probe` | 0.22070 | 0.16504 | 0.18262 | 0.13184 | 701 |
| s2 | `d7_p0p005_probe_s2model` | 0.25879 | 0.19727 | 0.28320 | 0.21484 | 834 |
| s3 | `d7_p0p005_probe_s3model` | 0.27246 | 0.18750 | 0.28125 | 0.20605 | 841 |

### 跨 seed 配对（种子是重复单位）

ΔLER = LER(A) − LER(B)，**负值表示 A 更好**；相对一列以该配对的 B 为基准。

| 配对 | 逐 seed ΔLER | 跨 seed 均值 ± SE | 相对 B |
|---|---|---:|---:|
| `bp_gnn` − `bp_gnn_osd_cs0` | -0.01758 / -0.08594 / -0.09375 | -0.06576 ± 0.02419 | -26.4% |
| `bp_gnn_osd_cs0` − `bp_gnn_osd_cs4` | +0.05078 / +0.06836 / +0.07520 | +0.06478 ± 0.00727 | +35.2% |
| `bp_gnn` − `bp_gnn_osd_cs4` | +0.03320 / -0.01758 / -0.01855 | -0.00098 ± 0.01709 | -0.5% |
| `bp` − `bp_gnn_osd_cs4` | +0.08887 / +0.04395 / +0.06641 | +0.06641 ± 0.01297 | +36.0% |

### 每个 seed 的配对 McNemar（单份 1024-shot 测试集，仅供方向）

| 模型 seed | 配对 | 只 A 错 | 只 B 错 | z |
|---|---|---:|---:|---:|
| s1 | `bp_gnn` vs `bp_gnn_osd_cs0` | 77 | 95 | +1.37 |
| s1 | `bp_gnn_osd_cs0` vs `bp_gnn_osd_cs4` | 73 | 21 | -5.36 |
| s1 | `bp_gnn` vs `bp_gnn_osd_cs4` | 102 | 68 | -2.61 |
| s2 | `bp_gnn` vs `bp_gnn_osd_cs0` | 80 | 168 | +5.59 |
| s2 | `bp_gnn_osd_cs0` vs `bp_gnn_osd_cs4` | 110 | 40 | -5.72 |
| s2 | `bp_gnn` vs `bp_gnn_osd_cs4` | 113 | 131 | +1.15 |
| s3 | `bp_gnn` vs `bp_gnn_osd_cs0` | 79 | 175 | +6.02 |
| s3 | `bp_gnn_osd_cs0` vs `bp_gnn_osd_cs4` | 112 | 35 | -6.35 |
| s3 | `bp_gnn` vs `bp_gnn_osd_cs4` | 107 | 126 | +1.24 |

## p = 0.008　（3 个模型 seed：s1, s2, s3；每 seed 1024 shots）

| 模型 seed | 目录 | bp | bp_gnn | `bp_gnn_osd_cs0` | `bp_gnn_osd_cs4` | 未收敛 shot |
|---|---|---:|---:|---:|---:|---:|
| s1 | `d7_p0p008_probe` | 0.35449 | 0.30371 | 0.34277 | 0.28809 | 952 |
| s2 | `d7_p0p008_probe_s2model` | 0.34668 | 0.33594 | 0.38281 | 0.33887 | 992 |
| s3 | `d7_p0p008_probe_s3model` | 0.36816 | 0.29785 | 0.35938 | 0.29688 | 966 |

### 跨 seed 配对（种子是重复单位）

ΔLER = LER(A) − LER(B)，**负值表示 A 更好**；相对一列以该配对的 B 为基准。

| 配对 | 逐 seed ΔLER | 跨 seed 均值 ± SE | 相对 B |
|---|---|---:|---:|
| `bp_gnn` − `bp_gnn_osd_cs0` | -0.03906 / -0.04688 / -0.06152 | -0.04915 ± 0.00658 | -13.6% |
| `bp_gnn_osd_cs0` − `bp_gnn_osd_cs4` | +0.05469 / +0.04395 / +0.06250 | +0.05371 ± 0.00538 | +17.4% |
| `bp_gnn` − `bp_gnn_osd_cs4` | +0.01562 / -0.00293 / +0.00098 | +0.00456 ± 0.00565 | +1.5% |
| `bp` − `bp_gnn_osd_cs4` | +0.06641 / +0.00781 / +0.07129 | +0.04850 ± 0.02039 | +15.8% |

### 每个 seed 的配对 McNemar（单份 1024-shot 测试集，仅供方向）

| 模型 seed | 配对 | 只 A 错 | 只 B 错 | z |
|---|---|---:|---:|---:|
| s1 | `bp_gnn` vs `bp_gnn_osd_cs0` | 108 | 148 | +2.50 |
| s1 | `bp_gnn_osd_cs0` vs `bp_gnn_osd_cs4` | 104 | 48 | -4.54 |
| s1 | `bp_gnn` vs `bp_gnn_osd_cs4` | 143 | 127 | -0.97 |
| s2 | `bp_gnn` vs `bp_gnn_osd_cs0` | 160 | 208 | +2.50 |
| s2 | `bp_gnn_osd_cs0` vs `bp_gnn_osd_cs4` | 122 | 77 | -3.19 |
| s2 | `bp_gnn` vs `bp_gnn_osd_cs4` | 173 | 176 | +0.16 |
| s3 | `bp_gnn` vs `bp_gnn_osd_cs0` | 131 | 194 | +3.49 |
| s3 | `bp_gnn_osd_cs0` vs `bp_gnn_osd_cs4` | 132 | 68 | -4.53 |
| s3 | `bp_gnn` vs `bp_gnn_osd_cs4` | 158 | 157 | -0.06 |

## p = 0.01　（1 个模型 seed：s1；每 seed 1024 shots）

⚠ 缺模型 seed s2, s3（该噪声率下尚未跑该 seed 的探针）。

| 模型 seed | 目录 | bp | bp_gnn | `bp_gnn_osd_cs0` | `bp_gnn_osd_cs4` | 未收敛 shot |
|---|---|---:|---:|---:|---:|---:|
| s1 | `d7_p0p01_probe` | 0.37988 | 0.34668 | 0.38770 | 0.36914 | 996 |

### 跨 seed 配对（种子是重复单位）

ΔLER = LER(A) − LER(B)，**负值表示 A 更好**；相对一列以该配对的 B 为基准。

| 配对 | 逐 seed ΔLER | 跨 seed 均值 ± SE | 相对 B |
|---|---|---:|---:|
| `bp_gnn` − `bp_gnn_osd_cs0` | -0.04102 | -0.04102 ± nan | -10.6% |
| `bp_gnn_osd_cs0` − `bp_gnn_osd_cs4` | +0.01855 | +0.01855 ± nan | +5.0% |
| `bp_gnn` − `bp_gnn_osd_cs4` | -0.02246 | -0.02246 ± nan | -6.1% |
| `bp` − `bp_gnn_osd_cs4` | +0.01074 | +0.01074 ± nan | +2.9% |

### 每个 seed 的配对 McNemar（单份 1024-shot 测试集，仅供方向）

| 模型 seed | 配对 | 只 A 错 | 只 B 错 | z |
|---|---|---:|---:|---:|
| s1 | `bp_gnn` vs `bp_gnn_osd_cs0` | 144 | 186 | +2.31 |
| s1 | `bp_gnn_osd_cs0` vs `bp_gnn_osd_cs4` | 73 | 54 | -1.69 |
| s1 | `bp_gnn` vs `bp_gnn_osd_cs4` | 156 | 179 | +1.26 |

