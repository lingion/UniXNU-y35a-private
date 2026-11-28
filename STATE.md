# UniXNU Y35A state

Updated: 2026-11-28T03:06Z
Goal: iOS 12.4.1 on Y35A. D1/D2/D3 remain IN_PROGRESS / NOT_MET; no verified Y35A iOS boot or interactive SpringBoard.
Active branch: `codex/unixnu-ci-package-v2`, latest code commit `958df9b5dad9485a55d2beaeb19b1b75420a20e3`.
Device: not queried or operated this turn. `device_run_allowed=false`; persistent writes: none.
Local UniXNU builds/tests/static gates prohibited. `/Volumes/Mobile` remains forbidden; `/Volumes/Portable` used only for a 79 MB CI artifact sidecar inspection.

## Current verified CI

- Native run `46086948983` on commit `332843f94ee4eb5cb541a5b956f1c75ba3172eb8` passed build, linked verifier and kernel artifact contract. Kernel SHA-256 `ca948860a1e99542d2e4d8e45498a45ecbf1b454d64d672f124415504fdc0137`, 12,828,688 bytes. Artifact ID `15239965878`, digest `sha256:f388776022526f45628e1d7593adc247a97198eabfbc4a1dece5782402ab5578`.
- Package run `46100598017` on `958df9b5dad9485a55d2beaeb19b1b75420a20e3` consumed that exact native artifact; validate and package jobs succeeded. TF/APFS intermediate and offline-control jobs were skipped because no stock-boot source path was supplied.
- RAM diagnostic artifact `y35a-ramboot-46100598017`, ID `15245323039`, digest `sha256:4981c4c04afd0141afb6f3a0c69f8e4d03f74da94cefb97cc406ed0347a9fc4f`.
- Root-tree artifact ID `15244974333`, digest `sha256:d3180a272f99da5cf9e36ee1add9e028ab2e396bb1c584bae3738be8fc12e55c`; single `root-tree.tar` artifact ID `15245193498`, digest `sha256:112df00c9b05ca97755c0c91d868c8c443b2607be5598d1849722a6372f31679`.
- Full iOS 12.4.1 System-volume source artifact ID `15245028918`, digest `sha256:3a06bb3c3bc0364dd0ab83e921bda45c89390f1e9226db3118fabb1d5e08ae06`, artifact size 2,826,122,994 bytes. Its contained IPSW OS image is 2,826,117,884 bytes, SHA-256 `f740ff9931061a2adc10d7b1e766cbe907346f11180014fe8ee58a2f554a9880`.
- Schema-2 source report binds `private/var`, `private/var/db`, and `private/var/mobile` as directories in the pinned j96ap/16G102 source. This is path metadata from a mounted source image; it does not prove writability, Y35A compatibility, or runtime mount. Apple introduced System/Data volume groups for iOS 13-era systems; do not make a paired group a prerequisite for the iOS 12.4.1 target. Legacy root initialization remains unverified.

## Blockers and next action

- No eligible stock PD1502A boot/QCDT bytes exist in the checked repository, artifact set, or official download sources. The original historical full boot image is recorded as exactly 67,108,864 bytes, SHA-256 `92611f876a022fb5af1138f0591f5dafe2b359a226b2f0b28d292211f2fec012`, but the file is missing. Third-party mirrors and derived DTS/QCDT are not acceptable substitutes.
- CI now fails closed: the only stock intake path is tracked `evidence/y35a-20261102/stock-boot.img`; Actions checks the historical full-image hash, extracts QCDT from the Android header dt range, binds commit/path/offset/size/hash, then rechecks the original boot bytes in the APFS consumer.
- Next code stage: add an offline-only GPT/APFS source-image control using the exact full System-volume artifact and clearly label the Y35A/boot/root-selection qualification as false; keep stock QCDT intake and production TF gate blocked on the original input.
- Complete-system runtime, linked root selection/fallback, physical TF binding, probes, device boot, and SpringBoard remain unverified. Full partition backup and EDL/firehose recovery remain unverified; persistent boot/GPT writes stay prohibited.
