> **范围更正（20261124T232133Z）**：本报告仅描述 pristine `pe_serial.c`。仓库已有 `patches/xnu/native-uartdm-console.patch` 与 `scripts/test-uartdm.py`；启用后生成 v1.4 会被接受。更正与边界见 `20261124T232133Z-y35a-uart-report-scope-correction.md`。

# Y35A UART console backend rejection — 2026-11-25

## Scope and ownership

This completes the single source-only compatibility audit recommended by `20261125T223000Z-y35a-uart-console-static-contract-gap.md`. It does not modify R188, build code, touch a device, or change shared state files.

Latest main-thread activity is R188 package/probe geometry and binding work. Neither main nor review has claimed a Y35A UART backend implementation or acceptance test.

## Evidence

| Evidence | SHA-256 | Relevant observation |
|---|---|---|
| `/Users/lingion_k/unixnu-research/UniXNU-y35a/upstream-refresh/2026-11-11/sources/xnu-ios12/repo/pexpert/arm/pe_serial.c` | `e1884c9d8f79da5912bc7c8ff6d428615290e46e2fe1fb5f9e87c0edfa3f4117` | The traditional UART implementation is under `#ifdef S3CUART` (line 48). `serial_init` maps `boot-console`/`uart0`/`uart1` and reads `compatible` (lines 902–920), but accepts only four Samsung/16550 strings (lines 940–948); otherwise it returns 0 (lines 954–956). `uart_putc` emits only when `uart_initted` is true (lines 966–973). |
| `/Users/lingion_k/unixnu-research/UniXNU-y35a/upstream-refresh/2026-11-11/sources/xnu-ios12/repo/pexpert/pexpert/arm64/board_config.h` | `cee1e2b61dab31063deedc94d3ba0af031fbcf6681ad75257f3ae2ec9270c6a3` | The `ARM64_BOARD_CONFIG_T7001` block includes `pexpert/arm64/T7000.h` at line 41. |
| `/Users/lingion_k/unixnu-research/UniXNU-y35a/upstream-refresh/2026-11-11/sources/xnu-ios12/repo/pexpert/pexpert/arm64/T7000.h` | `72def6bee859c13ee4d0335c05b035ee2c4d3265c52ee6022255292c82b151f4` | Line 15 includes `pexpert/arm/S3cUART.h`. |
| `/Users/lingion_k/unixnu-research/UniXNU-y35a/upstream-refresh/2026-11-11/sources/xnu-ios12/repo/pexpert/pexpert/arm/S3cUART.h` | not separately hashed in this cycle | Line 7 defines `S3CUART`; this closes the macro chain from T7001 to the backend compiled in `pe_serial.c`. |
| `/Users/lingion_k/unixnu-research/UniXNU-y35a/upstream-refresh/2026-11-11/sources/xnu-ios12/repo/pexpert/conf/files.arm64` | `e11e5d8b0b835ca1a8d90d83540b0e76261f66c11b801b79cd3a54b9f2fe6774` | Line 8 includes `pexpert/arm/pe_serial.c` in the ARM64 kernel file set. |
| `/Users/lingion_k/unixnu-research/UniXNU-y35a/scripts/y35a/make_adt.py` | `d9d4d8874d6b7d8b59bc06094aa396598f672950d0dee762b2ce9ea542af244e` | Lines 64–65 emit `uart0` with compatible `qcom,msm-uartdm-v1.4` and the `0x078b0000` register window. |
| `/Users/lingion_k/unixnu-research/UniXNU-y35a/evidence/y35a-20261102/boot3-20261106/touch-t02-20261109/dtb10-cache/dtb10.dts` | `4b2a7fda53ab9b4a69aa3bf9c1247feb7f767b577612914b353f076b391a8714` | Lines 5292–5298 use `qcom,msm-lsuart-v14` at the same physical window and provide status, interrupt, and clock properties. |
| `/Users/lingion_k/unixnu-research/UniXNU-y35a/docs/coordination/claude-codex-sync/automation-reports/20261125T223000Z-y35a-uart-console-static-contract-gap.md` | `d12dc22afcc88b5c9357f678e84b7f4fa559cbb8117ecc18a71692479f511972` | Prior report left backend selection and register mapping unresolved. |
| `/Users/lingion_k/unixnu-research/UniXNU-y35a/STATE.md` | `96a473505f1a24a027e73fcc1013512308fcaa2ae408efe6623f964269602a9a` | Runtime qualification remains false; R188 is host/package work, not a UART witness. |

## Facts

1. The generated node name `uart0` and its `reg` property satisfy the lookup/mapping shape expected by `serial_init`.
2. T7001 selects T7000, T7000 includes `S3cUART.h`, and that header defines `S3CUART`; therefore the Samsung/16550 compatibility branch is the active traditional-UART branch in the pinned source configuration.
3. Neither generated `qcom,msm-uartdm-v1.4` nor stock `qcom,msm-lsuart-v14` matches any accepted string in that branch.
4. With the current generated compatible string, source-level `serial_init` reaches the final `return 0`, leaving `uart_initted` false; `uart_putc` then performs no transmit.
5. The source comment says “S3c2410 and PL011,” but the visible traditional backend registers and initialization are the S3C2410-style implementation; no Qualcomm UARTDM/LSUART backend was found in this file.

## Pending

- Confirm the exact R188 linked binary retains this dispatch and has no out-of-tree `pe_serial.c` replacement or build override.
- Derive the Qualcomm UARTDM transmit-ready/data register protocol and clock/baud handoff before implementing a backend.
- Determine whether an early console should reuse lk2nd's already-configured UART state or perform its own initialization.

## Inference

Changing only the ADT compatible string to the stock LSUART string would not close the gap: neither Qualcomm string is accepted, and the selected S3C register implementation is not evidence of UARTDM register compatibility. A Qualcomm-specific polled backend or an explicit equivalent implementation is required before serial output can be trusted.

## Impact

Do not enable `serial=3` or replace matched readback probes on the assumption that the existing `uart0` node already provides console output. In the pinned source, the current node is rejected and characters are silently dropped. Readback remains the accepted evidence channel until a backend and runtime witness exist.

## Single next step

Add a host-only UART console contract test that feeds the generated `uart0` properties through the current compatibility dispatch, asserts rejection for both Qualcomm compatible strings, and requires an explicit backend-selection entry before the ADT contract may be changed.

## Safety

Offline reads and one new automation report only. No Y35A, USB, fastboot, adb, serial-port, persistent-partition, build, flash, or device-probe operation was performed. No shared `CURRENT.md`, `LONG-RUN-STATE.md`, `LOG.md`, or `STATE.md` file was modified.
