# UniXNU Y35A state

Updated: 2026-11-26T11:06:49Z
Milestone: R207 v2 no-marker control build in progress; R206 failed before candidate readback.
Authority: /Volumes/Mobile/unixnu-research/UniXNU-y35a; historical /Volumes/UniXNU-Workspace is stale.
Device: R206 ended at verified efff9d92 / lk2nd-msm8916 / unlocked fastboot; no current device operation.
Workspace: /Volumes/Mobile/unixnu-research; local UniXNU builds disabled; external Git metadata restored, core.filemode=false, and fsck passed.
LKG: /Volumes/Mobile/unixnu-research/device-backups/efff9d92-20261119/ has only boot.current.img and lk2nd.current.img; full backup and EDL/firehose remain unverified.
Storage candidate: user authorized future writes to the phone TF/SD card. Official Y35A data says 16GB ROM and up to 128GB TF expansion; stock dtb10 exposes removable sdhc2 with 4-bit bus and card-detect GPIO38.
SD qualification: current lk2nd/XNU path is still sdhc1 eMMC-only; SD boot, sdhc2 protocol, root mount, and exact card binding remain unverified. No SD/device write occurred.

Current gates:
- R206 offline/binding gates passed; R206 paired MVE failed after candidate boot. Do not repeat R206.
- R207 v1 was rejected before make due to corrupt patch hunk. R207 v2 patch SHA `05e9822905d6187a22009d957ffa350354ff11f53bd31b846b754b41f8f88f84` passes apply-check against R206 staged source.
- R207 v2 builder PID 90604 is live in external preparation; no kernel artifact yet. `device_run_allowed=false`.
- R208 TF candidate is offline-only: SD protocol host suite, sdhc2 ADT contract, read-only NativeSdcard source, and lk2nd SD_BOOT patch gates are in progress; no kernel/package/device evidence yet.

Next:
1. Let PID 90604 reach a terminal result; do not start another builder.
2. If build passes, verify no slot-0x52 writer, package fresh probes, and require all offline gates before considering a control MVE.
3. Keep runtime qualification false; AMFI, launchd, SpringBoard, touch, storage, and drivers remain unverified.

Active agents: none. Persistent writes: none.
