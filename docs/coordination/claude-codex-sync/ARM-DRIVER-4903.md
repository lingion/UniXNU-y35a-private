# 4903 平台驱动独立编译交接

当前交付以文末 R75 与 ArmCpu 自检修正章节为准。主代理报告 R75 已进入 machine_startup，正在独占处理 IOKit platform 匹配和内核链接。本侧线只处理 ArmCpu；ArmDTPlatform 对象已备好供主代理使用。早期目录仅保留为历史对照，不能无条件链接到其他配置。当前仍仅完成对象编译与静态核验。

本侧线于 2026 年 11 月 11 日完成 ArmDTPlatform 对象编译。完整本地 ArmDTPlatform 源码只在独立副本中应用所有权补丁，使用真实 XNU 4903.270.47 头文件编译成功。ArmCpu 的原始编译仍失败；后续新增显式启动核模式的 4903 兼容对象，结果和边界见下文新增章节。没有进行内核链接、真机测试或完整 iOS 启动验证。

第一阶段收到的主线状态为首次进入 arm_init C、尚未取得 PE marker。后续主代理报告 R71 已定位 cpu_data_init 中 MOVI 触发 EC7，R72 正验证 CPACR 修复。本侧线没有重复测量它。ArmDTPlatform 属于后续 IOKit 平台匹配阶段，本产物不能证明早期 PE 初始化已通过。

## 文件和产物

仓库根目录为 `/Users/lingion_k/unixnu-research/UniXNU-y35a`。

| 新文件 | 用途 |
| --- | --- |
| `scripts/y35a/build_arm_driver_4903.py` | 只读现有 4903 构建树，创建全新独立快照，编译并审计对象，保留成功及失败日志。 |
| `patches/arm-driver-4903/0001-armdt-ownership.patch` | 将 ArmDTPlatform 的 OSSharedPtr 换为 4903 的真实原始指针接口，并匹配 retain/release 生命周期。 |
| `patches/arm-driver-4903/abi-probe.cpp` | 用真实头文件检查 Darwin 版本和 CPU 注册函数签名，输出结构大小和字段偏移。此对象不进入驱动归档。 |
| `tests/test_arm_driver_4903.py` | 对象格式、配置参数、输出隔离、头文件来源及真实编译回归检查。 |
| 本文 | 验证结果、准确边界及主代理集成条件。 |

ArmDTPlatform 第一阶段成功目录为 `/private/tmp/arm-driver-4903-nxo5iqcw`。这是临时产物，不是设备证据目录，也没有接入现有构建流水线。

| 产物 | SHA-256 |
| --- | --- |
| `ArmDTPlatform.o` | `456a65c544716bfead5ac6ebc62b9e3778bb105834ba6a7c757596220750b1bf` |
| `libArmDTPlatform.a` | `22a7fc2b66c2019a4cfd9f6e467be43b72eaf8d71bbe1284744b9273705c9b48` |
| `abi-probe.o` | `ffc11d5d1e97a42b146aebb06dff54a50afad9fd298a95005e404e53b52ee364` |

对象在多次全新目录构建中哈希相同；归档由本地 ar 创建，成员时间等元数据会改变归档哈希，不宣称归档逐字节可重复。

`manifest.json` 记录结果、工具链、符号需求及命令日志位置。`inputs.json` 记录源输入与快照哈希；`consumed-inputs.json` 和 `headers.d` 记录驱动编译实际读取的 272 个输入，全部位于独立目录内。`compile-command.json` 保存完整编译参数，`compile.log` 为空。`abi-probe-command.json`、`abi-probe-layout-command.json`、`undefined-symbols-command.json` 等保留实际执行命令及工作目录。

原始 ArmDTPlatform 失败对照在 `/private/tmp/arm-driver-4903-rgfmssdd`。ArmCpu 原始失败诊断在 `/private/tmp/arm-driver-4903-ja8q6wcm`。最终版本的自动红绿编译对照在 `/tmp/arm-driver-4903-test-py9orf6y/baseline` 和 `/tmp/arm-driver-4903-test-py9orf6y/patched`。

## 实际执行与结果

以下命令工作目录均为仓库根目录。只使用本地编译器、文件和符号工具。

```sh
PYTHONDONTWRITEBYTECODE=1 ARM_DRIVER_4903_NATIVE_BUILD=/tmp/xnu4903-native-bqbvhqi_ python3 -m unittest discover -s tests -p test_arm_driver_4903.py -v
python3 scripts/y35a/build_arm_driver_4903.py --kernel evidence/y35a-20261102/boot3-20261106/phase-r70-a53-no-apple-hid-20261111/kernel/kernel.macho
python3 scripts/y35a/build_arm_driver_4903.py --baseline
python3 scripts/y35a/build_arm_driver_4903.py --component ArmCpu
```

第一条完成 10 项测试，没有跳过，其中真实编译回归验证原版失败、补丁版成功和原始驱动文件哈希不变。第二条退出 0，得到上列最终成功目录。第三条退出 1，准确报告 OSSharedPtr 和 OSNoRetain 不存在。第四条是第一阶段旧入口执行记录，当时退出 1，保留 ArmCpu 的完整编译错误。当前入口必须以 `--component ArmCpu --baseline` 重放这个原版失败对照；适配编译必须显式传入 `--boot-cpu-only`。后两条失败是诊断结果，不是可用驱动。

额外实际运行了 `xcrun nm -g`、`xcrun otool -l` 查看对象，使用 `xcrun otool -s __TEXT __const` 读取 ABI 探针，使用 Python ast.parse 检查两个新增 Python 文件语法。只运行本侧线的定向测试，没有运行可能涉及设备或主线构建的全仓库测试。

编译器是 Apple clang 14.0.3，实际目标参数是 `-target arm64-apple-ios12.4`，使用 `-std=gnu++17 -fapple-kext -mkernel -mgeneral-regs-only -fno-exceptions -fno-rtti -O2 -Wall -Wextra -Werror`。Apple 原始头文件通过 `-isystem` 引入，驱动自身警告仍作为错误。Mach-O 审计确认 arm64 subtype 0、MH_OBJECT 和 iOS 12.4 的 LC_BUILD_VERSION；没有使用 arm64e、iOS 17 对象或伪造 IOKit 类定义。

## 来源和兼容修改

读取的 XNU 源码为 `/tmp/xnu4903-native-bqbvhqi_/src`，Git 基线提交为 `494ffe1c29d37ca720c37328feb83069c9641b67`，对应 xnu-4903.270.47。该工作树已有主线补丁，提交号只标识上游基线。实际头文件内容以独立快照及哈希为准。脚本验证 MasterVersion 为 18.7.0，ABI 探针再以真实 version.h 编译验证 Darwin 18.7。

已有 `scripts/build-arm-driver.py` 从 `build/xnu/ios-obj/DEVELOPMENT_ARM64_BCM2837/iokit/DEVELOPMENT/IOPlatformExpert.cpo.json` 重放 10063 构建记录，并强制检查 iOS 17 部署版本。它没有被修改。仓库 patches、相关脚本及本地驱动中没有找到可以直接使用的 4903 ArmDTPlatform 所有权补丁。现有 `patches/xnu/armvirt-platform-personality.patch` 可供集成时参考匹配逻辑，但本侧线没有向 4903 内核应用它。

新入口读取已生成的 DEVELOPMENT_ARM64_T7001 IOKit Makefile 中 CONFIG_DEFINES，保留 IOKITSTATS、IOTRACKING 等实际配置。不能简单用 shlex 重放 `.CFLAGS` 文件：该文件丢失了带空格宏值的引号，CONFIG_NMBCLUSTERS 会被拆成额外输入文件。本入口读取仍保留引号的 Makefile 行，且仅接受 -D 参数，不执行 Makefile。

ArmDTPlatform 补丁没有引入名为 OSSharedPtr 的仿制类型。IOMemoryDescriptor::withPhysicalAddress 返回的所有权在 map 调用后释放；成功映射由平台对象持有，替换映射时释放旧映射，在 free 中释放最终映射，然后调用真实父类 free。失败路径不泄漏新 descriptor。原有 DT 校验、设备节点发布和诊断复位行为保留。父类布局和虚函数直接来自 4903 头文件。

## 符号和 ABI

ArmDTPlatform 对象有 232 个未定义符号，完整列表见成功目录的 `undefined-symbols.log` 和 manifest。它们全部存在于指定 R70 内核的全局已定义符号表中。比较对象为：

```text
evidence/y35a-20261102/boot3-20261106/phase-r70-a53-no-apple-hid-20261111/kernel/kernel.macho
SHA-256 03916ed78c7f6b1a2343427c9b450ae5b36ab36462507db924ac37540023c530
```

主要依赖包括 IODTPlatformExpert、IOPlatformExpert、IOService、IORegistryEntry、OSMetaClass、OSData、IOMemoryDescriptor 的构造函数和虚函数，以及 IOLog、PE_parse_boot_argn、gIODTPlane、gIOServicePlane、memcmp、strcmp。大量继承虚函数表项同样产生链接需求。符号名称齐备不等于内核已链接该驱动，也不证明 KPI 导出许可、虚表布局或运行时状态正确。

ABI 探针使用与驱动相同的真实头文件和配置，arm64 下输出如下。偏移单位为字节。

| 项目 | 数值 |
| --- | --- |
| sizeof(IOCPU) | 184 |
| sizeof(IODTPlatformExpert) | 240 |
| sizeof(ml_processor_info_t) | 144 |
| cpu_id 偏移 | 0 |
| phys_id 偏移 | 104 |
| log_id 偏移 | 108 |
| cluster_id 偏移 | 116 |
| cluster_type 偏移 | 120 |

真实 CPU 注册签名通过编译期检查：

```cpp
kern_return_t ml_processor_register(
    ml_processor_info_t *, processor_t *, ipi_handler_t *,
    perfmon_interrupt_handler_func *);
```

ArmCpu 原始编译的独立根因是 OSSharedPtr/OSNoRetain 不存在，以及源码第 455、506 行使用不存在的 ml_get_cluster_number，第 456、507 行使用不存在的 ml_get_boot_cluster_type。其余很多转换和成员错误由模板缺失连带产生，不应逐条伪造接口修补。

4903 `osfmk/arm/machine_routines.c` 的 ml_get_boot_cluster 返回 CLUSTER_TYPE_SMP；ml_get_cpu_number 直接把 phys_id 转为 int，启动核编号为 0。ml_processor_register 检查 phys_id 是否小于 MAX_CPUS 和 avail_cpus。不能把 10063 的 MPIDR、cluster 查询逻辑仅重命名后宣布可用。后续 ArmCpu 适配须明确只支持启动核还是完整拓扑，并核对 cpu_id、phys_id、log_id 的语义、时间基回调及 IRQ 安装顺序。

4903 `osfmk/arm/rtclock.h` 的 rtclock_intr(unsigned int) 与现有声明相符。R70 全局符号表可找到 rtclock_intr、LowResetVectorBase、LowResetVectorEnd、ResetHandlerData、const_boot_args 和 ml_get_boot_cluster；没有据此证明 SMP/PSCI 路径可运行。第一阶段没有产出 ArmCpu.o 或 libArmCpu.a；后续启动核对象见下文。

## 主代理集成条件

1. 在自己的独立内核构建中选择上列 ArmDTPlatform.o，或 force-load libArmDTPlatform.a，确保链接器没有因缺少显式引用而丢弃对象。对象包含 __mod_init_func 和 __mod_term_func，必须进入正常 libkern C++ 元类初始化流程。本侧线没有改动链接 runner 或尝试链接现有内核。
2. 4903 当前 KernelConfigTables.cpp 没有 ArmDTPlatform/ArmCpu personality。ArmDTPlatform 至少需要 IOClass 为 ArmDTPlatform、IOProviderClass 为 IOPlatformExpertDevice、IONameMatch 为 device-tree、匹配分值适当高于 IOPanicPlatform 的 personality。静态链接类符号并不会自动创建 personality。现在新增独立的 4903 personality 补丁，具体限制见下文；仍不能仅加匹配项就宣称硬件可用。
3. 确保实际 ADT 有 /cpus、/arm-io、/defaults、/options 和 /chosen 代理数据。4903 IODTPlatformExpert::processTopLevel 从 /options 发布 IODTNVRAM；后者从 /chosen 读取 nvram-proxy-data。4903 的 kIODTNVRAMImageSize 固定为 8192；本地 scripts/unixnu/devicetree.py 的 empty_nvram_proxy 生成 8192 字节镜像。驱动原有 hasNVRAMProxy 只检查非空和 bank-size 属性宽度，并没有完整校验 CHRP 格式或证明 NVRAM 已成功解析，不能把 armdt_platform_nvram_proxy 计数当作安全初始化证据。
4. 默认不提供 pshold 节点时保留父类行为；提供时仍要求已确认的 unixnu,warm-reset-prepared。现有 sheng-platform-stage=1 至 5、sheng-platform-panic 非零会触发 PSCI SYSTEM_RESET 诊断路径。正常集成必须明确检查这些启动参数，不能把旧诊断参数当作无副作用标记。
5. 链接后重新核对对象和内核配置、元类注册、实际 personality 匹配、NVRAM 解析和 IORegistry 节点。再由主代理执行实际启动验证。本侧线符号名审计没有替代任何运行验证。

## 授权范围核验与可复用经验

| 用户原话 | 实现行为 |
| --- | --- |
| 先找已有实现和 4903 补丁，勿大扫主目录。 | 读取仓库和相关 memory，检查现有驱动、构建脚本、patches 与指定 4903 树。 |
| 允许全新脚本、补丁目录、测试、独立临时构建和交接文档。 | 开始时确认指定文件均不存在，再创建上述文件；输出目录必须全新，拒绝位于仓库或受保护输入树下的路径，包括符号链接别名。 |
| 禁止写主线 runners、汇编、CURRENT/LOG、设备证据或当前 4903 树。 | 只读这些必要输入；补丁只应用到新建 driver 副本，未触碰上述写入禁区。 |
| 禁止设备、容器、远端、外部协作。 | 构建与验证均为本机执行，没有设备、容器、远端执行或外部代理。 |
| 真实 4903 头文件下完成最小平台 driver 对象或明确精确编译阻塞。 | ArmDTPlatform.o 和归档成功；后续新增 ArmCpu 启动核对象，保留原始失败日志。 |
| 不冒称全 iOS 可运行。 | 结论仅为编译成功、对象格式及符号名审计通过。 |

可复用经验是先读取真实版本的配置和头文件，保留未经适配的失败对照；不要把部署版本检查改成 12.4 后继续重放 10063 命令，也不要用后代 OSSharedPtr 头文件或假结构定义绕过旧 ABI。CONFIG_DEFINES 的带空格宏值必须作为单个参数保存。所有输入均先复制再编译，并用编译器实际依赖文件验证没有逃出快照。本会话写入范围只允许本侧线文件，因此这些经验记录于此，未写全局 memory。


## 后续完成：ArmCpu 的显式启动核阶段

本阶段新增 ArmCpu.o 和 libArmCpu.a，只支持 Y35A 单 cluster 的启动核 0。构建入口要求 `--component ArmCpu --boot-cpu-only`，编译时必须有 `ARMCPU_4903_BOOT_CPU_ONLY=1`，否则补丁源码直接报错。manifest 明确写入 cpu_mode 为 boot-cpu-only、maximum_supported_cpus 为 1、smp_supported 为 false、required_boot_args 为 cpus=1、unload_supported 为 false。未伪造现代 XNU 类型或 ml_get_cluster_number 接口。

最终产物目录为 `/private/tmp/arm-driver-4903-bjf1_fm_`。

| 产物 | SHA-256 |
| --- | --- |
| `ArmCpu.o` | `5b974fa1f18d8f57b5968bdad4aded66f06a595cbc9751be9372c498d6cee12f` |
| `libArmCpu.a` | `18c91c57ff879eb37d748cc7032120ae397ccdaa9615003b954422941874f5c5` |
| 独立校验用 `KernelConfigTables.o` | `5c146ebaab144c026bf66a0a1fe3efc4223f7c2494dc76fb8c2873c129086ab6` |

ArmCpu 对象使用真实 4903 头文件、`-Werror`、`-mgeneral-regs-only`，目标为 arm64 iOS 12.4。编译日志为空，274 个实际编译输入全部来自独立快照。205 个未定义符号均在上文指定 SHA-256 的 R70 内核全局已定义符号表中存在。此次没有改用正在验证的 R72 内核，也没有将符号名齐备等同于链接或硬件可用。

新增文件如下，原始 drivers/ArmCpu 文件未改动。

| 文件 | 内容 |
| --- | --- |
| `patches/arm-driver-4903/0002-armcpu-boot-only.patch` | 所有权、单启动核约束、真实 4903 注册调用、次核拒绝及移除 PSCI/启动线程。 |
| `patches/arm-driver-4903/ArmCpu4903Support.h` | 可测试的启动策略及原始 map/descriptor 引用处理。没有定义 IOKit ABI 替身，也没有模拟现代共享指针。 |
| `patches/arm-driver-4903/test-support.cpp` | 仅宿主测试使用的引用计数对象和故障注入；不会被驱动入口复制或编入 arm64 对象。 |
| `patches/arm-driver-4903/0003-kernel-personalities.patch` | 向 4903 KernelConfigTables 添加 ArmCpu 和 ArmDTPlatform 两个匹配项，保留 IOPanicPlatform。 |

实际最终构建命令如下，工作目录为仓库根目录：

```sh
python3 scripts/y35a/build_arm_driver_4903.py --component ArmCpu --boot-cpu-only --check-personalities --kernel evidence/y35a-20261102/boot3-20261106/phase-r70-a53-no-apple-hid-20261111/kernel/kernel.macho
PYTHONDONTWRITEBYTECODE=1 ARM_DRIVER_4903_NATIVE_BUILD=/tmp/xnu4903-native-bqbvhqi_ python3 -m unittest discover -s tests -p test_arm_driver_4903.py -v
```

最终定向测试共 13 项通过，没有跳过。ArmCpu 原版失败和适配成功对照位于 `/tmp/armcpu-4903-test-z5d9yy93/baseline` 与 `/tmp/armcpu-4903-test-z5d9yy93/boot-only`。该成功目录还保存 `mode-guard.log` 和命令记录，验证显式设置 ARMCPU_4903_BOOT_CPU_ONLY=0 会被拒绝；`disassembly.log` 保存无 SMC/HVC 的实际反汇编。所有权和启动策略 sanitizer 结果位于 `/tmp/armcpu-4903-ownership-pihpit6u`。ArmDTPlatform 回归对照位于 `/tmp/arm-driver-4903-test-5roarcwe`。

最终复核逐一校验了产物及 274 个编译输入的 SHA-256，确认原始 ArmCpu.cpp、GicV2.h、主线 KernelConfigTables.cpp 和指定 R70 内核哈希未变。两个 Python 文件通过 ast.parse 语法检查，personality 补丁统计为一个文件新增 12 行。当前没有提交、推送、发布、设备访问或内核链接。

`--check-personalities` 只复制原始 KernelConfigTables.cpp 到运行目录，执行 git apply --check、git apply，再把副本编为独立对象。这个校验对象不放进 libArmCpu.a，脚本没有修改内核树，也没有链接内核。补丁的匹配含义由本地真实 OSUnserialize.y 的字典、数组、十六进制 DATA 语法及 IOService 的 IOPropertyMatch 路径交叉核对；未执行内核运行时反序列化或匹配。

### 启动核限制和真实 helper 语义

1. probe 和 start 都先验证 CPU 节点的 device_type 为四字节 cpu 加 NUL，reg 恰为 native-endian u32；不截断八字节地址或把未知 topology 当成 0。
2. 显式要求启动参数 cpus=1，ml_get_cpu_count() 为 1、ml_get_max_cpu_number() 为 0、ml_get_boot_cpu_number() 为 0。它使用 4903 已有 boot-arg 限制，而不把包含多个核的结果硬改成单核。
3. phys_id 和 ml_get_cpu_number(phys_id) 都必须为 0，当前 MPIDR 的 Aff0、Aff1、Aff2、Aff3 都必须为 0。允许 MPIDR 的架构非 affinity 位，例如 bit31；不会把非零 cluster 的启动核冒充为 cluster 0。
4. sheng-smp 或 sheng-smp-gic 非零时，整个驱动拒绝启动。其余 CPU 节点返回 nullptr/false，记录拒绝计数、原因和 IOLog。此阶段不会发布或注册次核，armcpu_smp_running 不会增加。
5. 只有通过上述检查后才建立 ml_processor_info_t，cpu_id 为 this，phys_id/log_id 为实测接受的 0，cluster_id 为 Y35A 已确认的单 cluster 0，cluster_type 来自真实 ml_get_boot_cluster()。其余字段初始化为零。4903 当前注册实现不读取 time_base_enable；时间基仍由驱动 initCPU 显式使能，没有编造回调。
6. 次核 finishSecondary、drainPending、PSCI 调用和辅助 kernel_thread_start 路径全部从适配副本删除。startCPU 明确记录拒绝并返回 KERN_NOT_SUPPORTED。signalCPU 仅允许 this；外部 selftest 也拒绝远端 affinity。反汇编检查没有 SMC 或 HVC 指令，未定义符号中没有 processor_start、kernel_thread_start、ResetHandlerData、LowResetVectorBase 或现代 cluster helper。
7. IRQ controller 只有一个 source 和一个 CPU，但前提是原生 helper 已报告 cpus=1；因此不会借由 controller 的大小虚构其他 CPU 已启动。重复启动核节点通过原子 gBootOwner 认领拒绝，避免并发覆盖全局映射。

新增观测变量 armcpu_4903_boot_only 为 1；armcpu_4903_rejected_cpus 记录策略拒绝次数，armcpu_4903_rejected_starts 记录 startCPU 拒绝次数，armcpu_4903_last_rejection 记录最近一次策略错误。原因 1 是 CPU ID 不支持，2 是 SMP 参数不支持，3 是没有满足显式单核配置，4 是 affinity 不支持。拒绝次数是调用次数，probe 和 start 可能重复检查，不代表唯一物理 CPU 数量。诊断开关 armcpu-skip-gic 仍只是注册诊断，不证明 GIC 或 timer 工作。

4903 的 ml_parse_cpu_topology 在应用 cpus 限制前仍遍历原始 ADT。MACH_ASSERT 打开时要求第一个节点 state 为 running，reg 按 0、1、2 等顺序排列。因此 cpus=1 不会修复错误 ADT；主代理仍须核对现有树的 reg 宽度、节点顺序和 state。本侧线不改 ADT、不隐藏真实硬件核心。

### 内存所有权审查

真实 4903 IOMemoryMap::setMemoryDescriptor 对 descriptor 执行 retain，IOMemoryMap::free 在解除映射后 release。新帮助函数依此管理两个 descriptor 和两个 map：descriptor 创建失败时释放已创建者；任一 map 失败时释放成功的 map；两个 descriptor 的调用方初始引用无论 map 成败均释放；完整成功时才把两个 map 的拥有引用转给 ArmCpu 成员。已有 map 非空时拒绝重新初始化，不覆盖原指针。

全局 GIC 地址只借用启动核对象持有的 map，不再创建全局 OSSharedPtr 或额外持有引用。prepareGic 或 IOCPU::start 返回失败时，releaseMappings 清理拥有引用并清除该实例发布的全局地址，同时释放 cpuName，撤销启动核认领。free 对未注册实例执行同样的幂等清理。

IOCPU::start 成功后，4903 把 this 放进 gIOCPUs，随后机器层和 IRQ controller 使用原始回调指针。本适配显式 retain 一次，使成功注册对象、其 maps、cpuName 和 controller 保持到内核结束。该持有是声明过的内核生命周期策略，不是可卸载驱动。发布之后的注册或 controller 失败直接 panic，不返回一个看似可继续重试的成功状态；注册后的 free/stop 也拒绝，以避免悬空 IRQ 回调。本阶段没有实现注销、卸载、休眠恢复或全 SMP。

宿主测试用真实引用计数行为的简单替身注入第一个/第二个 descriptor 创建失败、第一/第二个 map 失败，检查没有遗留对象、二次清理安全且非空拥有指针不会被覆盖。运行 AddressSanitizer 和 UndefinedBehaviorSanitizer。它验证的是同一个模板帮助函数的所有权逻辑，不能替代真实内核内存压力测试。

### Personality 与主代理集成

新增 `0003-kernel-personalities.patch` 的 ArmCpu personality 使用 IOProviderClass=IOPlatformDevice，IOPropertyMatch 要求 device_type 为 OSData `<63707500>`，IOProbeScore=2000。这让非 CPU 设备不进入 ArmCpu probe；CPU 0 的选择仍由上述真实 helper 和策略检查决定。ArmDTPlatform 使用 IOPlatformExpertDevice、IONameMatch=device-tree、IOProbeScore=5000。IOPanicPlatform 保留为分值 0 的既有项。没有添加 ArmVirtPlatform 或虚构设备节点。

主代理应在自己的待构建内核副本应用 personality 补丁，再明确 force-load 两个归档，或直接把两个对象加入内核对象列表。传给 ld 的参数形式为 `-force_load /绝对路径/libArmCpu.a` 和 `-force_load /绝对路径/libArmDTPlatform.a`；经 clang++ 驱动转发时可用 `-Wl,-force_load,/绝对路径/libArmCpu.a`。必须避免同时加入旧 10063 同名对象或其他 ArmCpu/ArmDTPlatform 实现。普通 archive 搜索可能因没有显式符号引用而省略驱动，单独 personality 字符串不会解决此问题。

两个对象都包含 __mod_init_func 和 __mod_term_func。链接必须保留 libkern C++ 元类初始化所需的构造段，并让驱动元类在 IOCatalogue 匹配前完成注册。不得把校验用 KernelConfigTables.o 作为额外同名定义加入已有内核；应从应用补丁后的内核源码正常编译它。ABI 探针和宿主测试对象都不得 force-load。

需要由主代理实际验证的条件仍包括：早期 CPACR/PE 进度、元类初始化顺序、匹配成功、CPU 注册、真实 IRQ 分发、timer 中断、self IPI 和设备服务。此前 R70/10063 的观测不能作为这个新 4903 ArmCpu 对象的硬件验证。完整 SMP 必须另做拓扑、启动向量、次核初始化和同步验证。

### 本轮验收对应

| 用户要求 | 实现与验证 |
| --- | --- |
| 完成 ArmCpu 的 4903 兼容对象，优先单启动核。 | ArmCpu.o 和归档成功；显式构建开关及运行前 cpus=1 检查。 |
| 使用真实所有权和 cluster 语义，不伪造现代接口。 | 原始 IOKit 指针、retain/release、真实 ml_processor_info_t 和 ml_get_boot_cluster；不支持的次核路径删除。 |
| 其余核不得静默当成功。 | probe/start 明确拒绝并记录原因；startCPU 返回 KERN_NOT_SUPPORTED；没有 PSCI CPU_ON。 |
| 原版失败对照、符号审计、所有权审查。 | 自动原版失败与适配成功编译，205 个符号核对，失败注入及 sanitizer 检查。 |
| 提供 personality 最小补丁，不修改主树。 | 新补丁在独立副本完成应用和编译；主树 KernelConfigTables 原文件哈希核对。 |
| 保持主文件边界，不操作设备。 | 只修改原授权脚本、补丁目录、测试和本文；只读现有内核及源码。 |

## R75 配置绑定重编

主代理报告 R74b 真机出现 No sleep token buffer，并在 R75 全量重建前完成 installhdrs。配置在 T7000.h 中以 XNU_Y35A_A53=1 选择 WITH_CLASSIC_S2R=0；主线消费 OTHER_CFLAGS，而不是 CFLAGS_EXTRA。本侧线未重新测量真机，也未修改主线配置。

2026 年 11 月 11 日 15:21:08 UTC，即台北时间 23:21:08，两个独立构建开始复制更新后的真实头文件，至 15:21:13 UTC 完成编译及输入一致性核验。构建参数明确选择 `--board-profile y35a-a53`，驱动、personality 校验和 ABI 探针命令均包含独立参数 `-DXNU_Y35A_A53=1`。预处理器实际输出 XNU_Y35A_A53=1、WITH_CLASSIC_S2R=0，保留 ARM64_BOARD_CONFIG_T7001。没有向主线传递任何标志。

| 当前产物 | 路径 | SHA-256 |
| --- | --- | --- |
| ArmCpu 对象 | `/private/tmp/arm-driver-4903-jnou0q2s/ArmCpu.o` | `5b974fa1f18d8f57b5968bdad4aded66f06a595cbc9751be9372c498d6cee12f` |
| ArmCpu 归档 | `/private/tmp/arm-driver-4903-jnou0q2s/libArmCpu.a` | `e9fa2845d718bb128b9fc6e188f6242eac9f0aee477040f9f27bcdfe708df82a` |
| ArmDTPlatform 对象 | `/private/tmp/arm-driver-4903-v7mms_w7/ArmDTPlatform.o` | `456a65c544716bfead5ac6ebc62b9e3778bb105834ba6a7c757596220750b1bf` |
| ArmDTPlatform 归档 | `/private/tmp/arm-driver-4903-v7mms_w7/libArmDTPlatform.a` | `a473982f5d21d169d7357f73bc7d01a7465983d6abcf04d233944852ca8d73e3` |

两个目录各有 schema 2 的 manifest.json。记录快照起止时间、原始 CONFIG_DEFINES、显式 OTHER_CFLAGS 对应参数、有效宏、inputs.json 的哈希、实际编译输入及产物哈希。原有含空格宏仍从 Makefile 的字面 CONFIG_DEFINES 保留完整单参数读取；没有对 .CFLAGS 做丢失引号的解析。额外复制并记录 cpu_data_internal.h、machine_routines.h、T7000.h 和 board_config.h 的源文件；源 T7000.h、board_config.h 必须与导出副本逐字节一致，否则拒绝构建。构建结束还检查所有记录的原始输入是否发生并发变化。

两个新对象的字节哈希与早期对象一致，这是实际重编结果，不是用旧对象替代重编。新头和新宏下，静态断言与编译后的常量段均确认 IOCPU=184、IODTPlatformExpert=240、ml_processor_info_t=144 字节；cpu_id、phys_id、log_id、cluster_id、cluster_type 的偏移分别为 0、104、108、116、120。探针还核验真实 cluster helper、物理 CPU 转换、IPI 回调、中断安装和时间基回调签名。此探针没有包含或测量 cpu_data_t，不对其布局、生成汇编偏移或整内核 ABI 作结论。

ArmCpu 的 205 个未定义符号和 ArmDTPlatform 的 232 个未定义符号在固定 R70 内核的名称清单中均存在。R70 仅为只读符号清单参考，不能证明 R75 布局匹配或链接成功。两个对象均通过 arm64 MH_OBJECT、iOS 12.4 deployment 检查，编译日志为空。驱动对象的 deployment 不能证明 libcc_kext 或 InstrProfiling 等整内核依赖版本兼容；主代理保留的 iOS17 警告仍需单独核查。

实际命令在仓库根目录执行：

```sh
python3 scripts/y35a/build_arm_driver_4903.py --component ArmCpu --boot-cpu-only --board-profile y35a-a53 --check-personalities --kernel evidence/y35a-20261102/boot3-20261106/phase-r70-a53-no-apple-hid-20261111/kernel/kernel.macho
python3 scripts/y35a/build_arm_driver_4903.py --component ArmDTPlatform --board-profile y35a-a53 --kernel evidence/y35a-20261102/boot3-20261106/phase-r70-a53-no-apple-hid-20261111/kernel/kernel.macho
PYTHONDONTWRITEBYTECODE=1 ARM_DRIVER_4903_NATIVE_BUILD=/tmp/xnu4903-native-bqbvhqi_ python3 -m unittest discover -s tests -p test_arm_driver_4903.py -v
python3 scripts/y35a/build_arm_driver_4903.py --verify-inputs /private/tmp/arm-driver-4903-jnou0q2s
python3 scripts/y35a/build_arm_driver_4903.py --verify-inputs /private/tmp/arm-driver-4903-v7mms_w7
```

15 项测试全部通过，没有跳过。真实新配置下的 ArmCpu 原版失败和适配成功对照位于 `/tmp/armcpu-4903-test-uu_ep3ky`，ArmDTPlatform 对照位于 `/tmp/arm-driver-4903-test-m5tc0psk`，所有权与启动策略 ASan/UBSan 记录位于 `/tmp/armcpu-4903-ownership-0avsgpub`。新增配置绑定测试先因缺少实现而失败，完成实现后通过，覆盖头文件内容变化及缺失的拒绝。旧版没有配置绑定信息的 manifest 不通过新检查。

`--verify-inputs` 是只读检查，不创建构建目录。它检查记录的原始输入、实际消费的快照文件和对象/归档/ABI 探针哈希；上述两个目录本次均返回 0。它不自动识别另一个目标内核的编译标志，也不是链接许可。主代理必须独立确认目标内核同样使用该 profile；后续任何头文件或宏变化均应先完成 installhdrs，再重编两个驱动。默认 legacy-t7001 仍用于明确的历史诊断，R75 集成必须显式传入 y35a-a53。

R75 后续最新状态由主代理于 2026 年 11 月 11 日提供：kernel 哈希前缀 `32ec304b`，完整证据目录 `evidence/y35a-20261102/boot3-20261106/phase-r75-y35a-no-classic-s2r-20261111`；真机取得新鲜 MST slot `R73MST00` 并进入 `machine_startup`。主代理给出的新 panic format 地址为 `fffffff0070bdf8e`，caller 为 `fffffff007684ff8`，format 为 `Unable to find driver for this platform: "%s".\n`。这些是主代理提供的证据摘要，本侧线没有读取设备证据，也不复核或接手 platform matching 根因。

ArmDTPlatform 当前可交付归档为 `/private/tmp/arm-driver-4903-v7mms_w7/libArmDTPlatform.a`，对象为同目录 `ArmDTPlatform.o`。manifest 的有效宏是 `XNU_Y35A_A53=1` 和 `WITH_CLASSIC_S2R=0`，编译日志为空；personality 最小补丁为 `0003-kernel-personalities.patch`。链接选项为 `-force_load /private/tmp/arm-driver-4903-v7mms_w7/libArmDTPlatform.a`，或直接把对象加入 kernel object list。需与 ArmCpu archive 一同 force-load，并保留 libkern 的 C++ 元类初始化。校验副本的 KernelConfigTables.o 不得作为重复定义加入内核。它不包含本次更新的 ArmCpu SGI 修正，该修正在独立 ArmCpu 归档中。

主代理开始改动原生 XNU 源树后，本侧线的一次 `--check-personalities` 失败在复制 KernelConfigTables.cpp 后的 `git apply --check`。因此最新 ArmCpu 对象构建不再请求该可选检查；personality patch 的独立副本应用与编译已在 2026-11-11 15:21 UTC 记录的 R75 配置构建中通过。没有读取或修改主代理当前 KernelConfigTables.cpp。

### 4903 生命周期复核及集成边界

make_adt.py 的 make_tree 当前仅生成 cpu0，state 为 running，device_type 为四字节 cpu 加 NUL，reg 为四字节小端零。该函数不生成 cpus 启动参数，驱动仍必须独立检查实际 PE_parse_boot_argn 的 cpus=1。次核拒绝策略、原子启动核认领、真实所有权和不可卸载声明保持不变。

本地 4903 IOCPU.cpp 中，enableCPUInterrupt 调用 ml_install_interrupt_handler 并增加 enabledCPUs；registerInterrupt 在 enabledCPUs 不等于 numCPUs 时等待。因此当前单核顺序保持先安装 CPU 中断入口，再注册 source 0 action，最后使能 GIC/时间基。handleInterrupt 按 interruptRegistered 分发，enableInterrupt 的机器中断使能语句在该版本被注释，不能仅凭 disabled 字段臆造补充调用。机器层安装函数针对当前 CPU，所以启动策略必须继续保证当前 affinity 为启动核。

ml_processor_register 不消费 time_base_enable 字段；本适配保留零初始化并由 initCPU 显式使能时间基。rtclock_intr 的传入参数在 4903 被标记 unused，用户态判定从 cpu_int_state 读取，调用 rtclock_intr(0) 不会把用户态硬编码为内核态。实际 IRQ 屏蔽、timer、self IPI 和调度行为仍须真机验证。

personality 补丁仍是独立 `patches/arm-driver-4903/0003-kernel-personalities.patch`，本次也在新配置下成功应用并编译副本。两个驱动对象均实查保留 __mod_init_func 和 __mod_term_func。主代理集成仍须 force_load 两个归档或直接链接对象，并保留正常 libkern 元类初始化；校验用 KernelConfigTables.o 和 abi-probe.o 不得额外加入内核。没有替主代理链接或启动当前内核。

可复用经验是把对象可编译、符号名称存在、指定公开接口布局一致、目标内核配置一致和真实硬件可运行分别验证。尤其在 classic S2R 能力切换时，即使对象哈希未变，也应以新头、新宏、新命令记录证明重编，不能从符号清单推断私有布局兼容。

### ArmCpu SGI 探针操作数修正

对原始 ArmCpu 自检代码的实际 arm64 反汇编发现，SGI 构造值在 `x12`，但 `msr ICC_SGI1R_EL1` 使用了未初始化的 `x14`；随后 `mrs cntvct_el0` 还把计数写入仅声明为输入的 sgi 操作数寄存器。该缺陷只在 `armcpu_sgi_selfprobe` 诊断路径，不是 R75 machine_startup panic 的根因，也没有真机调用证据。

新增 `0004-armcpu-sgi-probe-constraints.patch` 把模板操作数改为输出 `tb` 用 `%0`，输入 `sgi` 用 `%1`。测试先在旧补丁结果上复现缺少修正版操作数，再应用两份 ArmCpu 补丁验证修正，并从编译对象反汇编断言 SGI 编码由同一寄存器送入 ICC_SGI1R_EL1。原始 drivers/ArmCpu/ArmCpu.cpp 保持未改。

修正后对象位于 `/private/tmp/arm-driver-4903-d48193ux/ArmCpu.o`，SHA-256 `655a841a0da62de99d9f9afdbe9ef0527912134c3c41c362778d23edfd4694c2`；归档位于同目录，SHA-256 `c1ef3bf0fedb5f345c0e99aeebaafce384e94ad7a596b76adb7c3567ab2865b0`。本次快照于 2026-11-11 15:42:05 UTC 开始，于 15:42:12 UTC 完成；manifest 记录有效宏 `XNU_Y35A_A53=1`、`WITH_CLASSIC_S2R=0` 和全部输入哈希。`--verify-inputs` 返回 0。205 个未定义符号与固定 R70 内核只按名称比对，缺失为 0；R70 不代表 R75 布局或链接验证。此构建未请求 personality 检查，因此 ArmDTPlatform 的主线集成工作保持独立。

```sh
python3 scripts/y35a/build_arm_driver_4903.py --component ArmCpu --boot-cpu-only --board-profile y35a-a53
xcrun nm -u -j /private/tmp/arm-driver-4903-d48193ux/ArmCpu.o
xcrun nm -g -U -j evidence/y35a-20261102/boot3-20261106/phase-r70-a53-no-apple-hid-20261111/kernel/kernel.macho
PYTHONDONTWRITEBYTECODE=1 ARM_DRIVER_4903_NATIVE_BUILD=/tmp/xnu4903-native-bqbvhqi_ python3 -m unittest discover -s tests -p test_arm_driver_4903.py -v
python3 scripts/y35a/build_arm_driver_4903.py --verify-inputs /private/tmp/arm-driver-4903-d48193ux
```

完整定向测试在修正后通过 16 项，没有跳过。最新原版失败与适配成功对照位于 `/tmp/armcpu-4903-test-lo6ov442`，ASan/UBSan 所有权记录位于 `/tmp/armcpu-4903-ownership-ejvm4_29`，ArmDTPlatform 对照位于 `/tmp/arm-driver-4903-test-kf2f8jqx`。该次对象编译不包含 kernel link；后续 R76b 使用修正前 ArmCpu archive force-load 到 kernel。修正后的 archive 尚未进入 R76b kernel，也不代表 timer、GIC 或自检在真机上工作。

### R76b 集成快照核对

主代理提供的 R76b relink command 只读记录确认 `LD_KERNEL_LIBS` 同时 force-load ArmCpu 和 ArmDTPlatform。该命令记录的 ArmCpu archive SHA-256 为 `e9fa2845d718bb128b9fc6e188f6242eac9f0aee477040f9f27bcdfe708df82a`，ArmDTPlatform archive 为 `a473982f5d21d169d7357f73bc7d01a7465983d6abcf04d233944852ca8d73e3`。使用 `xcrun ar -p` 对归档成员做只读复核，前者包含旧 ArmCpu 对象 `5b974fa1f18d8f57b5968bdad4aded66f06a595cbc9751be9372c498d6cee12f`，后者包含 ArmDTPlatform 对象 `456a65c544716bfead5ac6ebc62b9e3778bb105834ba6a7c757596220750b1bf`。

R76b 使用的 ArmCpu 归档早于 0004 的诊断 SGI 操作数修正；当前独立交付归档是 `c1ef3bf0fedb5f345c0e99aeebaafce384e94ad7a596b76adb7c3567ab2865b0`，成员对象为 `655a841a0da62de99d9f9afdbe9ef0527912134c3c41c362778d23edfd4694c2`。旧、新对象 global symbol 集合完全相同，各 75 项；205 个 undefined symbol 也在修正前后的清单中一致。修正仅改变 `armcpu_sgi_selfprobe` 内联汇编的寄存器操作数，不改变启动策略、对象接口或链接符号。R76b 的 force-load 命令不能视为包含修正后对象；若要把该诊断修正放入后续 kernel，需以后续构建明确选择新 archive。

R76b 的 `readback-probe/readback.json` 记录 kernel SHA-256 为 `4dce94a82c518aa4e6e8bbdbc593e88a709776543b1ebe2bcff921797ef308c2`，与主代理提供的值一致。证据目录尚无静态 gate 完成结果；主代理报告 gates 仍运行。本侧线没有重新链接、改写 R76b 证据或访问设备。`relink.log` 中 InstrProfiling 相关 iOS 17 deployment warnings 属于 libcc_kext 输入，与这两份独立 iOS 12.4 驱动对象的 deployment 记录分开看待。

本轮只读命令包括：

```sh
python3 scripts/y35a/build_arm_driver_4903.py --verify-inputs /private/tmp/arm-driver-4903-d48193ux
python3 scripts/y35a/build_arm_driver_4903.py --verify-inputs /private/tmp/arm-driver-4903-v7mms_w7
xcrun ar -p /private/tmp/arm-driver-4903-jnou0q2s/libArmCpu.a ArmCpu.o
xcrun ar -p /private/tmp/arm-driver-4903-d48193ux/libArmCpu.a ArmCpu.o
xcrun ar -p /private/tmp/arm-driver-4903-v7mms_w7/libArmDTPlatform.a ArmDTPlatform.o
xcrun nm -g -U -j /private/tmp/arm-driver-4903-jnou0q2s/ArmCpu.o
xcrun nm -g -U -j /private/tmp/arm-driver-4903-d48193ux/ArmCpu.o
```

R76b manifest 指定的 force-load 归档来自 R75 时构建的固定路径和哈希；R76b readback SHA 来自对应的 probe manifest。原生 obj 下当前 `mach.development.t7001` 哈希与 readback 所记 kernel SHA 不同，因此本侧线不把该本地未剥离产物冒称为 R76b readback image，也不对 binary-level kernel 内容作额外推断。
