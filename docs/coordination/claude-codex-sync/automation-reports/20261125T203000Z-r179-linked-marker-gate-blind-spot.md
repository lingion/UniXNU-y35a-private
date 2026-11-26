# R179-linked-marker gate blind spot (offline auxiliary audit)

- Timestamp: 2026-11-25T20:30:00Z
- Scope: offline verifier contract only. No R181 build, source patch, package edit, device access, or runtime experiment.
- Shared state files modified: none.
- Main-line ownership respected: the active `arm64/cpu.c` / R181 rebuild was not duplicated or modified.

## Impact

`verify_phase_instrumentation.py` can report `ok:true` for the exact R179 kernel even though its requested CPU entry/return markers are absent from the linked function. A green result from this default invocation therefore does **not** qualify R172–R179 diagnostic marker presence and must not be used to turn a missing runtime marker into a real execution boundary.

## Evidence paths and SHA-256

| Path | SHA-256 | Evidence |
|---|---|---|
| `/Users/lingion_k/unixnu-research/reboot-checkpoints/R179-cpu-data-init-native-build-20261125-01/obj/DEVELOPMENT_ARM64_T7001/mach.development.t7001.unstripped` | `7bdebd4c8389c353259d1a9ceb79af4f7fb17dc1cb8684f86479dc01f0e7c4d6` | Exact R179 kernel, 11,635,368 bytes |
| `/Users/lingion_k/unixnu-research/UniXNU-y35a/scripts/y35a/verify_phase_instrumentation.py` | `9668f4373a9239cc7d560bf5c139d1759c094e3eb72e1fbe4ea302ea17edf461` | Default gate implementation and CLI |
| `/Users/lingion_k/unixnu-research/reboot-checkpoints/R179-cpu-data-init-native-build-20261125-01/src/osfmk/arm/cpu.c` | `95eaef587c488280570ebc12de7fe471d67a8189486dc541fd79b63caf319f8e` | Wrong-architecture source carries guarded CPU markers at lines 324–325 and 394–395 |
| `/Users/lingion_k/unixnu-research/reboot-checkpoints/R179-cpu-data-init-native-build-20261125-01/src/osfmk/arm64/cpu.c` | `143ab7c450cd33797910ca68e4f6ea14418bacb71e578a82fc51735a876e194f` | Actual ARM64 translation unit has no CPUENTR0/CPUDRET0 or related marker-guard hits |
| `/Users/lingion_k/unixnu-research/UniXNU-y35a/STATE.md` | `0312bdc14a2e646a4bc8a1aeb6d432bf347ac410a5b4b84d0837f028c5141bc8` | Authoritative R179 snapshot read this cycle; still describes the pre-correction boundary |
| `/Users/lingion_k/.codex/sessions/2026/11/15/rollout-2026-11-15T13-41-09-01a1bbf9-dcb8-7af3-9622-ff82f0684444_01a1ddb9-47cf-7d71-b3b7-93fcd3490099.jsonl` | Not re-hashed this cycle (468,909,651 bytes at refresh) | Latest main tool result at `2026-11-24T20:17:24.440Z` independently disassembles `_cpu_data_init` with no marker call; later messages identify wrong source and guard |

## Reproduction

Read-only command shape:

```text
python3 scripts/y35a/verify_phase_instrumentation.py \
  --kernel /Users/lingion_k/unixnu-research/reboot-checkpoints/R179-cpu-data-init-native-build-20261125-01/obj/DEVELOPMENT_ARM64_T7001/mach.development.t7001.unstripped
```

Observed result:

```json
{
  "kernel": "/Users/lingion_k/unixnu-research/reboot-checkpoints/R179-cpu-data-init-native-build-20261125-01/obj/DEVELOPMENT_ARM64_T7001/mach.development.t7001.unstripped",
  "ok": true,
  "failures": []
}
```

Exit status: `0`.

## Facts

1. The verifier's generation-specific CLI stops at R93 (`verify_phase_instrumentation.py:5254-5277`). Its dispatch covers the base handoff/arm-init checks and R82–R93 contracts (`:5311-5398`), with no R172–R179 marker contract.
2. The verifier contains no `CPUDPRE0`, `CPUENTR0`, `CPUDRET0`, `HIDPRE00`, `HIKSPI00`, or `POSTHI00` definitions or required-marker checks.
3. The exact R179 kernel contains zero contiguous ASCII occurrences of `CPUENTR0` and `CPUDRET0`. This byte search is corroborating evidence only: the also-absent contiguous `CPUDPRE0` demonstrates that runtime-observed markers can be materialized as instruction immediates rather than ASCII data.
4. The staged wrong-architecture `osfmk/arm/cpu.c` contains both CPU marker calls under `XNU_NATIVE_EARLY_FAULT`; the staged `osfmk/arm64/cpu.c` contains none. The latest main linked disassembly independently shows `_cpu_data_init` beginning with field stores and no call to `_native_phase_marker_external`.
5. Main's latest rollout states the two root causes: the wrong architecture file was edited, and the guard macro did not enable the marker in the actual translation unit. R181 is already rebuilding the corrected `arm64/cpu.c`; this report does not alter that work.

## Pending confirmation

- Whether any separate R179 package/run gate, outside this verifier invocation, independently required the linked CPU markers. This audit proves a blind spot in `verify_phase_instrumentation.py`, not that every gate in the repository was absent.
- Whether the shared state documents will be corrected to withdraw the runtime-boundary interpretation. They still contained the old R179 wording at the hash-binding point above.
- The final R181 linked marker presence remains a main-line build result and was not inspected or qualified here.

## Inference

The default verifier is a legacy/base-contract gate, not a generation-complete diagnostic gate. Without an explicit linked-marker requirement, `ok:true` means only that the checks it actually implements passed; it cannot establish that a newly added runtime marker exists. R179's missing `CPUENTR0/CPUDRET0` is therefore a marker-delivery false negative, not evidence of a stop at `cpu_data_init`.

## Single next-step recommendation

Add one required linked-marker contract for each diagnostic generation before packaging: for R179, require exactly one `_native_phase_marker_external(0x28, CPUENTR0)` entry call and one `(0x2a, CPUDRET0)` return call inside `_cpu_data_init`, and keep the exact R179 kernel above as a negative regression fixture that must fail the gate.
