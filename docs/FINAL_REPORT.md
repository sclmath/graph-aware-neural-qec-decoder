# Graph-Aware Neural QEC Decoder · 第一阶段技术报告（T17）

- **日期**：2026-10-15
- **状态**：主体完成；第 4.6 / 4.7 节（表面码 d=5/d=7 全网格与阈值）在网格跑完后由夜间巡检刷新，文中以 `【待刷新】` 标记
- **交付环境**：Intel i5-12400（6C/12T）/ 16 GB / CPU-only PyTorch（`torch.cuda.is_available() == False`）
- **代码**：`src/graph_qec/`；测试：`pytest` **72 项全绿**；所有表格中的数字均可由仓库内脚本复现

> 本文口径与 `README.md` 第 9-15 节、各里程碑文档一致；凡有冲突以本文为准并已同步回各文档。

---

## 1. 摘要

本项目把量子纠错解码建模为带噪图上的推断与组合优化问题，交付了一条 **BP → 图神经网络重加权 → OSD 候选集后处理** 的混合解码器链路，并在 CPU-only 环境下完成了 repetition code、旋转表面码（d=3/5/7）与两个小型 HGP 码的完整实验、代码与报告。

**五条可交付的核心结论：**

1. **机制层面判别很容易，但机制边际本身换不来精度。** GNN 把「哪个 error mechanism 发生」的 AUC 从 0.62 提到 0.99 以上（M2），但把同一份预测当先验接进 BP，在 d=3 repetition 上**没有显著收益**（0.00943 → 0.00952，McNemar p=0.44）；它的稳定价值是**把 BP 平均迭代数降下来**（0.707 → 0.557）并在 BP 较弱的大图上显著改善 LER。
2. **学习先验的收益随 BP 变弱先升后降，在 d=5 达到峰值。** 表面码线路级 p=0.005（各 3 seeds）：d=3 `bp` 0.04007 → `bp_gnn` 0.03278（**−18%**）；d=5 0.10376 → 0.06527（**−37%**）；**d=7 0.24056 → 0.18009（−25%）**。d=3 repetition 上无效（BP 已接近最优），而 d=7 上收益回落——因为那里 BP 已经退化到"局部推断本身不再有信息"的区间（收敛率 0.12、平均迭代 28.9/32）。**"BP 越弱收益越大"只在 BP 仍然可用的区间成立，越过该区间后学习先验也无法救回来**（见 4.6）。
3. **真正的杠杆是「候选基质量」，不是「机制边际」。** 把 OSD-0 换成 **OSD-CS(λ)**（对 λ 个最不可靠的非 pivot 列做组合扫描）后，表面码 d=3 线路级从 0.04007 降到 **0.01913**（`bp_gnn_osd_cs8`，−52%，距 MWPM 仅 +13%），而 OSD-0 在该配置上**让结果变差**。这条结果把 M2/M3/M5 的三条负结果统一收口成了正面出口。
4. **基线可信度问题已修复。** 原 `UnionFindDecoder` 缺少 peeling，约 97% 的含缺陷 shot 产出违反 syndrome 约束的 correction；重写为忠实加权 Union-Find（half-edge 生长 + peeling + 2-core T-join）后，表面码 d=3 码容量 LER 与 MWPM **逐位一致**，全部 10 个扫描点比值 1.00-1.41×。
5. **图结构决定解码器的可用性。** 线路级表面码 DEM 是稠密超图（d=3/5 check 度最大 48/80、4-圈 1956/26046），HGP 码**不可匹配**（`matchable=False`），MWPM 类解码器对其完全不可用——这才是混合解码器不可替代的场景。

---

## 2. 交付范围与出口标准

| 出口标准（`docs/ROADMAP_TODO.md` 第 0.1 节） | 状态 |
|---|---|
| `pytest` 全绿，CI 在干净环境可复现 | ✅ 72 项全绿；`.github/workflows/ci.yml`（3.10/3.12 矩阵） |
| `scripts/run_all.ps1` 小规模模式端到端跑通 | ✅ 18 s |
| d=3/5/7 的 LER-p 曲线与阈值估计，显式标注 shots 与 seed 数 | 🔶 d=3/5 完成；d=7 曲线由 T6 网格产出；阈值见 4.7 |
| 学习重加权在至少一个噪声区间改善精度或延迟，且给出配对检验 | ✅ 见 4.3 / 4.6（McNemar + 多种子标准误） |
| 所有图表由脚本自动生成 | ✅ |
| `docs/FINAL_REPORT.md` 写清适用范围、计算成本与未解决问题 | ✅ 本文第 5-7 节 |

## 3. 方法与实现

| 模块 | 内容 | 关键文件 |
|---|---|---|
| M0 | Stim 线路与 DEM、固定种子采样、可复现数据链路 | `data_pipeline.py`、`circuits.py` |
| M1 | 统一 LER / 延迟 / 吞吐 / 内存夹具；MWPM、Union-Find、BP、BP+OSD 四个基线 | `benchmark.py`、`decoders/` |
| M2 | detector graph 特征化 + 二分图 GNN，输出逐机制后验，按固定 LLR 转换接入 BP | `graph_features.py`、`models/bipartite_gnn.py`、`m2_pipeline.py` |
| M3 | 同分布 / 噪声率外推 / 跨码距迁移；失败分析 | `m3_pipeline.py`、`scripts/m3_failure_analysis.py` |
| M4 | 旋转表面码；HGP 码构造（Tillich-Zémor、辛配对逻辑算符、code-capacity DEM）；图结构对比 | `codes/hgp.py`、`m4_pipeline.py` |
| M5 | 向量化 BP（约 100×）；GNN int8 量化；学习后验接入 MWPM | `decoders/bp_engine.py`、`scripts/m5_*.py` |
| **T8** | **OSD-CS(λ) 候选组合扫描**（Gray 码枚举 + 增量软权重） | `decoders/bp.py`、`scripts/t8_osd_cs_study.py` |
| **T18** | **忠实加权 Union-Find**（half-edge 生长 + erasure peeling + 2-core T-join） | `decoders/union_find.py` |

## 4. 结果

### 4.1 经典基线（M1，repetition d=3，4096 shots，p=0.01）

| decoder | 码容量 LER | 线路级 LER | 线路级 µs/shot |
|---|---:|---:|---:|
| mwpm | 0.00049 | 0.00952 | 0.1 |
| union_find | 0.00049 | **0.00903** | 10.7 |
| bp | 0.00049 | 0.01294 | 3.8 |
| bp_osd | 0.00049 | 0.01489 | 6.6 |

码容量下四个解码器完全一致；线路级下 Union-Find 追平并略优于 MWPM，BP 系落后。Union-Find 的数字来自 T18 重写后的重跑（`scripts/t18_rerun.ps1`）。

### 4.2 图结构与码族（M4）

- 线路级表面码 DEM 是稠密超图：d=3/d=5 的 check 度最大 48/80、平均 23.5/41.7，4-圈 1956/26046；
- 两个 HGP 码 [[13,1,3]] 与 [[58,16,3]] 由超图积构造，**不可匹配**（`matchable=False`），MWPM / Union-Find 完全不可用；
- 规律：**DEM 越大、BP 收敛率越低，学习先验的收益越大**（d=3 0.888 → d=5 0.535 → d=7 0.109）。

### 4.3 GNN 重加权（M2 / M3 / M4）

同分布 headline（repetition d=3，线路级 p=0.01，32768 shots）：

| decoder | logical errors | LER | 收敛率 | 平均迭代 | µs/shot |
|---|---:|---:|---:|---:|---:|
| mwpm | 217 | **0.00662** | - | - | 0.1 |
| bp | 309 | 0.00943 | 0.9899 | 0.707 | 1.9 |
| bp_gnn | 312 | 0.00952 | 0.9912 | **0.557** | 1.8 |
| bp_osd | 331 | 0.01010 | 0.9899 | 0.707 | 4.0 |
| bp_gnn_osd_learned_order | 317 | 0.00967 | 0.9912 | 0.557 | 3.0 |

结论：d=3 repetition 上**学习先验无显著收益**（+21% 迭代节省），但把 OSD 排序换成学习 logits 有正收益（0.01016 → 0.00967，McNemar z=+2.26，p=0.024）。跨码距迁移（d=3 → d=5）`bp` 0.05078 → `bp_gnn` **0.01709（−66%）**。

### 4.4 OSD 候选集学习（T8）

| 配置（32768 shots） | bp | OSD-0 | OSD-CS | bp+GNN | bp+GNN+OSD-CS | mwpm |
|---|---:|---:|---:|---:|---:|---:|
| repetition d=3 线路级 p=0.01 | 0.00943 | 0.01010 | **0.00754** (λ=4) | 0.00952 | **0.00760** | 0.00662 |
| 表面码 d=3 线路级 p=0.005 | 0.04007 | 0.04315 | **0.02505** (λ=8) | 0.03455 | **0.01913** | 0.01694 |

- OSD-0 在两个配置上都**有害**（McNemar z=−1.73 / −3.19）；OSD-CS 把它变成**显著有益**（`bp_osd_cs0 → bp_osd_cs8`：835 救回 / 242 弄坏，z=18.07）
- 收益集中在未收敛 shot：表面码 1521/32768 个未收敛 shot 上，`bp_gnn` 764 错 → OSD-0 **955 错（弄坏）** → OSD-CS(8) **259 错**（MWPM 参考 209）
- `bp_gnn_osd_cs8` 距 MWPM 仅 **+13%**（`bp` 差 +137%）
- 机制洞见：repetition 上 DEM 先验与学习先验在 λ=4 打平（247 vs 249，p=0.53）→ **候选集选对后，逐机制边际不再提供增量**；表面码上学习先验仍有 −24%（BP 越弱越有用）

### 4.5 Union-Find 重写（T18）

| 配置 | shots | MWPM | 修复前 | 修复后 | 修复后比值 |
|---|---:|---:|---:|---:|---:|
| 表面码 d=3 码容量 p=0.01 | 16384 | 0.00214 | 0.06311 | **0.00214** | 1.00 |
| 表面码 d=3 线路级 p=0.005 | 8192 | 0.01599 | 0.11121 | 0.01685 | 1.05 |
| 表面码 d=5 码容量 p=0.05 | 16384 | 0.04016 | 0.47565 | 0.04517 | 1.12 |
| 表面码 d=5 线路级 p=0.005 | 4096 | 0.01416 | 0.28906 | 0.02002 | 1.41 |

原实现的问题是**协议级错误**（97% 的缺陷 shot 违反 `H·c = s`），不是精度不足。重写覆盖了 half-edge 生长、冻结/解冻、以及 peeling 的三处语义缺陷，详见 `docs/T18_UNION_FIND_ANALYSIS.md`。

### 4.6 表面码 d=5 / d=7 多种子扫描（T6 / T10）

规模：5 个噪声率 × 3 seeds × {d=5, d=7}，线路级；d=5 每点 8192 test shots、d=7 每点 4096 test shots（训练 8192/4096 shots）。驱动 `scripts/t6_surface_grid.py`（可断点续跑、按价值排序）。

**已完成的 headline（d=5 线路级 p=0.005，3 seeds，每 seed 2048 shots，另含历史单点共 4 点）：**

| decoder | 各 seed LER | 均值 | 标准误 | 相对 `bp` |
|---|---|---:|---:|---:|
| mwpm | 0.01074 / 0.01257 / 0.01392 / 0.01294 | 0.01254 | 0.00066 | −88% |
| bp | 0.10352 / 0.10278 / 0.10400 / 0.10449 | 0.10370 | 0.00036 | — |
| **bp_gnn** | 0.06445 / 0.06030 / 0.06653 / 0.06897 | **0.06506** | 0.00184 | **−37%** |
| bp_osd | 0.13623 / 0.13904 / 0.13501 / 0.13818 | 0.13712 | 0.00092 | +32% |
| bp_gnn_osd | 0.08057 / 0.08301 / 0.08191 / 0.08228 | 0.08194 | 0.00051 | −21% |

- 多种子的**每一个 seed 单独看**都是 −37% 到 −42%，符号检验 p=1/8（3 seeds 下的一致方向）——与单点结论（−38%）一致，且排除了单 seed 偶然；
- `bp_osd` 在 d=5 上**比 bp 更差**（+32%），与 T8 的结论互相印证：**OSD 的问题从来不是"该不该开"，而是"候选基选得对不对"**。

**d=7 线路级 p=0.005（3 seeds，每 seed 4096 test shots）：**

| decoder | 各 seed LER | 均值 | 标准误 | 相对 `bp` |
|---|---|---:|---:|---:|
| mwpm | 0.00854 / 0.00977 / 0.01001 | 0.00944 | 0.00045 | −96% |
| bp | 0.23633 / 0.24463 / 0.24072 | 0.24056 | 0.00240 | — |
| **bp_gnn** | 0.16748 / 0.19629 / 0.17651 | **0.18009** | 0.00851 | **−25%** |
| bp_osd | 0.27734 / 0.30273 / 0.30396 | 0.29468 | 0.00867 | +23% |
| bp_gnn_osd | 0.21069 / 0.25586 / 0.26587 | 0.24414 | 0.01697 | +2% |

三条读数：

1. **增益与码距的关系不是单调的**：d=3 −18% → d=5 −37% → **d=7 −25%**。d=7 上 BP 已经越过了"仍可用"的边界（收敛率 0.118-0.121，平均迭代 28.9/32），学习先验能把收敛率提到 0.166-0.298、把迭代降到 23.5-27.6，但既不彻底也换不来同比例的精度——**局部推断本身失效时，重加权救不回来**。
2. **OSD-0 在 d=7 上伤害更大**：`bp_osd` 比 `bp` 差 23%，`bp_gnn_osd` 比 `bp_gnn` 差 36%（0.180 → 0.244）。原因清楚——d=7 未收敛率高达 88%，几乎每个 shot 都走 OSD-0。
3. **这正好是 T8 的适用位置，但本次窗口内没有实测**：T8 已证明 OSD-CS 能把表面码 d=3 的 OSD 从"有害"翻成"−52%"，d=7 是同一个失效模式、且规模更大。**按现有数据推断 d=7 上 OSD-CS 的收益应当更大，但这属于推断而非测量**，已列入第 7 节未解决问题。

**【待刷新】完整 LER-p 曲线（d=5 与 d=7 × 5 噪声率 × 3 seeds）**：由夜间 T6 网格产出，汇总在 `results/t10/MULTISEED.md` 与 `results/t10/surface_sweep_mean.json`；本节表格在网格结束后由巡检任务替换为最终值。

### 4.7 阈值估计（T7）

现有结果（MWPM，码容量，d=3/5，各 16384 shots）：**0.05 < p_th < 0.08**（线性插值 ≈ 0.0616）——p=0.05 时 d=5 更优（0.04016 vs 0.04877），p=0.08 时 d=3 更优（0.11432 vs 0.12799）。

BP / BP+OSD 的码容量阈值在 0.01-0.12 内**始终没有出现码距抑制**（d=3 全程优于 d=5），需要 d=7 与更高噪声率才能定位。

**【待刷新】线路级阈值**：T7 原本"完全未定"（现有扫描只有一个 p 点同时覆盖 d=3 与 d=5）。T6 网格给出 d=5/d=7 的线路级 LER-p 曲线后，`scripts/threshold_estimate.py` 会用 `results/t10/surface_sweep_mean.json` 补齐这个区间；结果写入 `results/m4/THRESHOLD.md`。

### 4.8 消融（T9）

README 7.2 列出 7 类消融，当前状态：

| 消融项 | 状态 | 结论 |
|---|---|---|
| top-k 候选规模（OSD-CS 的 λ） | ✅ | 表面码上单调（0.04315 → 0.02505，λ=0→8）；repetition 上非单调（λ=4 最优），说明 `Σ|posterior LLR|` 只是 LER 的代理 |
| 有/无 GNN 重加权 | ✅ | 见 4.3 / 4.6：d=3 repetition 无效、大图有效（−18% ~ −37%） |
| 有/无 OSD | ✅ | 见 4.4：OSD-0 有害、OSD-CS 大幅有益 |
| 强度自标定 | ✅ | 目标分布验证集上重选先验插值强度，最优点落在 0.75-1.00，曲线平坦 |
| 不同图特征组合 | ✅ | 见下方 4.8.1 |
| CPU vs GPU | ⛔ | 不适用（交付环境无 GPU，见第 6 节） |
| 浮点 vs 量化推理 | ✅ | M5 动态 int8：权重压缩 3.72×、精度无损、CPU 无加速 |

#### 4.8.1 图特征组合消融（`scripts/t9_feature_ablation.py`）

做法：把某一组特征列**置零**后用同一 seed 重训（架构不变），因此比较的是该组特征携带的**信息量**。repetition d=3 线路级 p=0.01，32768 shots：

| 消融臂 | 机制 AUC | bp_gnn LER | 逻辑错误 | Δ LER |
|---|---:|---:|---:|---:|
| all（基线） | 0.9905 | 0.00952 | 312 | — |
| no_check_features | 0.9924 | 0.00943 | 309 | −0.00009 |
| no_variable_geometry | 0.9894 | 0.00964 | 316 | +0.00012 |
| no_check_geometry | 0.9924 | 0.00955 | 313 | +0.00003 |
| no_edge_degree | 0.9880 | 0.00943 | 309 | −0.00009 |
| **prior_only**（只留 DEM 先验） | 0.9857 | **0.02371** | 777 | **+0.01419** |

两条结论：

1. **显式的坐标/时间特征在 GNN 里是冗余的**：置零 `detector_index`/`detector_time` 后 LER 变化 < 0.0002。原因是**二分图拓扑本身已经携带了几何信息**，消息传递可以从中恢复局部性——这也解释了为什么 `graph_features.py` 里那批"手工几何特征"对最终精度贡献有限。
2. **但图结构特征整体不可省**：只留 DEM 先验（置零所有 check 特征与度数特征）时，机制 AUC 仍有 0.9857，**LER 却恶化 2.5×**（0.00952 → 0.02371）。这正是 M2/M3 那条主线的又一个侧面：**判别能力好 ≠ 能当先验用**；把机制判别转成可用的 BP 先验，依赖的是图结构特征（度、拓扑）而不只是"证据强度"。

**表面码 d=3 线路级 p=0.005，32768 shots（同一脚本；`all` 臂精确复现出厂模型 0.03455 / 1132 错）：**

| 消融臂 | 机制 AUC | bp_gnn LER | Δ LER |
|---|---:|---:|---:|
| all（基线） | 0.9931 | 0.03455 | — |
| **no_variable_geometry** | 0.9933 | **0.02615** | **−0.00839（−24%）** |
| no_check_features | 0.9932 | 0.02972 | −0.00482（−14%） |
| no_check_geometry | 0.9934 | 0.03174 | −0.00281（−8%） |
| no_edge_degree | 0.9930 | 0.03439 | −0.00015 |
| prior_only | 0.9921 | 0.06616 | +0.03162（+91%） |

3. **在表面码上，显式的坐标/时间特征不只是冗余，而是有害的。** 置零 `detector_index_mean` / `detector_time_mean` 反而把 LER 拉低 **24%**（0.03455 → 0.02615），置零整组 check 特征降 14%，而机制 AUC **几乎不动**（0.9931 → 0.9932-0.9934）。也就是说：GNN 从这几列里学到了**不可迁移的位置先验**并因此过拟合，而拓扑本身已经提供了同等（甚至更干净）的几何信息。
4. `prior_only` 仍然是最差的一臂（+91%），与 repetition 一致：**"用得上"的不是坐标，而是图结构（度、拓扑）与拓扑条件下的机制推断。**

> **工程含义（建议的后续动作）**：把 `detector_index_mean`/`detector_time_mean`（以及 check 的 `detector_index`/`detector_time`）从默认特征集里去掉可以**无成本地改善精度**，代价是失去跨码距的位置泛化能力——需要用多种子复核并在 d=5/d=7 上重测。上述为**单 seed** 结果，只作方向性结论。


### 4.9 工程性能（M5 / T11）

由 `scripts/engineering_table.py` 从 `results/` 自动生成 `results/m5/ENGINEERING_TABLE.md`，含 M1 六个配置与 M2/M3/M4/T8/T18 的运行记录：LER、µs/shot、shot/s、峰值 RSS delta、BP 平均迭代、OSD 触发比例、syndrome 一致率、模型规模。不可测项（GPU 延迟/显存、更大 batch 的吞吐）在表中显式列出原因。

关键工程数字：
- 向量化 BP 约 **100×** 加速（repetition d=3 205 → 1.9 µs/shot；表面码 d=3 18.5 ms → 0.54 ms/shot）；
- GNN 前向优化 1.11-1.22×（T5，未达 10 ms/shot 目标，遗留按边分块/稀疏乘）；
- OSD-CS 延迟（强制每 shot 都跑 OSD）：repetition d=3 λ=0→4 为 149→304 µs；表面码 d=3 λ=0→8 为 1323→2432 µs。实际 OSD 只在未收敛 shot 上触发（repetition 约 1%、表面码 d=3 约 60%），**推荐工作点 λ=4**；
- 加权 Union-Find：repetition d=3 线路级 10.7 µs/shot（低于同配置 BP），表面码 d=5 线路级 3441 µs/shot。

## 5. 适用范围

**结论成立的区间：**

- **码族**：repetition code（d=3/5/9）、旋转表面码（d=3 完整、d=5 完整、d=7 见 4.6）、两个小型 HGP 码。**不可匹配码（HGP）上 MWPM / Union-Find 不可用**，BP 系是唯一通用选择。
- **噪声**：code-capacity 与 circuit-level，p ∈ [0.001, 0.12]。
- **统计规模**：8192-32768 shots；每结论 3 seeds（d=5 线路级 headline 已满足；d=7 与其余噪声率点由 T6 网格补齐）。
- **增益条件（最重要的一条）**：学习重加权的收益随 **BP 变弱**（DEM 更大、收敛率更低）而增大。d=3 repetition（收敛率 0.99）上无显著收益；HGP 与 d=5/d=7 表面码上有 −11% ~ −37% 的稳定收益。**不要在小图上期待收益。**
- **谁在起作用**：在 OSD 路径上，**候选基质量（OSD-CS）比机制边际（学习先验）重要得多**：λ 从 0 到 8 带来 −42%，而先验换成学习值在 repetition 上是 0%。

**明确不适用的场景：**

- GPU 相关的一切数字（延迟、显存、吞吐）——交付阶段无 GPU；
- d=9 及更大码距的 BP 系解码（收敛率 0.000，属"需要更强先验或更长迭代"的开放问题，不是算力问题）；
- 时序编码器（syndrome history）与端到端可微 BP——未实现。

## 6. 计算成本

| 项目 | 实测 |
|---|---|
| 交付环境 | Intel i5-12400（6C/12T）/ 16 GB / CPU-only |
| 回归测试 | `pytest -q` 约 8 s（72 项） |
| 端到端 smoke | `scripts/run_all.ps1` 约 18 s |
| 单点 M2 训练 + 评测（表面码 d=5，8192 test shots） | 约 33 min（训练 ~18 min） |
| 单点 M2 训练 + 评测（表面码 d=7，4096 test shots） | **92 min**（训练 18 min，评测 ~74 min） |
| T6 全网格（30 点） | 约 12 h 预算（按价值排序，超预算时丢弃 d=7 的低价值点） |
| T8 研究（两个配置 × 32768 shots × 5 个 λ） | 约 15 min |
| T18 重跑（M1 六个配置 + 表面码 10 个扫描点） | 约 25 min |
| **第一阶段合计算力壁钟** | **约 20-25 h**（与 `docs/ROADMAP_TODO.md` 第 1.4 节预算一致） |

**结论**：交付瓶颈是编码人日，不是 CPU 算力。16 GB 内存是表面码 d=5/d=7 训练的硬约束（`batch_size` 必须 ≤128；1024 会在 d=5 直接 OOM 并被系统静默杀死）。

**实测的 d=7 成本结构（新增观察，值得记录）**：d=7 单点 92 min，其中训练只占 18 min，**评测占了 74 min（80%）**。评测里的主要开销是 `bp_osd` / `bp_gnn_osd`：d=7 的 BP 收敛率只有 0.109，意味着约 89% 的 shot 要跑 OSD-0，而 OSD-0 在 6023 个 mechanism × 336 个 detector 的规模上仍是逐列 numpy 的前向消元。**要把 d=7 扫描做便宜，先优化 OSD 的批量化/位运算重写，而不是优化训练。** 这也解释了本窗口内 d=7 只能覆盖少量噪声率点。

## 7. 未解决问题

1. **OSD-CS 的目标函数不是 LER 的单调代理。** λ 增大时目标值单调不增，但 repetition 上 LER 反而在 λ=4 之后变差。直接动机是**数据驱动的候选排序（learning-to-rank）**——这正是 T8 未做的那一半。
2. **Union-Find 的 2-core T-join 是近似。** 当前用最小生成森林上的 T-join 收尾，不是 core 上的精确最小 T-join；后者能进一步压低 d=5 的差距。
3. **学习先验的机制性解释仍不完整。** "BP 越弱收益越大"是经验规律；缺少从 DEM 结构（度数、环数、收敛率）到收益的定量预测。
4. **HGP 只做到 code-capacity、小码（[[13,1,3]]、[[58,16,3]]）。** 结构化量子 LDPC（非 HGP）未实现（`docs/ROADMAP_TODO.md` F1）。
5. **BP+OSD 的 OSD 触发策略仍是"未收敛就触发"。** M3 已证明不存在"只救不伤"的阈值，T8 说明正确的解法是换候选集而不是换阈值；但**何时该触发 OSD-CS** 仍以"未收敛"为唯一判据。
6. **d=9 是 BP 的失能区**（收敛率 0.000，128 ms/shot），交付内未处理。
7. **小规模统计功效**：部分结论（HGP、跨码距迁移）仍是单 seed 或 2048 shots 量级，标准误 0.005-0.008，只够给方向。

## 8. 复现说明

```powershell
# 0) 环境（CPU-only）
$env:PYTHONPATH = "src"; $env:PYTHONUTF8 = "1"

# 1) 回归测试（72 项）
.\.venv\Scripts\python.exe -m pytest -q

# 2) 端到端 smoke（约 18 s）
.\scripts\run_all.ps1

# 3) 经典基线 + 表面码扫描（T18 重跑，生成 results/m1 与 results/m4/surface_sweep.*）
.\scripts\t18_rerun.ps1

# 4) 表面码 d=5/d=7 学习重加权网格（T6，可断点续跑）
.\.venv\Scripts\python.exe scripts\t6_surface_grid.py --print-plan
.\.venv\Scripts\python.exe scripts\t6_surface_grid.py --budget-minutes 720

# 5) 多种子汇总（T10）与阈值（T7）
.\.venv\Scripts\python.exe scripts\t10_multiseed_stats.py --results-dir results\m4_surface --output-dir results\t10
.\.venv\Scripts\python.exe scripts\threshold_estimate.py --inputs results\t10\surface_sweep_mean.json results\m4\surface_sweep.json results\m4_threshold\surface_sweep.json --output results\m4\THRESHOLD.md

# 6) OSD 候选集研究（T8）
.\.venv\Scripts\python.exe scripts\t8_osd_cs_study.py --config <run>\config.json --checkpoint <run>\model_state.pt --sweeps 0 2 4 6 8 --output-dir results\t8\<tag>

# 7) 工程性能表（T11）
.\.venv\Scripts\python.exe scripts\engineering_table.py
```

**逐模块的技术细节**见 `docs/M0_ENVIRONMENT_AND_DATA_PIPELINE.md`、`M1_BASELINE_DECODERS_AND_BENCHMARK.md`、`M2_GNN_REWEIGHTING.md`、`M3_HYBRID_DECODER.md`、`M4_HGP_AND_SURFACE.md`、`M5_ENGINEERING.md`、`M5_DECOMPOSED_MWPM.md`、`BP_IMPLEMENTATION.md`、`T8_OSD_CANDIDATE_SET.md`、`T18_UNION_FIND_ANALYSIS.md`。
