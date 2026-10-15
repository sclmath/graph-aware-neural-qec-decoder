# CPU 工程性能表

由 `scripts/engineering_table.py` 从 `results/` 自动生成，请勿手工编辑。
延迟与吞吐为固定 batch 的测量值；内存为执行期间 working set 的峰值增量。

| 配置 | 解码器 | LER | µs/shot | shot/s | 峰值 RSS delta | BP 平均迭代 | OSD 触发比例 | syndrome 一致率 |
|---|---|---|---|---|---|---|---|---|
| m1_repetition_circuit_level | mwpm | 0.00952148 | 0.123677 | 8,085,594 | 36864 | - | - | - |
| m1_repetition_circuit_level | union_find | 0.0129395 | 33.3701 | 29,967 | 36864 | - | - | - |
| m1_repetition_circuit_level | bp | 0.0129395 | 2.33384 | 428,478 | 1974272 | 0.818848 | - | - |
| m1_repetition_circuit_level | bp_osd | 0.0148926 | 3.86836 | 258,507 | 2068480 | 0.818848 | 0.0129395 | - |
| m1_repetition_circuit_level_p0p001 | mwpm | 0 | 0.0268359 | 37,263,464 | 49152 | - | - | - |
| m1_repetition_circuit_level_p0p001 | union_find | 0 | 30.1606 | 33,156 | 24576 | - | - | - |
| m1_repetition_circuit_level_p0p001 | bp | 0 | 0.344194 | 2,905,335 | 65536 | 0.0461426 | - | - |
| m1_repetition_circuit_level_p0p001 | bp_osd | 0 | 0.309868 | 3,227,179 | 2048000 | 0.0461426 | 0 | - |
| m1_repetition_circuit_level_p0p002 | mwpm | 0.000244141 | 0.0396631 | 25,212,360 | 61440 | - | - | - |
| m1_repetition_circuit_level_p0p002 | union_find | 0.000244141 | 30.5937 | 32,686 | 24576 | - | - | - |
| m1_repetition_circuit_level_p0p002 | bp | 0.000244141 | 0.407358 | 2,454,841 | 61440 | 0.0913086 | - | - |
| m1_repetition_circuit_level_p0p002 | bp_osd | 0.000244141 | 0.684517 | 1,460,885 | 106496 | 0.0913086 | 0 | - |
| m1_repetition_code_capacity | mwpm | 0.000488281 | 0.0296973 | 33,673,134 | 20480 | - | - | - |
| m1_repetition_code_capacity | union_find | 0.000488281 | 12.0946 | 82,682 | 24576 | - | - | - |
| m1_repetition_code_capacity | bp | 0.000488281 | 0.310303 | 3,222,659 | 53248 | 0.106689 | - | - |
| m1_repetition_code_capacity | bp_osd | 0.000488281 | 0.28646 | 3,490,889 | 45056 | 0.106689 | 0 | - |
| m1_repetition_code_capacity_p0p001 | mwpm | 0 | 0.01979 | 50,530,471 | 40960 | - | - | - |
| m1_repetition_code_capacity_p0p001 | union_find | 0 | 11.311 | 88,410 | 40960 | - | - | - |
| m1_repetition_code_capacity_p0p001 | bp | 0 | 0.0975439 | 10,251,790 | 12288 | 0.0109863 | - | - |
| m1_repetition_code_capacity_p0p001 | bp_osd | 0 | 0.089917 | 11,121,368 | 0 | 0.0109863 | 0 | - |
| m1_repetition_code_capacity_p0p002 | mwpm | 0 | 0.0203076 | 49,242,606 | 8192 | - | - | - |
| m1_repetition_code_capacity_p0p002 | union_find | 0 | 11.1769 | 89,470 | 28672 | - | - | - |
| m1_repetition_code_capacity_p0p002 | bp | 0 | 0.103037 | 9,705,241 | 0 | 0.0200195 | - | - |
| m1_repetition_code_capacity_p0p002 | bp_osd | 0 | 0.0983887 | 10,163,772 | 28672 | 0.0200195 | 0 | - |
| m2_learned_basis_repetition_circuit_level_d3__d3__circuit_level__p0p01 | mwpm | 0.00662231 | 0.107042 | 9,342,133 | - | - | - | - |
| m2_learned_basis_repetition_circuit_level_d3__d3__circuit_level__p0p01 | union_find | 0.00970459 | 31.856 | 31,391 | - | - | - | - |
| m2_learned_basis_repetition_circuit_level_d3__d3__circuit_level__p0p01 | bp | 0.00942993 | 1.73313 | 576,991 | - | 0.706696 | - | 0.989929 |
| m2_learned_basis_repetition_circuit_level_d3__d3__circuit_level__p0p01 | bp_osd | 0.0101013 | 2.94997 | 338,987 | - | 0.706696 | 0.0100708 | 1 |
| m2_learned_basis_repetition_circuit_level_d3__d3__circuit_level__p0p01 | osd_bp | 0.0101013 | 123.074 | 8,125 | - | 0.706696 | 1 | 1 |
| m2_learned_basis_repetition_circuit_level_d3__d3__circuit_level__p0p01 | osd_gnn | 0.00973511 | 116.32 | 8,597 | - | 0.706696 | 1 | 1 |
| m2_repetition_circuit_level_d3__d3__circuit_level__p0p01 | mwpm | 0.00662231 | 0.115461 | 8,660,916 | - | - | - | - |
| m2_repetition_circuit_level_d3__d3__circuit_level__p0p01 | union_find | 0.00970459 | 33.6336 | 29,732 | - | - | - | - |
| m2_repetition_circuit_level_d3__d3__circuit_level__p0p01 | bp | 0.00942993 | 1.77668 | 562,846 | - | 0.706696 | - | 0.989929 |
| m2_repetition_circuit_level_d3__d3__circuit_level__p0p01 | bp_osd | 0.0101013 | 2.83498 | 352,736 | - | 0.706696 | 0.0100708 | 1 |
| m2_repetition_circuit_level_d3__d3__circuit_level__p0p01 | bp_gnn | 0.00952148 | 1.64356 | 608,435 | - | 0.557373 | - | 0.991211 |
| m2_d5_eval | mwpm | 0.0012207 | 0.556958 | 1,795,467 | - | - | - | - |
| m2_d5_eval | bp | 0.0473633 | 70.8042 | 14,123 | - | 5.24072 | - | 0.887451 |
| m2_d5_eval | bp_osd | 0.0593262 | 133.339 | 7,500 | - | 5.24072 | 0.112549 | 1 |
| m2_d5_eval | bp_gnn | 0.0136719 | 19.766 | 50,592 | - | 1.63208 | - | 0.969238 |
| m2_d5_eval | bp_gnn_osd | 0.0197754 | 35.7026 | 28,009 | - | 1.63208 | 0.0307617 | 1 |
| m3_learned_basis_repetition_circuit_level_d3__d3__circuit_level__p0p01 | mwpm | 0.00662231 | 0.149575 | 6,685,619 | - | - | - | - |
| m3_learned_basis_repetition_circuit_level_d3__d3__circuit_level__p0p01 | bp | 0.00942993 | 1.90921 | 523,777 | - | 0.706696 | - | 0.989929 |
| m3_learned_basis_repetition_circuit_level_d3__d3__circuit_level__p0p01 | bp_osd | 0.0101013 | 3.97515 | 251,563 | - | 0.706696 | 0.0100708 | 1 |
| m3_learned_basis_repetition_circuit_level_d3__d3__circuit_level__p0p01 | bp_gnn | 0.00952148 | 1.76042 | 568,047 | - | 0.557373 | - | 0.991211 |
| m3_learned_basis_repetition_circuit_level_d3__d3__circuit_level__p0p01 | bp_gnn_osd | 0.0101624 | 2.61842 | 381,910 | - | 0.557373 | 0.00878906 | 1 |
| m3_learned_basis_repetition_circuit_level_d3__d3__circuit_level__p0p01 | bp_gnn_osd_learned_order | 0.00967407 | 3.02018 | 331,107 | - | 0.557373 | 0.00878906 | 1 |
| m3_learned_basis_repetition_circuit_level_d3__d3__circuit_level__p0p01 | osd_gnn | 0.00973511 | 135.086 | 7,403 | - | 0.706696 | 1 | 1 |
| m3_learned_basis_repetition_circuit_level_d3__from_d3__to_d3__circuit_level__p0p003 | mwpm | 0.000823975 | 0.140356 | 7,124,717 | - | - | - | - |
| m3_learned_basis_repetition_circuit_level_d3__from_d3__to_d3__circuit_level__p0p003 | bp | 0.0010376 | 2.598 | 384,911 | - | 0.155975 | - | 0.999115 |
| m3_learned_basis_repetition_circuit_level_d3__from_d3__to_d3__circuit_level__p0p003 | bp_osd | 0.00106812 | 2.89976 | 344,856 | - | 0.155975 | 0.00088501 | 1 |
| m3_learned_basis_repetition_circuit_level_d3__from_d3__to_d3__circuit_level__p0p003 | bp_gnn | 0.000976562 | 2.24449 | 445,535 | - | 0.119263 | - | 0.999237 |
| m3_learned_basis_repetition_circuit_level_d3__from_d3__to_d3__circuit_level__p0p003 | bp_gnn_osd | 0.00112915 | 2.34575 | 426,303 | - | 0.119263 | 0.000762939 | 1 |
| m3_learned_basis_repetition_circuit_level_d3__from_d3__to_d3__circuit_level__p0p005 | mwpm | 0.0017395 | 0.156088 | 6,406,632 | - | - | - | - |
| m3_learned_basis_repetition_circuit_level_d3__from_d3__to_d3__circuit_level__p0p005 | bp | 0.00265503 | 4.49807 | 222,318 | - | 0.293976 | - | 0.997223 |
| m3_learned_basis_repetition_circuit_level_d3__from_d3__to_d3__circuit_level__p0p005 | bp_osd | 0.00286865 | 5.74738 | 173,992 | - | 0.293976 | 0.0027771 | 1 |
| m3_learned_basis_repetition_circuit_level_d3__from_d3__to_d3__circuit_level__p0p005 | bp_gnn | 0.00259399 | 3.96398 | 252,272 | - | 0.229095 | - | 0.997589 |
| m3_learned_basis_repetition_circuit_level_d3__from_d3__to_d3__circuit_level__p0p005 | bp_gnn_osd | 0.0027771 | 4.62221 | 216,347 | - | 0.229095 | 0.00241089 | 1 |
| m3_learned_basis_repetition_circuit_level_d3__from_d3__to_d3__circuit_level__p0p008 | mwpm | 0.00485229 | 0.217902 | 4,589,227 | - | - | - | - |
| m3_learned_basis_repetition_circuit_level_d3__from_d3__to_d3__circuit_level__p0p008 | bp | 0.00601196 | 7.85958 | 127,233 | - | 0.51889 | - | 0.993774 |
| m3_learned_basis_repetition_circuit_level_d3__from_d3__to_d3__circuit_level__p0p008 | bp_osd | 0.00637817 | 9.15129 | 109,274 | - | 0.51889 | 0.00622559 | 1 |
| m3_learned_basis_repetition_circuit_level_d3__from_d3__to_d3__circuit_level__p0p008 | bp_gnn | 0.00592041 | 3.60789 | 277,171 | - | 0.390564 | - | 0.995056 |
| m3_learned_basis_repetition_circuit_level_d3__from_d3__to_d3__circuit_level__p0p008 | bp_gnn_osd | 0.00631714 | 4.42691 | 225,891 | - | 0.390564 | 0.00494385 | 1 |
| m3_learned_basis_repetition_circuit_level_d3__from_d3__to_d3__circuit_level__p0p02 | mwpm | 0.0255432 | 0.425961 | 2,347,631 | - | - | - | - |
| m3_learned_basis_repetition_circuit_level_d3__from_d3__to_d3__circuit_level__p0p02 | bp | 0.0344543 | 18.9907 | 52,657 | - | 1.78162 | - | 0.965973 |
| m3_learned_basis_repetition_circuit_level_d3__from_d3__to_d3__circuit_level__p0p02 | bp_osd | 0.0383911 | 31.4557 | 31,791 | - | 1.78162 | 0.0340271 | 1 |
| m3_learned_basis_repetition_circuit_level_d3__from_d3__to_d3__circuit_level__p0p02 | bp_gnn | 0.0342407 | 11.7072 | 85,418 | - | 1.42755 | - | 0.970032 |
| m3_learned_basis_repetition_circuit_level_d3__from_d3__to_d3__circuit_level__p0p02 | bp_gnn_osd | 0.036377 | 18.8694 | 52,996 | - | 1.42755 | 0.0299683 | 1 |
| m3_learned_basis_repetition_circuit_level_d3__from_d3__to_d5__circuit_level__p0p01 | mwpm | 0.00134277 | 0.863306 | 1,158,338 | - | - | - | - |
| m3_learned_basis_repetition_circuit_level_d3__from_d3__to_d5__circuit_level__p0p01 | bp | 0.0507812 | 336.697 | 2,970 | - | 5.46741 | - | 0.879517 |
| m3_learned_basis_repetition_circuit_level_d3__from_d3__to_d5__circuit_level__p0p01 | bp_osd | 0.0629883 | 416.009 | 2,404 | - | 5.46741 | 0.120483 | 1 |
| m3_learned_basis_repetition_circuit_level_d3__from_d3__to_d5__circuit_level__p0p01 | bp_gnn | 0.0170898 | 31.7621 | 31,484 | - | 1.8894 | - | 0.963379 |
| m3_learned_basis_repetition_circuit_level_d3__from_d3__to_d5__circuit_level__p0p01 | bp_gnn_osd | 0.0235596 | 58.7854 | 17,011 | - | 1.8894 | 0.0366211 | 1 |
| m4_learned_basis_rotated_surface_code_circuit_level_d3__d3__circuit_level__p0p005 | mwpm | 0.0169373 | 0.432031 | 2,314,647 | - | - | - | - |
| m4_learned_basis_rotated_surface_code_circuit_level_d3__d3__circuit_level__p0p005 | bp | 0.0400696 | 780.669 | 1,281 | - | 4.08786 | - | 0.902588 |
| m4_learned_basis_rotated_surface_code_circuit_level_d3__d3__circuit_level__p0p005 | bp_osd | 0.0431519 | 751.105 | 1,331 | - | 4.08786 | 0.0974121 | 1 |
| m4_learned_basis_rotated_surface_code_circuit_level_d3__d3__circuit_level__p0p005 | bp_gnn | 0.0327759 | 422.765 | 2,365 | - | 2.461 | - | 0.946167 |
| m4_learned_basis_rotated_surface_code_circuit_level_d3__d3__circuit_level__p0p005 | bp_gnn_osd | 0.0354919 | 444.516 | 2,250 | - | 2.461 | 0.053833 | 1 |
| m4_rotated_surface_code_circuit_level_d5__d5__circuit_level__p0p005 | mwpm | 0.0107422 | 3.20063 | 312,438 | - | - | - | - |
| m4_rotated_surface_code_circuit_level_d5__d5__circuit_level__p0p005 | bp | 0.103516 | 10,268 | 97.388 | - | 15.4116 | - | 0.578613 |
| m4_rotated_surface_code_circuit_level_d5__d5__circuit_level__p0p005 | bp_osd | 0.13623 | 12,724 | 78.5917 | - | 15.4116 | 0.421387 | 1 |
| m4_rotated_surface_code_circuit_level_d5__d5__circuit_level__p0p005 | bp_gnn | 0.0644531 | 5,767 | 173.396 | - | 8.76318 | - | 0.76709 |
| m4_rotated_surface_code_circuit_level_d5__d5__circuit_level__p0p005 | bp_gnn_osd | 0.0805664 | 6,377 | 156.819 | - | 8.76318 | 0.23291 | 1 |
| m4_learned_basis_rotated_surface_code_code_capacity_d3__d3__code_capacity__p0p05 | mwpm | 0.0507812 | 0.381763 | 2,619,428 | - | - | - | - |
| m4_learned_basis_rotated_surface_code_code_capacity_d3__d3__code_capacity__p0p05 | bp | 0.053894 | 114.189 | 8,757 | - | 2.82269 | - | 0.952423 |
| m4_learned_basis_rotated_surface_code_code_capacity_d3__d3__code_capacity__p0p05 | bp_osd | 0.0609741 | 132.627 | 7,540 | - | 2.82269 | 0.0475769 | 1 |
| m4_learned_basis_rotated_surface_code_code_capacity_d3__d3__code_capacity__p0p05 | bp_gnn | 0.0526733 | 48.2973 | 20,705 | - | 1.89868 | - | 0.963409 |
| m4_learned_basis_rotated_surface_code_code_capacity_d3__d3__code_capacity__p0p05 | bp_gnn_osd | 0.0500793 | 66.8098 | 14,968 | - | 1.89868 | 0.0365906 | 1 |
| m4_learned_basis_rotated_surface_code_code_capacity_d3__from_d3__to_d5__code_capacity__p0p05 | mwpm | 0.0429077 | 3.15445 | 317,013 | - | - | - | - |
| m4_learned_basis_rotated_surface_code_code_capacity_d3__from_d3__to_d5__code_capacity__p0p05 | bp | 0.138062 | 3,102 | 322.332 | - | 15.3224 | - | 0.585999 |
| m4_learned_basis_rotated_surface_code_code_capacity_d3__from_d3__to_d5__code_capacity__p0p05 | bp_osd | 0.215576 | 4,126 | 242.364 | - | 15.3224 | 0.414001 | 1 |
| m4_learned_basis_rotated_surface_code_code_capacity_d3__from_d3__to_d5__code_capacity__p0p05 | bp_gnn | 0.121521 | 1,368 | 730.747 | - | 12.3235 | - | 0.646729 |
| m4_learned_basis_rotated_surface_code_code_capacity_d3__from_d3__to_d5__code_capacity__p0p05 | bp_gnn_osd | 0.180664 | 3,472 | 287.979 | - | 12.3235 | 0.353271 | 1 |
| m4_hgp_hamming7x7_code_capacity_p0p05__d3__code_capacity__p0p05 | bp | 0.394867 | 674.341 | 1,483 | - | 13.5313 | - | 0.655487 |
| m4_hgp_hamming7x7_code_capacity_p0p05__d3__code_capacity__p0p05 | bp_osd | 0.410126 | 973.452 | 1,027 | - | 13.5313 | 0.344513 | 1 |
| m4_hgp_hamming7x7_code_capacity_p0p05__d3__code_capacity__p0p05 | bp_gnn | 0.286377 | 321.689 | 3,109 | - | 6.62997 | - | 0.841003 |
| m4_hgp_hamming7x7_code_capacity_p0p05__d3__code_capacity__p0p05 | bp_gnn_osd | 0.297302 | 453.272 | 2,206 | - | 6.62997 | 0.158997 | 1 |
| m4_hgp_rep3x3_code_capacity_p0p05__d3__code_capacity__p0p05 | bp | 0.0360107 | 25.7239 | 38,874 | - | 2.35641 | - | 0.954254 |
| m4_hgp_rep3x3_code_capacity_p0p05__d3__code_capacity__p0p05 | bp_osd | 0.0466919 | 65.2523 | 15,325 | - | 2.35641 | 0.0457458 | 1 |
| m4_hgp_rep3x3_code_capacity_p0p05__d3__code_capacity__p0p05 | bp_gnn | 0.0349121 | 23.4588 | 42,628 | - | 1.65582 | - | 0.964874 |
| m4_hgp_rep3x3_code_capacity_p0p05__d3__code_capacity__p0p05 | bp_gnn_osd | 0.0381775 | 36.9761 | 27,044 | - | 1.65582 | 0.0351257 | 1 |

## 模型规模

| 模型 | 参数量 | float32 权重 | int8 动态量化权重 |
|---|---:|---:|---:|
| BipartiteSyndromeGNN (hidden=32, layers=3) | 1024 shots/batch | 0.06119 MB | 0.01645 MB |

量化推理（`scripts/m5_quantization.py`，batch=1024，16384 shots）：float32 31.73 µs/shot、int8 动态 40.99 µs/shot（speedup 0.7742），权重压缩 0.2689，机制符号一致率 0.999951，logit 最大偏差 0.4377。

## 不可测项与原因

| 项 | 原因 |
|---|---|
| gpu_latency | 交付环境为 CPU-only（`torch.cuda.is_available() == False`） |
| gpu_memory | 同左，见 `docs/M5_ENGINEERING.md` 第 4 节 |
| batch_throughput_multi | M1 的 `timed_runs` 已覆盖固定 batch 的吞吐；更大 batch 的吞吐随噪声率/码距变化，未逐点测量 |
