# 04:0x 心跳轮: r7 CNTVCT 见证 — 捕获链判 LIVE, r6 悖论消解, 新悖论立案 (authorized RAM-only)

## 授权与门禁
- 本轮心跳指令明确授权 RAM-only 探针流程; 前置三门全过:
  1. 无并行 fastboot (pgrep 空; linked sessions 2 个均 idle)
  2. 镜像实核: r7 从 HEAD 归档 (/tmp/r7-run, git archive scripts+tests) 生成,
     绕开并行 dirty 文件; image sha 2aaf092c… == manifest; 真 ELF 反汇编实证
     `mrs CNTVCT_EL0; str x11,[x10,#16]` @0x80080064; entry.bin 内嵌于 img
  3. 安全性实核: r6 stage 解出 EL2 存在(PFR0=0x2222)+ CPACR_EL1.TFP=0 →
     CNTVCT 读路由到 EL2, 无 trap-hang 风险; MIDR=0x410fd030 与 A53+ARMv8.1
     内核一致。boot3.img 实测 d7640a42 == manifest == 授权世代。
- 全程 `fastboot boot` (RAM-only), 零分区写, 零 userdata。

## 实测序列 (同电源周期, 每步 getvar 瞬答)
| # | 动作 | 见证 W | 结果 |
|---|------|--------|------|
| 1 | r7 探针 boot | 206,632,793,465 (~6297s 计数, 跨上电保持) | stage 全字段正常 |
| 2 | r7 探针 boot #2 | 889,200,838 (**变小**) | 见"计数器语义更正" |
| 3 | boot3 → 探针 #3 | 72,579,148 | 三连捕获逐字节仅差 W 的 5 字节 |

## 判词 1: 捕获链 = LIVE (0340 悖论的 (i) 分支否决)
两份探针捕获整 69632B 里只有 stage 偏移 16..20 的见证值不同 —
records 是 LK 对同一 stage 缓冲的重新活读, 通道不冻结、不缓存假死。

## 判词 2 (更正): panic 窗 0x10000 = boot3 shim 交棒标记, 非 debug_buf 拷贝
追 package_native.py:132 与 capture_format.py:61 定罪: 文件偏移 0x10000 处
"Y35AXNU2"+kernel_sha[0:8] 是 **boot3 RAMBoot 垫片**写入的交棒戳, 不是
readback 探针的 debug_buf 字节拷贝。探针的拷贝目标是同址 0x859f0000, 但
三元组 _debug_buf_base/ptr/size 实测全 0x0 → 生成器汇编里 `cbz x2` 在
copy_bytes 入口即跳 capture_done, **拷贝分支从未执行**。
所以: (a) panic 窗内容 = 该电源周期内最后一次 boot3 的内核世代戳,
r7-probe2 显示 6e9a09d2 (上一 session 00:16 跑过 6e9a09d2 boot3, DRAM 存活),
r7-post-boot3 显示 5fd4e6b5 (本轮跑了 d7640a42=5fd4e6b5 世代) → **戳随世代翻转,
证明 boot3 确实执行且交棒戳落地**, r6 三份恒 5fd4e6b5 只是同世代连续 boot, 无悖论。
(b) 真正的洞: debug_buf 三元组读回 0x0 = 探针 record 的 VA→PA 换算错
(或 debug_buf_* 在 4903 里本就是运行时才写、boot 完仍 0 的全局, 需查),
⇒ 判词 3。

## 判词 3 (新悖论, 取代旧悖论): XNU 写的 globals 读回全零
_BootArgs/_gPanicBase/_debug_buf_base/_panicDebugging/_debugger_panic_str
在 post-boot3 捕获里与 baseline 全等 (LK 从未写这些, 值=上电零+噪声)。
_BootArgs=0 是硬的: XNU 入口不可能填过 boot_args 后又清零。
⇒ 候选: (a) 符号 VA→PA 换算错 (物理基址映射假设错, kernel_physical_base
  0xa0004000 vs layout 推导不同源) — panic.raw 里 "XNU 文本在 record 区"
  旧证据也早有 table 错位前科 (09cfea3 自证), 支持换算/布局层有洞;
  (b) boot3 确实没执行到 globals 初始化 (旧判词复活, 但需要 (a) 先出局);
  (c) stage 区 0x859e0000 被 LK/其他 master 占用, 拷贝互相覆盖。
下一步裁决 (离线可做): 用 boot_layout 重算 record PA 并抽 raw DRAM 窗口
直接找 boot_args Revision 魔数 (0x1/0x2 开头)+ "Y35A" DT compatible 字符串,
不依赖符号换算; 若活 DRAM 里能找到而 record 读到 0 → (a) 定罪。

## 计数器语义更正
W 非单调 (2.06e11 → 8.9e8 → 7.3e7): CNTVCT 被 XNU/LK 启动路径重编 KVM
timer 控制块 (cntvoff/CNTFRQ/SCR_EL1) 重基 — "跨上电恒保持"假设错误。
见证仍有效: 同阶段值稳定、异世代可辨, 足以裁决捕获链; 不可当时钟用。

## 产物
- out/y35a/readback-probe-20261109-r7/ (img 2aaf092c…, entry.S/elf/bin/json)
- r7-witness-20261109/{r7-baseline,r7-probe2,r7-post-boot3}.raw + w1.txt
- 本轮无生成器/打包器代码改动; builder SFLAGS_ADD 与 package_native
  并行件未触碰。

verify: fastboot boot x3 + oem y35a panic + get_staged 实录; r7 生成/核验
命令与 SHA 见本文件与上一 Bash; r6 头字段逐字节 diff=8@65544 实测。
