# Current State

Last reconciled: 2026-11-09, repository HEAD `772f858`, with evidence through the 10:20 r8-not-landed gate and the independent R9 transport mode verifier.

## Active Target

- Device: vivo Y35A / PD1502A, MSM8916, serial `efff9d92`.
- XNU line: iOS 12.4.1 `16G102`, XNU-4903.270.47. The `xnu-4570` tree is a separate iOS 11/Darwin 17 reference line, not the kernel used in these device boots.
- Last locally observed device state during the Codex run: `lk2nd-msm8916` fastboot. Always check again before another run.
- Repository branch at reconciliation: `fix/readback-panic-globals`. The worktree contains another session's modified and untracked files. Read current Git status before editing; do not overwrite its work.

## Confirmed Evidence

- The legacy boot3 artifact is `out/y35a/ios12-boot3/boot3.img`, SHA-256 `d7640a423935b6dbe9322b0b8bbcdac305d25428ff87e0a8ac8bd5439cb74ad6`; kernel SHA-256 `5fd4e6b5f7fa10e1b2cc9323ac5802833c15479fce5c67068f2ba8837fdcdc94`.
- The phase boot3 artifact is `out/y35a/ios12-boot3-phase/boot3.img`, SHA-256 `8694a25fdef575a5b615e8fee6f59bf546495f1f206478c5398af994a7462c4c`; kernel SHA-256 `6e9a09d2453a57532111dbead64ea67018ca31128e3ca7dcaa4e3fbf6f0216c5`.
- Codex ran the phase image on the real device. Fastboot returned `Booting OKAY`; the device returned to fastboot after approximately 13 seconds. A probe rebuilt against the phase kernel was then booted and staged.
- Phase readback: `evidence/y35a-20261102/boot3-20261106/boot4-r3-20261108/phase-readback-phaseprobe.raw`, SHA-256 `1e3c8e0f2bf2c352dd28d53e4b9179aef55533b8e6dee728bcc6f8a5d25624fe`. Its Y35ARD01 and Y35AXNU2 headers contain the phase kernel stamp. The phase-specific early-fault record at physical `0xa0b7c800` is zero.
- The phase result does not establish a failing XNU function. A zero early-fault record means only that this record contains no captured exception state. The three phase markers in `native-phase-markers.patch` are written after `arm_vm_init`, `panic_init`, and `PE_create_console`; none discriminates the earlier pexpert calls.
- A separate 2026-11-06 `panic.raw` contains a real XNU panic report for `pid 1: launchd`. This proves that one older boot reached deep kernel and user-process startup. Do not transfer that result to a different kernel/image generation.
- The r7 witness chain is live: `r7-baseline.raw`, `r7-probe2.raw`, and `r7-post-boot3.raw` differ at the CNTVCT witness field, and the Y35AXNU2 handoff stamp changes from the phase generation to the legacy `5fd4e6b5` generation after the legacy boot. This proves the probe reran and the boot shim's handoff stamp reflects the preceding image generation.
- The r7 witness does not prove that XNU reached `PE_init_panicheader()`. `Y35AXNU2` is written by the boot shim before branching to XNU. Treat the stronger “panic header written” statement in the 06:00 heartbeat as provisional until an XNU-owned field or independent raw header proves it.
- 2026-11-09 08:3x addendum (measured): the three r7 captures differ *only* in the CNTVCT witness (bytes 0x10..0x14) and the handoff stamp (0x10008..0x1000F); every sampled carrier window is byte-identical across baseline, probe2, and post-boot3, and the `_BootArgs` window equals the static Mach-O file bytes for that VA (not an LK-written boot_args struct). Two independent readings follow: (i) the boot3 runs captured no runtime XNU writes into any carrier window — contrast with 2026-11-06 `panic.raw`, which carries panic text at exactly those window offsets; (ii) the panic-header question cannot be adjudicated by any current-probe capture at all, because the probe's stage window aliases the DT pram panic-log window (`make_adt.py:51` reg base 0x859e0000 == `readback_native.py` `STAGE_BASE`) and the probe overwrites pram[0..0xC640) during sampling. Source: `heartbeat-20261109-0830-stage-pram-aliasing.md`.
- Focused offline validation is green: 39 tests passed across readback names, capture format, and native packaging. The full r7 comparison is recorded in `R7-AUDIT-20261109.md`.
- The phase instrumentation audit found that `out/y35a/ios12-boot3-phase/kernel-packed.macho` does not contain the intended phase markers or `_native_early_fault_address`. Its phase-device result is therefore a transport/boot-image result, not a valid XNU startup-boundary measurement. Details are in `PHASE-INSTRUMENTATION-AUDIT-20261109.md`.
- `scripts/y35a/verify_phase_instrumentation.py` now acts as an offline artifact gate. It correctly rejects the existing phase artifact for missing `_native_early_fault_address` and all three marker paths; the existing 39-test suite still passes.
- `scripts/y35a/verify_capture_layout.py` now acts as the panic-capture layout gate. It correctly rejects the current manifest because stage `0x859e0000..0x859f1000` and every record overlap DT pram `0x859e0000..0x859f0000`.
- T0.2 touch probe is offline-built and verified: `scripts/y35a/rmi_probe.cpp` plus `probe_rmi.py` compile cleanly with no undefined symbols and use raw TLMM/GCC dumps plus one bounded QUP5 transaction. Its report write interval is now `0x859f0000..0x859f0bc4`, outside pram. It remains device-gated by explicit per-experiment authorization and no parallel fastboot; this green touch geometry does not close full readback transport.
- Container source audit found an LK-compatible transport fix candidate: snapshot pram to `0x95000000`, write the report at `0x859f0000`, restore pram, then use the existing LK `oem y35a panic` source range. The exact constraints and ownership are recorded in `CAPTURE-TRANSPORT-AUDIT-20261109.md`; this is not yet implemented or device-verified.
- `scripts/y35a/verify_capture_transport.py` passes the two-area candidate against measured LK constraints: pram `0x859e0000..0x859f0000`, snapshot `0x95000000..0x95010000`, report `0x859f0000..0x859f1000`, LK scratch `0x90000000..0xa0000000`, and boot3 RAMDisk `0x90aea000..0x933ea000`.
- Fresh 10:0x verification: commit `93b7978` makes the standalone T0.2 report `0x859f0000..0x859f0bc4`, and its layout and transport gates pass. The full readback manifest still writes records through `0xc640` inside the pram-backed source range, so the T0.2 green result does not close full readback transport. See `R9-READBACK-TRANSPORT-RECONCILIATION-20261109.md`.
- Fresh 10:20 verification at the next repository tip: `772f858` is an evidence-only r8-not-landed heartbeat. Readback regeneration still matches the prior `2aaf092c...` image prefix, `STAGE_BASE` is still `0x859e0000`, and the raw layout gate still reports 13 failures. The independent `verify_readback_transport.py` also rejects the legacy manifest until it declares a transport mode and preservation contract. The touch line remains geometry-green but device-gated.

## Corrections to Earlier Interpretations

- The three r6 files `r6-baseline-retained.raw`, `r6-post-boot3.raw`, and `panic-direct-20261109-0017.raw` are byte-identical. Equality supplies no new content. Later r7 CNTVCT witness captures show the probe did rerun, so the earlier claim that the capture path was necessarily a frozen buffer is superseded.
- The initial claim that the readback probe used the wrong `__BOOTDATA` physical addresses was withdrawn. Later review of all eight boot3 `segment_table` entries found linear placement `PA = 0xa0004000 + voff`; the stack-address mismatch claim must not be repeated.
- Fixed 128-byte symbol records include neighboring bytes for 4-byte and 8-byte fields. Compare only the field's actual width; neighboring bytes are not evidence that the symbol itself has that value.
- `Y35AXNU2` is written by the boot shim immediately before its branch to the XNU entry. It proves the shim reached that handoff point and identifies the packaged kernel generation. It is not an XNU phase marker, EPH panic header, or proof that `PE_init_panicheader()` ran.
- The 2026-11-06 launchd panic and the 2026-11-09 short-return boots are different observations. The current cause remains unresolved.

## Current Disagreement

Claude's 2026-11-09 06:00 evidence note says the `d7640a42` boot reached panic-header initialization and stopped before panic text. The available `Y35AXNU2` stamp alone proves only that the boot shim handed off to XNU. Keep the stronger panic-header claim provisional until it is tied to an XNU-owned header field or independently verified raw bytes. The source note is `evidence/y35a-20261102/boot3-20261106/heartbeat-20261109-0600-staging-model-verdict.md`.

The r7 witness proves that the capture probe re-executed and that the handoff stamp changed with the preceding boot generation. It does not by itself prove that every symbol-addressed record is an XNU runtime value. The 05:00, 06:00, and 07:45 heartbeat notes contain the successive analysis and corrections; read them in order when adjudicating any r7 claim.

## Next Work

0. **R9 transport split:** the standalone T0.2 report-page geometry is green, but the existing full readback record table still overlaps pram and reaches `0xc640`. Do not restore full pram after writing that table and call the result preserved readback. Implement the `minimal-boundary` report mode from `R9-READBACK-TRANSPORT-RECONCILIATION-20261109.md`, or explicitly choose a new LK/composite upload path for full readback. The independent mode gate must pass before any device decision. Coordinate with the Claude fixer session `local_c3ce3e96` (owns `readback_native.py` / segment-layout work) so this and the implementation are not done twice. No device run is informative until the selected mode has a green independent layout gate.
1. Rebuild or recover a kernel whose Mach-O binary passes `scripts/y35a/verify_phase_instrumentation.py`. Do not use the existing phase artifact for boundary conclusions.
2. Add a distinct assembly handoff marker separate from the XNU C marker, then prove the phase marker raw offset and binary stores offline.
3. Record one minimal, falsifiable next experiment here before touching the device. The T0.2 geometry gate is now green but still requires a separate per-experiment user GO; the readback mode gate is a different prerequisite. A prior RAM-only boot is not blanket authorization for a new run.
4. After the gate is satisfied, test one earliest-boundary marker or one ADT `interrupt-controller="master"` A/B change per device run. Stop if the result cannot distinguish hypotheses.
5. Keep GPU, IIG, broad driver work, and userland out of the active investigation until the earliest XNU boundary is supported by runtime evidence.

## Source Files

- `evidence/y35a-20261102/boot3-20261106/heartbeat-20261109-0405-r7-witness-capture-chain-live.md`
- `evidence/y35a-20261102/boot3-20261106/heartbeat-20261109-0500-r7-live-read-adjudication.md`
- `evidence/y35a-20261102/boot3-20261106/heartbeat-20261109-0545-boot4-verdict.md`
- `evidence/y35a-20261102/boot3-20261106/heartbeat-20261109-0600-staging-model-verdict.md`
- `evidence/y35a-20261102/boot3-20261106/heartbeat-20261109-0745-t02-gate-recheck.md`
- `evidence/y35a-20261102/boot3-20261106/codex-review-20261109.md`
