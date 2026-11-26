# T0.2 Probe Audit

Date: 2026-11-09

## Finding

The T0.2 probe has derived its staging base from `readback_native.py`, but the report has not yet been moved above the pram window.

Current code facts:

- `probe_rmi.py` derives `sb = stage_base()` and passes only `-DY35A_STAGE_BASE={sb}UL` to clang++.
- `rmi_probe.cpp` defines `Report *rep` from `STAGE_BASE`.
- The current report destination therefore remains the derived readback stage. With the current readback literal, that is `0x859e0000`, which is the DT pram base.
- The comments mention `Y35A_REPORT_BASE` and an above-pram report, but no such compile-time macro or C++ address is currently present in the code path.

This is a semantic mismatch between the comments and the binary layout. The probe can compile cleanly while still writing its report into pram.

## Evidence

- DT pram: `0x859e0000..0x859f0000`.
- Existing LK command stages: `0x859e0000..0x859f1000`.
- The two-area candidate report interval: `0x859f0000..0x859f1000`.
- Current `probe_main()` report pointer: `volatile Report *rep = (volatile Report *)STAGE_BASE;`.
- Current builder defines `Y35A_STAGE_BASE`, but not `Y35A_REPORT_BASE`.

## Required correction

Keep the staging convention as a derived input, but derive and pass two addresses:

1. `Y35A_STAGE_BASE`: the LK source/stage convention.
2. `Y35A_REPORT_BASE`: the report destination, outside pram and inside the bytes LK stages.

The C++ report pointer and cache flush loop must use `Y35A_REPORT_BASE`. The manifest must record both values and the layout gate must check the report interval against pram. The XNU readback probe additionally needs the snapshot/restore sequence described in `CAPTURE-TRANSPORT-AUDIT-20261109.md`; the standalone T0.2 probe does not need an XNU panic snapshot but must still write its report outside pram.

This audit is read-only. `rmi_probe.cpp` and `probe_rmi.py` remain owned by the Claude fixer workstream.
