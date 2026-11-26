# UniXNU Y35A state

Updated: 2026-11-26T12:00:00Z
Milestone: R208 TF/SD offline CI gate passed; all UniXNU mechanical-disk local compilation is disabled.
Authority: /Volumes/Mobile/unixnu-research/UniXNU-y35a; historical /Volumes/UniXNU-Workspace is stale.
Device: R206 ended at verified efff9d92 / lk2nd-msm8916 / unlocked fastboot; no current device operation.
Workspace: /Volumes/Mobile/unixnu-research; local UniXNU builds disabled; external Git metadata restored, core.filemode=false, and fsck passed.
LKG: /Volumes/Mobile/unixnu-research/device-backups/efff9d92-20261119/ has only boot.current.img and lk2nd.current.img; full backup and EDL/firehose remain unverified.
Storage candidate: user authorized future writes to the phone TF/SD card. Official Y35A data says 16GB ROM and up to 128GB TF expansion; stock dtb10 exposes removable sdhc2 with 4-bit bus and card-detect GPIO38.
SD qualification: current lk2nd/XNU path is still sdhc1 eMMC-only; SD boot, sdhc2 protocol, root mount, and exact card binding remain unverified. No SD/device write occurred.

Current gates:
- R206 offline/binding gates passed; R206 paired MVE failed after candidate boot. Do not repeat R206.
- R207 v1 was rejected before make due to corrupt patch hunk. R207 v2 patch SHA `05e9822905d6187a22009d957ffa350354ff11f53bd31b846b754b41f8f88f84` passes apply-check against R206 staged source.
- R207 v2 external builder PID 90604 was terminated per user instruction. It produced no provenance or kernel artifact. Do not restart local mechanical-disk compilation.
- R208 TF candidate is offline-only: SD protocol host suite, sdhc2 ADT contract, read-only NativeSdcard source, and lk2nd SD_BOOT patch gates are in progress; no kernel/package/device evidence yet.
- R208 CI plan commit `bc1dacf822dd1a2d013716dca50cbf07a09ab7c8` binds exact XNU ref and six arm-driver patches; macOS plan-only run `45812745086` passed. NativeSdcard compile, kernel link, package/probe, TF image and root mount remain pending.

Next:
1. Run R208 NativeSdcard object compile and static gates in GitHub Actions only.
2. Complete TF GPT/APFS, eMMC fallback, card-detect and root-selection contracts offline.
3. Keep runtime qualification and device_run_allowed false; do not start mechanical-disk compilation.

Active agents: none. Persistent writes: none.
