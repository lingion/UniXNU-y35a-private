# Phase Instrumentation Audit

Date: 2026-11-09

## Finding

The artifact named `out/y35a/ios12-boot3-phase/kernel-packed.macho` is not a valid phase-instrumented kernel for the current marker patch.

Artifact:

- SHA-256: `6e9a09d2453a57532111dbead64ea67018ca31128e3ca7dcaa4e3fbf6f0216c5`
- mtime: 2026-11-08 01:00:04
- `_arm_init`: `0xfffffff00725a494`
- `_arm_vm_init`: `0xfffffff00725b6c4`
- `_panic_init`: `0xfffffff0071261c8`
- `_PE_create_console`: `0xfffffff0076a948c`

## Binary evidence

The Mach-O was disassembled with Xcode's `llvm-objdump` from `__TEXT_EXEC,__text`.

At `_arm_init`, the call to `_arm_vm_init` is:

```text
fffffff00725a810: bl _arm_vm_init
fffffff00725a814: adrp ...
fffffff00725a81c: add ...
fffffff00725a824: mov w2, #4
fffffff00725a824: bl _PE_parse_boot_argn
```

There is no call or store corresponding to `native_phase_marker` between `_arm_vm_init` and the next boot-argument parse.

At the later path, `_panic_init` is called and execution immediately continues through `DAIFClr`, sleep-token setup, and kprintf initialization. `_PE_create_console` is called and execution immediately continues to `_PE_init_printf` and CPU idle initialization. No marker write is present after either call.

The symbol table contains `_arm_init`, `_arm_vm_init`, `_panic_init`, and `_PE_create_console`, but no `_native_early_fault_address` symbol. The phase binary also has no direct little-endian occurrences of the three marker constants from `native-phase-markers.patch`.

The new offline gate `scripts/y35a/verify_phase_instrumentation.py` reproduces this result from the artifact itself:

```json
{
  "ok": false,
  "failures": [
    "missing _native_early_fault_address symbol",
    "_arm_init contains no phystokv call for phase markers",
    "no marker address translation after arm_vm_init",
    "no marker address translation after panic_init",
    "no marker address translation after PE_create_console"
  ]
}
```

The focused readback, capture, and packaging suite remains green: `39 passed`.

## Consequence

The previous phase-device result with an all-zero early-fault record is not a phase-boundary result. The image did not contain the intended phase marker instrumentation, so it cannot prove that the marker channel failed or that XNU stopped before `arm_vm_init`.

The phase result remains useful only as a boot-image and transport observation: the image was accepted by lk2nd and the device returned to fastboot. It is not valid evidence for the XNU startup boundary.

## Required correction

Before another device run:

1. Rebuild the kernel from a clean, explicitly identified source tree with both `native-early-fault-record.patch` and `native-phase-markers.patch` applied.
2. Verify the resulting Mach-O disassembly contains the marker stores after `_arm_vm_init`, `_panic_init`, and `_PE_create_console`, plus `_native_early_fault_address`.
3. Generate the boot image and readback probe from that exact kernel; record all hashes in the manifest.
4. Only then request a new RAM-only device run.
