## 2026-11-26 R205b paired MVE adjudication

R205b preclear and baseline completed with fresh zero target windows and `PSTCOPY0 count=12`. Candidate boot was accepted, then fastboot returned `e00002ed / Write to device failed`; the device did not return to verified fastboot within the 600-second run window. No candidate or final raw exists. This does not adjudicate `ARG1RD00` execution or a kernel fault. Adjudication: `/Volumes/Mobile/unixnu-research/reboot-checkpoints/R205b-pe-bootargs-first-read-paired-run-20261126-01/R205b-adjudication.md`. Keep `device_run_allowed=false`; next is offline comparison with R204b package/shim and failure timing.


## 工作区路径切换（2026-11-26）
当前唯一活动工作根：`/Volumes/Mobile/unixnu-research/UniXNU-y35a`。
当前账本：`/Volumes/Mobile/unixnu-research/UniXNU-y35a/docs/coordination/claude-codex-sync/LOG.md`。
当前参考根：`/Volumes/Mobile/unixnu-research/UniXNU-y35a/upstream-refresh/2026-11-11/sources/`。
当前设备锁：`/Volumes/Mobile/unixnu-research/UniXNU-y35a/.device.lock`。
当前备份根：`/Volumes/Mobile/unixnu-research/device-backups/efff9d92-20261119/`。
Xcode 目标：由 GitHub Actions runner 用于 UniXNU 构建；`/Volumes/Mobile` 保存源码缓存、CI 输入快照、CI 下载产物、备份和 raw，`/Volumes/Portable` 仅作临时 staging。本机任何磁盘不运行 UniXNU 编译或链接。
历史条目中的旧路径保持原样，作为当时证据位置，不代表当前活动路径。

## 2026-11-26 R208 CI-only and temporary staging handoff

R208 validation `45855811648` (`host-validation`) and Docs `45855811845` (`build`) passed on commit `ba4854d4cb076388f61cb2bcdbdf13efb8404dc5`. NativeSdcard, IOStorageFamily archive, root-selection and documentation gates are green. Kernel link, package/probe, TF GPT/APFS image, root mount, eMMC fallback and device evidence remain pending.

No UniXNU build, link or large-build process was found locally. `/Volumes/Mobile` returned `Input/output error` during a shallow read; no further scan or write was attempted. `/Volumes/Portable` is temporary staging only and is not a local build root. `device_run_allowed=false`; persistent writes remain none.
Staging is `/Volumes/Portable/UniXNU-staging-20261127-0042`, exported from private-mirror commit `68b2cf91038fedb1ccacdc5950223ef618d8215e`; manifest SHA-256 `a4d970a878c88c8e21dbfeeca086f78d2f8fad0b09180584048b4430ee0d8538`; 1424/1424 files verified.

## 2026-11-26 R208 native-input closure and package producer handoff

Main is at `fc6a4727e74e9913d4336deb78bce3557c91c56f`. Validation `45879899093` and Docs `45879899053` passed on main ancestor `0e0a1356ab09ab6dee8fec6f4a9459ad82467d8c`. Native run `45879966044` failed before kernel build during Darwin 18 firehose input preparation; no kernel artifact exists. `fc6a472` push-triggered native workflow `45880957209` was skipped and is not a build result. The native workflow now defines the future `unixnu-kernel-${run_id}` producer contract, but it has not yet emitted an artifact. Package/probe/TF/root/fallback/device gates remain pending.

State documents were superseded by main commit `53966d60ea558dae8a12c795736e8418bcc8cca9`: validation `45882596692` and Docs `45882596678` passed, and native plan-only run `45882865622` passed with `execute=false`. No kernel artifact exists yet; package stage must land before the one execute=true native build.

## 2026-11-26 R208 remote validation after staging sync

Private mirror commit `9a98ce2480220da4e663688dd730beb62b004bb7` is on remote main. UniXNU validation run `45862410871` (`host-validation`) and Docs run `45862410942` (`build`) both completed successfully. This verifies the documented offline gates and staging policy only; kernel link, package/probe, TF image, root mount, eMMC fallback and device evidence remain pending.
## 2026-11-25 R204b boundary

R204b used maximum memory (`0x5fe00000`) and added PEBARGRT after `args = PE_boot_args()`. Fresh final contains PEBARGRT but not ARMDFPAR or ARMDFRET. The measured boundary is after PE_boot_args returns and before the first command-line dereference / parser return. Preclear and baseline carrier windows were zero, final was fresh and nonzero, and the device returned to verified unlocked fastboot without persistent writes.

R204b raw SHA: preclear `e83d9152c8e204cfe86d35b0f7bae45ccdaf6bfd268c1305b60daa4fcd07d501`; baseline `714c473398183ed137673bf7977da33984b533ac9c615b0c945584cce69b7176`; candidate `3d8849185e30a5f98cfcf15575700a1e8b9029d1b53d5626054135a61e954bb8`; final `4b392fc2e19367b51781373de48c7de3b9e112fabf765509c56c9a9a6d019041`. Do not repeat R204b. Keep device_run_allowed=false.

## 2026-11-25 R203 boundary

R203 added ARMDFPAR immediately after the cpus_defeatures parse call. Fresh final contains ARMDFPRE but not ARMDFPAR or ARMDFRET, so the boundary is after ARMDFPRE and before ARMDFPAR, inside PE_parse_boot_argn or before its return. Preclear and baseline carrier windows were zero, final was fresh and nonzero, and the device returned to verified unlocked fastboot without persistent writes.

R203 raw SHA: preclear `542b00cafe53fec38cc2ce8db1e98d83f7e2e7be4595e9150abc2cfd2e2a0076`; baseline `19046b28809d50527e9f6b4f9865b102b8730ad5b19dc717ab41214a76121f24`; candidate `e1c60154fc70671f7f7b8d9be83afd1aed329988e82dab7a67d7246644371a7e`; final `3e8651a42be3de173d73db63be077fd3d6cd9736aef179b8a33d14605a21885f`. Do not repeat R203. Keep device_run_allowed=false; next is the offline PEBARGRT split.

## 2026-11-25 R202 boundary

R202 added ARMDFPRE before the cpus_defeatures parse call and retained ARMDFRET after the block. Fresh final contains ARMDFPRE but not ARMDFRET, so the boundary is after ARMDFPRE and before ARMDFRET, inside the parse call or before its return. Preclear and baseline carrier windows were zero, final was fresh and nonzero, and the device returned to verified unlocked fastboot without persistent writes.

R202 raw SHA: preclear `0a78d0917b08f8ce76cc28b943c54ec65ddfc1ae97cffd16fb9eefd9d0a22401`; baseline `49301ea87628c80598d889cc6b8b8757a9c1c04f2184bb0032f9139af4b23a47`; candidate `7eb0161b79cbc26416cf00221061304d082b999bd48306078851d6ddec70081e`; final `a1bf2b47dc99e8f71743840a9d63c55c3362c6e3444b54546fd0478c9ebd93af`. Do not repeat R202. Keep device_run_allowed=false; next is the offline ARMDFPAR split.

## 2026-11-25 R201 boundary

R201 inserted and linked `ARMDFRET` after cpus_defeatures handling and before `ARMPAGE0`. Fresh final retained ARMPGSZ0, ARMRADR0, ARMPGBEG and ARMRDENT, but ARMDFRET was absent. The valid boundary is after ARMPGSZ0 and before ARMDFRET. Preclear and baseline carrier windows were zero, final was fresh and nonzero, and the device returned to verified unlocked fastboot without persistent writes.

R201 raw SHA: preclear `4f4da838e2ae06131356530306a8d56b294adc4f45b62069c9bb343a840e3520`; baseline `8da8f79d99c463b89f7afe4fa4d2d527c7cbbd2569bc77b9718a68d473a561cb`; candidate `2d54b5dc7638e7865fa2f0604f03989099b212d49c429e25149b170cc29c4374`; final `893932a5f95cdf217854e08e594ae056027d87af7b29c0a98bf0bbe3355f02cd`. Do not repeat R201. Keep device_run_allowed=false; next is an offline split around the cpus_defeatures parse/return.

## 2026-11-25 R200 boundary

R200 direct `PE_boot_args` path completed a fresh paired RAM-only run and advanced the boundary. Final contains `ARMPGSZ0`, `ARMRADR0`, `ARMPGBEG`, and `ARMRDENT`; `ARMPAGE0` is absent. The strongest boundary is after `ARMPGSZ0` and before `ARMPAGE0`. Preclear and baseline carrier windows were zero, final was fresh and nonzero, and the device returned to verified unlocked fastboot without persistent writes.

R200 raw SHA: preclear `b03ee53dac55243a4790bed023d0006ca6f5bf125782e06b9a28f2b8b59cd106`; baseline `5e8c895ff3fdf44f2937c5ec4303e688264ed302e92d1ba91cf15a3ddd03150e`; candidate `3815f629106adf3224479b76127d9637f007602f6a4e6b1bf4e240fde6a7d704`; final `0b7639493c4d7b3d51c79e476b6cb50be6c37224b9883f99bebbd2cf8542826c`. Do not repeat R200. Keep device_run_allowed=false; next is the offline ARMPAGE0 bracket.

## 2026-11-25 R197 boundary

R197 advances the valid boundary to after ARMRDENT and before ARMRADR0, inside or immediately after the radar parse call. No R198 input exists yet; keep device_run_allowed=false.

## 2026-11-25 R196 boundary

R196 advances the boundary to after ARMPGBEG and before ARMRADR0. No R197 input exists yet; keep device_run_allowed=false.

## 2026-11-25 R195 boundary

R195 advances no further: final retains PECFGRET but not ARMRADR0. Boundary remains after PECFGRET and before ARMRADR0. No R196 input yet.

## 2026-11-25 R192 boundary

R192 advances the valid boundary to after PECFGRET and before ARMBTSTR. No R193 input exists yet; keep device_run_allowed=false.

## 2026-11-25 R191 boundary

R191 valid carrier evidence advances the boundary to after PEFCGOK0 and before ARMBTSTR. No R192 input exists; keep device_run_allowed=false.

## 2026-11-25 R191 queue

R191 host/probe gates passed; next is one exact-hash RAM-only run to distinguish ARMBTSTR from ARMARGOK. No device run yet.

## 2026-11-25 R190 marker correction

R190 valid carrier evidence advanced the boundary to after actual PEFCGOK0 and before ARMARGOK. The source label PECFGOK0 is a naming mismatch; do not interpret it as missing. No R191 input exists yet.

## 2026-11-25 R189 corrected carrier boundary

R189 corrected the package/probe carrier mapping and validly advanced the boundary to after POSTPE00 and before ARMARGOK. R188's wrong-address negative result is superseded. No R190 input exists yet; keep device_run_allowed=false.

## 2026-11-25 R188 host gate

R188 linked gate confirms ARMARGOK after PAN setup and ARMVMPRE before arm_vm_init. Build passed; probe generation remains. No device run.

## 2026-11-25 R187 result, R188 next

R187 advanced the runtime boundary to after POSTPE00 and before ARMVMPRE, with fresh carrier evidence and safe fastboot return. R188 adds ARMARGOK immediately after PAN setup to split the remaining arm_init interval. No R188 build or device run yet. Keep device_run_allowed=false.

## 2026-11-25 R187 package/probe ready

R187 package and matched regular/clear probes are bound to the new kernel, with POSTPE00 immediately after PEINITRT and ARMVMPRE before arm_vm_init. No device run has occurred. Keep device_run_allowed=false until capture/transport gates and the exact-hash run plan are complete.

## 2026-11-25 R187 host gate

R187 adds POSTPE00 immediately after PEINITRT and keeps ARMVMPRE before arm_vm_init. Host build and linked order gate passed; no probe or device run yet. Keep device_run_allowed=false. Next queue item is regular/clear probe generation with one carrier record and exact kernel binding.

## 2026-11-25 R186 arm_vm bracket boundary

R186 final fresh carrier retained the earlier PE bypass continuation but did not contain ARMVMPRE or ARMVMRET. The run completed RAM-only and returned to verified unlocked fastboot without persistent writes. The measured boundary is after PEINITRT and before the new ARMVMPRE marker; arm_vm_init is not adjudicated. The legacy phase verifier remains incompatible with this minimal-boundary manifest because it requires historical R68E7 records.

Keep device_run_allowed=false and do not repeat R186. Next queue item is an offline bracket immediately after PEINITRT and before ARMVMPRE. AMFI, launchd, SpringBoard, storage, touch, and driver state remain unverified.

## 2026-11-25 R185b PE_init_platform bypass boundary

R185b final fresh raw 872277d70cb8542d2dbee6770b498488a7ae5d8df0b2f7e72567440d46fa0630 contains ARMINITE, PEINITEN, and PEINITRT, plus the carried A53 HID bypass and post-HID continuation markers. The R185b HACK keeps the PE_init_platform call statically visible but uses volatile y35a_skip_peinit = TRUE to bypass it. Therefore PEINITRT proves only that the bypass continuation executed; it does not prove a real PE_init_platform return. ARMVMINI is absent. AMFI, launchd, SpringBoard, storage, touch, and driver state remain unverified.

Keep device_run_allowed=false. Do not repeat R185b. The next queue item is an offline PEINITRT-to-ARMVMINI marker bracket with strict source/binary ownership, eight-byte codeword validation, and matched probe geometry. Adjudication JSON SHA-256 2eedf56b1bf66e2904fb4b17bdf77bb6480c9fd164cae053aa680d9d1b2098fb; Markdown SHA-256 10e92827a0f7ec142554e7be30c032d7658c4538973d24d99ee46f7a9ec3ebe0.


## 2026-11-25 R184 PE_init_platform boundary

R184 is the latest corrected-address paired RAM-only run. Kernel `fc4852ea60dcc6da43c38b5c09d218c3f4c889d2cff503523facda6969c1920d`, boot `878b13863abbe443c958ab799bb118b1a17b152c33149b1825c5899c2b7364c7`, final `4b5c15987e5584bfa80ceab3b4c0831dcbe72c9ad0ad8ba093a22aa48e780772`. The A53 HACK reached ARMINITE and PEINITEN; PEINITRT is absent. Device returned to fastboot without persistent writes. Keep device_run_allowed=false; next queue item is a PE_init_platform return witness.


## 2026-11-25 R181 arm64 cpu_data_init boundary

The linked arm64 cpu_data_init entry is proven by CPUENTR0; return is not.


## 2026-11-25 R179 cpu_data_init boundary

R179 is the latest paired RAM-only measurement. Kernel `7bdebd4c8389c353259d1a9ceb79af4f7fb17dc1cb8684f86479dc01f0e7c4d6`, final raw `e233afaddac31cb970b62e81a49a947c916dc4a12305b276b3daa4c5864c1778`. A53 bypass and arm_init continuation executed; CPUDPRE0 executed, but CPUENTR0 did not. The boundary is before or at cpu_data_init entry/prologue. Device returned to fastboot without persistent writes. Keep device_run_allowed=false.


## 2026-11-25 R177 ARMRET correction

R177 slot12 `ARMRET00` proves the assembly transfer reached the point immediately before returning into `arm_init`. The absent `ARMINIT0` marker leaves first C instruction unproven.


## 2026-11-25 R177 post-HID continuation boundary

R177 is the latest current-generation paired RAM-only measurement. Kernel `21b6f9b54476bca79884a853b0855f58f90b64a5fe9c2ee7757f508da8345f5d`, candidate `25d17fdd3075ffec67d67d7a113e8ca11a9f5ab959e08dee7ba4598dfa6f439a`, and raw final `2cafa203158d9d0f5771e4c08c73ce0b143979a2ef9ddb22c8b0d7edae1182be` are bound. A53 bypass and POSTHID continuation executed; ARMINIT0 did not. The device returned to verified fastboot without persistent writes. Keep device_run_allowed=false and do not repeat R177.


## 2026-11-25 R174 HID4 read boundary

R174 is the latest current-generation paired RAM-only measurement. Kernel `87286c16d10072f38d4b40f66430ee2cd945126a92dd9fa2274f4a6a358b0304`, candidate `f64fdfa5de51bbd127d596e9f99036175cc30be37ef5edbd882b9b986b223d48` and gate `3dcd3ebe5cd871671cfa9fc5824648322477a0c2dfa25bd7a9fdbe548390c3f9` are hash-bound. Final raw `309e793cbf71993c66d8e375f86f7542c06d2856825b10be92b77afd64b7145e` carries `HIDPRE00` and actual eight-byte `HID4PCOR`, but no HID4 read, write, or later marker. The device returned to verified fastboot with no persistent writes. Keep `device_run_allowed=false`; no claim of trap or register semantics is allowed.


## 2026-11-25 R174 HID4 micro bracket host-ready

R174 is a host-only candidate with kernel `87286c16d10072f38d4b40f66430ee2cd945126a92dd9fa2274f4a6a358b0304`, package `f64fdfa5de51bbd127d596e9f99036175cc30be37ef5edbd882b9b986b223d48`, matched probes, gate `3dcd3ebe5cd871671cfa9fc5824648322477a0c2dfa25bd7a9fdbe548390c3f9` and plan `ea1369f908640dc542f67061305298c29b3452ac39015a85fda7d1b53792a4f9`. It adds micro witnesses after ARM64_IS_PCORE and after the HID4 read; no device run has occurred. R173b remains the latest runtime boundary before HID4RET0.


## 2026-11-25 R173b per-access HID boundary

R173b is the latest accepted current-generation paired RAM-only measurement. Kernel `09ae5b1baa149e5a57fb222749dfe3a2b4d9c1d4ef4c058eb1143df24db9557f`, candidate `c73450f1177b32a75a4c0f6b31acdef3d27cafc32c507a78331755016a6bf0a5`, regular probe `4364a9442c657f841735dd3bcd6f785c557f4275c78a8bbed10bc933a4bd50e4`, clear probe `92c26afb3ea5ed9c66bea183e4b539372c7241cf14170fccfc8139a314daa642` and gate `9a44adf2a849d460404bbdef09713a061b03fb50bec0654cb21f4b2849f56bee` are hash-bound. Final raw `ab64f6f4d0a59fc498b1f4f149d1e990123576484c4f2eaa2124a3d4a8e6ec44` has fresh `HIDPRE00` and no HID4RET0 or later per-access markers; all preclear/baseline target windows are zero. This places the stop before completion of HID4's private-register bracket. No specific trap, undefined behavior or later HID access is proven. Device returned to verified fastboot with no persistent writes. Keep `device_run_allowed=false`; do not repeat these inputs.


## 2026-11-25 R172 HID bracket boundary

R172-02 is the latest accepted current-generation paired RAM-only measurement. Kernel `22c2fa08c911afc9f5ed57c6f272f1a19b0b4b75bac5b6a5f2465c1d173db6f8`, candidate image `0a73156cd977d0120ada8a2a379ab745f1455b3775967a3350604f8447c76a03`, regular probe `ba8f83f317a1a5da854f4d7b01536bbc5d6b72f3a03f0b03159b2447b7163cd1`, clear probe `11f20c868639d193dbe32f715a71dcbfc59f1cc6fcd4889ebe67f5cd29c1bac5`, and offline gate `f67d1cbfb5163b9bcecc00483ad8421302ea1f14e67a4108db8e702d3bbbc676` are hash-bound. Final raw `84f47b8df83d769147e66cc1e2fc64bc71242bbc1b9f4d024fa84d892fe35ef0` differs from baseline and carries `HIDPRE00` at `0xa0baca30/16`; `HIDPOST0` at `0xa0baca80/16` is zero. Preclear and baseline HID/external windows are zero. The strongest boundary is after entering the six Apple private system-register bracket and before its post marker; no per-register or trap conclusion is available. Device returned to verified fastboot with no persistent writes. Keep `device_run_allowed=false`; do not repeat these inputs.

# UniXNU Y35A Long-Run State

Last updated: 2026-11-22

This file is the durable operating handoff for Claude Desktop, Codex, and currently authorized `ccs-terra` sidecars. Read it after `CURRENT.md` and before starting a new investigation. Append evidence to `LOG.md`; update this file only when the active queue, ownership, or safety boundary changes.

## Objective

Boot the actual iOS 12.4.1 system on the vivo Y35A / PD1502A (MSM8916, serial `efff9d92`), reaching the system startup path and visible display. A logo by itself is not completion. Keep each boundary tied to a real linked image, matching package and probe hashes, named raw-record mappings, and a paired baseline/final capture. After userspace is running, continue the remaining platform-driver work in dependency order.

## 2026-11-21 R159 graft candidate measurement

The corrected-link R159 graft package was sent with `fastboot boot` on `efff9d92` in a paired RAM-only sequence. Candidate kernel SHA-256 is `b37cee63a1a8987ecc4c2b562cf1c896270bd2d14f0980d57cd8cad3b6c2e833`, boot SHA-256 is `5cc8490dbacb91cf5ef2a63723631dee5e4fce1f78141dfaec7b9dc442f86834`, and matching minimal-boundary probe SHA-256 is `75ab0c895aa6dfee1dcb041d857f257b6d2b0d22224062b30ec7d5e79cb49577`. The entry linker was checked to place `__text` at `0x80080000`.

The run directory is `/Volumes/SleepyExternalData/r159-graft-run-20261121-v6/`; baseline and candidate raw both hash `28274ea00489e5eb5936ef61b73fd8a7c157e84a8bb897a539d784da4b2d67b6`, and final raw hashes `484b800ba6891be7ff4b421b6dee5c232dfd708017d24f7ac6d92657813f29f2`. All fastboot operations returned zero and no persistent writes occurred. The identical baseline/candidate raw means the transport did not supply a distinct candidate-generation witness; it does not qualify the graft or prove AMFI registration.

A separate marker-only shim run captured `R159GFT0` at raw offset `0x10080`, raw SHA-256 `415b028a46d5a0620d5834c01aba16eae817df23ecd05fe8f4013fd44ff3bd3b`, but its baseline/final transport was unavailable and it is not a paired runtime boundary. The marker is consistent with shim execution but is not independently bound to that candidate boot; a fresh XNU-owned marker remains required before claiming that the grafted kernel reached XNU after the shim branch.

The clean-report paired run `/Users/lingion_k/r159-clean-report-run-20261121-v2/` gives a stronger current boundary. Boot SHA-256 is `d02b05cd00a2184a1faefeca8308249f931c6a0a0be80069be09945d0b3fa11`, probe SHA-256 is `75ab0c895aa6dfee1dcb041d857f257b6d2b0d22224062b30ec7d5e79cb49577`, baseline raw is `5b4cb2360d96dee370bf88d355881b3fff0a2ffd72fd1d5ec07b7ca1b84afd76`, candidate raw is `308064904b65bef69f5200107a5af0cfad2eccba2d6ea0522067a15cbcfb6729`, and final raw is `ed4ea8bd955f7bbaa77da8c91f59f6e768e3ec6721ddaa8af2f8002a3a8e270b`. Candidate raw has fresh `R159GFT0` at `0x10080` and entry pointer `0xa0283098` at `0x10088`; the cleared early-fault/XNU-entry region, including raw `0x10120` where the current `_start_first_cpu` contract writes `R84ENT00`, remains zero. The current candidate therefore proves the clean shim marker store but does not prove first XNU instruction execution; the next work is branch/entry transfer diagnosis before AMFI.

## Current measured state as of 2026-11-20: R154 replay and R158 host-only

The latest accepted paired device result is the fresh R154 replay on serial `efff9d92`; it returned to fastboot with `persistent_writes=false`. Kernel SHA-256 is `4e7903810d5f70d6ab2907754a9619650113fc803c777c0a37a2bd4ff70fea2f`, boot SHA `d9d4c4f43986717e80332056da82086f5dede9c36f83b6314a0780a67be41891`, matching probe SHA `ea257e369e3cd682d41557905d41d6bacd48cfdfce911f899881f2a76b37f63f`, baseline raw `fdad9101e1305dab95d9ed31af3c76dfdb95aabf7f4c6892a13436de4f2d27a6`, and final raw `8bd00adb81f6b2637794b0c31ca33da302d6c759ddab99c40fd79c11cdb9cb40`. The fresh probe records no AMFI policy, no callback, and `ENOPOLICY=103` at pid 1 `launchd`; no launchd main-loop, Apple Logo, SpringBoard, display, touch, storage attach, or complete UI witness exists.

R158 is host-only. Its clean no-minimac kernel SHA-256 is `4c12d04788b1df00ee47e353c588ef5f7d5d08023e8f58c33feab0ce06c4d67b`; the persisted build manifest and source/toolchain snapshots are under `reboot-checkpoints/2026-11-19-mainline/r158-clean-host-20261120-01/`. The linked kernel has no matching boot/probe pair and is not a device candidate. The R158 TrustCache patch covers static/legacy v1 behavior but not the original Image4/security-interface lifecycle or shared reserved-page ownership.

| Daily-driver boundary | Current state | Evidence |
|---|---|---|
| AMFI and pid 1 | Reproduced `ENOPOLICY=103`; launchd exits before its main loop | R154 kernel/boot/probe and final raw hashes above |
| StartIOKit/platform invocation | Not established on an accepted no-stub run | No accepted current-generation witness |
| Apple Logo/display | Not observed | No current visual or framebuffer witness |
| Touch/buttons | Not tested on the current accepted iOS kernel | No current input witness |
| Durable System/Data storage | No current attach or read/write proof | No accepted current-generation storage witness |
| Power/battery, Wi-Fi, cellular, audio | Not established | No current driver witness |

The LK framebuffer geometry is a separate handoff fact; it does not prove that XNU scanned out. Later-numbered historical runs do not replace this boundary when they used the prohibited minimac security policy or lack a trustworthy current-generation witness.

## Historical initial R154 state on 2026-11-15 (superseded by the 2026-11-20 replay)

R154-v3 is the latest paired RAM-only measurement on Y35A serial `efff9d92` / `lk2nd-msm8916`, unlocked=yes. The handset returned to fastboot after the final probe. No persistent partition write occurred. The full phase record is `evidence/y35a-20261102/boot3-20261106/phase-r154-v3-amfi-syscall-errno-20261115/record-r154-v3.md`.

R154 kernel SHA-256 is `4e7903810d5f70d6ab2907754a9619650113fc803c777c0a37a2bd4ff70fea2f`; boot is `d9d4c4f43986717e80332056da82086f5dede9c36f83b6314a0780a67be41891`; readback probe is `ea257e369e3cd682d41557905d41d6bacd48cfdfce911f899881f2a76b37f63f`. Baseline/final raw SHA-256 are `63edf05a4069ebdcabec73e6926b62afa609d7eaf5f081c4e926a6a0d90d6b18` and `3f594eabd8428ab609614eea631fd4462c15142d0bbe035d82a5f81f366d4e23`.

Fresh R154 slot21 and slot22 jointly record the exact `__mac_syscall("AMFI", 90)` boundary: no matching policy name, no callback, return errno 103 (`ENOPOLICY`). The Y35A-only patch preserves the original return value. This is direct device evidence of the current AMFI policy-registration failure. Dyld 650.3.4 uses BSD syscall 381, then exits with `OS_REASON_DYLD` default subcode 9; 9 is not the errno. No launchd main loop, SpringBoard, Apple logo, or visible iOS UI is evidenced.

R152 slot22 `R150MROK` was inherited and not fresh; fresh slot23 `R150RVOK` is written after `VFS_ROOT()` succeeds, and later `R90VMIL0` is reached. This downstream control flow supports an earlier successful `vfs_mountroot()` return, but that result itself was not freshly encoded. R154 supersedes R152's AMFI hypothesis with an errno/dispatch observation.

R152 includes only the 174-entry RestoreTrustCache. It covers `dyld` and `launchd` and 56/58 current mixed-root Mach-Os; `bin/df` and `bin/ps` are present only in the separate 1,737-entry StaticTrustCache. The union covers 58/58. This is a later package-coverage gap, not the measured R154 cause.

R153's native Xcode 14.3.1 T7000/RELEASE host build resolves `_ccaes_cbc_encrypt_mode` from real `bsd/nfs/gss/ccrypto.c`, but its geometry matches 0/15 cache segment records and 0/32 shared section records. Its prelink segments remain empty; it is not boot-ready. R154 build, package, readback transport, static verifier, and 10 focused contracts passed. The paired capture saved both raw files; the first runner stopped only at its inherited R152 freshness assertion, then the corrected offline decoder read the same raws. No second device run was made for the decoder repair.

### Historical prior checkpoint: R100 v8 (superseded by R149)

R100 v8 is recorded in `evidence/y35a-20261102/boot3-20261106/phase-r99-thread-block-return-20261113/record-r100-v8.md`. It measured the scheduler wait-result boundary and preceded the R111–R149 BSD bring-up ladder.

R100 v8 linked kernel SHA-256 is 3b096524f1a821ed2222ea0543d3f01a64416c9773865db9039387c3a69a993f; boot image SHA-256 is c71434d09c402ba86027c122ef440652700f0f3bdaa808784ea3f3f8a13cb5fd; matching readback probe SHA-256 is e242b322757f40f285d3d6483717e439a89282b898155f1e3106da834527fda1. All 16 offline gates passed; summary SHA-256 is 680aa531f07b670a3153ed208a6c3c1d3074c463bd9ef95b711c98296889319e. The supplemental H-series codeword freshness check also passed against the previous final raw.

Baseline/final raw SHA-256 values are 5c886f1f9d170a9e7975927599f0e76ac0a5908b3cef308a68d070cfaa9b02b9 and 9a6f2db498da70145e98baa0f089c60d1b8e9962941ab83f78989e742a54e99b; CNTVCT changed. Fresh slot39/raw 0x10238 is R9HCAL00. Fresh slot40/raw 0x10240 is R9HERTN0 after the slot50 helper call and before the _thread_block_reason RET at 0xfffffff00714c184. New post-return cursors in _thread_block and _lck_mtx_sleep_deadline were not retained. This does not identify a unique fault, timeout, false predicate, non-returning marker helper, persistence loss, or overwrite. No root mount, launchd, Apple logo, or iOS UI has been observed.

## Active queue, reconciled after the R158 host audit on 2026-11-20

1. Preserve the 2026-11-20 R154 replay pair as the latest accepted device evidence; it reproduces AMFI call 90 with no matching policy/callback and errno 103 (`ENOPOLICY`). Do not spend another boot merely to repeat it.
2. Continue the R158 host closure from the persisted source and build manifest. Its v1 static/legacy TrustCache subset compiles into a no-minimac host kernel, but the original 16G102 pointer tables and machine code show shared claim/free/Image4 list ownership and indirect security callbacks. Trace the actual prelinked KEXT call path and close the missing APIs with real behavior before producing a graft candidate. Do not use placeholders, permissive policy behavior, or false PPL state.
   R159's follow-up audit confirms that the newer XNU Image4 implementation depends on `pmap_cs`, AMFI, TrustCache, PPL page reservation, and Image4 types absent from the pinned 4903 source. The dependency-shape report is `docs/coordination/claude-codex-sync/R159-IMAGE4-CLOSURE-AUDIT-20261120.md`; it is a host finding, not a device result.
3. Supply complete TrustCache inputs for the actual mixed root while preserving module semantics. R152's Restore cache is missing `df` and `ps`; the full authentic cache union covers all 58 staged Mach-Os. Do not claim this gap caused the current policy-not-found result.
4. Complete the durable OS/Data route. The verified md0 HFS+ root is a bring-up root only. The APFS OS volume uses 3,933,454,336 bytes, larger than the 3 GiB system partition and 2 GiB RAM. Userdata is about 11.8 GB and has not been backed up. The SDCC driver is read-only, NativeSdcc only accepts read operations, eMMC root authentication is incomplete, and APFS runtime loading requires the matching file system component. Do not treat userdata as free space.
5. Retry only after authentic AMFI policy registration, required API bindings, complete trust inputs, durable root/storage plan, and all offline/package/readback gates pass. Require the fresh R154 errno/dispatch probe, launchd main-loop evidence, intended root, and visible system UI.

The independent QcomSdcc host milestone is recorded in `/private/tmp/r155-qcom-sdcc-object-v10/manifest.json`: NativeSdcc and the pinned IOStorageFamily-191 base compile as arm64 iOS 12.4 objects, and their combined relocatable object has no unresolved names against the R154 kernel symbol inventory. This is not a linked kernel or device result; the next step is a controlled IOStorageFamily KEXT/prelink integration audit.

The relocation-aware graft design and its current no-boot stop are recorded in `docs/coordination/claude-codex-sync/R155-AMFI-GRAFT-DESIGN-20261115.md`; deterministic planner output is `evidence/y35a-20261102/boot3-20261106/phase-r155-amfi-graft-plan-20261115/graft-plan-r155-v6.json` (plan SHA-256 `9fa3851c8524979b16f2a461d16df04f35b073480fcec0a3937de34b29f6875a`, planner SHA-256 `778d99e93c44813a12a23fd12dc59745e1d271400f57964ce140675d12bb758e`). It includes the 791 individual bindings, selected components' `AppleSecurityExtension` and `OSBundleLibraries` metadata, and 10,273 PC-relative encodings internal to the selected KEXT extents; register dataflow remains unqualified.

Do not write persistent partitions or userdata without a concrete reviewed layout and backup path.

### Historical R100 address interpretation

R100 v8 reaches the low-slot marker after the slot50 helper inside _thread_block_reason, before the function RET. The wrapper's target compare and branch are at 0xfffffff00714a940/0xfffffff00714a944; slot48 and slot40 markers are inside the branch. Missing markers cannot distinguish a false predicate, helper non-return, persistence loss, or overwrite. The next experiment brackets the helper with a low cursor immediately after the C return and before slot48, then brackets the slot41 and slot49 calls the same way.

### Historical R100 build environment

R100 v8 was linked natively with Xcode in a fresh source snapshot and separate OBJROOT/SYMROOT/DSTROOT. The link succeeded. The linker warned that supplied libcc_kext.a objects target iOS 17 while the kernel target is iOS 12.4; preserve that as a toolchain/input caveat. Exact command, source manifest, patch, build log, result, package/probe manifests, and all hashes are in the R100 evidence directory.
## Historical operating state through r68d

- The device was last observed in `fastboot` with serial `efff9d92`, product `lk2nd-msm8916`, and `unlocked=yes`, after the r68d RAM-only boot/readback.
- Latest real-device run is r68d. Its exact boot, probe, baseline/final raw hashes and interpretation are in `evidence/y35a-20261102/boot3-20261106/phase-r68d-carrier-20261110/record.md`.
- r68d's final raw has the current XNU/probe generation stamps, fresh CNTVCT, and `PREMMU00`; slots 56/57, MMUON, ARMRET, and C-entry markers are zero. Early-fault flag/state and the global pointer window are also zero. The last observed marker is before the SCTLR write; no exact failing instruction is proven.
- The r68d kernel is `de4bf9407c994bee66cf39b20e503f8cd8f1ae9e86faf553eb16d8c113a70a7c`, boot is `a23f5f263800ccb600c69fd242d50c97c5ab7c8de40d965fab83f3345e37fea5`, probe is `5a1cf9df700726db3498acaf6da5c874693b73ccd1a5b1b4920cdf66d66c2f45`, final raw is `fa52ddf407f3bb64789039f086358bd17e2eace0e531b3598717d7c2a2dce798`.
- r68d's final Mach-O split-boundary verifier, independent minimal-boundary layout/transport gates, and the complete 105-test host suite passed. r68c is superseded because its split stores were not adjacent to MSR/ISB.
- The current shared worktree full offline test suite was rerun as `89/89` at HEAD `a3f0273`; older `92/92` and `86/86` entries are historical counts. Readback and capture-format contracts are committed at `e434dc9` and `7566c88`, while the corrected T0.2 source, independent DWARF parser, phase verifier, and entry-witness contracts remain in the shared worktree.
- The phase-r11 kernel SHA-256 is `619a6ea03be230529d4eeeaac64a3fd9d44cef8e1d302255a6bd5f70dd70381a`.
- The phase-r11 boot image SHA-256 is `a98c0b26340b503d05414c2cf9586e52725ffa0e99cb420a63619931dad47e99`.
- The minimal-boundary readback image SHA-256 is `9466188a5b3f91fedb53525823dea7ced471f5ad1d7e69b1bf4ddbf462d9a405`.
- The current-source minimal-boundary manifest SHA-256 is `39574d2fdab3b336f859fc2d0e814f9ea6779c294244e26bd07d1876eed44371`; historical manifest SHA-256 is `0ae59dac07ed1a7accd8f26a47123633084c6c95c30da3cad9cd64a54d1d4fea`, with identical entry and image bytes.
- The phase-r16 run produced the first positive XNU-owned runtime witness: `ARMENTRY` (`0x5952544e454d5241`) at slot 0, body `0x10100`. This proves `start_first_cpu` executed, but slot 0 overlaps the early-fault flag and is superseded by the r18 full-readback contract.
- Phase-r17 was superseded by the phase-r18 run. The r18 kernel is `1eb5d20ebaa10a06fb1895c2501eb091d158a40372428317335169fa534e228c`, the boot image is `5a71c3f1ae66481343822dd4df8db61c11f81a8b626cbcfe7eccb1593edbf28f`, and the full-readback probe is `f0429b7f4b9853540625a30287032d695119f53191a208ea551fb2c5e711ff60`.
- Phase-r18 final raw `8c97dd66b33a25d42de27692b857c30e06e1c2e22b7ddfafe32cae6e2d8cc33e` has the full-readback carrier at body `0x40`: slot 4 `ARMENTRY`, slots 0 through 3 and 5 through 10 zero. C marker publication remains unproven.

## Historical active queue before R68E6

1. Independently derive the `_native_early_fault_address` ADRP/ADD runtime address and payload with x22/x23; capture the raw destination, payload, and pre/post store states in unused cleared slots 58..63 and read them back as a separate physical window.
2. Strengthen the final Mach-O verifier and tests for the address-conversion instructions and carrier offsets, then apply the exact 22-patch chain in a fresh XNU tree and rerun all host/static/layout/transport gates.
3. Run one serial RAM-only r68e experiment only after those offline gates pass. Require matching boot/probe stamps, a fresh CNTVCT, a new handoff witness, and the complete pointer-publication window. Stop on any gate, identity, raw, or USB failure.
4. Proceed to MMU/C entry only after the marker boundary advances. QUP5 remains gated on C entry; GPU, broad drivers, and userspace remain downstream.

### Earlier direction lock (re-evaluate with R68E6 evidence)

Do not reopen the VA-to-PA translation premise. The independent segment-table decode and the r7 carrier comparison already agree at delta `0x0` for the relevant carriers, including `__BOOTDATA` stacks. Any new translation patch must first provide a counterexample against those exact bytes; a failing test in the current shared worktree is not such a counterexample.

## Ownership

- Codex: maintain the shared ledger, independently validate phase artifacts, construct the R154 diagnostic, and control paired device sequencing.
- Franklin (ccs-terra GPT-6.1 Terra): completed the R153 T7000/RELEASE geometry-only build; the candidate is not cache-compatible and is not boot-ready.
- Feynman (ccs-terra GPT-6.1 Terra): completed binary-level dyld 650.3.4 / AMFI call-path audit; key findings independently checked against local bytes.
- Leibniz (ccs-terra Grok 4.7): completed mixed-root TrustCache/CDHash census; key cache hashes and critical CDHashes independently checked.
- Confucius (ccs-terra Haiku 5.5): returned first read-only eMMC/APFS/Data findings. Final route/stop-conditions section remains pending; no userdata or device writes were performed.
- McClintock and Darwin (ccs-terra GPT-6.1 Terra / Grok 4.7): alternate-prelink and API-availability reports did not reach a final result.

## Device boundary

The user has now authorized arbitrary device recovery and fastboot work for this long-run task. Keep operations bounded by the active experiment record, never run two fastboot operations concurrently, and retain the device serial, image hashes, raw upload hashes, pre/post device state, and stop condition. Flashing or other destructive operations still require a concrete recovery purpose and a recorded rollback path before execution.

## Interpretation rules

- `Y35AXNU2` is a boot-shim handoff stamp. It identifies the packaged kernel generation and does not prove that an XNU function ran.
- A readback is runtime evidence only after stage/pram separation, correct physical translation, exact field width, and image provenance are independently checked.
- A zero marker is a negative observation about that marker path, not proof that the whole kernel did not start.
- In r18, the full-readback carrier fields are fixed as: slot 0 `early-fault recorded flag`; slot 1 `ELR_EL1`; slot 2 `ESR_EL1`; slot 3 `FAR_EL1`; slot 4 `ARMENTRY`; slots 5 through 10 are `ARMINITE`, `PEINITEN`, `PEINITRT`, `ARMVMINI`, `PANICINI`, and `CONSOLE`. The carrier starts at raw body `0x40` for full-readback and at body `0x10100` for minimal-boundary.
- A failed transport gate is a transport result. Do not convert it into a kernel-progress claim.
- When new evidence contradicts an older conclusion, preserve the older record and mark it superseded in `CURRENT.md` and `LOG.md`.

## Required handoff format

Every new entry should state:

- exact date and repository HEAD;
- direct measurements and their source files;
- image, manifest, and raw SHA-256 values;
- the hypothesis tested and the observation that would falsify it;
- the next action, its owner, and its stop condition;
- whether a new device authorization is required.


## 2026-11-10: R21 boundary result

R21 completed on the real device under the standing RAM-only authorization. The exact record is in evidence/y35a-20261102/boot3-20261106/phase-r21-carrier-20261110-014546/record.md.

The final raw SHA-256 is bef018039dcda4ca7cbed697ae3aad93d72c8c0e3becc698e24f56517f09b406. It carries the current r21 kernel prefix, ARMENTRY at carrier slot 4/body 0x60, and zero at MMUON000 slot 11/body 0x98, ARMRET00 slot 12/body 0xa0, C slots 5 through 10, and body 0x3c0.

This narrows the unresolved boundary to the pre-MMU portion of common_start after the _start_first_cpu entry witness and before the post-SCTLR witness. The next owner is Codex. R22 should add physical pre-MMU checkpoints around common_start entry, bootstrap mapping completion, TTBR publication/barriers, and the SCTLR write. Do not change readback transport or VA-to-PA mapping on this evidence.

The device remains in fastboot with serial efff9d92. No persistent write was performed. The next RAM-only experiment is covered by the user's standing authorization; any partition write still needs a separate recovery purpose and rollback path.

## 2026-11-10: R43 partial mapping result

R43's first probe send failed at USB transport after boot3 returned to fastboot. The device re-enumerated and the same probe was resent; the retry raw is preserved under phase-r43-carrier-20261110-130000. The retry confirms the entire pre-mapping chain through PTSHIFT0, but mapping call witness slots were shared with loop-state data in that generation. Do not infer V=P/KVA mapping progress from the retry. The next owner is Codex for a clean independent-slot mapping build.

## 2026-11-10: mapping boundary and USB transport state

The valid runtime ladder now reaches the end of bootstrap table invalidation and first table write. The r43 retry did not provide an independent V=P/KVA mapping result because mapping slots were shared with a loop-state experiment. A later r49 attempt again lost USB during probe transfer after boot3 returned to fastboot. This is an external transport condition, not a kernel result. Keep the goal active; continue with offline independent-slot mapping verification and retry hardware only after the transport state is stable.


## 2026-11-10: phase-r50b boundary and pointer-window follow-up

R50b was rebuilt from a fresh XNU work tree after the first r50 draft was rejected by the final Mach-O gate for incorrectly encoded V=P/KVA return markers. The exact r50b record is `evidence/y35a-20261102/boot3-20261106/phase-r50b-carrier-20261110/record.md`.

R50b kernel SHA-256 is `f3223ebb654f11fbe5e043535c62b3582c2016071bbc913d24af9caf970821d2`; boot3 is `90825cd3f6bfb4a142f80fd731a61869b23bf021825648b28d10067e815a4112`; minimal-boundary probe is `f5bf3429d666d4ba3770acc3c46134fa310ee650cf24f0d198d9b200ebe6add0`; manifest is `c94a0da49260bd8fda7c003f02b28ff09408d0ef96f098c143dcd6575f2e3806`; final raw is `f2b62e61b4a1dc4313803187f72e0d1d87e8c46fddb80655e2f807aaa0c31e17`.

The 98/98 host suite, final Mach-O verifier, minimal layout gate, and minimal transport gate passed. The real-device raw is 69,632 bytes and carries matching r50b boot/probe stamps. It proves ARMENTRY, ARGSLOAD, all six boot-argument witnesses, x22/x23, TPIDRRO, exception-stack, and interrupt-stack witnesses. LINKADDR and mapping slots 50 through 55 are zero.

The pointer-window follow-up read back the 16-byte aligned physical window `0xa06d2100..0xa06d2110`, containing `_native_early_fault_address` at `0xa06d2108`. Probe image SHA-256 is `7e3130b059e97276409bcb64c5e3d8d285e8d26af5488b112e8913410a6a7081`; manifest is `ab66f4042f8947a7d56dbe2df546a080071f4ac34af5cfbf79f521c6a51a291a`; final raw is `34cc523767dd18591673f6fb74cb7b96a6d94116d7222a29ac2d56e60f1df033`. The global value is zero. The preserved PRAM prefix matches the r50b final, while CNTVCT differs, proving a fresh readback execution.

The narrow leading hypothesis is a failure in or before the r50b physical publication of `_native_early_fault_address`, because that publication precedes LINKADDR and the global remains zero. This is not yet a proven faulting instruction. The next experiment must add independent operand, pre-store, and post-store witnesses around that publication, then rebuild from a fresh XNU work tree and repeat one serial RAM-only sequence. Stop on failed static gates, invalid raw, or transport failure. No persistent device write occurred.


## 2026-11-10: phase-r58 low-carrier split boundary

R58 record: evidence/y35a-20261102/boot3-20261106/phase-r58-carrier-20261110/record.md.

R58 kernel SHA-256 is 4105d9d04fc4f76fc067eb8964de4ebdec10875e082e7259ab4a805fd47942cb; boot3 is 3f60dacce5bd753f04c776e195c15a0607a74ac41b0379203954246b11c46e06; minimal probe is a9f64d86aa2f627f6f7022879500a34d3b4b1b6abde05f9316f73e9822d2ccf5; final raw is dcf6f27f44958f4120c6489227fcad83151c66a2b4713145a3062a997e8f9f0d.

The 98/98 suite, final Mach-O verifier, minimal layout gate, and minimal transport gate passed. The device returned valid 69,632-byte baseline and final captures. The final carrier contains LRPRE000 at slot 38, LRPAGE00 at slot 39, and LROFF000 at slot 40. The high fault-publication window is all zero.

This proves the run passed INTSP000 and both arm_init link adrp/pageoff instructions. It stops before or at the first high-offset carrier marker store in the fault-publication block. The next owner is Codex for root-cause repair of that high-offset physical carrier store or its addressability contract. Keep QUP5, MMU mapping, drivers, and userspace out until this boundary is repaired and rerun.



## Current checkpoint, 2026-11-11: R68E7 v5

Current branch `fix/readback-panic-globals`, HEAD `91299b4715923826a978994075a4b420c07e3bda`. The v5 real-device run is preserved under `evidence/y35a-20261102/boot3-20261106/phase-r68e7-store-boundary-v5-20261111/`. Device `efff9d92` is rechecked in `lk2nd-msm8916` fastboot, unlocked. No persistent partition or userdata writes occurred.

The immediate same-boot direct store/load-back is proven by fresh slots5-11; the later probe reads the global pointer as zero and is a separate time point. Fresh table/build markers reach `TTBRDONE` and `PREMMU00`. SCTLR post-ISB data and marker are zero, so the raw does not prove MMU enable, C entry, or userspace. The XNU T7001 configuration compiles out the cold-start `TLBI VMALLE1`/`IC IALLU` block through `__ARM_IC_NOALIAS_ICACHE__`; table-zero marker `INVALID0` is not a hardware invalidation witness. Whether lk2nd guarantees a reset state that makes explicit invalidation unnecessary remains under read-only audit.

The verifier validates each surviving low-carrier slot when later C markers overwrite only some fields. The historical 144-test run had 6 failures and 4 errors; after correcting stale marker/API assertions and hardening readback manifest, transport, kernel-tag, and probe-image checks, the current full host suite passes 153/153. The real minimal-boundary transport gate is green; the real v5 phase verifier remains negative only for the expected absent SCTLRRD0 and unproven SCTLR.M.

The packed v5 shim itself executes IC IALLU and completion barriers before jumping to XNU; therefore “the whole handoff has no I-cache invalidate” is false. The XNU cold-start path still contains no TLBI VMALLE1 or IC IALLU before SCTLR, and neither that absence nor the shim invalidate proves incoming TLB/D-cache/reset state. The v5 final raw's MIDR sample is Cortex-A53 r0p0, contradicting the old r0p3 label; per-core identity and MMFR0 remain unmeasured. The linked T7001/APPLETYPHOON path contains Apple HID accesses after the SCTLR witness region, a compatibility risk that cannot explain the earlier missing witness.

The saved v5 transcript identity audit is complete: it binds three RAM boots to the probe, v5 boot3 image, and probe on serial `efff9d92`, reporting product `lk2nd-msm8916`; it contains no resident loader version/build-id/hash or boot1 image replacement event. The two legacy candidate images cannot be bound to the resident loader, and the transcript cannot distinguish them from another external resident build. The current run record is therefore insufficient to identify resident lk2nd.

Next: finish the A53 architectural access audit and the low-vector exception-entry review. Then prepare a minimal, statically gated RAM-only candidate with a low, no-stack, no-TPIDR early-fault vector path that distinguishes exception syndrome around the SCTLR boundary. Preserve the original four-instruction SCTLR/ISB/MRS/first-store sequence for the first diagnostic candidate. Require matching kernel/boot/probe hashes and fresh baseline/final comparison before interpreting any new run.

Low-vector feasibility check from the v5 Mach-O: `_LowExceptionVectorBase` is linked at `0xfffffff00726f000`, which maps to physical/low alias `0xa026f000` under the v5 kernel bases. The actual linked vector page has 16 branch entries at offsets `0x000` through `0x780`, each 128 bytes apart; after the final 4-byte branch, `.align 12,0` leaves a page tail `0x784..0xfff` (0x87c bytes) available for bounded stubs. This is a static space observation only; no vector behavior, page-table walk, or exception capture has been tested on hardware. The early vector contract must cover both EL1t synchronous at `+0x000` and EL1h/SP1 synchronous at `+0x200`, avoid stack/TPIDR/global-pointer loads before preserving ELR/ESR/FAR/SPSR, and must not reuse slots 58-62 without first transferring ownership from the earlier publication witness.


## R107 skip-wait bring-up, November 14, 2026

R107 linked kernel SHA-256 is 56d2511b0dad4094c10bdd3b9e43a3e44674d4d540dc7b805865b5dc550340b5; boot is 0e7e1e660b5bad7ff8afe0e13f1bba53e08e931ad6870bf14ae2fe5bfdd28b48; readback probe is 250cd1948570a380390cbeb924926aab3b061d208b3eadeb9fb0ea9ab06bdee2. The R105 skip-wait source was relinked into R107. One paired RAM-only sequence ran on efff9d92 / lk2nd-msm8916 / unlocked=yes with no persistent writes. Baseline/final raw SHA-256 values are 0bef1ea68e51afd8dadf64522dff803646a1c48f21f3afc50ae81dc630ca4e45 and 9d7323ebb77def23eae0eb41280df74aea8243a98556aaa884f688cf642fbea5. The XNU image was accepted but returned to fastboot on the first poll. No root mount, launchd, Apple logo, or iOS UI was observed.

The bring-up change conditionally skipped SLEEPNOTIFYTO only when the diagnostic event pointer still equaled &result. The final raw contains no R105 skip marker; therefore this run does not prove that the target wait reached that finite sleep branch. The prior wrapper-entry marker also remained absent, while the caller-side pre-call witness continued to appear. The next diagnostic must cover the indefinite SLEEPNOTIFY branch or instrument the exact wait call selection before claiming the bypass was exercised.


## R108 skip-both-waits bring-up, November 14, 2026

R108 linked kernel SHA-256 is 9af17b0048b11d158a49c12a1b98002c99cc0ae271de4e751ed9410e2f44d1ac; boot is e240f6a1a04174768d935e26b3a75764ec2d543f0ce1dde8d242e5cf4cc4a919; readback probe is 73cc48e8c8d83615c9e689a458ddb82b82855dad302a523951868ab9b7204dad. One paired RAM-only run on efff9d92 accepted the image but returned to fastboot on the first poll. No root mount, launchd, Apple logo, or UI was observed.

R108 conditionally skipped both finite SLEEPNOTIFYTO and indefinite SLEEPNOTIFY for the diagnostic event. Neither R105SKIP0 nor the new P-series markers appeared in final raw. Therefore the instrumented IOService wait branch was not reached or not retained; the wait bypass was not exercised. The mainline boundary remains earlier than this wait site, and further wait bypass variants should stop until the caller/entry path is independently proven.


## R109 bypass-target-thread-block, November 14, 2026

R109 kernel SHA-256 is 1676efc296c4f8aec0c02b4539c867973ad6b42008e1c3b0dcdd21cf0d90a423; boot and probe were bound before the run. The target event path set THREAD_TIMED_OUT and skipped thread_block. One paired RAM-only run on efff9d92 accepted the image but returned to fastboot on the first poll. No root mount, launchd, Apple logo, or UI was observed. Baseline/final raw SHA-256 values are recorded in experiment-r109.json.

The bypass did not advance the observable boundary. The caller/global marker stream is not sufficient to prove that this specific thread reached the target wrapper; later slot40 values can come from other threads. Stop adding more global return markers. The next useful change is a thread-local or per-run transport witness tied to the exact caller, or an earlier boot-stage probe before this IOKit wait chain.


## R111 IOKit entry witness, November 14, 2026

R111 linked kernel SHA-256 is 052d94b309040e2b753dc8850650391a4f7a8ac7feb5dcdabe47d27565976f07. The image was paired and RAM-booted on efff9d92 with no persistent writes; it returned to fastboot on the first poll. New unconditional witnesses were placed at waitForMatchingService entry, IORecursiveLockSleepDeadline entry, and its return. None appeared in final raw. Therefore the active path has not been proven to reach this IOKit wait chain; older R95/R100 markers cannot be attributed to this same thread or branch. No root mount, launchd, Apple logo, or iOS UI was observed.

The next diagnostic boundary moves earlier into the XNU/IOLock/IOKit startup ladder, with per-call entry witnesses and a fresh named transport area. Do not continue bypassing SLEEPNOTIFY until the actual caller entry is proven.


## R112 bsd root/init entry witness, November 14, 2026

R112 added unconditional T-series witnesses at the VFS_ROOT callsite and bsdinit_task entry. The paired RAM-only run accepted the image but returned to fastboot on the first poll. Neither root/init witness was fresh. No root mount, launchd, Apple logo, or iOS UI was observed.

The baseline carrier contained stale/garbled retained values in older slots, while the final retained older values were R90PNAM0/R90LOCK0/R90SUBM0/R90FPX00 and T-series slots remained zero. This run is negative evidence only; the transport baseline is contaminated and cannot identify a faulting function. The reliable next boundary remains the earlier bsd_init startup ladder, with a clean versioned carrier or a direct source-linked witness at the last proven fresh stage.


## R113 bsd_init ladder witnesses, November 14, 2026

R113 linked kernel SHA-256 is 6c218e46058099d7c15d5bad426fe04b0c9a25b1ec2a24134f5acde226c058b5. It added fresh T-series witnesses at bsd_init entry, after bsd_bufferinit, around IOKitInitializeTime, and bsdinit_task entry. One paired RAM-only run on efff9d92 returned to fastboot on the first poll; no persistent writes. None of the T-series markers was fresh. The result does not reach root mount or init task and does not validate the downstream IOKit wait path. The next boundary is immediately after the known fresh R90FPX00 point in bsd_init.

## 2026-11-20 current security and toolchain update

The official Xcode 14.3.1 (14E300c) and iPhoneOS 16.4 SDK are restored at `/Volumes/SleepyExternalData/Offloaded/Applications/Xcode.app`; `/Applications/Xcode.app` resolves there. A new formal Xcode rebuild produced kernel `f309866a8a6329bd493568c883495f6cc504e5e4667295a169d4ce55b2f54101`, boot `8ace3aac0d7cc9f295d63c41f5d7a250769538e985239f1386af2579dbcadb27`, matching probe `fba84fac0c10ce0a3eb79f83bf5776b7f92516a9ae441325a1581ca6b57738f0`, and paired final raw `84b2f817297422b61d8eba0d67a0e6a766a6cc863a9cb5436b5cdc3e7752a080`. The final raw contains fresh `Y35AXNU2`/`R84ENT00` and current `launchd`/AMFI failure; no UI or driver attach claim is added.

R159 legacy pmap/TrustCache host closure linked kernel `69fb5f078119213df42649f777ce3ab66686e09a1fb9b2dfc8116b351f3e18d1` and emitted security candidate `b37cee63a1a8987ecc4c2b562cf1c896270bd2d14f0980d57cd8cad3b6c2e833`. The candidate has 799 bindings, zero missing exports/collisions/nulls and 18 prelink entries including AMFI/CoreTrust/corecrypto. It remains `loadable=false`/`runtime_qualified=false`; no device boot is allowed until register/dataflow, loader, Image4/CoreTrust and protected-page behavior are closed.

The candidate disassembly fixes the two XNU entry markers used for this diagnosis: `__start` at `0xfffffff007283098` stores `RTENT0R0` to `boot_args+0xa00` and branches to `_start_first_cpu`; `_start_first_cpu` at `0xfffffff007285058` stores `R84ENT00` to `boot_args+0x820`. Neither fresh value appears in the clean candidate report. The attempted extra-PA read of `boot_args+0xa00` was transport-failed and is not evidence.

A direct candidate-only clean-report read succeeded with boot SHA-256 `5a1188048bd24da2ea21b29f92d6d8add3e05bd03f0c1b1037f7c629752e25dd` and raw SHA-256 `308064904b65bef69f5200107a5af0cfad2eccba2d6ea0522067a15cbcfb6729`. The report contains `R159GFT0` at `0x10080` and `0xa0283098` at `0x10088`; `RTENT0R0`, `R84ENT00` and early-fault slots are zero. The shim executed its marker path, but the XNU `__start` store was not observed. The active host task is now to verify the flat entry target bytes, branch address, and memory mapping at `0xa0283098` before changing AMFI.

The branch-probe run `/Users/lingion_k/r159-branch-probe-run-20261121/` is the strongest entry evidence. Boot SHA-256 is `d398e950d7f6897e8acdcd536a0d920a32106000bdca20b267bbc569bb30dd6c`; raw SHA-256 is `308064904b65bef69f5200107a5af0cfad2eccba2d6ea0522067a15cbcfb6729`. Before `br x1`, the shim read target `0xa0283098` and retained bytes matching the candidate `__start` first 16 bytes exactly. The shim marker is fresh, while `RTENT0R0` and `R84ENT00` are absent. Payload copy and data access are therefore established; the remaining pre-XNU boundary is instruction fetch/branch execution or exception routing at the target.
## 2026-11-21: R159 formal ELF v3 live run and R326 control

R159 formal ELF v3 was paired and RAM-booted on serial 'efff9d92' / 'lk2nd-msm8916' with no persistent writes. Inputs were entry '68c1b4bbcdcfed9cac04b288a22070fe522a6349b25f475723d081f1204d715e', boot 'e7fbbb384760117c19a0753a226cf72f04ab2c223cc1b1e4b64139e7c8af8d8f', and matching probe '8e4ec35f92fe7e691c8335bb9a0dcbfb03fe951b942447bfb0c6f7de773f9e0d'. Run artifacts are /Users/lingion_k/r159-formal-elf-run-20261121-03/; baseline raw is 'acdaafff96d1e0512d05e22cf4127884492ae3fde5967f5a8ba637196efd2dd8', final raw is '7d425a73e834be082381f1b576c62d0f0262c94691d081ad4ad46f6b978a9849'.

The final R159 report contains the current Y35AXNU2 handoff prefix, fresh Y35ARD02, and R260CPY0 with target 0xa0283098 and the candidate first instructions. The early-fault record, _native_entry_trace, RTENT0R0, R84ENT00, and current panic carriers remain zero. This proves the corrected shim copy/report path and leaves the candidate boundary before a fresh XNU __start witness; it does not prove AMFI, launchd, display, or UI.

A separate R326 formal3 control replay used the matched durable probe 'f217be233ac370ef095b4c7102432fa2b5a63c9ef7911beffeee23e17744f6bf' and boot 'e3ef10009914ffa209b04a5f59f15c03411dca55c74f45a336ac1fcc693497f2'. Artifacts are /Users/lingion_k/unixnu-research/reboot-checkpoints/2026-11-21-r326-live-control/; baseline raw is '8d0bed5ffee2aa3d9890f57622c6bfb447b6ac4b6294c8ed632aebc27824288', final raw is 'd59e9d859683b204edfb8d4ddf188199041aa220760c28be49b40bbfb4ec1a5e'. The raw starts with the matched Y35ARD01 / 9b9c... probe identity; final contains current Y35AXNU2 / 9b9c..., R84ENT00, and initproc exited ... amfi_check_dyld_policy_self() failed. This re-establishes the live launchd/AMFI boundary and confirms the device/transport path is healthy. It does not prove Apple Logo, display, storage attach, SpringBoard, touch, or complete iOS boot.

The next work item is a source-grounded AMFI/CoreTrust registration and policy-path closure audit. Do not replace it with a blanket allow-all policy or claim a security bypass is a daily-driver implementation. Preserve paired baseline/final evidence and exact hashes for any later RAM-only run.
## 2026-11-21: R159 matched probe v4 correction

The first R159 formal ELF v3 paired run used probe image '8e4ec35f92fe7e691c8335bb9a0dcbfb03fe951b942447bfb0c6f7de773f9e0d'. Its diagnostic extra record named 'xnu-start' was at 0xa27e0a00, while the R159 shim's boot-args base is 0xa27e4000. That address mismatch made the original absence of the boot-args entry marker non-decisive.

A new probe was generated from /tmp/r159-candidate-original-20261121.macho with XNU kernel SHA 'b37cee63a1a8987ecc4c2b562cf1c896270bd2d14f0980d57cd8cad3b6c2e833', minimal-boundary transport, and an extra record for RTENT0R0 at 0xa27e4a00. Probe SHA-256 is '97d00c63acebbf31bf86cb3c1ec283871b50d34098437cd14961de5eedb49346'. The paired run is /Users/lingion_k/r159-formal-elf-run-v4-20261121/; baseline raw is '0778452f0ba6bb3553983fa4f86b6a614a2191a2a1c4965dfeae535817dc62aa', final raw is 'adc490f7cedfd906ea364287d3831f4e34629d3d3d71b17963bfda43e26bd6ba'. The candidate boot SHA remains 'e7fbbb384760117c19a0753a226cf72f04ab2c223cc1b1e4b64139e7c8af8d8f'.

In the corrected pair, the RTENT0R0 record at 0xa27e4a00 is zero in both baseline and final, the early-fault record has no fresh R84ENT00 at its expected +0x20 position, and _native_entry_trace is zero. Only the probe freshness/header values differ. This removes the old probe-address ambiguity but still does not identify whether the failure is the branch, instruction fetch, first store, or unobservable exception route. The next experiment must isolate the entry transfer with a fresh current-generation witness before any AMFI change.
## 2026-11-21 correction: R159 entry pointer mapping

A transient static calculation incorrectly concluded that the R159 entry pointer should move from 0xa0283098 to 0xa0287098 because it omitted the actual kernel_data file offset inside the entry image. The embedded R159 Mach-O begins at entry file offset 0x4590, not 0x590. The candidate __start bytes begin at entry file offset 0x283628, so their source offset relative to kernel_data is 0x27f098. The actual segment-table mapping is source 0xfc000 to destination 0xa0100000, yielding destination 0xa0283098. The original pointer is therefore the correct destination.

The pointer-fix paired run /Users/lingion_k/r159-formal-elf-run-v4-pointerfix-20261121/ used boot SHA '9dd497fc8ae0aa4fce405ffcd9d7ddc6f1a8aa7aa6658a181054c875c72f62ce' and the matched probe SHA '97d00c63acebbf31bf86cb3c1ec283871b50d34098437cd14961de5eedb49346'. It returned to fastboot, but the retained R260 copy witness now pointed at 0xa0287098 and its read bytes no longer matched the candidate __start prefix; RTENT0R0 and R84ENT00 remained absent. This negative experiment is rejected as an invalid pointer correction and must not replace the original R159 artifact.

The valid R159 pointer remains 0xa0283098. The entry-transfer failure is still unresolved after the corrected v4 probe; continue with a new one-variable branch/fetch diagnostic.


## 2026-11-21: R326 early entry ladder now reaches BAVIRT00

Fresh paired RAM-only diagnostics on efff9d92 returned to fastboot with persistent_writes=false. Durable assets are in /Users/lingion_k/unixnu-research/reboot-checkpoints/2026-11-21-r326-entry-transfer-diagnostics/ and the detailed report is R326-ENTRY-TRANSFER-20261121.md.

The current-generation entry ladder is now measured through _start_first_cpu markers: R84ENT00, R84FS00, the original cache-clean/readback sequence, PREARGS0, and BAVIRT00. The decisive paired captures use explicit minimal-boundary record mappings and clear probes; stale final values are not accepted as candidate evidence. No AMFI, launchd, display, storage, touch, SpringBoard, or complete iOS UI claim is made.

The formal host-only pmap/arm_vm_init object audit is preserved at /Users/lingion_k/unixnu-research/reboot-checkpoints/2026-11-21-r326-formal-object-audit/. It reports formal 12.4/SDK 16.4 object metadata and CONFIG_PGTRACE, but the objects are not linked, packaged, or device-qualified.


## 2026-11-21: R326 entry ladder reaches BAPHYS00

The current-generation paired RAM-only ladder now reaches the BAPHYS00 store after PREARGS0 and BAVIRT00. The fresh V18 candidate record is PREARGS0; the fresh V19 candidate record is BAVIRT00; the fresh V20 candidate record is BAPHYS00. Each baseline and final probe clears the relevant retained slots before capture, so stale values are not accepted.

The durable evidence root is /Users/lingion_k/unixnu-research/reboot-checkpoints/2026-11-21-r326-entry-transfer-diagnostics/ with asset-index SHA-256 d06bcf3d1cdd7c9920db99263a1ba164ab759f8a0dea710b2c90720862db5d00. The formal host object audit remains under /Users/lingion_k/unixnu-research/reboot-checkpoints/2026-11-21-r326-formal-object-audit/.

The next one-variable entry experiment is the BAMEM000 marker after BAPHYS00. No AMFI, launchd, root mount, Apple Logo, display, SpringBoard, storage, touch, or complete iOS UI claim is made.


## 2026-11-21 continuation: BAPHYS00 measured

V20 paired RAM-only capture on efff9d92 produced a fresh candidate bound record BAPHYS00 at raw 0x106e0. Baseline was zero. This extends the measured _start_first_cpu ladder through PREARGS0, BAVIRT00, and BAPHYS00. The device returned to fastboot and persistent_writes remained false.

V21 is queued as the next BAMEM000 boundary experiment. Durable package and paired evidence remain under the R326 entry-transfer checkpoint. No AMFI, launchd, display, storage, SpringBoard, touch, or complete iOS UI claim is made.


## 2026-11-21: R326 paired BAMEM000 boundary measured

V23c is the first corrected R326 BAMEM boundary run with the required `fastboot oem y35a panic` staging step. The candidate-only raw contains fresh `BAMEM000` at raw `0x106e0`; baseline and final are zero. Candidate kernel SHA is `627b4d14cc8d59e6123b8f1201a0223de7f1e6f668307f205c2fae415e726131`; candidate boot SHA is `3ef9701f34e19c54b5f6c603508279451229af3ea4f2e980dc8b00876b8102a1`; probe SHA is `806b2fd36083c67db5c309af24c41997371d56091a32b73de4bc8507114ae847`. Raw evidence is under `reboot-checkpoints/r326-amfi-start-firstcpu-bamem-bound-run-v23c-20261121-01/decoded-v23c.json`. Next boundary is BATOP000 after `+0x8d0`.


## 2026-11-21 continuation: BATOP000 and BAFLAG00 measured

V24 paired evidence reaches fresh `BATOP000` at raw `0x106e0`; V25 paired evidence reaches fresh `BAFLAG00` at the same transport slot. Each baseline and final is zero, and each run uses full kernel/boot/probe SHA binding plus `fastboot oem y35a panic` staging. Evidence is under `reboot-checkpoints/r326-amfi-start-firstcpu-batop-bound-run-v24-20261121-01/decoded-v24.json` and `reboot-checkpoints/r326-amfi-start-firstcpu-baflag-bound-run-v25-20261121-01/decoded-v25.json`. The next boundary is ARGSLOAD at `+0x8e0`.


## 2026-11-21 continuation: target-address cacheability boundary

V27/V28/V30/V31/V32/V33/V34/V35 isolated the `_native_early_fault_address` path. The candidate-only path stops before return when using the computed physical alias `x9 = 0xa0762488` for the direct store and DCCVAC. Skipping the physical accesses reaches ARGSLOAD; using the known-valid bootargs carrier reaches ARGSLOAD; using the high alias `x16 = fffffff007762488` for both store and DCCVAC also reaches fresh ARGSLOAD. This establishes the current causal boundary as the physical alias access, while preserving the high-VA path as the viable continuation. V35 evidence is under `reboot-checkpoints/r326-amfi-start-firstcpu-target-high-alias-run-v35-20261121-01/decoded-v35.json`. The next experiment is the post-ARGSLOAD TPIDRRO witness using the high alias path.


## 2026-11-21 continuation: R326 boundary ladder through EXCSP1

Fresh paired RAM-only captures now establish the boot_args ladder through `BAPHYS00`, `BAMEM000`, `BATOP000`, `BAFLAG00`, `ARGSLOAD`, `TPIDR000`, and `EXCSPS00`/`EXCSP1`. Baseline and final are zero for each accepted marker. All runs use exact candidate kernel/boot/probe hashes and `fastboot oem y35a panic` staging.

The target publication path is now isolated: physical alias `x9 = 0xa0762488` fails on direct store and DCCVAC, while the high alias `x16 = fffffff007762488` reaches ARGSLOAD. A known-valid bootargs carrier reaches ARGSLOAD as well. This is the current measured address-path blocker; no UI, AMFI, launchd, storage, display, or SpringBoard claim is made.

The latest accepted boundary is EXCSP1 under `reboot-checkpoints/r326-amfi-start-firstcpu-excsp1-bound-run-v38-20261121-01/decoded-v38.json`. Candidate raw SHA is `fa1faa2903466349db858c4285ff114d8dfab6a9193922ee026b6af33500a836`; kernel SHA is `5457fadf01f647d753a20d74f345c38c2f436cd1342f6a3e2118d4d80b291ea4`. Next boundary is the `mov sp,x0` after EXCSP1.


## 2026-11-21 continuation: target alias and early stack ladder

The physical `x9` target path is now separated from the viable high alias. V34 (`dc cvac x20` with safe carrier) reaches ARGSLOAD; V35 (`str/dc cvac x16` high alias) also reaches ARGSLOAD. The computed physical alias `x9=0xa0762488` remains the failing path. V36 reaches `TPIDR000`, V37 reaches `EXCADDR0`, V38 reaches `EXCSPS00`, and V39 reaches `EXCSP000`, each with candidate-only fresh markers and zero baseline/final slots. The latest evidence is `reboot-checkpoints/r326-amfi-start-firstcpu-excsp0-bound-run-v39-20261121-01/decoded-v39.json`; candidate raw SHA is `49dfee2fa0f2d1dae3429bfe77473d745c78c64634f46b4fb1a1ff8f19a26e22`. Next boundary is the stack/object setup after EXCSP0.


## 2026-11-21 continuation: early stack ladder through EXCSTACK2

The paired ladder now reaches `EXCSPS00` (V38), `EXCSP000` (V39), and `INTADDR0`/EXCSTACK2 (V40), with candidate-only fresh markers and zero baseline/final slots. Latest V40 candidate raw SHA is `319db370f3b7cf4a02e9d2a1952c0e8e80716ac53b5a7f0899e83e1cfe597a7c`; kernel SHA is `acfa186b3f0d43e67bf7940028051bdbcadf1abdaea6ab3f160064862c7d7085`. Persistent evidence is under `reboot-checkpoints/r326-amfi-start-firstcpu-excstack2-bound-run-v40-20261121-01/decoded-v40.json`. The next boundary is `SPSel #0` after EXCSTACK2.


## 2026-11-21 continuation: lower-stack transition

The paired ladder now reaches `EXCSP0_LOWER`/`INTSPS00` after `SPSel,#0`; V41 candidate raw is `09e5b565c05826d746bec28299a319a0c1ddf14bce958583a911a49dea870962`, kernel SHA `fc0a540163aeee09cb404068df6286abadf583cb82646ce936336215bee00c27`. Baseline and final remain zero. Evidence: `reboot-checkpoints/r326-amfi-start-firstcpu-excsp0-lower-bound-run-v41-20261121-01/decoded-v41.json`. Next boundary is post-lower-stack marker setup.


## 2026-11-21 continuation: LR return preparation

The R326 ladder now reaches LRPAGE00 at raw `0x106e0`; baseline/final are zero and candidate is fresh. V45 candidate raw SHA is `aecded7d83cefb9a865bbe841798171a5db53dd07b3a2d166fd8266ce60aac56`; kernel SHA is `b938971982c5a76ac1ed6167beb3e16eacce300b89ffe9f03311b45346a33aaa`. Evidence is `reboot-checkpoints/r326-amfi-start-firstcpu-lrpage-bound-run-v45-20261121-01/decoded-v45.json`. Next boundary is LR add and LROFF.


## 2026-11-21 evidence correction and current boundary

The V27–V35 target-path experiments are retained as raw artifacts but are not individually accepted as direct-store causal proofs because some package metadata and branch labels inherited the ARGSLOAD generation while the actual instruction order places the ARGSLOAD store at `L2a11d8` before the target store at `L2a1198`. The raw files remain immutable evidence; ledger conclusions use only correctly bound static control flow plus paired freshness.

The latest correctly bound accepted boundary is V47 `FPGVA00`: candidate raw SHA `6b579ac27242e7f190e4753436d71a5dc4c18249f6f33fffab5340e657239fff`, kernel SHA `e4c26d37af08f1899286ac071e8f23a5f669ed3baf3fe9836e19f7686482d19c`. Baseline and final are zero. The next boundary is the R68E7IN0 operand snapshot after FPGVA.


## 2026-11-21 correction: publication witness binding

V48 reached the R68E7IN0 return branch, but the payload snapshot was zero because the branch intentionally occurred before the later clean/publish sequence. V49 reached a branch after the PUBLIN00 store, but its entry_return read `0xa0c48a70`, which returned the unrelated `ternaliz` payload; V49 is therefore execution evidence only and is not accepted as PUBLIN00 persistence evidence. The next experiment must add an independently mapped readback record for `0xa0c48a70` and a separate publication carrier before claiming PUBLIN00.


## 2026-11-21 authoritative correction: target path status

V47 is the authoritative target-path evidence. Its branch is after the FPGVA store, and its kernel leaves the original `L2a1198 STR [x9]` and `L2a119c DC CVAC, x9` intact. Fresh candidate-only FPGVA therefore proves that the original target store and cache maintenance returned on that path. The earlier V30–V35 packages branched at earlier bootargs/publication points and cannot be used to attribute a target-store fault; their raw artifacts remain preserved but are demoted to non-causal branch-order experiments.

The current boundary is after FPGVA, before the later operand snapshot/publication/direct global-pointer sequence. V48 R68E7IN0 returned only because its branch was after the R68E7IN0 store; its payload persistence was a separate carrier/readback issue. Continue from V47/V48 control flow, not from the demoted target-path variants.


## 2026-11-22: R326 V73-V76 physical-alias boundary

The latest accepted device state is serial `efff9d92`, product `lk2nd-msm8916`, `unlocked=yes`, returned to lk2nd fastboot after every RAM-only run; `persistent_writes=false`. No Apple logo, launchd, SpringBoard, display, storage attach, touch, or complete iOS UI is evidenced by these runs.

V73 paired run: kernel `35d78c583451b5967b0744d7f794aea2a186bb1013128c9f5ed1f3b7655eb96d`, boot `8c5723597b339676534172457f256e54db4b1ed02a0fdd10a29cf17753027af5`, probe `70646e1e3e02e65afa520a38d55040c91e1e1a806b5882647dc4621127818e40`; raws preclear `10b83f0039f80fd4237cbcae6564d9f6783dbf88ff33519faf8cbb525f18787d`, baseline `a07dd1a1db015433922e2f277db5243b82208434e8342306f503383a2edb8f53`, candidate `0121e95531c818ddb80976ce61cf531e65d8c7fc0f6bcbe084eeb2ad5ab3951f`, final `d5d36f063449a8449e9de4e96674058828a5bc5c0fd5ffc2bb9984191c2edfb3`. V73 branches after physical-alias `STR [x9,#0x10]`, `DC CVAC x9`, and `DSB SY`; candidate return marker is absent.

V74 paired run: kernel `f76e2a61e8c628a69d21b19ad28e6d3056139736b199bc0dc3c45a50a154a2a3`, boot `e6fd74d69f6c8fde71650633f8f472c1fe8897a4452f6ff2a323c1fc39e65e0a`, probe `a84c80408bc8a00b14774fae9ccf98a3e2adbfbd2e2eb35715b9f67639304908`; raws preclear `53d8011b6b431995d355dff3bcad0475ed0fcc216484c5b4ffdeb3e414f18db0`, baseline `3e8970d10f643bc0dcee7b0919db7203caabfbd4baf28b3e8371930f0e556165`, candidate `f900d91d7f6ae70fb1569b98cfcfbec24e72f3fbe2cdd06feb3123628b5063ed`, final `4ff9ece7a6f328bc45d04129a5d9a4afddbb8999c6e1952039b8c221e7d6c580`. V74 changes only `L2a14fc` (`DC CVAC x9` to `BR x21`) and still has no candidate return marker.

V75 paired run: kernel `1bc9ee8702c0bef58a303d27e534c070b578bd30f1dd91834b53799547e7e5b5`, boot `d983b425e964fd5fe83559b9a4cea7d4bb4503ad5f2b2f24290b0b779c0a7e14`, probe `5d8021461c2f3babe1a56212684bb1327239dbe5f9969099ba49271c3fea5b7c`; candidate raw `89b68ed8864b8b0577b1f203174d00ee8fa8a0ce97b205f51bb0f95ffd8e3e93`. V75 changes only `L2a14f8` (`STR [x9,#0x10]` to `BR x21`) and candidate fresh `RRET0GR0` appears while baseline target window is zero. This proves the existing continuation branch and return path can execute when the preceding physical-alias store is skipped.

V76 paired run: kernel `021716b73310f8585f88cc4533f83e911618976c4133cd866e700175c8d5f710`, boot `d150f4cd066d5e8ba40354d81db9899e3e13d897d2c8260cff3f21d472fc4204`, probe `9885dbe5200c4d14d05519b9c06c3c4b9ceffeaef0b4b8800515e9e03f7bbfff`; raws preclear `c91468c4ab8ecabfdc23c9cf763cf8c762f0d90bff5b6882e6ebb8b57c411ca4`, baseline `feb9e3be5dadbf9b5859e254fb064eb07b70d8e3d530044e935e5565a5e01c6c`, candidate `66150593125c4829303831fcd2a894cb03b853490174be49838ffb1955788274`, final `62e96819bf48f4525312bee48709f01440d3c263992f76100ff2060f4495be42`. V76 changes only `L2a14f8` (`STR [x9,#0x10]` to `NOP`) while keeping the V74 post-store branch at `L2a14fc`; candidate fresh `RRET0GR0` appears.

The accepted causal classification is therefore: `BR x21`/continuation is viable; V74's missing return marker is consistent with the physical-alias `STR` itself failing or not returning. This does not distinguish a translation fault, permission fault, alignment/cacheability fault, or other hardware/system-control cause. The next experiment must vary only the target address or mapping/access mode around the same store, preserving the paired probe and exact hash discipline.


## 2026-11-22: R326 V77 high-alias control

V77 completed one paired RAM-only sequence on `efff9d92` / `lk2nd-msm8916` / `unlocked=yes`, returned to fastboot, and kept `persistent_writes=false`. Kernel SHA-256 is `33216ee38365bcc31f1858aa57644a0e61c91f642e20773f752e6ba5fe4340c0`; boot SHA-256 is `b62715231ae1039fbe93cf9ef47dd8a1ea9c488b63dc09ead082c3a706caf50e`; matching probe SHA-256 is `03c0fbe57277753576ab2a14d082a2bac8138cb37e434b1009c68c676c90020b`. Raw SHA-256 values are preclear `fd17e040a455dca8fc22b41105c21414e220c604b283fc5643f37e01f1bf83c3`, baseline `2ee2549f23e962785c51f3186131f0a85dfe735bd4c438aaaf1cd6507a0a57d6`, candidate `0752e3e7642bfbdefea11fbd7ff76058987c985a7210c9f0b23e3e3af8988dc1`, and final `938de51e3a480290578cb7ddd99f36a0e4791b2c12b5f8129c0191bde0e2d0bb`.

V77 changes only the instruction at file offset `0x29d4f8` / `L2a14f8`: `NOP` becomes `STR x15,[x16,#0x10]`; the same `BR x21` remains at `L2a14fc`. Candidate raw has fresh `RRET0GR0`, while baseline target-return window is zero. The high-alias store returns at the same control point where the x9 physical-alias store variants V74 and V76 do not.

The current accepted boundary is: the continuation branch is viable; the known high alias `x16` store is viable; the computed physical alias `x9` store is the failing access class. This still does not establish the exact translation or permission defect, and it does not advance the device to UI. Next work should inspect the page-table descriptor and access attributes for the x9 PA path against the x16 KVA path, then test one mapping/access change at a time.


## 2026-11-22: R326 V78 TLBI control

V78 completed a paired RAM-only run on `efff9d92` / `lk2nd-msm8916` / `unlocked=yes`, returned to fastboot, and used no persistent writes. Kernel SHA-256 is `73de1b4d0c1a4e58d38e29f4ef646c12385b1639c2ef5959a0ab2ef20986f146`; boot SHA-256 is `44faa419a1a8004ac75ec93b80289e22395088b8f00d02fb84a977d48f8833ef`; probe SHA-256 is `9e01bdc2950987e58c58724cbe37eef91bbfe2788cb8852c7af26b477db3a909`. Raw SHA-256 values are preclear `bc3dcc0921975ef1821529d8c4841b7b9ec6fb019c67c2ad76e312eea450f33b`, baseline `b342f8e2cd1d92cde1894558122d246878084bfae9f388b90c2a69a241aec7d0`, candidate `a971a03124cdc00359b5136a0630a1cbd3e985ece56bed8fb5d6b90920b9fb45`, and final `b673103364e51d2d8221d201429a7f0acd2afb2e78391ce35f5f4a1e2cdd06f9`.

V78 retains the x9 physical-alias `STR` and replaces only the following `DC CVAC x9` at `L2a14fc` with `TLBI VMALLE1`; the next `DSB SY` and `BR x21` remain. Candidate has no fresh `RRET0GR0`, while the paired baseline return window is zero. The TLBI control therefore did not restore the x9 path. This lowers the stale-TLB hypothesis but does not identify the exact fault or prove the page descriptor state.


## 2026-11-22: R326 V79 physical-alias load control

V79 completed a paired RAM-only run on `efff9d92` / `lk2nd-msm8916` / `unlocked=yes`, returned to fastboot, and used no persistent writes. Kernel SHA-256 is `a1b06ad6be7fbe1972594197633ac83cff71450d17b7bc6360d5f1d04ae2cb9b`; boot SHA-256 is `5ccb1265cdb967ab2f1bcf7ede5422d3d6f092ebf3a651209be2a73567e22042`; probe SHA-256 is `0305246efd17db215322aee99297f8ef4a353e7b4416f6a47e554df8b633e79f`. Raw SHA-256 values are preclear `ad36c101e0c5b1ce328370a2c998ce1e62d9149f14da684ebe212a64fc8196cc`, baseline `6dc383961e57c46e4711fe554d84fd96515f5e1ec8ad59b5f9a6dac1f265fde5`, candidate `29ce46189523a2aedca2b93fce81dedee0aa0f5d402d66c2b38c506c31ca96db`, and final `e2bba1319b67cdd59db239c1fc3de9f62342aefa25511307e2b1420dc74a4066`.

V79 changes the same branch-point instruction to `LDR x14,[x9]` before `BR x21`; candidate has no fresh return marker. Since V75/V76 prove the same branch returns with no x9 access, V77 proves the high-alias store returns, and V79 shows an x9 load also fails, the current classification is a general V=P low-alias data-access failure. This still requires descriptor/context verification before assigning an exact architectural fault cause.


## 2026-11-22: R326 V80 page-table descriptor read attempt

V80 was built from V76 and passed the minimal-boundary transport gate. It replaced the branch-point diagnostic with a high-alias read of physical address `0xa34a2818` (the expected V=P L2[0x103] descriptor) and stored the result at `boot_args+0x9f8`, without touching `x9`. Kernel SHA-256 is `c7166ac01af1d8a142280d8f6858affa8248df47dc886a2c7ece5567423a518f`; boot SHA-256 is `fa7ec51e472961a14290c4d13987a6c4043275d19f6a47d543c160fba0a3fcf2`; probe SHA-256 is `8f750c310104126830cddf38d3e20bcdb59ff7bba9ed2104ab282fd139719df4`.

The V80 candidate raw has no return marker and `boot_args+0x9f8` remains zero. This does not provide a descriptor value: the failure is now in the attempted descriptor-read path or an earlier control-flow/access precondition. No hardware PTE value is inferred. Source-derived expected V=P descriptor geometry remains: root `a34a0000`, low L2 table `a34a2000`, index `0x103`, entry `a34a2818`; the expected template is a normal outer-shareable write-back AF block with the build's kernel-protect/NG choice. Hardware visibility is still unproved.


## 2026-11-22: R326 V80/V81 descriptor-read calibration

V80 attempted to read the expected V=P low L2 entry at physical `0xa34a2818` through a computed high alias and publish it to `boot_args+0x9f8`; it produced no return marker. V81 used the same seven-instruction window but read the already-proven high-alias global through `x16`; it returned with fresh `RRET0GR0`. This validates the diagnostic sequence and branch, and localizes V80's failure to the page-table address/read path rather than the carrier store or continuation.

V81 kernel SHA-256 is `11ec5e5302b8356dee9a51bd3c5e1a334ad55ddf978cb8520778be6d0d05b3c1`; boot SHA-256 is `3e684fa86ec160740ac5777afc309c80b6b2f2738ebc23825fca6f0b6d03f5a0`; probe SHA-256 is `d9fe37175b70927dbd0f794e2334897a813ab56b2d0a761ca678e6b151bcec56`; candidate raw SHA-256 is `bc15c1641fd8d44ca7249c0988b553414f395efa7dd85c695cf4166185b01cd0`; final raw SHA-256 is `ef934004180a270167baced0cdddcfc6cc1aaad1e34d13416611683807cdaa11`.

The descriptor value itself remains unobserved. V80/V81 together prove that a high-alias read of the known global returns, while the computed page-table address read does not. The next diagnostic must validate the page-table physical address and high-alias formula or use an earlier table-owned witness; no PTE value is fabricated.


## 2026-11-22: R326 V83 correction and V84 real continuation

V83 proved the correction: replacing the invalid x9 target conversion with x16 for both `STR` and `DC CVAC` produced fresh `RRET0GR0` and `R68E7ST0`. V84 then restored the original post-store continuation from the V58 Mach-O while retaining the x16 correction.

V84 kernel SHA-256 is `1b52256f56f0ee8046c6bcdc6cd3efbb7fec139340a35153dfd9a3f36b06ad1b`; boot SHA-256 is `c6e87472733b8e0cb7db123e8e2c948e1e283105cafcad858bdf0099d5fdecfe`; matching probe SHA-256 is `a8e782c3e2a33d153409cd6f796756625cf55453a777e182107db9bd11b409ba`. Candidate raw SHA-256 is `bcf89d33ec915c984fa2b6cec30e0d73e10fd233cdfc39fd2b55ae6d193ebdff`; final raw SHA-256 is `fe766319e0a585986a60c5b13c79671edb8e66b26e843020c7f14e9b2be6ada1`. Device `efff9d92` returned to lk2nd fastboot with `persistent_writes=false`.

The final paired readback contains fresh current-generation markers through the corrected path: `R84ENT00`, `R68E7RB0`, `ARGSLOAD`, `STACKS00`, `PREARGS0`, `BAVIRT00`, `BAPHYS00`, `BAMEM000`, `BATOP000`, `BAFLAG00`, `KVACALC0`, `TPIDR000`, `EXCADDR0`, `EXCSPS00`, `EXCSP000`, `INTADDR0`, `INTSPS00`, `INTSP000`, `LINKADDR`, `RLPAGE00`, `RLOFF000`, `R68E7GV0`, `R68E7BF0`, `R68E7ST0`, `LRADD000`, `R68E7PR0`, `R68E7PS0`, and `R84FS00`. This is a fresh continuation through the early `_start_first_cpu` ladder and into the post-return first-CPU boundary. It is not evidence of launchd, display, SpringBoard, storage attach, touch, or complete iOS.

The root cause of the prior x9 boundary is now evidence-backed: at low runtime PC, ADRP-derived `x16` already held the physical alias `0xa0762488`; applying `x9 = x16 - x22 + x23` generated `0x1139762488`. The x16 correction removes that double conversion.


## 2026-11-22: R326 V84 corrected continuation and V85 V=P mapping boundary

V84 restored the original post-target continuation while retaining the x16 correction. It produced fresh final markers through `R84FS00`, `R68E7RB0`, `ARGSLOAD`, `STACKS00`, the boot-argument ladder, `LINKADDR`, `R68E7ST0`, `LRADD000`, and `R68E7PR0/R68E7PS0`. Kernel SHA-256 `1b52256f56f0ee8046c6bcdc6cd3efbb7fec139340a35153dfd9a3f36b06ad1b`; boot `c6e87472733b8e0cb7db123e8e2c948e1e283105cafcad858bdf0099d5fdecfe`; probe `a8e782c3e2a33d153409cd6f796756625cf55453a777e182107db9bd11b409ba`; final raw `fe766319e0a585986a60c5b13c79671edb8e66b26e843020c7f14e9b2be6ada1`.

V85 placed a branch immediately after the actual `VPMAP000` marker store at `L2a172c`, preserving the corrected x16 path. Its kernel SHA-256 is `4cbf347f5eaed0fe270a3387c5c9dda6fb5337502bcc540668135358cf623029`; boot `fcd0817853f712cb38758033012c0fabae7fd57c351a72219c5ae7ebb47f59aa`; probe `ce62b098bf77ac7c817c22180459fdfcf5f5faa990f71e5a551e86c95ce04c26`; candidate raw `bef915acca2d42e4f1b80fa4b600fc6f9190c9f11a93db9242d037f94d2fef77`; final raw `2379d7bf1060b781f717c86e5e381aa91e0fc8e7f08dd11902cb5b3eb683e87f`. No fresh return marker appeared. The current boundary is inside or before V=P `create_bootstrap_mapping`, after the corrected target path and before VPMAP completion.


## 2026-11-22: R326 V86/V87 V=P mapping sub-boundary

V86 placed `BR x21` immediately after the first V=P L1 descriptor store at `L2a16c4`; it did not return. V87 placed the branch immediately before that store at `L2a16c4`; it also did not return. These controls move the boundary into the address/descriptor preparation sequence before the first V=P L1 table write, or the corresponding instruction-fetch/control context. The target x16 correction remains valid and earlier startup witnesses remain fresh.

No descriptor value or UI progress is claimed. The next diagnostic should bracket the preceding `AND/LSR/ADD/ORR` address construction and first table pointer load with an independent carrier, preserving the corrected x16 target path.


## 2026-11-22: R326 V86-V88 V=P mapping controls

V86 branched immediately after the first V=P L1 descriptor store at `L2a16c4`; V87 branched immediately before that store; V88 branched after the preceding L1 table pointer `ADD x10,x1,x10` at `L2a16b4`. None produced a valid return marker. These are diagnostic controls only: because they use the late continuation register, they do not by themselves prove a page-table hardware fault. The current boundary remains in the V=P table-pointer/descriptor preparation window, before the first L1 store, with the corrected x16 target path already proven.


## 2026-11-22: R326 V90 x27 continuation control

V90 repeated the VPMAP000 post-marker branch using preserved `x27` rather than `x21`; it still produced no return marker. This removes one continuation-register ambiguity but remains a diagnostic branch result, not a direct hardware fault classification. V84 remains the strongest real continuation: corrected x16 target path reached the page-table setup region and early startup markers.

## 2026-11-22: R326 x16 physical-alias correction and full boundary capture

A fresh native Xcode 14.3.1 build was produced from XNU `494ffe1c29d37ca720c37328feb83069c9641b67` with the persisted fakeroot/SDK inputs and the V5 source diff plus `native-r68e7-x16-physical-fix.patch`. The linked kernel SHA-256 is `c421346470336105d5f85b4fe68534ea90d10aaec009867556325f4dbc4f6d68`. The offline static gate passes after the verifier was versioned to require `mov x9,x16` and reject the old `sub/add` double conversion.

The matching package is `reboot-checkpoints/r326-x16-physical-fix-package-20261122-01/`: boot SHA-256 `a8ef05e2e78f1cd6960f4a402550167362ef87c6252b8d9d17bc693049a70f08`; package manifest SHA-256 `15c78ff1e9ac12fbf3759244f854cc1e48ebdb338cdc7acecebc1879246d8915`. The full-coverage probe is `reboot-checkpoints/r326-x16-physical-fix-probe2-20261122-01/`: image SHA-256 `cfc965ace13c05810aa1ace42063b8b1142dcb40e30b3dc842d7d248f44ccc4b`, entry SHA-256 `c185cc7a009d2ec047f515aa1aa4ae0e1af85c942958c51a2084f02dbab41140`, manifest SHA-256 `5ce585871ebca29addba3a6cddc7543d71e51db0b36347b719b3a913d1adc9bf`.

The paired RAM-only run is `reboot-checkpoints/r326-x16-physical-fix-run-20261122-04/` on serial `efff9d92`, product `lk2nd-msm8916`, unlocked=yes. Raw SHA-256 values are preclear `0e3bcd9691671501c91e768e25f73dc52cdeb0739896e33b8bd0fd589e91db09`, baseline `8498c9febe6106f40e7e69dfe278c105fb2c6710c40fbd8562dec2360997b361`, candidate `53a15d1436f23f6f76f6c3c433c8ca20570087397ee18ae0d1be4565150000b7`, and final `377997d10879069563014a40f2f0c7b61ec05e47448f5bf70276bbf6a7066529`. The adjudication JSON SHA-256 is `273e6c7a5c380819f7f6215e1f27fa1463b3ab6184532b14e08df8896483c67d`. Every step returned the phone to fastboot; no persistent writes occurred.

Fresh final evidence establishes the corrected direct physical-alias contract: `x16=0xa06ea0d8`, `x9=0xa06ea0d8`, `x17=0xfffffff007ba4800`, `x22=0xfffffff007004000`, `x23=0xa0004000`, and immediate loadback `0xfffffff007ba4800`. `R68E7IN0` and `R68E7RB0` are fresh, and the full store window plus pointer binding agree. Fresh `SCTLRRD0` is `0x34d4593d`, proving M/C/I enabled in this run; fresh `R68E7RD0` and `KVAON000` are also present. Fresh `COMMON00`, `MAPDONE0`, `TTBRDONE`, `PREMMU00`, `PTBASE00`, `PTCOUNT0`, and `PTSHIFT0` show continuation through the page-table setup markers. `PUBLPR00` and `PUBLPS00` are fresh. `FPBEFOR0` and `FPSTOR00` are later overwritten by the temporal `PTBASE00` and `PTCOUNT0` slots, so they are not independent negative evidence.

The accepted current boundary is therefore post-SCTLR, with both alias witnesses and page-table markers through `PTSHIFT0`. This run does not prove `arm_init`, BSD, launchd, display, storage, touch, SpringBoard, or a usable iOS system. The next experiment should preserve this kernel/package and add a narrowly scoped C-entry or first post-`RET` cursor, instead of changing the already-proven x16 path.


## 2026-11-22: R326 C-entry and A53 HID boundary

The C-entry cursor `CENTRY00` was linked immediately before the real return to `arm_init`. With the Apple HID accesses present, `CENTRY00` was absent. The A53-specific no-HID build then produced fresh `CENTRY00` and `ARMINITE`, while `PEINITEN` remained absent. This confirms the six Apple private-register accesses are a causal blocker before C entry on this A53 target; the exact post-C stop was not yet identified.

The next no-HID cursors were then run in paired RAM-only captures. `REBASE00` after `rebase_threaded_starts` was fresh; `CPUDATA0` after `cpu_data_init` was absent. The current C-side boundary is after rebase and before the post-cpu-data cursor, covering const-boot-args copy and/or `cpu_data_init`. The `PRECPU0` build/package is already started and persisted under `reboot-checkpoints/r326-precpudata-cursor-build-20261122-01/` and `r326-precpudata-cursor-package-20261122-01/`.


## 2026-11-22: R326 fresh cpu_data_init subcursor adjudication

The retained-memory instrument was corrected before accepting the new boundary. The preclear-only probe clears `0xa0ba4b00..0xa0ba4b4f` and cleans both cache lines; the regular probe copies the same 80-byte external record without clearing it. In the paired runs, baseline external bytes `raw 0x10550..0x105a0` were all zero, so final markers are current-generation evidence.

The latency kernel package used kernel SHA-256 `715481569cec20d38f1d5151f19ceba030c70557a6e2137d7d2043ecde630bd0` and boot SHA-256 `a11f8bf2be298ab9bb588bb12de5fc43349d9913c9c02681f3c650e3fa369a6e`. Expanded probe SHA-256 `2aa623996ac8f6fd4212aa189a76a8279aaa4e1cebe359d894fc71bb1c8136c3`; clear-probe SHA-256 `5f3b9d7595323309941341d3e044aea45baa076190138596864669995d13e3cb`. Baseline raw SHA-256 `0b4e43d7ebad4573346af52528dc1dfe6ac006bb72ce754a3b791cefa9b17a9f`; final raw SHA-256 `9cf7ea0bc935aa3969c3dd61881857a974daebd6752fc7e05e7cfb23f2d3a6f7`. Fresh final values include `CDIN1300` at `0xb38` after `cpu_idle_latency` and `CDIN1500` at `0xb28` after `cpu_regmap_paddr`; `CDIN1600` and `CDIN2000` are absent.

The phys-id kernel package used kernel SHA-256 `c5a285c721b5e896f3464d2f0bc8d43bfa2d0b987e04e9131f94baa2a94a564b` and boot SHA-256 `0da39e29ceef374879641a53a3b3b132f98cdeb0acbbee541da515f5342243fe`. Expanded probe SHA-256 `8a57a33a98e27b21a6282d93c4fda8c64879b23df4012e6c9d9d1a83948b2b5a`; clear-probe SHA-256 `db426e88c5a645bcb31b2980f269716b2921f32f7300affefb20d02b32f4d05e`. Baseline raw SHA-256 `98a426259c85360206fe1623167261f78751aa10ff92024c5fabeddb098ce172`; final raw SHA-256 `9aac35e6620d23937fb6e861608327bd9aa3c46c87aeb5521f3dee3c73da7c9c`. Fresh final `CDIN1600` appears at `0xb40`; `CDIN1700` and `CDIN2000` remain absent.

The accepted boundary is now after `cpu_phys_id` and before the later cluster metadata / `cpu_signal` completion. Earlier reports that treated un-cleared external strings as fresh are superseded by these paired zero-baseline runs. The next experiment is a static comparison of the phys-id and cluster linked variants, followed by a combined latency+phys-id+cluster asset if the host compiler becomes usable; the already-proven clear-probe contract remains mandatory.

## 2026-11-22: R326 cpu_data_init metadata controls

Fresh zero-baseline controls show that skipping the entire post-`cpu_phys_id` metadata and `cpu_signal` interval produces `CDIN2000`, while controls skipping only the first cluster store, second cluster store, `CDIN1700` marker call, or `cpu_signal` store do not. This localizes the unmodified path to the cluster metadata / marker / signal window, but does not assign one exact instruction because the controls also alter code flow.

The skip-metadata control used kernel SHA-256 `3be457aa483749698396280c7639d0aea0fa3a5805b9e17f7796ec0b30c46ebe`, boot SHA-256 `357caa2aebb54cc2c671394fa91343dabe7630e1b447b899396c4548f0d4ec1b`, baseline raw SHA-256 `8c9999a5c45711a79ad985993c89407fd8bc990cc23501fe981db14cb3403131`, and final raw SHA-256 `5245ee906770c48f88c0054be64e2989dfce46c9c3ce8e2ad65d7944939ff01b`. Final baseline comparison shows fresh `CDIN1500`, `CDIN1600`, and `CDIN2000`; no `CDATER00`.

The cpu-data-tail control used kernel SHA-256 `4970bbcf6ea71aa0fa0c13c8a68d7f4556a42c9a941ff4449c43b1de9789338d`, boot SHA-256 `0dfcc59a4e68855075eb8ee49ae366b5f0b30605d087b2967e76b0d99070d458`, baseline raw SHA-256 `0bdd86a7b9f0fe359153e48433246fb359e8d3a9bbc36faeffba62b434620f98`, and final raw SHA-256 `294d529cf87f4ee3f8c2648d8c2edb6c1c982c3449b3f0a420e70ad6b0fcb791`. It reached the tail marker slot, but the value was `CDIN2000` because the control jump preserved the prior marker value in `x2`; this is a control reachability witness only, not a normal return witness.

## 2026-11-22: R326 A53 FP control resolves cluster-store boundary

The cluster path was retested with a binary control at the actual linked `common_start` addresses `L2748cc/L2748d0`: `mov x0,#0` became `mov x0,#0x300000`, and `MSR TPIDR_EL1,x0` became `MSR CPACR_EL1,x0`. This sacrifices the TPIDR clear only for diagnosis. The original cluster stores were left unchanged.

Kernel SHA-256 `3ac582a2c5d57e4d1da2b353886d198499fbf488f2c8fafdc76881c9bdc29d06`; boot SHA-256 `976ab6c55adb06928b190cf09f0975339255ff9da39318dd0a2a5cdc24d629dc`; baseline raw SHA-256 `b056aa4506dd901c76e3dece286823d1274be85626241318f81dd943a89e90da`; final raw SHA-256 `449219a5fff37c962e087a82186ff21a3acc114f397d70d2daf28ade1326a055`.

Fresh final contains `CDIN1500`, `CDIN1600`, `CDIN1700`, `CDIN2000`, and the corrected `CDATER00` tail marker. This proves the original SIMD cluster stores and cpu_data_init tail can execute when FPEN is enabled. The source build did not include `native-y35a-a53-enable-fp.patch`; the missing A53 FP enable is now the leading causal fix candidate, supported by the binary control. TPIDR preservation means this control is diagnostic and not yet the final source candidate.

## 2026-11-22: R326 FPEN control reaches arm_init after cpu_data_init

The FPEN binary control was paired with an expanded probe that captured the original const_boot_args slot 51 (`0xa00d2f08`). Kernel SHA-256 `3ac582a2c5d57e4d1da2b353886d198499fbf488f2c8fafdc76881c9bdc29d06`; boot SHA-256 `976ab6c55adb06928b190cf09f0975339255ff9da39318dd0a2a5cdc24d629dc`; baseline raw SHA-256 `89e3afbadfd11fb7165d3fcdd91e0909c9a1ef3ced4c3aa3fe4cdad89a4af37b`; final raw SHA-256 `d1e1fd5ff82b0b9228e112ee4ad132d6e38edb2b0ecc22680b602bc2b4204bea`.

Fresh final now contains `CPUDATA0` at the original const_boot_args slot, plus `CDATER00` at the corrected cpu_data tail, `PEINITEN`, `PEINITRT`, `ARMVMINI`, `PANICINI`, and `CONSOLE`. This is the strongest current R326 continuation: FPEN-enabled cluster stores execute, cpu_data_init returns, and arm_init proceeds through platform, VM, panic, and console initialization. The control still sacrifices the normal TPIDR clear and is not yet the final source build.

## 2026-11-22: source-level A53 FP build

A local CommandLineTools build completed after the external Xcode SDK compiler path was bypassed. The source tree includes the formal `native-y35a-a53-enable-fp.patch`, and the linked common_start disassembly now contains `MRS CPACR_EL1`, `ORR FPEN`, `MSR CPACR_EL1`, `ISB`, followed by the normal TPIDR clear. Unstripped kernel SHA-256 is `505da572a9d7eb9ea4fd085d4b654f373a872a57fd7b25cafff7df2a9dc19d5e` under `reboot-checkpoints/r326-cpudata-fp-source-build-20261122-01/`.

The existing package assembler lacks an ELF lld/objcopy tool, so this source kernel has not been claimed as a booted package. The binary FP control remains the current device-tested carrier; the source build is the formal replacement input pending packaging.

## 2026-11-22: source-level FP package paired run

The source-level FP kernel was packaged with local `rust-lld` plus the ELF text extraction wrapper. Kernel SHA-256 `505da572a9d7eb9ea4fd085d4b654f373a872a57fd7b25cafff7df2a9dc19d5e`; boot SHA-256 `7fb3a30f0545ca059c9874ce8850d24b34450f866a44c68985a9385ffced34f5`. Paired raw SHA-256 values are preclear `e30103d107a8d132929c5af222cd95b5a1851258b5d241f8cb0412344e1c2ccd`, baseline `6a79f0e4cda90e31ef9ec28a7ad46061608b763fe640e5def90656e643dde95f`, candidate `b7ee239c5cceee10e971973a648afc51177ea91d7bdf8c00e1c8858837825197`, final `a63e4cf4cb7225169a5642f9917af1a82e40d7639d72c0d7114ebfeb334e45fd`.

Fresh final contains CPUDATA0, CDATER00, PEINITEN, PEINITRT, ARMVMINI, PANICINI, CONSOLE, CDIN1700, and CDIN2000. The source FP patch is therefore validated through the same arm_init/console boundary on a freshly packaged kernel. No Apple logo, launchd, SpringBoard, or UI witness is present yet.

## 2026-11-22: formal source post-console boundary

The formal source-level FP kernel with post-console external cursors was paired RAM-booted. Kernel SHA-256 `32f937357f81738b9e53cd801c51f9e32ab4d4b3e1a465de174ecd3a9aaf3a93`; boot SHA-256 `075fb3f72a58ad8c55638e6a45e23f5dd226f71f52f28a61217c10dcc11ac5f9`; baseline raw SHA-256 `da9f6cfde0b606f03b47a7dd29e2c3a6ff5bd036796db82432f5203f286df67b`; final raw SHA-256 `6c57816f8c96bf5bed3db789472a7e001ad35e0b98124a2beca8343b04c44aae`.

Fresh post-console markers are `POSTCNS00` after `PE_create_console` and `POSTPRT00` after `PE_init_printf`. `POSTIDL00`, `POSTPLT00`, `POSTTIM00`, `POSTFIQ00`, and `POSTMST00` are absent. The accepted formal source boundary is therefore after console printf initialization and before or inside `cpu_machine_idle_init(TRUE)`. A later binary skip control is retained but is not accepted because its marker relocation did not reproduce the formal post-console evidence.


## 2026-11-23: R91 accepted boundary

R91 paired run `reboot-checkpoints/r326-r91-machine-startup-cursor-paired-run-20261123-24/` used kernel `b50eee7ad783390971e43d7bb61c9e8e606174343c8dc27dcd10a3e039df3e15`, boot `d01a4c2141fb845f89cc3330e21d9efd5a50be563cbf2d06183c71508102bb72`, regular probe `b556e0801bae5024a7e7e9bd3384b6532378f5eb37c7e30aa0b1af8c9bbb8022`, and clear probe `cde76b4d5643755de44368370a00717dc2085dbc9571bb7d7f9f46b20071fe0f`. Raw hashes are preclear `80b29219b5dc47e5a1cae475984ff0e13a955f39b1e5d7f00388ec700b87c2fd`, baseline `8b89756ca6a342a566e6f781fe6b7539b48f309e3711059efe0281e0ea25a473`, candidate `c2614086777097da8036061b908af6ab85fde1e16e1e84333f4aff50eeb9efbd`, final `56127969c217f999fd3093a6ccce05d51a40aee1fe67a7fcdb72b544db4d275a`.

The final regular-probe external record is fresh after zero preclear/baseline and 15 copied records. It contains `IDLEBEF0`/`IDLERET0`, then `MCHCALL0`/`MCHENTR0`/`MCHCONF0`, then `KBOOTEN0`/`KTHRBEF0`/`KTHRRET0`. The accepted boundary is after `machine_startup`'s `machine_conf` and after return from `kernel_thread_create`, before the explicit `KERN_SUCCESS` check. Candidate external bytes are not used as physical XNU evidence.

Next: R92 adds a success marker after the `result != KERN_SUCCESS` branch and a `KBTENTR0` marker at `kernel_bootstrap_thread` entry.


## 2026-11-23: R92 kernel-bootstrap boundary

R92 paired run `reboot-checkpoints/r326-r92-kernel-bootstrap-cursor-paired-run-20261123-31/` used kernel `865466467ebbaf6e36d07b58e02ca191789c7cedbf1bb76633d43fb550317ae3`, boot `7bd280daa287dccbcfa41751cafffa0b5d9506005219f2a1204fdb7d244158c0`, regular probe `d2380db6878b1ce86daab9e4c7d60fcafc7f2ad81f4b94b634b3986c01a56176`, and clear probe `6dfdd3b9265312057b5e71b18aa467c057c6d7b6a9b57fbdf7ad814aeb564c61`.

Raw hashes: preclear `7d07dd335365ef3249ea1bdc953b22e18fef378ca5eb97f524139032cd2d1797`; baseline `4a81e2f1f5628a1a8be33d8f270265bdd4dc932837e4942ecc38f8376899d0ea`; candidate `fdbf43569b2aa7e4956db9ec31b4d66185e78770858a63edc6fefae5cbadd8ab`; final `0c138b16f4e9b65edc35c7e2258a8172735daf734c2bd3f4b77c1f8b39f09948`. Preclear and baseline external data are zero; final is same-channel fresh evidence.

`KTHROK00`, `KBTENTR0`, and `KBTIDL00` are absent from final. The existing R91 markers remain fresh, so the measured boundary is after the `kernel_thread_create()` call returns and before the explicit `KERN_SUCCESS` pass marker or `kernel_bootstrap_thread` body entry. Next R93 adds markers after `sched_startup`, `thread_daemon_init`, and `thread_call_initialize`.


## 2026-11-23: R93 thread-init boundary

R93 paired run `reboot-checkpoints/r326-r93-thread-init-cursor-paired-run-20261123-39/` used kernel `3d480f82773d28fb1826921c8eb10ae09e880560268243a00463eee5351cc75a`, boot `d8425c1165e0af62e31f7b206cc758e24c302fb0365860b09a5e4437b7c63230`, regular probe `58f8e7956ef2d9d08464f0ce5dd1502f63c8220cae758f0c95c66610164e62d2`, clear probe `13c27c899bfa1f0330d52a3263611c16890fe92d3f89c0d0a98144871b21dc54`.

Raw hashes: preclear `fbd263a62269b449a02f20e09ddea2b2e7835839e2c5b6314d6dcf32fe7b8202`; baseline `ae2f6a10fcb75b700b78de6c48f0cf90b64325f0ab00411d844272d4b74386a5`; candidate `a6af23f2523e9ede1228477c5e6ed3a54d46acfee187680d86773538f2c9f0f7`; final `c2988656c779cb820e3c6d99c76bf8fc073e931958f56abcccabfe95cf8648ae`.

The final same-channel record has the R91/R92 markers and lacks `KBTSCH00`, `KBTHD000`, and `KBTTCI00`. Thus no `kernel_bootstrap_thread` entry or scheduler-return witness is established. R93-38 is retained as a mixed/aborted run with preclear and baseline only; it is not included in this accepted sequence.


## 2026-11-23: R92/R93 marker-layout correction

独立源级复核发现 R92/R93 新增 marker 的 offset 使用错误：`native_external_phase_marker` 以 `native_phase_args + offset` 写入，而本轮 external probe window 从 `args+0xb00` 开始，物理范围为 `0xa0bacb00..0xa0bacbff`。R92 的 `args+0xc8/+0xd0/+0xd8` 与 R93 的 `args+0xe0/+0xe8/+0xf0` 均落在 probe window 之外，因此 R92/R93 final 缺少 `KTHROK00`、`KBTENTR0`、`KBTIDL00`、`KBTSCH00`、`KBTHD000`、`KBTTCI00` 不能用于判定这些阶段未执行。

R91 的旧 marker 位于 `args+0xb98..0xbc0`，正好对应 external window 相对偏移 `0x98..0xc0`，其边界结论仍有效。R92/R93 run、raw 和失败/混合 sequence 保留，但相关新增 marker 裁决标为 `UNVERIFIED` 并由本条 supersede。R94 修正版将 marker 放到 `args+0xbc8/+0xbd0/+0xbd8/+0xbe0/+0xbe8/+0xbf0`，并要求 gate 逐项核对 linked source offset、probe manifest PA/size 和 preclear 几何。


## 2026-11-23: R94 corrected thread-init boundary

R94 uses corrected offsets inside the external window: args `+0xbc8/+0xbd0/+0xbd8/+0xbe0/+0xbe8/+0xbf0`, mapping to relative offsets `0xc8..0xf0` from external `args+0xb00`. The layout gate passed before build/run.

Accepted paired run `reboot-checkpoints/r326-r94-corrected-thread-cursor-paired-run-20261123-47/`: kernel `b9992598c9ae717dc36173a5f8642252c9ef9ceb6ca7d15dd478081aa880bee6`, boot `d6ad8238d1f13791bcb33d86fe191d414970725b0a44c7bbf97132d6e1a375de`, regular probe `0b66c4551ece493d63696c138ee01bbea59a2acb19ad843cf08ee58423c5c925`, clear probe `2cd7b970631b732274a51cc86bc1b94e919cfa4023c17c724992fdd34721c5d5`. Raw hashes: preclear `1fa34fdd5bd9baa071cf9c2e3872e169821972e40dfb932d03875175c50e8397`; baseline `b9e643fea98ff92912a267ef802898b2625711058536636d38715e61e0dfc523`; candidate `cfb368610b6e7d6abf818b8cf4d0d0badba269915de439593a9f98e809abfa68`; final `caaba9407e6035a5de8b62722672e9f2bdbed0fd8e3d778e03aa23a9d51842b0`.

The same-channel fresh final contains all six corrected markers. Accepted boundary is after `thread_call_initialize()` returns, before `thread_bind()`. R92/R93 marker-absence conclusions remain superseded by the offset correction.

Next R95 adds return cursors after `thread_bind`, `ipc_thread_call_init`, `mapping_adjust`, and `clock_service_create`.


## 2026-11-23: R95 thread-service boundary

R95 uses a 512-byte external record at `0xa0bacb00`, with preclear and regular probes independently bound to the same 512-byte geometry. Kernel `c3131ea5ada5102ce2c1b05c8be5286d5bdd788b71798ad4617f01a038c7c87d`, boot `926a4dbac051889dea964e1f88e0860ae4c75bebff8a5b422d132635647884e9`, regular probe `d1fa2019f6fed6af6b2e265db4dc761d2d5fb81055e74ad89bb433cd4fa65565`, clear probe `606ba7ee5d6a11d2a3c4e386f54e763afa3e595e7a447efac3b2020e56b0abd6`.

Run `reboot-checkpoints/r326-r95-thread-service-cursor-paired-run-20261123-55/` raw hashes: preclear `151311b2e1d1e8281e79ef33f279e3e6aaf01ec478d3e09183f8903be7809af8`; baseline `f360b1e1ac469228a4245450ca9514137744721949bd5d0db8e41d4fa3768091`; candidate `97d321f2b57e0158574c75bce56d9512bf36af9c2f5ea5633385cc537cd8b2b4`; final `a2fba487b302198f6d317970b4947d476b2d0591fa64cf73065e5a1cffc2144f`.

Fresh final confirms the thread-init path through `device_service_create()`. The current boundary is after device_service_create and before the later debugger/ktrace/user bootstrap sequence.


## 2026-11-23: R96 bootstrap services boundary

R96 paired run `reboot-checkpoints/r326-r96-bootstrap-services-paired-run-20261123-62/` used kernel `81e5dafe3d5edcd7517cabb90de044554add2e3e8febd1123769babaf07a7f34`, boot `6e3a9f889cddbde1060b0c4b84777d4aea434fc495940edae1b357cebd7da96e`, regular probe `b82f289960b8f5c1a5c47e4b370c49cc0524909f4692b76487a6cd2d3b72549e`, clear probe `14949948f59383eec325da9b21effdbaec264bbd2d32cb20ed8a54e2f9d8c41b`.

Raw hashes: preclear `303ca17ac5e9daa12a5316aa894a56bf450f2c483e69d868b9ccfe42c7479b75`; baseline `58e62179158e43fe8c266a7acde82bca6d8b8488c666be3fe1cd42444054eadb`; candidate `325f437b46facfc365ce1e13d18501eeafef22fafe0faf049f0d3651f2034a8e`; final `e5fb9a8e1d7e5a86dbcfaf510395d4adb57211eb222d9fdf211d336c670a7f74`.

The same-channel final contains `KBTKTR00`, `KBTBSD00`, and `KBTIOK00`; `KBTMAC00`, `KBTSFI00`, and `KBTPOST0` are absent. Current boundary is after PE_init_iokit and before mac_policy_initmach.


## 2026-11-23: R97 post-policy boundary

R97 same-channel fresh final confirms the R95/R96 sequence through PE_init_iokit, but contains none of the corrected `KBTMAC00`, `KBTSFI00`, or `KBTPOST0` markers. The measured boundary is before or inside `mac_policy_initmach`; no inference distinguishes the call entry from a prior failure until a separate entry marker is added.

Run `reboot-checkpoints/r326-r97-post-policy-paired-run-20261123-69/`; kernel `06a1af85b9b5d1570937669481a6a60ff992b9dcffe48501ff2f0a6ce5b92a39`, boot `26873d11ea2c54abb66b01abe0be35c8822f304112a35e961b696c07a845239c`, raw final `d9e7659b9f8843bfe25ff3d5fcd993d3599eac3b1e454c4326b9976b984a4e04`.

Next R98 must add an entry marker immediately before `mac_policy_initmach`, preserving the same 512-byte geometry.


## 2026-11-23: R98 mac-policy entry cursor queued

R98 adds `KBTMACEN` immediately before `mac_policy_initmach` at args `+0xc48`, which maps to relative external offset `0x148` in the 512-byte record. The source-to-manifest marker gate passed. Kernel build is complete with SHA-256 `f06d882180c064fb2ab781f91853613e812fde165cbfa1cabc4d03dc1838ad70`; package/probe and paired RAM-only capture remain queued.


## 2026-11-23: R98 mac-policy entry boundary

R98 added a correctly windowed entry marker immediately before `mac_policy_initmach`. The paired final has neither `KBTMACEN` nor `KBTMAC00`, while all earlier bootstrap markers remain fresh. The accepted boundary is before the `mac_policy_initmach` callsite, not inside the function.

Run `reboot-checkpoints/r326-r98-policy-entry-paired-run-20261123-76/`; kernel `f06d882180c064fb2ab781f91853613e812fde165cbfa1cabc4d03dc1838ad70`, boot `45bc744f0f9010c4bfac06ff1b760350bcfae3fdf6cffa67975e16d1479db079`, final raw `c9f7067469991cab29510b73f9817c63f9eac3a9848b91f184db029dc2278b9c`.

Next: bracket the immediately preceding `vm_commpage_text_init` / `vm_shared_region_init` sequence and the mac-policy entry callsite with corrected in-window markers.


## 2026-11-23: R99 commpage-policy bracket build

R99 corrected patch context from the R97 staged source after the first R99 apply failed against an R95 context. The corrected R99 patch SHA-256 is `96fa71a3514a568c0b4fb8e44f3b10c3bf51717e767f40ebfd843a557657d367`. Build completed with kernel SHA-256 `b7dbac43a61e2445097b30e99dccb7a24d7dccecabcb3875c68f52b1d3466ddf`. Package/probe and device capture remain pending.


## 2026-11-23: R99 commpage boundary

R99 final same-channel evidence proves `vm_shared_region_init()` returned. It does not prove return from `vm_commpage_init()` or `vm_commpage_text_init()`, and does not reach the mac-policy entry marker.

Run `reboot-checkpoints/r326-r99-commpage-policy-paired-run-20261123-85/`; kernel `b7dbac43a61e2445097b30e99dccb7a24d7dccecabcb3875c68f52b1d3466ddf`, boot `dcc2e19d5b39a3aea1000d9e9b7f757a02d6bae4caf860d088246910d38f0f09`, final raw `5226e946be57d24285863ab312ffd635370c47048871b7f74a1e969fe61bb452`. Next R100 brackets vm_commpage_init entry/return.


## 2026-11-23: R100 vm_commpage entry/return build

R100 adds `KBTCEN00` before and `KBTCRE00` after `vm_commpage_init` using the existing 512-byte external window. The linked kernel SHA-256 is `49cbe12f3c6871edab319825e35d3734411e253a9b2df812c58f8ca607a95dd7`. Package/probe and paired capture remain pending.


## 2026-11-23: R100 vm_commpage boundary

R100 proves execution reached the `vm_commpage_init` callsite and returned from `vm_shared_region_init`, but does not prove `vm_commpage_init` returned. Same-channel final raw is `e455d392f8a20b1d8b2279fa4ef795ed2902992693523973c64bf8d1fa609b7d`; kernel `49cbe12f3c6871edab319825e35d3734411e253a9b2df812c58f8ca607a95dd7`. Next R101 brackets the internal commpage init path.


## 2026-11-23: R101 commpage internal build

R101 corrected patch order (`R91→R94→R95→R97→R99→R100→R101`) and linked successfully. Kernel SHA-256 `3478dc6c5bd119028d8b63422f6a89d4814fd0ccd5887fa052470c5821c5ef53`. It adds `KBTCINT0` at vm_commpage_init body entry and `KBTCPOP0` after commpage_populate; package/probe/device capture pending.


## 2026-11-23: R101 vm_commpage internal boundary

R101 same-channel fresh final proves the body entry of `vm_commpage_init()` but lacks `KBTCPOP0`, the marker after `commpage_populate()`. The current boundary is inside `vm_commpage_init`, before or during commpage_populate.

Run `reboot-checkpoints/r326-r101-commpage-internal-paired-run-20261123-101/`; kernel `3478dc6c5bd119028d8b63422f6a89d4814fd0ccd5887fa052470c5821c5ef53`, final raw `0ba8e8661305a40f35e627c0758c90e44ba80ce9b17c30677af4f1a9694bc502`.


## 2026-11-23: R102 commpage_populate internal build

R102 adds `KBTCPEN0` at `commpage_populate` entry and `KBTCPR00` after its final initialization writes. Kernel SHA-256 `e10507ded452e690c168ec65ee34e7427444278fae9bb7c31c423bdf4f364053`; package/probe and paired capture remain pending.


## 2026-11-23: R102 commpage_populate boundary

R102 directly instrumented `osfmk/arm/commpage/commpage.c`. Same-channel final proves both commpage_populate entry and return. Run `reboot-checkpoints/r326-r102-commpage-populate-paired-run-20261123-108/`; final raw `8c3853b84c2985fad64305e91653139136507c46145b339b2109b095f6ce48a7`. Next boundary is vm_commpage_text_init before mac_policy.


## 2026-11-23: R103 commpage-text boundary

R103 directly instrumented `vm_commpage_text_init` entry/return. Same-channel fresh final proves both markers. The accepted boundary is after vm_commpage_text_init and before mac_policy_initmach.

Run `reboot-checkpoints/r326-r103-commpage-text-paired-run-20261123-117/`; final raw `d526a346f4853c98e2289231302a0c1b636c6c2b5756f105063338700ee07336`.


## 2026-11-23: R104 post-bootstrap boundary

R104 fresh final confirms commpage text/entry/internal markers through `KBTCINT0` and still does not reach the corrected mac-policy entry marker `KBTMACE1`.

Run `reboot-checkpoints/r326-r104-post-bootstrap-paired-run-20261123-126/`; final raw `755ac573f12b641b64f5586272c652a8146aeb7caa582a935359bd43752f6b8c`. The next experiment remains a mac-policy callsite bracket, then sfi/kernel post and BSD/user bootstrap.

## 2026-11-23: R105 commpage caller resume adjudication

R105 completed a RAM-only paired run on efff9d92 and returned to fastboot with persistent_writes=false. Kernel 7cc801f747797f7fbec16df6836cd1f44143b19b1100f2154c272ac3feba6616; boot 40683d0477a317b6d7f81f2c63032ae1a0dad5ae04d69f5102a268cff2a90acf; regular probe bd1dcf93a7b519c104138cb75023c462eb5b6a23730537e3377c0d59500a7e49; clear probe 0b317402d2292cda4937553d658b0368155f8b2aa9c0dea29347483d7c8fd010. Raw SHA-256: preclear 4b888266e85e87288be5309f5be833c3feeca5f2def891e0a7b04d422c802abc, baseline da45264a1dbaf75e12b9b6f888461744a5685293c68a88c1fd646eb625f868d1, candidate 1d660916ba797ff1ae871c27749bf5851bdb492de4e73694d8efdd728af28a80, final 3ea25aef87a1f265a853f2cb72959db219294488817a0b144919b2f805415c29. Full adjudication: /Users/lingion_k/unixnu-research/reboot-checkpoints/r326-r105-commpage-caller-paired-run-20261123-133/adjudication-r105.md.

Fresh final external record contains KBTCPRE0 (args+0xc68), KBTCINT0 (args+0xc90), and KBTCPEN0 (args+0xca0). It does not contain KBTCPR00 (args+0xca8), KBTCTEN0, KBTCTRE0, or KBTCTXR0. Because args+0xca0 is shared by the R102 commpage-populate entry, R103 text-init entry, and R105 caller-resume marker, the retained KBTCPEN0 proves entry into commpage_populate() and disproves caller-resume evidence for this run. Current measured boundary is inside commpage_populate() before its return marker.

The independent phase verifier command failed with manifest must contain one fault-pointer-window record; the R105 readback manifest contains fault-publish-window but not fault-pointer-window. Raw evidence remains valid for the narrow fresh marker adjudication, while the full static gate is pending repair. Next: compare R102/R105 source and link inputs offline, allocate distinct slots after args+0xcd8, repair the manifest contract, then run a new paired experiment.\n
## 2026-11-23: R106 commpage populate internal cursor adjudication

R106 completed a RAM-only paired run on efff9d92 and returned to fastboot with persistent_writes=false. Kernel d92e3814df0ba33023bd0d527c957ccb5323ad762b7ffc3e0ab351e7523dda1d; boot 7f3aa6de965165a0c4c95a6ad16d127d5d62015777999fd84df7d3cbe6710f29; regular probe 6de7082cad84d8416dba6db85c0736440f3743e85f0cb771716bd38db0fd9f2a; clear probe 58fcca88bddfc70c5fa333d3495be84b4a5988215e7ea849e849a0653c693fca. Raw SHA-256: preclear c94a012aa871e71a93637f49f7b4ab843724ff66aeeaba5a4a6e3318c3795c91, baseline f32008d52be38acc021fd3b8b6e9d33fd657a8a0a7300bdb87b57508fb53da28, candidate daaf21d638ff147e3442b2b300b4d2d00067cb09166b79c4770305e505620483, final 23c3039ed51f39c203736d9a4f7e9789e6ab9c75ce3e151cd9c647527d99efd7. Full adjudication: /Users/lingion_k/unixnu-research/reboot-checkpoints/r326-r106-commpage-populate-internal-paired-run-20261123-146/adjudication-r106.md.

Fresh final contains KBTCPRE0 at args+0xc68, KBTCINT0 at args+0xc90, KBTCPEN0 at args+0xca0, and CPCMP0M0 at args+0xce0. CPCMP0M0 is placed immediately before pmap_create_sharedpage(), so the current boundary is after commpage_populate entry and before that call's return. No later internal cursor or commpage return marker is present. R106 phase, capture-layout, and transport gates all returned ok:true.

R107 is already building offline with distinct after-call cursor placements. Continue with package, dynamic fault-pointer-bound 16-record probes, three static gates, and only then another unique paired RAM-only run.\n
## 2026-11-23: R107b post-sharedpage commpage cursor adjudication

R107b completed a RAM-only paired run on efff9d92 and returned to fastboot with persistent_writes=false. Kernel ebc1e1ca5e5e8e5a7125e28148b92e566c3cbc76169fa7459a77a8da1d47b297; boot 9547c1c77d41609d73e23392ea3b0cefe5d3b423d42aaf7c54db93034f1a551a; regular probe 90c05e14ba48e6dd06072dcb3139dc7323aef7b1b7115e05b54c1dac61ac6d94; clear probe ada5ef216d34ec984503c19be63747aa3f092ef1b2a7a05a18ef91a53d9db099. Raw SHA-256: preclear 89bf0a752c632ce2a3c180ed123970d45b19a0517af45bd1b3e7b4489fbce730, baseline d6b8240293e05cf1f67505f68616c4531461bb4e2f24bce7db892b1a965a82a3, candidate c53ed820b8b59f12ed2c4c5f7c04a4469ad324ce85d42722a6f7d86b4fb08c32, final 6dc22e5d0f048520426496b868f830f3412534c1db943c18b3e4d5f211ae12fa. Full report: /Users/lingion_k/unixnu-research/reboot-checkpoints/r326-r107b-commpage-populate-subcursor-paired-run-20261123-154/adjudication-r107b.md.

Fresh final contains KBTCPRE0, KBTCINT0, KBTCPEN0, CPCMP0M0, and CPCMAFT0. CPCMP0M0 is immediately before pmap_create_sharedpage(); CPCMAFT0 is after pmap_create_sharedpage() and commPagePtr setup. The next CPCAPOK0 and CPCPUOK0 markers are absent. Current boundary is after sharedpage setup and before the combined capability/time completion marker. All three static gates returned ok:true.

Next experiment R108 will split capability initialization and timestamp completion into separate cursors, with new unique artifacts and paired raw files.\n
## 2026-11-23: R108 capability/time cursor adjudication

R108 completed a RAM-only paired run on efff9d92 and returned to fastboot with persistent_writes=false. Kernel 1cbb054a90ed48ee91d60404a7daec43ebf31253da1f4e0cad8cd3d8106773fc; boot badc7ff87ee97e5fc8f2716084aa7624228e47924226093644222881d3329e95; regular probe 82fcfb0085d22f8083e5cca0395567325a5852bb44d65c08603a1cf9e00d08ae; clear probe 5206dbeecc78ac01f22a6e16297c4b97dccf027174f5f86d7516e1f2e28eb484. Raw SHA-256: preclear 737007ecddd3c75c87fc3023e648fdb3ea3bb6b6da5cf535a9a514862b1bf2e7, baseline 004ff62d5653051e9047dcb4553995ab6984ecead9aa198bf1c6af33ba83106f, candidate 739c2a053db2e325aa430cddd7dbb2e8f39225374866e496832f0651b297852a, final 18605104199a8a0d33337c5bcfd99fd60745471e102ff125a3ecb9dfa2e21131. Full report: /Users/lingion_k/unixnu-research/reboot-checkpoints/r326-r108-commpage-capability-time-paired-run-20261123-160/adjudication-r108.md.

Fresh final contains CPCMP0M0 at args+0xce0 and CPCMAFT0 at args+0xce8, but neither CPCAPOK0 nor CPCPUOK0. This proves pmap_create_sharedpage() returned and commPagePtr setup completed; the current boundary remains before commpage_init_cpu_capabilities() completion. All three static gates returned ok:true. Next R109 will instrument commpage_init_cpu_capabilities() internally with new unique source and run artifacts.\n
## 2026-11-23: R109 capability helper internal cursor adjudication

R109 completed a RAM-only paired run on efff9d92 and returned to fastboot with persistent_writes=false. Kernel bd61faec62d9f813cf80d092b79cf90d13e22af0ad1eedc17d7e8a5887b417b9; boot b9f5be4aadf51adf8ae328a6625cd8e33433069b030e54df778dbf808c5bfda3; regular probe 172668e2db411421f8705e71e49cec84b7337aa2e5aebbc38d8b1503a68a5dfe; clear probe 2e89d91f71a74f119437ebd8b3ded09fab55281a9561383f10d610e2aeac0861. Raw SHA-256: preclear c7566be0e591a041124d048ea2619ac772e98ead3e4b220358347d59e3e1ca6f, baseline 2e66fb0b7160b388d9c023f3df4c4b6135aa80f091f77369d1ff658dac693c06, candidate f5136e9a62cbd63b6413982760bfc443ea16a48699975ccfe2be4eec2d38d0fc, final 4f5c2ecf579c360ec44e1040a1439b0cfe25d8cc6bd59b9dcaa515c0c296297d. Full report: /Users/lingion_k/unixnu-research/reboot-checkpoints/r326-r109-commpage-capability-internal-paired-run-20261123-166/adjudication-r109.md.

Fresh final contains CPCAEN00 (capability helper entry), CPCMAFT0 (sharedpage setup), and CPMLOK00 (ml_cpu_get_info returned). CPCPCOK0 (commpage_cpus returned) is absent. The measured boundary is inside commpage_init_cpu_capabilities after ml_cpu_get_info and before commpage_cpus returns. All three static gates are ok:true.

Next R110 will split commpage_cpus() and its immediate caller path with new unique artifacts.\n
## 2026-11-23: R110 ml_get_max_cpus cursor adjudication

R110 completed a RAM-only paired run on efff9d92 and returned to fastboot with persistent_writes=false. Kernel 673d91c4b4ff3a759ad4655fe4b4463fcca560b92800a241974a6a1265ef2531; boot ed62422249cd35e678d5b1a70cb9809a27716ef91081e27a608372049c21b96a; regular probe ae2c20f3532fbd1d7f4bbdc9c4df81cc01131f5835918e4bff47cf98bd19f334; clear probe 90ed7573346fec74054dbe239ba5fe440fea2ab5799eb20cd0b5980f26ca03bf. Raw SHA-256: preclear 417b0fd99079c533c1b53278e7d3001de85353165834cf2776a6b4666ac0bdcc, baseline f28e6cd9868404e0f1726cf28a20a14d1c710dbc0b8b1b8f0b9ec0929d226177, candidate 5339e9b9ca71a842501c373177f9fa7c1ea9b2b31f6dca2bc5fdd7fc3f000e55, final 1aca359096f7f26f2d1c992dc528b360bd83fdc5da7bb0c60d0ab17c41904514. Full report: /Users/lingion_k/unixnu-research/reboot-checkpoints/r326-r110-commpage-cpus-paired-run-20261123-174/adjudication-r110.md.

Fresh final contains CCPUNEN0 (commpage_cpus entry), CPCMAFT0, and CPMLOK00 (ml_cpu_get_info returned), but not CPCRUN00 (ml_get_max_cpus returned). The current boundary is inside ml_get_max_cpus, whose source can wait in thread_block while max CPU initialization is incomplete. All three static gates are ok:true. R111 is already building offline to instrument the wait path.

## 2026-11-23: R119 marker correction and backup audit status

R119 completed a paired RAM-only run and returned fastboot. Kernel 0b15324d406a3cfe253b8a478d175b3af87233b160199ccdafb4cf1abe898df2; boot 44fae66a83577593bc7068ba9c143e782a194d1dd374807fe1521f50a4b0bbb4; final raw f717c03911e577190dec3e18f50468f53486c3776e6699f6c36cc3e1520ec8d...; full report is in the R119 run directory.

Fresh evidence validly reaches KBTMACR1 and MLMAXRT0. CPCNUR00 is the last writer at shared cf8. R119 pre-BSD markers are invalid for negative inference because of slot reuse and unaligned overlap; R114/R115 BSD markers are also invalid. R116/R117/R118 dedicated windows remain the valid negative controls and showed no BSD/SFI/post marker.

Backup correction: GOAL-required device-backups/efff9d92-20261123 does not exist. The only visible candidate is device-backups/efff9d92-20261119 with boot.current.img and lk2nd.current.img. Full partition backup and EDL/firehose recovery remain unverified; no LKG is registered.

R120 was stopped before device use. Next build starts from R118, uses aligned free slots after args+d60, and enforces marker ownership and overlap before package or device execution.
## 2026-11-23 R120 gate state

The active work is split into two mutually exclusive offline gates. Gate one is R326 startup marker contract repair: every required marker must have a fixed name, codeword, offset, 8-byte width, alignment, owner, semantic position, and carrier binding; all source marker calls, including inherited calls, are scanned for duplicate offsets and unauthorized reuse. Gate two is RAM evidence reconciliation: the candidate boot_args, ADT, manifest, staged runtime DTB evidence, and recorded usable windows are checked separately by scope.

The staged runtime DTB is `evidence/y35a-20261102/lk2nd-runtime.dtb`, SHA-256 `36555c5e66b4a09cd38506706b0a301c2c8b8d6b883de51c51b89971825e9709`; it reports two 1 GiB banks totaling 2 GiB and no FDT reserve-map entries. It is not the final candidate DT. The current maximum-memory candidate is offline-only and internally consistent at `0xa0004000..0xffe04000` (`0x5fe00000` bytes). The original `/proc/iomem` raw dump remains unavailable; the three windows in `PROGRESS.md:11` are a recorded summary.

No new paired device experiment, BSD claim, IOKit claim, storage claim, or UI claim is permitted until both offline gates are green and a new exact package/probe binding exists.

## 2026-11-23: R121/R122 maximum-memory startup boundary

R121 maximum-memory paired run completed with kernel `3fb0e8311dc2f275724aaad17fac880094cb6052b72966483911df6bb0d20366`, boot `06a049d0290ec2804a8b9957bc1b52092a8bd6ae23473e384d639a8094743f51`, final raw `01b4a0c7d5d69b7e22ca015c3b9993c15c53a73d227517a0fd1649c04fb7906c`. Fresh final contains all seven gap cursors through `PRERAND0`; `RAND0010` is absent. The boundary is after `arm_vm_prot_finalize()` and before return from the first `read_random()` call.

R122 added cursors inside `read_random()` and completed with kernel `c7b312feece848994716bf1ed14a3069be8b8baf2cb518038536d482734ed719`, boot `e4dc7483984eaae3623fb2e9575274fe46a8d9a0f67e16d267fd169ecbd88819`, final raw `8373c53baa32a3b361fbdb6f8776f2ed9eea37100efdd64e27d4076eb640bb4f`. Fresh final contains `RNDENTR0` but not `RNDLOCK0`, `RNDGEN00`, or `RNDRETN0`; the boundary is at or inside `lck_mtx_lock(prng.lock.mutex)`. Both runs returned to fastboot without persistent writes.

## 2026-11-23: R123/R124/R126 lock boundary

R123 final `a75e99749a265c299d455ba45c06ef349f0ddf06dcc016e9e37a43c6943c9613` contains `RNDENTR0` only. R124 final `0b618577727a0de265f31e2a1351f39e0f7b3e53da215349326496b3d43ea4f2` contains `RNDENTR0` and `RNDBEFL0`, but not `RNDLOCK0`. R126 final uses kernel `f5c78154a9e6e4ea5fd55f670a25373bb8ddaa247ff469d2a5def07a0624f806` and contains `RNDLKEN0`, but not `RNDLOCK0` or `RNDLCNT0`. The measured boundary is inside `lck_mtx_lock()` after function entry and before its post-call return cursor. All runs were RAM-only, returned fastboot, and preserved zero preclear/baseline external windows. R127 is building offline to split the internal lock path.

## 2026-11-23: R130 PRNG callsite adjudication

R130 maximum-memory paired run is valid and returned fastboot. Kernel `05875efe3e55b137338adc7f352b345d41cc445058a2427139ae09172a46ee87`; boot `9c02fe618a1c7e08be295df9556e5673ea78e8a79edfea81f09a38bc8b06fc7d`; final raw `8a93155eb9ed7281fce222862c701a166af94cb2fc0a865767f563bb816189e5`. Preclear/baseline external windows are zero; final completion count is 15 and postcopy checksum is nonzero. Final retains the prior lock-path markers but lacks `PRNCALL0`, `PRNGEN00`, and `PRNGENRT`. Boundary: after the observed lock path and before the R130 callsite marker. `verify_y35a_prng.py` still fails its separate older `_y35a_prng_*` linked-symbol contract; do not use that failure as a runtime marker conclusion. Next: isolated post-lock/callsite bracket with new slots and new package/probes.

## 2026-11-23: R131 post-lock bracket adjudication

R131 is a valid maximum-memory paired run. Final raw `4adaa5e00b85c83d57293b3f5307811a2c269a094ca9136473316785a9fb7cf7` has fresh count 15, nonzero postcopy checksum, and `RNDACQ00`; it lacks `RNDLOOP0`, `PRNARM00`, `PRNCALL0`, `PRNGEN00`, and `PRNGENRT`. The boundary is after the lock implementation acquisition return witness and before the first caller-side marker/write after `lck_mtx_lock()` returns. Next: direct scalar witness after the lock call, dynamically read by extra-PA.

## 2026-11-23: R132 direct witness adjudication

R132 final raw `4fa483ff31aaac199110e9d6b09597d3045094a25114df26433e48c85ab19707` is fresh and complete with 16 records. The direct scalar after `lck_mtx_lock()` is zero; external final still reaches `RNDACQ00` but no caller-side marker. Boundary remains after lock acquisition return witness and before caller-side first write. Next: direct scalar inside `lck_mtx_lock()` after `RNDACQ00` and before `return`.

## 2026-11-23: R134b PRNG bootstrap boundary

R134b establishes that the refreshed Y35A provider is registered before idle_thread_create/read_random consumers. Fresh final reports bootstrap entered/returned, registration-started, initialized, phase 3, and nonzero mutex pointer. It reaches PRNCALL0/PRNGEN00/PRNGENRT/RNDGEN00/RNDRETN0 but not RAND0010 after the first caller-side read_random. Current boundary is after read_random internal return and before the caller marker. R130/R131/R132 zero-lock interpretations are superseded because their effective source never called register_and_init_prng; R133 generic CAS marker is not PRNG-specific. Next: preclear and read `vm_kernel_addrperm` through a symbol-derived physical window.

## 2026-11-23: R134b/R135 correction

R134b/R135 prove the refreshed PRNG provider initialized and the first `read_random()` output was stored. R135 final `2b16acbb57d606db7777f05bbe99780569f64f48face343d4538d2afea657016` reads `_vm_kernel_addrperm=0xfc4a85a6fa47ab11` at dynamic PA `0xa0731840`, against zeroed preclear/baseline. The apparent missing `RAND0010` was a decoder error: source comment/codeword mismatch; actual bytes `010DNAR0` through `050DNAR0` are present. BSD callsite/body entry are present as actual bytes `BDBCALL0`, `DBSENTR0`, and `BDSTEN0\0`; `BSDUTEN0` actual bytes `BTDBSUT0` are absent. Current boundary is inside `bsd_init()` before `bsd_utaskbootstrap()`, with no specific failing callee identified.

## 2026-11-23: R136 BSD-init stage-ladder adjudication

R136 final raw `995e9891f4157cc75cbea2af0f81fd074ddeda4e71c30d75c6c43f7270b61f4d` is fresh and complete with 21 records. The source- and link-verified ladder reaches `BSDTHR00` through `BUFRET00`; `IOKRET00` and all later bsd_init cursors are absent. Current boundary: after `bsd_bufferinit()` return, before a recorded `IOKitInitializeTime()` return. With no pre-call IOKit marker, the exact position relative to that call remains unknown. Memory gate v2 uses the exact three recorded ranges and explicitly retains the missing raw `/proc/iomem` limitation. Next: bracket IOKitInitializeTime callsite/entry/return or first internal boundary with fresh slots.

## 2026-11-23: R137 IOKit cursor offline candidate

R137 has a fresh offline kernel/package/probe set bound to kernel `a24a176d09571016bfa608c681c4a0058fa3a319a54a55ecd1c124c0a3afac77`. Package-06 boot is `593d64cae53fc82034cc7c9b5ac9586ef9e47ca33595e367b9c314193fcbeabb`; regular-03 and clear-06 manifests are `7f9540d6772da3948cab00c0d09c8f76d2ba72f3c1bbc55d49a0229bf98e03f9` and `c039afaad4a2896d0b1ad4560f79afe5f7c366928e28e03fefc241937f76179f`. The 1024-byte carrier is derived from the package args physical address plus `0xb00`; both probes use minimal-boundary staging with 4096-byte reports.

The source contract inventories 132 writers and the six IOKit cursors are linked exact-once. The wider linked inventory finds 113 of 132 because 19 inherited/conditional writers are absent from the ARM64 link; this is recorded as a limitation. No R137 raw exists. Next work is an immutable plan/preflight and one RAM-only paired MVE only after all hashes are fixed; no device lock is held.

## 2026-11-23: R137 paired runtime result

R137 is no longer an offline-only candidate. The unique paired RAM-only run completed with package-06, regular-03 and clear-07, returned `efff9d92` to fastboot, and used no persistent writes. Final raw SHA is `b9eb1a520f9e7edf4fae79a4f5e7af7711efd1a03fd83bfa3e71f255ac0023d8`; preclear and baseline raw SHA are `c19dd0fd38a388193898b285822dfc3e4ec505276493d56d150cf836661ceeff` and `7f817e4046399f6dd7debab1bd900250e01dd1e7f9a41ce020e4368520d5e935`; candidate raw is `7a7a3d47c60edd07330b3b15b7808827d993bde8f51056aacbbd790b666427f3`.

R137 final confirms `IOKCALL0`, `IOKENTR0`, and `IOKWAIT0`, then stops before `IOKRETN0`. The measured runtime boundary is inside the IORTC wait path. It does not prove whether a matching IORTC service was found or the 30-second wait timed out, and it does not prove calendar or outer IOKit return. Next R138 should add a result-specific wait-return cursor and preserve the same maximum-memory, paired freshness and RAM-only discipline.

## 2026-11-23: R138c corrected IOKit result candidate

R138b static review caught a real codeword/alias mismatch before device use: the branch literals were `KIOKFND0` and `KIOKTMO0`, not the documented result markers. R138c corrects them to `IOKFND00` and `IOKTMO00` and links the exact conditional call plus six surrounding IOKit markers. Kernel `067f570085cec9c8857078f681514fda5941ed5da5f9f42b8e63f737a387c383`; package boot `9df283abda151278574e3a6c79a2e7d9df18e116e92d0d08abe664f8f372d17c`; regular/clear probe images `d703af803bf73ba82a282a053f05c1d171b8c3e8407f17ee9c8c033d6bf2805d` / `2f9a4817a2191909407c151efc8d1a364782f1bc6afabf0560a0da49a5b711b1`. All offline geometry, transport, phase and R138c linked gates are green. Next is exactly one fresh paired RAM-only run; the only dynamic discriminator is `IOKFND00` versus `IOKTMO00`, with calendar and outer return still separately observed.

## 2026-11-23: R138c paired result

R138c fresh paired raw confirms the corrected kernel entered `IOKitInitializeTime()` and reached the IORTC wait callsite. Final external bytes contain `IOKCALL0`, `IOKENTR0`, and `IOKWAIT0`; result-specific `IOKFND00`/`IOKTMO00`, `IOKRETN0`, `IOKCLAR0`, and `IOKRET00` are absent. Preclear and baseline external windows are zero, final copy count is 21, and the final OR checksum is nonzero. Device returned fastboot without persistent writes. The host candidate return included a 20-second polling timeout followed by a later return; this is not a wait-result witness.

The initial runner decoder used the wrong coordinate base and failed on `IOKCALL0`; supplemental adjudication corrected the mapping from source `native_phase_args + offset` to the external window (`offset - 0xb00`) and preserved the raw result. The measured boundary remains inside the IORTC wait path. Next: add aligned entry/pre-sleep/post-sleep cursors in `IOService::waitForMatchingService()` and repeat one fresh paired MVE after offline gates.

## 2026-11-24: R139d waitmatching cursor candidate

R139d is the corrected offline successor to the failed R139 attempts. The linked waitForMatchingService function contains entry `IOKWSEN0`, pre-sleep `IOKWSPR0`, post-sleep `IOKWSRT0`, and loop-exit `IOKWLEX0`; the contract verifies their offsets and order and confirms the post-sleep marker follows both timed and indefinite sleep callsites. The new kernel/package/probe set is bound to kernel `373996f1ef2dc45f596df76e23fb036a364442b1f2023d35d38fd72b55625480`, boot `4f7794d4eb5069c2ea6aef5d27c1f55ad1a581ee1a04eabddcfde1eeb0dbca00`, and dynamic probe geometry for `args_physical=0xa0ba8000`. Offline gates are green; next is one fresh paired RAM-only MVE.

## 2026-11-24: R139d result and AMFI priority switch

R139d confirms a fresh waitForMatchingService entry and pre-sleep marker, but not the sleep return or IORTC result. The raw pair is complete and hash-bound; no downstream milestone changed. The current priority returns to the documented R154/R159 blocker: launchd/dyld is reached, real AMFI policy dispatch returns `ENOPOLICY=103`, and the R159 graft is structurally valid but `runtime_qualified=false`. Continue with real 16G102 security KEXT ABI and formal iOS 12.4 build closure; prohibit allow-all/minimac, fake PPL, placeholder TrustCache and any device candidate until host behavior is real and all gates pass.

## 2026-11-24: R159 real ABI closure audit

The new host audit confirms the R159 legacy graft is not a security-complete implementation. The pinned XNU 4903 tree lacks the newer pmap_cs/AMFI/TrustCache implementation paths; the newer XNU ARM pmap shows real Image4 behavior depends on address validation, page lockdown, TrustCache runtime state, PPL page lifecycle and `amfi->TrustCache.load`. R159's patch is legacy-only and fail-closed for signed Image4, but its non-PPL page/PPL behavior cannot qualify the 16G102 security ABI. Keep it out of device runs. The queue now requires real API behavior and formal iOS 12.4 registration/dataflow before any new AMFI candidate.

## 2026-11-24: R159 original binding replay

The original 16G102 pointer/ownership audit was replayed against the pinned kernelcache and reproduced all eight pmap/PPL bindings and five AMFI import thunks. This confirms the target ABI surface and owners, not runtime reachability. The next host work remains real behavior closure and formal iOS 12.4 AMFI registration/dataflow.

## 2026-11-24: AMFI registration path narrowed

The pinned 4903 source already contains the formal security-extension loader and MAC policy initialization order. The active AMFI task is now a host prelink/KEXT load and registration dataflow gate: prove the three original 16G102 security KEXTs are accepted and their real eight pmap/PPL imports resolve, before changing startup code or running another device image.

## 2026-11-24: R159 current candidate static closure

R159 was rebuilt locally with Xcode 14.3.1 and the exact legacy patch. The current candidate reproduces the prior structural result: 799 bindings, zero missing/collisions/nulls, three component relocation gates green and loader metadata green. This is a valid host artifact, but `runtime_qualified=false`; the active work remains real KEXT registration/dataflow and security semantics, not another device boot.


## 2026-11-24: R159 AMFI registration trace, runtime still unqualified

A parent-Mach-O byte-bound audit now confirms the current graft contains the real AMFI policy construction and call path: policy string `AMFI`, `mpo_policy_syscall` vector field at index 117/offset `0x3a8`, callback target `0xfffffff0081f3ca4`, and a GOT-bound call to XNU `_mac_policy_register`. It also identifies two guards before registration and the caller’s zero/nonzero return split. The callback has request-specific paths for `0x5a` and `0x5b`; this is static code presence, not evidence it ran.

The boot loader’s security-extension load and IOKit personality start are separate stages. The default `loadKextWithIdentifier` invocation excludes matching; the AMFI personality requires `IOResources/IOBSD`. The candidate kmod-start wrapper also dispatches through an unresolved `__common` pointer at `0xfffffff0096f8b08`. Runtime KEXT load, service start, registration success and launchd’s AMFI result remain unproven.

Audit report SHA-256 `2e4a6f752c3b2d246bcfd7b5a8d41eb24dabf6f4f0e92cd78bbf4d4cb6f7fb9f`; JSON SHA-256 `1cdb380a46e5b01ae48bfdf703fe750aaa93ce06cc3d898072a5b7ae3247a09d`. Current graft candidate `f55e7533f70dd1eb8fea172f30bd632a5739b015db04db7791b43402e5d4f643` remains `loadable=false/runtime_qualified=false`; builder provenance is failed at the separate legacy R326 diagnostic check. Keep it off-device. Next host task: resolve the common-slot producer and exact IOBSD service-start order, then formalize the real callback/Image4/PPL behavior gate.


## 2026-11-24: R159 loader order narrowed

The zero-filled AMFI `__common` slot is identical in the original 16G102 KEXT and the current graft, so it is not a graft-only file defect. The source path shows `readStartupExtensions()` adds personalities without matching; `loadSecurityExtensions()` starts security KEXT modules separately; `IOKitBSDInit()` publishes `IOBSD` from `bsd_autoconf()`; resource registration then drives IOKit matching and service `start()`. The IORTC wait in `IOKitInitializeTime()` is later and distinct. Runtime slot population and AMFI service/registration remain unproven. Keep the candidate unqualified and off-device.


## 2026-11-24: R159 AMFI method attribution tightened

Candidate vtable prefix comparison against the linked kernel identifies the traced function as the `AppleMobileFileIntegrity::start(IOService *)` override. This strengthens the static path from the `IOResources/IOBSD` personality to the registration helper, while leaving actual service matching and execution unverified.


## 2026-11-24: R159 common-slot relation corrected

The unresolved kmod common-slot trampoline is separate from the statically attributed AMFI `start(IOService *)` override. It is not by itself a reason to reject the service-start registration path. The next boundary is the `IOBSD` publication triggered by `bsd_autoconf()`, followed by IOKit matching.


## 2026-11-24: R159 common-slot producer remains external

The original/candidate `__common` bytes match. The prelinked XNU load path skips KXLD’s common-symbol resolver, while the current source tree contains only the generic `_realmain` declaration/use and macro definition, not the closed AMFI producer. Keep this as an unresolved runtime input; it is separate from the statically identified AMFI service-start path after IOBSD publication.


## 2026-11-24: R159 planner/emitter provenance separated

Planner and emitter artifacts are now linked by an immutable bridge. The planner remains planning-only (`candidate_emitted=false`); the emit report describes the candidate (`true`). The candidate is still `loadable=false/runtime_qualified=false`; no package or device action.


## 2026-11-24: R159 request 90 coverage

The measured R154 AMFI request is 90/0x5a. The current candidate callback contains a dedicated 0x5a branch with validation and error paths, but no runtime callback or success evidence exists.


## 2026-11-24: R159 request-90 callback preserved

The candidate’s exact callback block is byte-identical to the original 16G102 block after rebasing and contains the measured request 0x5a branch. Runtime policy registration and return success remain unverified.


## 2026-11-24: R159 provenance replay bound

A fresh offline replay reproduces the planner JSON, emit report, and candidate bytes exactly from the bound native kernel/cache and current planner/emitter tools. This closes artifact determinism while leaving the historical emitter invocation string unavailable. It does not qualify runtime loading or security behavior.


## 2026-11-24: R159 TrustCache state is inert

The linked `trust_cache_init()` has zero callers; its readiness byte stays zero, so load and lookup helpers return failure/not-found and the page-list API is dormant. Image4 manifest bytes are not authenticated by the legacy patch. This is a concrete blocker before any security qualification. Keep candidate off-device.


## 2026-11-24: R159 TrustCache initialization blocker

The current linked candidate has an uncalled `trust_cache_init`; its readiness byte remains zero. Legacy load and lookup functions consequently return failure/not-found, and the reserved-page list is not seeded. The Image4 wrapper does not authenticate the manifest. The current patch is not a usable TrustCache/PPL implementation; keep it unqualified and off-device. Next host step must repair initialization/input binding and real security semantics, not treat symbol presence as closure.


## 2026-11-24: R159 TrustCache APIs are inert in the linked candidate

The TrustCache initializer is never called in the effective ARM source or linked text, so its readiness byte remains zero and the load/lookup paths are inert. The Image4 wrapper does not authenticate manifests. Next host task: integrate initialization and final TrustCache memory-map binding with negative tests, then close real Image4/PPL semantics; no candidate boot.


## 2026-11-24 R160 host-only security correction

R160 只完成离线 TrustCache 初始化顺序与外部 Image4 fail-closed 修正。链接 kernel SHA-256 `131ae78f6445d5fd465527b62f9e42c0ca22f9779a1f60e3356b7da87e199755`；focused contract tests 3/3 passed。TrustCache sidecar、ADT range 和 linked call graph 已绑定。签名 Image4/CoreTrust、真实 PPL 页保护、AMFI runtime registration、package/probe 和设备运行仍未验证。保持 `runtime_qualified=false`，不打包、不上机。


## 2026-11-24 R160 Image4 provider boundary

R160 的 legacy raw wrapper 具备静态 zero-manifest 路径，但 kernel 只有 `_img4_interface_register` 存储入口，未发现直接调用者，也没有 `coretrust_interface_register` 或 `image4_dlxk_link` 链接符号。签名 Image4/CoreTrust provider 仍是未闭合的安全边界；不打包、不上机。


## 2026-11-24 R161 security closure expansion

AppleImage4 provider 已被纳入九根 structural graft，原始依赖闭包无 missing/collision，并生成离线 candidate。仍未完成指令重定位、KEXT/provider 启动、CoreTrust/PPL、AMFI runtime 或设备资格；保持 off-device。


## 2026-11-24 R161 static gate status

R161 candidate structural and PC-relative gates are green. Remaining active gate is native 4903 loader/KEXT start and Image4/CoreTrust interface registration; no package or device run.


## 2026-11-24 R161 loader and provider static gates

R161 AppleImage4 candidate has green PC-relative preservation and loader metadata rebasing gates. AppleImage4 provider registration call and `_img4_interface_register` binding are statically present. Native loader KEXT start, runtime interface population, CoreTrust/PPL semantics and AMFI runtime remain unverified; candidate stays off-device.


## 2026-11-24 R163 Phase-A queue

R163 Phase-A bounded AMFI PID1/request-0x5a paired MVE is offline-ready. Exact hashes and preclear geometry are in `reboot-checkpoints/R163-phase-a-amfi-witness-20261124-01/R163-RUN-PLAN.json`; `device_run_allowed=false`. The only next device question is whether fresh AMFI entry/return witnesses appear and whether R154 ENOPOLICY=103 advances.

## 2026-11-24 R165 current queue

R165 ran once with a new physical ARMRET diagnostic and returned the device to verified unlocked fastboot without persistent writes. Final raw SHA-256 is `1d299c0b73c7d482599fb5ed2bc94f652df2b074f51298dcd329bf9630c5dff6`.

Fresh final evidence contains `COMMON00`, `MAPDONE0`, `TTBRDONE`, and `PREMMU00`; `ARMRET00`, `SCTLRRD0`, arm_init markers, and AMFI markers are absent. The measured boundary is after `PREMMU00` and before the SCTLR readback witness. Keep `device_run_allowed=false`; do not repeat R165. Next queue item is an offline SCTLR-window ownership and linked-PC audit covering `MSR SCTLR_EL1`, `ISB`, `MRS SCTLR_EL1`, `SCTLRRD0`, and cache maintenance.

## 2026-11-25 R168 current queue

R168 completed the RAM-only four-stage sequence and returned to verified unlocked fastboot. Its runner misread 16-byte records, but raw decoding proves `SCTPRE00` at `0xa0bb0a10` and `SCTPOST0` at `0xa0bb0a20`, crossing the SCTLR write/ISB/MRS sequence. The original SCTLRRD physical windows were not in the probe manifest, so their absence is not evidence.

Keep `device_run_allowed=false`. Do not repeat R168. Next queue item is a new matched probe pair binding `0xa0bb09c0/16` and `0xa0bb09c8/16`, with first-eight-byte record decoding and a corrected runner.

## 2026-11-25 R170 current queue

R170 final proved `R68E7RD0` and a nonzero SCTLR value through the new physical `0xa0bb09c0/32` record. Preclear, baseline, and candidate were zero. Later early markers through `PTSHIFT0` are present; arm_init and AMFI remain unobserved. The runner's 16-byte decode failure does not invalidate the raw evidence.

Keep `device_run_allowed=false` and do not repeat R170. Next queue item is a matched post-SCTLR/page-table invalidation marker window with corrected first-eight-byte record decoding.

## 2026-11-25 R171 current queue

R171 final post-map record `0xa0bb0980/64` contains all seven linked mapping markers: `HDRLOAD0`, `HDRADJ00`, `L1ALLOC0`, `VPPRE000`, `VPCALL00`, `KVPRE000`, `KVCALL00`; controls are zero. The boundary is after post-map and before/within the HID private sysreg sequence. Keep `device_run_allowed=false`; next queue item is an offline HID bracket.


## 2026-11-26 R205c queue

R205c is the corrected offline candidate for the first boot-args byte. `ARG1RD00` is bound to `args_physical + 0xb00 + 0x290 = 0xa0bb0d90`, with a 16-byte record; the clear probe also clears `precpudata-external` at `0xa0bb0b00/1024`. Combined offline gate `4f28c836dad993032c88bbad267d2579d40c6fe96de954f0edcb2f131390618e` and one-run MVE plan `45a8be2e83bbd521f573e9b2b1191817e59350a4475e6d08e28afd4ae663b43e` are green for their versioned minimal contract.

R205b remains a retained invalid measurement because its probe used the wrong physical address and candidate/final readback was absent after USB `e00002ed`. No R205c device run has occurred. Keep `device_run_allowed=false`; do not reuse R205b inputs or raw. Runtime qualification and all later launchd/SpringBoard/driver claims remain unverified.


## 2026-11-26 R206 queue

R206 replaces the invalid R205c candidate. Its static root-cause gate `3523303bd179b6a558b7c13f05ebc938f8cbd3c4d8cb15d9cb8e893b6863c40f` confirms the early-read ordering defect; patch `d0cde1f9cd1a0a23b8a684d44950b5c3b112098ccab976f3e6254031eb8dc3e8` is applied only to the new candidate source/build path. Builder PID 33875 is still running in external preparation. No device operation is authorized. After build completion, require linked guard/order verification and fresh package/probe gates.


## 2026-11-26 R206 queue

R206 is offline-ready after correcting the R205 early-read ordering defect. Combined gate `7cf42f734771f94d531bb68ca685e11d3e44f31ca4c2378fd97c113985c2d99a` is green; package image `a18a64dc0ee87ece42ef60973b098636d818d69ef754623e209bd2c42cfc5f29`; regular/clear probes are fresh and bound to the new kernel. The package uses a derived QCDT reference only, with that limitation recorded. No device run has occurred; keep `device_run_allowed=false` until live G0 preflight, then run one 600-second RAM-only MVE.


## 2026-11-26 R206 paired failure and offline comparison

R206 is no longer an unrun candidate. Its single RAM-only MVE accepted the candidate boot, then lost fastboot enumeration; preclear/baseline raw are valid, candidate/final raw are absent, and the device returned to unlocked fastboot without persistent writes. Do not rerun R206.

R204b fresh `PEBARGRT` proves the external marker carrier path. R206 linked guard/order and slot ownership are valid; repeated disconnect remains unlocalized. Next queue item is offline package/entry/early-control-flow comparison, with `device_run_allowed=false`.


## 2026-11-26 R208 current target supersedes R207 queue

The active target is the R208 TF/SD offline path with GitHub Actions as the only UniXNU build route. R207 v2 PID 90604 was terminated and produced no provenance or kernel artifact. R208 has passed the SD protocol host suite, sdhc2 ADT contract and lk2nd SD_BOOT patch apply-check. Private manifest commit `bc1dacf822dd1a2d013716dca50cbf07a09ab7c8` binds the exact XNU ref and six arm-driver patches. Plan-only run `45812745086` passed. Native runs `45838744656` and `45838740886` on commit `4c817f03fbd5a0611fadfd2675381c32ae995363` passed exact XNU header generation but failed the NativeSdcard object step, so source compilation and artifact production remain unverified. XNU link, package/probe, TF GPT/APFS image, root mount, eMMC fallback and device evidence remain pending. No local UniXNU compilation is allowed on any disk. Keep `device_run_allowed=false`.


## 2026-11-26 机械盘本地编译已关闭

用户要求取消所有本机磁盘上的 UniXNU 编译。R207 v2 builder PID 90604 已终止，未生成 provenance 或 kernel artifact。后续编译、NativeSdcard object、XNU link、package/probe 和静态门禁全部走 GitHub Actions；机械盘只保存缓存、run roots、CI 下载产物、备份和 raw。`device_run_allowed=false`。


## 2026-11-26 R208 latest CI closure
R208 latest CI run `45852497429` on commit `3538cccc70e4b3490f7b65e9042713e6266b8c4e` is green through root-selection contracts, NativeSdcard object compile, IOStorageFamily-191 combine and deterministic archive. Object `47bec72ade1ff792938b9ae468f778a7d7e4c13bb62f97d18e5dbf96242e900e`; combined `0353a170088989517d6634805f16537e26844fa89bd2acf9040dffd3cfa400fd`; archive `f401224182f56a5d27532482c1978528ae1570c3d5b16931b98384a6aaba1e73`. Kernel link, package/probe, TF GPT/APFS/root/fallback and device evidence remain pending.


## 2026-11-27 R208 offline CI state
R208 validation `45855811648` and Docs `45855811845` pass on commit `ba4854d4cb076388f61cb2bcdbdf9a7e8874ec5d7`. Offline source, host, root-selection, NativeSdcard, IOStorage archive and documentation gates are green. Kernel link inputs, package/probe, TF GPT/APFS/root/fallback and device evidence remain pending; device_run_allowed=false.
