# 硬件条件评估与云部署方案

> 评估日期：2026-09-25  
> 评估依据：当前仓库中的 `README.md`、`docs/LITERATURE_REVIEW.md` 和 `docs/references.md`。  
> 说明：以下资源估算基于项目规划、模型复杂度与实测数据（见 `docs/ROADMAP_TODO.md` 第 1 节）。第一阶段在 CPU-only 环境完成；GPU 相关内容作为未来展望。

## 一、本项目硬件条件评估

### 1. 结论

按当前 README 的计划，项目并不一定需要 H100 级集群。最平衡的研发配置是：

> **16–24 核 CPU + 64–128 GB 内存 + 1 张 24–48 GB NVIDIA GPU + 2–4 TB NVMe**

其中，24 GB 显存可以完成 d=7、部分 d=9 和轻量 GNN；如果加入时序 Transformer、较大图批处理或更完整的 HGP/qLDPC 实验，建议使用 **48 GB 显存**。

### 2. 分阶段硬件建议

| 阶段 | CPU | 系统内存 | GPU 显存 | 存储 | 说明 |
|---|---:|---:|---:|---:|---|
| M0–M1：Stim、MWPM、BP+OSD 基线 | 8–12 核 | 32–64 GB | 无 GPU 也可 | 500 GB–1 TB | Stim、PyMatching、OSD 都是 CPU 负载 |
| M2–M3：GNN 边权重、混合解码 | 12–16 核 | 64 GB | 16 GB 可跑，24 GB 推荐 | 1–2 TB NVMe | d=3/5/7 较舒适，d=9 需要控制 batch |
| M4–M5：d=9、HGP、qLDPC、完整消融 | 24–32 核 | 128–256 GB | 48 GB | 4–8 TB NVMe | qLDPC/OSD 和并行评估更吃 CPU/内存 |
| 大 Transformer、多随机种子、大规模扫描 | 32–64 核 | 256–512 GB | 1–4 张 48–80 GB | 8–20 TB，必要时 100GbE | 不是起步必需，仅用于缩短扫描周期 |

### 3. 资源需求原因

- d=7、d=9 的 rotated surface code 在 circuit-level 设置下，检测器数量大约分别为 336 和 720；DEM 中会有数千到上万个 error mechanism。单个图不大，但按 batch 和边特征展开后，显存增长很快。
- Stim 数据生成主要吃 **CPU 核数**；PyMatching、BP、OSD 后处理也主要吃 **CPU 单核性能、核数和内存**。GPU 不会替代这些环节。
- GNN 训练主要吃 **GPU 显存和 batch 吞吐**。模型本身可能只有几百万到几千万参数，真正的显存瓶颈是图批量、边特征、中间激活和优化器状态。
- Transformer/时序编码器对显存更敏感。d=9 的长序列加较大 batch，16 GB 很快就会成为限制，24 GB 是实际下限，48 GB 更稳妥。
- 如果连续 syndrome 流要求真正达到微秒级或每个 QEC cycle 内完成，普通服务器 GPU 还存在 PCIe 传输、核函数启动和尾延迟问题。该目标最终更可能需要 FPGA、ASIC 或专用近存解码硬件；服务器 GPU 更适合离线训练、批量评估和算法验证。

数据存储方面也要注意：如果保存稀疏、位打包的 syndrome，1 亿 shot 的 d=9 数据量大约是个位数到十几 GB 级别；但如果每个 shot 都保存 dense float32 图特征，规模会膨胀到数百 GB 甚至更多。建议复用固定拓扑，仅动态保存 syndrome、标签和少量特征，优先在训练时生成数据。

### 4. 当前机器评估

当前机器实测为：

- CPU：Intel i5-12400，6 核 12 线程；
- 内存：16 GB；
- GPU：Intel UHD 730，无 NVIDIA/CUDA GPU；
- C、D 盘各约 25 GB 可用空间。

这个配置只适合文档工作、环境调试以及 repetition code/d=3、d=5 的小规模 CPU smoke test。它**不足以完成 M2 以后的 GNN 训练、GPU/CPU 推理对比和系统化 sweep**，主要瓶颈是 16 GB 内存、无 CUDA GPU 以及剩余磁盘空间不足。

### 5. 本机升级方向

1. 内存提升到 **64 GB**，完整项目建议 **128 GB**。
2. 增加一块 **24 GB 显存的 NVIDIA GPU**；预算允许时优先 32–48 GB。
3. 增加至少 **2 TB NVMe SSD**，最好作为独立数据盘。
4. CPU 升级到 **16 核以上**；若暂不换主机，可把 Stim/OSD 评估放到多核云 CPU 上。
5. 多 GPU 和 FPGA 暂时不要作为第一优先级，等完成单 GPU profiling、确认真正瓶颈后再采购。

## 二、不改变本机配置的云方案

### 1. 总体思路

本机不改配置，只作为 SSH/浏览器终端使用；所有数据生成、训练、解码和存储都在云上完成。推荐把“GPU 训练机”和“CPU 解码评估机”分开，因为 Stim、PyMatching、BP+OSD 主要吃 CPU 和内存，而 GNN/Transformer 训练主要吃 GPU 显存。

推荐架构：

```text
本机：浏览器 / VS Code Remote / Git / rsync
        │
        ├── 云 GPU 机：GNN、Transformer 训练和批量推理
        ├── 云 CPU 机：Stim 数据生成、MWPM、BP+OSD、LER sweep
        └── 同区域对象存储：数据集、checkpoint、日志、图表
```

### 2. 推荐云配置

| 阶段 | 云实例 | CPU/内存 | GPU | 存储 | 用途 |
|---|---|---|---|---|---|
| M0–M1 基线与数据链路 | CPU 计算型 Spot | 16–32 vCPU / 64–128 GB | 无 | 500 GB–1 TB | Stim、PyMatching、BP+OSD、小规模 LER |
| M2 MVP 训练 | 24 GB GPU 实例 | 8–16 vCPU / 32–64 GB | L4 或 A10 24 GB | 200 GB NVMe | d=3/5/7 GNN 边权重模型 |
| M3 混合解码 | 48 GB GPU 实例 | 16–32 vCPU / 64–128 GB | L40S 48 GB 或 A100 40 GB | 500 GB–1 TB NVMe | d=7/9、时序编码器、批量推理 |
| M4–M5 完整实验 | 单卡大显存 + CPU Spot | 32–64 vCPU / 128–256 GB | A100 80 GB | 2–4 TB 对象存储 | HGP/qLDPC、噪声外推、消融 |
| 大规模 Transformer 复现 | 多卡节点 | 64–96 vCPU / 512 GB+ | 4×A100/H100 80 GB | 8 TB+ | d≥11–25、多个随机种子；不是起步必需 |

### 3. 首选建议

- **MVP 首选：L4 24 GB。** 适合 d≤7 的 GNN、较小 batch 和中等规模实验，价格通常明显低于 A100。
- **完整项目首选：L40S 48 GB 或 A100 80 GB。** 对时序 Transformer、d=9 和较大的图 batch 更安全。没有必要一开始就上 H100，除非确定要做大规模 Transformer 预训练或极大的 batch sweep。
- **CPU 侧建议：32–64 vCPU、128–256 GB 内存的 Spot/抢占式实例。** 这类任务可以按 shot 分片，非常适合抢占式执行。
- 不建议把普通云盘跨公网挂载后直接训练。先把数据拉到实例本地 NVMe，再上传到对象存储，否则 I/O 会成为瓶颈。

### 4. 主要云商对应选择

- **AWS**：`g6.xlarge/2xlarge` 对应 L4 24 GB；`g6e.2xlarge/4xlarge` 对应 L40S 48 GB；更大规模用 `p4d`/`p5`。CPU 侧选 `c7i` 或 `c7g`。
- **Google Cloud**：`g2-standard-8/16` 对应 L4 24 GB；`a2-highgpu-1g` 或 `a2-ultragpu-1g` 对应 A100；H100 使用 `a3-highgpu-1g`。
- **Azure**：`NVadsA10 v5` 对应 A10 24 GB；`NC A100 v4` 对应 A100；大规模使用 `ND H100 v5`。
- **国内云**：阿里云、腾讯云、华为云选择 A10 24 GB、L20/L40S 48 GB 或 A100 80 GB 档实例。具体 SKU 会随地域变化，购买前核对 CUDA 版本、驱动支持和按量价格。
- **临时 GPU 平台**：RunPod、Lambda、Vast.ai 等可用于非敏感实验和短周期训练，但应使用容器化环境，并把 checkpoint 定期同步到对象存储。它们不适合作为不可替代的唯一数据存放位置。
- **TPU**：如果继续使用 PyTorch/PyG，不建议先切 TPU。TPU 更适合后续改用 JAX 或 PyTorch/XLA 的大规模 Transformer 路线。

### 5. 成本控制方案

1. 数据和代码全部放对象存储，例如 S3、GCS、Azure Blob 或 OSS；实例只保留 500 GB–1 TB NVMe 作为工作盘。
2. 训练机使用“按量 + 空闲自动关机”，不要长期 24 小时开机。
3. 能分片的实验优先使用 Spot/Preemptible 实例，每 10–30 分钟保存一次 checkpoint。
4. 数据生成和 BP+OSD 评估放到 CPU Spot，不要占用昂贵的 GPU 实例。
5. 所有实例放在同一地域，避免跨区域流量和 egress 费用。
6. 先按 1 张 GPU 做 profiling，确认 GPU 利用率、显存瓶颈和 OSD 时间；如果 GPU 利用率长期低于 40%，增加 GPU 数量通常没有收益。

### 6. 可直接落地的初始云方案

> 16 vCPU、64 GB 内存、1×L40S 48 GB、500 GB NVMe、2 TB 对象存储；另配 32 vCPU、128 GB 的 CPU Spot 实例做 Stim 和 OSD。训练机按需启动，CPU 实例按扫参任务启停。

这套方案可以覆盖 d=3/5/7/9 的 GNN、d=9 的时序模型、HGP 小规模实验和完整 baseline sweep。只有当后续确认要复现 d≥11–25 的大 Transformer，才需要升级到 A100/H100 80 GB 多卡。