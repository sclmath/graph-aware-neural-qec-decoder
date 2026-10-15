# T18 · Union-Find 解码器的失效分析与修复

- **日期**：2026-10-15
- **状态**：**部分完成**。peeling 已补齐、correction 的 syndrome 一致性已恢复；**LER 仍未达 MWPM 量级**，因此报告口径下 Union-Find 的表面码数字仍不可用于与 MWPM 并列。
- **代码**：`src/graph_qec/decoders/union_find.py`
- **测试**：`tests/test_union_find_t18.py`（5 项）
- **相关决策**：`docs/ROADMAP_TODO.md` 6.1 节（2026-10-15 定案「修实现，不降级」）

---

## 1. 原始缺陷（已确认）

旧实现把**每一个发生合并的边的 `fault_mask` 直接累加**，缺少 peeling 步骤。

后果不是「精度略差」，而是**协议级错误**：产出的 correction 不满足 syndrome 约束。用 `matching_dem` 重建 check matrix 后可定量验证——在表面码 d=3 码容量 p=0.01、2000 shots 中，468 个含缺陷的 shot 里 **456 个（97%）** 的 correction 违反 `H·c = s`。

因此 `results/m4/surface_sweep.json` 里的 `union_find` 列（d=3 码容量 0.06311、d=5 0.226-0.476）不是「弱基线」，而是**无效输出**。

## 2. 已修复：改用 T-join peeling

生长阶段（按权重升序 Kruskal，仅当至少一侧簇为 odd 时合并）保持不变；**peeling 阶段重写**为在生长出的生成森林上求最小 T-join：

- 对每个簇的生成树任取根，做一次自底向上的子树奇偶扫描；
- 边被选入 correction 当且仅当其子树包含**奇数个终端**；
- 终端集合＝该簇内的缺陷；当簇内缺陷数为奇数时把 boundary 节点并入终端集合。

这一形式与原实现「剥除非缺陷叶子」的朴素做法**不等价**，后者会留下度为偶数、因而不在边界中的缺陷。测试 `test_union_find_peeled_correction_reproduces_the_syndrome` 在 3 个配置上逐 shot 断言 `H·c = s`。

### 2.1 修复前后（同机、CPU-only）

| 配置 | shots | 修复前 LER | 修复后 LER | MWPM LER |
|---|---:|---:|---:|---:|
| repetition d=3，电路级 p=0.01 | 4096 | 0.01294 | 0.01294 | 0.00952 |
| repetition d=5，电路级 p=0.01 | 4096 | 0.01880 | 0.01880 | 0.00122 |
| 表面码 d=3，码容量 p=0.01 | 8192 | 0.06738 | **0.05420** | 0.00281 |
| 表面码 d=5，码容量 p=0.01 | 4096 | 0.21924 | **0.01172** | 0.00024 |
| 表面码 d=3，电路级 p=0.005 | 4096 | 0.12085 | **0.07202** | 0.01831 |

修复是**严格改进**（没有一项变差），并且恢复了 syndrome 一致性。但表面码上仍比 MWPM 差 **9-50×**，距离「同量级」的验收标准还差很远。

## 3. 残余差距的根因：greedy growth 的「边界短视」

差距不来自 peeling（peeling 现在是最优的），而来自生长阶段的策略。最小反例（repetition d=5 码容量，所有机制概率相同 0.0333，故权重全相等）：

- 图：若干条 4 节点链共享**同一个** boundary 节点 `B`；链内边权重均等；
- syndrome = `{12, 14}`，两者同处一条链 `12-13-14-15`（`12` 与 `15` 各连一条 boundary 边）；
- **最优 correction**：`{12-13, 13-14}`（2 条边，逻辑翻转 0，与真值一致）；
- **greedy 结果**：`12` 在自己的 boundary 边（权重相等、下标更靠前）上被立刻「终止」，于是 `12-13` 被 "两侧皆 even" 规则跳过；`14` 只能绕到 `15` 再进 boundary，得到 `{12-B, 13-14, 14-15, 15-B}`（4 条边，逻辑翻转 1）——**既更重又翻转了逻辑**。

即：一个缺陷一旦碰到 boundary 就被判定为 even 并停止生长，而**权重相同的链内边因此永远没机会进入候选集**。MWPM 因为解全局匹配而不受影响。

## 4. 已实测的其它变体（均未达标，供后续接手参考）

| 变体 | 思路 | 结果 |
|---|---|---|
| A（当前） | 边界使簇 even，parity 归零；Kruskal 森林 + T-join | 表中「修复后」 |
| B | 保留真实缺陷 parity 参与合并判据 | repetition 码容量变差（0.0308），表面码无改善 |
| B+界边延后 | 等权重时 boundary 边排后 | 有改善但表面码仍差 9-30× |
| C | 无条件 Kruskal（含 even-even 合并）+ T-join | 显著变差（表面码 d=5 0.145）——T-join 只在「为目标生长出来的树」上才是好近似 |
| 半径生长 + toggling peel | 按 `reach = min(dist(u),dist(v)) + w` 生长，保留全部生成长边 ε'，用「带 syndrome 翻转的 erasure peeling」 | 仍未达标，大量 shot 的残余 syndrome 非空（ε' 含环，peeling 无法归约） |
| 合并平行边 | 把同一 `(u,v)` 的多个机制合并（pymatching 的做法） | 边长与 pymatching 一致（表面码 d=3 均为 35），部分配置改善、部分变差，非决定性 |

## 5. 距离「忠实实现」还差什么

Delfosse–Nickerson 的加权版本要求：

1. **ε' 是生长区域内的全部边**（"add full edges that are in the grown clusters"），而不只是触发生成的边；
2. peeling 用的是 **erasure peeling decoder（带 syndrome 翻转）**，而不是在生成森林上求 T-join；
3. 「half-edge」生长需要**按半径分步**推进（每半步检查一次簇的 even 性），使簇在被边界终止前有机会与其它缺陷簇前沿相遇。

这三条需要一起实现才有意义；单独改动任何一条（如上表）都不能收敛。工作量评估见 `docs/ROADMAP_TODO.md`（8-12 人日），本次窗口内未能完成。

## 6. 结论与建议

- **已完成且可交付**：peeling 补齐 + syndrome 一致性测试 + 修复前后对照。这是对旧实现**正确性**的修复，不是性能调优。
- **未完成**：Union-Find 的表面码 LER 仍不可与 MWPM 并列；`results/m4/surface_sweep.json` 的 `union_find` 列必须在报告中显式标注为「启发式、非可用基线」。
- **建议**（择一）：
  1. 按第 5 节实现忠实的加权 Union-Find（8-12 人日），保留 P1；
  2. 把 Union-Find 的适用范围限定为 repetition code（与 2026-10-15 的「不降级」决策相反，需要重新决策）；
  3. 用「贪心匹配」等可验证有效的近似解码器替换该基线。
