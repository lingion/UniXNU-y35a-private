# R70 C 入口独立审计，附 R71 实测核验

审计日期：2026年11月11日。执行者：本会话 C 核验分支。

结论：R70 封存机器码在 ARMINITE 与 PEINITEN 之间依次执行启动参数复制和 cpu_data_init。最早使用 SIMD 的实际指令是 **0xfffffff0072577b4，movi v0.16b, #0，指令字 0x4f00e400**。T7001 的 Watchtower 配置使进入 C 前的 CPACR 初始化被编译掉。审计期间主线提供 R71 结果后，本分支独立读取其 raw 和 Mach-O，确认新鲜 Y35ALV02 捕获的 ELR 正是此 PC，ESR=0x1fe00000，EC=7。因此“首条 SIMD 指令发生访问 trap”已由静态候选升级为 R71 真机实证。证据支持主线直接实施 A53 专用 CPACR 最小修复及一次配对验证，不再增加同类定位实验。

R70 本身没有这条异常记录，不能把 R71 的实测无标注地写成 R70 的实测。两代相关 C 代码逐字节相同，比较结果见下文。

## 范围与证据等级

本分支仅读取本地文件、使用 llvm-objdump、llvm-nm 和内存中的独立 Python 字节解析。没有构建，没有运行项目脚本，没有设备、容器、远端或外部 agent 操作。唯一写入是本文件，使用排他创建；没有修改 start、locore、arm_init、验证器、共享账本或记忆文件。

采用 systematic-debugging 的证据优先流程，并用 verification-before-completion 核验最终交付。三个验收条件是实际调用链有序可复核、候选 PC 与平台条件明确、实测与静态及未知分开。

“实证”指本分支从已封存的真机 raw 独立读取的数据，不表示本分支执行过设备实验。“静态”指封存产物和源码对应。“未知”指原始记录没有给出的状态。工作目录源码可随主线变化，R70 汇编依据封存的 inputs/start-after.s；绝不把当前 start.s 当作 R70 原件。

## 产物身份与地址换算

R70 根目录：[phase-r70-a53-no-apple-hid-20261111](/Users/lingion_k/unixnu-research/UniXNU-y35a/evidence/y35a-20261102/boot3-20261106/phase-r70-a53-no-apple-hid-20261111)。

| 产物 | 本次重新计算的 SHA-256 |
|---|---|
| kernel/kernel.macho 与 boot/kernel-packed.macho，均为 11,532,768 字节 | 03916ed78c7f6b1a2343427c9b450ae5b36ab36462507db924ac37540023c530 |
| boot/boot3.img | 4073ffa4848e9a388675abff745695249ee393d931bbc33fedf61947bf625e76 |
| readback-probe/readback-probe-not-xnu.img | cdc31e97b8a97b1100d6fddff575959e7fdc2f960ea55102e23bac94cc416c88 |
| baseline.raw | beb176eac4c4316110d5c3fe69d26e34c5d2bdd612fc958bc6df9af836bab4d1 |
| final.raw | 5126d9cdd30478fd81d7bbe766fe37ad6c7a62bce8baac8ef84b6a55f6155719 |
| inputs/start-after.s | 7675d2947f5a8b276fead575998793039f201b933911fa1564af0b3139dd8c84 |

独立逐字节比对确认：完整 kernel/kernel.macho 位于 entry.bin 偏移 0x4450，以及 boot3.img 偏移 0x4c50，两处均完全一致。这不仅是相信 manifest 中的哈希。

Mach-O 的 __TEXT 基址为 0xfffffff007004000；manifest 的物理基址为 0xa0004000。本文列出的 C 代码位于 __TEXT_EXEC，VM 起点 0xfffffff0070ec000，文件起点 0xe8000。该段内文件偏移为 PC - 0xfffffff007004000，物理位置为 PC - 0xfffffff007004000 + 0xa0004000。物理位置只是装载地址，不是进入高地址 C 后应报告的 ELR。

关键绑定：

| 内容 | 链接 VA / PC | 文件偏移 | 物理位置 | 四字节小端编码 |
|---|---|---|---|---|
| ARMINITE store | 0xfffffff007259884 | 0x255884 | 0xa0259884 | 0a 15 04 f9 |
| 参数复制 BL | 0xfffffff0072598d8 | 0x2558d8 | 0xa02598d8 | 5e f2 ff 97 |
| cpu_data_init BL | 0xfffffff0072598f0 | 0x2558f0 | 0xa02598f0 | a5 f7 ff 97 |
| 首条 SIMD MOVI | 0xfffffff0072577b4 | 0x2537b4 | 0xa02577b4 | 00 e4 00 4f |
| 紧随其后的 STUR Q0 | 0xfffffff0072577b8 | 0x2537b8 | 0xa02577b8 | 00 80 8e 3c |
| PEINITEN store | 0xfffffff007259918 | 0x255918 | 0xa0259918 | 16 19 04 f9 |

## R70 raw 实际能证明什么

依据 [readback.json](/Users/lingion_k/unixnu-research/UniXNU-y35a/evidence/y35a-20261102/boot3-20261106/phase-r70-a53-no-apple-hid-20261111/readback-probe/readback.json)，early-fault-record 的物理起点是 0xa0b94800，raw 起点是 0x10100；slot n 对应 raw 0x10100 + 8n。以下均按小端 64 位解析：

| 项目 | baseline | final | 解释 |
|---|---|---|---|
| raw 0x10008，shim kernel tag | 0x9ce25106ce653734 | 0x1a6b7f8cd76e9103 | final tag 与 R70 kernel 哈希前八字节一致 |
| raw 0x10048，probe kernel tag | 0x1a6b7f8cd76e9103 | 0x1a6b7f8cd76e9103 | 探针按 R70 产物生成 |
| slot 5，raw 0x10128 | 0x00000000a06e60d8 | 0x41524d494e495445 | 新出现的 ARMINITE 值，证明进入 arm_init 并执行其 marker store |
| slot 6，raw 0x10130 | 0xfffffff007b94800 | 0xfffffff007b94800 | 仍是旧用途指针值，既不是 PEINITEN，也不是零 |
| slot 12，raw 0x10160 | 0 | 0x30305445524d5241 | 新出现 ARMRET00，是准备返回进入 C 的标记 |
| fault slots 0、1、2 | Y35ALV01、0xa0270908、0x02000000 | 全零 | R69 记录不再保留；不是 R70 没有异常的证明 |

ARMRET00 写在 common_start 返回 arm_init 之前，不表示 arm_init 已经执行完毕。其 R70 store PC 是 0xfffffff007270924；之后 0xfffffff00727093c 将 VBAR_EL1 切到 LowExceptionVectorBase，0xfffffff007270940 执行 ISB，0xfffffff007270944 执行 RET。

ARMINITE 的正值不能单独证明紧跟的 DC CIVAC、DSB 已正常完成，更不能证明参数复制或 PE 初始化已完成。PEINITEN 缺失只能表述为没有保留下这个值。

## ARMINITE 到 PEINITEN 的有序实际路径

源码入口：[arm_init.c:227](/tmp/xnu4903-native-bqbvhqi_/src/osfmk/arm/arm_init.c:227)。marker 实现：[arm_init.c:90](/tmp/xnu4903-native-bqbvhqi_/src/osfmk/arm/arm_init.c:90)。

| 顺序 | 实际 PC | 实际行为及条件 |
|---|---|---|
| 1 | 0xfffffff007259840 至 0xfffffff007259880 | 建立 80 字节栈帧；x1 保存原始 args。读取 native_phase_args，非零则复用，零则设为当前 args。该静态变量 VA 为 0xfffffff0077a7750。 |
| 2 | 0xfffffff007259884、0xfffffff007259888、0xfffffff00725988c | STR 将 ARMINITE 写到原始 args + 0x828；随后 DC CIVAC 和 DSB SY。正确原始 args KVA 为 0xfffffff007b94000。 |
| 3 | 0xfffffff007259890 至 0xfffffff0072598a4 | 两组 ADRP/ADD 均生成 0xfffffff0070c7ff3，CMP 后 B.EQ 到 0xfffffff0072598c8。Mach-O 的 __TEXT,__thread_starts 实际大小为零。 |
| 4 | 0xfffffff0072598c8 至 0xfffffff0072598d8 | x0=0xfffffff0070ce570，即 const_boot_args；x1 仍为原始 args；w2=384。BL 0xfffffff007256250。此地址同时属于 memcpy 与 memmove，objdump 标签选择 memmove。 |
| 5 | 0xfffffff007256250 至返回 | 参数复制只用通用寄存器，不调用其他函数，不用 NEON，不访问 Apple HID 或 CPACR。按预期不重叠的地址走正向大块复制。首条源 LDP 在 0xfffffff007256278，首条目标 STP 在 0xfffffff007256298。 |
| 6 | 0xfffffff0072598dc、0xfffffff0072598e0 | 向 BootArgs 全局（VA 0xfffffff0070ce6f0）写 const_boot_args 指针。 |
| 7 | 0xfffffff0072598e4 至 0xfffffff0072598f0 | 生成 BootCpuData 地址 0xfffffff007763da0，传入 x0，BL 0xfffffff007257784，即 cpu_data_init。 |
| 8 | 0xfffffff007257784 至 0xfffffff0072577b0 | cpu_data_init 先进行标量字段清零和 RTClockData 地址写入；没有子调用、MRS、MSR 或 Apple 实现寄存器访问。 |
| 9 | 0xfffffff0072577b4 | MOVI V0.16B,#0，首条 SIMD 指令。下一条 0xfffffff0072577b8 是 STUR Q0,[X0,#232]。后续还有 Q/D 寄存器存储和第二条 MOVI；不能将这些普通结构清零视为“没有浮点操作”。 |
| 10 | 0xfffffff007257868 至 0xfffffff007257874 | 得到 exc_vectors_table 地址，写入 BootCpuData+248，RET。此处只写字段，不是安装 VBAR，也没有初始化 TPIDR_EL1。 |
| 11 | 0xfffffff0072598f4 至 0xfffffff007259914 | 重新读取 native_phase_args。正常情况下仍指向原始启动参数，因此 marker 不随 args 变量切到 const_boot_args。 |
| 12 | 0xfffffff007259918、0xfffffff00725991c、0xfffffff007259920 | 写 PEINITEN=0x5045494e4954454e 到原始 args+0x830，再 DC CIVAC、DSB SY。 |
| 13 | 0xfffffff007259934 | 才执行 BL PE_init_platform，目标 0xfffffff0076bd73c，w0=FALSE，x1=const_boot_args。它在本次区间的结束 marker 之后。 |

实际正常链只有两次区间内 BL：memcpy/memmove，然后 cpu_data_init。两者都没有递归子调用。bzero、cpu_init、cpu_bootstrap、rtclock_early_init、ml_parse_cpu_topology 和 Apple HID 初始化不在此区间内。

JOP 源码仍存在，但本产物的正常路径不会进入重定位循环。不能只根据 arm_init.c 中出现 rebase_threaded_starts 就把它列为已经执行的调用；它已被内联，且被上述相等地址分支跳过。

cpu_data_init 的正确源文件是 [osfmk/arm64/cpu.c:531](/tmp/xnu4903-native-bqbvhqi_/src/osfmk/arm64/cpu.c:531)，不是同名的 osfmk/arm/cpu.c。生成的 cpu.d 第一条依赖明确指向 arm64/cpu.c。源中的普通字段清零及循环被编译成 SIMD 写入；不应把 MOVI 精确归到某个单独 C 赋值。结尾 cpu_exc_vectors 赋值受 __ARM_KERNEL_PROTECT__ 控制，位于 cpu.c:593。

独立比较现有 cpu.o 与封存函数：cpu_data_init 在 object 内偏移 0x83c，首条 MOVI 为函数+0x30，编码与链接产物一致。完整函数的不同字节仅落在 object 的 0x854、0x858、0x920、0x924 四条带重定位的指令内；llvm-objdump -r 将前两处绑定 RTClockData，后两处绑定 exc_vectors_table。这与最终链接的地址重定位和指令松弛一致。

## T7001 宏、CPACR 缺口及剩余 Apple 访问

宏链有源码与产物双重依据：

1. [R70 experiment.json](/Users/lingion_k/unixnu-research/UniXNU-y35a/evidence/y35a-20261102/boot3-20261106/phase-r70-a53-no-apple-hid-20261111/experiment.json) 记录 MACHINE_CONFIGS=T7001、KERNEL_CONFIGS=DEVELOPMENT。[MakeInc.def:55](/tmp/xnu4903-native-bqbvhqi_/src/makedefs/MakeInc.def:55) 将 T7001 转成 ARM64_BOARD_CONFIG_T7001。
2. [board_config.h:37](/tmp/xnu4903-native-bqbvhqi_/src/pexpert/pexpert/arm64/board_config.h:37) 为 T7001 定义 APPLE_ARM64_ARCH_FAMILY、APPLETYPHOON、KERNEL_INTEGRITY_WT=1，以及 CPU_COUNT=3 等 Apple 板级假设。这不是按真机 MIDR 自动选择 A53。
3. [MASTER.arm64:64](/tmp/xnu4903-native-bqbvhqi_/src/config/MASTER.arm64:64) 将 kernel_integrity 纳入 SECURITY，DEVELOPMENT 纳入 SECURITY，86 行定义 CONFIG_KERNEL_INTEGRITY。现有 osfmk/DEVELOPMENT/Makefile 的 CONFIG_DEFINES 也实际包含 -DCONFIG_KERNEL_INTEGRITY。
4. [R70 封存 start-after.s:1382](/Users/lingion_k/unixnu-research/UniXNU-y35a/evidence/y35a-20261102/boot3-20261106/phase-r70-a53-no-apple-hid-20261111/inputs/start-after.s:1382) 仅在 !CONFIG_KERNEL_INTEGRITY，或已启用完整性但没有定义 KERNEL_INTEGRITY_WT 时执行 CPACR 初始化。本配置条件为假。注释明确假定 Watchtower 会负责开启它。
5. 初始化常量来自 [arm64/proc_reg.h:294](/tmp/xnu4903-native-bqbvhqi_/src/osfmk/arm64/proc_reg.h:294)：FPEN 位移 20，CPACR_FPEN_ENABLE 为 3<<20，即 0x00300000。
6. R70 排除 HID 的补丁只改 start.s 的两个条件；XNU_Y35A_A53 只出现在该轮 SFLAGS_ARM64 参数中。它没有改变 T7001 的完整性条件，也没有为 C 代码建立 A53 配置。

实际指令检查：R70 common_start 在 SCTLR 之后的诊断 store/barrier 完成后，0xfffffff007270900 直接 MOV X0,#0，0xfffffff007270904 写 TPIDR_EL1。其间不存在 CPACR MSR。从 start_first_cpu 到 cold RET、唯一调用的 set_mmu_ttb，以及到 PEINITEN 为止的 C 路径，都没有 CPACR 读写。封存 boot/entry.elf 的实际 shim 代码 0x80080040 至 0x8008017c 也未配置 CPACR 或 CPTR。因此“封存 shim/kernel 已保证 C 可以使用 NEON”没有成立；不能依赖不存在的 Watchtower 契约。

FPEN 为 00 或 10 时，EL1 的此类 FP/SIMD 访问会被禁止；01 允许 EL1、限制 EL0，11 同时允许 EL0/EL1。本程序原先希望写入 11。R70/R71 后续探针读到 CPACR=0，只能描述探针当次执行状态，不能当作进入 C 时的实时采样。R71 观察到 EC=7，则直接证明当前失败是 FP/SIMD 访问 trap；该指令只生成向量常量，不访问内存，因此不能把 FAR=0 解释为访问空指针。CPACR 的故障瞬间完整数值尚未采样，但这不妨碍针对已经证实的初始化遗漏做最小修复。

区间内没有新的 Apple 专用 MRS/MSR。区间之后仍有真实的条件化 Apple 访问：[arm_init.c:304](/tmp/xnu4903-native-bqbvhqi_/src/osfmk/arm/arm_init.c:304) 在 APPLETYPHOON 下解析 cpus_defeatures；调用 PC 为 0xfffffff007259a08。函数内部进一步只对低四位等于 1 或 2 执行 HID 操作，其他非零值也会直接返回。等于 1 的第一条 HID0 MRS 在 0xfffffff007273d9c；等于 2 在 0xfffffff007273e50，编码均为 S3_0_C15_C0_0。源码对应 [machine_routines_asm.s:1093](/tmp/xnu4903-native-bqbvhqi_/src/osfmk/arm64/machine_routines_asm.s:1093)。R70 boot-args.bin 的命令行是 cpus=1 debug=0x8 rd=md0，不包含 cpus_defeatures；这里的 cpus=1 不能混同于 cpus_defeatures=1。

APPLETYPHOON 还定义 __ARM_V8_CRYPTO_EXTENSIONS__、__ARM_COHERENT_IO__、__ARM_IC_NOALIAS_ICACHE__ 和 __ARM_KERNEL_PROTECT__，见 [arm/proc_reg.h:115](/tmp/xnu4903-native-bqbvhqi_/src/osfmk/arm/proc_reg.h:115)。这些是后续移植审计项；它们不是本区间已经执行的额外 Apple 访问，也不能据此宣称六组 HID 排除已经完成所有 A53 适配。

## 候选 PC 与 R71 实证更新

在 R71 raw 到达前，最有针对性的静态候选是首条 MOVI，但更早的数据访问仍需保留为候选；这些候选不能由 retained 零值排序成唯一根因。

| R70 PC | 触发条件 | 原先可区分的异常 | R71 后的判断 |
|---|---|---|---|
| 0xfffffff007259888 | marker 地址对应的 cache maintenance 访问出错或受限制 | 依实际 syndrome 区分 | R71 捕获在后面的 MOVI，不能继续把这里作为该次停止点 |
| 0xfffffff007256250、0xfffffff007256278、0xfffffff007256298 | 栈、原始 args 读取或 const_boot_args 写入的映射/权限等不满足 | 数据异常或栈对齐异常 | 同上；零副本没有推翻先前执行 |
| 0xfffffff0072598e0、0xfffffff007257784 | BootArgs 全局或 BootCpuData 首次字段写不可用 | 数据异常 | 同上 |
| **0xfffffff0072577b4** | 首条 SIMD 指令遇到 FP/SIMD 访问禁用 | **EC=7** | **R71 新鲜 ELR 与 EC 精确命中** |
| 0xfffffff0072577b8 | 若 MOVI 已通过，向量存储地址/权限等出错 | 通常应检查数据异常 syndrome | 本次 ELR 在前一条，没有证据将其归为向量存储 fault |
| 0xfffffff007259918、0xfffffff00725991c | marker carrier store 或维护失败 | 按 syndrome 判断 | 本次尚未到达；R70 单凭缺失值仍不能定位于这里 |

此处 EC 命名也能与本地 XNU 定义交叉核对：[arm64/proc_reg.h:1240](/tmp/xnu4903-native-bqbvhqi_/src/osfmk/arm64/proc_reg.h:1240) 定义 ESR_EC_TRAP_SIMD_FP=0x07；EC=0x18 是不同的系统寄存器 trap，EC=0 是 R69 HID 未定义类，不能混写。

## R71 追加核验：从候选到实证

本节依据用户最新授权，只读读取 [phase-r71-c-vector-v2-20261111](/Users/lingion_k/unixnu-research/UniXNU-y35a/evidence/y35a-20261102/boot3-20261106/phase-r71-c-vector-v2-20261111)。没有重复设计、修改或运行向量。

| R71 产物 | 本次重新计算的 SHA-256 |
|---|---|
| kernel/kernel.macho 与 boot/kernel-packed.macho，11,532,808 字节 | f8b6927d38d63864b01c07f2e61a99a7a77bde47b1ef69f2b1658a66d6a2c564 |
| boot/boot3.img | fc408ad024f516b36602b0c75910a609418c583525447ff04bcfc38e92b730cc |
| readback-probe/readback-probe-not-xnu.img | c948c5f7c20f4d5e6d2ad9adf8fe9e45f1986dbe780b3f75509812a4a1758aa6 |
| baseline.raw | ab4b93929450a6ce2d0a70a3fbcf60d7615013f0c1a0e330eee83695a2dc97ae |
| final.raw | c732b131650e994fbd850d710caeea0c4e498a26fef764188d0550e44bbe764c |

R71 boot3.img 偏移 0x4c50 处的完整内核亦与 kernel/kernel.macho 逐字节相同。

独立解析 baseline/final：raw 0x10100 从 0 变为 0x3230564c41353359，即字节串 Y35ALV02；0x10108 从 0 变为 0xfffffff0072577b4；0x10110 从 0 变为 0x1fe00000。ESR 解码为 EC=7、IL=1、ISS=0x1e00000；0x10118 的 FAR=0。final 的 shim/probe tag 同为 0x6438d6387d92b6f8，与 R71 kernel 哈希相符；baseline 的 shim tag 仍为 R70。R71 的 ARMINITE、ARMRET00 在 baseline 已存在，不能将这两个未变化值算为 R71 新鲜执行证据；本次新鲜证据是 Y35ALV02 及其 syndrome。

R71 实际记录器在 0xfffffff00726f814、0xfffffff00726f818 分别读取 ELR_EL1、ESR_EL1，向立即数构造的 0xa0b94800+8/+16 存储；在 syndrome 之后才写 Y35ALV02。故上述字段是异常状态，而非 report 页中的探针寄存器采样。记录器虽把 SPSR_EL1 读入 x27，但当前这段记录没有将其写出；不声称 raw 保存了 SPSR 或 CPACR。

逐字节验证以下 R70/R71 半开区间完全相同：

| 区间 | 含义 | 区间字节 SHA-256 |
|---|---|---|
| 0xfffffff007259840 至 0xfffffff007259938 | arm_init 入口至 PE 调用之后 | 04e312d401b2a37923477ca1fd79e9a83e7cb2c2a48f75daacd92216da8ac689 |
| 0xfffffff007256250 至 0xfffffff0072563fc | memcpy/memmove 全实现 | 9c27385f291628c7f64a0b3f90c57ae8bdbe39a73e692c8fb6afe238ffefd0fb |
| 0xfffffff007257784 至 0xfffffff007257878 | cpu_data_init 全函数 | 80a6e5ed686f740a0c0cd5b763501bb9d8985a95f8ad088470b5b7d872e6199d |

因此这一次能使用相同 PC，依据是实际字节相等，不能推广为以后重链接地址都相同。

特别重要：R71 final 中 raw 0x10280 的 BootArgs 指针仍为零，0x10300 起的 384 字节 const_boot_args 副本也仍全零。正常冷启动实际链到达 cpu_data_init 的首条 MOVI 前，已经经过 memcpy 返回及 BootArgs 全局 store。这提供了本轮直接反例：后来保留内存中的零值，不能唯一定位执行停在复制或指针赋值之前。缓存保留、复位过程、采样映射或其他读回条件中的具体原因尚未确定，本分支不替其编造解释。

## 主线可直接采用的下一步及证伪条件

R71 已完成对首条 SIMD trap 的定位。无需再做一次相同条件的纯观测。建议主线按既定计划，仅针对 A53 路径在首条 C SIMD 之前显式开放 CPACR_EL1.FPEN，并执行 ISB；使用现有 CPACR_FPEN_ENABLE=0x00300000，保留其他 CPACR 位时可读改写。该 A53 路径必须绕开“Watchtower 已替本机配置”的编译期假设，而不是仅继续排除 HID。此建议不要求全局关闭 CONFIG_KERNEL_INTEGRITY，也不涉及 MMU 修改。

修复候选以自身最终 Mach-O 验证实际 CPACR MSR、值和 ISB 位于进入 C 前；不能仅验证源码宏或镜像中任意位置存在 MSR。保持已经可用的 R71 terminal observer。该步骤由主线负责，本分支不修改或操作。

一次配对验证的判据：

- 若首个新鲜异常不再是对应 MOVI 的 EC=7，且出现新鲜 PEINITEN、PEINITRT 或更后面的可归属证据，则原先 FP/SIMD 阻塞已被跨越。
- 若仅命中新的更后方 ELR，也应准确报告已越过首条 SIMD、接下来在哪条指令失败；不能要求一次修复同时证明整个 iOS 启动。
- 若新产物仍在相应 MOVI 捕获 EC=7，则“修复路径已经有效开放 EL1 FP/SIMD”被证伪，应核对实际到达的 CPACR 写入和值、是否被改回及 trap 配置。若没有新鲜记录而标记也缺失，结论是无有效进展证据，不能凭零值宣告修复失败于某条 PC。

故障时 CPACR 的完整值未保存在 R71 raw，这是范围明确的未知；已经有准确的首条 SIMD 指令和 EC=7，以及对应的初始化遗漏，不应拿这个未知继续阻塞最小修复。

## 源码版本绑定与复核方式

以下为审计时读取的源码 SHA-256。它们是解释封存机器码的辅助证据，并非声称整个可变工作树与 R70 构建时逐文件一致：

| 源码，相对 /tmp/xnu4903-native-bqbvhqi_/src | SHA-256 |
|---|---|
| osfmk/arm/arm_init.c | b7b3a1710701d534697e9665d600a87a1853d0429ecc3029f4eb9c942758cad7 |
| osfmk/arm64/cpu.c | 143ab7c450cd33797910ca68e4f6ea14418bacb71e578a82fc51735a876e194f |
| osfmk/arm64/bcopy.s | e01aa92db4f9f283e250103e7d20a935e9a707a18cb5d6e4a3b518c3440f7c22 |
| osfmk/arm/proc_reg.h | f784601b6c893bde2006196bd65ad16812d889b6d7a6e85561809d955b0aeffe |
| osfmk/arm64/proc_reg.h | d3bfc31e00b57a55a19345586dd7608f38f6ed57e5c4af89f4548a13c7570622 |
| pexpert/pexpert/arm64/board_config.h | cee1e2b61dab31063deedc94d3ba0af031fbcf6681ad75257f3ae2ec9270c6a3 |
| config/MASTER.arm64 | 46916249a0f598ca811b82fecc275b40e30c1aec44a3449c159049fe16f1bdba |

复核使用 Xcode 自带 llvm-objdump 对指定起止地址进行反汇编，使用 llvm-nm 确定符号边界；另以 Python struct 解析 Mach-O LC_SEGMENT_64、节大小、原始指令字、raw 小端值及 hashlib SHA-256。参数复制与 cpu_data_init 的结论均检查了完整函数，没有只凭源码函数名推断。

关键复核命令形式如下，K 应指向上表某一代已经核对哈希的 kernel/kernel.macho：

    xcrun llvm-objdump -d --start-address=0xfffffff007259840 --stop-address=0xfffffff007259938 "$K"
    xcrun llvm-objdump -d --start-address=0xfffffff007256250 --stop-address=0xfffffff0072563fc "$K"
    xcrun llvm-objdump -d --start-address=0xfffffff007257784 --stop-address=0xfffffff007257878 "$K"

本轮没有重跑项目检查器、测试或构建，不将历史 gate 标记当作本分支重新执行过的验证。架构在线检索没有返回可引用正文；寄存器和异常命名交叉依据本地 Apple XNU 原始定义及实际 syndrome，未声称完成新的 Arm 文档逐页认证。

## 用户要求与交付核验

| 用户要求 | 实际交付 |
|---|---|
| 以封存 kernel 实际机器码为 authority | 重新计算两代完整 SHA，并核对 boot3 内嵌内核逐字节相同；PC、文件偏移、指令字列出 |
| 有序实际调用链 | 给出 marker、条件分支、复制、cpu_data_init、PE marker 与后续 PE 调用，明确空 JOP 节 |
| T7001 Apple 访问、CPACR、NEON 缺口 | 宏链、编译消除条件、无 CPACR 的实际 cold path、首条 SIMD 和后续条件化 HID 分开说明 |
| retained 零值不能唯一定位 | 明确 slot6 是残留指针；R71 MOVI fault 与零 BootArgs/副本形成直接交叉证据 |
| 候选精确 PC、条件与可证伪下一步 | 表列原候选，并用 R71 实证收敛到 FP/SIMD trap；给出最小修复及验收条件 |
| 唯一允许写入本文件 | 使用排他创建，其余审计操作只读；没有设备、构建、项目脚本或外部 agent 操作 |

## 后续交付：R72 闭环与终止异常 decoder

本节记录用户随后授权的实现阶段。上文“没有重跑测试”“唯一写入本文件”只描述最初只读审计阶段；后续授权允许新增 decoder 和测试，最终本分支写入范围只有本审计文档、scripts/y35a/decode_terminal_fault.py 和 tests/test_terminal_fault_decoder.py。没有修改主验证器、start、locore、arm_init，也没有设备、容器、远端或构建操作。

R72 封存 final.raw 的独立 SHA-256 检查得到 862e5cd171bff210663e41ee92d6b0be27468e6a165cffd10602b911e77f0da9。按 readback.json 中 name 为 early-fault-record 的记录定位，slot0 至 slot3 均为零；slot6 至 slot10 相对同轮 baseline 新鲜出现 PEINITEN、PEINITRT、ARMVMINI、PANICINI、CONSOLE。这满足上文“跨越首条 SIMD 停点并出现后续标记”的可证伪判据。PANICINI 是 panic 初始化检查点，不是发生 panic 的证据。本分支据此结束 C 入口阻塞审计，不将后续启动完成与否纳入结论。

新增 [decode_terminal_fault.py](/Users/lingion_k/unixnu-research/UniXNU-y35a/scripts/y35a/decode_terminal_fault.py) 按记录名称获取偏移，不固定假设 carrier 在 raw 0x10100。它复用既有只读验证函数检查 kernel 完整 SHA、probe 完整 SHA、raw probe kernel tag；minimal-boundary 最终捕获另检查 shim kernel tag。baseline 必须与同轮 probe 的 kernel tag 匹配，但其前次启动 shim tag 允许保留旧代内核。哈希和短 tag 用于产物关联，不构成设备执行的密码认证。

支持 Y35ALV01、Y35ALV02、Y35ALV03，均只将前四个 64 位字段解释为 magic、ELR、ESR、FAR。v3 的 PC 相对 carrier 和高 VA VBAR 安装不改变解码结构。slot13 的 R73 附加阶段链不实现、不解释为 syndrome。另行输出的 phase_markers 仅限 slot5 至 slot10，独立于异常分类。

分类约定如下：全零四字段为 missing；未提交或不完整字段为 partial；未知 magic 为 unsupported；缺 baseline 的完整记录为 unverified；与 baseline 四字段相同为 unchanged；相同 magic 下 payload 变化为 changed，freshness 为 ambiguous，因为不能排除旧提交标记下的部分新写入；提交 magic 相对完整 baseline 更新的有效记录才判 fresh。缺失终止记录不意味着没有异常，更不意味着启动或 iOS 完成。无法映射 ELR 时保留原值和 unmapped 原因，不猜指令或符号。

高 ELR 直接按 Mach-O segment 映射；低 ELR 必须有 boot 或 probe manifest 明确给出的虚拟与物理基址，两者都存在时必须一致。仅接受文件实际覆盖的可执行代码节，指令字直接读取 kernel 字节。符号为同一代码节内最近定义符号，明确不保证完整函数范围；可选 llvm-objdump 只负责显示，并核对输出字节。ESR 输出 EC、ISS、IL；FAR 仅在受支持的 abort 类别和 fault status 且 FnV 允许时作为地址。EC0 和 EC7 的 FAR 永远只保留原值。

命令示例在仓库根目录执行，JSON 输出到标准输出，不写 evidence：

```sh
phase=/Users/lingion_k/unixnu-research/UniXNU-y35a/evidence/y35a-20261102/boot3-20261106/phase-r71-c-vector-v2-20261111
PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/y35a/decode_terminal_fault.py \
  --kernel "$phase/kernel/kernel.macho" \
  --manifest "$phase/readback-probe/readback.json" \
  --probe "$phase/readback-probe/readback-probe-not-xnu.img" \
  --raw "$phase/final.raw" --baseline "$phase/baseline.raw"
```

可选 --boot-manifest 提供绑定同一 kernel SHA 的显式映射基址；--no-disassembly 禁用外部反汇编显示而保留原始指令字。退出码 0 只表示 fresh、产物关联成立且实际指令映射成功的终止异常已解码，绝不是成功启动；其他分类退出码均为 1。

对封存实物执行 CLI，结果如下：

| 轮次 | 状态与退出码 | 实际解码结果 |
|---|---|---|
| R69 | fresh，0 | 物理 ELR 0xa0270908 映射 0xfffffff007270908，指令字 0xd538f40c，MRS x12, S3_0_C15_C4_0，EC0，FAR 不作为地址 |
| R70 | missing，1 | 没有终止记录；ARMINITE 相对 baseline 新鲜 |
| R71 | fresh，0 | ELR 0xfffffff0072577b4，_cpu_data_init+0x30，0x4f00e400，MOVI v0.16b,#0，EC7，FAR 不作为地址 |
| R72 | missing，1 | 没有终止记录；PEINITEN、PEINITRT、ARMVMINI、PANICINI、CONSOLE 均新鲜 |

[test_terminal_fault_decoder.py](/Users/lingion_k/unixnu-research/UniXNU-y35a/tests/test_terminal_fault_decoder.py) 包含 28 项测试，使用临时合成 Mach-O 和捕获数据，并只读重放 R69 至 R72。覆盖错 kernel/probe/tag、缺 baseline、旧记录、相同提交下 payload 变化、部分记录、未知 magic/EC、不可映射 ELR、错误基址、畸形 Mach-O/manifest、FAR 保守判定、v3 四字段兼容和 slot13 不参与解析。v3 使用合成夹具验证，本节不声称验证过 R73 真机结果。新增测试曾实际暴露 boot manifest 非字符串 SHA 引发 AttributeError；加入类型校验后返回结构化 invalid，红绿验证已完成。

最终执行的纯离线回归命令：

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=tests:scripts/y35a python3 -B -m unittest \
  test_terminal_fault_decoder test_readback_manifest_integrity \
  test_phase_instrumentation_contract test_capture_format \
  test_capture_layout test_verify_readback_transport
```

实际结果为 78 tests，OK，没有跳过。未运行含编译、仓库创建或设备操作的全量测试套件，也未把主线的独立测试计为本分支执行结果。
