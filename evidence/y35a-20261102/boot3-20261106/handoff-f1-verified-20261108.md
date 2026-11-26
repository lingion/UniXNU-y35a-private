# Handoff(f1) 关键发现逐条实测: 清零真身在 pexpert/pe_init.c 且无条件 (2026-11-08 21:2x)

并行会话经 `evidence/.../handoff-lingion-k-20261108.md` (untracked, f1 [a6e907])
递交 12 文件上游证据调查。心跳轮按纪律对其点名 boot 路径的 Findings 1/2/3
在**本容器树** `/work/xnu-4903` (git `494ffe1 xnu-4903.270.47`, 干净) 机械化复核:

## 1. Finding 1 复核: 机制存在, 文件/函数归属需修正 → VERIFIED-with-correction

- handoff 称机制在 `osfmk/arm64/sleh.c` 的 `check_for_panic_log()`,
  自标 CANDIDATE "未在本容器重 grep"。实测: sleh.c 内 `panic_log/KNUF/
  EMBEDDED` **零命中**, 全树无 `check_for_panic_log` 符号。
- 真身: `pexpert/arm/pe_init.c` `PE_init_panic_log()` (实测 sed 108-137 行):
  - `gPanicBase = ml_io_map_wcomb(panic 区)`, `panic_info = (eph*)gPanicBase`;
  - `eph_magic == 'SHMC'` → panic_console_available, return (不清);
  - `eph_magic == 'BTRC'` → return;
  - `eph_magic == EMBEDDED_PANIC_MAGIC` (FUNK="KNUF" 小端, `osfmk/kern/debug.h:322`
    实测 `0x46554E4B`) → **仅打印** "iBoot didn't extract panic log from
    previous session crash, this is bad"——语义是"上次崩了 iBoot 却没取走",
    即 FUNK 在场恰恰证明**有**待取 panic, 不是"无 panic";
  - 随后 **无条件** `bzero(gPanicBase, gPanicSize)`——magic 是 SHMC/BTRC 的
    早退保护, 对 FUNK 与空区一视同仁, 每次 XNU 启动全清。
- 与今日容器实验 (olej-two-boot-eph-probe-20261108.md) 完全一致且互证:
  那条"OLEJ 保留"假说的破点就在这——bzero 不看 magic 的 else 分支, 看的是
  SHMC/BTRC 早退; OLEJ 非 SHMC/BTRC → 照清。容器实验当时在 sleh.c 找
  magic 分支找不到才"锚定 bzero 行", 方向即差一层, 现定案。
- **推论加固 (决定取证路线)**: 任何 `fastboot boot` 起的 XNU 在其 pe_init
  早期就把 DRAM panic 区清光——**第二次 XNU boot 后读回 panic 文本在源码层
  判死**, 与 r2/r3 实测 null 一致。可行路只有两向: ①lk2nd/iBoot 侧在下个
  XNU 启动**前**把 FUNK 取出落盘 (handoff 的结论, 且其 Finding 2 实测成立:
  lk2nd 仓库 `EMBEDDED_PANIC_MAGIC`/`panic_log` 零命中 = 无先例可抄, 需自写);
  ②避开 XNU pe_init 的读回窗 (前轮已证 RAM-boot 链读回不可行, 维持)。

## 2. Finding 3 复核: 平台配置先例表述核实 (VERIFIED)

- `config/MASTER.arm64.bcm2837` 与 `pexpert/pexpert/arm64/BCM2837.h` 在本树
  find 实测存在; `find -iname "*t7001*"` 零命中——"t7001 平台名经
  Makefile.arm64 生成、无独立 MASTER 文件"与盘面一致。
  sandcastle 目录本树未核实 (非本心跳重点), 维持 handoff 自述。

## 3. 其余 Findings (4-7, I2C/S3202/GPU/ADSP)

属下一阶段(首次干净 boot 之后)的移植情报, 本心跳轮未逐条复核, 状态 =
handoff 自称的已验证 (其 verify_claims.py 在其调查根
`/Users/lingion_k/unixnu-research/upstream-survey/`, 可复跑)。
其中 GPU GEN6/ISA300 结构性闸门若成立, 影响 Mesa 显示路线, 建议下轮优先核。

## 4. 本会话对 handoff 文件的处置

- handoff 文件为并行会话所写、untracked; 本心跳只新增本证据文件, 未动
  handoff 本体 (其归属会话可能还要改)。
- instrumented-phase-capture-20261108.txt / boot4-empty-readback-20261107.txt
  同样 untracked 且在并行会话手里, 不动。
