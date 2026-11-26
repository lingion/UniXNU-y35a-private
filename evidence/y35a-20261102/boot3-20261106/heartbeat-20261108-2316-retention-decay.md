# 心跳交叉验证 23:16 (2026-11-08): f1 的 panic-direct 揭示 retained DRAM 在无断电下实时自衰减——取证窗比 f1 README 设想的更窄, 且 classify() 对衰减敏感

设备仍归 f1 会话 (fastboot efff9d92; `panic-direct-20261108.raw` 23:04 落盘, 12 分钟前)。
本会话零设备接触、零写盘 (规则①: 不抢 f1 的在途 boot4-r3), 仅对 f1 已落盘的三份读回快照
做只读交叉核对, 得出一条 f1 自己的 README 未点到的结论。

## 三份同一 retained-DRAM 快照的时间序列

| 文件 | 落盘 | 头 8 字节 (marker) | 非零字节 |
|---|---|---|---|
| readback-raw.bin (r3) | 21:53 | (见 f1 README) | 5124 |
| readback-r4-raw.bin (r4) | 22:36 | `Y35ARD01` (干净) | 5200 |
| panic-direct-20261108.raw (direct) | 23:04 | `Y31ARD 1` (烂) | 5045 |

## 关键测量: r4 → direct 是"纯衰减"——只丢 1-bit, 无一个 bit 被新写入

- **方向分解 (全 69632 字节)**: r4 相对 direct 独有 312 个置位 bit; direct 相对 r4 独有 **0 个**。
  即 22:36→23:04 这 28 分钟内, retained DRAM **单调 1→0 流失 312 bit, 无任何探针/boot 写入**。
- **marker 自己烂了**: `Y35ARD01` 的 7 个差异字节逐个验证均为纯掉 bit
  (byte2 `0x35→0x31` 丢 bit2、byte6 `0x30→0x20` 丢 bit4、byte8 `0x5f→0x5e` 丢 bit0、
  byte10 `0xe6→0xa6` 丢 bit6、byte11 `0xb5→0xb4` 丢 bit0、byte12 `0xf7→0xd7` 丢 bit5)。
  若是"重跑探针的新一份", header 会被重写为干净 `Y35ARD01` (应 0 掉 bit + 有新增)——
  实测相反, 故 direct **不是新 boot, 是同一份 retained 内存被更晚读出、进一步衰减**。
- **丢失位号 0..7 分布均匀** (57/46/30/31/44/30/37/37), 非某条坏列/坏行, 符合位独立随机流失。
- **数据却稳**: `Y35AXNU2` handoff 头 `0x10000..0x10020` 两份**字节完全相同**, entry 恒为
  `0x00000000a026e0a0`。丢的 12 个正文字节全在 `0x101f5` 之后 (正文残留区), 结构头恰没摊上。

r3→r4 则**非纯衰减** (r4 有 47 个 bit 是 r3 没有的): 与 f1 README 定性一致——22:36 前后那次
USB 物理拔插冷复位, 清掉了 649 bit 旧 panic 数据、并由新探针 boot 写回 47 bit (干净 marker 头)。
即"冷复位后 r4 是最新基线, 此后只随时间衰减"。

## 结论一: 取证窗比 f1 README 设想的更窄 (补强, 非推翻)

f1 README 下一轮序列写"必须同一次上电周期内完成, 中途禁 USB 断电"。本轮数据说明这**必要但不充分**:
**即便全程不断电, panic 区也在从 halt 那一刻起自衰减** (28 分钟即 312 bit)。debug_buf 本就只剩
~5045 非零字节的"残留", 每多等一轮 readback 就更空。故要求应收紧为:
> 同一上电周期内 **且 halt 后尽可能首次** readback——间隔越短, panic log 保真越高。
不臆测衰减机理 (DRAM 保持/refresh、探针 stage 复用皆可解释), 只锁死"单调、无需断电即发生"这一观测。

## 结论二: classify() 对衰减敏感, 可被翻转 kind (给 f1 工具留一句)

`scripts/y35a/capture_format.py:classify` 先测 `head8==Y35ARD01` 再测 `body[0x10000:8]==Y35AXNU2`。
direct 里第一个 magic 已烂 (掉进下一分支)、第二个 magic 因所在 bit 未衰而幸存 →
`classify(panic-direct)= {kind:Y35AXNU2, entry:0xa026e0a0}`, 而 `classify(r4)=Y35ARD01`。
同一份物理内存, 因哪个 magic 先腐烂而返回不同 kind。**判据 (entry/字段值) 本身稳, 别把 kind 翻转
当"内容变了"读**; 若后续要防误判, 可在 classify 里对 magic 位衰减加容差 (非本轮任务, 仅记录)。

## 本会话状态

GPU (a3xx) 线维持等待 f1 的 phase-marker 阶段链。cron 提示的 QcomTouch T2.1→NativeTouch→实机 V 段
需**驱动设备**, 与 f1 在途 boot4-r3 冲突 → 本会话不启动 (规则①)。本轮只做不冲突的只读交叉分析。

verify: 三快照 od 直读; 方向分解 (312 丢/0 增)、逐 marker 字节位掩码、`Y35AXNU2` 头 `pd[h]==r4[h]==True`、
entry 两份相等、classify() 走 capture_format.py 本体 (sys.path 注入后直接调用) 实测 kind 翻转——
全为读 f1 已落盘文件, 无设备写, 无动 f1 工作树 (7 dirty 原样)。
