# 心跳 20261110-040x: R30 阳性再推进 — KVACALC0 命中且 x22/x23 原值双双非零(首个数值型目击), 停点推到 KVA 算术后; R31 方向已可读(ARGSLOAD 物理直写修正 04:01 落); 四份 record 欠收

时刻 04:0x。HEAD=fb52fdd(本线顶)。设备 efff9d92 fastboot
空闲。零设备指令。

## 1. R30 独立解码(阳性七连 + 数值目击)

Codex 03:56 构建、03:58-04:00 实跑 `phase-r30-carrier-20261110-
040000/`(R28/R29 又跳号, 无目录)。final.raw SHA
`fceac841f8c19355…` 本线 python 逐字节解:

- 链式核验: baseline.raw = R27 final(`aeea22b9…`) ✓,
  核前缀 56d7ba6ec76a255f = r30 kernel SHA 首 8 字节 ✓,
  `Y35AXNU2`/`Y35ARD02` 双 header ✓;
- R27 六连阳在 r30 镜像全部复现(PREARGS0..BAFLAG00,
  slot22..27) — 阳性可重复, 非单次噪声;
- **slot28@0x120 = `KVACALC0`(第七道阳)**;
- **slot29@0x128 = 0xfffffff007004000 = x22 原值**;
- **slot30@0x130 = 0x00000000a0004000 = x23 原值**;
- early_fault@0x3c0 零。

数值旁注(支持性观察, 非独立终证): x23 落在 boot3 线性区
已知物理段, x22 形如 XNU 核 V 段镜像基 — 与"boot_args VA/PA
对"自洽; 精确判读归 Codex record。

裁决: **执行确证越过 KVA 算术(x22/x23 计算完成且原值可
读)**, 停点从"BAFLAG00 后"推进到"KVACALC0 后、后续 KVA
carrier 存储之前"(R30 假设原话的二分)。与 decoded-fields.txt
slot_28/29/30 逐字节互证一致。

## 2. R31 方向已可读(04:01 新 patch)

第 7 件 `native-args-physical-witness.patch`(04:01)是对
startup-witness 的**修正**: ARGSLOAD 发布由 `[x14,#0x888]`
(x14=x20+x22-x23 VA 算术) 改 `[x20,#0x888]` 物理直写 —
正是 R27 六连阳验证过的写法推广到 ARGSLOAD 本身。下一跑
预期: R24 链的 VA 系零槽将逐个翻阳或定位新边界。

## 3. 治理与盘态

- record 欠账 **4 笔**(R22/R24/R27/R30 全无 record.md),
  协同 LOG 停在 R21 段 — 夜间 4 代阳性/阴性混跑不回写,
  误导风险随代际累积, 本线证据链暂为唯一全程记录;
- witness patch 7 件全 untracked(034x 6 件→7 件), R30/R31
  构建输入不可再生风险继续加深;
- probe 双 M 原样, 全套新鲜 `Ran 95 OK`; 守护龄 ~4.36d,
  保险丝 06:13; GO 未回。

verify: python3 逐字节解码 R30 final.raw(sha/8 slot/双原值/
header/early_fault)+baseline 哈希对照 R27 final; decoded-
fields.txt slot_28..30 互证实读; patch 头 diff 实读(0x888
目标改写作证); ls -dt 全 r2x/r3x 目录(R28/29 跳号实查);
record.md 四缺实查; unittest discover 新鲜(Ran 95 OK);
fastboot devices — 全部本轮执行。
作者: lingion <lingion@hrbeu.edu.cn>
