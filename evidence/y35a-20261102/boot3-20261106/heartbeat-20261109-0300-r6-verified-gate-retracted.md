# 心跳 20261109-0300: r6 候选本轮独立核验 GREEN + 02:00 轮错误论据正式回撤 (只读)

时刻: 2026-11-09 03:0x CST。分支 fix/readback-panic-globals @ 84cf481,
工作区 22 处在途 (builder/package/patch 系并行件, 本会话未碰, 未 commit)。
无 fastboot 进程; ioreg "Android" 条目 = idVendor 6353 ( webcam 系, 非
Qualcomm 05c6) → 设备不在 fastboot 模式, RAM boot 轮直接跳过 (无争用
风险, 也无对象)。linked sessions 2 个 running 均与 Y35A 无关。
定时件: 心跳 20min 出现双份 (12362354 持久 + 483afcf9 session-only) —
疑似重复唤醒, 待用户裁决是否撤一。

## 1. r6 候选 = 本轮新鲜实测 GREEN (不采信 README-r6 记录, 全部重跑)

- tests/test_readback_names.py: 15/15 OK (本轮运行, 0.301s)。
- entry.S 字节等式: 用 HEAD 生成器 + manifest 自带 15 records 重新生成,
  与盘上 out/y35a/readback-probe-20261109-r6/entry.S 全等 (True)。
- 镜像完整性: 盘上 .img sha256 = manifest image_sha256 (8407f821…) = 真。
- kernel_sha256 三方一致: manifest = 盘上 ios12-kernel.noctf (5fd4e6b5…)。
- REQUIRED 载核 (debug_buf 三元组 + gPanicBase/Size + debugger_panic_str +
  panicDebugging) 全部在该内核符号表解析成功。
- 发射 Assembly 含: cmp x0,x3 / cmp x1,x5 / sub x6,x1,x0 / mov w6,#0x1000
  / csel 双限 / copy_bytes: 逐字节拷贝循环 — 读 debug_buf 有界拷贝真实存在。
- 定序: r6 = 新序 (set_table 后置, panic 正文先拷) — 修自我覆盖的 aa0fec9
  已生效; 旧 r3 (19:04) 仍是 table-first 旧序, 已被 r6 取代, 勿再上机。

## 2. 本轮纠错两条 (对自己既往笔迹)

- 02:00 笔记 §1 "消费点不存在/路径无效" 系误判: MakeInc.rule:301 C_RULE_1A
  展开 ${$@_CFLAGS_ADD}, 与 Apple lz4.o_CFLAGS_ADD 同机制; build.log
  grep=0 是无效观察 (日志不回显 make 命令行, BUILD_LTO 等同样 0)。
- 00:27 "定罪件" 的 nm 计数 0 命中实为 "file format not recognized" (Mach-O
  arm64 对象必须 llvm-nm), 错误被 grep -c 吞掉 → 该证据作废。用 llvm-nm +
  LE64 字面量双模式重扫 arm_init.o/locore.o/start.o/kernel-packed.macho
  (6e9a09d2): 全部 0 命中, 且对照组 panic 字符串 350 命中 (方法有效)
  → 插桩确未编译, r6 笔记 "phase-markers-never-compiled" 结论维持并加固;
  根因候选回到 builder 宏传递/时序, 与 02:47 诊断 (locore/start 走
  S_RULE_1A 只吃 _SFLAGS_ADD, builder 从未传 → 汇编侧 guard 恒假) 一致。
  builder 当前 diff 仍只有 arm_init.o_CFLAGS_ADD 一行, SFLAGS_ADD 缺失 =
  持久缺陷, 重建前必须先修, 否则再烧一次 RAM-boot 取证窗。

## 3. 事务窗与下一步 (需用户)

- r6 静态核验已闭环, 它是合格候选; 但 "有文本无头" 的最终裁决件应是
  带真插桩的内核, 而插桩修复在 builder 侧 (并行件在途) → 顺序闸:
  builder 去 guard 或补 *_o_SFLAGS_ADD → 增量重建 → llvm-nm+LE64 双扫描
  过闸 (0→非0) → 重打包 → 申请 RAM boot。任何颠倒 = 烧窗。
- 本轮未碰设备、未写分区、未 commit/push、未访问 userdata。

verify: 命令记录见本会话 Bash — pytest 15/15、regen diff True、shasum
对照、llvm-nm/LE64 扫描含对照组、ioreg/pgrep 快照、git status 22。
