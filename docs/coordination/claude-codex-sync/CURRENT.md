## 2026-11-26 R205b paired MVE adjudication

R205b preclear and baseline completed with fresh zero target windows and `PSTCOPY0 count=12`. Candidate boot was accepted, then fastboot returned `e00002ed / Write to device failed`; the device did not return to verified fastboot within the 600-second run window. No candidate or final raw exists. This does not adjudicate `ARG1RD00` execution or a kernel fault. Adjudication: `/Volumes/Mobile/unixnu-research/reboot-checkpoints/R205b-pe-bootargs-first-read-paired-run-20261126-01/R205b-adjudication.md`. Keep `device_run_allowed=false`; next is offline comparison with R204b package/shim and failure timing.


## 工作区路径切换（2026-11-26）
当前唯一活动工作根：`/Volumes/Mobile/unixnu-research/UniXNU-y35a`。
当前账本：`/Volumes/Mobile/unixnu-research/UniXNU-y35a/docs/coordination/claude-codex-sync/LOG.md`。
当前参考根：`/Volumes/Mobile/unixnu-research/UniXNU-y35a/upstream-refresh/2026-11-11/sources/`。
当前设备锁：`/Volumes/Mobile/unixnu-research/UniXNU-y35a/.device.lock`。
当前备份根：`/Volumes/Mobile/unixnu-research/device-backups/efff9d92-20261119/`。
Xcode 仅由 GitHub Actions runner 用于 UniXNU 构建。`/Volumes/Mobile` 只保存源码缓存、CI 输入快照、CI 下载产物、备份和 raw；`/Volumes/Portable` 仅作临时 staging。本机任何磁盘均不运行 UniXNU 编译或链接。
历史条目中的旧路径保持原样，作为当时证据位置，不代表当前活动路径。

## 2026-11-26 R208 CI-only and temporary staging handoff

R208 validation `45855811648` (`host-validation`) and Docs `45855811845` (`build`) passed on commit `ba4854d4cb076388f61cb2bcdbdf13efb8404dc5`. NativeSdcard, IOStorageFamily archive, root-selection and documentation gates are green. Kernel link, package/probe, TF GPT/APFS image, root mount, eMMC fallback and device evidence remain pending.

The local process check found no UniXNU build, link or large-build process. `/Volumes/Mobile` returned `Input/output error` during a shallow read, so no further scan or write was attempted. `/Volumes/Portable` is permitted as temporary staging only; it is not the canonical tree and must not be used for local UniXNU compilation. `device_run_allowed=false`; persistent writes remain none.
Staging is `/Volumes/Portable/UniXNU-staging-20261127-0042`, exported from private-mirror commit `68b2cf91038fedb1ccacdc5950223ef618d8215e`; manifest SHA-256 `a4d970a878c88c8e21dbfeeca086f78d2f8fad0b09180584048b4430ee0d8538`; 1424/1424 files verified.

## 2026-11-26 R208 native-input closure and package producer handoff

Main is at `fc6a4727e74e9913d4336deb78bce3557c91c56f`. Validation `45879899093` and Docs `45879899053` passed on main ancestor `0e0a1356ab09ab6dee8fec6f4a9459ad82467d8c`. Native run `45879966044` failed before kernel build during Darwin 18 firehose input preparation; no kernel artifact exists. `fc6a472` push-triggered native workflow `45880957209` was skipped and is not a build result. The native workflow now defines the future `unixnu-kernel-${run_id}` producer contract, but it has not yet emitted an artifact. Package/probe/TF/root/fallback/device gates remain pending.

State documents were superseded by main commit `49ecec4c59964644d4bbbab09db3488e54fa63bf4`: validation `45884101324` and Docs `45884101618` passed, and native plan-only run `45882865622` passed with `execute=false`. No kernel artifact exists yet; package stage must land before the one execute=true native build.

TF validation `45885655057` on `c2d6c980cd6a57d7ab5c9fc8ac85fc97ee5b4d8c` passed the new TF/eMMC fallback contract. The contract is offline-only; implementation status remains `unverified` because the two drivers still register independently without a linked root coordinator.

Stock DTS path is now bound by main `425ec007c2973fc14c81f64f14898138340cca3c`; TF validation `45887232679` passed manifest, SD, ADT, root-selection, fallback, XNU headers and NativeSdcard artifact checks.

## 2026-11-26 R208 remote validation after staging sync

Private mirror commit `9a98ce2480220da4e663688dd730beb62b004bb7` is on remote main. UniXNU validation run `45862410871` (`host-validation`) and Docs run `45862410942` (`build`) both completed successfully. This verifies the documented offline gates and staging policy only; kernel link, package/probe, TF image, root mount, eMMC fallback and device evidence remain pending.
## 2026-11-25 R204b adjudication

R204b used the required maximum contiguous memory profile (`owned_memory=0x5fe00000`, `memory_profile=max-contiguous-measured`) and completed one four-stage RAM-only paired MVE. The device returned to verified `efff9d92 / lk2nd-msm8916` unlocked fastboot with `persistent_writes=false`. Fresh final contains `PEBARGRT` immediately after `args = PE_boot_args()` inside `PE_parse_boot_argn_internal`, but not `ARMDFPAR` after the caller returns. The strongest boundary is after `PE_boot_args()` returns and before the first command-line dereference / parser return, at or before `if (*args == '\0')`.

Kernel `783f7be6690e1c1460c8eb1aee13aaf2197ba8fe6708fe59b22422a57e3f654b`; boot `bda96bc257931eab6e943fc5030b41839cc3d546331e2dc8956d2d97c72b09e3`; regular probe `3bea26fd9f21e15432a3ddf9be99f833a45939b8a9a459133815236fd1bc14a0`; clear probe `802065069e4ee41175d1a3dab33b1c6eb6b2bfee58c2284deb7ffc03efa7fea5`.

Raw SHA: preclear `e83d9152c8e204cfe86d35b0f7bae45ccdaf6bfd268c1305b60daa4fcd07d501`; baseline `714c473398183ed137673bf7977da33984b533ac9c615b0c945584cce69b7176`; candidate `3d8849185e30a5f98cfcf15575700a1e8b9029d1b53d5626054135a61e954bb8`; final `4b392fc2e19367b51781373de48c7de3b9e112fabf765509c56c9a9a6d019041`. Corrected adjudication JSON `8f3d0d168f78d01feda7870badac0b5af3e179b80133bc982aed6f5724e997c0`; Markdown `18e00f612c8c0498e7283f95d036f4df04b663b689bf731210de25835549b60b`.

The first R204 build failed because the marker declaration was missing; R204b corrected it and passed. The R204b runner records semantic fastboot failures separately from subprocess exit codes. Keep `device_run_allowed=false`; next is offline analysis or a marker immediately after the first `*args` read. AMFI, launchd, SpringBoard, storage, touch, and drivers remain unverified.

## 2026-11-25 R203 adjudication

R203 completed one four-stage RAM-only paired MVE and returned to verified `efff9d92 / lk2nd-msm8916` unlocked fastboot with `persistent_writes=false`. Fresh final contains `ARMDFPRE` immediately before `PE_parse_boot_argn("cpus_defeatures")`, but not `ARMDFPAR` immediately after the call and not `ARMDFRET` after the block. The strongest boundary is after `ARMDFPRE` and before `ARMDFPAR`, inside `PE_parse_boot_argn` or before its return.

Kernel `d5ae4a461c83e7be840233edf9a927b65264cd8d74c98dfe8619dc35d305e277`; boot `d5c5fe1fd01721841e1f89bcd8bccbe14357e39a53ed54ba50b9ca61fbedb5ee`; regular probe `dcfe0dc80257ca00bd7b6be51b78c64c83e5df96acde96086b08aeba56eddf20`; clear probe `b59e54d858d2d76ae8a65bbfb87219fa6bc3d00b2020b30853b4a7a5aa0f0d74`.

Raw SHA: preclear `542b00cafe53fec38cc2ce8db1e98d83f7e2e7be4595e9150abc2cfd2e2a0076`; baseline `19046b28809d50527e9f6b4f9865b102b8730ad5b19dc717ab41214a76121f24`; candidate `e1c60154fc70671f7f7b8d9be83afd1aed329988e82dab7a67d7246644371a7e`; final `3e8651a42be3de173d73db63be077fd3d6cd9736aef179b8a33d14605a21885f`. Adjudication JSON `235aaf760c319c399fce9a3963240c3ce5349d9b4e15f795e24d18540b0270e4`; Markdown `cfec295161687870e784f9d4e776e8301e982ba8c8b2d5398a756dc774a1b2ae`.

Keep `device_run_allowed=false`; do not repeat R203. Next is offline `PEBARGRT` immediately after `args = PE_boot_args()` inside the parser. AMFI, launchd, SpringBoard, storage, touch, and drivers remain unverified.

## 2026-11-25 R202 adjudication

R202 completed one four-stage RAM-only paired MVE and returned to verified `efff9d92 / lk2nd-msm8916` unlocked fastboot with `persistent_writes=false`. Fresh final contains `ARMDFPRE` immediately before `PE_parse_boot_argn("cpus_defeatures")`, but not `ARMDFRET` after the block. It retains `ARMPGSZ0`, `ARMRADR0`, `ARMPGBEG`, and `ARMRDENT`. The strongest boundary is after `ARMDFPRE` and before `ARMDFRET`, inside the parse call or before its return.

Kernel `02bad7d7a5c5992d729db1425e3c20dbebf3d37f7e3a8ab54631f1dc7fb31be6`; boot `d20767ad7c717f5998bf32683eb31ace555994ff084dd282ad8b9d5e834b9bfe`; regular probe `7d4669c8faf8b4efce9cc5f31366b681e591f63b617dbeace4936f44e2beed63`; clear probe `e9c6d7f5352241f58d8888d5f96ddaf0a33fc5ca5a8af5fd3bb37055a652affc`.

Raw SHA: preclear `0a78d0917b08f8ce76cc28b943c54ec65ddfc1ae97cffd16fb9eefd9d0a22401`; baseline `49301ea87628c80598d889cc6b8b8757a9c1c04f2184bb0032f9139af4b23a47`; candidate `7eb0161b79cbc26416cf00221061304d082b999bd48306078851d6ddec70081e`; final `a1bf2b47dc99e8f71743840a9d63c55c3362c6e3444b54546fd0478c9ebd93af`. Corrected adjudication JSON `33f5f7beea6d6e18142fc1e5cd9c36430b24740eea5146063a71f119b993151f`; Markdown `c9e399c52e57178bbef775751604e429ccc2f84dce0d6464eee2fafa8e743d39`.

Keep `device_run_allowed=false`; do not repeat R202. Next is offline `ARMDFPAR` immediately after the parse call. AMFI, launchd, SpringBoard, storage, touch, and drivers remain unverified.

## 2026-11-25 R201 adjudication

R201 completed one four-stage RAM-only paired MVE and returned to verified `efff9d92 / lk2nd-msm8916` unlocked fastboot with `persistent_writes=false`. Fresh final retains `ARMPGSZ0`, `ARMRADR0`, `ARMPGBEG`, and `ARMRDENT`; the new `ARMDFRET` marker at carrier offset `0x250` is absent, and `ARMPAGE0` at `0x200` is absent. The strongest boundary is after `ARMPGSZ0` and before `ARMDFRET`, inside or before completion of the `cpus_defeatures` handling bracket.

Kernel `e9244ea2a58c72e7f27f92a78d133e9941cf4d47f233fdd58bb5901041a8f581`; boot `86d2986df2c95790488c4f2af0c568255cc86a5bd825d182138a7ac7a8ec9a95`; regular probe `bac0fc422db9853a3ff30c10e0bd8a05ec13d4abaf244d6a109efcdc6e8c4680`; clear probe `92dd2b92f6b37e28a20bdf60b3ec7477a695d59ba7891e030dbcb6812d90f5ff`.

Raw SHA: preclear `4f4da838e2ae06131356530306a8d56b294adc4f45b62069c9bb343a840e3520`; baseline `8da8f79d99c463b89f7afe4fa4d2d527c7cbbd2569bc77b9718a68d473a561cb`; candidate `2d54b5dc7638e7865fa2f0604f03989099b212d49c429e25149b170cc29c4374`; final `893932a5f95cdf217854e08e594ae056027d87af7b29c0a98bf0bbe3355f02cd`. Adjudication JSON `849f7d77fba46e4e5c0128800d18ece0d5512f876173583d082a73dbdea6f712`; Markdown `6865f2bdad347624f9805ca292d66aa937faf44364ea9cbc96c56ef9280300b2`.

Keep `device_run_allowed=false`; do not repeat R201. Next is offline split of cpus_defeatures parse versus return. AMFI, launchd, SpringBoard, storage, touch, and drivers remain unverified.

## 2026-11-25 R200 PE_boot_args direct-path adjudication

R200 completed one four-stage RAM-only paired MVE and returned to verified `efff9d92 / lk2nd-msm8916` unlocked fastboot with `persistent_writes=false`. Fresh final carrier contains `ARMPGSZ0`, `ARMRADR0`, `ARMPGBEG`, and `ARMRDENT`; `ARMPAGE0`, `ARMBTSTR`, `ARMARGOK`, and `ARMVMPRE` are absent. The strongest boundary is after `ARMPGSZ0` and before `ARMPAGE0`, after the `PE_parse_boot_argn("radar_20804515")` page-size selection block. Do not attribute later failures beyond this boundary.

Kernel `2d65a16c63576cb8b6340d2e0727b9da5857c65e6c14449ced129083b4d7c9c9`; boot `2e945d394542523b24977237ff105585bf6471acfce71e209986fa57bfec7d70`; regular probe `7c1a06deb070b15abb7f77b03dce13ab1ead8d17a928b6dca0eb044f20744523`; clear probe `36f489faee5af24b821d99aeca791d4a6e42a2803c397c87d3da74f1ad1756cc`.

Raw SHA: preclear `b03ee53dac55243a4790bed023d0006ca6f5bf125782e06b9a28f2b8b59cd106`; baseline `5e8c895ff3fdf44f2937c5ec4303e688264ed302e92d1ba91cf15a3ddd03150e`; candidate `3815f629106adf3224479b76127d9637f007602f6a4e6b1bf4e240fde6a7d704`; final `0b7639493c4d7b3d51c79e476b6cb50be6c37224b9883f99bebbd2cf8542826c`. Corrected adjudication JSON `2bff2cb74b2d8d04dad37eeb8554877bf54d18da2b555e8d6974048fbbdebdae`; Markdown `44fda57a34213f2b2933a7049d9add76e5357d16f4d73d581225dee4a5b3557c`. `ARMPAGE0` is checked at carrier offset `0x200` from source slot `0x40`; the earlier `0x250` decoder check is superseded.

Keep `device_run_allowed=false`; do not repeat R200. Next is one offline marker bracket after `ARMPGSZ0` and before `ARMPAGE0`. AMFI, launchd, SpringBoard, storage, touch, and drivers remain unverified.

## 2026-11-25 R197 adjudication

R197 valid final contains ARMRDENT but not ARMRADR0 or ARMPGSZ0. Boundary is after ARMRDENT and before ARMRADR0. Final raw SHA eaa16a938049b1c8f8e7444ecdb6ceed65cc1b7f4709226f1ab1de4c2b66e2bf. Keep device_run_allowed=false.

## 2026-11-25 R196 adjudication

R196 valid final contains ARMPGBEG but not ARMRADR0 or ARMPGSZ0. Boundary is after ARMPGBEG and before ARMRADR0. Final raw SHA 8f5206cf75c1eb0c8c59f283ec73dba0ce461f930822529ea9cdf83f9751e828. Keep device_run_allowed=false.

## 2026-11-25 R195 adjudication

R195 valid final retains PECFGRET but lacks ARMRADR0, ARMPGSZ0 and ARMPAGE0. Boundary remains after PECFGRET and before ARMRADR0. Final raw SHA cf92157bb7e5a4aff7e995831cec1682263caf8f227f398b1a52a14e8aed5e44. Keep device_run_allowed=false.

## 2026-11-25 R192 adjudication

R192 valid final contains PECFGRET but not ARMBTSTR or ARMARGOK. Boundary is after PECFGRET and before ARMBTSTR. Final raw SHA 24ba9622544db1b54d4b6df03f2fedf7300ec85b8d294fa9ec9afcd7c9796c9a. Keep device_run_allowed=false.

## 2026-11-25 R191 adjudication

R191 final retains PEFCGOK0 but not ARMBTSTR, ARMARGOK, or ARMVMPRE. Valid boundary is after PEFCGOK0 and before ARMBTSTR. Final raw SHA d79962d475790968df2d83a253c2c250d54d58699434f465a4be08963bc33439. Adjudication JSON SHA 80d8b99b4d626e05d6ced538249a56a3b36eaa97fe0e7ba88a5a2fd17e4d992d; Markdown SHA 1869f26266161bce7e4f11d3b4624d39ca1b724956589140570ba42afe857978. Keep device_run_allowed=false.

## 2026-11-25 R191 host/probe ready

R191 adds ARMBTSTR after processor_bootstrap and before ARMARGOK. Build, linked, package and matched probe binding gates passed. No R191 device run yet; keep device_run_allowed=false.

## 2026-11-25 R190 adjudication

R190 valid corrected-carrier final contains actual PEFCGOK0, while ARMARGOK and ARMVMPRE are absent. The source label PECFGOK0 is superseded by the linked little-endian codeword PEFCGOK0. Boundary is after PEFCGOK0 and before ARMARGOK. Final raw SHA 9c032f0e43346d4504d9d0be592fa927e0b0cbf8bdafc167dc12ac10ede1825a. Keep device_run_allowed=false.

## 2026-11-25 R189 corrected carrier adjudication

R188 is superseded as invalid carrier mapping. R189 corrected the carrier to package args_physical+0xb00 and produced valid fresh evidence. Final contains POSTPE00 but not ARMARGOK or ARMVMPRE; boundary is after POSTPE00 and before ARMARGOK. Final raw SHA 11de5eb183c3fcea54b7004bab727ffd34e1407020b46b6c3fa79484045a440c. Adjudication JSON SHA 6db090f43af808c363e2e47c28c0855f6d1983ebdbaad008407b43aab5ac206e; Markdown SHA dd29f1a226630f031396cea0953a2efdba807539751f73d8f2f6cf4b092811ca. Keep device_run_allowed=false.

## 2026-11-25 R188 host build and linked gate

R188 build and static verification passed; kernel SHA 803ed85e2b66a8518ca557efa9f167942527adde052c04bddd9686215f1bcf48. Linked ARMARGOK and ARMVMPRE order passed. No R188 probes or device run yet. Keep device_run_allowed=false.

## 2026-11-25 R187 adjudication and R188 queue

R187 fresh final contains POSTPE00 but not ARMVMPRE. The boundary is after POSTPE00 and before ARMVMPRE. R187 adjudication JSON SHA ec9d7b22801894a5a35c463c685a45cb9fc6f48fb405932637e87f64fc4b2ff1; Markdown SHA 4b27a3d9dd0c5392b4b75efc7418bd74e39a3c93d8841f4ee5efa1d1ceabb0f5e. R188 offline design adds ARMARGOK after PAN setup and before ARMVMPRE. No R188 device input exists; keep device_run_allowed=false.

## 2026-11-25 R187 package/probe binding

R187 kernel, package, regular probe, and clear probe are bound. Kernel SHA e31004c18a4fc253d5b623d1d3ab9a3c6fc939c1595c5b4ab63c9734207457ba; boot SHA 942ef333ba63323d9ba8a3fd12a48fd429603daf7faaa2354f89ebd917b8221d. Both manifests use one carrier, and the R187 binding gate passed. No R187 device run has occurred. Keep device_run_allowed=false; next is offline capture/transport validation.

## 2026-11-25 R187 host build and linked gate

R187 host build completed with kernel SHA e31004c18a4fc253d5b623d1d3ab9a3c6fc939c1595c5b4ab63c9734207457ba. The linked gate confirms POSTPE00 immediately after the PEINITRT gap and ARMVMPRE before the arm_vm_init call. No R187 package, probe, or device run exists yet. Keep device_run_allowed=false; next is new regular/clear probe generation.

## 2026-11-25 R186 arm_vm bracket adjudication

R186 host build and linked ARMVMPRE/ARMVMRET gate passed. The unique RAM-only paired run completed all four captures and returned the device to verified unlocked fastboot with persistent_writes=false. Final raw SHA-256 is 6388831b1838eee04f924553c0ff2f8f3b9ba1ef10e0ad63952c382f1d3d57e4. Fresh final contains PEINITRT, POSTHI00, CPUSKIP0, and PEPSKIP0; ARMVMPRE and ARMVMRET are absent. The strongest boundary is after PEINITRT and before ARMVMPRE, within arm_init setup and boot-argument parsing. Do not attribute this to arm_vm_init.

R186 adjudication JSON SHA-256 f3886d33d546df25e9f7d7493ec61ef68383a968818a7a81a3f91338a94c6487; Markdown SHA-256 f3027b099aca5d9a5278c6688adbcf3a7b32c8456016050af857ec03852cacbc. Keep device_run_allowed=false. Next is a new offline marker immediately after PEINITRT; do not repeat R186.

## 2026-11-25 R185b PE_init_platform bypass adjudication

R185b completed one RAM-only paired MVE and last observed the device back in verified unlocked fastboot with persistent_writes=false. Final raw is 872277d70cb8542d2dbee6770b498488a7ae5d8df0b2f7e72567440d46fa0630; preclear/baseline/candidate/final are bound in the adjudication JSON. Fresh final contains ARMINITE, PEINITEN, PEINITRT, HIKSPI00, POSTHI00, PEPSKIP0, and CPUSKIP0. The strongest result is: A53 HID bypass and arm_init entry are confirmed; PE_init_platform was bypassed on the diagnostic path and the continuation after its conditional block executed. PEINITRT is not a real PE_init_platform return witness. ARMVMINI is absent, so arm_vm_init and everything after it remain unverified.

R185b adjudication JSON SHA-256 2eedf56b1bf66e2904fb4b17bdf77bb6480c9fd164cae053aa680d9d1b2098fb; Markdown SHA-256 10e92827a0f7ec142554e7be30c032d7658c4538973d24d99ee46f7a9ec3ebe0. The source label PESKIP00 is corrected to actual codeword PEPSKIP0; raw bytes match the linked immediate. Keep this as a Phase-A diagnostic HACK. device_run_allowed=false; next is a new offline bracket from PEINITRT to ARMVMINI. Do not repeat R185b.

## 2026-11-25 R184 corrected current snapshot

R184 corrected-address final contains early slot5 `ARMINITE` and slot6 `PEINITEN`; slot7 is not PEINITRT. This is the latest reliable result: A53 HACK entered arm_init and PE_init_platform, but did not prove return. Current device_run_allowed=false; next is one PE_init_platform return witness.

## 2026-11-25 R181 correction

R181 final proves CPUENTR0 in the linked `osfmk/arm64/cpu.c`; CPUDRET0 is absent. R179 was a wrong-translation-unit false negative.

## 2026-11-25 R179 current snapshot

R179 final fresh raw `e233afaddac31cb970b62e81a49a947c916dc4a12305b276b3daa4c5864c1778` has HIKSPI00, POSTHI00 and CPUDPRE0; CPUENTR0/CPUDRET0 are absent. The current boundary is after arm_init's call-site pre-marker and before cpu_data_init entry. `device_run_allowed=false`; next is offline linked call/prologue analysis.

## 2026-11-25 R177 scope correction

R177 final contains `HIKSPI00`, `POSTHI00`, and early-record slot12 `ARMRET00`. The strongest conclusion is that the assembly path reached the point immediately before returning into `arm_init`; `ARMINIT0` remains zero, so first C execution is not proven.

## 2026-11-25 R177 current snapshot

R177 completed four RAM-only stages and returned to verified fastboot without persistent writes. Final raw `2cafa203158d9d0f5771e4c08c73ce0b143979a2ef9ddb22c8b0d7edae1182be` has actual eight-byte `HIKSPI00` and `POSTHI00`; `ARMINIT0` is zero. Boundary is after post-HID continuation and before arm_init entry. Current device_run_allowed=false; next queue item is offline assembly-to-arm_init transfer analysis.

## 2026-11-25 R174 current snapshot

R174 completed the four RAM-only stages and returned to verified fastboot without persistent writes. Final raw `309e793cbf71993c66d8e375f86f7542c06d2856825b10be92b77afd64b7145e` has `HIDPRE00` and actual eight-byte `HID4PCOR`; `HID4READ0`/`HID4READ`, HID4RET0 and later markers are zero. The current boundary is after `ARM64_IS_PCORE` and before HID4 read completion. The nine-byte source labels are corrected in the adjudication as eight-byte carrier values.

## 2026-11-25 R174 current snapshot

R174 host gate is green with kernel `87286c16d10072f38d4b40f66430ee2cd945126a92dd9fa2274f4a6a358b0304`, package `f64fdfa5de51bbd127d596e9f99036175cc30be37ef5edbd882b9b986b223d48`, gate `3dcd3ebe5cd871671cfa9fc5824648322477a0c2dfa25bd7a9fdbe548390c3f9` and run plan `ea1369f908640dc542f67061305298c29b3452ac39015a85fda7d1b53792a4f9`. Its two new micro markers are 16-byte aligned and bound to the dynamic args address; no R174 device run has occurred. R173b remains the latest device boundary: HIDPRE00 present, HID4RET0 absent. Current device_run_allowed=false.

## 2026-11-25 R173b current snapshot

R173b completed four RAM-only stages and returned to verified fastboot without persistent writes. Final raw `ab64f6f4d0a59fc498b1f4f149d1e990123576484c4f2eaa2124a3d4a8e6ec44` is fresh with 18 records; `HIDPRE00` is present at `0xa0bb0a30/16`, while HID4RET0, HID0RET0, HID1RET0, HID3RET0, HID5RET0 and HIDPOST0 are zero. The current measured boundary is before HID4RET0, inside or immediately after the HID4 sub-sequence. `device_run_allowed=false`; next queue item is an offline HID4 micro-bracket.

## 2026-11-25 R172 current snapshot

R172-02 completed the four RAM-only stages and returned the device to verified unlocked fastboot without persistent writes. Final raw `84f47b8df83d769147e66cc1e2fc64bc71242bbc1b9f4d024fa84d892fe35ef0` has fresh `HIDPRE00` at `0xa0baca30/16`; `HIDPOST0` at `0xa0baca80/16` is zero. Preclear and baseline are zero for HID and external windows. The boundary is after entry to the HID bracket and before the post-HID witness; no individual private register or trap cause is proven.

R172 offline gate v2 is green with kernel `22c2fa08c911afc9f5ed57c6f272f1a19b0b4b75bac5b6a5f2465c1d173db6f8`, package `0a73156cd977d0120ada8a2a379ab745f1455b3775967a3350604f8447c76a03`, regular probe `ba8f83f317a1a5da854f4d7b01536bbc5d6b72f3a03f0b03159b2447b7163cd1`, clear probe `11f20c868639d193dbe32f715a71dcbfc59f1cc6fcd4889ebe67f5cd29c1bac5` and gate `f67d1cbfb5163b9bcecc00483ad8421302ea1f14e67a4108db8e702d3bbbc676`. R172-01 runner failure and R172-02 adjudication are retained under `reboot-checkpoints/R172-hid-bracket-paired-run-20261125-01/` and `...-02/`. `device_run_allowed=false`; next queue item is an offline per-access HID bracket.


## R160-R175 graft execution isolation, November 16, 2026

R160 re-ran the known-good R154 kernel on serial `efff9d92` with the same readback probe. It freshly reproduced `R90VMIL0` and `R90LRET0`, and the R154 AMFI witness again decoded to `ENOPOLICY=103`. R160 final raw SHA-256 is `62dc2df28646a740afef5437abb3203d6cd83ac01c77bd248cbcfcf3c8900712`; kernel `4e7903810d5f70d6ab2907754a9619650113fc803c777c0a37a2bd4ff70fea2f`; boot `d9d4c4f43986717e80332056da82086f5dede9c36f83b6314a0780a67be41891`; probe `ea257e369e3cd682d41557905d41d6bacd48cfdfce911f899881f2a76b37f63f`. This validates the current readback chain.

An R160 padded-size control filled the R154 Android kernel domain from 12,046,264 to 33,469,648 bytes, matching the R157/R159 entry size, while keeping the R154 XNU unchanged. It still reached the R154 runtime markers. Therefore kernel-domain size alone is not the stop cause.

R161 restored `rd=md0` in the R159 graft boot-args. R162 additionally skipped copies of the five added prelink/PLK segments. R163 used the R159 graft with the R154 low physical layout. R164 added a D-cache clean-to-PoC loop before `IC IALLU`. R166c used the R159 graft with the R154 low carrier, DT, TrustCache and RAMDisk addresses and the correct R154 second source address, with a matching R154 probe. None produced a fresh current-generation XNU marker. These runs are retained under `/private/tmp`; none flashed persistent storage.

The earlier interpretation of missing `R84FS00` as proof of failure before `start_first_cpu` was too strong: `R84FS00` is written at boot-args plus `0xa00`, which is record slot64, outside the original 384-byte early record (slots0..47). A matched extra-PA probe now reads slot64/65. The R154 control final contains the expected early markers through `R84CON00`, while R159 matched probes leave both slot64/65 and slots0..47 empty.

R169 is a matched probe for the R157 plain kernel (`42f3d9c59e6a6e6fb3879e6e5e3097c1bee5722b97dfc155d53518f4f0b0efed`) and still has no fresh slot64/65 or early markers after restoring `rd=md0`. R174 is the same plain kernel with R154 boot-args and also has no fresh markers.

R170/R171/R173/R175/R176/R172 were RAM-only diagnostic controls. They changed only temporary `/private/tmp` kernel/entry bytes to test target entry execution, shim D-cache, physical entry contents, or stamp-page witnesses. None produced the temporary marker. They do not prove the copied entry bytes are absent because the retained-memory probe can be cleared or can read a different reset-generation buffer; keep their results as negative controls, not as a new root-cause claim.

Current engineering conclusion: the R154-to-R157/R159 transition has a real, already-corrected boot-args regression (`rd=md0`) and R157/R158 had definite prelink metadata/KASLR binding errors. R159 still has no runtime-qualified AMFI graft. The remaining stop is in the grafted kernel/runtime contract or an unobserved entry/translation condition; it is not justified to keep changing the shim without a stronger entry-owned witness. The latest productive gate is a host-side runtime qualification of the R159 graft, especially the legacy prelink relocation and AMFI/pmap closure, before any further userspace or display work.
# R156 current host state, November 16, 2026

R154's TrustCache input is present and correctly bound: `boot-r154-native/manifest.json` records physical `0xa3518000`, size `3852`, SHA-256 `099a621d60e0333eef68d11c2820f99aea0e0e3674d1873d7a52193877a44ba0`; `trustcache.bin` is v1 with UUID `9bd72ab3446a43b89459d362d5d0622f` and 174 entries. The remaining AMFI blocker is kernel-side consumption and policy registration.

A temporary R156 prototype under `/private/tmp/xnu4903-r156-amfi-legacy` is not a deliverable: its source SHA is `3075a3d9db6aed3ebfb65d5bcb1a8bca0ae66969b3d52fb4835c096ea6d557c4`, but it lacks static v1 DT loading and was not compiled into a kernel. Full make stopped in the old MIG tool path; targeted compilation stopped in reconstructed header context. No image or device run is authorized.

The local `xnu-0b4b910d` feed contains a newer `kern_trustcache.c` DT loader, but it depends on `TrustCache/API.h`, AMFI runtime objects, and PPL/TXM interfaces absent from XNU 4903. It is a reference for range/offset validation only until a 4903-compatible implementation is independently closed.

The R157 standalone harness now validates the exact raw v1 payload: version 1, 174 entries, 3852 bytes, sorted hashes, and dyld/launchd hits. Harness source SHA-256 is `834f809151c01bfb38d734f6ca7df733c7c20ab347830c94bd633b4a68052417`; binary SHA-256 is `f3cb2cdbec2eeffb0e13f9fdff4fa0c3c3b8c75534fec9ba8922fec5384a298e`. An isolated R157 source patch exists at `/private/tmp/r157-amfi-static.patch` with SHA-256 `ad46e62edc1e97bbd0ef78eb15d194de3c298159a51fdda423dd7a77afe604a6`; it has not produced a linked kernel.

# Current State

## R155 host-only AMFI graft planning, November 15, 2026

R154 remains the latest device evidence: `__mac_syscall("AMFI", 90)` found no policy/callback and returned `ENOPOLICY` 103. No device retry was made. A new read-only planner, `kits/XnuPrelink/legacy_graft_plan.py`, evaluates a relocation-aware graft of the original 16G102 security closure onto the R153 T7000 RELEASE kernel. With slide `0x2000000`, the minimal three-component closure (`AppleMobileFileIntegrity`, `CoreTrust`, `corecrypto`) has zero address collisions, 261 component bindings, and 530 resolvable kernel bindings. The deterministic v6 plan records all 791 binding sites, selected KEXT security/dependency metadata, and 10,273 internal PC-relative encodings; register dataflow is not qualified. Plan SHA-256 is `9fa3851c8524979b16f2a461d16df04f35b073480fcec0a3937de34b29f6875a`. The planner emits no candidate and marks the result loadable=false.

The only remaining bindings are the eight pmap/PPL APIs already listed in the R155 design record. The exact 4903 ARM tree has no implementations for them, so no constant-return stubs or device boot are allowed. The host gate is now a matching TrustCache/pmap implementation or source-equivalent API closure, followed by a real graft emitter and package/readback gates. Full APFS/Data and display remain later blockers.

XNU 4903 already has an early security-extension loader: `KLDBootstrap` installs `bootstrapLoadSecurityExtensions`; `mac_policy_initmach()` invokes it before setting `mac_late`; the loader starts Apple prelinked KEXTs marked `AppleSecurityExtension=true`. The 16G102 AMFI metadata has that property and declares CoreTrust/corecrypto. This removes the need for a new early-init hook, but it does not close the eight missing kernel exports or prove AMFI's runtime registration.

## R155 QcomSdcc host object milestone, November 15, 2026

The read-only QcomSdcc transport remains write-refusing and is covered by the existing ASan/UBSan host suites. The 4903 driver-object wrapper now accepts `QcomSdcc` as an isolated component, pins public Apple `IOStorageFamily-191` source metadata, and compiles the driver with an independent `IOBlockStorageDevice.cpp` base object. Run `/private/tmp/r155-qcom-sdcc-object-v10/manifest.json` is `object-compiled`; driver object SHA-256 `367e9140797d51da4847a598cfe6d3756c4f9b04f7da9890e69009af4d57f4b9`, base object SHA-256 `48b4bed130a3a450b88055d37895361ead8ee5312384f769b93a5dd60dc266af`, combined relocatable object SHA-256 `e7c1a57d813d2c511a9ba0f08db41f06757ac6e4af1623ace66e44cc22f9b32a`, and KernelConfigTables personality object SHA-256 `c60ab29a160bb12425e8b9adcd097db4f5f52339899039e2cd66e51367a92b05`.

The combined object has 202 undefined external symbol names and all 202 are present by name in the R154 kernel symbol inventory; this is object-level name resolution only. No IOStorageFamily KEXT link, kernel link, prelink, package, device boot, or storage write was performed. The official source snapshot is `upstream-refresh/2026-11-15/sources/IOStorageFamily-191`, commit `c95d31401f0ff950a883727f5e47d313685fde33`, archive SHA-256 `2a8a4e216a4de2944e2e33aa07846cd152f821d7731bbfe7ddd47f7a94491bd3`, and `IOBlockStorageDevice.h` SHA-256 `fe5807fdf2dc752d6c7bd0c6a6c4525bab5e0e99b4302ece767d3b0bc59d6e66`. Its bundle version is 2.1, matching the 16G102 IOStorageFamily metadata; byte-identical target build inputs remain unproven.

## Authoritative R154 live update, November 15, 2026

R154-v3 performed one paired RAM-only sequence on `efff9d92` / `lk2nd-msm8916` / unlocked=yes. The device returned to fastboot after both probes; no persistent write occurred. Kernel `4e7903810d5f70d6ab2907754a9619650113fc803c777c0a37a2bd4ff70fea2f`, boot `d9d4c4f43986717e80332056da82086f5dede9c36f83b6314a0780a67be41891`, probe `ea257e369e3cd682d41557905d41d6bacd48cfdfce911f899881f2a76b37f63f`, baseline raw `63edf05a4069ebdcabec73e6926b62afa609d7eaf5f081c4e926a6a0d90d6b18`, final raw `3f594eabd8428ab609614eea631fd4462c15142d0bbe035d82a5f81f366d4e23`.

R154 final slot21/22 are fresh and decode to policy name `AMFI` not found, callback not found, errno `103` (`ENOPOLICY`). The observation is made at the XNU `__mac_syscall` dispatcher for policy call 90 and preserves the original return value. This directly confirms the current missing-policy hypothesis. The final dyld panic remains the expected user-initproc response; its subcode 9 is the default DYLD exit reason, not errno 9.

R154 phase artifacts and corrected decode: `evidence/y35a-20261102/boot3-20261106/phase-r154-v3-amfi-syscall-errno-20261115/`. The next gate is a genuine AMFI/CoreTrust load route with real bindings and intact signature enforcement; no further device retry is justified before that host gate.

## Historical live update, November 15, 2026: R152 reached initproc before R154 errno instrumentation

R152 is the paired predecessor to R154 on Y35A serial `efff9d92` / `lk2nd-msm8916`, unlocked=yes. Kernel SHA-256 is `8507594105a6bc4ee4d85fdbf6aa9d17666ad45b4cf7feb10aef5ad3fd529322`, boot image SHA-256 is `96ea5dbaf1fdabeee01fb64f498be3205a3b114d7c6d165768fa99524500e1c3`, and readback probe SHA-256 is `53d7ae168e7096eb3767aafd9a1376fe1124b34e9831d6a62b02300272557497`. Baseline/final raw SHA-256 values are `9c26e127a374f89e3a082df035e443759c5509be993b3f368a717ecea9fa8c87` and `ce69b32ce0454d5f2edf6b291ed1ea6680bd27a60387fa666b8ed2e649ea801c`. The device returned to fastboot. No persistent partition writes occurred; full-readback overwrote the declared PRAM staging area.

Fresh slot17 `R152REG0` proves `registerService()` returned, not that a matching service was published. Fresh slot18 `R152GPLO` shows `IOSecureBSDRoot()` used the non-null global platform fallback after its matching-service wait returned null. Slot19 `R152SOTH` means `SecureRootName` returned a status other than success or not-privileged; it does not encode an exact IOReturn. Slot22 `R150MROK` is identical in baseline and final, so it is not a fresh R152 store. Fresh slot23 `R150RVOK` is written only after `VFS_ROOT()` returns successfully. That downstream control-flow witness, together with later `R90VMIL0`, supports that the earlier `vfs_mountroot()` returned success; the mountroot result itself was not freshly encoded in this pair.

The corrected offline decoder at `evidence/y35a-20261102/boot3-20261106/phase-r152-secure-root-global-fallback-20261115/device-result-r152-decoded.json` labels the final slot19 value as `superseded_by_r152` for the inherited R151 owner. It leaves the original device result and raw captures unchanged.

The fresh `_smsg_bufc` panic says `initproc exited -- exit reason namespace 6 subcode 0x9 description: amfi_check_dyld_policy_self() failed`, caller `0xfffffff0075c7180`. The dedicated panic-log copy matches baseline after its stamp and is stale. R152 reached the PID1/initproc failure path, but no launchd main loop, Apple logo, SpringBoard, or visible iOS UI is evidenced.

The preserved `_smsg_bufc` backtrace was independently symbolicated against the exact R152 Mach-O. Its kernel chain is `user_take_ast` → `ast_taken_user` → `bsd_ast` → `postsig_locked` → `exit_with_reason` → `proc_prepareexit` → `launchd_crashed_panic` → `panic_with_options` → synchronous debugger trap. The matching XNU source in `bsd/kern/kern_sig.c:3182-3237` shows the default signal disposition transfers the thread exit reason to `exit_with_reason`; `kern_exit.c:900-919` commits the reason and prepares process exit. Thus this is a user-initproc termination carrying DYLD namespace 6, code 0x9, followed by the kernel initproc panic handler; it is not a captured AMFI kernel fault PC. The raw does not preserve the signal number, failed image/CDHash, AMFI policy-list state, or `__mac_syscall` return value.

R152 boots with `rd=md0` and ADT `osenvironment=ramdisk`. Its 42,991,616-byte HFS+ root is a custom mix of 9 Mach-Os from the IPSW `OS` component and 49 files from RestoreRamDisk, not the full installed `OS` APFS volume. The 16G102 IPSW has an `OS` component and no separate SystemOS/Cryptex component. Its 3,852-byte TrustCache is the native v1, 174-entry RestoreTrustCache from the local 16G102 IPSW; the sidecar’s inner-payload SHA-1 matches. The older 176-entry memory claim is unsupported, and the panic string alone does not prove a trust-cache miss. A separate host candidate at `out/y35a/ios12-root/.trustcache` is 3,875 bytes and begins with a 23-byte IM4P `trst` envelope; its remaining 3,852 bytes are byte-identical to the R152 sidecar (SHA-256 `099a621d60e0333eef68d11c2820f99aea0e0e3674d1873d7a52193877a44ba0`). That host file was not the byte source sent in R152 and must not be substituted without stripping and re-auditing the wrapper. A separate 1,737-entry static cache exists in the IPSW but is not in R152 boot3. Direct CDHash checks show R152’s 174-entry Restore cache covers 56/58 Mach-Os in the mixed root, including `dyld` and `launchd`, but misses `bin/df` and `bin/ps`; the static cache covers those two. Their legitimate cache-union coverage is 58/58. This is a later trust-coverage gap, not evidence explaining the present dyld policy-check exit.

The leading source-level cause is the absent iOS 12 AMFI policy extension: R152’s prelink text/info segments are empty and no `Driver-*` booter extension is supplied. The matching 16G102 kernelcache contains AMFI, CoreTrust, and corecrypto, but the legacy emitter rejects R152’s segment geometry. Even the minimal three-KEXT AMFI closure needs eight kernel exports absent from R152. The `Driver-*` fallback cannot directly accept these already-prelinked cache fragments, and its early entitlement path is not viable as-is. Keep AMFI enforcement intact. Next, close a host-only security-extension route and prepare the installed `OS` APFS root plus writable Data volume before another device run. Full record: `evidence/y35a-20261102/boot3-20261106/phase-r152-secure-root-global-fallback-20261115/record-r152-v1.md`.

## Historical checkpoint, November 15, 2026: R151 fails secure-root service lookup

R151 superseded the R150b measurement and is itself superseded by R152 above. R151 used a fresh native Xcode 14.3.1 build of XNU 4903.270.47 with ordered R137b/R138–R151 patches. Kernel SHA-256 is `3205ec91f46c66e516ecdc7fb3ec032891bc58106bf0b8754b7e09f8ea73ec3f`, RAM-only boot image SHA-256 `ee068eba5f0d2c1cea6df6c03bfd8e493b64c54f8c17d5199225779c7e803c0e`, and matching full-readback probe SHA-256 `203a08811b5be251bf5c8ed46670e1f7dbfd9805ec5c4fda1bf677075beee497`. Native, linked, low-vector, PRNG, package/readback transport, linked-start audit, and 75 selected regressions passed.

One paired sequence ran on `efff9d92` / `lk2nd-msm8916`, unlocked=yes, with no persistent writes; the device returned to fastboot. Baseline/final raw SHA-256 values are `e217e0e8a7491a0e56752d5acc8d6ef4259142da070c859d6f929bc017befc23` and `613fe4d96db3a7f2daf3365b0e6c6ead54dc461c89a5034097464902eaa0da13`. Fresh `R150MROK` and `R90MNTOK` confirm `vfs_mountroot()` returned zero. Fresh `R151NUL0` confirms the subsequent `waitForMatchingService("IOPlatformExpert")` returned null; `_smsg_bufc` then records `IOKitBSDInit.cpp:758 Assertion failed: pe`. `VFS_ROOT` still has no fresh success marker. `R151REG0` was not retained because slot19 is reused by later secure-root cursors, so it does not prove `registerService()` published the service.

R151 stopped before `VFS_ROOT` and launchd. R152 implemented its planned wait-preserving global-platform fallback and result-class witness; see the R151 record at `evidence/y35a-20261102/boot3-20261106/phase-r151-secure-root-registration-20261115/record-r151-v1.md`.

## Historical live update, November 15, 2026: R150b returns from root mount, then fails secure-root platform lookup

R150b was the preceding measurement and is superseded by R151 above. R150b used a fresh native Xcode 14.3.1 build of XNU 4903.270.47 with the ordered R137b/R138–R150 patch chain and provider-scoped fallback. Kernel SHA-256 is `6356056dfdfbc313da0c6b10258741fe17ec093e68d962d9d84cb3123085343f`, RAM-only boot image SHA-256 `9bf0594f9e3a89eb40a2547e9ba4e0ff195d373c7cc909af927637852cd7cb17`, and matching full-readback probe SHA-256 `bd368abee5e7e55b3ac52d7673fd33d79f7eb4ce8d27d83a69314765589067bc`. Native build, linked phase, low-vector, PRNG, package-byte, capture/readback transport, probe-manifest, and 69 selected regression tests passed.

One paired baseline-probe / `fastboot boot` / final-probe sequence ran on `efff9d92`, product `lk2nd-msm8916`, unlocked. Baseline/final raw SHA-256 values are `df09b8fd5ae88f88ccaa974766d31f8b9fa7cb145defaad6fbd72d2ac221bd0d` and `2cbec28dcf89d332b75f674834fe32a3fa0acbc9fb3b2deaa9c2505691d1fdc4`; CNTVCT differs. No persistent partition or userdata writes occurred. Full-readback intentionally overwrote the declared PRAM stage, and the device returned to fastboot.

Fresh slots show `R150PSOK` after generic `IOPlatformExpert::start(provider)` returned, `R150MPNO` for the target provider's mapper-required decision, and `R150MROK` after `vfs_mountroot()` returned zero; slot45 `R90MNTOK` corroborates the mountroot success. Slot23 stayed at its baseline `R87FREE0`, so `VFS_ROOT` success and root-vnode setup remain unproven. The unknown-mapper cursor `R150UKRT` is immediately before `IOMapperIOVMAlloc()` returns zero; it does not prove the caller received that return or that it caused the mount progress.

The final `_smsg_bufc` contains a fresh panic at `IOKitBSDInit.cpp:745`: `Assertion failed: pe`, caller PC `0xfffffff007131dac`. `bsd_init` calls `IOSecureBSDRoot()` after the successful mountroot return and before its `VFS_ROOT` call. In that function, `pe` is the result of waiting for a matching `IOPlatformExpert` service and is null at the assertion. The base start had already set the global platform pointer; R151 will publish the fallback service after successful start and retain cursors around the subsequent secure-root match. No root vnode, `bsd_init` completion, `bsdinit_task`, launchd, Apple logo, display, or iOS UI is evidenced. Full report: `evidence/y35a-20261102/boot3-20261106/phase-r150b-platform-fallback-root-20261115/record-r150b-v1.md`.

## Historical live update, November 15, 2026: R149 reaches HFS mount and captures a platform panic

R149 is superseded by the R150b result above; the older R100/R113 summaries remain historical. R149 used a fresh native Xcode 14.3.1 build from XNU 4903.270.47 with the recorded R137b source diff and ordered R138–R149 patches. Kernel SHA-256 is `6c1531e03092e640ddca1c144aae560944c1b7117f08dae9507ad3f76dcf387a`, RAM-only boot image SHA-256 `dc57fc83b5fc182e7a1243125fd3679f68874d67e9795e21a73568e51ea460e1`, and matching full-readback probe SHA-256 `7b8803f1945f40436f1b0ab74f79252b1a625d3213fbdf76b677c79dadf0294c`. Native build, static Mach-O, low-vector, PRNG, package byte binding, capture layout, readback transport, and selected R140–R149 regression gates passed.

One paired baseline-probe / `fastboot boot` / final-probe sequence ran on `efff9d92`, product `lk2nd-msm8916`, unlocked. Baseline/final raw SHA-256 values are `cf4f9c02f8079301d504c1addd7bf389edb1561669c737ec564e8460c7e14340` and `c7be9b75a6a72228661d40f866011c746bde0d9ce9d46034951d7e1ff194e404`. The probe CNTVCT field differs between captures, and the final shim stamp binds R149. Only RAM boot was used; no persistent partition or userdata writes occurred. The device returned to fastboot.

Fresh named-record slots show `fpxlog_init` (`slot41/R90FPX00`), return from `vnode_pager_bootstrap` (`slot45/R142VRET`), the later BSD cursor (`slot42/R90VPG00`), and the `vfs_mountroot()` callsite (`slot44/R90MNTC0`). HFS-specific fresh writes also appear: `slot35/R131IO06` after `DKIOCGETBLOCKCOUNT`, `slot32/R131SCAN` at HFS bitmap-scan setup, and `slot33/R131GNR0` after an HFS cnode path returned a vnode. These show substantial HFS mount-path execution, but not a successful root `VFS_MOUNT`, a mounted root vnode, `launchd`, Apple logo, display, or iOS UI. Slot47 is the non-marker word `0xa351fff8`, not an IOMapper-start witness.

The R149 `_smsg_bufc` final record contains a current-generation panic: `Unable to find driver for this platform: "vivo,pd1502a."` Its caller PC `0xfffffff0076dfee4` is the return address after the linked `panic` call inside `IOPanicPlatform::start` (`0xfffffff0076dfea4`); source `iokit/Kernel/IOPlatformExpert.cpp:1937–1949` confirms this fallback deliberately panics when no legitimate platform driver matches. The separate raw panic-log copy at offset `0x10000` is stale R135D text and does not negate the fresh msgbuf panic. The platform-match panic and BSD/HFS cursors can be concurrent; the raw does not order them or prove that `vfs_mountroot()` returned.

R149 tested a per-call `kUnknown` fallback in `IOMapperIOVMAlloc()` that leaves global mapper state unchanged and returns the unsupported/zero result for the early mbuf pool allocation. The fallback marker was overwritten in slot44 by `R90MNTC0`; the platform-expert decision in slot42 was overwritten by `R90VPG00`. Therefore this run does not prove the fallback caused the advancement. The fresh platform panic is a stronger active failure candidate. Full record: `evidence/y35a-20261102/boot3-20261106/phase-r149-iomapper-unknown-fallback-20261115/record-r149-v1.md`.

Next: R150 should make the Y35A `IOPanicPlatform::start` fallback call generic `IOPlatformExpert::start(provider)` instead of panicking, guarded to this diagnostic configuration while leaving other configurations unchanged. Add retained markers for the fallback and the `vfs_mountroot()` / HFS mount return path, after slot ownership review. Keep the unknown-mapper fallback but record it in a dedicated slot. Then run one hash-bound paired RAM-only sequence; stop on any image, identity, raw, or transport mismatch.

## Live update, November 13, 2026: R100 v8 bracketed return cursors

R100 v8 is bound to kernel 3b096524f1a821ed2222ea0543d3f01a64416c9773865db9039387c3a69a993f, boot c71434d09c402ba86027c122ef440652700f0f3bdaa808784ea3f3f8a13cb5fd, and readback probe e242b322757f40f285d3d6483717e439a89282b898155f1e3106da834527fda1. Sixteen offline gates passed (summary 680aa531f07b670a3153ed208a6c3c1d3074c463bd9ef95b711c98296889319e); a separate H-series freshness gate also passed.

One paired RAM-only sequence ran on efff9d92 / lk2nd-msm8916 / unlocked=yes. Baseline/final raw hashes are 5c886f1f9d170a9e7975927599f0e76ac0a5908b3cef308a68d070cfaa9b02b9 and 9a6f2db498da70145e98baa0f089c60d1b8e9962941ab83f78989e742a54e99b; CNTVCT changed from 0xe80efe8cf to 0x21553a4c. The XNU boot command was accepted, but the first poll was already fastboot; no persistent writes occurred.

By manifest-derived offsets, slot39/raw 0x10238 is fresh R9HCAL00 and slot40/raw 0x10240 is fresh R9HERTN0. The latter is after the slot50 helper call inside _thread_block_reason, before the function RET at 0xfffffff00714c184. The new wrapper, caller, and mutex-return markers were not retained; slots41 and 48–51 stayed at old values or zero. This does not uniquely identify a false target predicate, a helper that did not return, a lost store, or an overwrite. No root mount, launchd, Apple logo, or iOS UI has been observed.

Full record: evidence/y35a-20261102/boot3-20261106/phase-r99-thread-block-return-20261113/record-r100-v8.md. Next, bracket the high-slot helper calls with a low slot40 marker immediately before and after each call; audit and version ownership before using any other named carrier slot. Keep the wait event and timeout unchanged.
## Live update, November 13, 2026: R100 v6 reached wait-result load before unresolved high-slot writes

R100 v6 uses a fresh Xcode-linked kernel (`aac83acf484c90c534b9bd89538ef66bfef4c0d9e63e71cabcad43f2b4a1fd97`), boot image (`da08dbb0710c27332b66964c23c4a23c594a3f5645dd61d5d5b135ef4128d8fd`), and matching readback probe (`3ef931e53bd279fbbf932298f0c9a320ace54d89dbdbaa313adac9d86c1774e4`). All 17 offline gates passed; the summary SHA-256 is `a5a5438e2f57b4c70741b097b1d354c5e994cdaae69e7140a1ec3254d833d8b5`.

One paired baseline-probe / `fastboot boot` / final-probe sequence ran on `efff9d92` (`lk2nd-msm8916`, unlocked=yes). It used RAM boot only, with no persistent writes. Baseline/final raw SHA-256 values are `a65ac59ae0c625ee68b1494ea340919fb80d4539459afcf444ad11767bbd37c3` and `9573365cea6f4600861fd2c90d8220c15e26bd10bec47eca60cdf44cbcf41052`; CNTVCT differs (`0xf7617160e` and `0x213e2eb5`). XNU returned to fastboot on the first poll.

Using the readback manifest's named records, slot39/raw `0x10238` changed from `R9ECAL00` to fresh `R9FCAL00` before `thread_block`; slot40/raw `0x10240` changed from `R9EVAL00` to fresh `R9FVAL00` after `wait_result` was loaded inside `_thread_block_reason`. The linked v6 binary places `R9FCAN00` slot51 at `0xfffffff00714c06c`, `R9FEXT00` slot50 at `0xfffffff00714c084`, and the function return at `0xfffffff00714c0ac`. The final named extension slots48–51 at raw `0x10570`, `0x10578`, `0x10580`, and `0x10588` remained zero, as did the later wrapper/caller return witnesses. This does not establish whether a high-slot helper call was skipped, faulted, stalled, returned without retaining its value, or was overwritten.

The next diagnostic should bracket the high-slot calls with sequential, generation-unique values in the already validated slot40, overwriting that same slot after slot51 and again after slot50. Slots42–47 remain owned by earlier R88/R90 markers and must not be repurposed. No root mount, `launchd`, Apple logo, or iOS UI has been observed. Full record: `evidence/y35a-20261102/boot3-20261106/phase-r99-thread-block-return-20261113/record-r100-v6.md`.

## Live update, November 13, 2026: R99 v7 RAM boot boundary

R99 v7 used the R99 v6 linked kernel (SHA-256 `d1819981c4d70c777e0d51962e06ccfa62f446200bf5fae513c6600ffc7a1378`) in a newly generated package and matching readback probe. The v6-named package/readback artifacts were bound to the older parent kernel, so they were not used; v7 output identities were independently regenerated and all 17 package, transport, layout, static, marker-freshness, source/decode, and inherited linked-binary gates passed. Boot SHA-256 is `749c19487157dda6f7ee4c68d8c0ed6f5974ab30e88b9cdde207111759f5a2b8`; probe SHA-256 is `8d77836224c03717f8e7a0a215fb185a605ab2fcc76576d79327fdd73fc524e5`.

One paired baseline-probe / `fastboot boot` / final-probe sequence completed on serial `efff9d92`, product `lk2nd-msm8916`, unlocked=yes; there were no persistent writes. Baseline/final raw SHA-256 values are `af33dd609e41894bd97b3ff719401ae468ab5b51b9a5acc83f0fd3b221553eee` and `e38ee697caa523760d8a900049a1b9fc925daa943bfea257e11c045223cb4910`; CNTVCT changed from `0xd94420286` to `0x2186e119`. XNU returned to fastboot on the first poll.

Named readback mappings show fresh slot39/raw `0x10238` `R9BCAL00` immediately before the `thread_block` call and fresh slot40/raw `0x10240` `R9BVAL00` after `thread_block_reason` loaded `wait_result` at linked PC `0xfffffff00714bedc` and before its return PC `0xfffffff00714bf1c`. The strongest supported boundary is therefore the post-scheduler, post-result-load point inside `thread_block_reason`. Slot41/raw `0x10248` remained old `R90FPX00`, so `R9BRTN00` after the `thread_block` call was not retained; this does not prove the call failed to return. Slot38/raw `0x10230` remained old `R90PNAM0`, so the wait result was not classified in retained evidence. Missing markers do not identify a fault or timeout. No root mount, `launchd`, display, Apple logo, or iOS UI was observed.

Full experiment and hashes are in `evidence/y35a-20261102/boot3-20261106/phase-r99-thread-block-return-20261113/experiment-r99-v7.json`, `device-sequence-r99-v7.log`, and `gates/offline-gate-summary-r99-v7.json`. The device remains in `lk2nd-msm8916` fastboot.

## Live update, November 13, 2026: R98

R98 v1 completed one paired baseline-probe / XNU RAM-only boot / final-probe sequence on serial `efff9d92`; the only XNU boot operation was `fastboot boot`, with no flash or persistent writes. Kernel SHA-256 is `fc3e0d512494139182bd7f87f3f7d2d07834ea9e5aa0e88c3bbcc15fdc9d58ec`, boot image `3e1d5690b8b6df39dfa0820704ecc6c62e5156af6ce2eb0b7c4eb45b27f26f01`, and probe `226811603d86ecd44fc31b7c5ce1e2040d1c9484bf0fe3f2a7709b4e63b27f52`. Baseline/final raw SHA-256 values are `8b07ac56fa16b72fd8acec66ba9c0045d81261dae2dddbb7478c8fb11ac649b1` and `d3291b7441da3461ac8636c3e21d9aa1d295344345e14d30bd1966e37c9cc485`; CNTVCT differs.

By the readback manifest's named `early-fault-record` mapping, slot37 is raw offset `0x10228`, changing from baseline `R93WPRE0` to fresh `R98TBRT0`. The linked marker at `0xfffffff00714be28` is after `thread_block_reason`'s `thread_invoke` loop and `splx`, but before its C return. This advances beyond R97's pre-`_thread_block` boundary; it does not prove return to `_lck_mtx_sleep_deadline`, wait-result classification, mutex reacquisition, recursive-lock restoration, or return from `IORecursiveLockSleepDeadline`. The timer marker shares slot37 and is overwritten, so its presence cannot be inferred from the final raw. Fastboot returned on the first poll; no root mount, `launchd`, display capture, Apple logo, or iOS UI was observed.

All 12 offline gates passed; summary SHA-256 is `5250dfdc70872dd39b28c21ffb4ab26955ffefcef7cc0a176087935d7637ed51`. The initial decoder's `thread_block_reason-returned` label overstates the marker; the corrected evidence-boundary adjudication is `evidence/y35a-20261102/boot3-20261106/phase-r98-scheduler-wait-20261113/gates/r98-result-adjudication-v1.json`. Full record: `evidence/y35a-20261102/boot3-20261106/phase-r98-scheduler-wait-20261113/record-r98-v1.md`.

## Live update, November 13, 2026: R97

R97 v1 completed one paired baseline-probe / XNU RAM-only boot / final-probe sequence on serial `efff9d92`; no flash or persistent writes occurred. Kernel SHA-256 is `9b5cf894c234948076f6ad606cb962de88646177488519929c55f4c9d1cf1e35`, boot image `263b52af12b75c16a8ba9bc83afd6023d0eca0c60c8167e6823376a2d75b274b`, and probe `5df0da401ee3edf6a2e9f7b58fec61da3fefdcd6c4f49b93ef2b57564cb6a76b`. Baseline/final raw hashes are `ad698e8530bb6390475c2b232d0e3f05888ab451dcbcdb5ca6b9b4791626cc62` and `a6335201cf51ce694ff1d529bfd37a2b9b00b80c242ac9046368ce078c38b927`; CNTVCT differs.

Slot37 at manifest-derived raw offset `0x10228` is fresh `R97BLK00`. The linked path passed `assert_wait_deadline`, took the `THREAD_WAITING` branch, returned from mutex unlock, and reached the marker immediately before `_thread_block`; no post-block result, mutex reacquire, or sleep return marker was retained. Early exception slots0..3 are zero and do not exclude an unrecorded fault. XNU and final probe both returned to fastboot on the first poll; this does not identify the faulting instruction. No root mount, launchd, display, Apple logo, or iOS UI is evidenced.

The native Xcode link, R97 binary/event-guard contract, package byte binding, inherited static, low-vector, PRNG, transport, capture-layout, and source/decoder tests passed. The first R97 incremental link was rejected because its copied OBJROOT pointed at R96 source; the device used only the corrected fresh-OBJROOT image. Full record: `evidence/y35a-20261102/boot3-20261106/phase-r97-lck-sleep-20261113/record-r97-v1.md`.

## Live update, November 13, 2026: R96

R96 v1 completed one baseline-probe / XNU RAM-only boot / final-probe sequence on serial `efff9d92`; no flash or persistent writes occurred. Kernel SHA-256 is `5fd097778076c769887e00d42e4d3a80ce6bd2ca450d45cd10f91b1694a3ba2c`, boot image `6c71af0f6ce4856f4a851a42b1c53892c3a45b723fd26e75a5d432b349abd3a2`, and readback probe `fb6cac0ee793d077a21e640001d9b7ec84cedc595d3f4cd05cde785acd9bae8c`. Baseline/final raw SHA-256 values are `ba64ae64145dfb605dd35d5f7b585738d217a090b070030c9c8226018e99363f` and `a2d25ee2b7fda299189d9af53bd1007ebd69b3f0678d846d000c52a823c0fa1e`; CNTVCT differs.

By the readback manifest's named early-fault-record mapping, slot37 at raw offset `0x10228` is fresh `R96TSLP0`; baseline still held `R95SLEP0`. The linked Mach-O places `R96TSLP0` after the recursive-lock owner assertion and shadow owner/count clear, immediately before the `lck_mtx_sleep_deadline` call. No `R96TRET0`, `R96TRES0`, or wake marker was retained, so the underlying sleep return remains unproven. Early exception slots0..3 are zero and do not exclude an unrecorded fault. Fastboot returned on the first poll; this does not identify a fault PC or timeout result.

R96 native Xcode link, source/decoder tests, event-guarded linked-binary contract, package byte contract, low-vector, inherited R93 static, PRNG, readback/capture transport, capture layout, and manifest postprocess gates pass. The device was rechecked in `lk2nd-msm8916` fastboot with `unlocked=yes`. No root mount, `launchd`, display capture, or iOS UI is evidenced. Full record: `evidence/y35a-20261102/boot3-20261106/phase-r96-iokit-sleep-20261113/record-r96-v1.md`.

## Live update, November 13, 2026: R95

This update supersedes the R94 device-progress note immediately below. R95 v1 completed one paired RAM-only sequence on serial efff9d92; no flash or persistent partition writes occurred, and the device returned to lk2nd fastboot.

R95 kernel SHA-256 is 7fc800f377e39b91eb6def1fca0189a257695e1fb7be0dfef1eece26e4a0e8a8; boot image 11773f89933cbf038339de3a2353c6cc601cc9a32ce7a79821b473e2b1f89b46; readback probe 7fd4724fa79cb32e934484c8b3c5056a6e3875bf9f8190a7907e112f37260fe1. Baseline/final raw hashes are 8148dbfe254b5b06165fcc9416970dc1bf96dd1d72e0397144aea6275b9c702c and c971fb27537661d417ee909649d2312e39e7562cc4a2534aeb3140c7c10e6539; CNTVCT changed from 0x1580796c62 to 0x2153fc48.

The manifest-derived slot37/raw offset 0x10228 is fresh R95SLEP0. The actual Mach-O places the same codeword before the timed IORecursiveLockSleepDeadline call at 0xfffffff007656af0 and before the indefinite IORecursiveLockSleep call at 0xfffffff007656b30; R95WAKE0 is the shared post-sleep marker at 0xfffffff007656b48. The caller sets a 30-second timeout, so the timed branch is expected, but this codeword alone cannot distinguish the two sites or prove the sleep returned. The fastboot return poll was the first poll after R95 XNU boot; this does not identify a fault PC or prove a particular timeout result. Early exception slots0 through 3 are zero, which is not proof that no exception occurred. No root mount, init/launchd, display capture, or iOS UI evidence exists.

The R95 linked-binary wait cursor, static/low-vector/package/readback/transport/capture-layout/PRNG gates, and source/decoder contracts pass. Next, separate IORecursiveLockSleepDeadline entry, sleep return, and lock restoration while keeping the existing timeout and service logic unchanged. See the R95 entry in LOG.md and phase-r95-iokit-wait-20261113 for hashes and reports.

## Prior live update, November 13, 2026: R94

R94 was the preceding measurement on serial efff9d92. It ran one baseline probe, one RAM-only XNU boot, and one final probe; no flash or persistent partition writes occurred. The sequence ended back in lk2nd fastboot.

R94 kernel SHA-256 is 5beec51e365db1298a82af137271b2c6fd653ce420908c7921a9788028d9cb52; boot image SHA-256 is 248ee07a14a70b60903469ead20d136840ab5f56c1cd7363661a05013a2c7c60; readback probe SHA-256 is 0338f16adbeeb954fa1c10111e032b76cac534077a95925307535debb2198866. Baseline and final raw SHA-256 values are 693a18b361929220fdb4bb6685533eaf26a94d91eec5d812401ece2bc606c4af and 24655c38102d35e0154d8cab134cc8f45037716b92566fa7cc9a7e55891e592b. The final capture carries Y35ARD02 and the R94 kernel prefix, and CNTVCT changed from 0x1335fa3395 to 0x2146f3bd.

The readback manifest maps slot37 to raw offset 0x10228. Its final value is fresh R94WMEN0; baseline slot37 contains a different older value. The marker is at linked PC fffffff007656998, at entry to IOService::waitForMatchingService, just before the null-match check at fffffff00765699c. R94MRET0 was not observed, so the function return remains unproven. This does not establish a null match, timeout, or fault. Early-fault slots0 through 3 are zero; gPanicBase and gPanicSize are initialized but are not panic-event evidence. No root mount, init/launchd, display capture, or iOS UI has been observed.

The R94 linked-binary cursor, inherited R93 static verification, PRNG, low-vector, readback/capture transport, capture-layout, package-byte, and source/decoder gates passed. The experiment log contains an inherited xnu-r93-ram-boot label, but its boot path, manifest, kernel hash, and experiment identity bind R94. The next experiment should split the null-match branch, service lookup, notification setup, and timed sleep return while preserving the existing 30-second timeout and notification behavior. Read the R94 entry in LOG.md and the phase-r94-iokit-wait-20261113 evidence directory for full inputs and hashes.

Last reconciled: 2026-11-13; the latest real-device measurement is R9BVAL00, which proves wait_result was loaded after scheduler resumption but before `thread_block_reason` returned. R99 v7 returned to fastboot; no iOS UI is evidenced. The R68E7 material below is retained as historical evidence.

## Active Target

- Device: vivo Y35A / PD1502A, MSM8916, serial `efff9d92`.
- XNU line: iOS 12.4.1 `16G102`, XNU-4903.270.47. The `xnu-4570` tree is a separate iOS 11/Darwin 17 reference line, not the kernel used in these device boots.
- Last locally observed device state: `lk2nd-msm8916` fastboot, serial `efff9d92`, `unlocked=yes`, rechecked on 2026-11-13 after the R97 paired RAM-only sequence.
- Repository branch at reconciliation: `fix/readback-panic-globals`. The worktree contains another session's modified and untracked files. Read current Git status before editing; do not overwrite its work.

## Confirmed Evidence

### R68E7 v5 current boundary, 2026-11-11

The real-device sequence on `efff9d92` was one baseline readback probe, one RAM-only XNU boot, and one matching final probe; no persistent partition or userdata writes occurred. The current device was rechecked in `lk2nd-msm8916` fastboot with `unlocked=yes`.

Exact artifacts: kernel SHA-256 `e22fb0cde89756b0eba152ae6b2a278aabfbe9fb109f507f9f04c0e2962f60a5`; RAM-only boot image `48e2e8953f9145551153b4f18986668f18c6f8db6e15620c1c1fc6a7959f181f`; matching probe `f7b67320ce88092bdd8b3d9f1fde13333c79e7506b641751472adc5bbd622a76`; baseline raw `ebcc24bc51701142ac6234f9b3e68a50157dab2e7e9c17df4d51531d36692fd2`; final raw `0c444f133cbe4c8201c549cd7f56a4aa9cef42299903243e977b849f732501f6`. Build provenance identifies XNU `xnu-4903.270.47`, commit `494ffe1c29d37ca720c37328feb83069c9641b67`, and 25 ordered patches.

The final raw has fresh `COMMON00`, `MAPDONE0`, `TTBRDONE`, `PREMMU00`, and `INVALID0` markers. `INVALID0` is slot 19 at raw offset `0x10198`; it is written after a loop that zeroes bootstrap page-table entries. It is not a TLB-invalidation marker. `TTBRDONE` is slot 15 at `0x10178`; `PREMMU00` is slot 16 at `0x10180`. Both changed from zero baseline to their current-generation values. The exact linked cold-start `common_start` has TCR write at `0xfffffff0072707a0`, `_set_mmu_ttb` call at `0xfffffff0072707ac`, TTBR1 write at `0xfffffff0072707bc`, MAIR write at `0xfffffff007270808`, VBAR write at `0xfffffff007270844`, PREMMU store at `0xfffffff007270864`, SCTLR write at `0xfffffff007270868`, ISB at `0xfffffff00727086c`, MRS SCTLR at `0xfffffff007270870`, and the first post-ISB data store at `0xfffffff007270874`.

There is no `TLBI VMALLE1` or `IC IALLU` in the linked cold-start path before SCTLR. The XNU source has `tlbi vmalle1; ic iallu` under `#ifndef __ARM_IC_NOALIAS_ICACHE__` at `kernel/start.s:1191-1197`, but the T7001 build selects `APPLETYPHOON`, whose `proc_reg.h` defines `__ARM_IC_NOALIAS_ICACHE__=1`; the linked disassembly confirms the block was compiled out. Other flush helpers in the same Mach-O contain `VMALLE1`/`VMALLE1IS`, but are not called by this cold-start path. Treat stale translation state as an unresolved risk, not as an established cause. The full image has an `IC IALLUIS` in a different helper; it is not the guarded cold-start `IC IALLU` instruction.

The low carrier provides same-boot store evidence: x16 `0xa06e60d8`, x17 `0xfffffff007b94800`, x9 `0x11396e60d8`, x22 `0xfffffff007004000`, x23 `0xa0004000`, and slot-10 immediate load-back `0xfffffff007b94800`; slot 11 carries fresh `R68E7RB0`. The separate post-XNU readback probe observes the global pointer as zero. That later observation does not negate the earlier immediate load-back and does not identify when the pointer became zero.

The post-ISB marker at raw `0x10480`, SCTLR value at `0x10488`, and KVA witness at `0x104b8` are zero. Therefore SCTLR.M, successful post-ISB MRS/store, C entry, and userspace remain unproven. The updated verifier replay is `raw-verification-codex-v3-20261111.json`, SHA-256 `b7791d04ea2f42e9b606bc568c6da941c0a46ab735503bf2adb0d589328e85b`; it removes the carrier-slot and cross-time pointer false failures and retains the SCTLR boundary failure. Its four messages are the same two missing facts reported by both raw and freshness gates.

The verifier now treats fresh R68E7 stage slot 11 as ownership of slots 5-10, classifies exact fresh C-phase overwrites per slot, and validates every surviving slot against its manifest-derived expectation, including the immediate read-back unless that exact slot has a fresh later marker. Regression coverage includes a partial ARMINITE overwrite with a corrupted still-live slot-10 read-back. The focused raw-gate, partial-overwrite, and fresh-carrier tests pass. The full host run is 144 tests with 6 failures and 4 errors; its exact output is preserved in `gates/codex-host-tests-20261111.log`, and the failures are being triaged separately.

Copilot's read-only exception audit found the current VBAR vector path depends on the TPIDR_EL1 to CPU-data to vector-table chain before reaching the early fault-record writer. No raw syndrome or SCTLR snapshot is present, so the exception path cannot uniquely distinguish MSR, ISB, MRS, first physical STR, or recursive vector failure. Copilot's next audit is tracing the local lk2nd/boot-shim CPU-state handoff; Codex continues the experiment design after that evidence is reconciled.


- The legacy boot3 artifact is `out/y35a/ios12-boot3/boot3.img`, SHA-256 `d7640a423935b6dbe9322b0b8bbcdac305d25428ff87e0a8ac8bd5439cb74ad6`; kernel SHA-256 `5fd4e6b5f7fa10e1b2cc9323ac5802833c15479fce5c67068f2ba8837fdcdc94`.
- The phase boot3 artifact is `out/y35a/ios12-boot3-phase/boot3.img`, SHA-256 `8694a25fdef575a5b615e8fee6f59bf546495f1f206478c5398af994a7462c4c`; kernel SHA-256 `6e9a09d2453a57532111dbead64ea67018ca31128e3ca7dcaa4e3fbf6f0216c5`.
- Codex ran the phase image on the real device. Fastboot returned `Booting OKAY`; the device returned to fastboot after approximately 13 seconds. A probe rebuilt against the phase kernel was then booted and staged.
- Phase readback: `evidence/y35a-20261102/boot3-20261106/boot4-r3-20261108/phase-readback-phaseprobe.raw`, SHA-256 `1e3c8e0f2bf2c352dd28d53e4b9179aef55533b8e6dee728bcc6f8a5d25624fe`. Its Y35ARD01 and Y35AXNU2 headers contain the phase kernel stamp. The phase-specific early-fault record at physical `0xa0b7c800` is zero.
- The phase result does not establish a failing XNU function. A zero early-fault record means only that this record contains no captured exception state. The three phase markers in `native-phase-markers.patch` are written after `arm_vm_init`, `panic_init`, and `PE_create_console`; none discriminates the earlier pexpert calls.
- A separate 2026-11-06 `panic.raw` contains a real XNU panic report for `pid 1: launchd`. This proves that one older boot reached deep kernel and user-process startup. Do not transfer that result to a different kernel/image generation.
- The r7 witness chain is live: `r7-baseline.raw`, `r7-probe2.raw`, and `r7-post-boot3.raw` differ at the CNTVCT witness field, and the Y35AXNU2 handoff stamp changes from the phase generation to the legacy `5fd4e6b5` generation after the legacy boot. This proves the probe reran and the boot shim's handoff stamp reflects the preceding image generation.
- The r7 witness does not prove that XNU reached `PE_init_panicheader()`. `Y35AXNU2` is written by the boot shim before branching to XNU. Treat the stronger “panic header written” statement in the 06:00 heartbeat as provisional until an XNU-owned field or independent raw header proves it.
- 2026-11-09 08:3x addendum (measured): the three r7 captures differ *only* in the CNTVCT witness (bytes 0x10..0x14) and the handoff stamp (0x10008..0x1000F); every sampled carrier window is byte-identical across baseline, probe2, and post-boot3, and the `_BootArgs` window equals the static Mach-O file bytes for that VA (not an LK-written boot_args struct). Two independent readings follow: (i) the boot3 runs captured no runtime XNU writes into any carrier window — contrast with 2026-11-06 `panic.raw`, which carries panic text at exactly those window offsets; (ii) the panic-header question cannot be adjudicated by any current-probe capture at all, because the probe's stage window aliases the DT pram panic-log window (`make_adt.py:51` reg base 0x859e0000 == `readback_native.py` `STAGE_BASE`) and the probe overwrites pram[0..0xC640) during sampling. Source: `heartbeat-20261109-0830-stage-pram-aliasing.md`.
- Focused offline validation is green: 39 tests passed across readback names, capture format, and native packaging. The full r7 comparison is recorded in `R7-AUDIT-20261109.md`.
- The phase instrumentation audit found that `out/y35a/ios12-boot3-phase/kernel-packed.macho` does not contain the intended phase markers or `_native_early_fault_address`. Its phase-device result is therefore a transport/boot-image result, not a valid XNU startup-boundary measurement. Details are in `PHASE-INSTRUMENTATION-AUDIT-20261109.md`.
- `scripts/y35a/verify_phase_instrumentation.py` now acts as an offline artifact gate. It correctly rejects the existing phase artifact for missing `_native_early_fault_address` and all three marker paths; the existing 39-test suite still passes.
- `scripts/y35a/verify_capture_layout.py` now acts as the panic-capture layout gate. It correctly rejects the current manifest because stage `0x859e0000..0x859f1000` and every record overlap DT pram `0x859e0000..0x859f0000`.
- Corrected T0.2 touch probe is offline-built and verified in `T02-CORRECTED-BUNDLE-20261109.md`: image SHA-256 `7a4b8e43d8b0048e8755f184b77948165457c2517e72a8f55437cf24ad9da90b`, manifest SHA-256 `204f87083b7849a003d7a52f75df3b543c6f057946358ed20fca3ee4a89551a2`, report `0x124` bytes at `0x859f0000`, exact TLMM GPIO12/13/18/19 windows, GPIO13 input/status samples, and QUP5/BLSP1 AHB control windows. All three offline gates pass. Its source changes are present in the current worktree, the image was rebuilt from them in the native container, and the corrected addresses are visible in the final probe ELF disassembly. It remains device-gated by explicit per-experiment authorization; the old T0.2 TLMM/GCC/ATTn fields are superseded, while its SE timeout classification remains.
- Container source audit found an LK-compatible transport fix candidate: snapshot pram to `0x95000000`, write the report at `0x859f0000`, restore pram, then use the existing LK `oem y35a panic` source range. The exact constraints and ownership are recorded in `CAPTURE-TRANSPORT-AUDIT-20261109.md`; this is not yet implemented or device-verified.
- `scripts/y35a/verify_capture_transport.py` passes the two-area candidate against measured LK constraints: pram `0x859e0000..0x859f0000`, snapshot `0x95000000..0x95010000`, report `0x859f0000..0x859f1000`, LK scratch `0x90000000..0xa0000000`, and boot3 RAMDisk `0x90aea000..0x933ea000`.
- Fresh 10:0x verification: commit `93b7978` makes the standalone T0.2 report `0x859f0000..0x859f0bc4`, and its layout and transport gates pass. The full readback manifest still writes records through `0xc640` inside the pram-backed source range, so the T0.2 green result does not close full readback transport. See `R9-READBACK-TRANSPORT-RECONCILIATION-20261109.md`.
- Fresh 10:20 verification at the next repository tip: `772f858` is an evidence-only r8-not-landed heartbeat. Readback regeneration still matches the prior `2aaf092c...` image prefix, `STAGE_BASE` is still `0x859e0000`, and the raw layout gate still reports 13 failures. The independent `verify_readback_transport.py` also rejects the legacy manifest until it declares a transport mode and preservation contract. The touch line remains geometry-green but device-gated.
- Fresh 11:15 verification at HEAD `176999a`: readback remains unchanged across three generations (`2aaf092c...`, `STAGE_BASE=0x859e0000`, layout gate 13 failures, no `transport_mode` field). The T0.2 line is independently reproducible after isolating XNU's `CCC_OVERRIDE_OPTIONS` from its Ubuntu clang subprocess: image SHA-256 `295241cebe164a1f01c370a0484beee6fa60777f150fcd9deed646de11509b98`, `probe.bin` 3864 bytes, layout/transport/mode all green.
- R8/R9 offline contracts are green in the current worktree: the fresh full suite is `92/92`, including the standalone-probe environment-isolation regression, destructive/full and minimal-boundary layout contracts, minimal snapshot/restore tests, optional `.dsym` width handling, explicit absent-symbol publication, width-driven capture decoding, legacy r7 opaque-window handling, and the independent DWARF provenance fixture. The minimal candidate uses the phase-r11 kernel and passes both independent gates when the layout gate is given the report write interval (`0x859f0000..0x859f1000`); the separate transport gate receives the LK source interval (`0x859e0000..0x859f1000`). Readback is committed at `e434dc9` and capture-format decoding at `7566c88`; `macho_field_widths.py` and its tests are currently untracked shared-worktree additions.
- R9 now has an explicit destructive transport contract: `transport_mode=full-readback`, `pram_preserved=false`, `report_bytes=0x1000`, EPH snapshot `0xf800/0x74` with physical write extent `0x80`, stamp snapshot `0xf900/0x40`, and fault-state `0xf000/0x400`. The fresh candidate is `out/y35a/readback-probe-20261109-r9/readback-probe-not-xnu.img`, SHA-256 `4187fedef2f6b874e899e55413aac48ed59a7378b64d9f33020adc19e8274c86`; both independent layout and full-readback mode gates are green with an explicit destructive warning. This is an offline witness image; it has not been booted.
- Phase instrumentation is now green in a newly rebuilt artifact: kernel `out/y35a/ios12-kernel-phase-r11/kernel-packed.macho`, SHA-256 `619a6ea03be230529d4eeeaac64a3fd9d44cef8e1d302255a6bd5f70dd70381a`, passes `verify_phase_instrumentation.py`. Its offline packaged boot image is `out/y35a/ios12-boot3-phase-r11/boot3.img`, SHA-256 `a98c0b26340b503d05414c2cf9586e52725ffa0e99cb420a63619931dad47e99`; manifest status is `offline-built experimental image; not device-boot validated`.
- R9 minimal-boundary is now green with the phase-r11 kernel: `out/y35a/readback-probe-20261109-min-r9/readback-probe-not-xnu.img`, SHA-256 `9466188a5b3f91fedb53525823dea7ced471f5ad1d7e69b1bf4ddbf462d9a405`; current-source manifest `out/y35a/readback-probe-20261109-min-r9-host-e434/readback.json`, SHA-256 `39574d2fdab3b336f859fc2d0e814f9ea6779c294244e26bd07d1876eed44371`. The historical manifest SHA is `0ae59dac07ed1a7accd8f26a47123633084c6c95c30da3cad9cd64a54d1d4fea`; entry/image bytes are identical. It declares `minimal-boundary`, `pram_preserved=true`, snapshot `0x95000000/0x10000`, report records offset `0x100`, 10 records ending at `0x480`; both independent gates are green. It has not been booted.
- The minimal-boundary implementation base is `a58d8f6`; the field-width, guard, `.dsym`, absent-symbol, and capture-format contract changes are committed at `e434dc9` and `7566c88`. The current shared worktree has a fresh full suite of `92/92`, including the untracked independent DWARF parser fixture. The generated minimal candidate uses the phase-r11 kernel and contains the early-fault record plus field-width boundary carriers in a report page; its entry shim snapshots all pram before writes and restores it before reset.
- The phase-r11 experiment's prior “valid zero phase marker” wording is superseded. It read the wrong slot for the C marker and looked at a boot-args padding area that the shim clears. Its raw proves shim handoff and probe transport only; see the correction appended to `phase-r11-minimal-20261109-1604/record.md`.
- Phase-r16 is the first positive XNU runtime result. Its final raw SHA-256 is `c4c723f864c09ed12cb879f01b14fe1836983974e3b311293c999e99fa39157d`; body `0x10100` changed from zero in the baseline raw to `0x5952544e454d5241` (`ARMENTRY`). The matching `Y35AXNU2` prefix identifies r16 kernel SHA `30cecbfca54bc2bb8330c73e8dd190c462f38e4e4a8bc3a58b290885b7eabea8`, and `Y35ARD02` confirms the probe ran. This proves XNU's `start_first_cpu` path executed; body `0x10128` remains zero, so C `arm_init` and later boundaries remain unproven.
- The r16 kernel, boot image, and probe hashes are respectively `30cecbfca54bc2bb8330c73e8dd190c462f38e4e4a8bc3a58b290885b7eabea8`, `44d4042bdebabfa343563191a2411158d0c6e5eed7d2aab19680f28340c8f3a8`, and `3e8283927c10f2c6a2db1d344a38777309e4d7c345d218c7760bc62d5e2c6c06`. Offline checks returned host tests `89/89`, phase instrumentation gate `ok:true`, and minimal layout/transport gates `ok:true`.
- r16's `ARMENTRY` was written to carrier slot 0 (`args+0x800`, raw body `0x10100`), which overlaps the early-fault recorded flag. It remains valid proof of `_start_first_cpu`, but slot 0 is not a clean entry-witness field and r16's duplicated phase carrier at raw body `0x10480` is not canonical.
- Phase-r17 is the corrected candidate. Kernel `out/y35a/ios12-kernel-phase-r17/kernel-packed.macho` SHA-256 `6ec40d835d99741ea82072bac01ea5988ab37645fda1360dc464476868866d92`; boot image `out/y35a/ios12-boot3-phase-r17/boot3.img` SHA-256 `b054c13e5073ef0a931ecf50643540ca9212cc8cf474fb6e5a8c95b53e66a2b1`; full-readback probe `out/y35a/readback-probe-20261109-r17-phase-carrier/readback-probe-not-xnu.img` SHA-256 `68b1a20166a1e3716f532fa7ef65805dfd1dfd1c9ac047d5eb52a9e0775fb287`.
- r17 final Mach-O verification is green. `_start_first_cpu` writes `ARMENTRY` to `args+0x820` (slot 4); C `arm_init` entry and the first `PE_init_platform(FALSE, args)` boundaries write slot 5; later `arm_vm_init`, `panic_init`, and console markers also use slot 5. The full-readback manifest has one canonical `early-fault-record` at physical `0xa0b7c800`, and the independent full-readback layout/transport gates plus `89/89` host tests pass.
- The immediate pre-run host suite was `86/86` from the current worktree. `verify_phase_instrumentation.py`, `verify_capture_layout.py`, and `verify_readback_transport.py` all returned `ok: true` with the exact current image and manifest hashes.
- Fresh 11:30 dual RAM-only experiment: T0.2 image `295241ce...` produced a fresh `Y35ARD01` report with `status=0x80000008` (`S_DONE|S_PAGE0_TIMEOUT`), `err=0x01000004` (`E_TIMEOUT_STATE`), and `clkctl_after=0`. The SE timeout remains valid evidence that this handoff did not reach a valid QUP5 transaction. The same report's TLMM pin, ATTn, and GCC values are superseded as hardware evidence: the probe used a wrong TLMM stride, sampled the wrong ATTn address, and stopped its GCC dump before the QUP5 gate registers. This does not prove clock/pinmux absence or S3202 absence. The raw evidence and exact hashes are in `heartbeat-20261109-1130-dual-boot-verdict.md`; the correction is `heartbeat-20261109-144x-probe-dump-window-defect.md`.
- The readback witness image `2aaf092c...` also reran: touch versus readback captures differ only at offsets `0x10..0x13` (CNTVCT), while the report page is byte-identical. This validates probe freshness and confirms the known aliasing transport pathology; it yields no XNU boundary evidence.
- Offline QUP5 source mapping is now frozen in `QUP5-UPSTREAM-MAP-20261109.md` from a sparse `torvalds/linux` snapshot at commit `7475ea8b58616b33c04afb976cf0fbaad9dd63fb`. It source-verifies QUP5 I2C RCG `GCC+0x06000`, application branch `GCC+0x06020` bit 0, reset BCR `GCC+0x06018` bit 0, BLSP1 AHB branch `GCC+0x45004` bit 10, TLMM GPIO18/19 with mux slot 2, QUP5 base `0x78b9000`, IRQ 99, and DMA 12/13. This closes the offline address question but is not a device result. The existing T0.2 dump cannot validate those registers until its TLMM/GCC windows are repaired.

## Corrections to Earlier Interpretations

- The three r6 files `r6-baseline-retained.raw`, `r6-post-boot3.raw`, and `panic-direct-20261109-0017.raw` are byte-identical. Equality supplies no new content. Later r7 CNTVCT witness captures show the probe did rerun, so the earlier claim that the capture path was necessarily a frozen buffer is superseded.
- The initial claim that the readback probe used the wrong `__BOOTDATA` physical addresses was withdrawn. Later review of all eight boot3 `segment_table` entries found linear placement `PA = 0xa0004000 + voff`; the stack-address mismatch claim must not be repeated.
- Fixed 128-byte symbol records include neighboring bytes for 4-byte and 8-byte fields. Compare only the field's actual width; neighboring bytes are not evidence that the symbol itself has that value.
- `Y35AXNU2` is written by the boot shim immediately before its branch to the XNU entry. It proves the shim reached that handoff point and identifies the packaged kernel generation. It is not an XNU phase marker, EPH panic header, or proof that `PE_init_panicheader()` ran.
- The 2026-11-06 launchd panic and the 2026-11-09 short-return boots are different observations. The current cause remains unresolved.

## Current Disagreement

### Immediate direction correction (2026-11-09)

The active readback fixer must stop treating VA-to-PA segment placement as the open defect. The shipped `boot3.img` segment table and the r7 carrier comparison already falsify that premise: for `_BootArgs`, `_const_boot_args`, the panic globals, and the stack carriers, `seg.dst + (va - seg.vmaddr)` equals the existing flat `base + (va - layout_base)` result. Changing the translation formula now would create a new error and invalidate already verified evidence. The remaining readback defects are field-width/host-decode contracts and transport ownership; the phase-r11/minimal-boundary pair is the boundary experiment.

The current shared worktree was measured at `76` tests: `1` failure and `2` errors. The failures are contract drift in `scripts/y35a/readback_native.py` versus the uncommitted `tests/test_readback_names.py` changes (`_field_bytes` is missing, the expected guard text differs, and the entry-trace width expectations are inconsistent). This test state is not evidence of a segment-translation bug. Resolve the test/code contract as one coherent change after the active fixer finishes its edit; do not patch address translation to make these tests pass.

The documented upstream cache `unixnu-research/dl/msm8916.dtsi` is not present on this machine as of this reconciliation. Treat `UniXNU-msm8916-common/dts/msm8916.dtsi` as a projection with recorded provenance, not as the cached upstream source itself, until the source snapshot is restored or independently re-fetched and hashed.

Claude's 2026-11-09 06:00 evidence note says the `d7640a42` boot reached panic-header initialization and stopped before panic text. The available `Y35AXNU2` stamp alone proves only that the boot shim handed off to XNU. Keep the stronger panic-header claim provisional until it is tied to an XNU-owned header field or independently verified raw bytes. The source note is `evidence/y35a-20261102/boot3-20261106/heartbeat-20261109-0600-staging-model-verdict.md`.

The r7 witness proves that the capture probe re-executed and that the handoff stamp changed with the preceding boot generation. It does not by itself prove that every symbol-addressed record is an XNU runtime value. The 05:00, 06:00, and 07:45 heartbeat notes contain the successive analysis and corrections; read them in order when adjudicating any r7 claim.

## Next Work

0. Add independent carrier operands and pre-store/post-store witnesses around r50b's `_native_early_fault_address` publication; preserve unique loop-state and mapping slots.
1. Build from a fresh XNU work tree and rerun the full host suite, final Mach-O verifier, and independent minimal-boundary layout and transport gates.
2. Run one serial RAM-only experiment. Require matching boot/probe kernel stamps, a fresh CNTVCT field, the pointer-window record, and the new publication checkpoints. Stop on a failed gate, invalid raw, or USB transport failure.
3. After a positive `LINKADDR` and mapping boundary, continue to MMU and C startup; run the bounded QUP5 experiment only after the C boundary is supported. Keep GPU, broad drivers, and userspace out until then.

## Source Files

- `evidence/y35a-20261102/boot3-20261106/heartbeat-20261109-0405-r7-witness-capture-chain-live.md`
- `evidence/y35a-20261102/boot3-20261106/heartbeat-20261109-0500-r7-live-read-adjudication.md`
- `evidence/y35a-20261102/boot3-20261106/heartbeat-20261109-0545-boot4-verdict.md`
- `evidence/y35a-20261102/boot3-20261106/heartbeat-20261109-0600-staging-model-verdict.md`
- `evidence/y35a-20261102/boot3-20261106/heartbeat-20261109-0745-t02-gate-recheck.md`
- `evidence/y35a-20261102/boot3-20261106/codex-review-20261109.md`

## 2026-11-10: phase-r21 MMU-to-C handoff result

R21 device result recorded in phase-r21-carrier-20261110-014546/record.md.
The final raw contains ARMENTRY at body 0x60, while MMUON000 at body 0x98, ARMRET00 at body 0xa0, all C slots, and the early-fault address at body 0x3c0 are zero.
The narrow conclusion is that _start_first_cpu reached the entry witness but no post-MMU-enable witness was observed. The exact failing instruction remains unproven.

The r21 kernel SHA-256 is 9c44033b680341811bee6b0ff5f1abc7094f5dded8984b665c8ec2434c5e97a6, boot3 is 8662d72471d3f7799e61c2e39d377f84a3f505492e00d5aea159246129a75380, probe is 2efe7e56de6cd0b3201d0323ef6879077cbad516b72ed2e08242b186c04bd77f, and final raw is bef018039dcda4ca7cbed697ae3aad93d72c8c0e3becc698e24f56517f09b406. Host suite and all offline gates were green.

Next: add pre-MMU checkpoints around common_start, bootstrap mapping construction, TTBR publication/barriers, and the SCTLR_EL1 write. Keep transport and VA-to-PA geometry unchanged.

## 2026-11-10: phase-r43 partial mapping result

R43 was built with the mapping witness chain, but the first probe send hit a USB disconnect (e00002ed) after boot3 returned to fastboot; that final is discarded. After re-enumeration, the matching probe was resent and final-r43-retry.raw was captured.

The retry raw SHA-256 is e44c15f630a94d8c45754fe43b801965dca092c89fdcffff4ce282da8659b154. Its kernel prefix is the r43 kernel generation and its probe header is present. Stable slots through PTSHIFT0 are present; mapping-call pre/return slots were shared with an earlier loop-state experiment in the generated chain, so no V=P/KVA call conclusion is accepted.

Next: rebuild a clean mapping witness with independent slots and no loop-state reuse, then rerun offline gates before another device operation. The device remains in fastboot and no persistent write occurred.

## 2026-11-10: startup ladder reconciled through r43

The valid real-device ladder is now:

- r31: direct physical ARGSLOAD plus raw x22/x23 completed; stack/link were not yet instrumented safely.
- r33: physical stack, TPIDRRO, exception/interrupt stack, and link witnesses completed.
- r34/r38/r39: bootstrap invalidation setup, loop entry/first store, and loop state completed.
- r41: invalidation completion remained blocked by an instrumentation KVA store; later physical correction moved the observation past that point.
- r43: first mapping witness attempt had a USB disconnect; retry raw is partial evidence only. Mapping call slots were not independent from an earlier loop-state generation.

The current clean next target is an independent mapping witness build. Repeated probe-send failures after boot3 (e00002ed/e0004061) are transport failures and must not be interpreted as XNU progress. Detailed partial evidence is in phase-r43-carrier-20261110-130000/record.md.


## 2026-11-10: phase-r50b boundary and pointer-window follow-up

R50b was rebuilt from a fresh XNU work tree after the first r50 draft was rejected by the final Mach-O gate for incorrectly encoded V=P/KVA return markers. The exact r50b record is `evidence/y35a-20261102/boot3-20261106/phase-r50b-carrier-20261110/record.md`.

R50b kernel SHA-256 is `f3223ebb654f11fbe5e043535c62b3582c2016071bbc913d24af9caf970821d2`; boot3 is `90825cd3f6bfb4a142f80fd731a61869b23bf021825648b28d10067e815a4112`; minimal-boundary probe is `f5bf3429d666d4ba3770acc3c46134fa310ee650cf24f0d198d9b200ebe6add0`; manifest is `c94a0da49260bd8fda7c003f02b28ff09408d0ef96f098c143dcd6575f2e3806`; final raw is `f2b62e61b4a1dc4313803187f72e0d1d87e8c46fddb80655e2f807aaa0c31e17`.

The 98/98 host suite, final Mach-O verifier, minimal layout gate, and minimal transport gate passed. The real-device raw is 69,632 bytes and carries matching r50b boot/probe stamps. It proves ARMENTRY, ARGSLOAD, all six boot-argument witnesses, x22/x23, TPIDRRO, exception-stack, and interrupt-stack witnesses. LINKADDR and mapping slots 50 through 55 are zero.

The pointer-window follow-up read back the 16-byte aligned physical window `0xa06d2100..0xa06d2110`, containing `_native_early_fault_address` at `0xa06d2108`. Probe image SHA-256 is `7e3130b059e97276409bcb64c5e3d8d285e8d26af5488b112e8913410a6a7081`; manifest is `ab66f4042f8947a7d56dbe2df546a080071f4ac34af5cfbf79f521c6a51a291a`; final raw is `34cc523767dd18591673f6fb74cb7b96a6d94116d7222a29ac2d56e60f1df033`. The global value is zero. The preserved PRAM prefix matches the r50b final, while CNTVCT differs, proving a fresh readback execution.

The narrow leading hypothesis is a failure in or before the r50b physical publication of `_native_early_fault_address`, because that publication precedes LINKADDR and the global remains zero. This is not yet a proven faulting instruction. The next experiment must add independent operand, pre-store, and post-store witnesses around that publication, then rebuild from a fresh XNU work tree and repeat one serial RAM-only sequence. Stop on failed static gates, invalid raw, or transport failure. No persistent device write occurred.

## R180-R181 decisive source-pointer fix, November 16, 2026

R180 identified and fixed the actual R159 handoff failure. The shim was linked with `__text` starting at `0x80080b30`, then flattened and loaded at `0x80080000`; its absolute `kernel_data` literal pointed at `0x80085000`, while the embedded Mach-O payload began at `0x800844d0`. The source pointer was therefore off by `0xb30`, so every segment copy read the wrong bytes.

The corrected temporary R180 image used the same R159 graft kernel, restored `rd=md0`, and changed only the source pointer to `0x800844d0`. Final raw SHA-256 is `7dce0a2db0348962b7814997e26a288ef6c8f249675e0b643339ff1c7858d0ae`; boot SHA `1cb0e1fd01c3dad7d7fa7a32730471d44a791c4bf19149448c196771ba21ed60`; kernel SHA `a78ed45cb9eb8d9651e7bd29bc4453bcc37720cec9778becc89fe6b4d18d0f36`. Fresh markers are `R84ENT00`, `R84CIN00`, `R84PEIN0`, `R84PERT0`, `R84AVM00`, `R84PAN00`, `R84CON00`, `R85LRET0`, `R86MSE00`, `R86VMB00`, `R90VMIL0`, and `R90LRET0`. The current `_smsg_bufc` contains the current-generation `initproc exited ... amfi_check_dyld_policy_self() failed` panic.

The shared `scripts/y35a/package_native.py` now emits a relocatable source pointer using `_start + (kernel_data - _start)` instead of absolute `adrp/add kernel_data`. New regression test: `tests/test_package_native_kernel_data_pointer.py`. Red-green verification was completed: the test failed against the absolute form and passed after the source fix. `tests/test_native_pack.py` passes all 17 tests. R181 rebuilt the corrected package from the updated source; its offline boot SHA is `1cb0e1fd01c3dad7d7fa7a32730471d44a791c4bf19149448c196771ba21ed60`, and disassembly contains the relative delta path.

The remaining blocking behavior is now narrow and real: AMFI policy registration is missing or not loaded. R154 and R181 both reach the same initproc AMFI failure; the entry, shim copy, DT, carrier, and first-CPU hypotheses are no longer the active root cause.

## R181 corrected builder validation, November 16, 2026

R181 rebuilt the R159 graft through the corrected `package_native.py`. The generated entry disassembly uses `adr x19,_start`, loads the link-time delta `kernel_data-_start` (`0x44d0`), and adds it to the executing flat-image address. The offline boot SHA is `1cb0e1fd01c3dad7d7fa7a32730471d44a791c4bf19149448c196771ba21ed60`; entry bytes are `33469648`.

The R181 matched paired RAM boot on `efff9d92` freshly retained `R84ENT00`, `R84CIN00`, `R84PEIN0`, `R84PERT0`, `R84AVM00`, `R84PAN00`, `R84CON00`, `R85LRET0`, `R86MSE00`, `R86VMB00`, `R90VMIL0`, and `R90LRET0`. R181 final raw is retained at `/private/tmp/r181-corrected-run-20261116/final.raw`; its SHA must be recomputed from that file when cited. The current `_smsg_bufc` contains the current-generation initproc AMFI panic. Treat R180's final raw `7dce0a2db0348962b7814997e26a288ef6c8f249675e0b643339ff1c7858d0ae` as the exact published R180 evidence; R181's manifest and raw files are the authoritative new pair.

The source regression test is `tests/test_package_native_kernel_data_pointer.py`; its red-green run passed. `tests/test_native_pack.py` passes 17/17. Three unrelated legacy failures remain in `test_kernel_build_contract.py` for old marker spellings and do not cover this packer fix.

The active blocker is now AMFI registration/loading, not entry handoff.

## R189 current correction, November 16, 2026

R189 completed a paired minimal-boundary readback around the R188 AMFI graft. Kernel `b04f35759cdc98f20d8b2433e78258dd63bcdb0758bdc87e8cb8880b16760180`, probe image `b185ca975a951e9cb51d33a7feb21c431faa76eac6b119ad3721f5caeab0e29b`, baseline `7d081ecbecc766c94672717c5380c08e8d79d5f227fc1ba31f1010e6d71bf9b6`, final `17aae95f005b3dd7d2a7c4ab363cdf977bdef3d5fc016dacea379ffbe56d99e8`. The device returned to lk2nd fastboot without persistent writes.

The probe preserved PRAM and staged records into the report page. It requested the same physical `0xa2800800` twice: early-fault-record at raw `0x10100` and R188CARRIER at raw `0x10480`. Those windows are inconsistent: the first contains early-fault/R84/R90 records, while the second contains panic text/backtrace. Duplicate-source reads are invalid as independent AMFI evidence. No unique R188/R189 registration witness was observed.

A host-only R189 TrustCache bridge linked all eight pmap names but used explicit placeholder PPL behavior for three functions. It was not packaged or booted. The original 16G102 kernelcache has real implementations at the corresponding pmap addresses, so AMFI remains gated on a legitimate implementation or a proven non-PPL path.


## R190 current correction, November 16, 2026

R190 used a single-source minimal-boundary probe for `R188CARRIER=0xa2800800:512`, removing the duplicate early-fault record from a temporary readback generator. Probe image SHA-256 `1a1443f22aa63adc05ad219048c8467562044cb58d86b5042e3973973f31964b`; R188 kernel `b04f35759cdc98f20d8b2433e78258dd63bcdb0758bdc87e8cb8880b16760180`; R188 boot `668ef11715647fa37f8ac1d42cc2aa5c85f7515b524b7ef41b0629bbf88831e6`; baseline `88cd57ca151371a5726803765fb0b8099eaae273d42a272a99b0d55a70b1ed53`; final `9d5a6f255b35f43af4ca0338deaf23a83d6b7c34cbc9cdb02db5c5670b4f2561`. The device returned to fastboot without persistent writes.

The sole R188CARRIER report is at raw `0x10300`; baseline and final both hold the same old panic/backtrace text, with no unique R188/R189 AMFI registration marker. Duplicate-source overlap is therefore not the only explanation. AMFI registration remains unproven, and placeholder PPL functions remain prohibited from device use.


## Driver and userspace current state, November 16, 2026

QcomSdcc `SdciCore` Phase 0, QcomSdcc `PersistStore` Phase 2, and QcomQupI2c T1 host suites now pass with fresh binaries under `/private/tmp/unixnu-driver-check-20261116/clt2`; the three binary SHA-256 values are recorded in LOG.md. The R156 QcomSdcc arm64 object closure remains host-only and verified; no device attach or kernel link has been completed.

The current 58-Mach-O RAM root reaches the PID 1/dyld boundary. R154's paired hardware result is the direct AMFI `ENOPOLICY=103` measurement, so rootfs mounting is downstream of the present security stop. SpringBoard and the full System/Data volume remain later dependencies.


## R193/R194 maximum-RAM driver boundary, November 17, 2026

The maximum-RAM safe kernel now links IOStorageFamily-191 plus QcomSdcc and its personality. R194 reached the R88 BSD/IOKit boundary on hardware, but the temporary QcomSdcc probe/start/ready markers did not appear. The next experiment must instrument the R88-to-IOKit attach ladder or fix the personality/provider path; changing SDCC register code before attach is observed would be misdirected.

AMFI remains a separate security stop after PID 1/dyld. No placeholder PPL, signature bypass, or fake TrustCache behavior was used in R193/R194.

## 2026-11-17: R154-native AMFI graft reached initproc

A clean R154-native security graft was paired with a probe generated from the exact graft Mach-O symbols. The device returned to fastboot after the RAM-only run. Final retained output contains a current `initproc exited -- amfi_check_dyld_policy_self() failed` panic, current Kernel UUID, iBoot version, and current timestamp. Kernel SHA-256 is `99f92d62bf3948c54671b1dfec7c87d1241e45dc0103ae297555cdddf9e7a563`; the formal package boot SHA-256 is `db307b69db80e460950df7b755182fb9722c666ed84cf2bc2b8c63b54cd67ef0`; exact probe SHA-256 is `cb9e3fb17e1252bad692021738d4a6a7e8a580aa5e31aad9d721ff37edaf2afa`; final raw SHA-256 is `8e567937260ce35e3830b90b286e3cc7830b09e4cb0972c0b5f79d5ea405c2a`. This rules out early handoff and page-table failure for this candidate. The active blocker is AMFI policy/security-extension registration or its runtime contract.


## R258/R259 current correction, 2026-11-18

R258 produced a genuinely relinked XNU kernel after fixing the host closure. The native unstripped kernel is `/private/tmp/r258-y35a-iokit-cursor-link-20261118-04/obj/DEVELOPMENT_ARM64_T7001/mach.development.t7001.unstripped`, SHA-256 `011e199dfb5bcc0865dc7b04cab372e14efe78f100f5f7c27bc82b995c7897b4`. Its final link force-loaded `/private/tmp/r258-arm-driver-archive-20261118-01/libarm-y35a-iokit.a` (SHA-256 `f920c94f2c7902414eeb6e54fd163a8c57b909f655443fcd3f6143454cb889db`), and `nm` shows ArmDTPlatform/ArmCpu metaclasses, vtables, methods, `_armdt_platform_configured`, `_armcpu_registered`, and `_gIOKernelConfigTables`. Both driver initializer pointers are present in the final `__DATA_CONST,__mod_init_func` section. The R258 cursor codewords are present in the compiled `pe_init.o` and `IOStartIOKit.cpo`; the final kernel also contains the linked class implementations.

R258 graft/package/readback identities: graft SHA-256 `b814ccaa4057083d649420a7b2cd97d5b76979d120598e48ec2decfcdd3fdb6c`; boot SHA-256 `d11a9656f8124840b1508bd6ae05f09804f13cc23b6d5b3201150737888b8a91`; probe SHA-256 `b2a8721e23378cd0ba973fe49cb930ae0a51397c27b1a5e3721f47abdfddd5de`. One paired RAM-only sequence ran on serial `efff9d92`, product `lk2nd-msm8916`, unlocked=yes, and returned to fastboot without persistent writes. Baseline raw SHA-256 is `f8fd833bda78b09c5aed7eccc3bac12fbbe5610d1487fc11d168d55a17d91ad8`; final raw SHA-256 is `85547c32af3fb5384dfa0c7dd420d2c847341753564d0eac93dd8c5e6cacefd4`. The report header and final shim kernel prefix are fresh and bind the R258 kernel. The original early record is unchanged between baseline and final and ends at `R88LOCK0`; `R88IOKIT` is absent. The proposed boot-args carrier window was overwritten by an old panic/stackshot buffer and is not usable as current-run cursor evidence. Full record: `/private/tmp/r258-amfi-iokit-run-20261118-01/experiment.json`.

A forensic minimal-boundary readback of physical `0xa27e4980:1536` returned raw SHA-256 `3ec18c019bb5bac8232ab069e4ac5a59c241405054df64d4559e12fe0ffea368` and showed the same stackshot text across the carrier tail. This proves the carrier ownership is contaminated by retained panic data; it does not locate an R258 fault.

R259 then moved the cursor array to a zero-initialized kernel BSS symbol. The R259 patch is `/Users/lingion_k/unixnu-research/UniXNU-y35a/patches/xnu/native-y35a-iokit-cursor-r259-bss.patch`; focused contract tests pass. Its private link is `/private/tmp/r259-bss-cursor-link-20261118-01`; the BSS cursor is at VA `0xfffffff0077ce408`, physical `0xa07ce408`, size 64. R259 has not been packaged or booted.

The next experiment must package R259 with a readback record bound to `0xa07ce408:64`, then run one paired RAM-only sequence. A fresh nonzero BSS cursor distinguishes current XNU C/IOKit execution from stale carrier text; a zero or unchanged BSS window leaves entry visibility unresolved. Do not interpret R258's old R88 markers or stackshot carrier as fresh evidence.

## R260-R268 retained-carrier and exact-entry boundary, November 18, 2026

R260 fixed a critical transport defect: a witness written in `boot_args+0xa00` is overwritten or replaced by the resident loader before the matching probe. `scripts/y35a/package_native.py` now also writes a copy witness into the preserved report-page gap at physical `0x859f0080`, while leaving the existing TrustCache probe at `+0x20` unchanged. The focused package contract passes.

Strict paired R260 run used kernel `8b2f6a8f3ee7c6a9e1d40c5aa6383cc668fc457dfc6ee19ba4d02a673b1f675d`, boot `72a05c25899b6e6e135a20f94868f91bc87aec7a47607f10bbcb536301c4ce98`, matching probe `7918c2902f3e6a4547cd1d94b8e8df601e8c02628a8b059f7399e4879fc95bca`, baseline `690b5d52bc50a114d22681b8368f6c83b3d50de89aac5f08454e8a3eae06596`, and final `78e82f5de0bd288bfa23bb5bfa7adca9f566c3bd547486e8aea4d17a5b308157`. Every boot observed disconnect then re-enumeration. Final retained carrier contained `R260CPY0`, entry `0xa027e098`, and first two copied instructions `0xd503201f140007f0` and `0xd503201fd503201f`. This proves shim copy completion and real entry payload capture.

R261 added an early assembly witness immediately after `mov x20,x0; mov x21,#0` in `_start_first_cpu`, stored to retained report carrier offset `0xa0`. The intended label was mistyped in the halfword construction and the actual little-endian bytes are `R261EN00` (`0x30304e4531363252`), not `R261ENT0`; treat the actual codeword as authoritative for the current binary. The final exact early record from R266/R267 also retained `R117EN00`, `R117CIN0`, `R117PEIN`, `R84SET00`, `ARMRET00`, `COMMON00`, `MAPDONE0`, `TTBRDONE`, `R68E7PM0`, and `R84FS00` in the current package's exact `args_physical=0xa0c1c000` window. Therefore XNU entered the first-CPU path and reached `arm_init`/the `PE_init_platform` callsite; old reads of `0xa27e4a00` were wrong for later packages and must not be reused.

R264-R266 retained mapping markers did not appear, so they are not valid proof of PE failure: their slots were either too early for `ml_io_map_wcomb` or were overwritten by later fixed owners. Existing slots31-47 are owned by earlier start.s/boot markers. Do not infer a stop from absent R267 markers in those slots.

The next diagnostic must use exclusive external slots 66+ or a matching extended readback record, because slots0-65 are already owned by startup/publication contracts. Current hard boundary is the `PE_init_platform`/`pe_identify_machine` region after proven C entry, with exact sub-boundary still to be isolated.

### Current continuation checkpoint: R304-R306 SIGTRAP audit

The latest full RAM-root paired runs remain bound to serial `efff9d92` and return to fastboot. The active kernel/userspace boundary is still `initproc exited`, OS reason namespace 2, code 5. `debug=0x0` did not change it. A PID1-only SIGTRAP suppression experiment did not change it. Moving diagnostic carrier slots 76..79 before the panic buffer did not produce reliable new values; retained carrier evidence after userland remains invalid. Do not claim crypto emulation or handler execution from these empty/ASCII slots.

Launchd static inspection found `_abort_with_reason` at `0x100028f80` with namespace argument 7, and signal calls at `0x10000e1bc` and `0x10001d650` using non-SIGTRAP values in the inspected paths. The separate launchd/dyld SIGTRAP source audit is still the next active task.

## 2026-11-20: R1D embedded strict entry audit

R1D was rerun with strict binding to the actual XNU bytes copied from `entry-obf.bin + 0x328` for 12,288,976 bytes. Embedded kernel SHA-256 is `93f95e079b39469f2dc2d4c5f4077fe4caeba6a64084e59963a7a119f8e374b9`; boot SHA-256 is `95f47dc50f82e92078fa0becf34582cdeedbf521236bbf8b8da20a0bca7f7385`; probe SHA-256 is `fd0f47adf5fa8089db6a8f9fdad7af33bbd95b86627e56338ca92651bfb31386`; baseline/final raw SHA-256 values are `95ab878337f6a4e154cc39c66a105b77eeaab4745810cbb8382c9a29ef0c5e57` and `34f3e1ee4d67e8e99f54a50dfa8adedc3e6a34f33c460d2cc78e605a93936bfd`. The run was RAM-only with `persistent_writes=false`.

The strict raw pair contains `Y35AXNU2`, `R260CPY0`, and old `R84/R90` strings in both baseline and final. It has no fresh R1D entry witness, early-fault record, or current entry trace. The direct-entry negative result is correctly bound but cannot locate a fault or prove current XNU entry.

## 2026-11-20: current R154 replay after host reboot

The persisted R154 v3 package/probe was replayed on serial `efff9d92` with the original hash bindings. Kernel SHA-256 is `4e7903810d5f70d6ab2907754a9619650113fc803c777c0a37a2bd4ff70fea2f`; boot `d9d4c4f43986717e80332056da82086f5dede9c36f83b6314a0780a67be41891`; probe `ea257e369e3cd682d41557905d41d6bacd48cfdfce911f899881f2a76b37f63f`. The new baseline/final raw SHA-256 values are `fdad9101e1305dab95d9ed31af3c76dfdb95aabf7f4c6892a13436de4f2d27a6` and `8bd00adb81f6b2637794b0c31ca33da302d6c759ddab99c40fd79c11cdb9cb40`; `persistent_writes=false`.

The current replay freshly decoded the R154 AMFI probe as `policy_name_matched=false`, `callback_present=false`, errno `103` (`ENOPOLICY`), with a fresh R154 state/commit pair. The current panic text again identifies pid 1 `launchd`; no Apple Logo, display, SpringBoard, or complete iOS UI is evidenced. This confirms the userspace-reaching control remains reproducible after the host reboot and the active blocker remains real AMFI/CoreTrust policy registration.

## 2026-11-20: original iOS 12 ARM64 pmap ABI recovered

The local 16G102 kernelcache (`70e80388d42fe2376096bb6248073b0380dd87b85b1a792b36205ba60c722ce1`) was disassembled directly. All eight R155 missing exports exist in the original ARM64 kernelcache. The legacy loader, static and loaded TrustCache lookup paths, UUID duplicate checks, and reserved-page list operations have concrete behavior that can be ported and tested. `_pmap_in_ppl` is genuinely `return false` in the original iOS 12 ARM64 binary. `_pmap_load_image4_trust_cache` remains dependent on opaque Image4/security interfaces and protected runtime state; it is not safe to replace with a constant. Full byte-level findings are in `R158-ORIGINAL-PMAP-ABI-AUDIT-20261120.md`.

## 2026-11-20: R158 original TrustCache ABI harness

A host-only harness now models the recoverable subset of the original iOS 12 ARM64 TrustCache ABI: sorted v1 static lookup, loaded-list lookup, UUID duplicate rejection, and reserved-page pool claim/free. It ran against the exact R154 RestoreTrustCache (`099a621d60e0333eef68d11c2820f99aea0e0e3674d1873d7a52193877a44ba0`): version 1, UUID `9bd72ab3446a43b89459d362d5d0622f`, 174 entries. Dyld and launchd both hit with hash type 2 and flags 0; a zero CDHash missed; first legacy load returned 0; duplicate returned 11; a freed page was reclaimed. Image4 loading remains unresolved and is explicitly not treated as success.

## 2026-11-20: R158 ARM TrustCache subset patch drafted

A host-only patch candidate `patches/xnu/native-y35a-pmap-trustcache-r158.patch` now targets the XNU 4903 ARM pmap layer. It implements the real v1 static binary search, loaded legacy TrustCache UUID/hash lookup, duplicate UUID rejection, `trust_cache_init()` from the existing ARM `segEXTRADATA` TrustCache mapping, and the original ARM64 `pmap_in_ppl=false` behavior. `git apply --check` and `git diff --check` pass against the pinned xnu-ios12 source. The patch is not applied, built, packaged, or booted. Image4 loader and reserved PPL page ownership remain explicit unresolved gates.

## 2026-11-20: R158 ARM pmap object compiled

The R158 patch was applied to an isolated copy of the persisted formal XNU 4903 source and compiled with the formal generated headers plus local Apple Clang 14.0.3. `osfmk/arm/pmap.c` compiled successfully with exit code 0. The resulting object is `/private/tmp/r158-xnu-obj-20261120-01/pmap-r158.o`, SHA-256 `de9803d7c93db7afdc7eb8cf8284d105da3e11dc5abb503b0e9b60218e876941`. The compilation emitted the existing ARM pointer-cast warnings and new missing-prototype warnings, but no R158 errors. A separate arm_vm_init attempt used the ARM64 compile database and is invalid for judging the ARM source; no kernel link or device boot has been claimed.

## 2026-11-20: R158 clean no-minimac host kernel linked

The R158 pmap patch, corrected AArch64 `arm_vm_init` call, and a startup object with the old minimac initializer removed were linked into a clean host kernel. Kernel SHA-256 is `4c12d04788b1df00ee47e353c588ef5f7d5d08023e8f58c33feab0ce06c4d67b`; manifest: `reboot-checkpoints/2026-11-19-mainline/r158-clean-host-20261120-01/manifest.json`. `native_minimac_policy_init` is absent from the linked symbol inventory. The existing phase verifier rejects this artifact because the retained formal archive does not satisfy the old R84 marker contract; this is a host artifact, not a device candidate. Image4/PPL API closure is still incomplete.

## 2026-11-20: R158 pmap pointer-table and ownership audit

The original `__PLK_DATA_CONST` table slots map through `__PRELINK_LINKKASLROffsets` to CoreCrypto's three claim/free/in-PPL imports and AppleMobileFileIntegrity's five TrustCache imports, matching the R155 v6 plan. The original claim/free routines and Image4 loader share BSS head `0xfffffff00764ab58` and lock `0xfffffff00764af58`, and the Image4 loader makes indirect security-interface calls. R158's Python page-pool model is not a kernel implementation. Exact offsets, addresses, and limits are recorded in `R158-ORIGINAL-PMAP-ABI-AUDIT-20261120.md`. No R158 device run or Apple UI result exists.

The AMFI image has five static import veneers at `0xfffffff0061f4800..0xfffffff0061f4838` for the five TrustCache APIs. The repeatable static audit and persisted JSON are bound by SHA-256 in `R158-ORIGINAL-PMAP-ABI-AUDIT-20261120.md`; they prove import wiring only, not runtime reachability.

The newer local XNU reference shows the real Image4 dependency shape: reserve a CoreCrypto page, validate and lockdown payload/manifest pages, obtain writable TrustCache state, call `amfi->TrustCache.load`, and release the page. Its current `pmap.c` and `pmap_cs.h` hashes are recorded in `R158-ORIGINAL-PMAP-ABI-AUDIT-20261120.md`; these files are a reference and do not make R158 bootable.

R159's complete closure audit is `R159-IMAGE4-CLOSURE-AUDIT-20261120.md`. It confirms the iOS 12 source tree lacks the corresponding `pmap_cs`, AMFI, TrustCache, and ARM pmap dependency paths; Image4 remains unresolved and no R159 device candidate exists.

The local `xnu-0b4b910d` feed is only a source lead: it uses a newer `pmap_load_trust_cache_with_type_internal` contract and still requires PPL/TrustCache interfaces. It has not been transplanted into XNU 4903.

## 2026-11-20: durable R326 restoration and live replay

The host-rebooted R326 state was restored from `/Users/lingion_k/unixnu-research/reboot-checkpoints/2026-11-19-mainline/` into the durable index `/Users/lingion_k/unixnu-research/reboot-checkpoints/2026-11-20-r326-restored/`. The formal kernel, formal3 package, matching probe, source snapshot, patch, force-load archive, and prior paired runs remain bound by SHA-256; only their old `/private/tmp` working directories were lost.

A new paired RAM-only replay on `efff9d92` used kernel `9b9c2f0302f08d563783533754116aa1b02e99540d6f8e03a45316935fabbe9c`, boot `e80800bf65177782eefc0bf150bca3b1fddb186f9f033d097c7b0b958c92cdbe`, and probe `f217be233ac370ef095b4c7102432fa2b5a63c9ef7911beffeee23e17744f6bf`. Baseline/final raw are `d8e635b6da02393f8885d535b44d0d76f48287af36d2438c64e5d15ee502d863` and `a21992466ee3a060649375f37ab043ec7c40909b6e5468c5b4460582aec92de0`. Fresh `Y35AXNU2` and `R260CPY0` are present, and the current panic is `pid 1: launchd` with `amfi_check_dyld_policy_self() failed`. Device returned to fastboot; persistent writes were false. This re-establishes the launchd/AMFI control on the restored assets.

## 2026-11-20: Xcode restored, formal rebuild and replay

The official Xcode 14.3.1 (14E300c) with iPhoneOS 16.4 SDK was restored to `/Volumes/SleepyExternalData/Offloaded/Applications/Xcode.app`, and `/Applications/Xcode.app` again resolves to that path. A formal native rebuild from the durable XNU snapshot/patch/force-load inputs completed compilation and linking on `/Volumes/Mobile/r326-native-rebuild-20261120`; the historical phase verifier rejected old R84/slot64 contracts, but the linked kernel was packaged with a matched probe and booted RAM-only.

New identities: kernel `f309866a8a6329bd493568c883495f6cc504e5e4667295a169d4ce55b2f54101`, boot `8ace3aac0d7cc9f295d63c41f5d7a250769538e985239f1386af2579dbcadb27`, probe `fba84fac0c10ce0a3eb79f83bf5776b7f92516a9ae441325a1581ca6b57738f0`. Paired raw are baseline `4ed154d1d2673a58e4c3b572ec5173f8283e69b5a0ef2014a26294bd9d92ca47` and final `84b2f817297422b61d8eba0d67a0e6a766a6cc863a9cb5436b5cdc3e7752a080`. Final contains fresh `Y35AXNU2`, `R84ENT00` and current handoff markers, with the same current `launchd`/`amfi_check_dyld_policy_self()` panic. Device returned to fastboot; persistent writes were false.

## 2026-11-20: R159 pmap closure linked and graft emitted

A new Xcode 14.3.1 host rebuild with `native-y35a-pmap-trustcache-r159-legacy-only.patch` linked kernel `69fb5f078119213df42649f777ce3ab66686e09a1fb9b2dfc8116b351f3e18d1`. `nm` shows all eight required pmap/TrustCache exports. The security-only legacy graft plan against the original 16G102 cache found 799 bindings, zero missing exports, zero collisions and zero null bindings; the emitter produced candidate `b37cee63a1a8987ecc4c2b562cf1c896270bd2d14f0980d57cd8cad3b6c2e833`. The candidate remains explicitly loadable=false/runtime_qualified=false because register/dataflow, prelink runtime placement, KEXT loading and Image4/CoreTrust/PPL behavior are not closed. No device boot was made.

## 2026-11-20: R159 graft candidate structural audit

The emitted R159 security candidate contains 18 prelink metadata entries including AppleMobileFileIntegrity, corecrypto and CoreTrust. It has 799 bindings, 0 missing exports, 0 collisions and 0 null bindings, with all eight pmap/TrustCache symbols supplied by the R159 kernel. The emitter still marks it `loadable=false` and `runtime_qualified=false`; no package or device boot was made. Remaining gates are register/dataflow qualification, loader acceptance, actual AMFI policy registration, CoreTrust/Image4 validation and equivalent protected-page behavior.

## 2026-11-20: R159 candidate static integrity gate

Added `scripts/y35a/qualify_r159_graft_static.py` as a repeatable host-only gate. It passed against candidate `b37cee63a1a8987ecc4c2b562cf1c896270bd2d14f0980d57cd8cad3b6c2e833`, verifying 18 prelink entries, all three security roots, 799 binding sites/targets inside candidate segments, 799 KASLR offsets, zero missing exports and zero collisions. It intentionally leaves `runtime_qualified=false`; it does not authorize a device boot.

## 2026-11-20: R159 component relocation gate

A new host-only component gate verifies the real graft candidate against the original 16G102 bytes. For AppleMobileFileIntegrity, corecrypto and CoreTrust, every difference is within declared binding or Mach-O header relocation ranges; all three kmod pointer fields rebase exactly by the slide; unexpected diff bytes are zero. This strengthens static graft integrity but leaves runtime qualification false.

2026-11-20 R159 prelink round-trip gate: the candidate's legacy prelink dictionary round-trips byte-exactly and idempotently; the full prelink segment is byte-identical after serialization; 18 entries and 799 KASLR offsets are structurally valid. Gate JSON SHA-256: 20ff8ad274cf66c8a036404f595f4a42d9c0fd2d7db65d3ad39bbfff6c29ccad. Runtime qualification remains false.

2026-11-20 R159 loader metadata gate: all three security entries have executable and kmod_info addresses inside the expected prelink text/data segments; AMFI has AppleSecurityExtension=true, OSBundleRequired=Root, and CoreTrust/corecrypto dependencies. Gate JSON SHA-256: f231f0f00c639be6949a27172546bcfc259fecb5c80d8bf1d5da6945e530143d. This proves metadata layout only; loader runtime acceptance and AMFI registration remain unverified.
## R159 graft candidate paired RAM-only result, November 21, 2026

A corrected-link graft package was tested on serial `efff9d92` with no persistent writes. The temporary Mach-O entry linker was corrected so the extracted `__text` VMA is exactly `0x80080000`, matching the Android handoff contract. The candidate boot image SHA-256 is `5cc8490dbacb91cf5ef2a63723631dee5e4fce1f78141dfaec7b9dc442f86834`; the matching minimal-boundary probe SHA-256 is `75ab0c895aa6dfee1dcb041d857f257b6d2b0d22224062b30ec7d5e79cb49577`. Candidate kernel SHA-256 remains `b37cee63a1a8987ecc4c2b562cf1c896270bd2d14f0980d57cd8cad3b6c2e833`.

The paired run is `/Volumes/SleepyExternalData/r159-graft-run-20261121-v6/`. Baseline raw SHA-256 is `28274ea00489e5eb5936ef61b73fd8a7c157e84a8bb897a539d784da4b2d67b6`, candidate raw SHA-256 is the same `28274ea00489e5eb5936ef61b73fd8a7c157e84a8bb897a539d784da4b2d67b6`, and final raw SHA-256 is `484b800ba6891be7ff4b421b6dee5c232dfd708017d24f7ac6d92657813f29f2`. All nine fastboot operations returned zero and `persistent_writes=false`. The candidate raw being byte-identical to baseline means the retained-memory result did not provide a fresh candidate-generation distinction; it does not prove candidate XNU or AMFI execution. The candidate remains `runtime_qualified=false`.

A separate marker-only diagnostic package used the same corrected entry and replaced the shim literal `R260CPY0` with `R159GFT0`. A staged raw captured the marker at raw offset `0x10080` with SHA-256 `415b028a46d5a0620d5834c01aba16eae817df23ecd05fe8f4013fd44ff3bd3b`; that run was not a clean paired capture because the baseline/final transport was unavailable, so the marker is consistent with shim execution but is not independently bound to that candidate boot and does not prove that XNU or AMFI reached a new boundary.

The next required witness is an XNU-owned marker with a generation value distinct from the shim marker. Until that exists, retain the R159 candidate as an experimental boot artifact and do not claim AMFI registration, launchd progress, display, or UI.

## R159 clean-report boundary run, November 21, 2026

A clean-report candidate shim cleared the entire report page before writing `R159GFT0`, then branched to the candidate XNU entry. The local boot image SHA-256 is `d02b05cd00a2184a1faefeca8308249f931c6a0a0be80069be09945d0b3fa11`; matching probe SHA-256 is `75ab0c895aa6dfee1dcb041d857f257b6d2b0d22224062b30ec7d5e79cb49577`. The paired run is `/Users/lingion_k/r159-clean-report-run-20261121-v2/`, with baseline raw `5b4cb2360d96dee370bf88d355881b3fff0a2ffd72fd1d5ec07b7ca1b84afd76`, candidate raw `308064904b65bef69f5200107a5af0cfad2eccba2d6ea0522067a15cbcfb6729`, and final raw `ed4ea8bd955f7bbaa77da8c91f59f6e768e3ec6721ddaa8af2f8002a3a8e270b`. All boot, staged-panic and get-staged operations returned zero; no persistent writes occurred.

The candidate raw report page contains fresh `R159GFT0` at raw `0x10080` and the candidate entry pointer `0xa0283098` at `0x10088`. The report was otherwise cleared: the early-fault record at raw `0x10100` and the `_start_first_cpu` carrier position raw `0x10120` are zero, so no fresh `R84ENT00` was observed. The baseline/final pages retain old probe strings, while the candidate page does not. This narrows the current candidate boundary to shim marker store and before the first XNU-owned `_start_first_cpu` marker. It does not reach the AMFI question yet.

Static candidate disassembly identifies `__start` at `0xfffffff007283098`, which stores `RTENT0R0` through `[x0,#0xa00]` and branches to `_start_first_cpu`, and `_start_first_cpu` at `0xfffffff007285058`, which stores `R84ENT00` through `[x20,#0x820]`. Neither marker is fresh in the clean candidate report. The follow-up extra-PA probe for `boot_args+0xa00` was interrupted by USB transport failure; no raw from that attempt is accepted.

A direct candidate-only read using the clean-report entry-witness kernel succeeded after USB re-enumeration. Boot SHA-256 is `5a1188048bd24da2ea21b29f92d6d8add3e05bd03f0c1b1037f7c629752e25dd`; raw SHA-256 is `308064904b65bef69f5200107a5af0cfad2eccba2d6ea0522067a15cbcfb6729`; `persistent_writes=false`. The clean report contains `R159GFT0` at `0x10080` and entry pointer `0xa0283098`, while `RTENT0R0`, `R84ENT00`, and the early-fault area are zero. This directly confirms the shim marker store and narrows the current failure to the flat entry branch/target physical code fetch before the first `__start` store.

A branch-probe candidate read back the target physical bytes before `br x1`. Boot SHA-256 is `d398e950d7f6897e8acdcd536a0d920a32106000bdca20b267bbc569bb30dd6c`; candidate raw SHA-256 is `308064904b65bef69f5200107a5af0cfad2eccba2d6ea0522067a15cbcfb6729`. The clean report contains `R159GFT0`, target `0xa0283098`, and target bytes `4f8a8ad2afc8a9f28f0ac6f24f0ae6f2` plus `0f1004f9704e01580f8005f9704e0158`, matching the candidate `__start` first 16 bytes. `RTENT0R0` and `R84ENT00` remain absent. This rules out the embedded payload/source pointer and target physical data read; the active boundary is now instruction fetch/branch execution at `0xa0283098` or its immediate exception route.


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

## 2026-11-22: R326 fresh cpu_data_init boundary correction

Paired clear-baseline-final captures now bind the external `cpu_data_init` record to the current generation. Latency kernel final fresh markers include `CDIN1300` after `cpu_idle_latency` and `CDIN1500` after `cpu_regmap_paddr`; phys-id kernel final adds fresh `CDIN1600` after `cpu_phys_id`. Current accepted boundary is after `cpu_phys_id`, before the later cluster metadata and `cpu_signal` completion. Earlier external strings from runs without a zero baseline are not accepted as fresh evidence. See the appended R326 adjudication in `LONG-RUN-STATE.md` and `LOG.md`.

## 2026-11-22: R326 metadata control boundary

A clear-baseline skip-metadata control reached fresh `CDIN2000`; individual cluster-store, marker-call, and cpu-signal skip controls did not. A tail control reached the end-marker slot with a reused `x2` value, so it is reachability-only. The unmodified boundary remains in the post-phys-id cluster metadata / signal / cpu_data_init-tail interval.

## 2026-11-22: A53 FP control resolved cpu_data_init cluster path

Enabling CPACR_EL1 FPEN at the actual linked common_start allowed the original SIMD cluster stores to execute. Fresh final reached CDIN1700, CDIN2000, and CDATER00. The source patch `native-y35a-a53-enable-fp.patch` must be incorporated into the real build; the current binary control sacrificed TPIDR clearing and is diagnostic only.

## 2026-11-22: current strongest continuation

The A53 FPEN control plus const_boot_args probe produced fresh CPUDATA0 and CDATER00, then PEINITEN, PEINITRT, ARMVMINI, PANICINI, and CONSOLE. This is the current strongest continuation beyond cpu_data_init. The FPEN control still sacrifices TPIDR clearing; source-level FP patch and post-console instrumentation remain pending.

## 2026-11-22: source FP build

Formal local-CLT source build now verifies the A53 FPEN patch in common_start. Kernel SHA-256 `505da572a9d7eb9ea4fd085d4b654f373a872a57fd7b25cafff7df2a9dc19d5e`. It is not yet packaged or device-run; the tested binary FP package remains the runtime evidence.

## 2026-11-22: formal FP package validated

The source-level FP kernel was formally packaged and paired-booted. Kernel `505da572a9d7eb9ea4fd085d4b654f373a872a57fd7b25cafff7df2a9dc19d5e`, boot `7fb3a30f0545ca059c9874ce8850d24b34450f866a44c68985a9385ffced34f5`, final raw `a63e4cf4cb7225169a5642f9917af1a82e40d7639d72c0d7114ebfeb334e45fd`. Fresh continuation reaches CPUDATA0, CDATER00, platform/VM/panic/console markers, CDIN1700, and CDIN2000.

## 2026-11-22: post-console formal boundary

The formal source FP/post-console package reached fresh POSTCNS00 and POSTPRT00, then stopped before POSTIDL00. The current accepted formal boundary is immediately before or inside cpu_machine_idle_init(TRUE).


## 2026-11-23: R326 R91 machine-startup boundary

R91 kernel SHA-256 `b50eee7ad783390971e43d7bb61c9e8e606174343c8dc27dcd10a3e039df3e15`; boot SHA-256 `d01a4c2141fb845f89cc3330e21d9efd5a50be563cbf2d06183c71508102bb72`. Regular probe SHA-256 `b556e0801bae5024a7e7e9bd3384b6532378f5eb37c7e30aa0b1af8c9bbb8022`, clear probe `cde76b4d5643755de44368370a00717dc2085dbc9571bb7d7f9f46b20071fe0f`; both carry 15 records and the current external record at `0xa0bacb00/256`.

Accepted paired run: `reboot-checkpoints/r326-r91-machine-startup-cursor-paired-run-20261123-24/`. Raw SHA-256: preclear `80b29219b5dc47e5a1cae475984ff0e13a955f39b1e5d7f00388ec700b87c2fd`, baseline `8b89756ca6a342a566e6f781fe6b7539b48f309e3711059efe0281e0ea25a473`, candidate `c2614086777097da8036061b908af6ab85fde1e16e1e84333f4aff50eeb9efbd`, final `56127969c217f999fd3093a6ccce05d51a40aee1fe67a7fcdb72b544db4d275a`. Preclear and baseline external windows are zero; candidate is shim-only mapping evidence; final is same-channel fresh evidence.

Final contains `IDLEBEF0`, `IDLERET0`, `MCHCALL0`, `MCHENTR0`, `MCHCONF0`, `KBOOTEN0`, `KTHRBEF0`, and `KTHRRET0`. This proves `cpu_machine_idle_init(TRUE)` returned, `machine_startup` was called and entered, `machine_conf` returned, `kernel_bootstrap` entered, and `kernel_thread_create` returned. `KTHRRET0` is before the error check and does not prove `KERN_SUCCESS`. No kernel-bootstrap-thread entry or success-branch witness yet.


## 2026-11-23: R326 R92 kernel-bootstrap boundary

R92 kernel SHA-256 `865466467ebbaf6e36d07b58e02ca191789c7cedbf1bb76633d43fb550317ae3`; boot SHA-256 `7bd280daa287dccbcfa41751cafffa0b5d9506005219f2a1204fdb7d244158c0`. Regular probe SHA-256 `d2380db6878b1ce86daab9e4c7d60fcafc7f2ad81f4b94b634b3986c01a56176`; clear probe `6dfdd3b9265312057b5e71b18aa467c057c6d7b6a9b57fbdf7ad814aeb564c61`.

Accepted paired run: `reboot-checkpoints/r326-r92-kernel-bootstrap-cursor-paired-run-20261123-31/`. Raw SHA-256: preclear `7d07dd335365ef3249ea1bdc953b22e18fef378ca5eb97f524139032cd2d1797`, baseline `4a81e2f1f5628a1a8be33d8f270265bdd4dc932837e4942ecc38f8376899d0ea`, candidate `fdbf43569b2aa7e4956db9ec31b4d66185e78770858a63edc6fefae5cbadd8ab`, final `0c138b16f4e9b65edc35c7e2258a8172735daf734c2bd3f4b77c1f8b39f09948`.

Preclear and baseline external windows are zero; final fresh data has 15 copied records and the R91 markers, but no `KTHROK00`, `KBTENTR0`, or `KBTIDL00`. The accepted boundary remains after `kernel_thread_create()` return, before the post-check success marker and before entry to `kernel_bootstrap_thread`.


## 2026-11-23: R326 R93 thread-init boundary

R93 kernel SHA-256 `3d480f82773d28fb1826921c8eb10ae09e880560268243a00463eee5351cc75a`; boot SHA-256 `d8425c1165e0af62e31f7b206cc758e24c302fb0365860b09a5e4437b7c63230`. Regular probe SHA-256 `58f8e7956ef2d9d08464f0ce5dd1502f63c8220cae758f0c95c66610164e62d2`; clear probe `13c27c899bfa1f0330d52a3263611c16890fe92d3f89c0d0a98144871b21dc54`.

Accepted paired run: `reboot-checkpoints/r326-r93-thread-init-cursor-paired-run-20261123-39/`. Raw SHA-256: preclear `fbd263a62269b449a02f20e09ddea2b2e7835839e2c5b6314d6dcf32fe7b8202`, baseline `ae2f6a10fcb75b700b78de6c48f0cf90b64325f0ab00411d844272d4b74386a5`, candidate `a6af23f2523e9ede1228477c5e6ed3a54d46acfee187680d86773538f2c9f0f7`, final `c2988656c779cb820e3c6d99c76bf8fc073e931958f56abcccabfe95cf8648ae`. Preclear/baseline external windows are zero; final is same-channel fresh.

Final retains all prior markers but contains no `KBTSCH00`, `KBTHD000`, or `KBTTCI00`. The measured boundary remains before or inside `sched_startup()` in `kernel_bootstrap_thread` (the entry marker itself is not present).


## 2026-11-23: R92/R93 marker-layout correction

独立源级复核发现 R92/R93 新增 marker 的 offset 使用错误：`native_external_phase_marker` 以 `native_phase_args + offset` 写入，而本轮 external probe window 从 `args+0xb00` 开始，物理范围为 `0xa0bacb00..0xa0bacbff`。R92 的 `args+0xc8/+0xd0/+0xd8` 与 R93 的 `args+0xe0/+0xe8/+0xf0` 均落在 probe window 之外，因此 R92/R93 final 缺少 `KTHROK00`、`KBTENTR0`、`KBTIDL00`、`KBTSCH00`、`KBTHD000`、`KBTTCI00` 不能用于判定这些阶段未执行。

R91 的旧 marker 位于 `args+0xb98..0xbc0`，正好对应 external window 相对偏移 `0x98..0xc0`，其边界结论仍有效。R92/R93 run、raw 和失败/混合 sequence 保留，但相关新增 marker 裁决标为 `UNVERIFIED` 并由本条 supersede。R94 修正版将 marker 放到 `args+0xbc8/+0xbd0/+0xbd8/+0xbe0/+0xbe8/+0xbf0`，并要求 gate 逐项核对 linked source offset、probe manifest PA/size 和 preclear 几何。


## 2026-11-23: R326 R94 corrected thread cursor boundary

R94 corrects the R92/R93 offset defect. Kernel `b9992598c9ae717dc36173a5f8642252c9ef9ceb6ca7d15dd478081aa880bee6`; boot `d6ad8238d1f13791bcb33d86fe191d414970725b0a44c7bbf97132d6e1a375de`; regular probe `0b66c4551ece493d63696c138ee01bbea59a2acb19ad843cf08ee58423c5c925`; clear probe `2cd7b970631b732274a51cc86bc1b94e919cfa4023c17c724992fdd34721c5d5`.

Accepted run: `reboot-checkpoints/r326-r94-corrected-thread-cursor-paired-run-20261123-47/`. Raw SHA-256: preclear `1fa34fdd5bd9baa071cf9c2e3872e169821972e40dfb932d03875175c50e8397`, baseline `b9e643fea98ff92912a267ef802898b2625711058536636d38715e61e0dfc523`, candidate `cfb368610b6e7d6abf818b8cf4d0d0badba269915de439593a9f98e809abfa68`, final `caaba9407e6035a5de8b62722672e9f2bdbed0fd8e3d778e03aa23a9d51842b0`.

Final fresh external record contains `KTHROK00`, `KBTENTR0`, `KBTIDL00`, `KBTSCH00`, `KBTHD000`, and `KBTTCI00` at relative offsets `0xc8..0xf0`. This proves the KERN_SUCCESS branch, kernel_bootstrap_thread entry, idle-thread creation return, sched_startup return, thread_daemon_init return, and thread_call_initialize return.


## 2026-11-23: R326 R95 thread-service boundary

R95 expanded the external record to 512 bytes so marker writes remain inside the readback window. Kernel `c3131ea5ada5102ce2c1b05c8be5286d5bdd788b71798ad4617f01a038c7c87d`; boot `926a4dbac051889dea964e1f88e0860ae4c75bebff8a5b422d132635647884e9`; regular probe `d1fa2019f6fed6af6b2e265db4dc761d2d5fb81055e74ad89bb433cd4fa65565`; clear probe `606ba7ee5d6a11d2a3c4e386f54e763afa3e595e7a447efac3b2020e56b0abd6`.

Accepted run: `reboot-checkpoints/r326-r95-thread-service-cursor-paired-run-20261123-55/`. Raw SHA-256: preclear `151311b2e1d1e8281e79ef33f279e3e6aaf01ec478d3e09183f8903be7809af8`, baseline `f360b1e1ac469228a4245450ca9514137744721949bd5d0db8e41d4fa3768091`, candidate `97d321f2b57e0158574c75bce56d9512bf36af9c2f5ea5633385cc537cd8b2b4`, final `a2fba487b302198f6d317970b4947d476b2d0591fa64cf73065e5a1cffc2144f`.

Final fresh external data contains `KBTBIND0`, `KBTIPC00`, `KBTMAP00`, `KBTCLK00`, and `KBTDEV00` at relative offsets `0xf8..0x118`. This proves returns from thread_bind, ipc_thread_call_init, mapping_adjust, clock_service_create, and device_service_create.


## 2026-11-23: R326 R96 bootstrap-services boundary

R96 kernel `81e5dafe3d5edcd7517cabb90de044554add2e3e8febd1123769babaf07a7f34`; boot `6e3a9f889cddbde1060b0c4b84777d4aea434fc495940edae1b357cebd7da96e`; regular probe `b82f289960b8f5c1a5c47e4b370c49cc0524909f4692b76487a6cd2d3b72549e`; clear probe `14949948f59383eec325da9b21effdbaec264bbd2d32cb20ed8a54e2f9d8c41b`.

Accepted run: `reboot-checkpoints/r326-r96-bootstrap-services-paired-run-20261123-62/`. Raw SHA-256: preclear `303ca17ac5e9daa12a5316aa894a56bf450f2c483e69d868b9ccfe42c7479b75`, baseline `58e62179158e43fe8c266a7acde82bca6d8b8488c666be3fe1cd42444054eadb`, candidate `325f437b46facfc365ce1e13d18501eeafef22fafe0faf049f0d3651f2034a8e`, final `e5fb9a8e1d7e5a86dbcfaf510395d4adb57211eb222d9fdf211d336c670a7f74`.

Final fresh external markers prove returns through `ktrace_init`, `bsd_early_init`, and `PE_init_iokit`; `KBTMAC00`, `KBTSFI00`, and `KBTPOST0` were not yet present.


## 2026-11-23: R326 R97 post-policy boundary

R97 kernel `06a1af85b9b5d1570937669481a6a60ff992b9dcffe48501ff2f0a6ce5b92a39`; boot `26873d11ea2c54abb66b01abe0be35c8822f304112a35e961b696c07a845239c`; regular probe `d8c8d681940040ff53174f6ac864084a899000cf93b2cd50b802ef7f5c5fcc6e`; clear probe `5b0b6468254f4a431a32d217c3505ac426b41988e6b407483eae552231c2ee9d`.

Accepted run `reboot-checkpoints/r326-r97-post-policy-paired-run-20261123-69/`: preclear `ae6801d7c2f2891ad823fc1ffc916bed670c3d501da9eac42cf2b3cbbd479564`, baseline `4adc4c0c7d5c9290577edd219dac1a4c6c08ade1a335b5ce7a5a3f6ee1826af0`, candidate `00704ef3a3deb326d922c048c26df368d5267259bed03d15cbb370d3475bc6ad`, final `d9e7659b9f8843bfe25ff3d5fcd993d3599eac3b1e454c4326b9976b984a4e04`.

Final has no `KBTMAC00`, `KBTSFI00`, or `KBTPOST0`; boundary remains before or inside `mac_policy_initmach`.


## 2026-11-23: R98 mac-policy entry cursor queued

R98 adds `KBTMACEN` immediately before `mac_policy_initmach` at args `+0xc48`, which maps to relative external offset `0x148` in the 512-byte record. The source-to-manifest marker gate passed. Kernel build is complete with SHA-256 `f06d882180c064fb2ab781f91853613e812fde165cbfa1cabc4d03dc1838ad70`; package/probe and paired RAM-only capture remain queued.


## 2026-11-23: R326 R98 mac-policy entry boundary

R98 kernel `f06d882180c064fb2ab781f91853613e812fde165cbfa1cabc4d03dc1838ad70`; boot `45bc744f0f9010c4bfac06ff1b760350bcfae3fdf6cffa67975e16d1479db079`; regular probe `440a60dbff5493d019074c9242d80fa2faeb7ba2677973640b1957a984471b52`; clear probe `23565b5bec0fe22bdf12fbc71b0faf01967908d516dbfcbcc69c23f12df5351f`.

Accepted run `reboot-checkpoints/r326-r98-policy-entry-paired-run-20261123-76/`: preclear `dd7ad00688b2cc536728bf371828724b597ddab0d8332861221959078ff08ed5`, baseline `0ab3ec31b0f1c8b1d6a855d0cea255bcfc3f1b64fcb8020e0e87fa40ea1062d6`, candidate `91bfdd0713b96f178fc79c3dc8c4e8bb21eb11d9100e80659918c9585043e8db`, final `c9f7067469991cab29510b73f9817c63f9eac3a9848b91f184db029dc2278b9c`.

The corrected entry marker `KBTMACEN` at external relative offset `0x148` is absent, and `KBTMAC00` is also absent. Therefore the current evidence stops before entry to `mac_policy_initmach`; no return or failure cause is inferred.


## 2026-11-23: R99 commpage-policy bracket build

R99 corrected patch context from the R97 staged source after the first R99 apply failed against an R95 context. The corrected R99 patch SHA-256 is `96fa71a3514a568c0b4fb8e44f3b10c3bf51717e767f40ebfd843a557657d367`. Build completed with kernel SHA-256 `b7dbac43a61e2445097b30e99dccb7a24d7dccecabcb3875c68f52b1d3466ddf`. Package/probe and device capture remain pending.


## 2026-11-23: R326 R99 commpage boundary

R99 kernel `b7dbac43a61e2445097b30e99dccb7a24d7dccecabcb3875c68f52b1d3466ddf`; boot `dcc2e19d5b39a3aea1000d9e9b7f757a02d6bae4caf860d088246910d38f0f09`; regular probe `220339e132f47a0b797c39972a3d828581942d377497392552af41ccddcbf05e`; clear probe `58d709e31ed90ab0d2a12374c2850e587be1bdd30a12112cddda161162d62e33`.

Accepted run `reboot-checkpoints/r326-r99-commpage-policy-paired-run-20261123-85/`: preclear `e0b6e9ad389a6e08b87287aa1be2b4b248dbed2092897425967a03b679aeba04`, baseline `31c8c0563b9199864884b9fec49510bd050bd7c18667d6dd016e293af1a88bd1`, candidate `afeb1c951ebabfffccfed7c2c43b044649951a86135e9339e5132830eea514fd`, final `5226e946be57d24285863ab312ffd635370c47048871b7f74a1e969fe61bb452`.

Final fresh data contains `KBTCPRE0` after `vm_shared_region_init`; `KBTCPAG0`, `KBTCTXT0`, `KBTMACE0`, and `KBTMAC00` are absent.


## 2026-11-23: R100 vm_commpage entry/return build

R100 adds `KBTCEN00` before and `KBTCRE00` after `vm_commpage_init` using the existing 512-byte external window. The linked kernel SHA-256 is `49cbe12f3c6871edab319825e35d3734411e253a9b2df812c58f8ca607a95dd7`. Package/probe and paired capture remain pending.


## 2026-11-23: R326 R100 vm_commpage boundary

R100 kernel `49cbe12f3c6871edab319825e35d3734411e253a9b2df812c58f8ca607a95dd7`; boot `9c3ce583b7a13d5a38fa145695ded27616e14ea9bd2c403ce14a2b79a62e2761`; regular probe `eb33027f66e537d2c4b26ede62503891c835e825114e5ba14279069b75e0b355`; clear probe `d457dae730501072f3aeccec0496638f64d05364b68873720d6d1592ec18a3de`.

Accepted run `reboot-checkpoints/r326-r100-commpage-entry-paired-run-20261123-92/`: preclear `2895ba5f9e2aa057d9a9b2f60f5aa7d24e83d5e6811920c6ec7a79dd79dc20dc`, baseline `0a15f9889d16e71c8ccc8b99d7153c6ab241c1266ccea0e3d13f3cc972659823`, candidate `72a3c6a667356bc5cabfd6e51310e2b4597e5dad70f91e4abc1fa8a36ff1c651`, final `e455d392f8a20b1d8b2279fa4ef795ed2902992693523973c64bf8d1fa609b7d`.

Final has `KBTCEN00` immediately before `vm_commpage_init` and `KBTCPRE0` after `vm_shared_region_init`; `KBTCRE00`, `KBTCPAG0`, `KBTCTXT0`, and mac-policy markers are absent.


## 2026-11-23: R101 commpage internal build

R101 corrected patch order (`R91→R94→R95→R97→R99→R100→R101`) and linked successfully. Kernel SHA-256 `3478dc6c5bd119028d8b63422f6a89d4814fd0ccd5887fa052470c5821c5ef53`. It adds `KBTCINT0` at vm_commpage_init body entry and `KBTCPOP0` after commpage_populate; package/probe/device capture pending.


## 2026-11-23: R326 R101 vm_commpage internal boundary

R101 kernel `3478dc6c5bd119028d8b63422f6a89d4814fd0ccd5887fa052470c5821c5ef53`; boot `af71445375b2c6c4748d956a1a344adcbcb0c07d047f9adab6d323deacd4ad49`; regular probe `804a31220385a57e1c249b53c19ddb74a5e50ea240c9ea741dced8eb92b7c765`; clear probe `1ea6335f31cf1134b7836e7397246a7e5c117f868e1e8e63b3d084a6305f3c43`.

Accepted run `reboot-checkpoints/r326-r101-commpage-internal-paired-run-20261123-101/`: preclear `a342c35649bcdbbbe16342ae8f95dfeaf44b8ae432b02e0381b144d09e2fa279`, baseline `2a18132dc4d85ea9504e6f92a2aabb42492e55f7305a42d6f11591eb7deddfe8`, candidate `2d08bfad11b84013b3255df2cdd634c931f72f9aaddcec35bf58948daa93621b`, final `0ba8e8661305a40f35e627c0758c90e44ba80ce9b17c30677af4f1a9694bc502`.

Final contains `KBTCINT0`, but not `KBTCPOP0`; entry into `vm_commpage_init()` is fresh, while `commpage_populate()` return remains unproven.


## 2026-11-23: R102 commpage_populate internal build

R102 adds `KBTCPEN0` at `commpage_populate` entry and `KBTCPR00` after its final initialization writes. Kernel SHA-256 `e10507ded452e690c168ec65ee34e7427444278fae9bb7c31c423bdf4f364053`; package/probe and paired capture remain pending.


## 2026-11-23: R326 R102 commpage_populate boundary

R102 kernel `e10507ded452e690c168ec65ee34e7427444278fae9bb7c31c423bdf4f364053`; boot `3f732de4040b5595c9191c9fff9c18da154dc6c2d5bafd91214248ff95172546`; regular probe `3452e9e1a55671248e08f03dc14a7eb849093a0ed6694d5aa813baf3ce9aa718`; clear probe `9fc652a141b8aa5016bda62af6d81384bdb1383d04626035e94a9e43ac28760d`.

Accepted run `reboot-checkpoints/r326-r102-commpage-populate-paired-run-20261123-108/`: preclear `2cf14e4279ffb6548a99ea96d7da1264be516f8cc7155cf3a8222cbd509952f6`, baseline `863c0efd17dfec71bf1354d960e5aeabba0ef2d03707cb9c41207d0a3545ad06`, candidate `1785efbcd1c3552e12aeb82bc980bcbce06bd3875b6376eb9e092140489f9121`, final `8c3853b84c2985fad64305e91653139136507c46145b339b2109b095f6ce48a7`.

Final contains `KBTCPEN0` and `KBTCPR00`; `vm_commpage_init()` returned.


## 2026-11-23: R326 R103 commpage-text boundary

R103 kernel `c4b5f0b3c7df36c088ece2f7473267a6abcc9d5e4e9e980dd6bdefdd9b2e35c9`; boot `458960aae1e15bcc8b3f5ef2d897520935b5e45d5bd17b90e064b5c008da9887`; regular probe `910b9561ea62e9e0ab4ce6ffe0ad9b4079e54479ba2fdfd84bae57968a4fa814`; clear probe `3048aca3e7305e54abc7dfb13518dab3edb5bc94b1dc7f8b7b3de90d374c677e`.

Accepted run `reboot-checkpoints/r326-r103-commpage-text-paired-run-20261123-117/`: preclear `b70d8112e75be1e3d79fef079bab8d2df41979b0104673d3234839d508e8fb75`, baseline `28dac486097ec2a0ab70c86af8417e4a3aadd933aa899eefdf74b3b631d72e0f`, candidate `09f3f1be1d64fa58b3561261c08c1394462d6c50786844fd83e7d261fa5e65ec`, final `d526a346f4853c98e2289231302a0c1b636c6c2b5756f105063338700ee07336`.

Final fresh record contains `KBTCTEN0` and `KBTCTRE0`; `vm_commpage_text_init()` returned.


## 2026-11-23: R326 R104 post-bootstrap boundary

R104 kernel `4ba2d7fcbe7f65aa8bf0f296ad6176c769b9ccc90507a186fd0d238dabeb91d9`; boot `91a840bb9c054e0617fc767ae12c074b9385eff15a456e456041514409a6bfda`; probes `deab038f0d79f39bca8215d3e4004e42380129124ab2e5a56d0fbd789467fb2a` and `17840140af114622c73b8d75c943e58fbce66724414e0d97587016042acd0810`.

Accepted run `reboot-checkpoints/r326-r104-post-bootstrap-paired-run-20261123-126/`: preclear `e9b4da508dab570ac9ab94ddfb72dd0e3e4d862ae5a9cfbd3a839531098da06b`, baseline `6cc2c88fe26ca6b51f8c993a588005f11c28e3b8d24e01c8d6b0843e5739a3d3`, candidate `e3ea3a6b3d8005dd233755e731567352669843a55bcd2238c77713678f2b7bb8`, final `755ac573f12b641b64f5586272c652a8146aeb7caa582a935359bd43752f6b8c`.

Final includes `KBTCEN00`, `KBTCPRE0`, and `KBTCINT0`; `KBTMACE1` is absent. Boundary remains before `mac_policy_initmach`.

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

R120 was stopped before device use. Its next step is gated by two independent offline contracts: startup marker ownership repair and RAM evidence reconciliation. The R119 correction is now authoritative: the effective R119 source removed `CCPUNEN0`, so `MLMAXEN0` and `MLMAXRT0` are valid same-run witnesses; the cf8 value is `CPCNUR00`, despite the stale `CPCRUN00` source comment. R120b remains only an unbuilt patch candidate until a manifest binds its carrier window.

The staged runtime DTB `/Users/lingion_k/unixnu-research/evidence/y35a-20261102/lk2nd-runtime.dtb` has SHA-256 `36555c5e66b4a09cd38506706b0a301c2c8b8d6b883de51c51b89971825e9709` and reports two 1 GiB memory ranges totaling 2 GiB with an empty FDT reserve map. This is prior-loader evidence, not the final candidate DT. The offline maximum-memory candidate is internally consistent at `physBase=0xa0004000`, `memSize=0x5fe00000`, and `end=0xffe04000`; its verifier reports `ok=true`, while the recorded `/proc/iomem` source remains a summary because the original dump is absent. No new device run is allowed until the marker gate and final DT/bootargs binding are both green.

## 2026-11-23: R121/R122 maximum-memory startup boundary

R121 maximum-memory paired run completed with kernel `3fb0e8311dc2f275724aaad17fac880094cb6052b72966483911df6bb0d20366`, boot `06a049d0290ec2804a8b9957bc1b52092a8bd6ae23473e384d639a8094743f51`, final raw `01b4a0c7d5d69b7e22ca015c3b9993c15c53a73d227517a0fd1649c04fb7906c`. Fresh final contains all seven gap cursors through `PRERAND0`; `RAND0010` is absent. The boundary is after `arm_vm_prot_finalize()` and before return from the first `read_random()` call.

R122 added cursors inside `read_random()` and completed with kernel `c7b312feece848994716bf1ed14a3069be8b8baf2cb518038536d482734ed719`, boot `e4dc7483984eaae3623fb2e9575274fe46a8d9a0f67e16d267fd169ecbd88819`, final raw `8373c53baa32a3b361fbdb6f8776f2ed9eea37100efdd64e27d4076eb640bb4f`. Fresh final contains `RNDENTR0` but not `RNDLOCK0`, `RNDGEN00`, or `RNDRETN0`; the boundary is at or inside `lck_mtx_lock(prng.lock.mutex)`. Both runs returned to fastboot without persistent writes.

## 2026-11-23: R123/R124/R126 lock boundary

R123 final `a75e99749a265c299d455ba45c06ef349f0ddf06dcc016e9e37a43c6943c9613` contains `RNDENTR0` only. R124 final `0b618577727a0de265f31e2a1351f39e0f7b3e53da215349326496b3d43ea4f2` contains `RNDENTR0` and `RNDBEFL0`, but not `RNDLOCK0`. R126 final uses kernel `f5c78154a9e6e4ea5fd55f670a25373bb8ddaa247ff469d2a5def07a0624f806` and contains `RNDLKEN0`, but not `RNDLOCK0` or `RNDLCNT0`. The measured boundary is inside `lck_mtx_lock()` after function entry and before its post-call return cursor. All runs were RAM-only, returned fastboot, and preserved zero preclear/baseline external windows. R127 is building offline to split the internal lock path.

## 2026-11-23: R130 PRNG callsite boundary

R130 completed a fresh maximum-memory RAM-only paired run on `efff9d92` and returned to fastboot with `persistent_writes=false`. Kernel `05875efe3e55b137338adc7f352b345d41cc445058a2427139ae09172a46ee87`; boot `9c02fe618a1c7e08be295df9556e5673ea78e8a79edfea81f09a38bc8b06fc7d`; regular probe `1d83aa76a9e88cf3273af279762303b8d7464122724331da6e3dda4dc9eb5f83`; clear probe `c867aae316daaa75cd8be983e1fe051103e898d0638c1248f9135cc1b5bb488d`. Raw SHA-256: preclear `ed41f1bc2af66f4ce67ba1a8210e2a1a9ba116e40fd16d3946d363677d7b3f46`, baseline `34f2d3b0ab435650f87df9bed681bd331ea2581458a636112b68625b294e04e0`, candidate `cda9af16c4eff0bc14f61eefccf84aef552dcc71f1ca0fb849968b5e32f76cb2`, final `8a93155eb9ed7281fce222862c701a166af94cb2fc0a865767f563bb816189e5`.

Preclear and baseline external windows are zero and final has fresh count 15 with nonzero postcopy checksum. Final contains the prior PRNG lock-path byte markers but no `PRNCALL0`, `PRNGEN00`, or `PRNGENRT`. The current boundary is after the observed lock path and before the R130 `read_random()` callsite marker; entry into `prng_generate()` remains unconfirmed. Full adjudication: `reboot-checkpoints/r326-r130-prng-callsite-paired-run-20261123-01/adjudication-r130.md`.

## 2026-11-23: R131 post-lock boundary

R131 completed a fresh maximum-memory RAM-only paired run and returned to fastboot. Kernel `1a4a130badbc51e51f67b56b5e9d6ad718b35177bba2405ac57ca84ca696508d`; boot `6cb87005dd406463c46fecd69a8d8c019547058582f8fedb73af0000a173a85c`; regular probe `0e35f459a04551a6749f13b8f8460910a1e6396b6d7388c71408a1a2980b045a`; clear probe `50e7e4b4509655a01272d28ee75047cdfe2e0148b0810893271d79f231d4b286`. Raw SHA-256: preclear `6bbe1898c50d6f148494f0f75952f8bb144ad7e4965e5078d734b6e126ed5587`, baseline `0494465cf0904e8338fd750f88b4860d1213ae3a26e32747429fb72a0b91cc56`, candidate `415281885d96a578c6cb828392d11d24e2b208e97c7d6742f2a425afeaa2846a`, final `4adaa5e00b85c83d57293b3f5307811a2c269a094ca9136473316785a9fb7cf7`.

Final fresh external data contains `RNDACQ00` and prior lock-path markers but not `RNDLOOP0`, `PRNARM00`, `PRNCALL0`, `PRNGEN00`, or `PRNGENRT`. Boundary: after the lock implementation acquisition return witness and before the first caller-side marker/write after `lck_mtx_lock()` returns. Full adjudication: `reboot-checkpoints/r326-r131-prng-bracket-paired-run-20261123-01/adjudication-r131.md`.

## 2026-11-23: R132 direct-after-lock boundary

R132 completed a fresh maximum-memory paired run and returned to fastboot. Kernel `fef22a728f386244a47cdc0ae3109c41e7cb974a3d15e4403c6696d1eea5151c`; boot `883311669619009822be3a5ee3d4206d87ced033f026e41c026daeb39be56749`; final raw `4fa483ff31aaac199110e9d6b09597d3045094a25114df26433e48c85ab19707`. The 16-record direct scalar after `lck_mtx_lock()` remains zero in final, while fresh external data contains `RNDACQ00` and lacks caller-side `RNDLOCK0`, `RNDLOOP0`, `PRNARM00`, `PRNCALL0`, `PRNGEN00`, and `PRNGENRT`. Retrospective correction: this build's effective source leaves `prng_fns` null and does not call `register_and_init_prng()` before the observed path. `RNDACQ00` is emitted for any successful mutex acquisition after `lck_mtx_verify()`, so it does not identify the `read_random()` lock. Do not use this run to locate a PRNG lock boundary. R134b supersedes that attribution. Full adjudication: `reboot-checkpoints/r326-r132-direct-after-lock-paired-run-20261123-01/adjudication-r132.md`.

## 2026-11-23: R134b PRNG bootstrap and first read_random boundary

R134b completed a fresh maximum-memory RAM-only paired run and returned fastboot with `persistent_writes=false`. Kernel `6a5a20f7c420bae5fc6c4f0039e3756a10a5f4e33fbc5759c1970a82f62f8a59`; boot `ec566c128ee655f3da4babe98bdfc90c21ccc19e71abd0e160924d2f0dc52f25`; regular probe `38d951199d5071112936375d3754a8486442a7f8e5fc32b289485aebb53ae471`; clear probe `efb99f7d7fbfba7f4846585857366b373bbb5f7181ca4c1b1c53149fa1d0e285`. Raw SHA-256: preclear `0e99060112f9fe1190f02bbe230881f472452d9012eb20950a4d8a27412b1bcc`, baseline `14db665e584da712545b5061c9059df6d58ea4fbad8b7b63f97a4458fc4f6ad8`, candidate `3bfac18bd43d25a7c1a6239784ceee37a3855d8f33637d441888456e3fc1d067`, final `136a069733bd0ccc74eb702c17b7893306b4eb165be7f31b3cb71fb04b8f8599`.

Final fresh fields prove bootstrap entered/returned, registration started/completed, phase 3, and nonzero mutex `0xfffffff09c0ee150`; final also contains `PRNCALL0`, `PRNGEN00`, `PRNGENRT`, `RNDGEN00`, `RNDRETN0`. `RAND0010` after the first `read_random(&vm_kernel_addrperm, ...)` is absent. At this stage, whether the output store completed remained unresolved. R135 supersedes that uncertainty by reading a nonzero `_vm_kernel_addrperm` from its symbol-bound physical window against zeroed preclear and baseline captures. R130/R131/R132 lock attribution is superseded: their effective source chain lacked `register_and_init_prng()`. Full adjudication: `reboot-checkpoints/r326b-prng-bootstrap-order-paired-run-20261123-02/adjudication-r134b.md`.

## 2026-11-23: R135 corrected boundary

R135 completed a fresh maximum-memory RAM-only pair on `efff9d92` and returned fastboot. Final raw `2b16acbb57d606db7777f05bbe99780569f64f48face343d4538d2afea657016`; `_vm_kernel_addrperm` at symbol-bound PA `0xa0731840` changed from preclear/baseline zero to `0xfc4a85a6fa47ab11`. This confirms the first `read_random()` output store completed. Decoder correction: `RAND0010`–`RAND0050` comments do not match their emitted little-endian codewords; all actual bytes `010DNAR0`…`050DNAR0` are present. Final also contains actual BSD callsite/body-entry codewords `BDBCALL0`, `DBSENTR0`, `BDSTEN0\0`; the next `BSDUTEN0` codeword `BTDBSUT0` at args+0xe18 is absent. Current boundary: inside `bsd_init()` after entry and before `bsd_utaskbootstrap()` callsite; not launchd or iOS. Full adjudication: `reboot-checkpoints/r326b-first-random-output-paired-run-20261123-01/adjudication-r135.md`.

## 2026-11-23: R136 BSD-init stage boundary

R136 completed a fresh maximum-memory RAM-only paired run on `efff9d92`, returned fastboot, `persistent_writes=false`. Kernel `d592dae12b192637cda3dd7453c5200714b74c1129f8609cc113c402d7656b51`; boot `4dab5ba90abfcdefe7e20e07794816c6efe060255fa0c7f197bbeeb74189cb31`; regular probe `9a482a21a29832621126521696f1603952596f286b73563fc27566e18ac3f47b`; clear probe `39e893af940dadd58a8f25de18feda2765bdac14453134e3328c965123e9880a`. Raw SHA-256: preclear `f79f06e458a9d374b6a43f5b90c8716e5f024bc61c64d20fe464e099f5a29c51`, baseline `bd99b9682afe3129e1ce5d8af8a742156c235ad8f1587cee0441b3cf7c3ed774`, candidate `75034562baae0a8eb9224f6caa67e978488237cd1f4bcbfc5fb80e12074d88d3`, final `995e9891f4157cc75cbea2af0f81fd074ddeda4e71c30d75c6c43f7270b61f4d`.

Final contains the R136 cursors through `BUFRET00` (bsd_bufferinit returned); `IOKRET00` after `IOKitInitializeTime` is absent. Boundary: after bsd_bufferinit and before a recorded IOKitInitializeTime return; no pre-call IOKit cursor, so the exact call interval remains unresolved. Offline memory/source/linked-marker/probe gates passed. Full adjudication: `reboot-checkpoints/r326b-bsd-init-ladder-paired-run-20261123-01/adjudication-r136.md`.

## 2026-11-23: R137 IOKit cursor offline candidate

R137 offline candidate is bound to kernel `a24a176d09571016bfa608c681c4a0058fa3a319a54a55ecd1c124c0a3afac77`, package-06 manifest `94d807a7e9dee0577b07bf65a2c42701d1cad99d533c4bf8aa958125019d3905`, boot `593d64cae53fc82034cc7c9b5ac9586ef9e47ca33595e367b9c314193fcbeabb`, regular-03 `82a94cbcee24c22f49f2738a4064310299e7dd92f2b821e2b023b150678e3417` / manifest `7f9540d6772da3948cab00c0d09c8f76d2ba72f3c1bbc55d49a0229bf98e03f9`, and clear-06 `a9fdc56a1b6cf0e56b04ace6ac8a3636b3e0a96ff434537aafdc2562ccd3984a` / manifest `c039afaad4a2896d0b1ad4560f79afe5f7c366928e28e03fefc241937f76179f`.

Source ownership is 132/132 with contract SHA `a35f083e434c6a609bcf7fa18ae942739e92f277e4bde882e4252796310db61e`; the six IOKit markers are exact-once in the linked Mach-O. Capture, transport and phase gates pass for both probes. The global 132-marker linked inventory is incomplete (113 linked calls; 19 source writers absent from this ARM64 link) and remains a limitation. No device run has occurred; `device_run_allowed=false`.

## 2026-11-23: R137 IOKit wait paired-run adjudication

R137 paired RAM-only MVE completed on `efff9d92 / lk2nd-msm8916`; device returned to fastboot and `persistent_writes=false`. The exact binding was package-06, regular-03 and clear-07; package-02/package-05 and clear-06 were excluded. Kernel `a24a176d09571016bfa608c681c4a0058fa3a319a54a55ecd1c124c0a3afac77`; boot `593d64cae53fc82034cc7c9b5ac9586ef9e47ca33595e367b9c314193fcbeabb`; regular probe `82a94cbcee24c22f49f2738a4064310299e7dd92f2b821e2b023b150678e3417`; clear probe `384a24e1ffde9e4930cb83cac40589926bec366f67354b2ee3cfa7d594c0332d`.

Raw SHA-256: preclear `c19dd0fd38a388193898b285822dfc3e4ec505276493d56d150cf836661ceeff`; baseline `7f817e4046399f6dd7debab1bd900250e01dd1e7f9a41ce020e4368520d5e935`; candidate `7a7a3d47c60edd07330b3b15b7808827d993bde8f51056aacbbd790b666427f3`; final `b9eb1a520f9e7edf4fae79a4f5e7af7711efd1a03fd83bfa3e71f255ac0023d8`. Preclear and baseline carrier/provider targets were zero; final completed 21 records with nonzero carrier checksum and provider fields matching the bootstrap contract.

Fresh final carrier contains `IOKCALL0`, `IOKENTR0`, `IOKWAIT0`; `IOKRETN0`, `IOKCLAR0`, and `IOKRET00` are absent. Confirmed boundary: entered `IOKitInitializeTime()` and reached the IORTC wait callsite; wait return, service-found versus timeout, calendar initialization and outer return remain unverified. No launchd, root mount, storage, display, touch or SpringBoard evidence exists. Full adjudication: `reboot-checkpoints/r326b-iokit-cursor-paired-run-20261123-01/adjudication-r137.json`.

## 2026-11-23: R138c IOKit wait-result offline candidate

R138b was rejected before device use: its two conditional branch constants decoded as `KIOKFND0` and `KIOKTMO0`, contradicting the source aliases. R138c applies codeword patch `6d65dbe3203ce0aee03ac2b3a88340baa755b6d87a900cd50c13f256df5d35d4` after R138b and links the corrected eight-marker contract. Kernel SHA-256 is `067f570085cec9c8857078f681514fda5941ed5da5f9f42b8e63f737a387c383`; package manifest/boot are `1101b79d06cb2195513d0631d67ecee2cb9c5cdc45b091e7cda2b7cebc72ee37` / `9df283abda151278574e3a6c79a2e7d9df18e116e92d0d08abe664f8f372d17c`; regular probe image/manifest are `d703af803bf73ba82a282a053f05c1d171b8c3e8407f17ee9c8c033d6bf2805d` / `c2a13c4d4c330dbb6471c97549b96aa056ce1a49e77d1d694a0064b68ab4a7c6`; clear probe image/manifest are `2f9a4817a2191909407c151efc8d1a364782f1bc6afabf0560a0da49a5b711b1` / `96f7c96f2008f6ac41c23679ae56e79aa2dfad3cafeb3d15d55cb67ddf0b5872`. Offline gate SHA is `f097f19887ef6003c9b9f5ab52fb72886c99d490646f379e7a024703425ed214`; plan SHA is `8557aea979f919714a2805826a2c2ae0a4389bac06b75b5ff5b407f407e9249c`.

The six capture/transport/phase gates and corrected linked marker gate passed. The paired runner has a one-run, 600-second monotonic deadline and binds all package/probe/manifest/gate hashes before acquiring the shared lock. No R138c device run has started yet; no new downstream claim is made. Full partition backup and EDL/firehose recovery remain unverified.

## 2026-11-23: R138c paired runtime adjudication

R138c completed one paired RAM-only sequence on `efff9d92 / lk2nd-msm8916`, returned to fastboot, and used `persistent_writes=false`. Inputs were bound to kernel `067f570085cec9c8857078f681514fda5941ed5da5f9f42b8e63f737a387c383`, boot `9df283abda151278574e3a6c79a2e7d9df18e116e92d0d08abe664f8f372d17c`, regular probe `d703af803bf73ba82a282a053f05c1d171b8c3e8407f17ee9c8c033d6bf2805d`, and clear probe `2f9a4817a2191909407c151efc8d1a364782f1bc6afabf0560a0da49a5b711b1`.

Raw SHA-256: preclear `8e84c61ec3a53ba541ea9f9592b3c1fba283f6eaa14c450f002ec069da5f05e7`, baseline `f7fb1afb5435c7288dc346d902d263d46470bf8d5a679ffd39540de30dfc9f2f`, candidate `539d17187573e930fbd25e3c31cd5b004629e5136bd490bfd36c1c254cd3c4df`, final `44824a20389e75aa9a16b9a3261007735f508733b43f696349d5e2b4ff9d3e85`. Fresh final external data contains `IOKCALL0`, `IOKENTR0`, and `IOKWAIT0`; it lacks `IOKFND00`, `IOKTMO00`, `IOKRETN0`, `IOKCLAR0`, and `IOKRET00`. Preclear/baseline external data is zero; final copy count is 21 and OR checksum is nonzero.

The first runner summary is preserved as a decoder failure because it used report offset `0x4e0` as the base for markers whose source offsets are relative to `native_phase_args`. The corrected mapping is `external_index = args_offset - 0xb00`; supplemental adjudication is `reboot-checkpoints/r326b-iokit-wait-result-input-20261123-14/adjudication-r138c.json` SHA-256 `f741f7d9ed4b67169ca4831cb41316a7bbfec659d847597f128afe6956296824`.

CONFIRMED: reached `IOKitInitializeTime()` and the IORTC wait callsite. UNVERIFIED: return from `waitForService`, service-found versus timeout, calendar initialization, outer IOKit return. Next is an offline-linked bracket inside `IOService::waitForMatchingService`; no launchd/root/UI claim.

## 2026-11-24: R139d waitmatching offline candidate

R139d corrects two R139 build issues before device use: it declares the helper in `IOService.cpp` with `extern "C"`, and separates `IOKWLEX0` loop exit from `IOKWSRT0` sleep return. The final linked contract proves `IOKWSEN0` entry, `IOKWSPR0` pre-sleep, `IOKWSRT0` after both sleep callsites, and `IOKWLEX0` after the post-sleep join. Kernel SHA-256 is `373996f1ef2dc45f596df76e23fb036a364442b1f2023d35d38fd72b55625480`; package/boot are `91b5efd6c10c4393d566728a2cf00ea8ef48424107bc6d7f313757f1896d6b0d` / `4f7794d4eb5069c2ea6aef5d27c1f55ad1a581ee1a04eabddcfde1eeb0dbca00`; regular/clear probes are `2a8d66087c66e54be7e23be37fadee08286d602640ee5d27c20b27ef0b118cf9` / `66d44bfb1ed12379002f00fb9a9cd6651ab20ed45b7df3811b50b17e7f96430e`.

The current package/probe bindings use the new `args_physical=0xa0ba8000` geometry. All capture, transport and phase gates pass; offline gate SHA is `d3299640082ce09b9d4df31af12bb42e5545a4c430411be9ecc302727d75f178`; plan SHA is `7f2b6397cafbc690b70d4e9136c5f529546c7e853e3c1cc921091a85a21d7cb5`. No R139d device run has started.

## 2026-11-24: R139d paired runtime adjudication

R139d used the local authority tree and local device lock. The exact package/probe set completed one RAM-only paired run on `efff9d92`, returned to `lk2nd-msm8916` fastboot, and used `persistent_writes=false`. Kernel `373996f1ef2dc45f596df76e23fb036a364442b1f2023d35d38fd72b55625480`; boot `4f7794d4eb5069c2ea6aef5d27c1f55ad1a581ee1a04eabddcfde1eeb0dbca00`. Raw SHA-256: preclear `08c92eeb6e0d10e31d8ae5cb0624f2ca5966421fd91d39525763916dc61893d`; baseline `f4825b630750e23e27e34da56c6889ee914fc6b76f5cafcc1bb0184546f207ef`; candidate `2c4640a3c21ceead0dd926df1ad28c062984b4da03adc19a0379a36f7c97c62a`; final `5cd50c149b6f697d54141d62fa1e67da8fbcecdc5b523e831e597809f46ea31d`.

Fresh final contains `IOKWSEN0` and `IOKWSPR0`. It lacks `IOKWSRT0`, `IOKWLEX0`, `IOKFND00`, `IOKTMO00`, `IOKRETN0`, `IOKCLAR0`, and `IOKRET00`. This confirms waitForMatchingService entry and the pre-sleep path; sleep return and result remain unverified. Adjudication: `reboot-checkpoints/r326b-waitmatching-input-20261124-07/adjudication-r139d.json`.

The new active priority is the real R154/R159 AMFI closure. R154 reproducibly reaches launchd/dyld but fails policy dispatch with `ENOPOLICY=103`; R159 remains host-only `runtime_qualified=false`. No AMFI placeholder, allow-all policy, fake PPL, or fake TrustCache may be used.

## 2026-11-24: R159 real ABI closure audit

The active blocker is R154's direct `ENOPOLICY=103` after reaching launchd/dyld. A new host-only audit at `reboot-checkpoints/R159-real-abi-audit-20261124-01/` compared the pinned iOS 12 tree, the newer XNU ARM pmap implementation, and `native-y35a-pmap-trustcache-r159-legacy-only.patch`. It confirms the pinned tree lacks `pmap_cs.h`, AMFI headers, TrustCache runtime source, ARM pmap implementation and trustcache.c at the required paths. The R159 legacy patch only parses legacy v0/v1 TrustCache data, explicitly rejects signed Image4, returns a non-PPL state, and uses a private page list; it is not a real 16G102 security closure.

Audit markdown SHA-256 is `72192283f1d6ec16ea7fb746d46d9064479f3abaad86daab7cf92da1e8817667`; JSON SHA-256 is `bbfc90bc15d10739de22763606ff51a142cb724da22eb37c32080c115939e7f7`. R159 remains host-only and prohibited from device use. Next work is exact behavior closure and formal iOS 12.4 AMFI registration/dataflow; no minimac/allow-all/fake PPL/placeholder TrustCache.

## 2026-11-24: R159 original ABI binding replay

The repeatable original-kernelcache audit was rerun host-only and produced the same SHA-256 `0bfdfc85173ecac641de204c7f7fe0fc8ce4516fec896a2ffacc00ac163c8632`. Original 16G102 kernelcache SHA is `70e80388d42fe2376096bb6248073b0380dd87b85b1a792b36205ba60c722ce1`. It confirms eight unique pmap/PPL pointer bindings owned by CoreCrypto and AppleMobileFileIntegrity plus five AMFI indirect import thunks at slots `0xf48..0xf68`. This is static ownership evidence only; it does not prove policy registration or runtime security behavior.

## 2026-11-24: R159 AMFI registration path audit

Host-only source audit confirms the pinned XNU 4903 startup chain already assigns `load_security_extensions_function` in `libsa/bootstrap.cpp`, filters `AppleSecurityExtension=true` entries and calls `OSKext::loadKextWithIdentifier(..., allowDefer=false)`, then calls `mac_policy_init()` and later `mac_policy_initmach()`. The missing work is therefore prelink loader acceptance, exact security KEXT metadata/dependencies, real pmap/PPL bindings and registration dataflow; adding another startup initializer would not address the measured ENOPOLICY stop.

Audit JSON: `reboot-checkpoints/R159-real-abi-audit-20261124-01/R159-AMFI-registration-path-audit.json`. The next host gate must reject missing metadata, failed KEXT linkage, placeholder PPL/TrustCache and allow-all policy.

## 2026-11-24: R159 current host candidate regenerated

Using the restored local Xcode 14.3.1 tree and the exact legacy patch, the current host kernel rebuilt as `6d1f7a6c39c3098f5544d055e63b6c36d9cad112368516148c183e784e62e3d6`. The regenerated security graft candidate is `f55e7533f70dd1eb8fea172f30bd632a5739b015db04db7791b43402e5d4f643`; its plan has 799 bindings, zero missing/collisions/nulls. Static integrity, component relocation and loader metadata gates all pass. The builder's legacy phase verifier failed only on an unrelated R326 x9 diagnostic check; this is recorded separately and does not authorize the candidate. `runtime_qualified=false`; no package or device boot.

Current static audit: `reboot-checkpoints/R159-real-abi-audit-20261124-01/r159-current-static-audit.json`. Remaining gate is real security behavior: KEXT load/registration dataflow, CoreTrust/Image4 and PPL semantics.

## 2026-11-24: R159 registration readiness gate

A host readiness report now binds the current candidate to the pinned XNU loader path and the three prelink security roots. Static gates are green, but KEXT load execution, `mac_policy_register` dataflow, AMFI syscall success, Image4/CoreTrust validation and PPL semantics remain unproven. The report explicitly keeps `runtime_qualified=false` and prohibits packaging/booting this candidate as an AMFI fix.


## 2026-11-24: R159 AMFI registration dataflow static audit

SUPERSEDES: earlier R159 readiness wording that treated registration/dataflow as not yet statically traced. Runtime KEXT load, policy registration, syscall success, Image4/CoreTrust and PPL remain unverified.

Host-only audit: `reboot-checkpoints/R159-real-abi-audit-20261124-01/R159-AMFI-registration-dataflow-audit.md`, SHA-256 `2e4a6f752c3b2d246bcfd7b5a8d41eb24dabf6f4f0e92cd78bbf4d4cb6f7fb9f`; JSON `R159-AMFI-registration-dataflow-audit.json`, SHA-256 `1cdb380a46e5b01ae48bfdf703fe750aaa93ce06cc3d898072a5b7ae3247a09d`; verifier SHA-256 `0531a92ea6ee89abff9841d2e816ef2f5cc23798729edd211179638776c0cff1`.

The correctly mapped candidate AMFI `__TEXT_EXEC,__text` begins at VA `0xfffffff0081ee000`, parent file offset `0x105c000`, and matches `amfi-kext-text.bin` SHA-256 `87605287940cffff81ebe693096d1d97733cfa2e229f4ab3604265c44fad73f4`. In the candidate’s linked code, a method-table entry reaches an internal helper through two guards; if both pass, the helper builds policy `AMFI`, assigns `mpo_policy_syscall` at ops offset `0x3a8` (field 117) to function `0xfffffff0081f3ca4`, and calls stub `0xfffffff0081f4758`. GOT slot `0xfffffff008e1fed8` resolves to kernel `_mac_policy_register` at `0xfffffff0076c3e40`; a zero return branches to the success continuation and a nonzero return to error handling. The callback has distinct `0x5a`/`0x5b` request paths; no unconditional allow behavior was found in this trace.

Loader boundary: the prelink entry has `AppleSecurityExtension=true` and an `IOResources/IOBSD` personality. `loadKextWithIdentifier` defaults to starting the module but excluding personality matching in that same call. The KEXT kmod start wrapper reads an unresolved indirect pointer in `__DATA.__common` at `0xfffffff0096f8b08`; the report does not infer its runtime target from zero-filled storage. IOKit service `start()` is a separate conditional path after matching.

The kernel SHA remains `6d1f7a6c39c3098f5544d055e63b6c36d9cad112368516148c183e784e62e3d6`; candidate SHA remains `f55e7533f70dd1eb8fea172f30bd632a5739b015db04db7791b43402e5d4f643`. Builder provenance is `failed` only at the unrelated legacy R326 x9 verifier; `installhdrs` and `build` passed. Candidate remains `loadable=false/runtime_qualified=false`, un-packaged and prohibited from device use.

Next: resolve the kmod-start common-slot producer and `IOResources/IOBSD` start ordering host-only; then close the callback and real Image4/CoreTrust/PPL behavior gates. No device run.


## 2026-11-24: R159 loader/common-slot and IOBSD ordering audit

Host-only comparison report: `reboot-checkpoints/R159-real-abi-audit-20261124-01/R159-AMFI-loader-order-audit.md`, SHA-256 `4caf50a4b45b9c41767a4bbb7cc5ecc5816c511bf9b7e9d73023512074be3420`; JSON SHA-256 `6f402352550cc3ad8d50b002101cd5b9042458374ff21f9086930fd48dbfc7bc`; verifier SHA-256 `353ff8bdf9f0bf680007fea7050a81ec29de9509b076dc2aee363ab906990daa`.

The original 16G102 AMFI KEXT and current graft have identical zero-filled `__common` and `__bss` data and exactly rebased initializer/kmod pointers. This refutes a graft-only file-level missing producer. Source order is now bounded: prelinked personalities enter the catalogue with matching disabled; the security-extension load starts the module path separately; `bsd_autoconf()` calls `IOKitBSDInit()`, publishes `IOBSD`, then IOKit matching can call the AMFI service `start()`. `IOKitInitializeTime()` is a separate IORTC wait. Runtime common-slot population, service start, registration success and AMFI syscall success remain unverified; candidate remains off-device and `runtime_qualified=false`.

Next: resolve the runtime common-slot producer or instrument its producer path host-only, then use the post-`bsd_autoconf` boundary for the next discriminator.


## 2026-11-24: R159 AMFI start override attribution

The loader-order audit now also compares the candidate AMFI vtable with the linked kernel `IOService` vtable. A unique 15-entry prefix match puts candidate slot 15 at the kernel’s exported `__ZN9IOService5startEPS_` slot (`0xfffffff00764d564`), so candidate VA `0xfffffff0081f201c` is statically the `AppleMobileFileIntegrity::start(IOService *)` override. This does not prove execution. Loader-order JSON is now SHA-256 `b2404d4cc22d83c3f888cd8793e51670250840fb523bc603d4d4ad585a18881a`; the report remains SHA-256 `4caf50a4b45b9c41767a4bbb7cc5ecc5816c511bf9b7e9d73023512074be3420`.


## 2026-11-24: R159 loader-order final hash correction

The final loader-order JSON SHA is `b2404d4cc22d83c3f888cd8793e51670250840fb523bc603d4d4ad585a18881a`; the final verifier SHA is `e1214f74262f7a97b4fa44d0ca1ffe4f345c81edbce15141231ef208d1d1d539`. The report Markdown remains `4caf50a4b45b9c41767a4bbb7cc5ecc5816c511bf9b7e9d73023512074be3420`. The vtable comparison identifies `0xfffffff0081f201c` as the AMFI `start(IOService *)` override; this is static only.


## 2026-11-24: R159 loader-order final relation correction

Final loader-order JSON SHA-256 is `d0cde3adcbc0de9ed44a229b7ae9d3410d4c8b3ddef66f1529e29b93f37ed073`; report Markdown remains `4caf50a4b45b9c41767a4bbb7cc5ecc5816c511bf9b7e9d73023512074be3420`. The audit now records that the unresolved kmod common-slot trampoline is separate from the proven `AppleMobileFileIntegrity::start(IOService *)` registration path. The next discriminator is `bsd_autoconf()` → `IOKitBSDInit()` → `IOBSD` publication and service matching.


## 2026-11-24: R159 common-slot producer audit

The new host-only producer report is `reboot-checkpoints/R159-real-abi-audit-20261124-01/R159-AMFI-common-slot-producer-audit.md`, SHA-256 `64dde0d8f289312e129fba6bedd313a5d7349a91db15d0c39d933edc8a5da59a`; JSON SHA-256 `7822e49d414bb21ce3db6782d57f5155c4fc83e4a8873ea8b358e1700ed04854`. Original/candidate common bytes match; prelinked XNU bypasses KXLD common-symbol resolution; no concrete closed-AMFI `_realmain` producer is present in current source. This leaves the slot unresolved without treating it as an AMFI service-start failure.


## 2026-11-24: R159 planner-to-emitter provenance bridge

The planner JSON and emitted-candidate report have different stage semantics: planner `candidate_emitted=false`, emitter report `candidate_emitted=true`. New immutable bridge: `reboot-checkpoints/R159-real-abi-audit-20261124-01/R159-provenance-bridge.md` SHA-256 `327b461b5cd36b2e3b4d8826264070121f28b21903ad9e3f00172861cc4dc8fe`; JSON SHA-256 `895a327c2bca002792f0829b7ef96ac94ae32c735f93017dd1e4dd9e8e70b6e8`; verifier SHA-256 `60317d14a37746b48d16edc708765feabfa748363ad9a5f30923b2e6d63d7ef3`. It binds plan SHA `b7d5be37...481aa9`, emit-report SHA `2ecdc6a9...c6aa45`, candidate SHA `f55e7533...d5e4f643`, shared kernel/cache hashes, tools and exact binding-list hash. Emit argv is unavailable in preserved log and is not invented.


## 2026-11-24: R159 callback coverage for measured AMFI request

R154 measured `__mac_syscall("AMFI", 90)` (`0x5a`) with `ENOPOLICY=103`. New host-only audit `R159-AMFI-request90-audit.md` SHA-256 `4844c91661721cf804c5fa5acef8ff3be9cc267703c9dd9273f4a8e4086217da`; JSON SHA-256 `bc4130cb223edcc9cf6671cd93950341ae6778d69da8f2a74781066bf82272ac`. The candidate callback has dedicated branches for 0x5a and 0x5b and nontrivial validation/error paths; this proves static request coverage only, not registration, execution or success.


## 2026-11-24: R159 request-90 callback byte comparison

The 60-instruction callback range for request 90/91 is byte-identical between the candidate and original 16G102 KEXT after the `0x2000000` slide. Final audit Markdown SHA-256 `bca60c139f053fb860be07a23e081188b6604b62e7f9bfc0a3ac4b69a7357b8c`; JSON SHA-256 `69fae27d367a1bb7a131d529b76af69efa88b3ce38e419bcf95528754932a34`. This proves preservation of the original callback bytes, not registration or runtime request success.


## 2026-11-24: R159 planner/emitter deterministic replay

Using the bound native kernel and 16G102 cache in a new replay directory, the plan, emit report and candidate each match the preserved R159 artifacts byte-for-byte. Replay audit: `reboot-checkpoints/R159-provenance-replay-20261124-01/R159-provenance-replay-audit.md` SHA-256 `0da17fc543c1e1ee8a49f0131b2b7004f303cafceba825cff8891755dca33808`; JSON SHA-256 `4d54f0c5370fd8f2e2f41aab9c7a8aa2359a01add7a69d66d54899485a767490`. The historical emit argv is absent; a successful replay proves deterministic artifact reproduction, not the original historical invocation. Candidate remains unqualified and off-device.


## 2026-11-24: R159 TrustCache lifecycle blocker found

The linked R159 kernel contains `_trust_cache_init` but has no source caller and zero direct `BL`/`B` references to its VA. It is the only writer of `y35a_trust_cache_lock_ready`, which is BSS at `0xfffffff0077ab7f0`; consequently the linked TrustCache load/lookup and reserved-page helpers take uninitialized branches. Report: `R159-TrustCache-lifecycle-audit.md` SHA-256 `fdf88a199db14983a9895b1b1aa695cf8a6ab58e62121a6646054c67baaf7992`; JSON SHA-256 `33d2f52ba0998194c336ef674eeb94d6f8b5602d966edcb55c9ab02c8351d516`. The Image4 helper also does not read/authenticate manifest bytes and is not a signed Image4 validator. Candidate remains off-device and runtime-unqualified.


## 2026-11-24: R159 TrustCache lifecycle blocker

The linked R159 kernel contains `trust_cache_init()` but there is no source caller and no linked direct branch to its address. Its sole readiness-byte write is never reached; linked TrustCache load/query functions take their uninitialized paths, static TrustCache stays unset, and reserved-page helpers do not provide PPL ownership. The Image4 wrapper only bounds-checks the manifest pointer/length and does not authenticate manifest bytes. Audit: `R159-TrustCache-lifecycle-audit.md` SHA-256 `fdf88a199db14983a9895b1b1aa695cf8a6ab58e62121a6646054c67baaf7992`; JSON SHA-256 `33d2f52ba0998194c336ef674eeb94d6f8b5602d966edcb55c9ab02c8351d516`. This is a concrete static blocker; candidate stays off-device and `runtime_qualified=false`.


## 2026-11-24: R159 TrustCache lifecycle blocker

The linked R159 kernel contains `trust_cache_init()` but it has no source caller or direct branch references; it is the only writer of `y35a_trust_cache_lock_ready`, which remains zero-initialized BSS. Legacy load rejects, loaded lookups return false, static lookup has a null module, page claim returns NULL and page free exits before enqueueing. The Image4 wrapper does not authenticate manifest bytes. Audit Markdown SHA-256 `fdf88a199db14983a9895b1b1aa695cf8a6ab58e62121a6646054c67baaf7992`; JSON SHA-256 `33d2f52ba0998194c336ef674eeb94d6f8b5602d966edcb55c9ab02c8351d516`. Candidate is not runtime-qualified and remains off-device.


## 2026-11-24 R160 TrustCache initialization correction

R159 的 TrustCache 初始化函数虽已链接但没有调用者。R160 新隔离构建 kernel `131ae78f6445d5fd465527b62f9e42c0ca22f9779a1f60e3356b7da87e199755` 在 `arm_init()` 中于 `arm_vm_init()` 返回后调用 `trust_cache_init()`；链接调用地址为 `0xfffffff0072624a4`，初始化符号为 `0xfffffff007258f8c`。

R160 将 legacy v1 TrustCache `099a621d60e0333eef68d11c2820f99aea0e0e3674d1873d7a52193877a44ba0`（174 entries, 3852 bytes）绑定到 ADT `chosen/memory-map:TrustCache` 的 `0xa0bb4000/3852`。绑定 ADT SHA-256 为 `c2caa21fcd7c824fbd6f0dcb5247c71bb4b10d9e6c1e21931b41ca18cff025a1`。

外部 Image4 manifest 在没有 AppleImage4/CoreTrust 验证器时明确返回 `PMAP_TC_UNKNOWN_FORMAT`。这只是 fail-closed 拒绝路径，不是签名验证实现；真实 PPL 页所有权、CoreTrust、AMFI runtime registration 和 device qualification 仍未闭合。R160 focused tests 为 3/3，通过；候选保持未打包、`runtime_qualified=false`、禁止上机。报告：`reboot-checkpoints/R160-trustcache-init-offline-20261124-01/R160-TrustCache-init-adjudication.md` SHA-256 `2ccb580a9e436ce5d799952d7531a6e4c88f4f47e859cb70d71a72acdf352e67`；JSON SHA-256 `ecb392f3856a16ea83441f9dd3ae61ecc60209f40fcf5de90237e533fcb84513`。

正式 builder 的 `installhdrs` 和 `build` 已通过，但 provenance 仍因旧 R326 x9 phase verifier 失败；该失败未被改写。


## 2026-11-24 R160 Image4 callsite correction

16G102 原始 AMFI KEXT 的 wrapper `0xfffffff0061efa60` 在调用 helper `0xfffffff0061ef664` 前将 `x2=0`、`x3=0`；helper 把 `x3` 保存为 `x21`，随后在 `0xfffffff0061ef84c` 调用 `pmap_load_image4_trust_cache`。因此这条静态识别的 wrapper 路径传入零 manifest pointer、零 buffer length、零 actual length，R160 会进入 legacy v0/v1 parser；非零 manifest actual length 仍返回 `PMAP_TC_UNKNOWN_FORMAT`。这不是签名 Image4/CoreTrust 实现，也不证明运行时 wrapper 被执行。

原始模块提取的 canonical hash 使用 manifest 声明的 prefix 长度；磁盘工作副本各多一个末尾 NUL，不得混用完整文件 hash。报告 `R160-Image4-callsite-adjudication.md` SHA-256 `30d2f89ed1e637d1194dc383cc145aa6511f2ce86df98e1d69c43b296fc6f568`；JSON SHA-256 `f6a3703f82ffc8177e9fad06e311597ff363fb8c64a518ef81eb8b093d345b9d`。


## 2026-11-24 R160 Image4 interface registration audit

R160 kernel 只有 XNU `_img4_interface_register` (`0xfffffff007644db0`) 与空 `img4if` (`0xfffffff00778ca38`)；全量链接反汇编没有任何直接调用者，链接符号表没有 `coretrust_interface_register` 或 `image4_dlxk_link`。因此 signed Image4/CoreTrust provider 未在当前 kernel image 中静态注册。legacy raw wrapper 的 zero-manifest 路径仍可解释，但不能作为签名验证闭合。报告 SHA-256 `be1388f9bd0beb790164768bd19cf24e53cfc2d82d43e60f0467bb244060106f`；JSON SHA-256 `39f6bc43a68700c91752295a1ef4525661e0b34f1e635b5e3d5f54f892b5cd09`。


## 2026-11-24 R161 AppleImage4 dependency closure

原始 16G102 prelink 中存在 `com.apple.security.AppleImage4`，但 R159 三根 graft 没有纳入它。R161 离线扩展为九根：AMFI、CoreTrust、corecrypto、AppleImage4、IOCryptoAcceleratorFamily、AppleARMPlatform、IOSlowAdaptiveClockingFamily、IOStorageFamily、IOReportFamily。规划结果 15,710 bindings，kernel/component 为 13,097/2,613，missing=0、collisions=0；AppleImage4 的 `_img4_interface_register` 与 AMFI 的 `_pmap_load_image4_trust_cache` 各有一个明确绑定。候选 SHA-256 `9c335aeec513d66971b70d014718f8a9aac2da3c214ff0d12119600ec220d351`，plan SHA-256 `93533fd4cc7e62eb39f5a224adc499d3c17b6c6ea1bc816f0cdfaa58607debd2`。

这是 structural graft evidence；planner/emitter 仍标 `loadable=false/runtime_qualified=false`，指令重定位、KEXT start/interface registration、CoreTrust/PPL 语义和设备运行未验证。报告 SHA-256 `51b88e69b1bb80732237bea4659336f2cacd9efb319434e7fab7e4494638759d`；JSON SHA-256 `e677b800443a6e2f24a8c3a139ee7c2693a9d2c85625e8a987aa8ae8988c2cf4`。


## 2026-11-24 R161 AppleImage4 candidate emitted

R161 已将原始 16G102 AppleImage4 及其依赖扩展为九根，plan missing=0/collisions=0，随后生成 host-only candidate `9c335aeec513d66971b70d014718f8a9aac2da3c214ff0d12119600ec220d351`。candidate 可解析，包含 24 个 prelink entries 和全部九根组件；结构检查 JSON SHA-256 `db571acedb066bd6b249031b600f69ea29d50cc361df4f0c20def97a71643746`。emitter 仍明确 `loadable=false/runtime_qualified=false`，因为它没有完成 PC-relative instruction relocation/ABI/runtime loader 资格。


## 2026-11-24 R161 PC-relative preservation gate

R161 九组件 candidate 的 PC-relative 静态门通过：25,861 个编码均指向组件内部，没有 external target；选定组件 `__TEXT_EXEC` 共 582,960 bytes 在 graft slide 后逐字节保持一致。因此 instruction-byte relocation 不是当前已证阻塞。候选仍未通过 native XNU 4903 loader ABI、KEXT start 顺序、Image4/CoreTrust interface registration、PPL/TrustCache 或 AMFI runtime 资格。JSON SHA-256 `85af07c3bb5e7a39db5403bf28a7ce0fc170537f37ec3e597163619c4e2f08c5`；报告 SHA-256 `536384dffb43ca97ab4b360dab60449912f0c1f788fe6c841e16ece667effbd1`。


## 2026-11-24 R161 static candidate integrity gate

R161 AppleImage4 full candidate 已通过现有静态 integrity gate：candidate SHA `9c335aeec513d66971b70d014718f8a9aac2da3c214ff0d12119600ec220d351`，24 prelink entries，15,710 bindings/KASLR offsets，missing=0，collisions=0。Gate JSON SHA-256 `9d37f0238f852f117787d5049e7f1eeaf5e48285b35ea0945eee4edac1ba351`。该 gate 只证明字节/元数据/范围一致，不证明 loader 接受、KEXT start、Image4/CoreTrust/PPL、AMFI runtime 或设备启动。


## 2026-11-24 R161 AppleImage4 provider registration path

原始 AppleImage4 provider 在 `0xfffffff006d02a1c` 调用间接 stub `0xfffffff006d03ec8`，该 stub 通过 GOT 绑定 `_img4_interface_register`。R161 nine-root plan 保留了对应绑定，因此 provider registration call 在 structural candidate 中存在。此证据不证明 KEXT 被 native loader 启动，也不证明 interface runtime population/CoreTrust/PPL/AMFI 成功。报告 SHA-256 `108053acfae65c44883773df1036983d82b4554e00d89785bf10cb4a542aba40`；JSON SHA-256 `6d17d532a57878a6f18d39506241c09d5faaae1ad707977acebcfddce67de7a1`。


## 2026-11-24 R161 loader metadata gate

R161 candidate 中 AMFI 与 AppleImage4 的 `AppleSecurityExtension`、`_PrelinkKmodInfo`、`__mod_init_func`、start/stop 指针和共同 slide 均与原始 16G102 一致。该 gate 证明 loader metadata rebasing，不证明 native loader 实际启动 KEXT 或 provider registration runtime。JSON SHA-256 `eeef9e62006a926f97fa71cb8791f18ff3bd67bdd4584edd1e8886547d7da1`。


## 2026-11-24 R161 security loader order gate

R161 candidate 的 AMFI 与 AppleImage4 metadata 均标记 `AppleSecurityExtension=true` 且 bundle ID 通过 `com.apple.` 筛选。pinned XNU 4903 源码链 `kernel_bootstrap -> mac_policy_initmach -> load_security_extensions_function -> bootstrapLoadSecurityExtensions -> OSKext::loadKextWithIdentifier(allowDefer=false)` 静态通过。该 gate 不证明 runtime KEXT start、img4if population 或 CoreTrust/PPL/AMFI 成功。JSON SHA-256 `958d0ce6abb9b4c07d1aa3f46dd48c7cd31fca9f5dccb54326951b1c9ffed332`；报告 SHA-256 `e150934eb57a324e868cbc385ed49464e35e9d4a69e1044c4868243c5f893399`。


## 2026-11-24 R161 XNU 4903 prelink loader simulation

针对 pinned 4903 的 `KLDBootstrap::readPrelinkedExtensions()` 实际规则，R161 candidate 的 15,710 个 KASLR relocation site/target 全部落在 12 个 loader segment slots 内；`__PRELINK_INFO`、KASLR table、`OSKext::withPrelinkedInfoDict` 与 security `allowDefer=false` 源码检查均通过。该结果排除 sparse-index ABI 误门造成的阻塞，但不证明真实 boot-time slide、KEXT start、interface population 或 AMFI runtime。JSON SHA-256 `f8bda53f371b1ee3eece3f325d173064ec8050be6530d585e81f1cd9ffef2705`; Markdown SHA-256 `aa2d5c6fbd6e27ba93f78dc38998529cca656910a418840b17e4e50c112f3467`。


## 2026-11-24 R161 KEXT start semantics

Pinned XNU 4903 的 `OSKext::loadKextWithIdentifier` 默认 `startOpt=kOSKextExcludeNone`、`startMatchingOpt=kOSKextExcludeAll`；security loader 传 `allowDefer=false`。`OSKext::load()` 会在该默认 startOpt 下调用 `start()`，但默认不启动 personality matching。静态路径已闭合，runtime start return/interface population 仍未证。JSON SHA-256 `9098eabb8568e7cbfbebc817eee4d10a51661ead046645c863509fd42d7fab0d`；报告 SHA-256 `4174239f8f67102beb19d8a874bf1838b7b0174c35c01f58b53352d55eadaec5`。


## 2026-11-24 R161 combined host closure gate

R161 九根 AppleImage4 closure 的全部静态 gate 已合并通过：plan integrity、PC-relative、executable bytes、loader metadata、provider registration、security loader order、XNU 4903 prelink simulation、kmod/header/start/stop range 均为 true。Candidate `9c335aeec513d66971b70d014718f8a9aac2da3c214ff0d12119600ec220d351`，15,710 bindings。Combined JSON SHA-256 `f1cdcc24cb91eb4203826b9ce4dfe5081cdb19d13cbe9a24bed24097926b6250`；Markdown SHA-256 `ee870de39dd89655315a41ea7614184de4014439a3869c92da7d41fd5c1ff7ff`。仍未证明 runtime KEXT start、img4if/CoreTrust、PPL/TrustCache、AMFI 或设备运行。


## 2026-11-24 R163 Phase-A paired MVE offline-ready

R163 已完成受限 Phase-A AMFI policy、witness patch、kernel/package/regular probe/clear probe 和离线绑定门。kernel `9793fb533ec6b5dbeefcb0a20fb8453ae99f157385d133f7dac646df899abb37`；boot `566b87c59e6949283b506aa6d80fb1fba7132a2778cff4cd8067813d9f54e1ce`；regular/clear images `4cb876c033c7dcecff3db89638b2dcaf0d2194a6842f06a55f5aaf6ec5cbed26` / `1b4693975eb967ceaefa7a38755410ad43fe86e068ec35c6f6faeca790afd0fd`。clearprobe 清零 `0xa0bb0b00/1024`，两个 probe geometry 相同，capture/transport gate 均 true。

R163 只处理 PID1 的 AMFI request 0x5a；其它调用/进程返回 ENOPOLICY，不改 vnode 签名、TrustCache 或 PPL。计划 SHA-256 `7888b5d79ee915e5cfdcd8c656b773d2267b071f8bce61024619766bda4a69dc`，offline gate SHA-256 `d87f36b241b0e11df2f80d7915b6f6f75a2ed678fa9eafa38d8343498d1cdf06`。`device_run_allowed=false`，尚未运行 fastboot。

## 2026-11-24 R164 Phase-A paired MVE adjudication

R164 did run once. The paired sequence completed from 2026-11-24T13:27:37Z to 13:28:24Z, used RAM-only fastboot boots, returned the device to verified unlocked fastboot, and recorded `persistent_writes=false`. It failed with `AMFI entry witness absent`.

R164 kernel `9bd95fb47853c6b6bba3224fa8a272d679de0f930961aba58e388119a5990df8`; boot `47b36729446d083aafbabcdd23115b8baff5103763cead641b7d582cbbf18fe1`; offline gate `c6a77466308c44dab4e7a28368fc648dfdfacd55295f0b012100179a1660dec7`. Raw SHA-256: preclear `2fccf0f8674186b6a4fbcf391d42047bcbde6c6a2586bc8671027db0865da75a`, baseline `6bd3c5d1099aa558c8eab6ed02492439fe20a1020dc021f65cb1ea8d5c6c750c`, candidate `7e274fa196935448678d47eabb3b5dfc3610dd3f409177c1425cf406dc22a786`, final `290a0362ac025f28f4dc930025ad2d78377b009f90b372ddde655181ce57d658`.

The readback instrument was fresh: all regular probe captures carried `Y35ARD02`, `PSTCOPY0`, and record count 11. The external `0xa0bb0b00/1024` window was zero in preclear, baseline, and final. The early record had the older direct physical R68E7 markers, but no `ARMRET00` at the expected pre-C return position and no arm_init slots 5–10. The measured boundary is therefore before arm_init; this run does not adjudicate AMFI policy registration or request execution.

R164 adjudication Markdown SHA-256 `431f9b6c473b37fa387cf282b8932ed212c03f6116b9419e54a3b406f35462f5`; JSON SHA-256 `39ea3b48dff9d884257023f939927c311ec30a40c7c9c6e0ab7bac2af4f104b3`. Do not repeat R164 inputs. Keep `device_run_allowed=false` until the BootArgs physical-to-KVA mapping and missing pre-arm witness are closed offline.

## 2026-11-24 R165 ARMRET physical diagnostic adjudication

R165 ran once from `2026-11-24T14:35:15Z` to `14:36:02Z` with the same RAM-only safety boundary. The device returned to verified unlocked fastboot and `persistent_writes=false`; the runner failed on `ARMRET00 witness absent`.

R165 kernel `0abdf5a79f76ed07845930fafca2ae6501d56044b69e63895a62518050911c3d`; boot `4b109ded154d858d7ecc1f283fe736c5a127816d68c3988cf3b13e2620a129a7`; offline gate `f036d0eb5baa0ae8a026512435c11242da48a747a765262a912187fe3ced4613`. Raw SHA-256: preclear `f5878469c9a7833bbb3344b7f96e465cac5268b6d78282a1c7cc9f1bff0a46e2`, baseline `185bc886cf576e3693a374c7dbf975077de34dfa4c30946461780a15a200f36f`, candidate `7c57d23acc107c5cca1d8eb79bf4b612e9ffa922dc84b95f8090f15073e11a64`, final `1d299c0b73c7d482599fb5ed2bc94f652df2b074f51298dcd329bf9630c5dff6`.

Fresh final contains `COMMON00`, `MAPDONE0`, `TTBRDONE`, and `PREMMU00`; `ARMRET00` and `SCTLRRD0` are zero. The physical ARMRET diagnostic is present in the linked binary, so the last observed boundary is earlier: after `PREMMU00` and before the SCTLR readback witness. AMFI remains untested.

R165 adjudication Markdown SHA-256 `3f3522f56f6fd244594435f1b6f6a77d3aeff090dd831f2d34fd27e04603a849`; JSON SHA-256 `c99ca4a2ad62e5bcf9a4821b1db1aecc0954ef66a519af994252c1a526201c1f`. Do not repeat R165 inputs. Keep `device_run_allowed=false`; next work is offline SCTLR-window ownership and linked-PC audit.

## 2026-11-25 R168 SCTLR window paired MVE adjudication

R168 completed all four RAM-only stages and returned the device to verified unlocked fastboot. The runner failed while decoding a 16-byte record as one integer; this is a runner defect, not a device boundary. R168 raw are retained.

R168 raw SHA-256: preclear `8f9c1660ec1b2a4f14e16362bf8149b456b3095b0b5e24963b2fe5efd58eb0f8`, baseline `da696be182ccb77973bdf0d770286c5bc7d89c7030d8a846d660cfe336682fa0`, candidate `459d483348cc3bcde91bc80c1a6409b55e1cbf244a32c50f215af30f69dfbe5e`, final `81650a035fbcd3a7f2ab81ea8a35f7101f0592cf58af880384f8080bfca892e6`.

Final first-eight-byte codewords show `SCTPRE00` at `0xa0bb0a10` and `SCTPOST0` at `0xa0bb0a20`; both were zero in preclear/baseline. This proves crossing MSR/ISB/MRS. The original SCTLRRD windows `0xa0bb09c0/0xa0bb09c8` were absent from the probe manifest, so their raw absence is invalid evidence. AMFI remains untested.

R168 adjudication Markdown SHA-256 `f3f078c6d1517ba66239f1b335397874798b5bdbdf64cd9dac3df38190dadd32`; JSON SHA-256 `8e44312ae791fd2e190e1b818664e6565014ce64c2f1fe261ea2702de473c1c0`. Do not repeat R168 inputs. Keep `device_run_allowed=false`; next step is a new matched probe pair binding the two SCTLRRD physical windows.

## 2026-11-25 R170 SCTLRRD physical window adjudication

R170 completed the RAM-only four-stage sequence and returned to verified unlocked fastboot. The runner misread a 16-byte pre/post record, but raw decoding is valid.

R170 raw SHA-256: preclear `05477655d99d8724b9cd3441d9a0907a732598b80942dec06bb3935799514b4d`, baseline `df2d38c05ba05c1ea7e6dc2c333c7eb5a92f37583a8b447e6dc462ac23688829`, candidate same, final `2f36b2aa6c8ef5337885237d75a3cc277fbf53e368b9e32fbdeaf27ffe344621`.

Final `sctlr-window` at `0xa0bb09c0/32` contains `R68E7RD0` in the first eight bytes and a nonzero SCTLR value in the next eight; preclear/baseline/candidate are zero. This proves SCTLRRD persistence. The final early record also contains later TPIDR, exception-stack and page-table markers through `PTSHIFT0`; arm_init and AMFI remain unobserved.

R170 adjudication Markdown SHA-256 `bddba0b7e9b613844a01b61afde86da12bdfb888989fb0b6e5fa6f2906ae6971`; JSON SHA-256 `e5372a499036e4024cc19fe7495e8bb26a1592a20eb0782a04c2d172bca0910d`. Do not repeat R170 inputs. Keep `device_run_allowed=false`; next step is a matched post-SCTLR/page-table invalidation marker window.

## 2026-11-25 R171 post-SCTLR mapping window adjudication

R171 completed the RAM-only four-stage sequence and returned to verified unlocked fastboot. The runner had the known 16-byte decode defect; raw decoding is valid.

R171 final post-map record `0xa0bb0980/64` contains `HDRLOAD0`, `HDRADJ00`, `L1ALLOC0`, `VPPRE000`, `VPCALL00`, `KVPRE000`, and `KVCALL00`; preclear, baseline, and candidate are zero. Final raw SHA-256 is `7ecf89489c82008418af7f3bb7687731265d5477c2d259e33eaa88cff5568a77`.

R171 adjudication Markdown SHA-256 `eab1c397d3e8d1d337f2bdf29d7c83e2d947765ba2977275a96e650d49c5b751`; JSON SHA-256 `b22688b30dc245e9714b137588da2b73b1db7460b45df9903921d990309bd2ec`. Do not repeat R171. Keep `device_run_allowed=false`; next step is an offline HID private sysreg bracket.


## 2026-11-26 R205c corrected boot-args probe

R205 was invalid because its patch hunk did not insert the byte read or marker. R205b's candidate run is retained as a failed-before-readback event, but its ARG1RD00 record address was wrong (`0xa0bb0a90`); the package-derived address is `0xa0bb0d90`.

R205c regenerates regular/clear probes against kernel `95cb85ba39fbefd34bd656653d6281b855d1f28349a6f42a473b16599395a5d1`. Regular/clear probe image hashes are `ba4e4847b4ec958d15ff349bb9af2ecc82276fce462adfb3819b379533c8e91c` / `9f88a8f2508ac02531989e18bff8036b6130cbea7605401663d0310196b8e41b`; manifest hashes are `1dfb7af2111011a5f5074119be8280d96dc357c020722b1224a5b308028573c5` / `d38d0cf143e69aafe03deb892163b6d7e895ca45943aad5d7d05657b15ab3d66`. Linked/binding and both capture/transport gates pass.

Combined gate: `4f28c836dad993032c88bbad267d2579d40c6fe96de954f0edcb2f131390618e`. MVE plan: `45a8be2e83bbd521f573e9b2b1191817e59350a4475e6d08e28afd4ae663b43e`. Device run has not occurred; keep `device_run_allowed=false`. Next step is live preflight followed by the single planned RAM-only MVE only after the run gate is intentionally opened; runtime qualification remains false.


## 2026-11-26 R206 guarded boot-args read

R205b/R205c failed after candidate boot because the new first-byte load preceded the existing embedded `max_len == -1` early return. Static source and linked disassembly show `PE_parse_boot_arg()` supplies `max_len=-1`; R205's `ldrb [x20]` therefore changed the old control-flow path.

R206 patch SHA `d0cde1f9cd1a0a23b8a684d44950b5c3b112098ccab976f3e6254031eb8dc3e8` moves `ARG1RD00` after that guard and before the empty-args test. Static root-cause JSON `3523303bd179b6a558b7c13f05ebc938f8cbd3c4d8cb15d9cb8e893b6863c40f` is green; `git apply --check` passed. R206 clean source is external and builder PID 33875 remains live in `preparing`, with no make/kernel result yet. Keep `device_run_allowed=false` and do not repeat R205b/R205c.


## 2026-11-26 R206 guarded boot-args candidate

R206 build and linked guard correction passed. Kernel `9c558a26adb924ec2174ab9d4bb3a64dd79b319aa1e514fd42d620dc61686e62`; linked order is guard before first byte load, then `ARG1RD00`. Binding gate `3f47ec2739724243a87680aee7b311904ce7681afc282d1866b58f6734821a13` and combined gate `7cf42f734771f94d531bb68ca685e11d3e44f31ca4c2378fd97c113985c2d99a` are green. Package/probe hashes are recorded in `R206-offline-adjudication.md`. Packaging used a derived QCDT-only reference, explicitly not stock boot provenance. No device run yet; next is live G0 preflight and one RAM-only MVE with `device_run_allowed=false` until preflight.


## 2026-11-26 R206 paired failure supersedes offline-ready status

R206 ran once after live G0 and failed after candidate boot before candidate readback. Preclear/baseline were fresh zero controls; candidate/final raw are absent; device returned to verified unlocked fastboot; `persistent_writes=false`; do not repeat R206.

Offline comparison found R204b final fresh `PEBARGRT`, proving the external carrier write/read path. R206 slot `0x52` has no duplicate writer and linked guard order is correct. The candidate disconnect is therefore not localized to the marker transport. Report `R206-vs-R204b-early-audit.json` SHA `fa32f532a75705121962280cf057c81054a4f674bd068f0076015a53ada76a1c`. Current next step is offline package/entry/early-kernel comparison; `device_run_allowed=false`.


## 2026-11-26 R208 current target supersedes R207 queue

The active target is the R208 TF/SD offline path with GitHub Actions as the only UniXNU build route. R207 v2 PID 90604 was terminated and produced no provenance or kernel artifact. R208 has passed the SD protocol host suite, sdhc2 ADT contract and lk2nd SD_BOOT patch apply-check. Private manifest commit `bc1dacf822dd1a2d013716dca50cbf07a09ab7c8` binds the exact XNU ref and six arm-driver patches. Plan-only run `45812745086` passed. Native runs `45838744656` and `45838740886` on commit `4c817f03fbd5a0611fadfd2675381c32ae995363` both passed exact XNU header generation but failed the NativeSdcard object step; this does not establish a source compile result or artifact. XNU link, package/probe, TF GPT/APFS image, root mount, eMMC fallback and device evidence remain pending. No local UniXNU compilation is allowed on any disk. Keep `device_run_allowed=false`.


## 2026-11-26 机械盘本地编译已关闭

用户要求取消所有本机磁盘上的 UniXNU 编译。R207 v2 builder PID 90604 已终止，未生成 provenance 或 kernel artifact。后续编译、NativeSdcard object、XNU link、package/probe 和静态门禁全部走 GitHub Actions；机械盘只保存缓存、run roots、CI 下载产物、备份和 raw。`device_run_allowed=false`。


## 2026-11-26 R208 latest CI closure
R208 latest CI run `45852497429` on commit `3538cccc70e4b3490f7b65e9042713e6266b8c4e` is green through root-selection contracts, NativeSdcard object compile, IOStorageFamily-191 combine and deterministic archive. Object `47bec72ade1ff792938b9ae468f778a7d7e4c13bb62f97d18e5dbf96242e900e`; combined `0353a170088989517d6634805f16537e26844fa89bd2acf9040dffd3cfa400fd`; archive `f401224182f56a5d27532482c1978528ae1570c3d5b16931b98384a6aaba1e73`. Kernel link, package/probe, TF GPT/APFS/root/fallback and device evidence remain pending.


## 2026-11-27 R208 offline CI state
R208 validation `45855811648` and Docs `45855811845` pass on commit `ba4854d4cb076388f61cb2bcdbdf9a7e8874ec5d7`. Offline source, host, root-selection, NativeSdcard, IOStorage archive and documentation gates are green. Kernel link inputs, package/probe, TF GPT/APFS/root/fallback and device evidence remain pending; device_run_allowed=false.


## 2026-11-26 R208 fallback candidate and Actions dispatch blocker

Main `43ae09a` adds the opt-in `XNU_Y35A_STORAGE_FALLBACK` candidate patch, bound to `emmc-boot-uuid`, with 3 patch tests plus 6 fallback-matrix tests passing locally and pinned-XNU `git apply --check` passing. The patch is not in the native build manifest. Push validation attempts `45889905156`, `45889905114`, and `45889905098` failed before runner allocation with zero steps; rerun attempt 2 of `45889905156` also completed with `runner_name=null` and zero steps. Keep the earlier green TF run `45887232679` as the valid code gate; classify these as CI dispatch failures, not source failures.


## 2026-11-26 R208 native execute source-tree cleanliness blocker

Native execute run `45888048634` on commit `2b45f50b143edf19c678892dab0d768a5e378f61` reached `Run native build` but stopped before kernel compilation because `run_native_build.py` rejected `/Users/runner/work/_temp/xnu` as dirty. The preceding host-tool preparation rewrote `bsd/kern/makekdebugevents.py` without a verified restore in the executed input path. No kernel artifact was emitted. This is a CI preparation failure; the isolated restoration fix must pass a new run before another execute build. `device_run_allowed=false`.


## 2026-11-26 R208 package candidate rebased; CI billing blocker

Package candidate commits `1cdc077`, `ac28710` and `73f1756` are based on current main and pushed as `codex/unixnu-ci-package-v2`. They add hash-bound package consumption, native build plan binding, derived QCDT provenance, iOS 12.4.1 root staging, combined TrustCache coverage and complete package input trigger paths. Status is `WAITING_FOR_CI`: package run `45896319737` also failed before steps because the GitHub account has failed recent payments or reached its Actions spending limit. No kernel or package artifact exists; `device_run_allowed=false`.


## 2026-11-26 R208 TF/APFS package contract split

Commit `f694b4f` adds a design-only TF/APFS device-package contract to `codex/unixnu-ci-package-v2`. It requires a schema-2 native artifact and build plan, stock QCDT provenance, GPT/APFS image with exact card binding, linked `native_storage_select_root`, first-read TF failure coverage in the eMMC fallback, and package/probe hashes. The existing RAM package remains `launchd-diagnostic-ramboot` with `runtime_qualified=false`; `device_ready=false` and `device_run_allowed=false` remain fixed. Billing/spending-limit recovery is still required before CI execution.


## 2026-11-27 R208 stock QCDT unavailable

Read-only checks of all registered Mobile stock boot/QCDT candidate paths returned `Input/output error`; Portable staging contains no stock boot/QCDT/image. The TF/APFS device-package contract therefore remains design-only: derived DTS/QCDT may support offline control packaging, but cannot satisfy stock-QCDT device provenance. Keep `WAITING_FOR_CI`, `device_ready=false` and `device_run_allowed=false`.


## 2026-11-27 R208 validation and intermediate producer

Validation run `45938145784` on package commit `0bf9aad` passed all 33 contract tests and the TF/APFS design contract. Package run `45938145777` on the same commit completed only the validate job; the RAM package and TF/APFS intermediate jobs were skipped because no native run/root-tree/stock-QCDT dispatch inputs were supplied. Package commit `3d88e3b` adds the root-tree producer artifact and macOS-only GPT/APFS intermediate path. This is an offline intermediate stage; it is not kernel, launchd, SpringBoard, or device evidence. Mission remains `IN_PROGRESS`, D1/D2/D3 `NOT_MET`.

## 2026-11-27 Native build and active repair

Native run `45956827212` on package branch commit `bd7615046eb01a42e74fa0a3e6194331e0557a29` reached the actual native build and failed without producing a kernel artifact. The failure advanced past genassym, monotonic-header compatibility, and the first Firehose declarations, then exposed missing XNU 4903 Firehose configuration APIs in the selected libdispatch inputs. The active repair restores the libdispatch 1477 API set and adds a provenance-bound compatibility header for its atomic-private dependency. GitHub Actions is operational. Package validation `45957683974` passed its contract checks, while native resolution, package and TF/APFS jobs were skipped because this was a push without native artifact inputs. The package workflow now accepts and compares explicit native run branch/SHA inputs, but consumption of a real successful native artifact remains unverified. Mission stays `IN_PROGRESS`; D1/D2/D3 remain `NOT_MET`; `device_run_allowed=false`.

Native repair commit `e007c2ed6cf09038ed32d6e99c6d394f50628606` was pushed with the Firehose 1477 API and atomic-private compatibility input. Native execute run `45960088944` is active on that SHA and currently fetching native input sources. TF validation run `45960008744` passed. No kernel artifact or device evidence is recorded. Continue this exact run to its terminal result before selecting the next CI action.

Native run `45960088944` completed with final arm64 kernel-link failure and no kernel artifact. The undefined references `_RESERVEDIOService33` through `_RESERVEDIOService47` originate from `libQcomSdcard.a(IOStorageFamily-QcomSdcard.o)`. Archive provenance identifies IOStorageFamily commit `c95d314`; its IOKit vtable exceeds the reserved-slot ABI in XNU 4903 `IOService`. The next fix is to pin an ABI-matched IOStorageFamily source, rebuild the archive and provenance on GitHub Actions, then rerun native link on the resulting exact SHA. All earlier native input and compilation stages passed in `45960088944`. Mission remains `IN_PROGRESS`, D1/D2/D3 `NOT_MET`, and `device_run_allowed=false`.
