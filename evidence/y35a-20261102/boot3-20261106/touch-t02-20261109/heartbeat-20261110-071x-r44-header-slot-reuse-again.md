# 心跳 20261110-071x: R44 方向落件 — header 段双哨兵 HDRLOAD0/HDRADJ00, 但写点 [x20,#0x970]/#0x978 = 复用 loop-state slot46/47, R43 record 自定的分槽承诺在新件上未见兑现; 观察登记两解释待实测分辨

时刻 07:1x。HEAD=0082f29(本线顶)。设备 efff9d92 fastboot
空闲,无构建/烧写进程(07:15 实拍)。零设备指令。

## 1. R44 输入可读(第 13 件 patch, 07:08)

`native-header-adjust-witness.patch` 三处哨兵全物理直写:
start.s 794 行(Mach-O header adrp/add 后)`HDRLOAD0` →
`[x20,#0x970]`; 814 行(phys/virt base adjust 后)`HDRADJ00`
→ `[x20,#0x978]`; 846 行(L1 表指针/空闲游标准备后)
`L1ALLOC0` → **再次** `[x20,#0x970]`(同 patch 内自复用,
HDRLOAD0 会被 L1ALLOC0 覆盖)。方向 = 在 R43 "先于清洁 V=P
mapping return" 边界的**下游** header/L1 分配段补哨兵。
start.s 行序(实测 hunk): 失效循环(571-575) < header 段
(794/814) < L1ALLOC(846) — 即 R44 若 slot46/47 出文字,
等于证明执行已**越过失效循环**到 header/L1 段。

**字节级预登记(解码防漏)**: python 逐字节重算 mov/movk
立即数 — HDRLOAD0 的 word2 写的是 0x4f41('A','O'),
运行时字节串实为 **`HDRLAOD0`**(注释名 O/A 换位, 非
`HDRLOAD0`); HDRADJ00 与 L1ALLOC0 重算均与注释名一致。
R44 解码时 grep 字面 HDRLOAD0 必假阴, 须按实际字节
HDRLAOD0 或全 ASCII 槽扫。登记不代改(patch 所有权 Codex)。

## 2. 槽复用再犯观察(064x 预言链的续篇)

**三处新哨兵写点全落在 `[x20,#0x970]`/`[x20,#0x978]`** — 与
loop-state patch(mtime 05:45 未再触线, 仍写此两点)的
x2/cursor 数值目击槽**同址**。R43 record 尾节白纸黑字:
"allocate distinct carrier slots … and remove the loop-state
slot reuse, then rebuild … before any further device run" —
新件未见兑现分槽(也可能是"先做 header 段, 分槽在后续件",
无法从单 patch 断定)。

两解释待 R44 final.raw 实测分辨:
① 有意改派(循环后槽位让给终程哨兵, x2/cursor 数值目击
   牺牲): 若 slot46/47 = HDR 文字 → 执行过 header 段, 循环
   完成实锤, 停点大推进;
② 撞车疏漏: 若 R44 仍停循环前, slot46/47 应回到零(映射/
   header 都没到)或仍数值(loop 到了、header 没到) — 三种
   读数各有判据, 解码时逐一对。

本线不代改(所有权 Codex), 登记为 064x→066x→068x→071x
第四笔同址观察, 若 R44 实测支持解释 ② 则升格报回项。

## 3. 治理与盘态

record 欠账 17 笔不变(R44 未跑); LOG 仍 M; 13 件
witness/loop-state/args-physical 类 patch 全 untracked
(计数实查); probe 三闸零漂移(cpp 15:15/py 14:54); 全套
`Ran 96 OK`(06:41 实测, 本轮无 tests 触线不重跑); 守护龄
~4.49d, 保险丝本轮同至(见 recap)。GO 未回。

verify: head -30 实读新 patch(HDRLOAD0/HDRADJ00 字符串与
[x20,#0x970]/#0x978 写点逐行); grep -c str.x20 物理写法计数; loop-state patch
mtime 05:45 + 写点 grep 对照; mapping/startup patch hunk
行号 grep -E "^@@" 实测校行序; ls -lat patches/out/evidence
三目录最新态实拍; git status 13 件计数实查; LOG=M 实查;
fastboot devices; pgrep 空 — 全部本轮执行。
作者: lingion <lingion@hrbeu.edu.cn>
