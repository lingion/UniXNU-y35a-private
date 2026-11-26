# UniXNU Y35A state

Updated: 2026-11-26T16:42:00Z
Milestone: R208 TF/SD source, host, root-selection, NativeSdcard object, IOStorageFamily archive and Docs gates passed in CI; native kernel link and TF root path remain pending. All local UniXNU compilation is disabled on every disk.
Authority: intended /Volumes/Mobile/unixnu-research/UniXNU-y35a; current writable metadata mirror /Users/lingion_k/unixnu-y35a-private-sync; /Volumes/Mobile currently returns I/O errors.
Device: R206 ended at verified efff9d92 / lk2nd-msm8916 / unlocked fastboot; no current device operation.
Workspace: /Volumes/Mobile/unixnu-research stores source caches, run roots, CI artifacts, backups and raw only when readable; /Volumes/Portable is temporary staging only. No local UniXNU compilation, linking or large builds. External Git metadata restored, core.filemode=false, and fsck passed.
LKG: /Volumes/Mobile/unixnu-research/device-backups/efff9d92-20261119/ has only boot.current.img and lk2nd.current.img; full backup and EDL/firehose remain unverified.
Storage candidate: user authorized future writes to the phone TF/SD card. Official Y35A data says 16GB ROM and up to 128GB TF expansion; stock dtb10 exposes removable sdhc2 with 4-bit bus and card-detect GPIO38.
SD qualification: current lk2nd/XNU path is still sdhc1 eMMC-only; SD boot, sdhc2 protocol, root mount, and exact card binding remain unverified. No SD/device write occurred.

Current gates:
- R206 offline/binding gates passed; R206 paired MVE failed after candidate boot. Do not repeat R206.
- R207 v1 was rejected before make due to corrupt patch hunk. R207 v2 patch SHA `05e9822905d6187a22009d957ffa350354ff11f53bd31b846b754b41f8f88f84` passes apply-check against R206 staged source.
- R207 v2 external builder PID 90604 was terminated per user instruction. It produced no provenance or kernel artifact. Do not restart it or run any local UniXNU build on any disk.
- R208 TF candidate is offline-only: SD protocol host suite, sdhc2 ADT contract, root-selection positive/negative contract, NativeSdcard object, IOStorageFamily combine/archive and Docs gates are green. Validation run `45855811648` (`host-validation`) and Docs run `45855811845` (`build`) passed on commit `ba4854d4cb076388f61cb2bcdbdf13efb8404dc5`. No verified kernel/package/device evidence is recorded.
- R208 object closure is bound by NativeSdcard object `47bec72ade1ff792938b9ae468f778a7d7e4c13bb62f97d18e5dbf96242e900e`, combined object `0353a170088989517d6634805f16537e26844fa89bd2acf9040dffd3cfa400fd`, and deterministic archive `f401224182f56a5d27532482c1978528ae1570c3d5b16931b98384a6aaba1e73`. Kernel link still lacks CI-bound native fakeroot/SDK overlay/source provenance and driver-link inputs; package/probe, TF image, root mount and fallback remain pending.
- Historical failures: Native runs `45838744656` and `45838740886` on commit `4c817f03fbd5a0611fadfd2675381c32ae995363` failed at `Compile NativeSdcard object`; later successful runs supersede them.

Next:
1. Produce an exact CI input manifest for native kernel link: fakeroot tree, SDK overlay tree, xcrun wrapper, source provenance, ordered patches, driver archive and driver manifest hashes.
2. Extend GitHub Actions with the bound native kernel-link and linked-Mach-O gates, then package/probe only from that exact kernel.
3. Keep runtime qualification and device_run_allowed false; do not run local UniXNU compilation on any disk.

Active agents: none. Persistent writes: none.
