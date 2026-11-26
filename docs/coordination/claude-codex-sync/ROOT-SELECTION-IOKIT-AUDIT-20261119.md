# Root selection / IOKit control-flow audit, 2026-11-19

This audit is independent and read-only with respect to drivers and build scripts. It uses the supplied kernel Mach-O, the R344 boot images and readbacks, the APFS OS DMG, and the actual `IOKitBSDInit.cpp` source snapshot. No device operation was performed as part of this audit.

## User requirements mapped to evidence

| Requirement | Evidence | Result |
|---|---|---|
| Determine what `rd=uuid` and `boot-uuid` really do | `IOKitBSDInit.cpp:455-584`, `boot-uuid-media` resource matching at `:217` | `rd=uuid` is the only boot-argument branch that publishes `boot-uuid` and waits for `boot-uuid-media`. `boot-uuid=<value>` supplies the exact UUID string. |
| Determine what `osenvironment=default` really does | Source snapshot has no `osenvironment` reference in `IOKitBSDInit.cpp`; the generated ADT contains the string but root selection does not consume it | It is not a root selector in this kernel. It cannot replace `rd=uuid`. |
| Confirm nested userdata APFS behavior | Mounted and inspected `/private/tmp/y35a-ios12-os-raw-20261119.cdr.dmg`, then detached it; `diskutil apfs list` / `diskutil info` | The image has one APFS container and one visible OS volume, `943918E9-4137-3834-886B-D09BB564C585`. There is no nested Data/userdata volume inside this image. The root volume is itself nested under a GPT Apple_APFS physical store. |
| Confirm `IOGUIDPartitionScheme` vs `IOApplePartitionScheme` | `IOGUIDPartitionScheme.cpp:700`, `IOApplePartitionScheme.cpp:557-661`, `IOMedia.cpp:124` | GUID scheme publishes partition `UUID` on each `IOMedia`; Apple scheme publishes only content hint/name/location/base. The UUID-based path therefore requires the GUID scheme. Matching by `Apple_HFS` content would not describe this APFS volume. |
| Identify latest verified and latest candidate boot image | R344 package directories and run logs | R344 `04` is the image used by the three 10:33-10:45 runs. R344 `05`/`06` add `rd=uuid boot-uuid=...` but have no device run. |
| Provide a dedicated verifier and test | `scripts/y35a/verify_root_selection_contract.py`, `tests/test_y35a_root_selection_contract.py` | Four focused contract tests pass; the real R344 inputs produce a FAIL verdict because no captured run proves root selection. |

## Source-grounded control flow

`IOFindBSDRoot()` first parses `rd` or `rootdev` at `IOKitBSDInit.cpp:455-458`. If the value is `uuid`, lines 568-587 publish a `boot-uuid` resource and call `IOUUIDMatching()`, which is `IOService::resourceMatching("boot-uuid-media")` at line 217. `IOService::resourceMatching()` builds an `IOResources` table keyed by `IOResourceMatch`, so this wait depends on a provider publishing `boot-uuid-media`, not merely on an `IOMedia` UUID property existing.

If no matching dictionary is established, lines 593-603 fall back to `IOMedia` with `Content=Apple_HFS`. That is an HFS+-specific fallback and cannot select an APFS OS volume by UUID.

The `-chosen` path at lines 471-484 is a separate fast path: if `/chosen/boot-uuid` exists, it logs `rooting via boot-uuid from /chosen`, publishes the resource, and uses the same `boot-uuid-media` matching. It does not require `rd=uuid`. The supplied generated ADT has no `/chosen/boot-uuid`, so the R344 images must use the boot-args branch.

`osenvironment=default` is present in the generated ADT, but `IOKitBSDInit.cpp` contains no `osenvironment` token. The only matches in the build tree are public sysctl header declarations, not root-selection code. It is not evidence of an APFS root decision.

## APFS image facts

`hdiutil imageinfo` shows the DMG is an uncompressed raw GUID-partitioned image:

- GPT partition 1: EFI System Partition, UUID `25BF40EB-3128-45AB-9E50-F92CD59AFCCB`.
- GPT partition 2: Apple_APFS (`7C3457EF-0000-11AA-AA11-00306543ECAC`), partition UUID `E71FEFC4-7D33-4E22-B393-2EA1A3527495`, start LBA 409640, length 8745512 sectors, 4,477,702,144 bytes.
- Container UUID: `AEFAA0BB-550F-4E4E-8FE5-808B93C80ECB`.
- One OS volume: `PeaceG16G102.J81J82J85mJ86mJ87mJ96J97OS`, Volume UUID `943918E9-4137-3834-886B-D09BB564C585`, 3,933,454,336 bytes used, read-only mount, APFS case-sensitive.
- No Data/userdata volume appears in the container. Therefore the nested userdata volume is outside this supplied DMG; this audit cannot prove that `943918E9...` is a userdata volume UUID. It is the OS volume UUID.

The verifier's GPT parse intentionally distinguishes three identities:

1. GPT partition type `7C3457EF-...` marks a physical store an APFS container can claim.
2. GPT partition UUID `E71FEFC4-...` is what `IOGUIDPartitionScheme` publishes as `IOMedia.UUID`.
3. APFS Volume UUID `943918E9-...` is inside the container and is the value used by `boot-uuid=`.

These are not interchangeable. `boot-uuid=943918E9...` requires an APFS-aware provider to publish a `boot-uuid-media` resource for the volume; a plain GUID partition scan cannot do that by itself.

## R344 image identity and run status

| Path | SHA-256 | Command line |
|---|---|---|
| `r344-apfs-root-package-20261119-03/boot3.img` | `6c5c0d858f9d4fe6ea64507d01d286cdd456840022e9c7b223162e15e59dc6c0` | default, generated from `-v serial=3 cpus=1 debug=0x8`; `rd=uuid` appears only as an unrelated kernel string |
| `r344-apfs-root-package-20261119-04/boot3.img` | `9c3cb4064e273ac97bfd9777c6562088142ffc001fae5a818ac8517f6aed2a61` | `-v serial=3 cpus=1 debug=0x8` |
| `r344-apfs-root-package-20261119-05/boot3.img` | `615cfaf1b0f65740807341c8e8f8465bf4cde51422af7c51ceb27aa2eb3c90de` | `-v serial=3 cpus=1 debug=0x8 rd=uuid boot-uuid=943918E9-4137-3834-886B-D09BB564C585` |
| `r344-apfs-root-package-20261119-06/boot3.img` | `8eb098cbb0f52300e9dad39a54e5b0286f1f50eeed753d44f6a79345ce6178f5` | same as `05`, different shim placement |

All four images embed kernel `0aa286cbfb1da9a8b5ac02dd06e840db3bad1333664991ad46cc0f7b17f56545`. The three final readbacks from 10:35, 10:39 and 10:45 all begin with `Y35ARD01` and the matching kernel prefix `0aa286cbfb1da9a8`, so they are fresh for that kernel generation.

The readbacks contain `-v serial=3 cpus=1 debug=0x8` at staged offset `0x23c` and `-v serial=3 cpus=1 debug=0x8 rd=md0` at `0x107fc`. They contain no `rd=uuid`, no `boot-uuid=`, no `rooting via boot-uuid`, no `Waiting for boot volume with UUID`, and no `BSD root:`. The command line at `0x107fc` is retained boot-args text inside the captured panic/readback window, not proof that the current run selected a root. The timing and image diff show the three runs used package `04`, whose handoff command line has no `rd=uuid`. Package `05`/`06` were built after those runs and have no matching readback.

Consequently no supplied final.raw proves APFS root selection. It proves only that the R344 kernel reached the early startup witness chain under `rd=md0`-era retained evidence.

## Minimal falsifiable repair contract

The next candidate must satisfy all of the following before anyone claims APFS root selection:

1. Use package `05` or `06`, whose embedded handoff command line is exactly `-v serial=3 cpus=1 debug=0x8 rd=uuid boot-uuid=943918E9-4137-3834-886B-D09BB564C585`.
2. The captured raw must have `Y35ARD01`, the kernel SHA-256 prefix `0aa286cbfb1da9a8`, and a fresh command-line copy containing `rd=uuid boot-uuid=943918E9-4137-3834-886B-D09BB564C585`. A raw containing only `rd=md0` fails.
3. The raw must contain `rooting via boot-uuid from /chosen` or `Waiting for boot volume with UUID 943918E9-4137-3834-886B-D09BB564C585`, proving `IOFindBSDRoot()` entered the UUID branch.
4. The raw must contain `BSD root:` with a non-zero major/minor, proving that `boot-uuid-media` resolved to a BSD media object.
5. The verifier must exit with status `PASS` on the same five input roles. If it exits `FAIL`, no follow-on claim about APFS mount, launchd, or userland is permitted.
6. `osenvironment=default` must not be cited as the cause of either success or failure; it is not read by this root-selection code.

The verifier deliberately treats these as falsifiers, not success narrative: a wrong UUID, a missing `rd=uuid`, a retained `rd=md0` command line, a stale kernel prefix, or absent root-selection logs all produce `FAIL`.

## Verification performed

- `python3 tests/test_y35a_root_selection_contract.py -v`: 4 tests, all pass.
- `python3 scripts/y35a/verify_root_selection_contract.py <package-05/boot3.img> <package-01/kernel-packed.macho> <run-03/final.raw> <APFS dmg> <IOKitBSDInit.cpp>`: `FAIL` with the two expected root-selection evidence failures.
- APFS image was attached read-only and detached; no device was contacted; no drivers or build scripts were modified.
