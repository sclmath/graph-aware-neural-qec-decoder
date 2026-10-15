# CPU 工程性能表

由 `scripts/engineering_table.py` 从 `results/` 自动生成，请勿手工编辑。
延迟与吞吐为固定 batch 的测量值；内存为执行期间 working set 的峰值增量。

| 配置 | 解码器 | LER | µs/shot | shot/s | 峰值 RSS delta | BP 平均迭代 | OSD 触发比例 | syndrome 一致率 |
|---|---|---|---|---|---|---|---|---|
| m1_repetition_circuit_level | mwpm | 0.00952148 | 0.137573 | 7,268,855 | 36864 | - | - | - |
| m1_repetition_circuit_level | union_find | 0.0090332 | 10.6774 | 93,656 | 36864 | - | - | - |
| m1_repetition_circuit_level | bp | 0.0129395 | 3.79292 | 263,649 | 5058560 | 0.818848 | - | - |
| m1_repetition_circuit_level | bp_osd | 0.0148926 | 6.5886 | 151,777 | 4009984 | 0.818848 | 0.0129395 | - |
| m1_repetition_circuit_level_p0p001 | mwpm | 0 | 0.037998 | 26,317,142 | 20480 | - | - | - |
| m1_repetition_circuit_level_p0p001 | union_find | 0 | 5.0238 | 199,053 | 24576 | - | - | - |
| m1_repetition_circuit_level_p0p001 | bp | 0 | 0.600825 | 1,664,378 | 73728 | 0.0461426 | - | - |
| m1_repetition_circuit_level_p0p001 | bp_osd | 0 | 0.420371 | 2,378,851 | 69632 | 0.0461426 | 0 | - |
| m1_repetition_circuit_level_p0p002 | mwpm | 0.000244141 | 0.0383887 | 26,049,351 | 65536 | - | - | - |
| m1_repetition_circuit_level_p0p002 | union_find | 0.000244141 | 5.33719 | 187,364 | 32768 | - | - | - |
| m1_repetition_circuit_level_p0p002 | bp | 0.000244141 | 0.797554 | 1,253,834 | 81920 | 0.0913086 | - | - |
| m1_repetition_circuit_level_p0p002 | bp_osd | 0.000244141 | 0.829321 | 1,205,805 | 61440 | 0.0913086 | 0 | - |
| m1_repetition_code_capacity | mwpm | 0.000488281 | 0.0418896 | 23,872,246 | 65536 | - | - | - |
| m1_repetition_code_capacity | union_find | 0.000488281 | 6.46799 | 154,608 | 28672 | - | - | - |
| m1_repetition_code_capacity | bp | 0.000488281 | 0.363955 | 2,747,592 | 36864 | 0.106689 | - | - |
| m1_repetition_code_capacity | bp_osd | 0.000488281 | 0.482266 | 2,073,546 | 20480 | 0.106689 | 0 | - |
| m1_repetition_code_capacity_p0p001 | mwpm | 0 | 0.0235645 | 42,436,801 | 20480 | - | - | - |
| m1_repetition_code_capacity_p0p001 | union_find | 0 | 5.85296 | 170,854 | 24576 | - | - | - |
| m1_repetition_code_capacity_p0p001 | bp | 0 | 0.175181 | 5,708,393 | 86016 | 0.0109863 | - | - |
| m1_repetition_code_capacity_p0p001 | bp_osd | 0 | 0.188672 | 5,300,207 | 24576 | 0.0109863 | 0 | - |
| m1_repetition_code_capacity_p0p002 | mwpm | 0 | 0.0347412 | 28,784,259 | 65536 | - | - | - |
| m1_repetition_code_capacity_p0p002 | union_find | 0 | 6.13951 | 162,880 | 24576 | - | - | - |
| m1_repetition_code_capacity_p0p002 | bp | 0 | 0.188408 | 5,307,625 | 69632 | 0.0200195 | - | - |
| m1_repetition_code_capacity_p0p002 | bp_osd | 0 | 0.124829 | 8,010,952 | 90112 | 0.0200195 | 0 | - |
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
| m4_rotated_surface_code_circuit_level_d5_s1__d5__circuit_level__p0p003 | mwpm | 0.00317383 | 1.29199 | 773,998 | - | - | - | - |
| m4_rotated_surface_code_circuit_level_d5_s1__d5__circuit_level__p0p003 | bp | 0.0402832 | 4,311 | 231.944 | - | 8.42383 | - | 0.797974 |
| m4_rotated_surface_code_circuit_level_d5_s1__d5__circuit_level__p0p003 | bp_osd | 0.0606689 | 5,302 | 188.619 | - | 8.42383 | 0.202026 | 1 |
| m4_rotated_surface_code_circuit_level_d5_s1__d5__circuit_level__p0p003 | bp_gnn | 0.0235596 | 2,049 | 488.069 | - | 4.3291 | - | 0.898682 |
| m4_rotated_surface_code_circuit_level_d5_s1__d5__circuit_level__p0p003 | bp_gnn_osd | 0.0334473 | 2,604 | 384.088 | - | 4.3291 | 0.101318 | 1 |
| m4_rotated_surface_code_circuit_level_d5_s1__d5__circuit_level__p0p005 | mwpm | 0.0125732 | 3.13237 | 319,247 | - | - | - | - |
| m4_rotated_surface_code_circuit_level_d5_s1__d5__circuit_level__p0p005 | bp | 0.102783 | 9,266 | 107.919 | - | 15.2411 | - | 0.58667 |
| m4_rotated_surface_code_circuit_level_d5_s1__d5__circuit_level__p0p005 | bp_osd | 0.139038 | 12,863 | 77.7411 | - | 15.2411 | 0.41333 | 1 |
| m4_rotated_surface_code_circuit_level_d5_s1__d5__circuit_level__p0p005 | bp_gnn | 0.0603027 | 5,080 | 196.866 | - | 9.04089 | - | 0.759766 |
| m4_rotated_surface_code_circuit_level_d5_s1__d5__circuit_level__p0p005 | bp_gnn_osd | 0.0830078 | 10,066 | 99.3484 | - | 9.04089 | 0.240234 | 1 |
| m4_rotated_surface_code_circuit_level_d5_s1__d5__circuit_level__p0p008 | mwpm | 0.0501709 | 5.90814 | 169,258 | - | - | - | - |
| m4_rotated_surface_code_circuit_level_d5_s1__d5__circuit_level__p0p008 | bp | 0.197754 | 13,554 | 73.7768 | - | 23.4595 | - | 0.310791 |
| m4_rotated_surface_code_circuit_level_d5_s1__d5__circuit_level__p0p008 | bp_osd | 0.242676 | 17,083 | 58.5386 | - | 23.4595 | 0.689209 | 1 |
| m4_rotated_surface_code_circuit_level_d5_s1__d5__circuit_level__p0p008 | bp_gnn | 0.125244 | 8,393 | 119.141 | - | 15.4706 | - | 0.556763 |
| m4_rotated_surface_code_circuit_level_d5_s1__d5__circuit_level__p0p008 | bp_gnn_osd | 0.163208 | 10,464 | 95.5638 | - | 15.4706 | 0.443237 | 1 |
| m4_rotated_surface_code_circuit_level_d5_s2__d5__circuit_level__p0p003 | mwpm | 0.00268555 | 1.30902 | 763,930 | - | - | - | - |
| m4_rotated_surface_code_circuit_level_d5_s2__d5__circuit_level__p0p003 | bp | 0.0441895 | 4,319 | 231.524 | - | 8.44153 | - | 0.79834 |
| m4_rotated_surface_code_circuit_level_d5_s2__d5__circuit_level__p0p003 | bp_osd | 0.0609131 | 5,277 | 189.502 | - | 8.44153 | 0.20166 | 1 |
| m4_rotated_surface_code_circuit_level_d5_s2__d5__circuit_level__p0p003 | bp_gnn | 0.0249023 | 2,459 | 406.66 | - | 5.06775 | - | 0.883667 |
| m4_rotated_surface_code_circuit_level_d5_s2__d5__circuit_level__p0p003 | bp_gnn_osd | 0.0328369 | 3,034 | 329.598 | - | 5.06775 | 0.116333 | 1 |
| m4_rotated_surface_code_circuit_level_d5_s2__d5__circuit_level__p0p005 | mwpm | 0.013916 | 2.42236 | 412,820 | - | - | - | - |
| m4_rotated_surface_code_circuit_level_d5_s2__d5__circuit_level__p0p005 | bp | 0.104004 | 9,548 | 104.735 | - | 15.5427 | - | 0.574585 |
| m4_rotated_surface_code_circuit_level_d5_s2__d5__circuit_level__p0p005 | bp_osd | 0.13501 | 12,039 | 83.0633 | - | 15.5427 | 0.425415 | 1 |
| m4_rotated_surface_code_circuit_level_d5_s2__d5__circuit_level__p0p005 | bp_gnn | 0.0665283 | 5,480 | 182.466 | - | 9.67432 | - | 0.743042 |
| m4_rotated_surface_code_circuit_level_d5_s2__d5__circuit_level__p0p005 | bp_gnn_osd | 0.0819092 | 7,229 | 138.328 | - | 9.67432 | 0.256958 | 1 |
| m4_rotated_surface_code_circuit_level_d5_s2__d5__circuit_level__p0p008 | mwpm | 0.0498047 | 5.28976 | 189,045 | - | - | - | - |
| m4_rotated_surface_code_circuit_level_d5_s2__d5__circuit_level__p0p008 | bp | 0.193359 | 13,714 | 72.9196 | - | 23.6855 | - | 0.30249 |
| m4_rotated_surface_code_circuit_level_d5_s2__d5__circuit_level__p0p008 | bp_osd | 0.244873 | 17,047 | 58.6602 | - | 23.6855 | 0.69751 | 1 |
| m4_rotated_surface_code_circuit_level_d5_s2__d5__circuit_level__p0p008 | bp_gnn | 0.131836 | 9,054 | 110.451 | - | 16.5979 | - | 0.522217 |
| m4_rotated_surface_code_circuit_level_d5_s2__d5__circuit_level__p0p008 | bp_gnn_osd | 0.167358 | 11,362 | 88.0159 | - | 16.5979 | 0.477783 | 1 |
| m4_rotated_surface_code_circuit_level_d5_s3__d5__circuit_level__p0p003 | mwpm | 0.0032959 | 1.29551 | 771,898 | - | - | - | - |
| m4_rotated_surface_code_circuit_level_d5_s3__d5__circuit_level__p0p003 | bp | 0.043457 | 4,379 | 228.363 | - | 8.63489 | - | 0.792969 |
| m4_rotated_surface_code_circuit_level_d5_s3__d5__circuit_level__p0p003 | bp_osd | 0.0634766 | 5,387 | 185.638 | - | 8.63489 | 0.207031 | 1 |
| m4_rotated_surface_code_circuit_level_d5_s3__d5__circuit_level__p0p003 | bp_gnn | 0.0239258 | 2,120 | 471.791 | - | 4.45142 | - | 0.896118 |
| m4_rotated_surface_code_circuit_level_d5_s3__d5__circuit_level__p0p003 | bp_gnn_osd | 0.03125 | 2,639 | 378.984 | - | 4.45142 | 0.103882 | 1 |
| m4_rotated_surface_code_circuit_level_d5_s3__d5__circuit_level__p0p005 | mwpm | 0.0129395 | 2.35519 | 424,595 | - | - | - | - |
| m4_rotated_surface_code_circuit_level_d5_s3__d5__circuit_level__p0p005 | bp | 0.104492 | 9,787 | 102.174 | - | 15.5984 | - | 0.573853 |
| m4_rotated_surface_code_circuit_level_d5_s3__d5__circuit_level__p0p005 | bp_osd | 0.138184 | 11,918 | 83.9046 | - | 15.5984 | 0.426147 | 1 |
| m4_rotated_surface_code_circuit_level_d5_s3__d5__circuit_level__p0p005 | bp_gnn | 0.0689697 | 5,720 | 174.821 | - | 10.1342 | - | 0.734619 |
| m4_rotated_surface_code_circuit_level_d5_s3__d5__circuit_level__p0p005 | bp_gnn_osd | 0.0822754 | 7,189 | 139.105 | - | 10.1342 | 0.265381 | 1 |
| m4_rotated_surface_code_circuit_level_d5_s3__d5__circuit_level__p0p008 | mwpm | 0.0474854 | 4.07579 | 245,351 | - | - | - | - |
| m4_rotated_surface_code_circuit_level_d5_s3__d5__circuit_level__p0p008 | bp | 0.188599 | 13,677 | 73.1164 | - | 23.6266 | - | 0.304321 |
| m4_rotated_surface_code_circuit_level_d5_s3__d5__circuit_level__p0p008 | bp_osd | 0.235352 | 17,044 | 58.6701 | - | 23.6266 | 0.695679 | 1 |
| m4_rotated_surface_code_circuit_level_d5_s3__d5__circuit_level__p0p008 | bp_gnn | 0.132446 | 8,895 | 112.421 | - | 16.2156 | - | 0.535522 |
| m4_rotated_surface_code_circuit_level_d5_s3__d5__circuit_level__p0p008 | bp_gnn_osd | 0.165894 | 10,984 | 91.0409 | - | 16.2156 | 0.464478 | 1 |
| m4_rotated_surface_code_circuit_level_d7_s1__d7__circuit_level__p0p003 | mwpm | 0.000732422 | 5.1228 | 195,206 | - | - | - | - |
| m4_rotated_surface_code_circuit_level_d7_s1__d7__circuit_level__p0p003 | bp | 0.162598 | 38,274 | 26.1275 | - | 22.8081 | - | 0.338623 |
| m4_rotated_surface_code_circuit_level_d7_s1__d7__circuit_level__p0p003 | bp_osd | 0.193115 | 63,778 | 15.6793 | - | 22.8081 | 0.661377 | 1 |
| m4_rotated_surface_code_circuit_level_d7_s1__d7__circuit_level__p0p003 | bp_gnn | 0.101318 | 23,983 | 41.6967 | - | 14.4624 | - | 0.595703 |
| m4_rotated_surface_code_circuit_level_d7_s1__d7__circuit_level__p0p003 | bp_gnn_osd | 0.105225 | 39,580 | 25.2656 | - | 14.4624 | 0.404297 | 1 |
| m4_rotated_surface_code_circuit_level_d7_s1__d7__circuit_level__p0p005 | mwpm | 0.00854492 | 11.7285 | 85,263 | - | - | - | - |
| m4_rotated_surface_code_circuit_level_d7_s1__d7__circuit_level__p0p005 | bp | 0.236328 | 91,965 | 10.8737 | - | 28.8784 | - | 0.12085 |
| m4_rotated_surface_code_circuit_level_d7_s1__d7__circuit_level__p0p005 | bp_osd | 0.277344 | 164,533 | 6.0778 | - | 28.8784 | 0.87915 | 1 |
| m4_rotated_surface_code_circuit_level_d7_s1__d7__circuit_level__p0p005 | bp_gnn | 0.16748 | 46,054 | 21.7137 | - | 23.5459 | - | 0.29834 |
| m4_rotated_surface_code_circuit_level_d7_s1__d7__circuit_level__p0p005 | bp_gnn_osd | 0.210693 | 78,175 | 12.7918 | - | 23.5459 | 0.70166 | 1 |
| m4_rotated_surface_code_circuit_level_d7_s2__d7__circuit_level__p0p003 | mwpm | 0.00170898 | 4.43962 | 225,244 | - | - | - | - |
| m4_rotated_surface_code_circuit_level_d7_s2__d7__circuit_level__p0p003 | bp | 0.158447 | 38,949 | 25.6745 | - | 23.0049 | - | 0.331055 |
| m4_rotated_surface_code_circuit_level_d7_s2__d7__circuit_level__p0p003 | bp_osd | 0.194092 | 64,728 | 15.4492 | - | 23.0049 | 0.668945 | 1 |
| m4_rotated_surface_code_circuit_level_d7_s2__d7__circuit_level__p0p003 | bp_gnn | 0.108643 | 36,307 | 27.5432 | - | 20.8823 | - | 0.408936 |
| m4_rotated_surface_code_circuit_level_d7_s2__d7__circuit_level__p0p003 | bp_gnn_osd | 0.162109 | 59,466 | 16.8163 | - | 20.8823 | 0.591064 | 1 |
| m4_rotated_surface_code_circuit_level_d7_s2__d7__circuit_level__p0p005 | mwpm | 0.00976562 | 10.2127 | 97,918 | - | - | - | - |
| m4_rotated_surface_code_circuit_level_d7_s2__d7__circuit_level__p0p005 | bp | 0.244629 | 51,663 | 19.3562 | - | 28.9241 | - | 0.121338 |
| m4_rotated_surface_code_circuit_level_d7_s2__d7__circuit_level__p0p005 | bp_osd | 0.302734 | 85,525 | 11.6925 | - | 28.9241 | 0.878662 | 1 |
| m4_rotated_surface_code_circuit_level_d7_s2__d7__circuit_level__p0p005 | bp_gnn | 0.196289 | 46,943 | 21.3024 | - | 27.489 | - | 0.17041 |
| m4_rotated_surface_code_circuit_level_d7_s2__d7__circuit_level__p0p005 | bp_gnn_osd | 0.255859 | 78,466 | 12.7444 | - | 27.489 | 0.82959 | 1 |
| m4_rotated_surface_code_circuit_level_d7_s3__d7__circuit_level__p0p003 | mwpm | 0.00170898 | 5.60222 | 178,501 | - | - | - | - |
| m4_rotated_surface_code_circuit_level_d7_s3__d7__circuit_level__p0p003 | bp | 0.14917 | 38,468 | 25.9956 | - | 22.7961 | - | 0.3396 |
| m4_rotated_surface_code_circuit_level_d7_s3__d7__circuit_level__p0p003 | bp_osd | 0.199219 | 64,493 | 15.5056 | - | 22.7961 | 0.6604 | 1 |
| m4_rotated_surface_code_circuit_level_d7_s3__d7__circuit_level__p0p003 | bp_gnn | 0.107178 | 37,620 | 26.5817 | - | 21.7769 | - | 0.368652 |
| m4_rotated_surface_code_circuit_level_d7_s3__d7__circuit_level__p0p003 | bp_gnn_osd | 0.174072 | 62,081 | 16.108 | - | 21.7769 | 0.631348 | 1 |
| m4_rotated_surface_code_circuit_level_d7_s3__d7__circuit_level__p0p005 | mwpm | 0.0100098 | 8.74385 | 114,366 | - | - | - | - |
| m4_rotated_surface_code_circuit_level_d7_s3__d7__circuit_level__p0p005 | bp | 0.240723 | 48,790 | 20.4961 | - | 28.9827 | - | 0.11792 |
| m4_rotated_surface_code_circuit_level_d7_s3__d7__circuit_level__p0p005 | bp_osd | 0.303955 | 82,193 | 12.1664 | - | 28.9827 | 0.88208 | 1 |
| m4_rotated_surface_code_circuit_level_d7_s3__d7__circuit_level__p0p005 | bp_gnn | 0.176514 | 46,847 | 21.346 | - | 27.6162 | - | 0.16626 |
| m4_rotated_surface_code_circuit_level_d7_s3__d7__circuit_level__p0p005 | bp_gnn_osd | 0.265869 | 78,142 | 12.7972 | - | 27.6162 | 0.83374 | 1 |
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
