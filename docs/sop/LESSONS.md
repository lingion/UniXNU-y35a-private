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
