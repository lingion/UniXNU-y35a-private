# Implementation Plan: vivo Y35A 触摸驱动(Synaptics S3202 / RMI4 over QUP I2C)

日期 2026-11-05。路线图位置:存储驱动 QcomSdcc(离线全链已收口,Phase 1/2
等实机批准)之后的下一步。本计划由盘面侦察产出:证据只引用本仓库实测文件,
不引用叙述。所有设备迭代遵守既有闸门:RAM boot 先行、写分区逐项请批、
userdata 永不动。

## Overview

给原生 XNU(iOS 12.4 线,xnu-4903)一条可用的触摸输入路径:在 MSM8916
BLSP1 QUP5 I2C 总线上驱动 Synaptics S3202(RMI4),经 IOHIDFamily 兼容的
自建 IOHIDDevice 发布 digitizer 报告,最终在实机上把触点变成 HID 事件。
形态完全复刻 QcomSdcc 的成功路径:传输无关核心(template IO)+ 主机红绿
套件 + 内核壳对 ABI 垫片 -Werror 实编 + ADT 节点 + personality 补丁。

## 盘面事实(全部实测,禁改拍脑袋)

| 项 | 值 | 源 |
| --- | --- | --- |
| 总线 | `i2c@78b9000` compatible `qcom,i2c-msm-v2` | 库存 DTB dtb10.dts:6834(容器 /tmp/qcdtdts/) |
| SE 窗口 | 0x78b9000 长 0x600;BAM 0x7884000 长 0x23000 | dtb10.dts:6839 |
| 中断 | qup_irq SPI 99(INTID 131),bam_irq SPI 238(INTID 270,与存储/WiFi 共享 BAM) | dtb10.dts:6841 |
| 时钟 | clk-freq-out 0x61a80 = 400 kHz;clk-freq-in 0x124f800 = 19.2 MHz | dtb10.dts:6844-6845 |
| 分频 | high-time-clk-div 0x17,fs-clk-div 0x16,noise-rjct 0/0 | dtb10.dts:6849-6852 |
| BAM 管道 | cons 0x0c,prod 0x0d;master-id 0x56 | dtb10.dts:6853-6855 |
| 从机 | `rmi_i2c@20`,addr 0x20,compatible "synaptics_3202" | dtb10.dts:6857-6859 |
| 触摸中断 | gpio 13(INTID 13+80=93? 不——TLMM 控制器 phandle 0x48 的中断域是 PPI 外独立 mux,见 §T0 实测项),attn_polarity 0(低有效) | dtb10.dts:6860-6868 |
| 复位 | synaptics,reset-gpio = TLMM 12;irq-gpio = TLMM 13 | dtb10.dts:6866-6867 |
| 供电 | vdd_ana(phandle 0xe3)/vcc_i2c(phandle 0x49)PMIC 供给 | dtb10.dts:6862-6863 |
| 坐标 | ts 1266x2220(0x4f2x0x8ac)映射 lcd 720x1280(0x2d0x0x500)——缩放映射 | dtb10.dts:6870-6873 |
| TLMM | pinctrl@1000000 compatible qcom,msm-tlmm-8916,reg 0x1000000 长 0x300000,122 脚 | dtb10.dts:750-756 |
| 触控键 | ts-virt-key 五枚虚拟键几何(139,117)-(1345..)等 | dtb10.dts:6879 |

缓存侧事实(2026-11-05 python 字节扫描 out/ipsw/16G102/kernelcache.decompressed):
- `com.apple.iokit.IOHIDFamily` 47 命中(bundle 注册与依赖记录),`IOHIDInterface` 50,
  `IOHIDEventService` 14,`AppleHIDKeyboard` 68,`RMI4`/`synaptics` 0 命中
  ——Apple 缓存里没有 Synaptics RMI kext,输入栈是干净的 IOHIDFamily 消费面。
- C++ mangled 符号在缓存里被剥离(`__ZN11IOHIDDevice` 0 命中),因此 IOHIDDevice
  的 ABI 垫片必须走 audit-storage-interface.py 同构路线:公开 Darwin 18 时代
  IOHIDFamily 源码 + 对 16G102 缓存内该 kext 的字节校验,产 `build/hid-abi/include`。
- IOService 世代替换(17→12)在 12 线同样成立:SdccCore 的 12 世代验证可复用。

仓库既有参照(读码定样,勿另起炉灶):
- `drivers/ShengNovatekTouch`(NvtTouchCore 纯逻辑 + nvt_bus 传输回调抽象 +
  主机假总线测试)——分层模板。
- `drivers/ShengHidInput/NativeHidInput.cpp`(IOHIDDevice 子类,报告描述符,
  一致触点快照发布)——OS 报告层模板,ABI 世代需从 2031.120.4 换 12.x。
- `drivers/QcomSdcc/*`(本仓 iOS12 线刚走通的全链:传输核/主机套件/内核壳/
  ADT/personality/容器编译)——工程流程模板。
- `docs/porting/input.md`(触摸与按键适配程序,含 nvt_bus 语义与检查单)。

## Architecture Decisions

1. **总线驱动自建,不走 Linux 移植**:MSM8916 QUP I2C(v2 SE)寄存器组小而
   干净(SE 模式 = 非 BAM 的 FIFO 事务,400 kHz 下完全够用),LK
   i2c_qup.c 只做位定义参照,清洁室实现。BAM/DMA 一律不用——触摸帧
   ≤ 64 字节,PIO 足够且无一致性问题(与 SdccCore Phase 0-2 的 PIO 纪律同理)。
2. **RMI4 核心传输无关**:`RmiCore.h` template<class BUS>,主机模型 fake
   RMI4 设备(页 0 产品 ID、F11 2D 触摸功能描述符、中断寄存器)与真机
   同一份代码。识别 S3202 靠页 0 读数(build ID/产品 ID),不靠字符串。
3. **HID 面用自建 IOHIDDevice 壳**,ABI 垫片由新审计脚本对缓存字节背书
   (同 storage-abi 模式);digitizer 报告描述符按 Apple MT 习惯面
   (MultitouchSupport 在缓存 1 命中,消费面存在)。坐标缩放(ts→lcd)
   在核心层做,与 DTB 数值锁成不变量。
4. **中断策略**:第一阶段 polled + attn GPIO 读(经 TLMM 寄存器直读 GPIO
   13 状态),第二阶段接 armcpu_spi_attach(INTID 131,QUP)与 GPIO mux
   路由的触摸线;slot 预算登记(SPEC §6 已为 touch 留 131)。TLMM 中断
   号到 INTID 的换算在本板 DT 上未定,列为 T0 实测项,禁猜。
5. **供电按 always-on 处理**:vdd_ana/vcc_i2c 在 lk2nd 之后已由 PMIC 配置,
   resume 纪律同 sdhc1(检查实况、失败即拒,不模拟稳压器);SPMI 主机驱动
   不在本计划范围,登记为依赖缺口。
6. **reset 时序**:GPIO 12 拉低 ≥ 1 ms、释放后 ≥ 10 ms 才能总线上问事
   (Synaptics datasheet 惯例 + LK synaptics_tcm 先例)。LK 在 fastboot 槽
   已跑过完整 init,交棒时设备处于已配置态;T0 探针要实测两种路径:纯
   交棒读 + 带 reset 的冷读,取实机证据定默认。

## Task List

### Phase T0 — 硬件事实探针(RAM 镜像,只读,设备迭代 #0)

- [x] T0.1 `drivers/QcomQupI2c/I2cCore.h` 最小事务核:SE 模式 start/xfer/stop,
      寄存器位从 dtb10 数值 + QUP v2 数据手册布局实现;400 kHz 分频直接用
      high-time-clk-div 0x17/fs-clk-div 0x16(实测值,不重新推导)。
      (落地 2026-11-06 49a55a0 + fa4095d;verify 行=commit body 内 i2c_host
      十组全过 exit 0,本 checkpoint 要求项;2026-11-09 心跳盘核验补勾)
- [ ] T0.2 `scripts/y35a/rmi_probe.cpp` RAM 探针(复刻 emmc_probe.cpp 形态):
      enableHost 无关;配置 QUP GPIO 功能(pinctrl 寄存器直写,读 dtb 值),
      对 addr 0x20 读 RMI4 页 0(8 字节),结果写检查点 RAM + Y35ARD01 读回。
      (2026-11-09 心跳注:读回验收口径须按 staging 镜像模型改写 — 9032a64/8a392ae
      已证运行时写不落线性 PA、fastboot 直读只见加载区静态影像;探针结果必须写
      staging 区(0x859e0000 同法)并以 warm-reset 保持为保持性判据, 勿沿用
      emmc_probe 时代的 PA 直读假设。
      (勘误 2026-11-09 07:3x: 上一注"电视整机离线致实机窗口顺延"是设备混淆 —
      本 bring-up 目标设备是 vivo Y35A 本机(fastboot efff9d92/PD1502A,
      make_adt.py:4 背书), 一直在槽可用; 192.168.31.168 属 Coocaa 电视, 是
      另一项目(gathin/tvhome 验收), 本项目文档零提及, ping 不通与 Y35A 无关。
      T0.2 实际顺延理由: staging 读回机制正在 9032a64 裁决后收敛, 并行会话
      活跃于此线, 待其稳定再启动探针烧写。)
      (落地注 2026-11-09 08:2x: 探针代码已起草并离线编译绿 —
      scripts/y35a/rmi_probe.cpp + probe_rmi.py, 容器内
      clang++ -std=c++17 -Wall -Werror -nostdlib 全绿, probe.bin 3856 B,
      零未定义符号, 报告布局镜像进 manifest.json。baf4604 §8 重判后
      读回口径 = staging 写 + dc civac 刷洗 + warm-reset 保持 +
      CNTVCT 新鲜见证(t_boot), 与 readback 线现行实现一致。设备执行
      仍未开始: RAM boot 烧写属设备迭代 #0, 逐项请批, 窗口在下一轮。)
      验收:读回 Product ID/Build ID 与 Synaptics S3202 家族一致(0x20 上
      有 ACK),GPIO13 attn 状态可读。
- [ ] T0.3 TLMM GPIO13 中断路由事实:探针顺带 dump TLMM_INTC_* 配置,把
      gpio→INTID 换算钉死写进 docs/board/y35a-facts.md Touch 节。
- 依赖:无(设备在 fastboot,用既有 harness)。风险:总线被 lk2nd 占用态未知
  ——探针先只读不写控制寄存器,写路径全在 enable 位之后。

### Phase T1 — I2C 总线核心(纯离线)

- [x] T1.1 `drivers/QcomQupI2c/Test/i2c_host.cpp` 主机套件:fake SE 寄存器面,
      覆盖 7-bit 寻址、写-读组合事务(repeated start)、NACK 错误路径、
      超时上界。ASan/UBSan,exit 0 才算绿。
- [x] T1.2 `I2cCore.h` 内核 IO shim 约定(hc 单窗口 0x600,mapDeviceMemoryWithIndex
      纪律与 SdccPorts 相同,写后 dsb oshst)。
- 验收:T1.1 全绿;`g++ -std=c++17 -fsanitize=address,undefined` 命令写进 commit body。

### Phase T2 — RMI4/S3202 功能核(纯离线)

- [x] T2.1 `drivers/QcomTouch/RmiCore.h`:页窗口切换(0x0a addr window)、
      页 0 身份(Firmware ID/Build ID/Product ID matrix)、F11 描述符解析
      (num_tx/num_y/max_abs)、中断状态读取 + 事件解码(1-5 触点,
      abs_x/abs_y/z)、ts→lcd 缩放映射(1266x2220→720x1280,DT 数值锁
      成 constexpr + 断言)。
- [x] T2.2 `Test/touch_host.cpp`:fake RMI4 从机(I2cCore 的 BUS 接口上),
      红绿覆盖:身份不符拒启、F11 缺失拒启、单指/五指帧解码、坐标映射
      不变量(0→0,max→max)、glitch 帧(重复中断)幂等。
- 验收:T2.2 全绿 + 映射契约测试(顺序/边界类断言按设计规范铁律 ③)。

### Phase T3 — IOHIDDevice 挂接(离线)

- [x] T3.1 `scripts/audit-hid-interface.py`:对公开 Darwin 18 IOHIDFamily
      源(refer/IOHIDFamily,需先镜像克隆,gh.qdp.qzz.io)构建 `build/hid-abi/include`
      垫片 + `IOHIDDevice-reference.o` 编译审计,并扫 16G102 缓存内
      com.apple.iokit.IOHIDFamily kext 的段边界/版本字符串一致(同
      audit-storage-interface.py 的结构;注意其本次暴露的 Linux 宏冲突要一并解决
      ——沿用 -Wno-macro-redefined 先例)。
- [x] T3.2 `drivers/QcomTouch/NativeHidDigitizer.cpp`:IOHIDDevice 子类,
      报告描述符(digitizer, multi, MT1 风格位),触点快照一致性(单锁),
      发布路径参照 NativeHidInput.cpp。probe 匹配 IOPlatformDevice sdhc 式
      的 `rmi_i2c`  nub。
      追记 2026-11-06(提交 86b831b/f125deb):实际形态按 T4.2 设计修正
      落地——provider 是 NativeQupI2c 服务而非 IOPlatformDevice nub;
      bring-up 序列拆成共享模板 DigitizerBoot.h(顺序本身由 touch_host
      case 17 字面锁定);报告描述符 297 B MT1 五触点,触点快照在单
      IOLock 下发布;容器 Darwin-18 头 -Werror 语法闸 rc=0,修复三处
      API 漂移(OSNumber::unsigned32BitValue 实名、IOLock 为 typedef
      非 class、影子全局归并真实成员)。原文"IOPlatformDevice rmi_i2c
      nub"匹配路径由人格补丁 5edfb11 更正,不另改。
- [x] T3.3 容器 -Werror 实编 + 对象符号审计(元类体系全套,同 QcomSdcc 验收法)。
      追记 2026-11-06:两壳容器内 -c 实编 rc=0(Mach-O arm64 目标文件);
      nm 审计元类体系全套——gMetaClass/MetaClass 构析全套/alloc/
      getMetaClass/vtable/typeinfo,NativeHidDigitizer 基类符号解析到
      IOHIDDevice 垫片(未定义引用 IOHIDDevice::gMetaClass/C2),链接期
      由垫片提供,同 QcomSdcc 验收法。
- 依赖:T3.1 先于 T3.2(垫片必须真头编译过)。

### Phase T4 — 构建集成(离线)

- [x] T4.1 ADT:`make_adt.py` 增 `qup_i2c5` 节点(reg 0x78b9000-0x7800000 长
      0x600,interrupts SPI 99→INTID 131;child `rmi4` 节点 reg 0x20 +
      reset/irq GPIO 12/13 + attn_polarity 0 + ts/lcd 四尺寸)。红→绿补
      test_board_adt 用例(锁 reg 换算与 INTID)。
      追记 2026-11-06:`rmi4` 节点补标准 `compatible="synaptics_3202"`
      (dtb10.dts:6859 同款身份,IODTCompareNubName 只查
      name/compatible/device_type/model 四属性,原节点只有 vendor 键
      `vivo,use-ic-list`,匹配不可达)。红→绿 9/9。
- [x] T4.2 personality 补丁 `patches/xnu/native-touch-personality.patch`
      (IOClass=NativeHidDigitizer;IOProviderClass=IOPlatformDevice;
      IONameMatch='synaptics_3202';1000:32),链式 git apply 验证。
      设计修正 2026-11-06(源码背书,落地形态以此为准):
      ① IOPlatformDevice nub 只为 arm-io 直接子节点发布
      (IOPlatformExpert.cpp:1736 processTopLevel 用 kIODTExclusive 非递归;
      ArmDTPlatform.cpp:132 createDeviceNubs 同样只迭代直接子节点),
      `rmi4` 是孙节点,`IOProviderClass=IOPlatformDevice`+
      `IONameMatch='synaptics_3202'` 永远匹配不到——原条文按此写会做出
      一个永不 attach 的驱动。
      ② 本核 4903 工作树与 refer/xnu 基线都没有 IODeviceTreeExpander
      (grep 全树零命中),没有把深层 DT 节点变成 service 的既有机制。
      ③ 实际补丁两条目:NativeQupI2c(IOPlatformDevice,
      IONameMatch='qcom,i2c-msm-v2',attach 在 qup_i2c5 nub 上,
      与 NativeSdcc 对 sdhc1 同构)+ NativeHidDigitizer
      (IOProviderClass=NativeQupI2c,总线驱动 start() 时经 DT 平面
      childFromPath 找到 rmi4、读 reg/attn_polarity/GPIO 四尺寸后
      attach 之;寄存器身份校验 RmiCore 在 probe 里照做,身份不符拒启)。
      验证:git apply --check 前后 rc=0,apply→reverse-check→还原全链绿。
- [x] T4.3 components.toml QcomTouch/QcomQupI2c 条目 + build-arm-driver.py
      hid-abi include 分支(与 storage-abi 同段)+ baseline 脚本
      XNU_NATIVE_TOUCH 闸门与 force_load stanza。
      落地 2026-11-07 4ae86c4。验收口径更正:实编在 host 认证配方
      (build/hid-abi/compile-command.json,arm64-apple-ios12.0;
      容器 clang 是 x86_64-linux 无 sysroot,对 arm64-apple 内核壳
      不可用——T3.2 报告 Findings 已记)。
- 验收:host 配方编译两驱动全绿;ADT 测试全绿;补丁链绿。

### Phase T5 — 实机触摸闭环(设备迭代 #1 起,逐项请批)

- [ ] T5.1 RAM boot 带触摸驱动:检查点 = F11 解析成功、读回 ≥1 帧真实触点
      (探针期人手按屏),不发布 HID(纯传输验证)。
- [ ] T5.2 IOHIDFamily 注册 + digitizer 发布;消费面(如 IOHIDEventService
      路径)在 12 世代 RAM 根下起事件线程,读回事件计数。
- [ ] T5.3 中断驱动化(T0.3 钉死的 INTID 接 armcpu_spi_attach,polling 降级
      保留为 boot-arg)。

### Checkpoint:每 Phase 收口
- [ ] 该 Phase 全部离线验收命令真实跑过且输出写进 commit body(verify 行)
- [ ] 设备未烧写;所有实机项只在 RAM boot 里发生

## Risks and Mitigations

| Risk | Impact | Mitigation |
| --- | --- | --- |
| QUP I2C 在 lk2nd 之后处于未知态 | 探针失败 | T0 先只读;失败路径复位 SE(软复位位),不碰 PMIC |
| TLMM→INTID 换算无文档 | 中断收不到 | T0.3 实测钉死;期间 polled 兜底(与 sdcc 同纪律) |
| IOHIDFamily 12.x 垫片 vs 缓存字节不符 | 内核拒链/运行时崩 | T3.1 审计闸:段边界+版本串对不上即停,禁放宽 |
| S3202 固件版本差异(page0 读数不同) | 误识别 | 身份检查只断言家族字段,Build ID 全量打印取证 |
| 与存储共享 BAM(238)线 | 中断串扰 | 不用 BAM;登记 cross-subsystem ledger |
| vdd_ana/vcc_i2c 未起 | 总线无响应 | resume 检查在探针里实测 PM8916 状态(只读 SPMI register 需 T0 补一个只读探针;若不可行,列依赖缺口) |

## Open Questions(给 owner)

1. 存储窗口(上轮遗留):cache 分区(计划默认)还是其他?批准后 Phase 2
   设备迭代 #2 才能排期。
2. 触摸第一阶段是否只验证到 T5.2(HID 发布),手势/虚拟键(DT 里五枚
   ts-virt-key)留到显示闭环之后?建议留——键区几何依赖 LCD 校准。
3. IOHIDFamily 公开源版本:Darwin 18.0 还是 18.5?T3.1 先按 16G102 内
   CFBundleVersion 实测值选 tag,再字节对齐。

## 文件清单(新建)

- drivers/QcomQupI2c/{I2cCore.h,Test/i2c_host.cpp}
- drivers/QcomTouch/{RmiCore.h,NativeHidDigitizer.cpp,Test/touch_host.cpp}
- scripts/audit-hid-interface.py, scripts/y35a/rmi_probe.cpp
- patches/xnu/native-touch-personality.patch
- scripts/build-arm-driver.py / build-xnu-4k-baseline.sh / components.toml /
  scripts/y35a/make_adt.py + test_board_adt.py 编辑
- docs/board/y35a-facts.md T0.3 追写
