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
