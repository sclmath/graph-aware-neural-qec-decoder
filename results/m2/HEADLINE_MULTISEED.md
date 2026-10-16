# M2 旗舰表（repetition d=3，线路级 p=0.01）的多种子复核

由 `scripts/m2_headline_multiseed.py` 自动生成，勿手改。
每个 seed = 32768 test shots（`splits.test_seeds` 两个 seed 合并）；除 `all` 之外的列来自 `graph_qec.m2` 的 `results.json`，
`bp_gnn` 列来自 T9 消融的 `all` 臂（同一 splits、同一训练种子，seed 0 与旗舰值逐位一致）。

| 训练/测试种子偏移 | 数据来源 | mwpm | bp | osd_gnn | bp_osd | bp_gnn |
|---:|---|---:|---:|---:|---:|---:|
| 0 | `m2_learned_basis_repetition_circuit_level_d3` | 0.00662 (217) | 0.00943 (309) | 0.00974 (319) | 0.01010 (331) | 0.00952 (312) |
| 10 | `m2_learned_basis_repetition_circuit_level_d3_s10` | 0.00705 (231) | 0.01031 (338) | 0.01013 (332) | 0.01068 (350) | 0.00934 (306) |
| 20 | `m2_learned_basis_repetition_circuit_level_d3_s20` | 0.00754 (247) | 0.01096 (359) | 0.01071 (351) | 0.01114 (365) | 0.01099 (360) |

## 跨 seed 配对（种子是重复单位）

| 比较 | 逐 seed ΔLER | 跨 seed 均值 ± SE | 相对 |
|---|---|---:|---:|
| `bp vs bp_gnn` | offset 0: +0.00009；offset 10: -0.00098；offset 20: +0.00003 | -0.00028 ± 0.00035 | -2.8% |
| `mwpm vs bp_gnn` | offset 0: +0.00290；offset 10: +0.00229；offset 20: +0.00345 | +0.00288 ± 0.00034 | +40.7% |

## 合并口径（整体尺度）

| decoder | LER（pooled） | 标准误 | 逻辑错误 | shots |
|---|---:|---:|---:|---:|
| `mwpm` | 0.00707 | 0.00027 | 695 | 98304 |
| `bp` | 0.01023 | 0.00032 | 1006 | 98304 |
| `osd_gnn` | 0.01019 | 0.00032 | 1002 | 98304 |
| `bp_osd` | 0.01064 | 0.00033 | 1046 | 98304 |
| `bp_gnn`（T9 all 臂） | 0.00995 | 0.00032 | 978 | 98304 |
