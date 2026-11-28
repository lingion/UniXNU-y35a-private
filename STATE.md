# UniXNU Y35A state

Updated: 2026-11-28T01:20Z
Goal: iOS 12.4.1 on Y35A. D1/D2/D3 remain IN_PROGRESS / NOT_MET; no verified Y35A iOS or interactive SpringBoard boot.
Active branch: `codex/unixnu-ci-package-v2`.
Device: not queried; no device/TF/USB/fastboot/adb/serial action this turn. `device_run_allowed=false`.
Persistent writes: none. Local UniXNU builds/tests/static gates prohibited. `/Volumes/Mobile` remains forbidden.

## Latest exact CI evidence

- Native run `46086948983`, commit `332843f94ee4eb5cb541a5b956f1c75ba3172eb8`: native build, linked R208 verifier and artifact contract passed. Kernel SHA-256 `ca948860a1e99542d2e4d8e45498a45ecbf1b454d64d672f124415504fdc0137`, 12,828,688 bytes. Kernel artifact ID `15239965878`, digest `sha256:f388776022526f45628e1d7593adc247a97198eabfbc4a1dece5782402ab5578`. XNU `494ffe1c29d37ca720c37328feb83069c9641b67`; fallback-v3 manifest SHA `f967a2fe75a10c83ac8ec24d55284b1391d9c27bfb58514d42e5dcb30fbc1651`.
- Package run `46087760341` dispatched against that exact native run and succeeded. RAM diagnostic artifact ID `15241627599`, digest `sha256:715d81cf98d6bb040f75d52ac0486fbd7a5ebceb2683f8fa1f6e88dc6fca9612`; root-tree artifact ID `15241652619`, digest `sha256:1d3622c344b4cfb799583e8723feda8cbc9bdb5d082bb42afbe64cd0301ced5a`; standalone root-tree.tar ID `15241732201`, digest `sha256:bde9467831c18f237b4b39a098c650a1087e7ae0e0145123747cf64a68502036`. RAM package `SHA256SUMS` 28/28 matched. Scope is the 58-Mach-O launchd diagnostic closure; `springboard_included=false`, `touch_runtime_validated=false`, `runtime_qualified=false`.
- New pinned System-volume source artifact from the same package run: `y35a-ios12-system-root-46091804871`, ID `15241677649`, digest `sha256:c74e86b815e3a44b618235cad7e856b882d4ccaae2fe37e77b3bae0de67bf66d`, size 2,826,122,053 bytes. Actions verified IPSW OS component hash/size, `12.4.1/16G102`, j96ap/iPad5,1, GPT/APFS relation and critical `launchd`/`dyld`/`SpringBoard` hashes. This is an unqualified j96ap System-volume source, not a complete installation or a Y35A bootable package. Paired writable Data volume is absent.
- Package validation `46091733461` and general validation `46091733421` on `8c0631a7611117e4ec35a5a845eec34991584fdf` passed 83 tests including full-System source bindings. The failure on parent commit `7ab26c4` was one negative test's expected error-text mismatch and is superseded.

## Open gates and next actions

- Stock PD1502A QCDT/boot bytes and provenance are still unavailable in readable repository/CI artifacts. Historical boot record says 67,108,864 bytes and SHA `92611f876a022fb5af1138f0591f5dafe2b359a226b2f0b28d292211f2fec012`; the file itself is absent. Do not scan `/Volumes/Mobile`; request that exact image or a directly extracted QCDT with source/hash/board tuple provenance.
- Complete System source lacks paired writable Data/APFS volume and `/private/var` mount contract. Root selector/fallback, physical TF binding, TF/APFS production package and probes are unverified. Do not describe the System artifact as bootable or the SpringBoard binary presence as runtime proof.
- Next: add a separate hash-bound CI Data-volume image/source artifact and system+data relation contract; then continue stock-QCDT intake and linked root-selection/fallback gates. No device execution until the complete run-plan and G0 gates explicitly pass.

## Recovery state

- Only RAM-only/published artifact CI work has occurred; no device actions or persistent writes this turn.
- Full partition backup and EDL/firehose recovery remain unverified; persistent boot/GPT writes stay prohibited.
- `/Volumes/Portable` is temporary artifact staging only.
