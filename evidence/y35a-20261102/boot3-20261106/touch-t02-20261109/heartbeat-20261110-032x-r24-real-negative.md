# 心跳 20261110-032x: R22 全零根因 = 哨兵贴错函数(secondary start_cpu); R24 已在 _start_first_cpu 重打十哨兵并实跑, 独立解码仍仅 ARMENTRY — 首个真可信负观测: 停点 = ARMENTRY 后、ARGSLOAD 前

时刻 03:2x。HEAD=4649040(本线顶)。设备 efff9d92 fastboot
空闲。零设备指令。

## 1. 框架性更正(本轮最重要)

R24 preflight 自白: **R22 的 witness patch 打在了 secondary-
CPU 的 start_cpu 路径, 不在 _start_first_cpu** — 故 R22 四哨
兵全零"证伪 MMU 激活说"的结论作废, R21 的 0x98/0xa0 零同样
可疑(哨兵可能根本不在执行路径上)。此前数轮"停点逐段收窄"
解读全部要按此根因打折: 全零分不清"没执行到" vs "没贴对"。

R23 不存在(R22→R24 直接重做)。R24 = 十哨兵在 _start_first_cpu
上下文重打: ARGSLOAD→STACKS00→INVALID0→VPMAP000→KVAMAP00→
MAPDONE0→COMMON00→TTBRDONE→PREMMU00→MMUON000→ARMRET00。

## 2. R24 实跑独立复核(02:50-02:54, decoded 未转述)

`phase-r24-carrier-20261110-025028/` 十件齐。python 逐字节解
码 final.raw(SHA `4a9b31fd20ae3386…`):

- slot4 0x60 = `ARMENTRY` ✓;
- **slot5..slot17(0x68..0xc8)全零 = ARGSLOAD 至 ARMRET00 整
  条新哨兵链无一命中**(preflight 期望序 11 名共享槽位, 故按
  槽实测不点名计数); slot18@0xd0 亦零(Codex decoded 实查);
- early_fault@0x3c0 = 0;
- header `Y35AXNU2` + 核前缀 e43e202d4259742b = r24 kernel
  SHA 首 8 字节 ✓; `Y35ARD02` ✓;
- baseline.raw 哈希恰 = R22 final(`1408bb24…`)链式衔接 ✓;
- changed_ranges 仅 CNTVCT 见证 12 字节 — 干净;
- 与 Codex decoded-fields.txt slot_4..slot_18 逐条互证一致。

裁决: **R24 是贴对函数后首个真可信负观测。XNU 执行确认止于
ARMENTRY 写入之后、ARGSLOAD(boot_args 参数装载完成点)之前**。
区间比 R22 旧结论更早。落点抽查: native-startup-witness.patch
hunk 落 start.s 476..644 区间(ARGSLOAD/STACKS00 注释实证在
patch 内), "确在 _start_first_cpu 体内"系 Codex digest 闸声称,
本线暂按板信任, 留反汇编终证项。

## 3. 治理与三闸

- witness patch 仍 5 件全 untracked(R24 构建输入不可再生风险
  持续, 030x 登记的续篇);
- R22/R24 record.md 均未收, Codex 冲刺实跑中(02:25 R22→
  02:50 R24), 收尾欠账在积;
- probe 双 M 原样(cpp 15:15/py 14:54), contract 无新触线,
  全套新鲜 `Ran 95 OK`; 不记 stalled。

## 4. 盘态

守护龄 ~4.32d; 保险丝 06:13 在位; GO 未回; 本线待办不变:
①盯 R24 record/LOG 回写与五 patch 入库; ②盯 probe 收口;
③设备事件瞬空先查他线实跑目录再裁决(015x 纪律)。

verify: ls -dt 全 phase-r2x 目录实查(R23 不存在确认); R24
preflight/decoded-fields 全读; python3 逐字节解码 final.raw
18 槽+header+0x3c0; baseline 哈希对照 R22 final; grep patch
落点实证; unittest discover 新鲜(Ran 95 OK); fastboot
devices; pgrep — 全部本轮执行。
作者: lingion <lingion@hrbeu.edu.cn>
