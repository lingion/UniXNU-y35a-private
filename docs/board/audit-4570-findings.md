# xnu-4570 审计发现(2026-11-04,Workflow wf_076367f4-94e 6-agent 精读 + 实物复核)

只记录**读过源码/跑过命令**的结论;被推翻的猜测也保留,防止复发。

## 推翻
1. **"KRR/AppleEmbedded 在 4570 是死路" —— 错。** kmod 分支完整(osfmk/kern/kern_module.c),
   kernelcache 预链接链里真有 AppleEmbedded 家族;KRR 缺失只是未开可选 build 旗标。
   真路标 = 使能 KRR + 修 AMCC 时序。
2. **"1559 个 LC_KEXT_* 命令" —— 不存在。** 实物普查:iOS12 kernelcache(MH_OBJECT)
   只有 0x2/0x5/0xb/0x19×15/0x1b/0x26/0x2a/0x32 各一或若干;
   预链接信息在 **KSS blob(com.apple.kernelcomponent.kss)+ kernelcomponent.c**,
   ApplePersistentKeyStore 是空壳。
3. **"MachSpmi/HID 在 4570 无匹配节点" —— 错(半)。** 有(经 IODeviceTree matching 与
   boot-phase kext);真缺口在 **PMIC/GLUE 寄存器层**。

## 证实
4. **AMCC 时钟竞争(启动阻塞 #1)**:apple_arm_cycles_per_sec 依赖
   AppleARMPlatformClockProvider;该驱动在 4570/iOS12 不存在 → 未初始化 →
   一切 clock_interval_to_deadline(驱动超时、panic 前打印)失效。
5. **panic 无屏**:IO80211 之外,panic 路径无任何显示驱动绑定 —— AppleDisplay 类驱动
   缺位;GPU 帧缓冲 + panic-at-through 是屏幕输出的最短路径。
6. **4570 iokit 树**:iokit/IOKit 仅 74 头,storage 家族不在树内(与 kernelcache 有
   IOStorageFamily 不矛盾——iOS12 kext 不都在 OSS 树)。链接层需 audit-storage-interface.py。
7. **CPU 家族宏**:proc_reg.h/board_config.h 按平台宏(APPLE_ARMxx_ARCH_FAMILY)分支;
   A53 需新家族块或 j71 家族复用 + 覆盖(crypto/PAN/16K-PG 位必须显式关)。
