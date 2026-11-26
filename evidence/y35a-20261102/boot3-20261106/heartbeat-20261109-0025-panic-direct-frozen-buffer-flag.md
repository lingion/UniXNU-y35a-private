# 心跳旗标 00:2x (2026-11-09): panic-direct 00:17 抓取与 r6base/r6post **sha 逐字节相同**(995333535c9f2c4f)——衰减中的 DRAM 窗 12min 零翻转违反已测衰减率,"独立交叉验证通道"疑似读到同一份 host/dump buffer,数据血统待 f1 澄清

LK console 抓到 = 本轮最重大工具升级确认:bootreason=65、Booted @0x80008000、DTB 有效、
splash 在屏、fastboot oem 命令全可见。f1 dirty=18(含新 drivers/* untracked),在途大改——本会话零触碰。

## 决定性观察

| 文件 | 时刻 | sha256 前缀 | 渠道 |
|---|---|---|---|
| readback-r4-raw.bin | 23:29 | bdb2cbc200196604 | 探针 retained |
| r6-baseline-retained.raw | 00:05 | 995333535c9f2c4f | 探针 retained |
| r6-post-boot3.raw | 00:07 | **995333535c9f2c4f**(同上) | 探针 retained |
| panic-direct-20261109-0017.raw | 00:17 | **995333535c9f2c4f**(同上) | "直抓"独立通道 |

1. 00:05→00:17 物理窗 12 分钟 **0 bit 翻转**。对照本盘自己的实测:r4→r6base 36min 翻 163bit,
   28min 翻 312bit(§10.9/10.12 两轮一致,饱和曲线)。12min 期望 ~40-130bit,实测 0。
   **正常物理衰减下几乎不可能**——除非 (a) 该窗保留突然完美(无先例),或 (b) 后两张不是
   独立新鲜抓取(同 dump 复制/host 缓存未刷新)。
2. 若 (b) 成立:"panic 直抓 = 独立交叉验证"的证词力打折——r6post==r6base 的"boot3 零写入"
   结论(f8d9829)同样降级为"两次抓取同一缓冲,未证零写入"。**f1 用 00:17 文件裁决候选 (a)/(c) 前必读此条**。
3. 反向对照:00:17 vs panic-direct **23:04** 差 79 字节——与纯衰减同型(23:04 文件确实是旧内容,
   在继续翻)。即 23:04 直抓是"新鲜但衰减中"的真抓取,而 00:17 直抓读到的是 00:05 的冻结内容。
   两通道行为差别的机制待定(oem log 与 oem y35a upload 共享 staging buffer?)。

## 给 f1 的最小复验(一条命令级)

重跑一次 panic-direct 并**立即**与 r6 文件 diff:若再次 0 差异且时间跨度 >5min,直抓通道
判定为缓存假象;若出现与 r4→r6 同型的散点衰减,则 00:17 恰好是保留完美的幸运样本(接受)。
LK console 的时间戳可辅助判定 dump 是否真的发生(00:17 抓取应出现在 console log 里,
lk-console-2.raw 只记到 81230ms 的 oem log,没有 panic-direct 条目——也指向"00:17 未重新 dump")。

verify: 三文件 sha256 直比全等;00:17↔23:04 79 字节散点(衰减型);00:17↔r6base 逐字节零差;
lk-console 两版 diff(第二版无 upload 记录)。全程只读。
