# R73 idle 初始化与主动 debugger trap 独立审计

2026 年 11 月 11 日。C 分支只读核对，唯一新增文件为本文。没有修改 decoder、主验证器、内核源码或实验资产，没有构建或运行设备、容器、远端操作。主线负责 panic reason 捕获和后续真机实验；本文不另行设计或执行设备实验。

## 结论与证据等级

已实证：R73 新鲜 Y35ALV03 的 ELR 为 0xfffffff007125b70，实际 kernel 文件偏移 0x121b70 的四字节为 ff de ff e7，指令字为 0xe7ffdeff。它位于 DebuggerTrapWithState+0x64，与 arm64 的 TRAP_DEBUGGER 宏主动发出的 .long 0xe7ffdeff 一致。EC0、IL1、ISS0 记录的是这次主动 trap，不是 sleep token、SMC 或原始 panic 原因的直接编码。FAR0 不作为地址。

最强静态候选：T7001 编入 WITH_CLASSIC_S2R，cpu_machine_idle_init(TRUE) 对 BootCpuData 强制要求 sleepTokenBuffer 非零；封存且实际嵌入 boot 镜像的 ADT 没有 stram 节点，早先 sleep_token_buffer_init 因查找失败而返回的正常路径不会设置该变量。对应直接 panic 调用点为 0xfffffff007257d14，格式指针为 0xfffffff0070592df，传入 DebuggerTrapWithState 的 panic_caller 应为 0xfffffff007257d18。

尚未实证：R73 四字段终止记录不含 db_op、格式指针、panic_caller 或运行时 sleepTokenBuffer，不能宣布上述原因已最终坐实。ml_static_vtop 的显式 panic 在 sleep-token 检查之前也可发生；树遍历的 overflow panic 亦有真实调用点。slot13 只证明最后保留了 R73PRT00，不能单独证明后续函数没有返回，更不能排除后续标记丢失。本文按实际顺序与输入资产给出候选排序，不以字符串存在代替因果链。

## 封存产物与独立检查

证据根目录为 [phase-r73-post-console-vector-20261111](/Users/lingion_k/unixnu-research/UniXNU-y35a/evidence/y35a-20261102/boot3-20261106/phase-r73-post-console-vector-20261111)。以下 SHA-256 均在本次审计重新计算：

| 产物，相对证据目录 | SHA-256 |
|---|---|
| kernel/kernel.macho | 848a07ff9736e881c0759b841d44ee0f6fdff42d61cfca682fe82b0ba8814b5b |
| boot/boot3.img | 85a723af5e6368ad46324d2fed8a97bf9817c1bba172b24e17e3cb6afdcae0d8 |
| boot/board.adt | 1a89ce9a6acff82b6b2a501314c5f4ae06f2259fbe9b39c1b19ce94950412ea1 |
| boot/boot-args.bin | 353edec03d763f03ec9d35b93eaacf2f9bf34a87631f8c8cff36e3fc37ceb404 |
| baseline.raw | 1c49eed16a6a3896101916ce27ffdc397d6965f6a90e6caf3cfe307a1b488c8a |
| final.raw | 64bb6cf440a0b29727247f302da43252c174f61c7844a2a1fe159ae8bc14b8ad |
| readback-probe/readback.json | 750345f778f2ec3a329d49e463d822fb437eb1fe1762c5ddecff37a0370ac365 |
| readback-probe/readback-probe-not-xnu.img | 30754ac71692070d897731d3681cd3cd49cf167a966d55d5e9bfdb97ca364010 |
| kernel/arm_init.c | 9ca2814f02dda332b0477a636852352fed000397f752eea5905482ad05298d31 |

kernel 完整 11,532,880 字节与 boot3.img 中偏移 0x4c50 的内容逐字节相同。board.adt 完整 12,556 字节与 boot3.img 中偏移 0xc30 的内容逐字节相同。本文不是只读取旁边的历史反汇编文本；使用 Xcode llvm-objdump、llvm-nm 直接读取以上 Mach-O，并独立用 Python struct 按 LC_SEGMENT_64 映射指令和字符串地址，解码关键 BL 的有符号偏移验证目标。

readback.json 按 record.name 找到 early-fault-record，minimal report_offset=0x100，故 raw 偏移为 0x10100。baseline 四字段全零，final 为 Y35ALV03、0xfffffff007125b70、0x02000000、0。slot13 的 raw 偏移 0x10168 从 COMMON00 变为 R73PRT00。两份 raw 的探针 tag 都匹配本轮 kernel 前缀 848a07ff9736e881，与落盘 terminal-fault.json 一致。

## 实际进入 idle 的边界和有序调用链

封存 [arm_init.c](/Users/lingion_k/unixnu-research/UniXNU-y35a/evidence/y35a-20261102/boot3-20261106/phase-r73-post-console-vector-20261111/kernel/arm_init.c:435) 的源码顺序与实际机器码一致：

| R73 PC | 实际动作与参数 |
|---|---|
| 0xfffffff007259cf8 | BL sleep_token_buffer_init，发生在 console 建立及 v3 高 VA VBAR 重装之前 |
| 0xfffffff007259dfc、0xfffffff007259e00 | MSR VBAR_EL1 和 ISB |
| 0xfffffff007259e2c | BL PE_init_printf，w0=0 |
| 0xfffffff007259e48 至 0xfffffff007259e50 | store R73PRT00、DC CIVAC、DSB SY |
| 0xfffffff007259e54、0xfffffff007259e58 | w0=1；BL cpu_machine_idle_init，正常返回地址 0xfffffff007259e5c |
| 0xfffffff007259e74 至 0xfffffff007259e7c | 正常返回后 store R73IDL00、DC CIVAC、DSB SY |

PRT 标记发布与 idle BL 之间没有 dump_kva_space 调用；源码的 DEBUG 条件块没有进入这份实际指令序列。新鲜 PRT 是 PE_init_printf 已返回且到达该 store 的正证据。没有 IDL 是保留证据的缺失，不单独构成“确定没有执行返回”的证明。

cpu_machine_idle_init 的入口为 0xfffffff007257b48，完整函数直到 0xfffffff007257d6c 的 RET。正常 from_boot=TRUE 路径依次为：

1. 0xfffffff007257b5c 读取 TPIDR_EL1，0xfffffff007257b60 从 thread+0x480 取得 cpu_data_ptr，保存在 x19。
2. 0xfffffff007257b8c、0xfffffff007257bbc 调用 PE_parse_boot_argn，分别读取 jtag、wfi。封存 boot-args 的命令行为 `-v serial=3 cpus=1 debug=0x8 rd=md0`，未指定 jtag 或 wfi，局部默认 wfi=1。仅 wfi 低字节等于 2 时才走 0xfffffff007257c10 的 nanoseconds_to_absolutetime 调用；默认路径跳过它。
3. 0xfffffff007257c28 调用 ml_static_vtop(CpuDataEntries)，把结果存入 ResetHandlerData。
4. 0xfffffff007257c38 调用 ml_static_vtop(LowResetVectorBase)，0xfffffff007257c4c 调用 monitor_call(0x800, 上一步结果, 0, 0)。
5. 0xfffffff007257c60 查询 /chosen；0xfffffff007257c88 读取 effective-production-status-ap。默认 production=1；属性不存在或长度不是 4 时不产生该函数的显式 panic。
6. 0xfffffff007257cc4、0xfffffff007257cd8 分别调用 ml_static_vtop(start_cpu)、ml_static_vtop(resume_idle_cpu)。
7. 0xfffffff007257ce8 比较 x19 与 BootCpuData=0xfffffff007763da0；不相等时跳过 sleep-token 块。相等时在 0xfffffff007257cf4 读取 sleepTokenBuffer=0xfffffff0077a76f0，在 0xfffffff007257cfc 用 CBZ 判零；零路径进入 0xfffffff007257d14 的直接 panic。
8. 仅 token 非零时，0xfffffff007257d00 调用 ml_vtophys；0xfffffff007257d20 调用 ml_static_vtop(running_signature)；0xfffffff007257d2c 调用 bcopy_phys，长度 x2=8；0xfffffff007257d40 调用 flush_dcache。最后写 cpu_reset_handler，0xfffffff007257d58 调用 clean_dcache，然后返回。

wfi=0 只设置全局 wfi 后汇入 0xfffffff007257c14，仍执行 monitor 和 sleep-token 检查。jtag 控制 idle_enable，也不跳过这些初始化。封存 ADT 的 /defaults/sleep-disabled=1 没有被这段函数读取，不能当作 WITH_CLASSIC_S2R 初始化已经禁用。

## 首选候选：classic S2R 缺少 sleep token

源码依据为 [arm64/cpu.c](/tmp/xnu4903-native-bqbvhqi_/src/osfmk/arm64/cpu.c:796)，必须区别于 arm/cpu.c。宏链为 board_config.h 的 ARM64_BOARD_CONFIG_T7001 分支定义 APPLETYPHOON 并包含 T7000.h；后者定义 WITH_CLASSIC_S2R=1 并包含 typhoon.h，typhoon.h 定义 MONITOR=1。实际 Mach-O 的 token 判零分支和 monitor BL 确认这两项均未被编译消除。

sleepTokenBuffer 是 cpu.c:133 的静态零初始化变量；符号位于 __DATA 的零填充区，不能把文件中的任意同偏移字节当作运行值。源码搜索到的正常赋值只有 sleep_token_buffer_init 的 ml_io_map 返回值。其实际代码为：

| R73 PC | 条件或动作 |
|---|---|
| 0xfffffff007257dd4 至 0xfffffff007257ddc | 只有 cpu_data_ptr==BootCpuData 且 sleepTokenBuffer==0 才继续初始化 |
| 0xfffffff007257df0 | DTLookupEntry(NULL, "stram", &entry) |
| 0xfffffff007257df4、0xfffffff007257df8 | 返回值不等于 kSuccess=1 时转向函数尾，静默返回 |
| 0xfffffff007257e10 | DTGetProperty(entry, "reg", ...)；失败也返回 |
| 0xfffffff007257e20 至 0xfffffff007257e28 | 从 reg 载入 x0=物理地址、x1=长度，BL ml_io_map，把 x0 写入 sleepTokenBuffer |

独立逐节点解析封存 ADT 的全部 12,556 字节，确认没有根节点下的 stram，整个树也没有同名节点；不是 `strings` 搜索或对当前生成脚本的猜测。DTLookupEntry(NULL,"stram",...) 从 DTRootNode 的子节点查找；缺节点返回错误。树中有 pram，但这是另一个名称和用途，不满足 stram 查找条件。

在正常冷启动的零初始化、BootCpuData 身份和未损坏 ADT 前提下，以上构成“缺 stram、初始化静默返回、token 为零、idle 显式 panic”的完整静态路径。四个前提的运行时值并未全部保存在 R73 raw，因此仍需主线的格式指针与 caller 取证，而不是直接宣布已确认根因。

最短候选调用链及其机器码绑定为：

    arm_init
      0xfffffff007259e58 BL cpu_machine_idle_init(TRUE)
      0xfffffff007257d14 BL panic
      0xfffffff007125d48 BL panic_trap_to_debugger
      0xfffffff0071268a0 BL DebuggerTrapWithState
      0xfffffff007125b6c BL DebuggerSaveState
      0xfffffff007125b70 .long 0xe7ffdeff

DebuggerSaveState 返回后才执行 trap。R73 的 ml_wants_panic_trap_to_debugger 为 `mov w0,#0; ret`，故此路径不会转入另一个架构专用 panic 入口。普通无上下文 panic 进入上述 0xfffffff0071268a0 的分支。这是一条与观察一致的最短候选链，不是从终止记录恢复出来的完整回溯。

此候选的唯一化证据：db_op=3（DBOP_PANIC）、db_panic_str=0xfffffff0070592df、db_panic_caller=0xfffffff007257d18。字符串实物包含首尾双引号，字节内容为 `"No sleep token buffer"`，因为 CONFIG_EMBEDDED 的 panic 宏对 ex 使用字符串化。cpu_sleep 也存在同文本，只有文本不足以区分调用点；caller 必须一并核对。

## 次选候选：ml_static_vtop 的合法范围检查

[arm64/arm_vm_init.c:322](/tmp/xnu4903-native-bqbvhqi_/src/osfmk/arm64/arm_vm_init.c:322) 先按最多八个 ptov_table 条目查找，遇 len=0 即停止。未匹配时检查无符号 `(va-gVirtBase) >= gPhysSize`；满足则 panic，未满足则返回 `va-gVirtBase+gPhysBase`。这不是页表翻译故障或 MMU abort，而是显式的 C 范围校验。

| 调用 PC | 输入 x0 | 按封存 boot-args 线性基址计算的 PA |
|---|---|---|
| 0xfffffff007257c28 | CpuDataEntries，0xfffffff0077632a0 | 0xa07632a0 |
| 0xfffffff007257c38 | LowResetVectorBase，0xfffffff00726e000 | 0xa026e000 |
| 0xfffffff007257cc4 | start_cpu，0xfffffff00727000c | 0xa027000c |
| 0xfffffff007257cd8 | resume_idle_cpu，0xfffffff007270000 | 0xa0270000 |
| 0xfffffff007257d20 | running_signature，0xfffffff007007eb0，仅 token 非零后 | 0xa0007eb0 |

封存 boot-args 的 virtBase=0xfffffff007004000、physBase=0xa0004000、memSize=0x10000000。以上五个 VA 相对 virtBase 的偏移分别是 0x75f2a0、0x26a000、0x26c00c、0x26c000、0x3eb0，全在此大小内。arm_vm_init 的源码在入口复制这些全局量。因此正常输入下该范围检查不应失败，但这不证明故障时全局量和 ptov_table 未损坏。

实际检查 PC 是 0xfffffff00725a65c 的 CMP 和 0xfffffff00725a660 的 B.LO；落入错误分支时，0xfffffff00725a664 把非法 VA=x19 写到当前 SP，0xfffffff00725a670 BL panic。格式指针为 0xfffffff00705976a，panic_caller 应为 0xfffffff00725a674。格式字符串实物为 `"ml_static_vtop(): illegal VA: %p\n"`，包含被字符串化的反斜线。

若主线得到此 caller，应再取实际 VA 参数及 gVirtBase=0xfffffff0077653c0、gPhysSize=0xfffffff0077653d0、gPhysBase=0xfffffff0077653b8。ptov_table=0xfffffff0077a7758，八个条目，每项按 pa、va、len 各八字节排列。读回全零不等于故障时全零；最好绑定 panic 时点的参数或有提交标记的快照。

## monitor SMC 与其余替代原因

monitor_call 的实际入口 0xfffffff007273f30 为指令字 0xd4000223，即源码 SMC #0x11 的编码；下一条 0xfffffff007273f34 是 RET。调用前 w0=0x800（MONITOR_SET_ENTRY）、x1 为 LowResetVectorBase 转换结果、x2=x3=0。调用后 0xfffffff007257c50 直接准备 DTLookupEntry 参数，既不检查 SMC 返回值，也没有“返回失败后 panic”的分支。

因此：SMC 仍是 Apple EL3 接口与平台契约的潜在不兼容点，但当前 ELR 在 DebuggerTrapWithState，不能称为已捕获 SMC 未定义。若 SMC 指令本身在当前 EL 被直接捕获，预期定位点应为 monitor_call 的 0xfffffff007273f30，而不是本轮 0xfffffff007125b70。若首选 sleep-token caller 被证实，则在正常顺序执行前提下，SMC 已经返回过；这也不证明固件理解或成功执行了 Apple MONITOR_SET_ENTRY 语义。固件副作用或寄存器破坏未被测量，不能凭存在一条 SMC 宣布根因。

真正存在的其他 C panic 路径如下，优先级低于有直接输入证据的 sleep token：

- DTLookupEntry 的 next_prop overflow panic 调用点为 0xfffffff0076bb1b0、0xfffffff0076bb20c；DTGetProperty 为 0xfffffff0076bb548。对应 caller 分别为调用点加 4。它们的格式指针均指向 0xfffffff0070c2fab，内容为 `"Device tree property overflow: prop %p, length 0x%x\n"`。封存 ADT 有界且完整解析通过，正常属性长度不会满足 overflow；运行时树指针或内容损坏仍属未知。没有 effective-production-status-ap 属性本身只保留 production=1，不触发此 panic。
- ml_vtophys 入口 0xfffffff007272b74 直接尾跳 kvtophys。它及 bcopy_phys 只在 token 非零的分支执行，不能用来解释“token 本来为零”的路径。bcopy_phys 的长度固定为 8；其源码参数溢出断言的实际 Assert 调用点为 0xfffffff00725cac0、0xfffffff00725cae0，要求实际物理地址加 8 溢出等异常输入。若格式变成 Assertion failed，需要继续用断言参数区分，不能归到同名 sleep-token 字符串。
- 实际 flush_dcache=0xfffffff007256524 和 clean_dcache=0xfffffff00725652c 在这份内核中都只有 DSB SY、RET，没有 Apple 寄存器访问或 panic 分支。不能拿未核对的原版缓存实现替代封存机器码。
- DebuggerWithContext 同样可以进入 DebuggerTrapWithState，db_op=4；故主动 trap 本身甚至不足以唯一证明调用者是 panic。当前正常 idle 链未发现直接 Debugger 调用，db_op 的捕获可立即区分此类替代路径。

## 供主线使用的最小参数取证点

以下 PC 全部只适用于上述 SHA 的 R73；新增代码重新链接后必须以新 Mach-O 重映射，不能照搬数字。

| 取证点 | 应保留的值 | 可区分的结论 |
|---|---|---|
| DebuggerTrapWithState 入口 0xfffffff007125b0c | w0=db_op、x2=格式指针、x7=panic_caller；x1=message、x3=va_list 指针按需要保留 | sleep token、ml_static_vtop、DT overflow、非 panic Debugger 可以直接分开 |
| panic 入口 0xfffffff007125d1c，在首次 BL 前 | x0=格式、x30=原调用者返回地址；原 SP 上的变参 | token 应得 caller 0xfffffff007257d18；vtop 应得 0xfffffff00725a674 |
| cpu_machine_idle_init 0xfffffff007257cfc | x19=cpu_data_ptr、x0=sleepTokenBuffer | 验证 BootCpuData 身份与零 token 分支 |
| ml_static_vtop 0xfffffff00725a664 或其 panic 入口 | x19=非法 VA；此处 SP 首个八字节也是该 VA | 区分五个调用输入，以及全局映射参数异常 |
| monitor_call 前后 0xfffffff007257c4c、0xfffffff007257c50 | 调用前 x0..x3；返回后的 x0，仅在已有捕获机制合适时 | 判断是否到达和返回，不能把返回当作 Apple 服务语义成功 |

在 R73 trap 指令处，编译器仍以 x26 保存 db_op、x24 保存格式、x23 保存 args、x19 保存 caller；但 terminal observer 会使用寄存器，现有 raw 没有这些字段。不能把 probe 时寄存器或 handler 已改写的值当作 fault 时值。用户主线已经在入口捕获 reason，优先使用入口参数，不需要本分支再改向量或设计设备回合。

Apple arm64 此处的实际 panic 汇编将原调用者 SP 作为变参区，并把 va_list 的地址传给后续函数；DebuggerTrapWithState 的 x3 不是非法 VA 本身。vtop 候选要读对应 va_list 指向的首个八字节变参，不能直接把 x3 当故障地址。取得格式、caller 后再决定是否需要读取有界变参；无需为了当前候选构造完整寄存器或完整回溯。

DebuggerSaveState 在 trap 之前写的是 current_processor()->debugger_state，相关实际偏移为 op +2696、message +2704、panic_str +2712、args +2720、caller +2760。全局 debugger_panic_str 的复制发生在后续 handle_debugger_trap；R73 的 terminal observer 在主动 trap 处截停，未执行这条正常处理链。因此 raw 中全局 _debugger_panic_str 为零不能反证没有 panic，更不能反证没有格式字符串。现有 raw 也没有 current_processor 对象的对应字段。嵌套时 DebuggerSaveState 还可能保留首次 panic 信息，应区别入口参数与对象中历史保留值。

主线一次 reason 捕获即可按下面条件收敛：

1. op=3、格式指向 sleep token 文本、caller 对应 idle 的直接 panic：确认 classic S2R 初始化前提缺失是本次路径原因；同时可推断前面的 SMC 已返回。
2. op=3、caller 对应 ml_static_vtop panic：首选 token 候选被本轮推翻，按变参 VA 与映射全局量定位具体输入。
3. op=3、DT overflow 格式及其 caller：优先核对运行时树指针和属性长度，不能把无 stram 当作此次 panic 原因。
4. op=4 或其他 caller：按捕获值重建调用者，不把本文排序当既定事实。新一轮若重链接，比较符号和指令关系而非旧绝对地址。

## 源码绑定与验证范围

当前 /tmp 工作源码中的 debug.c 已被主线写入后续 reason 捕获，不能当作 R73 的原始完整函数。本文改读主线封存的 [debug-before.c](/Users/lingion_k/unixnu-research/UniXNU-y35a/evidence/y35a-20261102/boot3-20261106/phase-r74-panic-reason-20261111/kernel/debug-before.c:462)，其 SHA-256 为 0fa36351a8f079af8d4c008cfdc3ccebd8e9e1a1da6014f1b5de49d8f5e6feca。该文件提供 R74 插桩前的解释来源；不是另一个实验结果，也不以文件名替代 R73 机器码核对。函数参数、assert 行号 468、SaveState 顺序、trap 字与 R73 实际代码相符。

其他本次读取源码的 SHA-256：

| 相对 /tmp/xnu4903-native-bqbvhqi_/src | SHA-256 |
|---|---|
| osfmk/arm64/cpu.c | 143ab7c450cd33797910ca68e4f6ea14418bacb71e578a82fc51735a876e194f |
| osfmk/arm64/arm_vm_init.c | 6e167fec085e8cd226f48aafbaa6d9d08560b96970cab8e4c977a95f898aec0c |
| osfmk/arm64/machine_routines_asm.s | 6baf04cedf03fe948432863b1d4321c5dde33ca00100287eb66c963491743bf6 |
| pexpert/pexpert/arm64/board_config.h | cee1e2b61dab31063deedc94d3ba0af031fbcf6681ad75257f3ae2ec9270c6a3 |
| pexpert/pexpert/arm64/T7000.h | 72def6bee859c13ee4d0335c05b035ee2c4d3265c52ee6022255292c82b151f4 |
| pexpert/pexpert/arm64/typhoon.h | 93cd23d67632eec3505efc7b2f901a930daf4032de084f9db4ca2cc571f91342 |
| osfmk/arm/machine_routines.h | a0d7d767066076f6310255c7b73bb60c48568d97117afff9b3142138049fa0e6 |
| pexpert/gen/device_tree.c | 5e206af904271775795dbdf6bbdbb7b196dbc7fbfd7bd958dcf5405dc5da5902 |

只读验证包括完整产物哈希、嵌入字节相等、raw 四字段与 slot13 对比、完整 ADT 结构解析、llvm-nm 符号定位、关键函数实际反汇编及关键 BL 指令独立解码。没有运行项目脚本、测试套件或构建。公开源码搜索未返回可引用结果；本文依据本地源码与封存机器码，不声称在线认证过固件或平台 SMC 行为。

用户要求逐项核验：已给出有序实际调用链和最短候选 panic 链；sleep token、monitor SMC、ml_static_vtop 分别核对条件与实际指令；所有候选区分已实证、静态推导和未知；给出具体 PC、格式与 caller 取证点；没有重复主线设备工作，也没有改动本文之外的文件。


## R74b 更新：根因已实证，关闭 classic S2R 的范围审计

2026 年 11 月 11 日后续更新。此节替代前文“sleep-token 仍待唯一化”的当前状态；前文保留为 R73 时点的证据和推导。此次仍只有本文发生本分支写入，未修改主线新补丁、构建器、头文件或驱动，也未运行构建或设备操作。

### 独立复核 R74b 的直接证据

读取 [result.json](/Users/lingion_k/unixnu-research/UniXNU-y35a/evidence/y35a-20261102/boot3-20261106/phase-r74b-panic-reason-20261111/result.json) 后，另外读取同目录真实 kernel、baseline.raw、final.raw、readback.json 和 probe，重新计算哈希并按段映射解码 caller，没有只接受 JSON 的 binary_string_matches 字段。

| R74b 产物 | 本次重新计算 SHA-256 |
|---|---|
| kernel/kernel.macho | 3fab5e39de922b8c2018b7d7a380ad2eb417d82284bc9f6e54491f0527a9a678 |
| baseline.raw | a119caf2d66af6c1772220924b4b34f4a6881723bb5b004b2798914fae3321f7 |
| final.raw | efa9a7cb4b01e58d8953d55157015a31d6ecc0cb01ae85e3b424abb331f8c941 |
| readback-probe/readback.json | a54cca8add9c88eeffdcea90802249784dfbdc309cb109c37af61c89841ab838 |
| readback-probe/readback-probe-not-xnu.img | da2bdc76befd4d72593f87daa73b617adebb552d7a3a3148c958c2c7cc0acb5f |

probe 完整哈希匹配 manifest；baseline 和 final 的 probe tag 都为 R74b kernel 前缀，final 的 shim tag 也匹配 R74b。baseline 的 shim tag 仍是 R73，符合先前启动世代保留，不作为绑定失败。

按 carrier 原始偏移读取，slot14 从旧 MAPDONE0 变为 R74PAN01，slot15=3，slot16=0xfffffff0070592df，slot17=0xfffffff007257ed8；slot24 至 slot31 的 64 字节为带双引号的 No sleep token buffer 文本、终止零和其余零填充。格式指针映射到 R74b 实际 Mach-O 后，直至 NUL 的文本逐字节相同。封存 debug.c 的记录器先写 payload 和文本、清理对应缓存行并 DSB，再发布 magic，支持此次记录的新鲜性判定。

实际 R74b cpu_machine_idle_init 入口已经移动到 0xfffffff007257d08。0xfffffff007257eb4 读取 sleepTokenBuffer，0xfffffff007257ebc 的 CBZ 跳到错误分支；0xfffffff007257ed4 的指令字 0x97fb37f6 解码为 BL panic=0xfffffff007125eac，因此 LR 正是捕获到的 0xfffffff007257ed8。独立 llvm-objdump 与 [panic-caller.disassembly.txt](/Users/lingion_k/unixnu-research/UniXNU-y35a/evidence/y35a-20261102/boot3-20261106/phase-r74b-panic-reason-20261111/kernel/panic-caller.disassembly.txt) 一致。

结论现在是已实证：本次在 cpu_machine_idle_init 的 BootCpuData classic S2R token 判零路径触发 panic，不是 cpu_sleep 中同名文本、ml_static_vtop 或 SMC 指令自身异常。正常顺序执行前提下，此路径之前的 monitor 调用已经返回；仍不证明 Apple monitor 服务在目标固件具有正确语义。R73 旧 caller=0xfffffff007257d18 不应继续用于 R74b。

### 最小关闭方式与主线当前选择

本轮读取到了主线新建的 [native-y35a-no-classic-s2r.patch](/Users/lingion_k/unixnu-research/UniXNU-y35a/patches/xnu/native-y35a-no-classic-s2r.patch)，读取时 SHA-256 为 5f95c60243a858ff7a9586f4587a060a56717a845fbeb7385b17531503a3e17f。它在 T7000.h 保持原默认值，只在 `defined(XNU_Y35A_A53) && XNU_Y35A_A53` 时定义 WITH_CLASSIC_S2R=0。这是现有宏边界下集中关闭 classic Apple S2R 协议的最小一致方式，符合不伪造 stram 的选择。

这个 guard 不应换成通用 XNU_NATIVE_EARLY_FAULT：故障观测开关不代表板级固件能力。也不宜仅从命令行定义 WITH_CLASSIC_S2R=0，因为原 T7000.h 无条件定义为 1，会出现宏重定义及选择不一致。由板级 guard 控制统一头文件，并让所有编译消费者使用同一选择，边界更明确。

仅局部跳过 idle 中 BootCpuData 的 token 块，确实可更少改变低启动区，但只代表绕过本次启动检查：ml_arm_sleep 的 suspend signature 路径仍会依赖 token。若要采用局部诊断 guard，则初始化调用、running signature 和 suspend signature 三处必须一致处理，同时保留旧低向量占位；这不等价于全局 WITH_CLASSIC_S2R=0。本轮主线已经选择集中关闭，不建议为了省去重建退回只删 panic 或把 token 设成假地址。

全局宏开关的实际消费者已对完整源码树搜索，范围如下：

| 文件与条件点 | 关闭后的直接影响 |
|---|---|
| arm64/cpu.c 的声明、签名常量、sleepTokenBuffer | 删除专用函数声明、两组八字节签名和静态 token 状态 |
| arm64/cpu.c 的 ml_arm_sleep | 删除写 suspend signature 和缺 token panic 的 classic 协议块；每 CPU 的 cpu_sleep_token 状态维护仍在 |
| arm64/cpu.c 的 cpu_machine_idle_init | 删除 token 检查、ml_vtophys、running signature 转换与八字节复制/flush；保留此前初始化及末尾 cpu_reset_handler 写入和 clean_dcache |
| arm64/cpu.c 的 sleep_token_buffer_init | 不再定义 stram 查找和 ml_io_map 函数 |
| arm/arm_init.c | 不再调用 sleep_token_buffer_init；其无条件 extern 声明本身不生成引用 |
| arm/cpu_data_internal.h | 仅删除条件 extern SleepToken[8] 声明，条件位于 cpu_data_t 结构结束之后 |
| arm64/genassym.c | arm64 下不再生成 stSize 和 stSize_NUM |
| arm64/start.s | 不再定义 SleepToken 标签及八字节 .space；后续启动符号位置必须重新核对 |

MONITOR=1 来自 typhoon.h，独立于 WITH_CLASSIC_S2R。当前 guard 没有关闭 monitor_call、ResetHandlerData 初始化、CPU 注册、FIQ、定时器或 PE 初始化。它也不会自动完成 Y35A 休眠或唤醒支持；其含义只是不用 Apple classic S2R token 协议。保留代码和功能已经能运行是两回事，后续运行能力仍由主线实验证明。

### 结构布局：已确认的事实与不能扩大声称的范围

需要纠正“全局关闭必然改变 cpu_data_t 布局”的潜在误解。当前 4903 的完整 WITH_CLASSIC_S2R 引用搜索中，没有用它包围 cpu_data_t 的字段。cpu_sleep_token 和 cpu_sleep_token_last 是无条件成员，不能因为名字相似而随 classic S2R 一起删除。reset_handler_data_t 也不以此宏控制成员。仅切换这一宏，静态源码上没有 cpu_data_t、cpu_data_entry_t、reset_handler_data_t 的成员增删依据。

R74b 机器码的 cpu_data 大小用途仍是 clean_dcache 长度 1280，cpu_reset_handler store 偏移为 256，current_processor 访问偏移为 128。这些是本代实际指令的观测，不是 C 分支重新编译得到的布局。此次没有做两配置编译对照，因此不能给新产物出具 ABI 已验证结论。

必然发生变化的是生成定义与链接内容：stSize 宏消失、SleepToken 的八字节存储消失、token 专用代码和常量消失。LowResetVectorEnd 后的入口及其他重链接 PC 可能变化；不能继续沿用旧 entry physical、固定偏移或旧反汇编门禁。start.s 的 `.global EXT(SleepToken)` 位于条件之外，关闭后必须检查对象及最终符号表是否遗留未定义声明或引用；本次静态读取不能替最终链接结果作保证。

本轮读取主线正在变化的 assym.s，观察到 stSize 已由先前的 8 消失，而 CPU_PROCESSOR_NUM=128、CPU_RESET_HANDLER_NUM=256、rhdSize_NUM=16 保留。该读取只证明当时文件内容，不是本分支执行 genassym 或完整重建的证明。读取时 assym.s SHA-256 为 be2b746ed1f68ecc3ae7ae2ea79513826a5e8d1cab6f5af2bba5c5bf60f23807。新 T7000.h 与当前 EXPORT_HDRS 对应头哈希均为 7a04d505c1c9b0584db95b64e49b97166e9efe06967508660545b603fa9ea591；cpu_data_internal.h 哈希为 01a4c7538ac3c5b0a182cf241c33c2e30d19c6c3bd50f478fbd62b0c09803ee8。

全局选择必须重生 genassym 并重编相关汇编、C/C++ 和驱动，这个要求成立的理由是配置一致性、导出头快照与链接布局发生变化，而不是已经证明 cpu_data_t 偏移改变。不得把旧 assym.s 或旧驱动对象混入新配置。

### 驱动头快照的具体风险与验收条件

只读检查真实成功目录 /private/tmp/arm-driver-4903-bjf1_fm_（ArmCpu）和 /private/tmp/arm-driver-4903-nxo5iqcw（ArmDTPlatform），两者的 consumed-inputs.json 均记录实际消费了旧 T7000.h、board_config.h、typhoon.h，哈希分别为 72def6bee859c13ee4d0335c05b035ee2c4d3265c52ee6022255292c82b151f4、cee1e2b61dab31063deedc94d3ba0af031fbcf6681ad75257f3ae2ec9270c6a3、93cd23d67632eec3505efc7b2f901a930daf4032de084f9db4ca2cc571f91342。其命令有 ARM64_BOARD_CONFIG_T7001，旧快照没有 XNU_Y35A_A53。

这两个已检查快照的 consumed-inputs.json 和 ArmCpu headers.d 未列 cpu_data_internal.h；因此不能声称它们已直接验证或固化完整 cpu_data_t 的布局。它们确实固化了板级宏和相关接口头。现有 abi-probe.cpp 只检查 IOCPU、IODTPlatformExpert、ml_processor_info_t 及注册签名，没有检查 sizeof(cpu_data_t) 或该结构字段偏移。既有 ABI 日志不能替代这次需要的布局对照。

现有 build_arm_driver_4903.py 从 generated IOKit Makefile 提取 CONFIG_DEFINES，再复制 EXPORT_HDRS 和生成头，不自动重放内核的 CFLAGS_EXTRA。读取时内核 osfmk .CFLAGS 已包含 -DXNU_Y35A_A53=1，但 IOKit Makefile 文本未含该宏。故即使刷新 T7000.h，若驱动编译命令未显式获得同一 guard，它仍会按头文件默认值选择 WITH_CLASSIC_S2R=1。这是已找到的配置传递缺口，主线需要在驱动重建时处理；本分支没有改构建器。

供主线验收新配置的最小项目：

1. 确认 C、C++、genassym、start 汇编与驱动的实际编译参数均使用同一 XNU_Y35A_A53 选择；不能只看源码 guard 或一个命令行片段。
2. 重新生成导出头、genassym/assym 与驱动独立快照，保存新 consumed-inputs 和完整命令。验证 stSize 的条件选择、CPU 数据关键偏移及接口 ABI，不复用旧日志声称已通过。
3. 在新 Mach-O 确认 cpu_machine_idle_init 的 token panic/复制路径和 arm_init 的 token 初始化调用消失，同时其余调用链与最终返回仍在；MONITOR 没有被意外改掉。
4. 重新从 Mach-O 导出入口、segments 和符号，核对 LowResetVectorBase、LowResetVectorEnd、_start、诊断向量与 carrier 的实际关系，检查 SleepToken 未定义引用。重包 boot/probe 并重算绑定哈希。
5. 运行时验收由主线完成：新鲜 R73IDL00 或更后阶段证明越过此前停点；仅没有新的 R74PAN01 不能证明修复成功，更不能证明休眠支持。

本次已重新验证 R74b 的直接证据和静态关闭范围；没有把主线进行中的构建或后续设备状态写成已完成结果。外部源码检索未返回内容，本节结论由本地版本、真实头快照和 R74b 封存机器码支撑。
