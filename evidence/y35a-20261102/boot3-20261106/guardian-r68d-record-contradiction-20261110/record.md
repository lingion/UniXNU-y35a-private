# 守护 18:2x — r68d record 与实物互斥: "包已清零 512B carrier" 声明被零差分证伪

## 实测(全部新鲜, 本轮复核)
- `phase-r68d-carrier-20261110/record.md`:26 声明 package 在 branch 进核前清零 `args_pa+0x800` 的 512 字节诊断 carrier(= min 布局 body 0x10100..0x10300)。
- 守护 18:0x 已测(见 guardian-r68d-independent-decode-20261110/): final-vs-baseline 全 raw 差异仅 13 字节(0x10008-0x1000f 戳 + 0x10050-0x10054 CNTVCT); carrier 窗内 PREMMU00/ARGSLOAD/LINKADDR/slot22-37 残值/slot49 等与 baseline 逐字节同。本轮已复跑确认差异字节集不变。

## 三值互斥推理
1. 若清零生效且核未达 slot17/22-49(record 边界判定): 这些槽 final 应为零 ≠ baseline 非零 → 必现大量差异。**未现。**
2. 若清零生效且核到达并重写 slot49(:877 header-adjust): r68d text 布局与 r68c 不同, 写值必变 → slot49 应现差异。**未现。**
3. 唯一与观测一致: **清零写到了别处(或包实际件与声明不符)** → carrier 全程未被清, 残值原样; 核的 marker store 同理可能也落在别处。

## 影响
- record 第 49 行边界"after pre-SCTLR checkpoint, before first post-MSR checkpoint"建立在"carrier 干净所以零=未达"前提上; 前提被证伪后, 全部"Readable zero"降级为"该窗口零, 不可区分未执行与落错址"。PREMMU00 "present"同理不能区分本轮写与 r68c 留存(两代同值)。
- 守护上轮候选(b)"x20/args_pa 地址形成错"从"未排除"升为**有独立阳性证据**; record 第 57 行下一代计划(x16 原始值/post-transform 值入 slot58-60)正命中, 建议把**boot3 清零指令的基址来源**一并纳入同一实验(它和核内 store 若共享同一形成式, 一条 CANARY 双杀)。

## 建议(归 Codex 拍板)
record 追加勘误段(不改原文); 实验顺序: 先 LK 侧独立读回 args_pa+0x800 头 16B 与核内 CANARY 对照, 再谈任何"未达"边界。
