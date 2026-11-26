# 心跳 20261109-0200: 插桩 guard 机制定罪 + 并行证据链复核 (只读轮)

> **回撤横幅 (2026-11-09 03:0x 轮)**: §1 "从未到达编译器/消费点不存在" 已证伪 ——
> 消费点 = MakeInc.rule:301 C_RULE_1A (${$@_CFLAGS_ADD}, 与 lz4 同机制);
> "build.log grep=0" 与 "00:27 nm 0 命中" 两条观察均无效 (日志不回显命令行;
> nm 报 "file format not recognized" 被 grep -c 吞掉)。llvm-nm+LE64 重扫
> 仍证插桩未编译, 真根因转向汇编侧 _SFLAGS_ADD 缺失 (见 §2 影响面的更精确版)。
> 详见 heartbeat-20261109-0300-r6-verified-gate-retracted.md §2。

时刻: 2026-11-09 02:04 CST。设备: 不在 fastboot 窗 (ioreg 最后 attach
11-09 00:21, 现已消失; 无 fastboot 进程)。HEAD=84cf481 (并行会话已提交
r6 核验 docs), 工作区 21 处在途改动 (builder/readback/package/patch 系
并行件, 本会话不碰)。readback-names 套件本轮重跑 OK。

## 1. 定罪: XNU_NATIVE_EARLY_FAULT guard 从未到达编译器 (升级 0130 轮的"未定罪")

证据链 (本轮新增部分):
- 容器 work 树 (.cache/xnu4903-work) 状态: 两个 marker 文件均在
  (.native-early-fault-applied / .native-phase-markers-applied),
  locore.s(2)/start.s(1)/arm_init.c(3) 均有宏引用 —— 但 arm_init.c 只有
  2/3 个 native_phase_marker 调用点 (定义:88 + ARMVINI:396 + PANICINI:408,
  CONSOLE hunk 缺失), 且全树无 .rej → 上轮 "Hunk#4 未落地" 观察复现。
- 判决件: arm_init.o (Nov 8 00:27 编译, 晚于 00:26:34 的源码打补丁) 内
  ARMVINI/PANICINI/CONSOLE 字符串与小端 8 字节字面量全部 0 命中,
  nm 无 native_phase_marker 符号 → 源码里存在的插桩代码在编译期被
  #if 整段剔除 = 宏当时不可见。
- build.log (169MB, 00:31 run) grep XNU_NATIVE_EARLY_FAULT = 0 命中:
  -DXNU_NATIVE_EARLY_FAULT=1 (make 命令行变量 arm_init.o_CFLAGS_ADD=…)
  从未出现在任何编译行 (静默规则只记 warning, 但宏字符串全局缺失
  与 .o 证据相互印证)。
- 消费端排查: lz4.o_CFLAGS_ADD 类 per-object 变量确实在 Makefile.arm64/
  Makefile.template 系中被"设置" (foreach eval +=), 但设置≠消费 ——
  生成 Makefile 与 makedefs (MakeInc.cmd/def) 均未找到 $(…_CFLAGS_ADD)
  的编译行消费点 (osfmk 生成 Makefile 无 .c.o/%.o:%.c 规则文本)。
  无论消费在更深 include 还是根本不存在, 实证结论已成立: 该传递
  路径对 arm_init.o 无效。
- 影响面: guard 保护的还有 native-early-fault-record.patch (locore/start
  系 record[0..4] 写入) —— 它同样依赖此宏 → 早期故障记录从未编译进
  任何内核, 与 r6 early-fault-record 全 0 观测吻合 (此前被解释为
  "没触发", 实为"代码不存在", 与 phase 同一根因)。

## 2. 对并行在途件的告警 (重要)

native-phase-markers.patch (untracked, 01:33 后新写) + builder 自动应用
逻辑仍原样使用 `#if defined(XNU_NATIVE_EARLY_FAULT) && …` guard。
§1 已证该 guard 在现 make 传参下失效 → 若不改 guard 机制直接重建,
新内核依旧 0 插桩, 将再次浪费一次 RAM-boot 取证窗。
修复方向 (任一, 由并行会话决策):
(a) 去 guard, 插桩无条件编译 (0130 轮笔记的既定倾向);
(b) 查得真实消费点后改用之 (如 LOCAL_CFLAGS / 直接改 Makefile 片段);
(c) 补 hunk4 时同步验证 patch 应用完整性 (marker 文件存在不代表
    全 hunk 落地 —— 本轮即反例)。

## 3. phase-r6.raw (00:47) 再定性

stage 头 kernel stamp = 5fd4e6b5 (vanilla 出货件), 非 00:31 的 70eec34f。
即 README-r6 序列里最后一次 boot4 也跑在无插桩内核上, record[5]=0 有
双重解释 (代码不存在 + 内核旧代)。容器新核 70eec34f 至今未打包未上机
(NAMES 中 phase 系符号全为可选, 对其 nm 校验无意义直到重打包)。
r6 定案判词 (死亡窗收窄到 PE_bootargs_init 之后、PE_create_console
之前) 不受本条影响 —— 它基于载体与 PRAM 行为, 不依赖相位标记。

## 4. 传输/设备轮值记录

- 02:04 USB 仅 webcam/hub, 设备不在 (00:21 attach 后已消失)。
- 本窗已烧的最近一次机会: 若并行件按 §2 修好 guard → 重建 → nm+字面量
  双扫描过闸 → 重打包 → 才可申请下一次 RAM boot; 顺序颠倒即烧窗。

verify: 命令记录见本会话 Bash — nm/grep 计数/stat 时间戳/mov 字面量
LE64 扫描/build.log grep/ioreg/pgrep/测试 11 OK。
