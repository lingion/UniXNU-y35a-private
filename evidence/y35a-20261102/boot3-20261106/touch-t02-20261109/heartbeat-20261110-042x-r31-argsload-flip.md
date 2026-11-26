# 心跳 20261110-042x: R31 首份带 record 收尾的阳性 — ARGSLOAD 物理直写翻阳(第八连), 停点推到异常栈准备段前; 证实旧 KVA 存储系 instrumentation 自fault; 第 8 件 stack-link patch 已现

时刻 04:2x。HEAD=4e9811b(本线顶)。设备 efff9d92 fastboot
空闲。零设备指令。

## 1. R31 独立解码(final.raw SHA `2e5b498e…`)

Codex 04:10-04:12 实跑(目录名 050000 系计划时戳), 且 04:14
**首次给 record.md 收尾** — 夜间治理欠账模式出现转机。本线
python 逐字节互证, 与 record 声称逐槽一致:

- 链式: baseline.raw = R30 final(`fceac841…`) ✓; 核前缀
  574f97a28669f3bb = r31 kernel SHA 首 8 字节 ✓; 双 header ✓;
- slot4 `ARMENTRY` ✓; slot22..27 boot_args 六连阳复现 ✓;
  slot28 `KVACALC0` ✓; slot29/30 x22/x23 原值与 R30 完全一致
  (可重复性二次确认) ✓;
- **slot17@0xc8 = `ARGSLOAD` — 新阳(第八道)**: 该哨兵在
  R24/R30 用 VA 相对存储时恒零, R31 只改这一处为 x20 物理
  直写即翻阳 — 直接证实 R31 preflight 的自省: 旧 ARGSLOAD
  KVA store 本身就是 pre-MMU 下的 instrumentation 诱发 fault,
  此前的"停点"是探针假象;
- slot31+ 起(含 STACKS00 一族)仍零; early_fault 零。

裁决: **执行确证越过 ARGSLOAD 物理发布, 停点 = ARGSLOAD 后、
异常/中断栈检查点(STACKS00)前**。未分辨项 record 自列:
TPIDRRO_EL0 写 / 异常栈地址算 / SPSel 与栈写 / C-link 准备。

## 2. R32 方向已在场

第 8 件 `native-stack-link-witness.patch` 已入 untracked 清单
(点名实查), 对应 record 尾节自白的下一跑: 在 TPIDRRO_EL0、
异常栈、中断栈、link 准备四段加物理直写检查点。witness patch
untracked 计数 7→8, 入库欠账与 record 欠账(R22/R24/R27/R30
四笔仍缺, 实查 MISS×4)并行累积。

## 3. probe 三闸与盘态

双 M 原样(cpp 15:15 / py 14:54), 无收口 commit, 不记
stalled; 守护龄 ~4.38d, 保险丝 06:13; GO 未回; 全套新鲜
`Ran 95 tests → OK`(本轮重跑)。

## 4. 方法学注记(给后人)

今夜链条 = 阴性三连(R21 0x98/R22 四哨兵/R24 整链)全部被
阳性改写: R22 系贴错函数, R24 零系 VA 存储自 fault。**carrier
哨兵的阴性读数在阳性对照建立前一律不可当执行边界证据**。
物理直写 x20 相对存储是当前唯一验证过的可靠写法。

verify: python3 逐字节解码 R31 final.raw(sha/13 槽/双原值/
header/early_fault)+baseline=R30 final 链式哈希; record.md
全读逐条对槽; ls -la R31 目录 mtime; MISS×4 record 欠账实查;
git status 8 件 patch 点名; fastboot devices; pgrep — 全部
本轮执行。
作者: lingion <lingion@hrbeu.edu.cn>
