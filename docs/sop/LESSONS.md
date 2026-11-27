# UniXNU 错误与返工 lessons

本文只追加。每条记录现象、根因、影响、错误做法、正确做法、证据、自动化入口和下一次触发条件。

## L-2026-11-26-01 R205 malformed patch

- 现象：R205 provenance 显示完成，但 staged source 只有 `first_arg_byte` 声明，缺少赋值、marker 和分支。
- 根因：unified-diff hunk 行数错误，patch 只部分应用。
- 影响：R205 build 不能证明目标代码进入候选。
- 错误做法：把 build provenance 的 complete 当成 patch 语义完成。
- 正确做法：对精确源树执行 `git apply --check`，再检查 source diff、变更函数和 linked codeword 顺序。
- 证据：`/Volumes/Mobile/unixnu-research/reboot-checkpoints/R205-pe-bootargs-first-read-native-build-20261126-01/`。
- 自动化入口：`scripts/y35a/verify_experiment_contract.py` 的 source patch 和 source tree 检查。
- 下一次触发：任何 patch 链进入 build 前。

## L-2026-11-26-02 R205b probe 地址错配

- 现象：R205b 使用 `0xa0bb0a90`，package-derived `ARG1RD00` 地址实际为 `0xa0bb0d90`。
- 根因：probe 地址手工复制，未从当前 package manifest 推导。
- 影响：preclear 和 baseline 不能证明目标 marker 窗口，candidate/final 缺失时不能裁决执行情况。
- 错误做法：复用旧地址和旧 gate。
- 正确做法：每次由当前 manifest 计算 `args_physical + carrier_offset + slot * width`，并用负对照拒绝旧地址。
- 证据：`R205b-offline-gates.json` 与 `R205c-offline-gates.json`。
- 自动化入口：experiment contract 的 `probe.record_map` 闭包检查。
- 下一次触发：任何 probe 或 clear probe 生成前。

## L-2026-11-26-03 early read before max_len guard

- 现象：R205b/R205c 在 `max_len == -1` 早退之前读取 `*args`，R206 修正了顺序。
- 根因：只验证了 marker 位置，没有验证调用者契约和 guard 的前后顺序。
- 影响：修正地址仍无法排除 candidate-stage disconnect。
- 错误做法：只看源码注释或 marker 是否存在。
- 正确做法：对调用者、源代码和实际 linked disassembly 做局部顺序核对。
- 证据：R206 linked objdump 和 `R206-vs-R204b-early-audit.json`。
- 自动化入口：linked gate 的局部窗口顺序检查。
- 下一次触发：新增任何 early boot read 或 marker 时。

## L-2026-11-26-04 derived DT provenance 丢失

- 现象：R206 使用 derived QCDT 生成 package，但 package manifest 没有完整记录 DT 推导链。
- 根因：DT 来源只写在旁边的 synthetic reference 文件，package hash closure 没有纳入。
- 影响：运行输入不能证明使用的 DT 来源，stock 和 derived 证据容易混淆。
- 错误做法：依据目录名或 `stock-boot` 参数名推断来源。
- 正确做法：manifest 必须记录 `source_type`、原始容器、QCDT offset/size/SHA、derived output/SHA 和用途。
- 证据：`R206-pe-bootargs-guarded-read-package-20261126-01/synthetic-stock-boot-reference.json`。
- 自动化入口：package gate 的 DT provenance 闭包检查。
- 下一次触发：任何 package 使用非原始 stock boot 时。

## L-2026-11-26-05 device permission split

- 现象：offline gate 写 `device_run_allowed=false`，运行摘要却写 `device_run_allowed=true`。
- 根因：设备 runner 可以自行覆盖许可，缺少单一实验合同。
- 影响：未完成 gate 的候选可能进入设备。
- 错误做法：把权限字段作为 runner 的可写状态。
- 正确做法：runner 只读取统一实验合同的计算结果，不能自行提升权限。candidate 结束后必须回落为 false。
- 证据：R205b、R205c、R206 paired run summaries 与各自 offline gates。
- 自动化入口：`scripts/y35a/verify_experiment_contract.py`。
- 下一次触发：任何运行计划生成或 runner 启动时。

## L-2026-11-26-06 R207 patch and builder drift

- 现象：R207 design 使用 v2 patch，但 builder 实际使用损坏的旧 patch，`git apply` 在 line 10 失败。
- 根因：设计文件、builder inputs 和 patch SHA 没有强绑定。
- 影响：失败构建不能证明设计已被测试，且容易继续读取旧输入。
- 错误做法：只检查候选目录名和 builder 是否启动。
- 正确做法：run plan 固定 patch SHA，builder provenance 必须列出同一 SHA，source gate 必须拒绝其他 patch。
- 证据：`R207-control-plan-v2.json` 与 `R207-bootargs-read-no-marker-control-native-build-20261126-01/build-provenance.json`。
- 自动化入口：experiment contract 的 ordered patch closure。
- 下一次触发：任何 builder 启动前和 provenance 结束后。

## L-2026-11-26-07 native artifact permission closure

- 现象：native workflow 的固定依赖源拉取成功，但下载同仓库 R208 driver artifact 返回 GitHub API HTTP 403，后续 native-inputs 和 build 均未执行。
- 根因：workflow 只声明了 `contents: read`，默认 `GITHUB_TOKEN` 没有 `actions: read`。
- 影响：hash-bound artifact 存在，但 CI 无法消费它，失败位置容易被误判为 artifact 缺失或构建问题。
- 错误做法：只在 runner 上调用 `gh run download`，不声明 artifact 读取权限。
- 正确做法：workflow 显式声明 `actions: read`，下载后继续检查 archive、driver manifest 和 SHA-256。
- 证据：GitHub Actions run `45866748560` failed at `Download hash-bound R208 driver archive`; log reports `HTTP 403: Resource not accessible by integration`.
- 自动化入口：native workflow permissions 和 driver artifact hash gate。
- 下一次触发：任何跨 run 复用 GitHub Actions artifact 的 workflow。

## L-2026-11-26-08 promisor checkout copy

- 现象：native workflow 成功下载 driver artifact，但 `Prepare exact native inputs` 在 `git clone --shared` 复制 XNU checkout 时失败，远端 promisor 报缺 blob。
- 根因：GitHub Actions 的 `actions/checkout` 使用 partial/promisor clone；`--shared` 复制会向原 promisor remote 请求未缓存对象。
- 影响：native inputs 尚未生成，后续 plan/build 未执行。
- 错误做法：把临时 checkout 当作完整本地仓库，用 `git clone --shared` 复制。
- 正确做法：在同一 runner 临时 checkout 上短时应用兼容补丁，完成 installhdrs 后在同一过程回滚；不复制 promisor Git metadata。
- 证据：run `45867874002` failed at `Prepare exact native inputs`; log reports `could not fetch ... from promisor remote` during `git clone --shared`.
- 自动化入口：`scripts/ci/prepare_native_inputs.py` 的 source staging。
- 下一次触发：任何 partial checkout 的临时源树复制。

## L-2026-11-26-09 CI script executable-bit assumption

- 现象：native inputs preparation 在 runner 上启动 `patch_xnu_host_tools.py` 时返回 `PermissionError: [Errno 13] Permission denied`。
- 根因：Git checkout 保留的脚本文件模式不是 executable，准备脚本直接 exec 了它。
- 影响：native inputs 尚未生成，native build 未执行。
- 错误做法：依赖仓库脚本的 executable bit。
- 正确做法：由 `sys.executable` 显式调用 Python 脚本；workflow 中的 Python 工具不依赖文件模式。
- 证据：run `45869025831` failed at `Prepare exact native inputs`; log shows `PermissionError` for `scripts/ci/patch_xnu_host_tools.py`.
- 自动化入口：`scripts/ci/prepare_native_inputs.py`。
- 下一次触发：任何 CI Python helper 调用。

## L-2026-11-26-10 SDK public headers missing from fakeroot

- 现象：XNU installhdrs passed, but `libcc_kext` preparation failed because `Libc/include/inttypes.h` could not find `Availability.h`.
- 根因：native fakeroot contained generated XNU headers but not the public `Availability*.h` headers from the selected iPhoneOS SDK.
- 影响：native inputs and kernel link did not start.
- 错误做法：把 generated XNU headers 当作完整 SDK header closure。
- 正确做法：copy the selected iPhoneOS SDK `usr/include/Availability*.h` and `TargetConditionals.h` into fakeroot, record the copied names and tree hash.
- 证据：run `45870056186` failed in `Prepare exact native inputs` at `libcc_kext` compile with `fatal error: 'Availability.h' file not found`.
- 自动化入口：`scripts/ci/prepare_native_inputs.py`。
- 下一次触发：任何 compiler-rt/libcc_kext preparation。

## L-2026-11-26-11 SDK cdefs include closure

- 现象：`Availability.h` 已纳入 fakeroot，但 compiler-rt 的 `Libc/include/stdio.h` 仍在 `__cold` 处解析失败。
- 根因：Libc public headers 还依赖选定 iPhoneOS SDK 的 `sys/cdefs.h`，compiler-rt 编译命令没有把 SDK `usr/include` 放入 include 搜索路径。
- 影响：native inputs 尚未生成，native build 未执行。
- 正确做法：将选定 SDK `usr/include` 作为显式 compiler-rt include 输入，并在实际 argv/provenance 中保留该路径。
- 证据：run `45871371371` failed at `Prepare exact native inputs`; log reports `stdio.h:200:28: error: expected function body after function declarator` at `__cold`.
- 自动化入口：`scripts/ci/prepare_native_inputs.py`。
- 下一次触发：任何 Libc/compiler-rt archive preparation。

## L-2026-11-26-12 unifdef exit semantics

- 现象：XNU headers、SDK include、Availability headers 和 `libcc_kext.a` 均已生成，但 firehose header preparation 失败。
- 根因：`unifdef` 返回码 1 表示输出发生变化，不表示命令失败；旧 `build-firehose.sh` 已明确接受 0/1，新 helper 使用 `check=True` 错误拒绝了 1。
- 影响：native inputs 尚未完成，native build 未执行。
- 正确做法：接受 `unifdef` 的 0 和 1，仅将其他返回码判为失败。
- 证据：run `45872635784` failed at `Prepare exact native inputs`; command was `/usr/bin/unifdef ... firehose_buffer_private.h`, exit code 1.
- 自动化入口：`scripts/ci/prepare_native_inputs.py`。
- 下一次触发：任何 unifdef header preprocessing。

## L-2026-11-26-13 XNU kernel private include root

- 现象：`libcc_kext.a` 成功生成，firehose 编译失败，找不到 `<os/atomic_private.h>`。
- 根因：XNU installhdrs 将该头放在 `usr/local/include/kernel/os`，firehose argv 没有把 `usr/local/include/kernel` 作为 include root。
- 影响：native inputs 尚未完成，native build 未执行。
- 正确做法：在 firehose 编译中显式加入 `fakeroot/usr/local/include/kernel`，并在编译前检查 `atomic_private.h` 存在。
- 证据：run `45873852552` failed at `Prepare exact native inputs`; log reports `firehose_buffer.c:21:10: fatal error: 'os/atomic_private.h' file not found`.
- 自动化入口：`scripts/ci/prepare_native_inputs.py`。
- 下一次触发：任何 XNU kernel private header consumer。

## L-2026-11-26-14 Darwin dependency generation mismatch

- 现象：XNU headers and `libcc_kext.a` preparation passed, but libfirehose from libdispatch 1477 failed on missing `os/atomic_private.h`.
- 根因：libdispatch 1477 expects a newer private atomic interface absent from XNU 4903/Darwin 18; the same-generation libdispatch 913 path uses `os/internal/atomic.h`, supplied by libplatform 177 private headers.
- 影响：native inputs and kernel link remained unverified.
- 正确做法：pin libdispatch 913.60.2 and libplatform 177.270.1 for the XNU 4903 native input recipe, copy their private atomic/lock headers, and record both versions in provenance.
- 证据：run `45876628778` failed at `Prepare exact native inputs`; `firehose_buffer.c` included `os/atomic_private.h`, absent from the XNU 4903 and libdispatch 1477 trees.
- 自动化入口：`scripts/ci/prepare_native_inputs.py` and native input manifest.
- 下一次触发：任何 cross-generation Darwin dependency selection.

## L-2026-11-26-15 same-generation firehose header branch

- 现象：切换到同代 libdispatch 913/libplatform 177 后，准备脚本仍在 firehose 编译前拒绝，声称 XNU installhdrs 缺 `os/atomic_private.h`。
- 根因：脚本的前置检查仍写死 libdispatch 1477 的 `<os/atomic_private.h>`，没有按实际 firehose source 的 `<internal/atomic.h>` include contract 分支。
- 影响：同代 private atomic header 已 staged，但 native inputs 仍未完成。
- 正确做法：根据 `firehose_buffer.c` 的实际 include 选择 XNU `atomic_private.h` 或 libplatform `os/internal/atomic.h`，未知 include 直接失败。
- 证据：run `45878934377` failed before firehose compile at the hard-coded `atomic_private.h` precheck; libdispatch 913 source uses `<internal/atomic.h>`.
- 自动化入口：`scripts/ci/prepare_native_inputs.py`。
- 下一次触发：任何依赖版本切换后的 firehose preparation。

## L-2026-11-26-16 native input tree hash function

- 现象：XNU headers、`libcc_kext.a` 和 `libfirehose_kernel.a` 均生成，但 manifest 写入阶段对 fakeroot 目录调用 file SHA-256，触发 `IsADirectoryError`。
- 根因：输入闭包需要 tree hash，而 helper 只有单文件 hash。
- 影响：native input manifest 未生成，native build 未执行。
- 正确做法：使用与 native builder 相同的名称、类型、权限、symlink 和文件内容 tree digest。
- 证据：main native run `45879966044` failed at manifest creation with `IsADirectoryError` on `fakeroot`.
- 自动化入口：`scripts/ci/prepare_native_inputs.py`。
- 下一次触发：任何 fakeroot/SDK overlay provenance 写入。

## L-2026-11-26-18 eMMC fallback coordinator boundary

- 现象：TF/eMMC fallback contract can describe the desired state matrix, but `NativeSdcard` and `NativeSdcc` currently register independently and no XNU root coordinator selects the alternate UUID.
- 根因：root selection in XNU 4903 waits on the published `boot-uuid-media` resource; TF failure does not automatically substitute an eMMC UUID.
- 影响：fallback implementation remains unverified and cannot be treated as a boot-ready feature.
- 正确做法：candidate XNU patch is opt-in under `XNU_Y35A_STORAGE_FALLBACK`, requires explicit `emmc-boot-uuid`, and switches only after the TF UUID wait fails; keep it outside native build/package inputs until its source/link/package gates pass.
- 证据：XNU 4903 `IOKitBSDInit.cpp` root wait path lines 600-650 in the pinned upstream source; candidate patch `patches/xnu/native-y35a-tf-emmc-root-fallback.patch` SHA-256 `f886e829b94999e79af06964ee274992d975382827191912d2ab8c8a8bd291eb` passes `git apply --check` against that source.
- 自动化入口：`tests/test_y35a_tf_emmc_root_fallback_patch.py` and `ci/manifests/r208-root-fallback-contract.json`。
- 下一次触发：before adding the candidate patch to native build/package inputs, require linked XNU and package/probe evidence.

## L-2026-11-27-01 libdispatch Firehose ABI closure

- 现象：native build 已通过输入准备，`libkern/os/log.c` 的第一组 Firehose 符号在启用 `OS_FIREHOSE_SPI` 后消失，但 `bsd/kern/subr_log.c` 仍缺 `FIREHOSE_BUFFER_KERNEL_DEFAULT_*` 和 `__firehose_kernel_configuration_valid`。
- 根因：`libdispatch-913.60.2` 提供同代 `internal/atomic.h` 路径，却没有 XNU 4903 `subr_log.c` 需要的 Firehose 配置 API；这些 API 位于 `libdispatch-1477.100.9`。1477 的 `firehose_buffer.c` 直接 include `os/atomic_private.h`，需要显式兼容头转接到已固定的 libplatform 177 internal atomic header。
- 影响：只切换依赖版本或向 `log.c` 添加声明都不能形成完整输入闭包。
- 正确做法：回到 1477，记录真实版本；在 `prepare_native_inputs.py` 生成带 `__OS_EXPOSE_INTERNALS_INDIRECT__` 的 `os/atomic_private.h` compatibility header，继续由 CI 编译和验证。
- 证据：native run `45956827212` 的 `build.log`；同代 libdispatch 913/1477 的 `os/firehose_buffer_private.h` 与 `src/firehose/firehose_buffer.c`。
- 自动化入口：`scripts/ci/prepare_native_inputs.py`、native input manifest 和 native build workflow。
- 下一次触发：任何 XNU 4903 Firehose 版本切换或私有头适配。

## L-2026-11-27-02 embedded KEXT vtable ABI must match XNU headers

- 现象：native XNU 4903 builds reached final link but failed on 122 `_RESERVED*` references emitted by `libQcomSdcard.a(IOStorageFamily-QcomSdcard.o)`; the errors included `OSMetaClass`, `IORegistryEntry`, `IOService`, and related base classes.
- 根因：driver compile passed `XNU_KERNEL_PRIVATE` without `CONFIG_EMBEDDED`, so `OSMetaClass.h` selected `APPLE_KEXT_VTABLE_PADDING=1` and `APPLE_KEXT_ALIGN_CONTAINERS=0`. XNU 4903 embedded kernel uses `CONFIG_EMBEDDED` and its exported header view selects padding 0/alignment 1. This is a compile-time header-view mismatch, not a missing IOService object or an IOStorageFamily version mismatch.
- 影响：all storage-derived class vtables had a different reserved-slot layout from the target kernel; forcing or stubbing the missing methods would conceal the ABI error and corrupt class layout.
- 正确做法：compile NativeSdcard and every IOStorageFamily support object with `CONFIG_EMBEDDED=1`; run a static-assert compile probe requiring `APPLE_KEXT_VTABLE_PADDING=0` and `APPLE_KEXT_ALIGN_CONTAINERS=1`; inspect archive undefined symbols and reject `_RESERVED*` imports before upload.
- 证据：runs `45960088944`, `45964692949`, and `45969385915`; XNU 4903 `libkern/libkern/c++/OSMetaClass.h:119-140,2056-2062,2122-2128`; XNU `iokit/Kernel/IOService.cpp:7213-7270`; run `45969385915` `link.filelist` confirms base objects are included. The inference from the old archive's `_RESERVED*` imports to padding mode is independently checked by the `CONFIG_EMBEDDED` branches in the pinned header.
- 自动化入口：`scripts/ci/compile_r208_sdcard.py` and `tests/test_r208_storage_abi_contract.py`, run by `.github/workflows/r208-tf-validation.yml`.
- 下一次触发：any external C++ KEXT/base-family objects force-loaded into an embedded XNU kernel.

## L-2026-11-27-03 native static gates must match the build candidate

- 现象：Run `45993248246` successfully completed native `installhdrs` and kernel link, then marked the build failed because `verify_phase_instrumentation.py` required R326/R68E7 diagnostic symbols, carrier slots, and historical handoff markers absent from the R208 candidate.
- 根因：The native runner unconditionally used the legacy R326 phase verifier for every 4903 build profile. Those checks were unrelated to R208's force-loaded storage driver and caused a false rejection after a real linked Mach-O already existed.
- 影响：The kernel artifact contract and upload were skipped, so the linked candidate was not reusable by the package workflow; the run provided no accepted kernel artifact.
- 正确做法：Pin a candidate-specific static verifier path and SHA in both native/source provenance. For R208, validate arm64 Mach-O structure, successful recorded installhdrs/build steps, post-compatibility staged-source hash/diff, profile flags, driver archive/manifest provenance, and the required force-loaded symbols in the final kernel. Retain a separate diagnostic kernel artifact on any post-link gate failure; only publish the package-consumable `unixnu-kernel-*` artifact after the candidate gate passes.
- 证据：Run `45993248246` build provenance records linked kernel bytes and `driver_integration.status=passed`; its `kernel-static-verification.log` fails on legacy R326 markers such as `_native_early_fault_address`, `ARMENTRY`, `PREMMU00`, and R68E7 slots.
- 自动化入口：`scripts/ci/verify_r208_native_kernel.py`, `scripts/build-xnu-4903-native.py`, `ci/native-build-manifest.r208.json`, and `.github/workflows/unixnu-native-build.yml`.
- 下一次触发：Every native candidate with a different instrumentation/build purpose than the legacy R326 probe ladder.

## L-2026-11-27-04 local verification is forbidden for UniXNU

- 现象：During the native-link audit, `git diff --check` was run on the local working tree.
- 根因：The CI-only constraint was followed for builds/tests but not for this local static check.
- 影响：That command is not an admissible UniXNU verification result and must not be cited as acceptance evidence.
- 正确做法：Run text checks, tests, static gates, and builds only in GitHub Actions; label any accidental local command as excluded evidence and rely on a matching Actions run.
- 证据：Codex local session command history for this task; no claim is derived from its result.
- 自动化入口：`.github/workflows/unixnu-validation.yml` and the candidate-specific GitHub Actions workflows.
- 下一次触发：Any UniXNU change review or pre-commit check.

## L-2026-11-27-05 GitHub artifact directories do not preserve filesystem metadata

- 现象：R208 的 RAM package 上传 `root-tree/` 目录供后续 TF/APFS job 使用，但 APFS root tree 的可执行位、owner、ACL 和 extended attributes 会参与 tree identity 与启动语义；普通目录 artifact 的传输模型不能作为文件系统快照。
- 根因：package job 的 `tree_sha256` 覆盖内容和元数据，而 Actions artifact 目录传输不保证保留 Unix mode。后续 runner 若直接使用下载目录，无法把原始构建树与恢复后的树等同。
- 影响：TF/APFS 中间镜像可能从被改变权限或 ACL 的树构造，或者跨 runner 的哈希比较拒绝有效输入；目录存在和文件内容 SHA 一致不足以闭合 filesystem provenance。
- 正确做法：将 root tree 封装为单个 PAX tar 作为权威传输输入；使用 `actions/upload-artifact@v7` 的 `archive: false` 单文件 artifact，并由 `actions/download-artifact@v8` 直接取回；附逐路径 metadata manifest 和 archive SHA；在 macOS producer 端用 metadata-aware extraction 做 round-trip tree hash。macOS 用 `--mac-metadata` 保存原生 ACL/resource metadata，另保存 xattrs 和 file flags，不用 `--acls` 把扩展 ACL 转换成 NFSv4 表示。consumer 校验 package run、两个 artifact ID/API digest、branch/commit、archive SHA 和恢复树 manifest 后才构建。普通目录 artifact 仅作浏览副本。
- 边界：derived-QCDT 生成的 GPT/APFS 镜像必须标记为 offline-control-only、non-bootable、non-system-image、`device_run_allowed=false`，不得覆盖 stock QCDT 或 TF 设备资格。
- 证据：GitHub Actions upload-artifact 官方说明的 file-permission limitation；R208 package run `46008544189` 成功上传 RAM package、而 `tf-apfs-intermediate` 被 skipped，未产生 TF/APFS 运行证据。
- 自动化入口：`scripts/ci/build_y35a_ci_package.py`、`scripts/ci/build_y35a_tf_apfs_image.py`、`.github/workflows/y35a-ci-package.yml` 与 `tests/test_y35a_tf_apfs_image.py`。
- 下一次触发：任何从 GitHub Actions artifact 把系统树交给另一个 runner、container builder 或镜像封装阶段的任务。

## L-2026-11-28-01 local UniXNU diff checks are excluded

- 现象：在 CI-only 项目工作树上再次执行了本机 `git diff --check`，本轮又重复执行一次。
- 根因：把通用 Git 文本检查误当成不属于项目静态门禁；实际目标合同明确本机不运行任何 UniXNU 静态验证。
- 影响：本机命令结果不得作为本次改动通过的证据；当前分支仍需精确 SHA 的 GitHub Actions 验证。
- 正确做法：本机只做编辑和只读人工代码审阅；不得调用任何本机项目验证命令，包括通用 Git diff check。所有 diff 检查、测试、门禁和构建都放入 GitHub Actions。提交信息不得写入这些本机命令为验证结果。
- 证据：2026-11-28 本机命令记录（本轮重复）；所有这些命令退出状态都不纳入验收，不据此得出通过结论。
- 自动化入口：`.github/workflows/y35a-ci-package.yml`。
- 下一次触发：任何 UniXNU package/workflow 改动的提交或验证。

## L-2026-11-28-02 preserve captured native tool errors in CI logs

- 现象：R208 offline-control run `46039400354` completed package/artifact identity checks, then failed at `hdiutil create` without exposing the tool's captured stderr.
- 根因：`subprocess.run(..., capture_output=True, check=True)` raised `CalledProcessError`; the workflow log showed only the command and exit code because the caller discarded `stdout` and `stderr`.
- 影响：The APFS intermediate remains unbuilt and the image-creation cause was not diagnosable from the run.
- 正确做法：Use a checked-command wrapper that reports the exact argv, exit code, stdout and stderr for subprocess failures. Diagnose the tool's actual message before changing image arguments.
- 证据：GitHub Actions run `46039400354`, job `tf-apfs-offline-control`, step `Build non-bootable derived-QCDT control image`, `hdiutil create` exit 1; artifact ID/digest and root tar download steps passed.
- 自动化入口：`scripts/ci/build_y35a_tf_apfs_image.py` and `tests/test_y35a_tf_apfs_image.py`.
- 下一次触发：Any CI subprocess that captures output and fails with check=True.

## L-2026-11-28-03 hdiutil empty-image type and output format are different options

- 现象：R208 offline-control run `46040773916` reached the macOS image builder after all artifact identity and tar restore gates passed, then failed at `hdiutil create`.
- 根因：The command used `-format UDRW` without `-srcfolder` or `-srcdevice`; hdiutil reported `-format requires -srcfolder or -srcdevice`. A follow-up attempt with `-type UDRW` also failed as an invalid `-type` argument.
- 影响：The derived-QCDT APFS control image was not created or uploaded. This is an image-builder command contract failure, not evidence against the root tree or QCDT provenance.
- 正确做法：For an empty image, use `-type UDIF` with `-size`, `-layout GPTSPUD` and `-fs APFS`; `UDIF` creates the writable UDRW image. `UDRW` is not a valid `-type` value. Preserve hdiutil stdout/stderr in failures.
- 证据：GitHub Actions run `46040773916` reported `-format requires -srcfolder or -srcdevice`; run `46041415209` reported `invalid argument for -type` when passed `UDRW`; the hdiutil manual distinguishes `-type UDIF` from the resulting UDRW image.
- 自动化入口：`scripts/ci/build_y35a_tf_apfs_image.py` and `tests/test_y35a_tf_apfs_image.py`.
- 下一次触发：Any macOS hdiutil empty-image creation or GPT/APFS intermediate builder.

## L-2026-11-28-04 use a recognized extension for hdiutil image output

- 现象：R208 offline-control run `46041901430` passed hdiutil create but `hdiutil attach` reported `No such file or directory` for the requested `.img` path.
- 根因：`hdiutil` selects/appends output extensions based on recognized disk-image suffixes; the create step did not prove that the requested `.img` path was the actual emitted file.
- 影响：The APFS intermediate was not attached or populated, so no image artifact was uploaded.
- 正确做法：Create to an explicit `.dmg` path, check that exact file exists and is non-empty, then rename it to the package's declared `.img` path before attach. Never assume a zero exit status means the path requested exists.
- 证据：GitHub Actions run `46041901430`, after `-type UDIF` the create command returned success; the next attach to `/Users/runner/work/_temp/y35a-tf-offline-control.apfs.img` failed `No such file or directory`.
- 自动化入口：`scripts/ci/build_y35a_tf_apfs_image.py` and `tests/test_y35a_tf_apfs_image.py`.
- 下一次触发：Any hdiutil create/convert step whose output suffix differs from the format-recognized extension.

## L-2026-11-28-05 diskutil plist may report GPT in Content, not PartitionMapType (superseded)

- 现象：R208 offline-control run `46042368705` successfully created, attached and force-unmounted the APFS volume, then the GPT/APFS gate rejected an empty `PartitionMapType`.
- 根因：The macOS `diskutil info -plist` whole-disk record did not populate `PartitionMapType`; the available whole-disk `Content` field carried the GUID partition-scheme fact.
- 影响：The image was structurally created and mounted, but the gate produced no control artifact because it required one plist key name rather than the partition-map fact.
- 更正：The earlier field-fallback recommendation is superseded by L-2026-11-28-06 and L-2026-11-28-08. `Content` may be an APFS partition-type GUID; do not treat it as partition-map scheme evidence.
- 证据：GitHub Actions run `46042368705`, job `tf-apfs-offline-control`, failure `TF image does not report a GPT partition map:` after the volume was force-unmounted.
- 自动化入口：`scripts/ci/build_y35a_tf_apfs_image.py` and `tests/test_y35a_tf_apfs_image.py`.
- 下一次触发：Any diskutil plist schema change or GPT/APFS image gate.

## L-2026-11-28-06 diskutil info Content can be an APFS partition-type GUID

- 现象：R208 offline-control run `46042907572` created, attached and unmounted the APFS image, but the GPT gate saw `Content=EF57347C-0000-11AA-AA11-00306543ECAC` and rejected it as a GPT partition map.
- 根因：`diskutil info -plist` for the selected whole-disk/parent device can expose a partition-type GUID in `Content`; that value is not the GUID partition-map scheme.
- 影响：The image and APFS volume were usable, but the GPT evidence was ambiguous and no control artifact was emitted.
- 正确做法：Use `hdiutil pmap -simple` on the image itself and accept only its explicit top-level scheme record; retain and verify the APFS volume-to-parent whole-disk identity from `diskutil info`. The pmap report is human-readable, so bind its exact bytes in the intermediate report rather than assuming a plist output mode.
- 证据：GitHub Actions run `46042907572`, job `tf-apfs-offline-control`, failure `TF image does not report a GPT partition map: EF57347C-0000-11AA-AA11-00306543ECAC`.
- 自动化入口：`scripts/ci/build_y35a_tf_apfs_image.py` and `tests/test_y35a_tf_apfs_image.py`.
- 下一次触发：Any GPT/APFS gate that infers the partition scheme from a partition's content GUID or omits volume-to-parent identity binding.

## L-2026-11-28-07 macOS runner Python may lack xattr APIs

- 现象：R208 package run `46037779595` failed while hashing the restored root tree with `AttributeError: module 'os' has no attribute 'listxattr'`.
- 根因：The macOS Actions Python runtime did not expose the Python xattr API expected by the producer-side metadata digest.
- 影响：The package could not complete its metadata-bound root-tree verification even though the tree contents were available.
- 正确做法：Use Python xattr APIs when present and fail over to the macOS `xattr` executable when they are absent; use `xattr -px` and decode hexadecimal output back to raw bytes before hashing, so both paths hash identical values. Preserve a fail-closed error when neither interface exists and add a structural fallback test so Linux validation does not skip this branch silently.
- 证据：Run `46037779595` failed at the package tree digest; run `46038856167` passed the same package path after commit `956abbb`, and run `46039400354` reached the later `hdiutil create` failure after the xattr stage.
- 自动化入口：`scripts/ci/build_y35a_tf_apfs_image.py`, `tests/test_y35a_tf_apfs_image.py` and `.github/workflows/y35a-ci-package.yml`.
- 下一次触发：Any root-tree metadata digest on a macOS Actions runner where Python xattr support is not guaranteed.

## L-2026-11-28-08 GPT evidence must be a scheme and bind the mounted volume

- 现象：R208 offline-control run `46044011970` created and mounted the APFS image, then rejected the GPT check after `diskutil list` exposed the APFS partition-type GUID `EF57347C-0000-11AA-AA11-00306543ECAC` rather than a top-level GUID partition scheme.
- 根因：Partition-type content and partition-map scheme are separate facts; a generic string search can mistake an APFS partition GUID for GPT, while accepting GPT plus APFS without requiring device identities leaves the parent-disk relationship unproven.
- 影响：No offline-control artifact was uploaded, and prior GPT checks did not establish that the inspected APFS volume belonged to the expected whole disk.
- 正确做法：Read the image's `hdiutil pmap -simple` output and accept only an explicit top-level `SCHEME` value of GPT/GUID partition scheme. Require the expected whole-disk identifier, returned whole-disk identifier, APFS volume identifier, and volume parent identifier; reject missing or mismatched values. Do not use `diskutil info` partition-content fields as a substitute for image scheme evidence. Keep APFS content/filesystem validation separate from the scheme check.
- 证据：GitHub Actions run `46044011970`, commit `10e998ac199dae277fb551deac35b3aa4ed65154`, failed in `tf-apfs-offline-control` at `Build non-bootable derived-QCDT control image`; log reported the APFS partition GUID as the supposed GPT evidence. No control artifact was emitted.
- 自动化入口：`scripts/ci/build_y35a_tf_apfs_image.py` and `tests/test_y35a_tf_apfs_image.py`.
- 下一次触发：Any GPT/APFS image validation or APFS-volume-to-parent-disk report.

## L-2026-11-28-09 hdiutil pmap requires the image to be detached

- 现象：R208 offline-control run `46047971221` passed package identity, artifact download, APFS creation, root-tree copy and metadata checks, then `hdiutil pmap -simple` failed with `Resource temporarily unavailable`.
- 根因：The image was still attached while the host tried to open the backing image file for its partition map; unmount/detach were only in the later cleanup block.
- 影响：The GPT scheme could not be read and no offline-control image artifact was uploaded. This run does not show an invalid GPT image or a failure in root-tree copy.
- 正确做法：After sync and diskutil info capture, successfully unmount the APFS volume and detach the image, then read `hdiutil pmap -simple` from the backing file. If unmount or detach fails, stop before scheme validation and keep cleanup best-effort in `finally`.
- 证据：GitHub Actions run `46047971221`, commit `a739997574207411b916c0c04b10849f3e9ac508`, step `Build non-bootable derived-QCDT control image`; stderr was `hdiutil: pmap: unable to open ... - Resource temporarily unavailable`.
- 修复验证：Actions run `46049301112` on commit `23502821148473f4baa411ec4dfe81745a4a9aa7` passed the `tf-apfs-offline-control` job and uploaded artifact `y35a-tf-apfs-offline-control-46049301112` (ID `15224410131`, digest `sha256:4182dbabd5303ffb1a348221150a774ac7b1b308504573afd1c0ec1edadd3c74`). The image SHA-256 is `8b7fae9326a0530f231487e1b48735b92780069aa11bef970b38e74c8bf093d4`; the report records explicit GPT scheme, whole disk `disk6`, APFS volume `disk6s1`, and parent `disk6`.
- 自动化入口：Commit `518f8f4` adds `detach_and_read_partition_map()` and `test_partition_map_read_waits_for_unmount_and_detach` in the TF/APFS builder and tests.
- 下一次触发：Any hdiutil operation that reads an image backing file after a mounted image was modified.

## L-2026-11-28-10 exact-source apply gate must resolve patch paths before changing cwd

- 现象：Fallback v2 source-gate run `46054142955` failed at `git apply --check` before evaluating patch hunks; stderr output was hidden in the script traceback, while the command passed a repository-relative patch path from inside the XNU checkout.
- 根因：The verifier resolved the patch path relative to the package repo but invoked Git with `cwd` set to the temporary XNU clone. Git returned 128 because it could not find the relative patch path; this was a verifier path error, not an XNU patch-context rejection.
- 影响：Exact-source applicability remains unverified. Package contract unit tests passed, but the workflow stopped before its TF/APFS design gate and package jobs were skipped.
- 正确做法：Resolve the manifest-pinned patch to an absolute readable path before invoking `git -C <exact-source> apply --check`, verify source HEAD equals the pinned commit, and preserve command/stdout/stderr on failure. Report `apply-check` only after Git returns zero.
- 证据：Actions run `46054142955`, commit `b2c97a3baad03631c1ae1ba3bad94b95b466b052`, step `Verify fallback v2 applies to exact XNU source`; Git exited 128 at `git -C <temp>/xnu apply --check patches/xnu/native-y35a-tf-emmc-root-fallback-v2.patch`.
- 自动化入口：`scripts/ci/verify_r208_fallback_v2_source.py` and package validation in `.github/workflows/y35a-ci-package.yml`.
- 下一次触发：Any CI step that runs a repository-relative input path after changing cwd or using `git -C`.

## L-2026-11-28-11 native candidate provenance hash must match its own manifest

- 现象：Fallback-v2 native execute run `46057855212` passed exact-source apply and all native input preparation, then stopped before compilation with `native source provenance SHA-256 does not match native build manifest`.
- 根因：The candidate manifest was copied from the production manifest and retained its old provenance digest `7dcb2b64...`; the new fallback-v2 provenance file had a different measured SHA.
- 影响：No compile or link ran and no kernel artifact was produced. The run does not evaluate the fallback source or kernel.
- 正确做法：Read the exact expected and actual digest from the CI preflight diagnostic, update only the candidate manifest binding, and rerun source/plan gates before the next execute build. Preserve the production manifest unchanged.
- 证据：Run `46057855212` on source workflow SHA `7672b05d4c3235951925fa825c21403a84ce5c72` reported old expected digest `7dcb2b64efbe9c094acd0f0ca68ca278089770dc6c398fb5c9859c95f5aa66d5`; exact file digest was `3cfcc009098eb9316f69675028f1ce8344b6e54babb46b3b2a51c2d47f0ea905`.
- 自动化入口：`ci/native-build-manifest.r208-fallback-v2.json`, `ci/native-source-provenance.r208-fallback-v2.json`, and native manifest validation in `scripts/ci/run_native_build.py`.
- 下一次触发：Any isolated candidate manifest copied or derived from a production native manifest.

## L-2026-11-28-12 package validator must consume the native artifact's selected manifest

- 现象：Package run `46062519190` downloaded a successful kernel artifact and passed toolchain/firmware preparation, then failed with `native build plan does not bind the package's R208 build manifest`.
- 根因：`build_y35a_ci_package.py` always compared the artifact plan against `ci/native-build-manifest.r208.json`, even though native run `46061043371` used the isolated fallback-v2 candidate manifest.
- 影响：The kernel artifact was valid for its exact candidate plan, but package construction and artifact upload did not occur. No RAM package or root-tree artifact came from this run.
- 正确做法：Select the exact native manifest as a restricted workflow input, validate it is one of the repository's allowed R208 manifests, compare the artifact plan/provenance against that manifest, and include its path/SHA plus the native artifact API ID/digest in package provenance. For manual dispatch, require the exact kernel artifact ID and API digest; keep the production manifest as default for normal workflow runs.
- 证据：Run `46062519190`, SHA `88387d1bc19262d5984d75fe837fb69d9bca2479`, package job `Build and verify RAM-boot package`; native run `46061043371` produced successful schema-2 artifact ID `15228783166`, digest `sha256:818e0f39a3e6aaedb0d51c5636015b0ea17fc0efc2ac1b5049ca1820ebb021e2`.
- 自动化入口：`scripts/ci/build_y35a_ci_package.py`, `.github/workflows/y35a-ci-package.yml`, `tests/test_ci_y35a_package.py`.
- 下一次触发：Any package run consuming a native artifact built from a non-default or experiment-specific manifest.
