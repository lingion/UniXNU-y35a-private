# 心跳 20261109-034x: 捕获件字节恒等悖论立案 + CNTVCT 新鲜度见证落地 (91ab4a1)

时刻: 2026-11-09 03:1x-03:4x CST。分支 fix/readback-panic-globals,
HEAD 91ab4a1 (本会话 feat commit), 前继 6f9d58a (上轮笔记)。
设备窗: pgrep fastboot 空, ioreg 无 idVendor=1478 → 不在 fastboot,
本轮零设备操作 (无 USB 争用风险, 亦无 RAM boot 对象)。容器无活动 build。

## 1. 新立案: r6 三份捕获逐比特恒等 (独立 sha256 复测, 非沿用 cmp 结论)

r6-baseline-retained.raw / r6-post-boot3.raw / panic-direct-20261109-0017.raw
三者 sha256 全等 = 995333535c9f… (本轮重算)。逐 record 窗口 diff: 15/15
equal=True, 全文 0 差异字节。三份捕获跨越: 探针跑#1 → boot3 真实 34s 运行
(presence-profile GONE 16s→present@00:16:05 为运行实证) → 探针跑#2 →
不经探针的直接 stage 读。

矛盾: 探针跑#2 是在 boot3 跑完之后重新采样活 DRAM 的全局值, 却与跑#1
逐字节相同 —— 一次真 XNU 启动不可能把 _BootArgs/_panicDebugging/debug_buf
三元组/excepstack/intstack (合计 48k 活内存) 恢复成启动前原样。
候选解释 (待裁决, 本轮不定罪):
(A) 探针跑#2 从未执行 (boot3 后设备未真正再进 r6, 或 r6 起不来) →
    所谓 post 捕获 = stage 缓冲区残留复读;
(B) get_staged 通道返回 lk2nd 缓存而非活 DRAM;
(C) records 通道本身读到冻结页。
旧 README-r6 的 "boot3 未到 check_for_panic_log" 判词依赖 0017 为活读,
而活读 vs 冻结未证 → 该判词降级为假设, 与 §2 见证互锁后重审。

## 2. 裁决机制已落地: CNTVCT_EL0 新鲜度见证 (TDD RED→GREEN)

- tests/test_readback_names.py: test_probe_stamps_cntvct_freshness_witness…
  先 RED (AssertionError 'mrs x11,cntvct_el0' not found), 修生成器后 GREEN。
- readback_native.py: stage 偏移 16 (原 reserved-zero) 写 mrs x11,cntvct_el0
  的读数; CNTVCT 同电源周期单调 → 两次真执行必不同值, 复读假象恒同值。
- 首次修正是无效汇编 `str x11,[x10,16]` (缺 #), 测试当场抓住 →
  `str x11,[x10,#16]`。
- 编译门 (非仅字符串断言): r6 同 records 重生成 entry.S → clang aarch64
  真编 → entry.bin 776B (< 0x11000 stage 预算) → llvm-objdump 实证
  `80080060: mrs x11, CNTVCT_EL0` + `f900114b…` 落 [x10,#16]。
- 全套回归: test_capture_format / test_kernel_build_contract /
  test_native_pack / test_readback_names 全 OK (41→42 例)。
commit 91ab4a1 (verify 行 = 上列真实命令)。

## 3. builder/guard 并行件状态 (只读盘点)

- git diff builder 仍仅 arm_init.o_CFLAGS_ADD 一行; locore/start 所需
  *_o_SFLAGS_ADD 依旧缺失 (03:00 轮定罪未解)。
- native-phase-markers.patch 未 staged (??), 内容 grep 无 ARMVINI/PANICINI/
  CONSOLE 字面量 → 该 patch 与 phase 记录所述不匹配或半成品, 不碰。
- work src arm_init.c 无 native_phase_marker → 插桩仍不在任何内核。
- 结论: 裁决件 (真插桩 boot3) 生成路径未就绪; 本会话不越并行件, 保持等待。

## 4. 下一步 (含设备窗到达后)

1. 重打 r7 = 带见证探针 (readback_native.py HEAD 直接可出, 无需并行件)
   → 同电源周期内 r7 baseline / boot3 / r7 post 三连: offset 16 若 post≠
   baseline → 捕获链活 (解释 A/B/C 全灭, 重启 §1 悖论分析); 若 post==
   baseline 且值非零 → 探针未再执行, 定罪通道; 若恒 0 → stage 从未写过。
2. 并行件落地 builder 修复后: 字面量扫描过闸 (0→非0) → 重打包 → 才谈
   插桩 boot3 裁决 (与 1 分轮, 各自哈希/manifest/readiness 独立过门)。
3. 心跳 cron 仍有持久+session-only 双份 (12362354/483afcf9), 用户未裁决
   撤一; 本轮未新建唤醒 (两份均在跑, 续唤醒条件已满足), 保险丝 5f873c8d 6h 在位。

verify: shasum 三 raw (上文 hash); git diff/log 计数; docker exec ls -la
对象 mtime; pgrep/ioreg 快照; 42 测试 OK; objdump 反汇编行见 §2。
本轮: 未 run fastboot, 未写分区, 未碰 userdata, 未 push。
