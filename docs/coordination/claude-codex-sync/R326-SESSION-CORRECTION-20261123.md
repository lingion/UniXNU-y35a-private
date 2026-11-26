# R326 Session Correction Audit

Date 2026-11-23

Target session `01a1bbf9-dcb8-7af3-9622-ff82f0684444` remains active. This audit covers the current R326 real-device investigation and the handoff risk between the Codex session and the Unixnu workspace.

## Verified outcome

The session has a valid live boundary around `ml_get_max_cpus()` only after the marker contract is interpreted conservatively. R111 produced fresh `MLMAXEN0` and `MLWAIT00` without `MLMAXRT0`. R113 later produced `MLMAXRT0` and `CPCNUR00`, but the later R119 adjudication shows that several marker slots were reused or overlapped. R114 through R119 therefore do not establish progress into BSD initialization.

The session created R112 through R120b while the R111 and R113 evidence was still being adjudicated. This produced a sequence of candidate builds and device runs whose marker contracts were not independently valid. R120 correctly stopped before device use after the ownership problem was found.

## Evidence table

| Run | Fresh observed result | Valid conclusion | Not established |
| --- | --- | --- | --- |
| R111 | `MLMAXEN0`, `MLWAIT00`, no `MLMAXRT0` | The instrumented consumer reached its wait-side marker | Producer absence, scheduler failure, or a global boot fault |
| R112 | No `MLINITOK0` | This run does not prove producer publication | Producer did not run, marker was not retained, or the source path differed |
| R113 | `MLMAXRT0`, `CPCNUR00` | A return-side marker was retained in this image | The shared `CPCNUR00` slot cannot be treated as an independent `CPCRUN00` witness |
| R114 to R118 | No valid new BSD boundary marker | The dedicated later windows did not produce their markers | A unique fault location after the last accepted marker |
| R119 | `MLMAXRT0`, `CPCNUR00` and no BSD markers | The run confirms the same limited retained marker state | BSD entry, `bsd_init`, task bootstrap, launchd, storage, display, or touch |

The R119 adjudication is stored at `/Users/lingion_k/unixnu-research/reboot-checkpoints/r326-r119-pre-bsd-split-paired-run-20261123-235/adjudication-r119.md`.

## Gate defect

The candidate verifier `/Users/lingion_k/unixnu-research/reboot-checkpoints/r326-r120b-pre-bsd-split-corrected-input-20261123-238/verify_marker_ownership.py` returns success for the uncorrected R119 source tree because it only checks conflicts involving the proposed new offsets. It does not require those offsets to exist. It does not reject duplicate ownership among existing markers. It does not reject all unaligned markers.

An independent scan of the R119 source tree found these duplicate offsets.

- `0xb30` appears twice in `osfmk/arm64/cpu.c`
- `0xc60` appears twice in `osfmk/kern/startup.c`
- `0xc70` appears twice in `osfmk/kern/startup.c`
- `0xca0` appears three times across startup, shared-region, and commpage code
- `0xca8` appears twice
- `0xcf8` appears in both commpage and `machine_routines.c`
- `0xd3c` is not 8-byte aligned

The scan counted 81 marker calls and 74 unique offsets. The existing verifier reported success with 81 calls because the required-new-slot set was absent from the source and therefore vacuously passed. A valid gate must require every declared marker, reject every duplicate offset unless an explicit last-writer contract exists, reject every unaligned 64-bit marker, and verify source order for markers that intentionally share a slot.

## Memory evidence separation

The staged artifact `/Users/lingion_k/unixnu-research/evidence/y35a-20261102/lk2nd-runtime.dtb` has SHA-256 `36555c5e66b4a09cd38506706b0a301c2c8b8d6b883de51c51b89971825e9709`. Independent parsing reports model `msm8916-vivo-pd1502a`, root address and size cell counts of two, and two consecutive 1 GiB memory banks at `0x80000000..0xbfffffff` and `0xc0000000..0xffffffff`. This supports a 2 GiB installed-memory interpretation for that staged runtime DTB. It does not by itself bind the final candidate boot image to the same FDT. The final boot chain still needs a record containing the DTB identity, raw hash, readback time, boot image hash, boot arguments, reservation table, and the selected XNU-owned window.

The package field `owned_memory=0x10000000` remains a selected 256 MiB XNU-owned window. It must not be presented as total physical RAM. The older `/proc/iomem` text in `PROGRESS.md` remains record-level evidence until the original capture is recovered and bound to the same boot chain.

## Required stop contract

```text
source chain
  -> complete marker ownership map
  -> offline gate rejects missing, duplicate, unaligned, or overlapping markers
  -> package hash and probe hash bind to the same kernel
  -> one paired RAM-only run
  -> independent raw adjudication
  -> update the next hypothesis
```

The next device run must stop before device access when any of these conditions holds.

- A required marker is absent from the source or binary contract.
- Two markers share an offset without an explicit ordered last-writer contract.
- A marker is not 8-byte aligned or its width is not eight bytes.
- The package, kernel, probe, or manifest hash is not mutually bound.
- The baseline is not zeroed by the dedicated preclear probe.
- A final marker is interpreted without comparing its last writer and source order.

## User request versus observed behavior

The request was to locate the Unixnu blocking session, identify drift and circular reasoning, and complete all useful auxiliary work. The session was located and its active state was verified. The main drift is repeated device experimentation before marker ownership was closed. The circular pattern is a missing marker being treated as a runtime boundary, followed by another marker patch without first proving that the previous marker contract was valid. The corrective action is to make marker ownership and runtime-DTB binding independent offline gates before another paired device run.

## Current decision

Treat R111 and R113 as the last useful R326 evidence until the marker contract is repaired. Treat R114 through R119 as non-progressing runs with invalid or insufficient marker contracts. Keep the 2 GiB staged-DTB observation as a separate capacity fact. Do not infer BSD, IOKit, storage, display, touch, SpringBoard, or complete iOS boot from this sequence.

## Superseding correction recorded later on 2026-11-23

The R119 source tree was re-read after this report. Its build provenance includes
`inputs/18-r111-commpage-cursor.patch`, which removes the earlier `CCPUNEN0`
call. Therefore R119's `MLMAXEN0` at ce0 and `MLMAXRT0` are valid same-run
entry/return witnesses for `ml_get_max_cpus()`. The remaining cf8 value is the
little-endian codeword `CPCNUR00`; the source comment `CPCRUN00` is stale and
cannot override the codeword. This narrows the R119 correction; it does not
advance the boundary into BSD or later subsystems.

The repaired repository gate is
`scripts/y35a/verify_marker_ownership.py`. Its R119 negative-control report
still fails, as required, on the unaligned `POSTVMR00`, duplicate offsets, and
the stale `CPCRUN00` name. The R120b candidate has no linked package/probe
manifest, so its carrier binding remains unresolved and no device run is
authorized.
