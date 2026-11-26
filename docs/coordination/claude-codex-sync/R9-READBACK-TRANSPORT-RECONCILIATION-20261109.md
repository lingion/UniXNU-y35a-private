# R9 readback transport reconciliation

Date: 2026-11-09

## Verdict

The transport candidate adopted by commit `93b7978` is valid for the standalone T0.2 touch probe. It is not yet a complete transport design for the existing full readback probe.

The distinction matters because the two probes have different payload sizes:

- T0.2 writes a `0xbc4`-byte report at `0x859f0000`, above the DT `pram` window. Its write interval is `0x859f0000..0x859f0bc4`, so the independent layout and transport gates both pass.
- The current readback manifest has a `0x11000` LK source interval and records extending through `0xc640` from the source base. That payload includes the 16 KiB exception stack and 32 KiB interrupt stack. It cannot be moved wholesale into the `0x1000` report page at `0x859f0000`.

Therefore, the sequence in `CAPTURE-TRANSPORT-AUDIT-20261109.md` must be scoped explicitly. Snapshotting all of pram, writing a small report above pram, and restoring all of pram is coherent for T0.2. For full readback, restoring all of pram after writing the record table would erase the record table before `oem y35a panic` stages the source range.

## Correct direction for the earliest XNU measurement

Use a separate minimal-boundary readback mode:

1. Snapshot `0x859e0000..0x859f0000` to the verified scratch interval `0x95000000..0x95010000`.
2. Write a fixed report no larger than `0x1000` at `0x859f0000`.
3. Put only the evidence needed for the first boundary decision in that report: freshness witness, kernel generation, CPU state, the early-fault record, the assembly handoff marker, the XNU phase marker, and field-width-correct scalar carriers.
4. Restore the full pram snapshot and flush it before reset.
5. Let the existing LK command upload the untouched pram followed by the report page.

The large stack records and arbitrary 128-byte symbol windows belong to a separate full-memory diagnostic mode. That mode needs either a deliberately destructive pram contract or a new LK/composite upload path. It must not be presented as preserving EPH evidence under the current `0x859e0000..0x859f1000` source contract.

## Required gates

- The manifest must state whether the image is `minimal-boundary` or `full-readback`.
- `scripts/y35a/verify_readback_transport.py` is the independent mode gate. It rejects
  the current legacy manifest because it has no explicit mode, no preservation contract,
  and no report-page payload declaration.
- `minimal-boundary` must have no record or write interval overlapping pram, a report size at most `0x1000`, and a complete snapshot/restore interval inside LK scratch and outside all measured reserved domains.
- `full-readback` must state explicitly whether pram preservation is sacrificed. A green T0.2 gate must not satisfy this gate.
- The binary must be inspected for the snapshot-before-write and restore-before-reset ordering, including cache maintenance.
- No device boot is informative until the selected mode has a green independent layout gate and a kernel artifact that passes `verify_phase_instrumentation.py`.

## Communication to the fixer

Keep the T0.2 geometry change. Do not use its green report-page gate as evidence that the existing full readback line is transport-correct. The next implementation decision is the minimal-boundary mode above, not another device run with the current 12-record manifest.

## R8 test-contract boundary

The current uncommitted R8 tests correctly expose missing field-width and EPH-snapshot behavior, but their wording must not widen the result. `STAGE_BASE + 0xf000` is `0x859ef000`, which is still inside the DT pram interval `0x859e0000..0x859f0000`; it is only outside the current record allocation ending at `stage+0xc640` and before the report page at `stage+0x10000`. A `0x74`-byte copy there can preserve a compact EPH header witness before the record writes. It does not de-alias the probe from pram and does not preserve the full EPH panic text.

Keep the R8 tests as a red implementation contract, but report the slot as a pram-tail preservation slot. The independent layout gate must remain red until the selected full transport mode is explicitly declared and its ownership is proven.

The contract is now implemented and green: the current full suite is `52/52`, the regenerated readback has 16 records ending at `0xc570`, and the manifest publishes `eph_snapshot_offset=0xf800` and `eph_snapshot_bytes=0x74`. R9 is still open because the same manifest does not yet declare `transport_mode`, `report_bytes`, or `pram_preserved`; fresh layout verification reports 17 pram overlaps.

The next R9 step is now verified offline. The current manifest declares `full-readback`, `pram_preserved=false`, `report_bytes=0x1000`, EPH write extent `0xf800..0xf880`, stamp snapshot `0xf900..0xf940`, and fault-state `0xf000..0xf400`. The candidate `out/y35a/readback-probe-20261109-r9/readback-probe-not-xnu.img` has SHA-256 `4187fedef2f6b874e899e55413aac48ed59a7378b64d9f33020adc19e8274c86`; both `verify_capture_layout.py` and `verify_readback_transport.py --mode full-readback` return `ok:true`. The layout result is explicitly destructive and is not a claim that pram or full EPH text survives.

The preservation-first minimal-boundary candidate is also green as a separate mode. It uses the phase-r11 kernel SHA-256 `619a6ea03be230529d4eeeaac64a3fd9d44cef8e1d302255a6bd5f70dd70381a`, image SHA-256 `9466188a5b3f91fedb53525823dea7ced471f5ad1d7e69b1bf4ddbf462d9a405`, manifest SHA-256 `0ae59dac07ed1a7accd8f26a47123633084c6c95c30da3cad9cd64a54d1d4fea`, and declares `minimal-boundary`, `pram_preserved=true`, snapshot `0x95000000..0x95010000`, report page `0x859f0000..0x859f1000`, and ten report records ending at `0x480`. Both independent gates return `ok:true`. It has not been booted.

## Build-environment correction

The container exports XNU's `CCC_OVERRIDE_OPTIONS` globally. Ubuntu clang 18 rejects the two Apple-clang-only warning suppressions in that variable under `-Werror`, so a direct probe build fails before compiling the probe. `probe_rmi.py` now removes that variable only from its standalone clang subprocess; the XNU build environment remains unchanged. With the current source copied into the container, the normal documented build produces `probe.bin` 3864 bytes, image SHA-256 `295241cebe164a1f01c370a0484beee6fa60777f150fcd9deed646de11509b98`, and all three manifest gates `ok:true`.
