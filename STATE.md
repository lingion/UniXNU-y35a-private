# UniXNU Y35A state

Updated: 2026-11-26T20:29:24Z
Milestone: R208 TF/SD source, host, root-selection, NativeSdcard object, IOStorageFamily archive and Docs gates passed in CI; native execute build is blocked in CI input preparation before kernel link. All local UniXNU compilation is disabled on every disk.
Authority: intended /Volumes/Mobile/unixnu-research/UniXNU-y35a; current writable metadata mirror /Users/lingion_k/unixnu-y35a-private-sync; /Volumes/Mobile currently returns I/O errors.
Device: R206 ended at verified efff9d92 / lk2nd-msm8916 / unlocked fastboot; no current device operation.
Workspace: /Volumes/Mobile/unixnu-research stores source caches, run roots, CI artifacts, backups and raw only when readable; /Volumes/Portable is temporary staging only. No local UniXNU compilation, linking or large builds. External Git metadata restored, core.filemode=false, and fsck passed.
Staging: /Volumes/Portable/UniXNU-staging-20261127-0042; manifest SHA a4d970a878c88c8e21dbfeeca086f78d2f8fad0b09180584048b4430ee0d8538; source commit 68b2cf91038fedb1ccacdc5950223ef618d8215e; 1424/1424 verified.
LKG: /Volumes/Mobile/unixnu-research/device-backups/efff9d92-20261119/ has only boot.current.img and lk2nd.current.img; full backup and EDL/firehose remain unverified.
Storage candidate: user authorized future writes to the phone TF/SD card. Official Y35A data says 16GB ROM and up to 128GB TF expansion; stock dtb10 exposes removable sdhc2 with 4-bit bus and card-detect GPIO38.
SD qualification: current lk2nd/XNU path is still sdhc1 eMMC-only; SD boot, sdhc2 protocol, root mount, and exact card binding remain unverified. No SD/device write occurred.

Current gates:
- R206 offline/binding gates passed; R206 paired MVE failed after candidate boot. Do not repeat R206.
- R207 v1 was rejected before make due to corrupt patch hunk. R207 v2 patch SHA `05e9822905d6187a22009d957ffa350354ff11f53bd31b846b754b41f8f88f84` passes apply-check against R206 staged source.
- R207 v2 external builder PID 90604 was terminated per user instruction. It produced no provenance or kernel artifact. Do not restart it or run any local UniXNU build on any disk.
- R208 TF candidate is offline-only: SD protocol host suite, sdhc2 ADT contract, root-selection positive/negative contract, TF/eMMC fallback contract, NativeSdcard object, IOStorageFamily combine/archive and Docs gates are green. Main validation run `45884101324` (`host-validation`) and Docs run `45884101618` (`build`) passed; latest TF validation `45887232679` passed all jobs on main commit `425ec007c2973fc14c81f64f14898138340cca3c`. No verified kernel/package/device evidence is recorded.
- R208 object closure is bound by NativeSdcard object `47bec72ade1ff792938b9ae468f778a7d7e4c13bb62f97d18e5dbf96242e900e`, combined object `0353a170088989517d6634805f16537e26844fa89bd2acf9040dffd3cfa400fd`, and deterministic archive `f401224182f56a5d27532482c1978528ae1570c3d5b16931b98384a6aaba1e73`. Native plan-only run `45882865622` passed on main commit `53966d60ea558dae8a12c795736e8418bcc8cca9`; no kernel artifact exists because execute=false. Fallback implementation remains unverified even though its offline contract is green; candidate patch `native-y35a-tf-emmc-root-fallback.patch` is apply-check verified but not in native build inputs.
- Native execute run `45888048634` on commit `2b45f50b143edf19c678892dab0d768a5e378f61` failed before kernel build because `run_native_build.py` found the staged XNU checkout dirty after host-tool preparation; no kernel artifact was emitted. This is a CI input-preparation blocker, not a kernel or driver result. The isolated fix must restore `bsd/kern/makekdebugevents.py` before source snapshot and pass a new CI run.
- Historical failures: Native runs `45838744656` and `45838740886` on commit `4c817f03fbd5a0611fadfd2675381c32ae995363` failed at `Compile NativeSdcard object`; later successful runs supersede them.

Next:
1. Land and validate the isolated native-input restoration fix, then run one `execute=true` native build on the exact package-stage SHA.
2. Use that successful run's `unixnu-kernel-${run_id}` artifact as the only package input; package/probe and TF/root/fallback gates remain downstream.
3. Keep runtime qualification and device_run_allowed false; do not run local UniXNU compilation on any disk.

Active agents: none. Persistent writes: none.
