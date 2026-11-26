# A53 实现自定义寄存器存活审计（R75 linked kernel，离线）

审计日期：2026-11-11，心跳触发。执行者：外部 Claude 会话。仅读取本地封存产物与 `/tmp` 反汇编，无构建、无脚本、无设备操作。

对象：`evidence/y35a-20261102/boot3-20261106/phase-r75-y35a-no-classic-s2r-20261111/kernel/kernel.macho`，SHA-256 前缀 `32ec304beb1b3532`，本次独立重算。反汇编工具为 NDK r27 `llvm-objdump`，覆盖 `__TEXT_EXEC,__text` 与 `__KLD,__text` 两个可执行段。

## 结论

我的 HID-A53 审计（`HID-A53-ABI-AUDIT-20261111.md`，六编码 A53 UNDEFINED）在 R75 中已被正确落实：R69 真机命中的冷启动 HID 块（`0x…072708xx`）已消失，`0x…07270900` 处代之以标准 `CPACR_EL1` FPEN 写入。R70–R72 的静态与真机证据也支持这一判读。

但 linked R75 内核仍残留 33 条 `op0=3, CRn=C15` 访问（`S3_0_C15_C0/C1/C2/C3/C4/C7_0`），分布在 6 个函数。其中一条位于前向可达路径且无任何门控，是跳过 HID 后下一个必然的 A53 同步异常点。按可触达性分级：

| 函数 | 访问数 | A53 可触达性 | 门控 |
|---|---|---|---|
| `_CleanPoC_DcacheRegion_Force_nopreempt` `0x…07256854` | 3（C4_0） | **必然** | **无** — 函数入口第一条即 `mrs x14, S3_0_C15_C4_0`（`0x…07256860`） |
| `_cpu_defeatures_set` `0x…07273d74` / `cpu_defeatures_set_2` `0x…07273e40` | 24（C0–C4、C7） | 条件 | 有 — 三处调用点（`_arm_init` `0x…07259a94`、`_arm_init_cpu` `0x…0725a068`、`_arm_init_idle_cpu` `0x…0725a158`）全部要求 boot-arg `"defeatures"` 存在且对应 nibble 非零；不带该参数时提前返回 |
| `_cyclone_typhoon_prepare_for_wfi` `0x…07273d20` | 2 | 后续 | `_cpu_idle` `0x…072573d8` 内 |
| `_cyclone_typhoon_return_from_wfi` `0x…07273d48` | 2 | 后续 | 同上（WFI 退出） |
| `_arm64_prepare_for_sleep` `0x…07273cc0` | 2 | 后续 | `_ml_arm_sleep` `0x…07257bec` 内 |

`CleanPoC` 分支：唯一直接调用者是 `_CleanPoC_DcacheRegion_Force` `0x…07256890`，后者唯一调用点是 `_pmap_batch_set_cache_attributes` `0x…0724dfac`。

`_CleanPoC_DcacheRegion` `0x…0725684c` 与 `_CleanPoC_DcacheRegion_internal` 本身不含 C15 访问，只执行 `dsb sy`。

## 编码对照（独立复核，与我的 HID 审计一致）

TF-A `lts-v2.8.10` `include/lib/cpus/aarch64/cortex_a53.h` 给出 A53 自身实现定义寄存器为 `S3_1_C15_C2_0`（CPUACTLR）、`S3_1_C15_C2_1`（ECTLR）、`S3_1_C15_C2_2`（MERRSR），即 **op1=1、CRm=C2**，与 XNU 中 Apple 的 `S3_0_C15_C{0,1,2,3,4,7}_0`（op1=0）任一都不相交。TF-A master `lib/cpus/aarch64/cortex_a53.S` 确认 A53 复位序列确实读写 C15（`sysreg_bit_set CORTEX_A53_CPUACTLR_EL1, …_DTAH` 等），说明 C15 这一 CRn 在 A53 上并非整体不可用，但 Apple 的 op1=0 编码族仍为 UNDEFINED。R75 目录名 `no-classic-s2r` 指向的正是这条边界。

## 可执行建议（不含实施）

1. 若目标是继续前推启动，最小改动是把 `_CleanPoC_DcacheRegion_Force_nopreempt` 中三条 C15_C4_0 访问按其在 A53 上的语义处理：该处读写 bit11（`#0x800`），语义为 Apple 私有 PoC 域控制，A53 无对应物，可整体删除这对 `mrs/msr` 与外围 `isb`，保留 `bl _CleanPoC_DcacheRegion_internal`。这与 R70 对 HID 块的做法同构。
2. `defeatures` 族在默认 boot-args 下不会触发，可暂不处理，但需在 boot-args 契约里显式确认不带 `"defeatures"`；否则 24 条访问会成为下一个异常源。
3. WFI/sleep 族（C0_0）只在 CPU 空闲与睡眠路径上，属启动之后的问题，优先级低于 1。

本审计不改变任何现有判决，只补上我在 `HID-A53-ABI-AUDIT-20261111.md` 里留下的未决条件（「两处后续 HID 站点是否跑在 A53 启动路径上」）：答案是 `_CleanPoC_DcacheRegion_Force_nopreempt` 在路径上且无门控，其余需 boot-arg 或进入空闲/睡眠才可达。
