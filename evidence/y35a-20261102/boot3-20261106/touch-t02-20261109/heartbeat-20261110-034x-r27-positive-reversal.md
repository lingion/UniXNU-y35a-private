# 心跳 20261110-034x: R27 阳性翻案 — PREARGS0+五道 boot_args 逐载哨兵全命中, XNU 执行确证越过全部 boot_args 装载; 032x 的 ARGSLOAD 前停点结论作废; 第六件 kva-calc patch 03:43 在写(R28 预备)

时刻 03:4x。HEAD=6f9ee9b(本线顶)。设备 efff9d92 fastboot
空闲,无进程。零设备指令。

## 1. R27 实跑与独立解码(阳性 — 本轮最重要)

Codex 03:23 构建、03:24-03:26 实跑 `phase-r27-carrier-20261110-
033000/`(目录名 033000 系计划时戳, 文件实证 03:24-03:26;
R25/R26 编号被跳过, 无对应 evidence 目录)。R27 假设: R24 的
boot_args 派生哨兵全零, 改用**直接物理 x20 相对 carrier 写**,
PREARGS0(首载前)+ BAVIRT00/BAPHYS00/BAMEM000/BATOP000/
BAFLAG00(五载各自后)。

python 逐字节解码 final.raw(SHA `aeea22b910c050d6…`):

- file 0x00 `Y35ARD01` 探针头, 0x08 核前缀 f304a7a2ce12afc4
  = r27 kernel SHA 首 8 字节 ✓;
- slot4@0x60 `ARMENTRY` ✓;
- **slot22@0xf0 PREARGS0 ✓ / slot23@0xf8 BAVIRT00 ✓ /
  slot24@0x100 BAPHYS00 ✓ / slot25@0x108 BAMEM000 ✓ /
  slot26@0x110 BATOP000 ✓ / slot27@0x118 BAFLAG00 ✓**;
- 老链 slot5..21 零(r27 镜像未带那些哨兵或另有落点问题, 归
  Codex record 解释, 本线不猜);
- early_fault 零; header `Y35AXNU2`@0x10000, `Y35ARD02`@
  0x10040 ✓; baseline.raw = R24 final(`4a9b31fd…`)链式 ✓;
- 与 Codex decoded-fields.txt slot_22..27 逐字节互证一致
  (value 十六进制对上 ASCII)。

## 2. 裁决与对 032x 的更正

**XNU 执行确证越过整个 boot_args 处理段**(KVA/物理参数/内存
顶/flags 五次装载全部完成)——032x 轮"停于 ARMENTRY 后、
ARGSLOAD 前"的结论**作废**, 根因即 032x 自己登记的警示:
"哨兵贴没贴在执行路径上"必须由阳性命中证明, 阴性不算。R27
的直接物理写法首次给出六连阳, 证明:
①carrier 物理落点方法对了; ②执行边界从 ARGSLOAD 前推到
BAFLAG00 之后。停点现在位于 BAFLAG00 之后的 pre-MMU 段
(STACKS/exception vectors/vmpmap/KVA map/TTBR/SCTLR 一族)。

## 3. 治理与盘态

- witness patch **6 件全 untracked**(第 6 件
  `native-kva-calc-witness.patch` 03:43 刚写 — R28 预备中,
  将切 KVA 计算段); R22/R24/R27 三份 record.md 均未收,
  Codex 以 ~25min/代 速度冲刺, 收尾欠账 3 笔;
- probe 双 M 原样(cpp 15:15 / py 14:54), 无收口 commit,
  不记 stalled; 全套新鲜 `Ran 95 OK`;
- 守护龄 ~4.34d; 保险丝 06:13; GO 未回。

## 4. 下轮盯点

①R28 是否实跑 + 阳性推进到哪道哨兵; ②三份 record/LOG 回写
是否补上(阴性时代结论若不回写更正, 会误导后来者 — 本文件
已先记 R27 阳性与 032x 作废链); ③6 patch 入库。

verify: ls -lat R27/out/patches 目录 mtime 实查; python3 逐
字节解码 final.raw 全槽+header+ASCII 扫槽; xxd offset 算术
复核(-o 0x40 显示 vs 绝对); decoded-fields.txt 互证; baseline
哈希对照 R24 final; git status patch 计数; unittest discover
新鲜(Ran 95 OK); fastboot devices; pgrep — 全部本轮执行。
作者: lingion <lingion@hrbeu.edu.cn>
