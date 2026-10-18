# 已完成任务归档（T1–T11、T17、T18）

- **归档日期**：2026-10-18
- **来源**：从 `docs/ROADMAP_TODO.md` 第 2 节迁出，保留完成时的原始记录与验收信息。
- **范围**：第一阶段 P0/P1 已完成任务。T12–T15 与 T8 learning-to-rank 仍留在 ROADMAP 的 P2 清单中。

> 本文件是历史记录，不再作为当前任务状态的主源；未完成任务、优先级和工时以 `docs/ROADMAP_TODO.md` 为准，科学结论与数字以 `docs/FINAL_REPORT.md` 为准。

## 1. 启动批次（P0）

- [x] **T1 · CI（GitHub Actions）**　（P0，2026-10-15 完成）
  - 产出：`.github/workflows/ci.yml`，Python 3.10/3.12 两个矩阵，torch 走 CPU 索引安装，跑 `pytest -q`
  - 待办：绑定远端（决策项 D1）后确认首次运行通过

- [x] **T2 · 文档同步**　（P0，2026-10-15 完成）
  - 已修正：`docs/HARDWARE_REQUIREMENTS.md` 的资源估算说明、`README.md` 的进度与交付范围段；各里程碑文档的历史叙述已按单一版本清理
  - 说明：`results/m4_surface/` 不含 `SUMMARY.md` 属设计如此（M4 管线只输出 `results.json`/`summary.csv`），不作为缺口

- [x] **T3 · 一键复现总脚本 + 端到端 smoke**　（P0，2026-10-15 完成）
  - 产出：`scripts/run_all.ps1`（默认小规模：单测 → M0 → M1 → CPU 预算探针 → M2 汇总与出图；`-Full` 追加 M2 训练与 M3 扫描）
  - 实测：跳过单测的端到端运行 **18 s** 全绿（M0 0.8 s、M1 1.5 s、CPU 探针 15.7 s、M2 汇总 0.1 s）

- [x] **T4 · 补噪声率 p = 0.001 / 0.002**　（P0，2026-10-15 完成）
  - 产出：`configs/m1_repetition_{code_capacity,circuit_level}_p0p00{1,2}.json` 与对应 `results/m1/` 结果（各 32768 shots）
  - 结果：p=0.001 四个解码器均为 0 个逻辑错误；p=0.002 为 0-1 个。**该区间低于 32768 shots 的分辨率**，要给出定量 LER 需 ≥1e5 shots，因此这两个点在报告中只作低噪声端的定性说明
  - 注意：噪声率写在 `experiment.noise.physical_error_rate`（不是 `experiment.physical_error_rate`）

- [x] **T5 · GNN 前向优化**　（P0，部分完成，2026-10-15）
  - 依据：第 1.3 节第 3 条——d=7 时 GNN 前向 39 ms/shot，与 BP 同量级
  - 已完成：拆掉消息 MLP 的三段 `cat`、把边特征项提到 batch 维之外、两个方向复用 gather 与聚合缓冲；数值等价（Δ logits ≤ 3e-7），已交付结果不变（M2 headline `bp_gnn` 312 错误 / 0.00952 逐位一致）
  - 实测：前向 **1.11-1.22×**（d=7 39.2 → 35.3 ms/shot @ batch 256；d=3 repetition 37.0 → 32.4 µs/shot），训练单步 4.65 → 4.29 s
  - **未达标**：原目标「d=7 ≤ 10 ms/shot」未实现；小 batch 下峰值 RSS 反而升高（d=7/batch 256：2.9 → 4.5 GB）
  - 遗留（转入后续工作）：按边分块的消息传递、稀疏矩阵乘实现、解耦消息 MLP 的中间宽度。详见 `results/m5/GNN_PERF.md`
  - 验收：`results/m5/GNN_PERF.md`、`tests/test_gnn_forward_equivalence.py`

## 2. 主线实验（P1）

- [x] **T6 · 表面码 d=5 / d=7 学习重加权 + LER-延迟 Pareto**　（P1，2026-10-17 完成 **30/30 点**）
  - 规模：5 个噪声率 x 8192 shots x 3 seeds，d=5 与 d=7
  - 已确认的约束：d=5/d=7 训练必须用 `batch_size=128`——`batch_size=1024` 在 d=5 的 5004 条边上内存耗尽（进程被系统终止，无 traceback），d=7 更紧张
  - **已完成的首个数据点**（2026-10-15）：表面码 d=5 线路级 p=0.005，2048 shots、1 seed——`bp` 0.10352 → `bp_gnn` **0.06445（-38%）**，迭代 -43%，收敛率 0.579 → 0.767，延迟 10.3 → 5.8 ms/shot；d=3 的对应增益是 -18%，**增益随码距增长**（详见 `docs/M4_HGP_AND_SURFACE.md` 第 7.4 节）
  - **2026-10-16 夜间进展**：d=5 与 d=7 的线路级 p=0.005 **各 3 seeds 已完成**（d=5 8192 test shots/seed、d=7 4096/seed）
    - d=5：`bp` 0.10376 ± 0.00051 → `bp_gnn` **0.06527 ± 0.00258（−37%）**；`bp_osd` 0.13741（+32%）、`bp_gnn_osd` 0.08240
    - d=7：`bp` 0.24056 ± 0.00240 → `bp_gnn` **0.18009 ± 0.00851（−25%）**；`bp_osd` 0.29468（+23%）、`bp_gnn_osd` 0.24414（比 `bp_gnn` 差 36%）
    - **关键修正**：增益与码距的关系是**先升后降**（d=3 −18% / d=5 −37% / d=7 −25%），此前"增益随码距增长"的说法只在 d=3→d=5 成立。d=7 处 BP 收敛率 0.118-0.121、平均迭代 28.9/32，属局部推断失效区
    - d=7 单点实测 **92 min**（训练 18 min + 评测 74 min，评测被 OSD-0 主导）→ 本窗口内只能覆盖少量噪声率点
  - **2026-10-16 夜间完成**：共 16 个运行——d=5 覆盖 p ∈ {0.003, 0.005, 0.008} × 3 seeds（8192 test shots/seed）；d=7 覆盖 p ∈ {0.003, 0.005} × 3 seeds 与 p=0.008 × 1 seed（4096/seed）
    - d=5：−43.4% / −37.1% / −32.8%；d=7：−32.6% / −25.1% / −15.6%（都随 p 升高而下降）
    - 同 p 下 d=5 的增益在三个噪声率上都高于 d=7
    - **规律修正**：收益在 BP 强度"中等"时最大——码距轴非单调（**d=3 −29.0% ± 2.4%（3 seeds）** → d=5 −37.1% → d=7 −25.1%），噪声率轴单调下降。"BP 越弱收益越大"只是码距轴现象
    - **2026-10-17 夜间完成全部 30 点**（`session4_seeds.ps1 -Stage grid`；6 个残点 208.5 min：d=5 p=0.002 三点 22.3-22.6 min，d=7 p=0.002 三点 42.5-51.6 min）
      - d=5 噪声率曲线：−37.4%（p=0.002）→ **−43.4%（p=0.003，峰值）** → −37.1% → −32.8% → −25.4%（p=0.01）
      - d=7：−38.2% → −32.6% → −25.1% → −13.4% → −9.9%，**单调下降**，峰值落在区间下沿
      - **新增结论**：噪声率轴上 d=5 出现低端拐点（p=0.003），d=7 的拐点已移到 p≤0.002 → 「拐点位置随码距移动」；OSD-0 在全部 10 个点上都比不开更差（`bp_osd` +10.4%~+60.5%，`bp_gnn_osd` +18.0%~+48.7%）
  - 验收：✅ 30/30 点、每点 3 seeds，`results/t10/MULTISEED.md` 与 `results/m4/THRESHOLD.md` 已由收口脚本重生成
  - 验收：✅ `results/m4_surface/` 的 d=5/d=7 `bp` vs `bp_gnn` 对照表（含均值 ± 标准误、shots 与 seed 数）；Pareto 图由 `results/t10/MULTISEED.md` 支撑
  - 依据：第 1.3 节第 1、2 条
  - 工作量：编码 1-2 人日；算力约 18 h（隔夜 + 1 天）
  - 验收：`results/m4_surface/` 的 d=5/d=7 `bp` vs `bp_gnn` 对照表 + `pareto_ler_latency` 图，标注 shots 与 seed 数

- [x] **T7 · 阈值估计**　（P1，2026-10-16 完成）
  - 产出：`scripts/threshold_estimate.py` + `results/m4/THRESHOLD.md`（从 LER-p 扫描自动生成；判据是两个最小码距的 LER 排序翻转区间）
  - 已得结论（MWPM，码容量，d=3/5，各 16384 shots）：**0.05 < p_th < 0.08（线性插值 ≈ 0.0616）**——p=0.05 时 d=5 更优（0.04016 vs 0.04877），p=0.08 时 d=3 更优（0.11432 vs 0.12799）
  - **线路级阈值（T6 完成后）**：MWPM 为 **0.005 < p_th < 0.008**；BP / BP+OSD 在 0.003-0.01 内始终 d=3 更优，阈值在采样区间之外（p_th < 0.003）。d=7 曲线已完成，但 d=5 在全部 5 个采样点均优于 d=7，未观测到排序翻转。
  - **仍开放（不阻塞本地交付）**：**BP / BP+OSD 的码容量阈值在 0.01-0.12 内始终没有出现码距抑制**（d=3 全程优于 d=5）；要定位阈值需扩展噪声率范围并加入 d=7。
  - 依赖：T6（线路级与 d=7 数据）

- [x] **T8 · OSD 候选集学习：OSD-λ / OSD-CS**　（P1，**最高性价比**，2026-10-15 完成 OSD-CS 部分）
  - 依据：M2 的 OSD 排序无改善、M3 的 OSD-0 回退无 Pareto 窗口、M5 的 MWPM 边权重无收益——三条结论都指向「学习目标应从逐机制边际改为候选基质量」
  - **已完成**：OSD-CS(λ)（combination sweep）——对 λ 个最不可靠的非 pivot 列枚举全部子集，按 `Σ|posterior LLR|` 取最优；Gray 码枚举 + 增量权重。新增解码器 `bp_osd_cs` / `bp_gnn_osd_cs` / `bp_gnn_osd_cs_learned_order`，`decoder.osd_combination_sweep` 配置项，4 项单测（`tests/test_osd_combination_sweep.py`），研究脚本 `scripts/t8_osd_cs_study.py`
  - **结果（repetition d=3 电路级 p=0.01，32768 shots）**：`bp` 309 → OSD-0 331（确认 M3 的负结果）→ **OSD-CS(4) 247**；OSD-0 vs OSD-CS(4)：救回 126 / 弄坏 42，McNemar z=6.48，p<1e-6。在 288 个 BP+GNN 未收敛 shot 上，OSD-0 把 154 变成 175（弄坏），OSD-CS(4) 降到 91（MWPM 83）
  - **结论**：M3 的负结果的正面出口——把学习目标从「逐机制边际」换成「候选基质量」后，OSD 回退从「有害」变成「显著有益」；而 DEM 先验与学习先验在 λ=4 上**在种子噪声内不可区分**（单 seed 曾写「打平 247 vs 249，p=0.53」，**3 seeds 复核后已撤回**），说明**候选集选对之后，逐机制边际不再提供额外信息**
  - 未完成（**不阻塞交付**，列为 P2 研究项）：learning-to-rank（数据驱动的候选排序）；见第 7 节
  - 产出：`results/t8/`、`docs/T8_OSD_CANDIDATE_SET.md`
  - **2026-10-16 补种子（P1 收口）**：d=7 三个噪声率各补到 **3 份独立测试集 × 1024 shots = 3072 shots**（`scripts/t8_osd_cs_study.py --seed-offset 10/20`，输出 `results/t8/d7_p0p00{3,5,8}_probe_s{10,20}/`；汇总脚本 `scripts/t8_d7_multiseed.py` → `results/t8/D7_MULTISEED.md`）
    - 结果：`bp_gnn_osd_cs4` 相对 `bp_gnn` 为 **−34.9%（z=−5.39）/ −11.6%（z=−2.67）/ −1.9%（n.s.）**；相对 OSD-0 三个点全部 −42.3% / −25.0% / −17.7%（z=−9.5 / −9.2 / −9.1）
    - 口径：只换测试集种子、共用同一 checkpoint → 压的是 LER 估计误差，不含模型种子方差
  - **2026-10-16 补种子（repetition d=3 全研究，3 seeds / 98304 shots）**：`scripts/t8_repetition_multiseed.py` → `results/t8/REPETITION_D3_MULTISEED.md`。两个新 seed 复用 M2 旗舰表的 s10/s20 运行（模型与 splits 都换）
    - `bp_osd_cs0 → bp_osd_cs4`：**−0.00279 ± 0.00012**（z=−12.23）→ 主结论更硬
    - `bp_osd_cs4 → bp_gnn_osd_cs4`：**+0.00055 ± 0.00043**（逐 seed +0.00006/+0.00140/+0.00018）→ **单 seed 的「打平（p=0.53）」要撤回**，改为「种子噪声内不可区分」
  - 验收：✅ 新增 decoder + 单测 + 与 `bp`/`bp_gnn`/`bp_gnn_osd` 的配对检验表 + d=7 与 repetition 的多种子汇总
  - **2026-10-17 夜间完成（模型 + 数据都换，`session4_seeds.ps1 -Stage probes`）**：6 次探针 6.5-9.5 min/次 → `results/t8/D7_MODEL_SEEDS.md`（新脚本 `scripts/t8_d7_model_seeds.py`，种子是重复单位）
    - OSD-0 相对 `bp_gnn` 恶化 **+43.0%±14.0% / +34.7%±12.2% / +15.8%±2.4%**（p=0.003/0.005/0.008，3 个模型 seed 全部同号）
    - OSD-CS 修回 **−41.7%±3.8% / −26.2%±1.1% / −14.9%±1.8%**；但 CS 相对 `bp_gnn` 的净增益只有 p=0.003 有方向（−15.7%±13.3%，n.s.），p≥0.005 归零
    - → **旧口径的 −34.9%/−11.6%/−1.9% 是单模型效应**（`D7_MULTISEED.md` 保留为「只换测试集」口径）；另补 d=7 p=0.01 的 3 份测试集（cs4 比 `bp_gnn` 差 +8.4%）

- [x] **T9 · 消融补全：图特征组合 + top-k 候选规模**　（P1，2026-10-15 完成）
  - top-k：OSD-CS 的 λ ∈ {0,2,4,6,8} 扫描（见 T8）——表面码单调、repetition 非单调（λ=4 最优）
  - 图特征组合：`scripts/t9_feature_ablation.py`（置零特征列 + 同 seed 重训，架构不变）
    - repetition d=3：显式坐标/时间特征**冗余**（ΔLER < 0.0002）；只留 DEM 先验时 LER 恶化 2.5×（0.00952 → 0.02371）而 AUC 仍有 0.986
    - 表面码 d=3：**单 seed 看到的"置零位置特征降 24%"经 3 seeds 复核后不成立**（种子 7/17/27 的 Δ 为 −24.3% / +2.3% / +14.5%，均值 −2.5%，符号翻转）→ 正确说法是"冗余"而非"有害"
    - 结论：① 显式坐标/时间特征在 GNN 里**冗余**（两种码族、3 seeds 一致）；② 但**图结构特征整体不可省**——只留 DEM 先验时 repetition 恶化 2.5×、表面码恶化 91%，且 AUC 仍高达 0.986，再次印证"判别好 ≠ 当先验好用"
    - **2026-10-16 补种子**：repetition d=3 的 6 条臂全部补到 **3 seeds（98304 shots）**（`scripts/t9_multiseed.py` 跨 seed 配对汇总 → `results/t9/REPETITION_D3_MULTISEED.md`；补跑用 `scripts/t9_feature_ablation.py --seed-offset 10/20 --merge` 分两次合并进同一目录）
      - 坐标/时间特征：ΔLER **+0.00113 ± 0.00104**（t≈1.1，不显著）→ 「冗余」；只留 DEM 先验：ΔLER **+0.01329 ± 0.00045**（t≈30，恶化 133%）→ 「图结构特征不可省」
    - **方法学教训（两条）**：① 32768 shots 下种子间散布仍有 ±15%，单 seed 消融不足以支撑结论；② 跨 seed 推断必须用种子的实测散布，把各 seed 的 shot 直接求和会把种子间散布当成二项噪声、高估显著性（见 `scripts/t9_multiseed.py` 的两张表）；均已写入 `docs/FINAL_REPORT.md` 4.8.1
  - 产出：`results/t9/`、`docs/FINAL_REPORT.md` 4.8 节
  - 依据：`README.md` 7.2 列出 7 类消融，当前 3 类有数据
  - 依赖：T8（top-k 需要候选集机制）
  - 工作量：编码 3 人日；算力 1 h
  - **2026-10-18 完成（`session4_seeds.ps1 -Stage ablation` + `prior_only` 补臂）**：表面码 d=3 的 5 条臂全部补齐到 3 seeds（98304 shots，`results/t9/SURFACE_D3_MULTISEED.md`）
    - `no_check_features` −4.8%±5.6%、`no_variable_geometry` −3.4%±11.1%、`no_edge_degree` +5.1%±4.3%（均在噪声内）；`no_check_geometry` −15.1%±8.5%（逐 seed 同号、t≈1.8，未达显著）
    - `prior_only` **+103.4% ± 12.0%**（逐 seed +0.03162/+0.03027/+0.04303）→ 「图结构特征不可省」在 3 seeds 上确认

- [x] **T10 · 多种子统计稳健性**　（P1，2026-10-16 完成；repetition d=5 的强度复核仍未做）
  - 产出：`results/t10/MULTISEED.md` + `multiseed.json` + `surface_sweep_mean.json`（跨 seed 均值 ± 标准误、逐 seed 值、配对 Δ 与符号检验）
  - 修正了一处数据质量问题：p=0.005 组曾混入 2048-shot 的历史单点，加了 `--min-test-shots` 过滤
  - **2026-10-16 补测 2**：表面码 d=3 线路级 p=0.005 的锚点也补到 3 seeds（`scripts/m2_headline_multiseed.py` 换 `--base-config`，产物 `results/m4_surface/D3_MULTISEED.md`）：`bp` 0.04149 → `bp_gnn` 0.02945，**Δ = −0.01204 ± 0.00239（−29.0%）**，三个 seed 同号；单 seed 曾给 −18.2%（三个 seed 里最小）→ 4.6 节的「码距轴」读数已按此更新（峰值仍在 d=5，但曲线更平坦）
  - **2026-10-16 补测**：M2 旗舰表（repetition d=3 同分布，效应量最小的一张表）补到 3 seeds / 98304 shots：`bp_gnn` vs `bp` 的配对 ΔLER = +0.00009 / −0.00098 / +0.00003（均值 −0.00028 ± 0.00035，符号翻转）→ 「无收益」结论被误差棒确认；`mwpm` vs `bp_gnn` = +0.00288 ± 0.00034（三 seed 同号）。工具：`scripts/m2_headline_multiseed.py`（`--write-configs` / `--aggregate`）+ `scripts/m2_headline_seeds.ps1`；产物 `results/m2/HEADLINE_MULTISEED.md`
  - 范围：对 4 个关键结论（d=5/d=7 的 `bp` vs `bp_gnn`、HGP 跨尺寸迁移、MWPM 边权结论）给出 3 seeds 的均值 ± 标准误与配对检验；并在 repetition d=5 的目标分布验证集上复核先验插值强度（当前 d=5 评测沿用源配置上限 1.00）
  - 工作量：编码 1 人日；算力并入 T6
  - **2026-10-18 完成（`session4_seeds.ps1 -Stage extra`）**：两项迁移各补到 3 seeds
    - **M3 跨码距迁移（d=3 → d=5）稳健**：`bp` → `bp_gnn` 为 −66.3% / −68.0% / −71.0%（三个种子同号；0.05078→0.01709 / 0.05466→0.01752 / 0.05365→0.01556）
    - **HGP 跨尺寸迁移不稳健**：−11.4%（s0）/ +4.9%（s10）/ +12.5%（s20），均值 **+2.0% ± 7.1%** → **单 seed 的 −11% 结论已撤回**（源域 [[13,1,3]] 的增益仍同号：−3.1%/−5.9%/−9.7%）

- [x] **T11 · CPU 工程性能表**　（P1，2026-10-15 完成）
  - 依据：`README.md` 8.2
  - 产出：`scripts/engineering_table.py` 从 `results/` 自动生成 `results/m5/ENGINEERING_TABLE.md`（95 行：M1 六个配置 + M2/M3/M4 运行记录，含 LER、µs/shot、shot/s、峰值 RSS delta、BP 平均迭代、OSD 触发比例、syndrome 一致率、模型规模）
  - 不可测项（GPU 延迟/显存、更大 batch 的吞吐）在表中显式列出原因

## 3. 报告与基线修复（P1）

- [x] **T18 · 修正 Union-Find 解码器**　（P1，2026-10-15 完成）
  - 现象：`UnionFindDecoder` 在表面码上严重失效——d=3 码容量 p=0.01 为 0.06311（MWPM 0.00214），d=5 为 0.22607-0.47565（接近随机）
  - 根因：`src/graph_qec/decoders/union_find.py` 的 `_decode_shot` 只把合并边的 `fault_mask` 累加进输出，**缺少标准 Union-Find 解码器的 peeling 步骤**（簇内对生成树自叶向根剥离，只保留真正的 correction）；该实现在 repetition d=3 的机构上恰好接近可用（0.01294），因此一直未被发现
  - 影响：`results/m4/surface_sweep.json` 中的 `union_find` 列不可用；`results/m4/SURFACE_BASELINE_TABLE.md` 已不含该列，但仍需显式声明
  - **决策（2026-10-15）：修实现，不降级**——不采用「把 Union-Find 限定为 repetition code 专用基线」的路线，因此 T18 保持 P1；修复后必须重跑所有引用它的结果，不能只在文档里缩小适用范围
  - **完成（2026-10-15）**：按分析文档的路线重写为 **忠实的加权 Union-Find**（`src/graph_qec/decoders/union_find.py`）：half-edge 生长 + 前沿中途相遇融合 + 冻结/解冻 + erasure peeling（带 syndrome 翻转）+ 2-core T-join 收尾。**关键决策由用户于 2026-10-15 拍板：按分析文档实现忠实版本**
  - 修复过程中定位到 3 个具体实现缺陷：① 簇覆盖 boundary 节点时从未置 boundary 标志；② 冻结的簇在融合后重新变奇时从未解冻；③ 前沿抵达已覆盖顶点时漏把穿越的边加入 ε'。三者都写进了 `docs/T18_UNION_FIND_ANALYSIS.md`
  - **结果**：表面码 d=3 码容量 0.06311 → **0.00214（= MWPM）**；d=3 线路级 0.07068 → 0.01685（MWPM 0.01599）；d=5 码容量 0.22607 → **0.00049**（MWPM 0.00037）；全部 10 个扫描点比值 1.00-1.41×。M1 repetition 上 union_find 37 vs mwpm 39（**略优**）
  - 产出：`results/m1/`（重跑）、`results/m4/surface_sweep.{json,csv}`（重跑）、`scripts/t18_rerun.ps1`、`tests/test_union_find_t18.py`（6 项）、`docs/T18_UNION_FIND_ANALYSIS.md`
  - 验收：✅ 表面码 d=3 码容量 p=0.01 的 Union-Find LER 与 MWPM **完全一致**（0.00214 vs 0.00214，16384 shots），单测已断言；所有引用 Union-Find 的表格已重新生成

- [x] **T17 · 技术报告（集成 M0-M5 + 局限性 + 复现说明）**　（P1，2026-10-15 完成）
  - 产出：`docs/FINAL_REPORT.md`（摘要 + 交付范围 + 方法与实现 + 4.1-4.9 结果 + 适用范围 + 计算成本 + 未解决问题 + 复现说明）
  - 说明：第 4.6/4.7 节（d=5/d=7 全网格与线路级阈值）已在 2026-10-18 用 `results/t10/` 与 `results/m4/THRESHOLD.md` 的最终值刷新
  - 验收：✅ 含适用范围、计算成本、未解决问题三节
