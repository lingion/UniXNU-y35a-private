# ArmCpu

先按[适配流程](/zh/porting/platform)准备板级输入、修改源码、接入构建并逐步验证。

ARM64 CPU、GIC 和定时器驱动。发布 CPU、中断控制器和架构定时器。

| 仓库 | 维护者 | 范围 |
| --- | --- | --- |
| [ArmCpu](https://github.com/UniXNU/ArmCpu) | [UniXNU](https://github.com/UniXNU) | ARM64 CPU、GIC 和定时器驱动。发布 CPU、中断控制器和架构定时器。 |

## 状态

实现支持 GICv3 和仅启动核心的 GICv2 路径，使用选定的 XNU ABI。
GICv2 接受 `qcom,msm-qgic2`、`arm,gic-400` 和 `arm,cortex-a15-gic`，
此路径尚不支持启动其他核心。

可选的 `/timer` ADT 节点提供 `arm,armv7-timer` 或 `arm,armv8-timer`，
以及四组三元 GIC 中断描述，使用本机字节序。第三组指定虚拟定时器 PPI。
缺省值为 INTID 27，GICv3 当前仍要求该值。节点的 `interrupt-parent` 必须
关联控制器的 `AAPL,phandle`；控制器声明 `interrupt-controller`、
`#interrupt-cells = 3` 和 `#address-cells = 0`。

2026 年 11 月 4 日，Y35A 真机使用虚拟 PPI 4，即 INTID 20，记录了 45 次
定时器中断和一次自 SGI。自行签名的诊断进程完成三十二轮阻塞线程切换，
检查全部三十二个 SIMD 寄存器后主动以状态 74 退出。此测试不代表完整系统、
多核心或休眠唤醒已通过验证。

## 构建

选定内核配方通过 `component:ArmCpu` 构建 `build/armcpu/libArmCpu.a`。启用对应内核配置，按平台适配流程核对 GIC、定时器和 PSCI 资源。
