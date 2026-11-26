> **范围更正（20261124T232133Z）**：本报告仅描述 pristine `pe_serial.c`。仓库已有 `patches/xnu/native-uartdm-console.patch` 与 `scripts/test-uartdm.py`；启用后生成 v1.4 会被接受。更正与边界见 `20261124T232133Z-y35a-uart-report-scope-correction.md`。

# Y35A UART console static contract gap — 2026-11-25

## Scope and ownership

This is one offline auxiliary item: assess whether the existing XNU serial-output path and the generated Y35A ADT already form a qualified polling-UART console contract. It does not modify R186, build code, touch a device, or change shared state files.

The latest main rollout is actively adjudicating R186 (`PEINITRT` present; `ARMVMPRE`/`ARMVMRET` absent). The latest review branch contains no technical UART-console investigation. Main-thread history contains a historical generated-ADT serial-node reference, not an implemented or accepted Y35A polling console.

## Evidence

| Evidence | SHA-256 | Relevant observation |
|---|---|---|
| `/Users/lingion_k/unixnu-research/UniXNU-y35a/scripts/y35a/make_adt.py` | `d9d4d8874d6b7d8b59bc06094aa396598f672950d0dee762b2ce9ea542af244e` | Lines 64–65 emit `uart0`, compatible `qcom,msm-uartdm-v1.4`, with `reg = 0x078b0000 - SOC_BASE`, size `0x200`. |
| `/Users/lingion_k/unixnu-research/UniXNU-y35a/evidence/y35a-20261102/boot3-20261106/touch-t02-20261109/dtb10-cache/dtb10.dts` | `4b2a7fda53ab9b4a69aa3bf9c1247feb7f767b577612914b353f076b391a8714` | Lines 5292–5298 describe `serial@78b0000` as `qcom,msm-lsuart-v14`, status `ok`, with interrupts and core/interface clocks; line 8552 selects it as `serial0`. |
| `/Users/lingion_k/unixnu-research/UniXNU-y35a/upstream-refresh/2026-11-11/sources/xnu-ios12/repo/pexpert/arm/pe_kprintf.c` | `c57ee703fa906fcbc3c74fd19fdd46b9caa2a107fcfe036533cc9f5554ce894f` | Line 42 assigns `PE_kputc = serial_putc`; lines 135–137 forward `serial_putc` to `uart_putc`. |
| `/Users/lingion_k/unixnu-research/UniXNU-y35a/upstream-refresh/2026-11-11/sources/xnu-ios12/repo/pexpert/arm/pe_serial.c` | `e1884c9d8f79da5912bc7c8ff6d428615290e46e2fe1fb5f9e87c0edfa3f4117` | Line 966 defines `uart_putc(char c)` in the ARM platform-expert backend. |
| `/Users/lingion_k/unixnu-research/UniXNU-y35a/upstream-refresh/2026-11-11/sources/xnu-ios12/repo/osfmk/console/serial_console.c` | `397d81593f5ebd8b8c1b906b0a359a23dcfd475d3eba47c4c34d920faf7a30cc` | Lines 120–126 declare `serial_putc` and install `_serial_putc`; lines 639–641 forward the console putc operation to it. |
| `/Users/lingion_k/unixnu-research/UniXNU-y35a/upstream-refresh/2026-11-11/sources/xnu-ios12/repo/osfmk/arm/arm_init.c` | `01a229bf60c330e20cc6f41cfd8b0ff21bab8fac10790b804ab75b4de6ed25db` | Line 419 contains the synchronous-UART warning path, showing that serial output policy exists in ARM initialization. |
| `/Users/lingion_k/unixnu-research/UniXNU-y35a/STATE.md` | `85bc10aa0e6927573c316717aad3e6eae7854a35d7432f0bf22a8b341b141e42` | Runtime qualification remains false; no launchd, SpringBoard, display, touch, storage, or driver acceptance is recorded. |

## Facts

1. XNU 4903 ARM source has a complete source-level output chain from the generic serial console to `serial_putc` and `uart_putc`.
2. The generated XNU ADT already emits a node at the same physical UART window (`0x078b0000`, size `0x200`) used by the stock DT's selected console.
3. The generated node and stock node are not contract-equivalent: the generated compatible string is `qcom,msm-uartdm-v1.4`; the stock selected node is `qcom,msm-lsuart-v14` and additionally carries status, interrupt, and clock properties.
4. No accepted current-generation local witness shows XNU transmitting through this UART path. Existing paired measurements use retained-memory readback and do not qualify a serial console.

## Pending

- Inspect `pexpert/arm/pe_serial.c::uart_putc` and its register-selection helpers to determine whether the backend consumes an ADT node, uses fixed addresses, or assumes a particular UART IP block.
- Determine whether the UARTDM-compatible generated node needs the stock LSUART clock/interrupt properties, a different compatible string, or a separate adapter.
- Confirm the boot-argument and baud/clock handoff assumptions from lk2nd before treating `PE_kputc` as an early-boot evidence channel.

## Inference

The polling-UART proposal is not a drop-in existing capability. The necessary generic output hooks and a same-address ADT node exist, but the source-level hardware contract is unresolved and runtime output is unproven. This is sufficient to justify a bounded source audit, not sufficient to claim that serial logging can replace readback.

## Impact

If the contract closes, early panic/printf output could reduce dependence on repeated build/package/four-stage readback cycles. Until then, substituting UART output for the matched probe would weaken evidence rather than improve it.

## Single next step

Perform a source-only compatibility audit of `pexpert/arm/pe_serial.c::uart_putc` against the generated `uart0` properties and the stock `serial@78b0000` clock/interrupt contract; emit a register/property mapping table with explicit unsupported assumptions. Do not build, package, probe, or run a device in that step.

## Safety

Offline reads only. No Y35A, USB, fastboot, adb, serial-port, persistent-partition, build, flash, or device-probe operation was performed. No shared `CURRENT.md`, `LONG-RUN-STATE.md`, `LOG.md`, or `STATE.md` file was modified.
