# ArmCpu

Start with the [adaptation procedure](/porting/platform) for board inputs, source changes, build integration and verification order.

ARM64 CPU, GIC and timer driver. Publishes the CPUs, interrupt controller and architectural timer.

| Repository | Maintainer | Scope |
| --- | --- | --- |
| [ArmCpu](https://github.com/UniXNU/ArmCpu) | [UniXNU](https://github.com/UniXNU) | ARM64 CPU, GIC and timer driver. Publishes the CPUs, interrupt controller and architectural timer. |

## State

The implementation supports GICv3 and a boot-CPU GICv2 path with the selected
XNU ABI. GICv2 accepts `qcom,msm-qgic2`, `arm,gic-400` and
`arm,cortex-a15-gic`; secondary CPU startup remains unsupported on this path.

An optional `/timer` ADT node supplies `arm,armv7-timer` or `arm,armv8-timer`
and four native-endian GIC interrupt triples. The virtual timer is the third
triple. The default is INTID 27, which GICv3 still requires. The node must have
an `interrupt-parent` resolving to the controller's `AAPL,phandle`; the controller
declares `interrupt-controller`, `#interrupt-cells = 3` and `#address-cells = 0`.

Y35A hardware with virtual PPI 4 (INTID 20) recorded 45 timer interrupts and one
self SGI on 2026-11-04. Its signed diagnostic completed 32 blocking thread switches
and preserved all 32 SIMD registers before deliberately exiting with status 74.
Full OS operation, SMP and suspend/resume are not validated by this test.

## Build

The selected kernel recipe builds `build/armcpu/libArmCpu.a` through `component:ArmCpu`. Enable its kernel configuration and verify the GIC/timer/PSCI resources using the platform adaptation procedure.
