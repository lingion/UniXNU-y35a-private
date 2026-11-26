# STATE mixed-generation handoff after R181 correction

- Timestamp: 2026-11-25T21:00:00Z
- Scope: authoritative-state consistency only; no source, package, device, or main-line investigation changes.
- Shared state files modified: none.
- Main-line ownership respected: the active R183 skip-`cpu_data_init` build/package path was not duplicated or altered.

## Impact

`STATE.md` now announces R181 as its milestone but retains R179 under **Current gates** and **Next**. A reader following the operational sections can therefore pursue the already-withdrawn R179 boundary and overlook the accepted R181 correction. This is a handoff/interpretation hazard, not evidence that R179 raw data changed and not a reason to relax `device_run_allowed=false`.

## Evidence paths and SHA-256

| Path | SHA-256 | Evidence |
|---|---|---|
| `/Users/lingion_k/unixnu-research/UniXNU-y35a/STATE.md` | `41f803421ec61a492608f8b3a8eaeebc2dc1c4a4f6a9a143bb2fb200af6a60c6` | Line 4 says R181; lines 10–11 and 13–15 still make R179 the current gate and next offline task |
| `/Users/lingion_k/unixnu-research/UniXNU-y35a/docs/coordination/claude-codex-sync/CURRENT.md` | `d03de53ffd3d7e03497fb57158bfbe48b9e8b3bf1301a4878868b88a4b06dd5b` | Lines 1–3 record the R181 correction; line 7 retains the older R179 snapshot |
| `/Users/lingion_k/unixnu-research/UniXNU-y35a/docs/coordination/claude-codex-sync/LOG.md` | `f2b6dc62fbf2363bd7df460a4d88ae549d98ee7cd23ff6b329e4bed512644a0a` | Lines 2433–2435 explicitly withdraw R179 as runtime-boundary evidence and record R181 `CPUENTR0` present / `CPUDRET0` absent |
| `/Users/lingion_k/unixnu-research/UniXNU-y35a/docs/coordination/claude-codex-sync/LONG-RUN-STATE.md` | `1b251d636cddcba5110dfa6781dd56bd1ff949d940b4478bda48ccf170ec239c` | Lines 2–4 prepend the R181 boundary; lines 7–9 retain the older R179 snapshot |

## Facts

1. `STATE.md:4` reads: `Milestone: R181 entered the actually linked arm64 cpu_data_init and stopped before CPUDRET0.`
2. The same file's `Current gates` at lines 10–11 still names only the R179 kernel `7bdebd4c...c4d6`, R179 final raw `e233afad...1778`, and the old `CPUENTR0/CPUDRET0` zero interpretation.
3. `STATE.md:13-15` still instructs the next operator to keep R179 inputs disabled and inspect the R179 linked call/prologue offline.
4. `CURRENT.md:1-3` and `LOG.md:2433-2435` agree that R181 patched the actual `osfmk/arm64/cpu.c`, freshly observed `CPUENTR0`, and did not observe `CPUDRET0`; the LOG expressly says R179 cannot support a runtime boundary claim.
5. The latest main rollout has advanced beyond the ledger to R182/R183. Those newer results are not used here to rewrite the accepted R181 finding.

## Pending confirmation

- Whether the R179-only `Current gates` / `Next` sections in `STATE.md` are intentional historical safety pins rather than an incomplete update. There is no explicit superseded/historical label on those sections.
- When the main line will atomically synchronize `STATE.md` with the accepted R181 entry and subsequent accepted runs.

## Inference

This is a partial, non-atomic state update: the milestone headline changed, but the operational gate and next-action body did not. The authoritative contradiction is internal to `STATE.md` and is independently resolved by the matching R181 correction in both `CURRENT.md` and `LOG.md`.

## Single next-step recommendation

Regenerate `STATE.md` atomically from the latest accepted ledger entry: make R181's kernel/raw binding and `CPUENTR0`-present / `CPUDRET0`-absent boundary the sole current gate, move R179 to an explicitly superseded historical note, and only promote R182/R183 after their accepted evidence is recorded.
