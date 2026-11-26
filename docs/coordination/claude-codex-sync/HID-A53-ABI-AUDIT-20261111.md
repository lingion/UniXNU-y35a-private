# Apple HID Encodings on Cortex-A53: Architectural Status and Access Semantics

Date: 2026-11-11. Owner: Claude (assigned in `CURRENT.md`: "Claude is checking the
architectural status and A53 access semantics of the six Apple HID encodings").
Read-only offline audit. No device interaction, no build, no writes to files owned by
the concurrent editing session.

## Inputs and provenance

- Linked v5 kernel: `evidence/y35a-20261102/boot3-20261106/phase-r68e7-store-boundary-v5-20261111/kernel/kernel.macho`,
  SHA-256 `e22fb0cde89756b0eba152ae6b2a278aabfbe9fb109f507f9f04c0e2962f60a5`
  (matches the authoritative v5 kernel hash in `CURRENT.md`).
- Source of truth for encodings: `pexpert/pexpert/arm64/arm64_common.h` and
  `osfmk/arm64/start.s` from `upstream-refresh/2026-11-11/sources/xnu-ios12/repo`
  (xnu-4903.270.47 line).
- Cold-start assembly listing: same evidence directory, `start.s`.
- A53 register model cross-reference: ARM Trusted Firmware `lts-v2.8.10`,
  `include/lib/cpus/aarch64/cortex_a53.h` (fetched 2026-11-11 via GitHub API).

## Finding 1 — The six HID encodings are confirmed present, unconditional, in the linked cold-start path

Raw 32-bit words from the linked Mach-O (decode rule: `0xd5` top byte, op0 bits 20-19,
L bit 21, op1 bits 18-16, CRn bits 15-12, CRm bits 11-8, op2 bits 7-5, Rt bits 4-0):

```text
0xfffffff007270868  d5181000  msr  SCTLR_EL1,  x0     (S3_0_c1_c0_0)
0xfffffff00727086c  d5033fdf  isb  sy
0xfffffff007270870  d538100b  mrs  x11, SCTLR_EL1     (post-ISB read-back)
0xfffffff007270874  f904e68b  str  x11, [x20, #0x9d0] (first post-ISB data store)
0xfffffff0072708d4  d518d080  msr  TPIDR_EL1, x0
0xfffffff0072708d8  d538f40c  mrs  x12, HID4          (S3_0_c15_c4_0)
0xfffffff0072708e4  d518f40c  msr  HID4, x12
0xfffffff0072708e8  d538f00c  mrs  x12, HID0          (S3_0_c15_c0_0)
0xfffffff0072708f0  d518f00c  msr  HID0, x12
0xfffffff0072708f4  d538f10c  mrs  x12, HID1          (S3_0_c15_c1_0)
0xfffffff0072708fc  d518f10c  msr  HID1, x12
0xfffffff007270900  d538f30c  mrs  x12, HID3          (S3_0_c15_c3_0)
0xfffffff007270908  d518f30c  msr  HID3, x12
0xfffffff00727090c  d538f50c  mrs  x12, HID5          (S3_0_c15_c5_0)
0xfffffff007270918  d518f50c  msr  HID5, x12
0xfffffff00727091c  d538f80c  mrs  x12, HID8          (S3_0_c15_c8_0)
0xfffffff007270928  d518f80c  msr  HID8, x12
```

Every access is a read-modify-write pair (`mrs` then `msr`), six registers, twelve
accesses in `0x2708d8..0x270928`. A full instruction scan of the block
(`0x2708d8..0x270930`) found zero conditional or unconditional branches: the block is
straight-line and executes unconditionally whenever this code path runs.

The same six encodings also appear in two further kernel sites
(`0x273db0..0x273ef0`, likely the secondary/idle CPU bring-up) and HID4 additionally at
`0x2566a0..0x2566bc`. Counts across all of `__TEXT_EXEC`: HID0 3/3, HID1 3/3,
HID3 3/3, HID4 4 mrs / 5 msr, HID5 1/1, HID8 1/1 (mrs/msr). This audit covers the
cold-start site; the later sites inherit the same semantics.

## Finding 2 — No runtime guard exists; the gate is compile-time only, and it is compiled in

- The block sits under `#if defined(APPLECYCLONE) || defined(APPLETYPHOON)`
  (`start.s:1297`). The T7001 board profile defines `APPLETYPHOON`
  (`board_config.h:37-44`), so the block is unconditionally present in this Mach-O.
- There is no MIDR/MPIDR-based runtime dispatch anywhere between the SCTLR witness
  store (`0x270874`) and the block: no `mrs` of MIDR_EL1 or MPIDR_EL1 occurs in that
  range (scanned `0x270600..0x2708d0`, zero hits).
- The `ARM64_READ_EP_SPR`/`ARM64_WRITE_EP_SPR` EHID4 dispatch collapses: `IS_PCORE`
  and the EP_SPR e-core branches exist only under `#if defined(APPLEMONSOON) ||
  HAS_CLUSTER`; neither is defined for T7001, so the macros degrade to the plain
  p-core/non-AMP form. Confirmed in the binary: `EHID4` (`S3_0_c15_c4_1`) has zero
  accesses anywhere in the linked kernel.

## Finding 3 — None of the six encodings exists in the Cortex-A53 programming model, and none collides with one

Apple's HID family occupies `op0=3, op1=0, CRn=15, op2=0, CRm in {0,1,3,4,5,8}`.
Cortex-A53's implementation-defined registers (TF-A `cortex_a53.h`, lts-v2.8.10) are:

```text
S3_1_C15_C0_0  L2ACTLR_EL1
S3_1_C15_C2_0  CPUACTLR_EL1
S3_1_C15_C2_1  CPUECTLR_EL1
S3_1_C15_C2_2  MERRSR_EL1
S3_1_C15_C2_3  L2MERRSR_EL1
S3_1_C11_C0_3  L2ECTLR_EL1
```

A53's control registers all use `op1=1`; Apple's all use `op1=0`. There is no
same-address collision (an earlier working hypothesis that Apple HID1 aliases A53
CPUACTLR_EL1 is wrong: CPUACTLR_EL1 is `S3_1_C15_C2_0`, not `S3_0_c15_c1_0`).
`S3_0_C15_C{0,1,3,4,5,8}_0` are absent from the A53 register table entirely.

## Finding 4 — Access semantics on A53: UNDEFINED, and the pair makes it fail at the first instruction

Under the ARMv8 architecture, an access to an unimplemented System register is
UNDEFINED: it raises a synchronous exception with EC=0b000000 (unknown or undefined
access to a System register). For Cortex-A53 specifically, the TRM lists only the
implemented encodings above; the behavior for the unlisted `op1=0` family is governed
by that architectural rule. (TRM-verbatim confirmation of the A53 reserved-encoding
clause remains an open cross-check; the architectural rule itself is not in doubt.)

Because every register is read *before* it is written, the first faulting instruction
on A53 is the `mrs` at `0x2708d8` (HID4 read) — the fault precedes any `msr`.

## Finding 5 — Position relative to the current boundary: not today's blocker, next deterministic fault

The block executes strictly after the SCTLR write, ISB, post-ISB read-back, and the
first post-ISB data store (`0x270868..0x270874`). Current v5 evidence shows the
post-ISB witness region reading zero, which means execution has not been proven to
complete even the store at `0x270874`. Therefore:

1. The HID accesses cannot explain the missing witness — they are downstream of it.
   This matches and sharpens the earlier note ("a compatibility risk, not an
   explanation for the earlier missing witness").
2. If boot ever advances past `0x270874`, the first unguarded instruction that cannot
   execute on A53 is `mrs x12, S3_0_c15_c4_0` at `0x2708d8`. On A53 that is a
   synchronous UNDEFINED exception, taken via the VBAR configured at `0x270844` —
   inside the same cold-start window, before `panic_init`/console.
3. The exception path depends on the TPIDR_EL1 → CPU-data → vector-table chain
   (Copilot's exception audit). `msr TPIDR_EL1, x0` at `0x2708d4` zeroes the thread
   pointer immediately before the block, so a synchronous fault raised here enters a
   handler whose per-CPU data pointer is null. A recursive fault is the expected
   outcome, consistent with silent early death rather than a captured fault record.

## Consequences for experiment design (input to Codex's line)

- Any kernel built from the T7001/APPLETYPHOON profile carries these twelve
  cold-start accesses plus the secondary-CPU sites unconditionally. On MSM8916/A53
  they are not "harmless no-ops": the architecture says they fault.
- To let the cold-start path survive past `0x2708d8`, the Typhoon tunables block
  (and the two later sites, and the `0x2566a0` HID4 site) must be patched out or
  runtime-gated by CPU part (MIDR part 0xD03 → skip). Patching out is the smaller
  change: the block's entire purpose is Cyclone/Typhoon microarchitectural workarounds
  with no A53 analogue.
- This also predicts: if a future experiment observes a fault record or hang at
  `0x2708d8`-adjacent state after crossing the SCTLR witness, this block — not the
  MSR/ISB pair — is the cause.

## Corrections to prior notes

- The earlier statement "the v5 linked path executes Apple HID4 and HID0/1/3/5/8
  reads/writes after the SCTLR witness region" is confirmed and extended here: the
  accesses are read-modify-write pairs, unconditional, with no runtime guard, and the
  first instruction that can fault on A53 is the HID4 `mrs` at `0x2708d8`.
- The working hypothesis that Apple `HID1` (`S3_0_c15_c1_0`) collides with A53
  `CPUACTLR_EL1` is retracted: A53 CPUACTLR_EL1 is `S3_1_C15_C2_0` (op1=1). No
  collision exists; the Apple family is simply absent from A53.

## Open items

- TRM-verbatim check of the Cortex-A53 reserved-encoding behavior clause (expected:
  UNDEFINED) — architectural rule already supports the conclusion.
- Per-core survey: MIDR sample `0x410fd030` (r0p0) is one PE; all eight A53 PEs on
  this SoC share the same core type, so the finding generalizes within this SoC.
- The two later HID sites (`0x273db0..0x273ef0`) and the `0x2566a0` HID4 site need the
  same patch-out treatment if their callers run on A53.
