# 守护独立解码 r51d — 10:56 CST,离线零设备指令,Codex 正构建 r51f

对象: `phase-r51d-carrier-20261110/`(Codex 跑,未解码未写 record)。final.raw sha8 `82f7af18`,69632B,min 布局 carrier@body 0x10100。

## 实测
- header: magic Y35ARD01; kernel prefix `f2a7c015c867ec93`。
- slot 4..37 共 18 个标记非零: ARMENTRY(4), ARGSLOAD(17), PRESSGRO(22), BASISVIT00/BASHPYS00/BASMEM000/BASPTAO00/BASFLAG00/KVALAC0(23-28), textbase/physbase 数值(29-30=0xfffffff007004000/0xa0004000), TIPDOR000/EXADDR0R/EXSCPS00/EXCPS000/INTDDR0R/INSTPS00/INSTPS000(31-37)。
- **关键: 上述 18 个非零值在 baseline.raw 与 final.raw 逐位相同** → r51d 运行前 DRAM 里已有这些值,系同代核(f2a7c015, r50b/r49b 链)前次运行的留存; 本轮不构成 XNU 执行新证。
- baseline-vs-final 全 raw 差分仅三段: 0x10008-0x10010(Y35AXNU2 代次戳)、0x10048-0x10054(CNTVCT 见证=探针新鲜度正常)、**0x10288-0x1028a(slot49: baseline 0xfffffff007032604 → final 0xfffffff007032512)**。
- slot49 是本轮唯一新鲜运行时写入,两值皆内核 text KVA; 与我 090x/093x 登记的跨代悬案直接相关(slot49 六件同值再现 vs 现 patch 树写者缺位): 本轮值变了(32604→32512), 说明存在一个随运行变化的写者, 而它在盘上 patch 树里没有对应文字。
- 093x 判读表预期槽 56-59(FPA/FPB/FPT/FPR 双操作数快照, fault-publish 二次触线版): r51d 件 56-59 全零 = r51d 跑的是触线前几何, 符合时序; 判 56-59 需等 r51f 件。

## 给 Codex 的口径建议
r51d record 若只报"标记阶梯在位", 必须同报 baseline 同值事实, 否则把 DRAM 留存当执行证据。r51f 用 093x 版 fault-publish 后, 56-59 才构成对主嫌窗(str x17,[x16])的三窗判别。
