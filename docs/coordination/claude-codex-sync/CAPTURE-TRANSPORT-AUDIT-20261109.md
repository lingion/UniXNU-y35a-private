# Capture Transport Audit

Date: 2026-11-09

## Fixed LK facts

The resident Y35A lk2nd code has these measured contracts:

- `cmd_oem_y35a_panic()` calls `fastboot_stage((void *)0x859e0000, 0x11000)`.
- `fastboot_stage()` copies that source range into the fastboot download buffer before `get_staged` uploads it.
- MSM8916 `target_get_scratch_address()` returns `0x90000000`.
- MSM8916 `target_get_max_flash_size()` returns `256 MiB`, so LK maps `0x90000000..0xa0000000` as scratch.
- The legacy boot3 second-domain RAMDisk occupies `0x90aea000..0x933ea000`; the `0x95000000` area is outside that domain and inside the LK scratch mapping.

Sources: container `lk2nd-y35a-codex/app/aboot/fastboot.c`, `lk2nd/fastboot/debug/register.c`, `target/msm8916/meminfo.c`, `target/msm8916/rules.mk`, and the boot3 manifest.

## Current defect

The XNU ADT declares `pram` as `0x859e0000..0x859f0000`, while the probe uses the same address as its staging destination. The probe overwrites the EPH header and panic text before LK stages the range. `verify_capture_layout.py` rejects this layout.

## Candidate fix without an LK rebuild

Keep the existing LK source range and use a temporary scratch snapshot:

```text
before probe writes:
    copy 0x859e0000..0x859f0000 -> 0x95000000..0x95010000

probe report:
    write report/marker/CPU witness at 0x859f0000..0x859f1000

before probe reset:
    copy 0x95000000..0x95010000 -> 0x859e0000..0x859f0000
    flush the restored pram range

existing LK command:
    oem y35a panic -> stage 0x859e0000..0x859f1000
```

The uploaded 69,632-byte body then contains the untouched 64 KiB pram snapshot followed by the probe report. This preserves the existing LK command and separates the report from the EPH region.

## Required gates

- The chosen scratch interval must be checked against the exact boot manifest's RAMDisk/second-domain interval and all shim allocations.
- The probe must snapshot the entire pram region before writing any byte to the source range.
- The copy-back must complete before the reset path and must include cache maintenance.
- The manifest must record `pram_snapshot_pa`, `report_pa`, `stage_source_pa`, and all interval sizes.
- `verify_capture_layout.py` must be extended to check the snapshot interval, report interval, and LK source interval separately.
- This is an offline design candidate, not a device result. Do not boot it until the builder and binary layout pass these gates.

## Ownership

The Claude fixer session `local_c3ce3e96` owns `readback_native.py` and the generator/segment-layout changes. Codex owns this transport audit and the independent layout gate. Do not apply the same implementation in both sessions.
