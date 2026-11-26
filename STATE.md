# UniXNU Y35A state

Updated: 2026-11-26T13:42:22Z
Milestone: R208 TF/SD offline gates passed; NativeSdcard object compilation remains unverified because the latest CI run failed during XNU header generation. All local UniXNU compilation is disabled on every disk.
Authority: /Volumes/Mobile/unixnu-research/UniXNU-y35a; historical /Volumes/UniXNU-Workspace is stale.
Device: R206 ended at verified efff9d92 / lk2nd-msm8916 / unlocked fastboot; no current device operation.
Workspace: /Volumes/Mobile/unixnu-research stores source caches, run roots, CI artifacts, backups and raw only; no local UniXNU compilation, linking or large builds. External Git metadata restored, core.filemode=false, and fsck passed.
LKG: /Volumes/Mobile/unixnu-research/device-backups/efff9d92-20261119/ has only boot.current.img and lk2nd.current.img; full backup and EDL/firehose remain unverified.
Storage candidate: user authorized future writes to the phone TF/SD card. Official Y35A data says 16GB ROM and up to 128GB TF expansion; stock dtb10 exposes removable sdhc2 with 4-bit bus and card-detect GPIO38.
SD qualification: current lk2nd/XNU path is still sdhc1 eMMC-only; SD boot, sdhc2 protocol, root mount, and exact card binding remain unverified. No SD/device write occurred.

Current gates:
- R206 offline/binding gates passed; R206 paired MVE failed after candidate boot. Do not repeat R206.
- R207 v1 was rejected before make due to corrupt patch hunk. R207 v2 patch SHA `05e9822905d6187a22009d957ffa350354ff11f53bd31b846b754b41f8f88f84` passes apply-check against R206 staged source.
- R207 v2 external builder PID 90604 was terminated per user instruction. It produced no provenance or kernel artifact. Do not restart it or run any local UniXNU build on any disk.
- R208 TF candidate is offline-only: SD protocol host suite, sdhc2 ADT contract, NativeSdcard scaffold, and lk2nd SD_BOOT patch gates passed their recorded offline checks. The final NativeSdcard CI compile result and bound artifact are not confirmed; no verified kernel/package/device evidence is recorded.
- R208 CI plan commit `bc1dacf822dd1a2d013716dca50cbf07a09ab7c8` binds exact XNU ref and six arm-driver patches; plan-only run `45812745086` passed. Latest native run `45831371261`, commit `794c5a7624b2ddfa0991971b6284e1971f348652`, failed at `Generate exact XNU headers` because `availability.pl` was missing; `Compile NativeSdcard object` was skipped. This is a host-header generation failure, not a NativeSdcard source compile verdict. No verified object artifact exists.

Next:
1. Verify the current R208 NativeSdcard object compile and static gates from GitHub Actions logs and bound artifacts only.
2. Complete TF GPT/APFS, eMMC fallback, card-detect and root-selection contracts offline.
3. Keep runtime qualification and device_run_allowed false; do not run local UniXNU compilation on any disk.

Active agents: none. Persistent writes: none.
