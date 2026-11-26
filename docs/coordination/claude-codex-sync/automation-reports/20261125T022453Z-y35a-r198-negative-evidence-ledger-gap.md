# R198 negative paired evidence missing from authoritative ledger

- Timestamp: 2026-11-25T02:24:53Z
- Scope: offline evidence-coverage audit only; no source, package, device, or shared-state edits.
- Main-line ownership respected: R200 is sealed and the current ARMPAGE0 bracket is not duplicated.
- Finding status: new ledger-coverage gap; it does not revise the accepted R200 boundary.

## Impact

R198 is the completed negative experiment that motivated replacing `PE_state` seeding with R200's direct `BootArgs` path. Its four raw captures and exact binding evidence remain under `reboot-checkpoints`, but there is no R198 adjudication file and no R198 entry in `CURRENT.md`, `LONG-RUN-STATE.md`, or `LOG.md`. A future operator can see R200's successful fix without the registered failed precursor that explains why the fix was necessary.

R199 has only host-build artifacts and no paired-run directory. Its omission is lower impact because it did not produce runtime evidence; it should be marked superseded rather than presented as another accepted boundary.

## Evidence paths and SHA-256

### Authoritative-state snapshot

| Path | SHA-256 | Observation |
|---|---|---|
| `/Users/lingion_k/unixnu-research/UniXNU-y35a/AGENTS.md` | `ea11e40ead1e83cb46514407413aa7934f577b38ab615ab002fa97c75296841a` | Unchanged authority pointer |
| `/Users/lingion_k/unixnu-research/UniXNU-y35a/STATE.md` | `379c8622dce5ed1e8bb4063d0987d0c086a2b80733081d0f96e9a08e1ef3eb33` | Milestone and operational body both at R200 |
| `/Users/lingion_k/unixnu-research/UniXNU-y35a/docs/coordination/claude-codex-sync/CURRENT.md` | `0fbe5048df105d73f413f24359b743fd8064e489d6d2326ac7df6497638d8de7` | Newest entry R200; previous accepted entry R197 |
| `/Users/lingion_k/unixnu-research/UniXNU-y35a/docs/coordination/claude-codex-sync/LONG-RUN-STATE.md` | `4c44081a6b5bf5658dfdb0a59929a8997e6a96eb125bbd2585aa97f612dc26bf` | Newest entry R200; previous accepted entry R197 |
| `/Users/lingion_k/unixnu-research/UniXNU-y35a/docs/coordination/claude-codex-sync/LOG.md` | `20d424ef82dde3382c656c39ed4828dc24c94bb69ff7a035720532aa5f65de59` | Latest entries R200 adjudication and marker-offset correction; no R198/R199 entry |

A case-sensitive search of the three coordination files found no `R198`, `R199`, `PE_state`, `PESEEDBG`, or `PEBOOTOK` reference in their current content. The `LONG-RUN-STATE.md` R197 sentence “No R198 input exists yet” is historically accurate for R197 and is not treated as a present-day contradiction.

### R198 local evidence

| Path | SHA-256 | Evidence |
|---|---|---|
| `/Users/lingion_k/unixnu-research/reboot-checkpoints/R198-pe-state-seed-run-plan-20261125-01/R198-RUN-PLAN.json` | `953569ef520b0a7ce949efe8b95f999f1394e279b50c8ccfacf86065f13ace73` | One paired MVE; `PEBOOTOK` is the runtime witness; carrier `0xa0bb0b00` |
| `/Users/lingion_k/unixnu-research/reboot-checkpoints/R198-pe-state-seed-design-20261125-01/R198-corrected-binding-gate.json` | `0b8b2ae01ab56ce38da2d8ccd5671ae241846e7868d4b01d13ce2b5fe7acbb78` | Corrected package/probe binding passed with no failures |
| `/Users/lingion_k/unixnu-research/reboot-checkpoints/R198-pe-state-seed-corrected-regular-probe-20261125-01/readback.json` | `7d2ab8d42b3de0b067cb7d579729df62c658ccf80db84b1b836072d42f8c6ab7` | 1024-byte `precpudata-external` record uses sequential raw offset `66688`; `report_offset=1152` is record order, not a raw offset |
| `/Users/lingion_k/unixnu-research/reboot-checkpoints/R198-pe-state-seed-paired-run-20261125-01/run-summary.json` | `977b595e8a90afdc73e9a194eb4071ba2ceb5b75bffb443ffcbf30457f9705bb` | Four captures recorded; `persistent_writes=false`; generic runner status `failed` |
| `/Users/lingion_k/unixnu-research/reboot-checkpoints/R198-pe-state-seed-paired-run-20261125-01/preclear.raw` | `0d11407cfd05eb3e06823b1f74bf7315a506947ab2b843a89219690beeb88571` | External carrier all zero |
| `/Users/lingion_k/unixnu-research/reboot-checkpoints/R198-pe-state-seed-paired-run-20261125-01/baseline.raw` | `d07e7495941425326928e856495555ece40fe04b46397c37f986c17ed393a7f9` | External carrier all zero |
| `/Users/lingion_k/unixnu-research/reboot-checkpoints/R198-pe-state-seed-paired-run-20261125-01/candidate.raw` | `f3466fe3fc792c0b5173c387ef29154000bafa44435ff058953296f655fcd02e` | External carrier all zero |
| `/Users/lingion_k/unixnu-research/reboot-checkpoints/R198-pe-state-seed-paired-run-20261125-01/final.raw` | `77a5156b2e81bc2db96780795f86102260cea6e02f00dbda97c94c5a452d5d3f` | Fresh nonzero carrier; negative seed result |
| `/Users/lingion_k/unixnu-research/reboot-checkpoints/R198-pe-state-seed-native-build-20261125-01/build-provenance.json` | `c74921c818aaf70b57a6481c35ee41e7358b7f51ec3d5fb0d224441f05e41190` | Records the applied R198 patch and kernel build inputs |
| `/Users/lingion_k/unixnu-research/reboot-checkpoints/R199-pe-state-minimal-native-build-20261125-01/build-provenance.json` | `b23fbe5817144b2c97eb96bea59766e23ce6c734a81c002940a7114bfcce6890` | Host-build provenance exists |
| `/Users/lingion_k/unixnu-research/reboot-checkpoints/R199-pe-state-minimal-native-build-20261125-01/kernel-artifact.json` | `fd058974311ab885a237d8e5f81497dd5e3b20b857b3ae4476ca64753fa9fbe6` | Host kernel artifact record exists |

Independent hashing of all four R198 raw files matches `run-summary.json.raw_sha256`. The R198 package kernel and boot hashes were also independently matched in the preceding offline cycle: kernel `b61a97d543da11c58c2be28607565013d845b71316cbdae1eb02a786b2fa72b1`, boot `9861f7f8c1982f23eac07995a412ce21bc3c88c3f793691c46fabcc5bde2b3c8`.

## Facts

1. R198 has a passed corrected binding gate and a complete four-stage raw set; it is not merely a proposed experiment.
2. Preclear, baseline, and candidate external carriers are all zero. The final external carrier is nonzero and contains `POSTHI00`, `REBPRE00`, `BOOTPRE0`, `BOOTPOST`, `CPUDPRE0`, `CPUDPOST`, `CPUSKIP0`, and `PEPSKIP0`.
3. The final external carrier does not contain `PEBOOTOK` or `POSTPE00`. The early-fault record contains little-endian `PEINITRT` (`TRTINIEP` bytes at raw offset `65848`). Thus the valid observation is that execution reached `PEINITRT` but did not reach the post-seed `PEBOOTOK` witness.
4. No `R198*adjudication*` file exists under the R198 checkpoint directories, and the three authoritative coordination files contain no R198 entry.
5. The top-level checkpoint inventory contains an R199 native-build directory but no R199 paired-run directory or raw captures.
6. R200 is separately and atomically represented in `STATE.md`, `CURRENT.md`, `LONG-RUN-STATE.md`, and `LOG.md`, including the corrected `ARMPAGE0` offset `0x200`. This report does not dispute R200.

## Pending confirmation

- Whether the main line intentionally treats R198/R199 as ephemeral diagnostics excluded from the authoritative ledger.
- If they are to be retained, whether a compact historical entry is sufficient or a standalone R198 adjudication JSON/Markdown pair is also desired.

## Inference

The missing R198 entry is an evidence-lineage gap, not a runtime regression and not a reason to repeat any device run. R200's direct `BootArgs` result supersedes the failed seed approach, but the failed precursor explains the design change. Registering it would make that causal chain recoverable without reading the large Codex rollout.

## Single next-step recommendation

At the next normal ledger synchronization, append one concise historical entry covering “R198 negative PE-state seed / R199 host-only precursor superseded by R200,” including the four R198 raw hashes, the `PEINITRT`-present / `PEBOOTOK`-absent observation, and “do not repeat R198.” Do not change the current R200 gate or start another run.
