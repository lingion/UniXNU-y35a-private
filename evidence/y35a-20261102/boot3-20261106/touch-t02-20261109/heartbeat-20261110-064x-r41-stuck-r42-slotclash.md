# 心跳 20261110-064x: R41 三代全同观测集(停点锁死 = 失效循环最后条目, x2=1 光标 0xa3483ff8); R42 输入现: mapping patch 06:21 物理化改造(0x8a0/0x8a8 VA→物理), 但复用 loop-state 数值槽 0x970/0x978 — 覆盖冲突观察登记; record 欠账 10 笔

时刻 06:4x。HEAD=ea40824(本线顶)。设备 efff9d92 fastboot
空闲,06:24 实拍无构建/烧写进程(Codex 停手写 record 或筹备
R42 间隙)。零设备指令。

## 1. R41 终态独立解码(兑现上轮承诺)

R41 完成于 06:15-06:16。final.raw SHA `cdf3cd758fe42d25…`,
链式 baseline = R40 final(`ccf37747…`) ✓, 核前缀
490ec055bc542028。**观测集与 R39、R40 逐槽完全相同**: 25
文字哨兵 + x2=1 + 光标 0xa3483ff8 + slot49, 零槽计数两代
机器比对相同(grep -c 差集空)。**停点"失效循环最后一条目
处理点"现已跨三代镜像锁死**, INVALID0 完成哨兵三连不达。

## 2. R42 输入可读 + 一个槽位复用观察(登记不代改)

`patches/xnu/native-mapping-witness.patch`(06:21, 第 12 件)
内容 = 把映射段旧 VA 写法 `[x14,#0x8a0]/[x14,#0x8a8]` 改
`[x20,#0x8a0]/[x20,#0x8a8]` 物理直写(052x 几何: 恒差 0x7c0
→ slot 0xe0/0xe8 区), 即 R24 时代 VA 伪零链的映射段补修,
方向正确。

**观察**: 该 patch 同时多处写 `[x20,#0x970]` 与
`[x20,#0x978]` — 而这两点正是 loop-state patch 的 x2/x1
数值目击槽(slot46/47)。若 R42 同批应用两 patch, 文字哨兵
会覆盖循环状态数值(或反序覆盖)。可能系有意复用(loop 完成
后槽位改作映射标记), 也可能撞车。**归 Codex 判断, 本线登记
待 R42 final.raw 实测裁决**: 看 slot46/47 届时是数值还是
文字, 谁赢即最后 apply 者。

## 3. 治理与盘态

- record 欠账 **16 笔**(逐代全量清点, carrier 实跑目录共 21:
  缺 record 的 16 = 旧夜 r12/r13/r14e/r15/r17/r19/r20 七笔 +
  昨夜今晨 r22/r24/r27/r30/r34/r38/r39/r40/r41 九笔; 已收 5
  = r16/r18/r21/r31/r33); LOG 六代回写仍 M;
  十二件 witness/loop-state/args-physical 类 patch 全
  untracked — **实跑已 10 代, 官方记录零入库推进**, 不可
  再生风险按代累积, 本线证据链(11 份)仍是唯一全程;
- probe 三闸零漂移(双 M 15:14/14:54 不变); 全套新鲜
  `Ran 96 OK`; 守护龄 ~4.47d; GO 未回。

## 4. 下轮盯点

R42 实跑(映射段翻阳?)与 slot46/47 裁决; record/LOG 是否
集中补库; Codex 若长歇, 观察其会话是否仍活(桌面会话名单)。

verify: python3 逐字节解码 R41 final.raw 64 槽全枚举(sha/
链式 baseline=R40 final/双 header); R40/R41 decoded 零槽计数
grep -c 差集机器比对; ls -lat patches/mapping 06:21 实拍;
patch 写点 0x8a0/0x8a8/0x970/0x978 全行实读; record MISS×4
新代实查+历史清点; LOG=M 实查; unittest discover 新鲜
(Ran 96 OK); pgrep 无进程; fastboot devices — 全部本轮执行。
作者: lingion <lingion@hrbeu.edu.cn>
