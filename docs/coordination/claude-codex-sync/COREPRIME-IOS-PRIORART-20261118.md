# coreprime-ios prior art for the AMFI/dyld and MSM8916 blockers, 2026-11-18

Source: https://github.com/tadashiutau/coreprime-ios (single commit `3af5f9c`, published 2026-11-04,
upstream HakiOS base `96ffbc532e970f3540885755d457e401e04d4707`).
User directive 2026-11-18: take it and use it directly ("发给 codex 让他直接拿来用").

Local copies (all read-only references, nothing merged into the build yet):

- `~/unixnu-research/coreprime-ios-priorart/` — full clone of their repo:
  `loader/` (native lk2nd→XNU loader, bringup-launchd.c, prepare-cache-signatures.py,
  coreprime_crypto_emul.h + host KAT test, mmc-readonly probe, build/package/run scripts),
  `shim/`, `hakios-patches/` (HakiOS `git diff` + generated-tree patches + new driver files),
  `docs/REPORT.md` (their full engineering log, every run keyed by SHA-256).
- `~/unixnu-research/coreprime-ios-priorart/hakios-upstream/` — pulled from upstream
  `oosexgang/hakios-xnu-kernel` at their base commit: `hakios-base-96ffbc5.patch`
  (SHA-256 `0d3f8ae3b78e78f611448f8563dfe41d16333413d38bb75a155315a508f65b8e`, 137181 B) and
  `minimac-stub/` containing the three files the patch registers but does not carry inline:
  `kern_minimac.c` (369 lines), `miniamfi.c` (264 lines), `miniamfi_entitlements.cpp` (123 lines).
- Evidence label per our sync rules: their hardware results are **self-reported** (no third-party
  repro, no raw logs in the repo; internal consistency and detail level are strong). The source
  code itself is **directly read and verified present** as described below.

## Why this matters to the current R150–R268 state

They run Apple userland on the same SoC family (SM-G360T1, MSM8916, 4x Cortex-A53 r0p3,
MIDR 0x410fd030, ISAR0 = 0x10000: no ARMv8 crypto, no PSCI in stock TrustZone, lk2nd RAM-boot
only) — and their Apple `launchd.darwin` is PID 1, SpringBoard reaches the home screen with
touch. Their iOS 16 userland gets through exactly the gate our R152/R154/R155+ line is stuck on:
dyld's `__mac_syscall("AMFI", ...)` policy check.

**Their answer to AMFI is not a graft — it is a ~750-line in-tree MAC policy stand-in.**
HakiOS registers a minimal AMFI policy (`minimac_policy_init()` called from
`kernel_bootstrap_thread`, `bsd/kern/kern_minimac.c`) with just two ops, and it is designed as:

1. `mpo_policy_syscall`: request `0x5a` (AMFI_SYSCALL_CHECK_DYLD_POLICY — the very call our R154
   measured as `ENOPOLICY=103` and which produces our `amfi_check_dyld_policy_self()` initproc
   panic) replies `AMFI_DYLD_OUTPUT_ALLOW_ALL = 0xff`; request `0x60` (query boot-arg state)
   replies `0x86` (not enforcing); everything else returns ENOPOLICY as before.
2. `mpo_vnode_check_signature`: sets `CS_SIGNED`, and for any `CS_ADHOC` blob sets
   `CS_PLATFORM_BINARY`. That is what keeps stock `launchd` from refusing system daemons — and it
   also **dissolves our R152 trust-coverage gap** (56/58 covered, `bin/df`/`bin/ps` missing): with
   this op, trust-cache coverage is not consulted at all.
3. Companion sandbox stand-in answers every query "allowed" and reports the container, so
   launchd's service lookups proceed.
4. `libkern/amfi/miniamfi.c` replaces Apple's closed cs validation glue ("this kernel runs
   whatever it is given"); `miniamfi_entitlements.cpp` returns an empty entitlement for
   `CS_OSSignatureFlag`-style queries so tools do not die on nil.

This directly contradicts the "graft the real 16G102 AMFI/CoreTrust closure" premise that R155–R268
have been grinding on (8 missing pmap/PPL exports, legacy prelink relocation, KASLR binding). The
prior-art route: keep enforcement structurally intact (the dispatcher stays real), register the
minimal policy, and let ad-hoc/platform flags flow. It is the same trust model our IPSW-derived
ad-hoc signatures already assume. Their REPORT shows the same trick chain for iOS 16: 43
F_ADDSIGS registrations of locally re-derived 4K CodeDirectories → dyld lists real Apple dylibs →
first genuine Apple `/bin/df` → launchd PID 1 → SpringBoard home screen.

Caveats specific to our iOS 12 target, before anyone copies code:

- The 16K-page-shift cache re-derivation (`prepare-cache-signatures.py`, kernel "disallowing
  unsupported code signature page shift: 14") is an iOS 16.x dyld-cache artifact. Our 16G102 j96ap
  cache is already page-shift 12; likely we do NOT need the re-derivation, only the policy stub.
  Verify against our own cache before porting.
- The `CS_ADHOC → CS_PLATFORM_BINARY` rule assumes launchd-era checks on iOS 12's launchd build;
  their evidence is launchd from iOS 16 (xnu-8796). Expect at minimum an equivalent
  `mac_proc_check_launch_constraints` / persona path audit on 4903 — our boot uses the same
  official launchd that panicked at `amfi_check_dyld_policy_self`, so the same 0x5a handler is
  the first thing to test.
- Do not let the stub's existence be read as "enforcement removed": it registers a real named
  policy with real ops. Our docs' constraint "keep AMFI enforcement intact" was aimed at
  constant-return hacks to the dispatcher; this is a policy, not a bypass of `__mac_syscall`.
  Codex owns that call.

## Second directly reusable block: no-PSCI secondary cores on this exact silicon

`hakios-patches/generated-*` + their `psci_smp.c` change implement what our P3 glue still lacks:
lk2nd on MSM8916 leaves only cpu@1 in its spin-table (shared release word at `0x86700088`,
`wfe; ldr; cbz; br` pen) and cpu@2/@3 are **never powered up**; their loader writes APCS ACC
PWR_CTL (`0x0b0a8000/0x0b0b8000 + 0x04`, GATE_CTL `+0x14`; sequence from Linux
`msm8916_cortex_a7_release_secondary`) to bring 2/3 up through TrustZone's cold-boot address,
then chains all parked cores into a per-core holding pen (`cp_pen_slot[Aff0]`) and republishes
`cpu-release-addr` per node in the FDT it hands the kernel. Kernel side: a cpu node with
`cpu-release-addr` is released by writing the slot address (ml_io_map + dsb + sev), never calling
PSCI, cores park in WFI. Result: `4 processors running` on hardware. Same lk2nd, same TrustZone,
same board family as Y35A — the register-level parts port 1:1; the addresses need re-derivation
from Y35A's lk2nd/DT.

## Third: crypto-extension emulation (likely our next landmine, after AMFI)

Apple `libcorecrypto` on arm64 executes `AESE` unconditionally (their proof: 888 `aese` in
libcorecrypto, commpage capability tests only check DIT bit 57, not bit 24). Our A53 has no
crypto. They solve it with an EL0 undefined-instruction trap-and-emulate in `sleh.c` before
`handle_uncategorized`: full AESE/AESD/AESMC/AESIMC, SHA1C/P/M/SU0/H/SU1, SHA256H/H2/SU0/SU1,
PMULL/PMULL2, computed from ARM ARM pseudocode on saved V regs, PC+4 on success, normal SIGILL
otherwise; host KAT covers FIPS-197 + SHA vectors + PMULL 9/9. `coreprime_crypto_emul.h` is
self-contained and builds in-tree and in a host test unmodified. Apple binaries untouched.
Note our iOS 12 corecrypto may guard with cpufeature bits instead — check before assuming we
need it, but it is cheap insurance and the host test runs as-is.

## Fourth: SD/SDHCI bring-up from lk2nd retained state

Their `drivers/storage/hakios.virtio_blk.c` extension is a working XNU read-only block backend on
MSM8916 SDHCI left initialized by lk2nd (slot 2: HC mode 1, power `0xd12`, clock `0xf007`-family;
CMD18 multi-block with auto-CMD12, ~11 MB/s after 6.6x fix; error → CMD/DAT reset + explicit CMD12
+ single-sector fallback disabled for the boot; per-command data timeout `0xe`; RCA=2 sleep CMD5
detail for eMMC). Our R194 stop is QcomSdcc probe/start never observed — their retained-state
assumption checklist (`target_uninit` deselects eMMC via CMD7 + CMD5 sleep + clears HC mode at
`core+0x78`) is the exact class of thing that makes a bring-up-time driver silently miss its
entry conditions. Device-specific register values differ on Y35A; re-derive, reuse the sequence.

## License status (checked 2026-11-18)

HakiOS upstream LICENSE: kernel-side (`xnu/files/`, `drivers/`, `hakios.patch`) is Apple XNU
derivative under APSL 2.0 (notices retained); loader/userland/tools/docs are MIT. coreprime-ios
itself has no license file, but its content is: HakiOS-derived (covered by the above) plus
original MIT-or-APSL-shaped additions (loader, input driver, crypto emul, scripts). For our
private research tree, direct inclusion is fine provided Apple/APSL notices are kept in the files
they belong to and we record the upstream commit `96ffbc5` as provenance. Nothing in the repo is
Apple IPSW content (they explicitly keep IPSW/APFS/dyld-cache material off GitHub; we already do
the same).

## Suggested adoption order (Codex owns the call)

1. Port `minimac_policy_init` + `kern_minimac.c` + `miniamfi.c` + `miniamfi_entitlements.cpp`
   into the 4903 build as a host-only experiment first (compile + link + symbol check, no boot),
   then a paired RAM-only run on `efff9d92` answering one question: does the R152-class
   `amfi_check_dyld_policy_self()` failure move to the next gate? Probe/cursor design should
   follow R259's BSS-slot approach so stale carriers cannot fake a result.
2. If (1) clears, chase the next dyld/exec refusal (likely per-image CD checks in our legacy
   prelink context, then launchd constraints), reusing their F_ADDSIGS pre-registration pattern
   only if our 16G102 ad-hoc blobs need help (page-shift 12 means probably not for the cache;
   individual binaries may still lack trust-cache entries — same fix applies).
3. Revisit `4 processors running` (APCS ACC + pen) only after single-core userland is stable;
   their loader.c `cp_pen` code and psci_smp.c patch are the reference.
4. Crypto emulation stays queued behind first-Apple-binary execution; test whether iOS 12
   corecrypto actually faults on this A53 before hooking it.

Their full run-by-run log is at `coreprime-ios-priorart/docs/REPORT.md` — every claim there is
keyed to a named hardware run and image/kernel SHA-256 on their build machine, so treat details
as their testimony, not ours.
