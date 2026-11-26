# UART 静态报告范围更正 — 20261124T232133Z

## 影响

本报告更正本辅助会话此前两份 UART 报告的结论范围，不否定 pristine `pe_serial.c` 的拒绝路径，
也不新增或重复 UART 实现。此前“当前生成 uart0 被拒绝”的表述只在未应用
`native-uartdm-console.patch` 或 `XNU_NATIVE_UARTDM=0` 时成立；仓库已存在显式启用后的 v1.4 分派实现和主机契约测试。

## 事实（static）

1. `scripts/y35a/make_adt.py:64-65` 生成 `qcom,msm-uartdm-v1.4` 与相对 `reg`。
   原始 DT 的 `qcom,msm-lsuart-v14` 是另一种字符串；两者不能混为同一兼容项。
2. pristine `upstream-refresh/2026-11-11/sources/xnu-ios12/repo/pexpert/arm/pe_serial.c:940-956`
   的 S3C 分派只接受四个 Samsung/16550 字符串，因此拒绝两种 Qualcomm 字符串。
3. `patches/xnu/native-uartdm-console.patch:8-71` 增加 `XNU_NATIVE_UARTDM` 分支，
   `uartdm_probe()` 使用有界 NUL 字符串列表匹配 `qcom,msm-uartdm-v1.4`，通过后注册 UARTDM TX 后端；
   该 patch 不接受 `qcom,msm-lsuart-v14`。
4. `scripts/test-uartdm.py:27-44` 在主机 worktree 应用同一 patch，并编译运行 leaf 与 dispatch 测试；
   `tests/uartdm/test_dispatch.c:104-138` 覆盖启用后接受生成 v1.4、关闭时保留 PL011、边界与映射失败。
   `scripts/build-xnu-4k-baseline.sh` 提供默认关闭的 opt-in 配方。
5. 本次遵守离线限制，没有运行该编译测试、内核构建或设备操作；上述均为源码/测试脚本核对，不是 fresh 运行结果。

## 待确认

- R191 实际 prepared recipe 是否应用该 patch 且 `XNU_NATIVE_UARTDM=1`。
- 对应链接内核是否含 UARTDM 分派，以及真机是否有 TX 输出；runtime qualification 仍为 false。

## 推断

若实际配方未启用该 patch，则 pristine 拒绝结论仍适用于该配方；若已启用，则生成 v1.4 的静态拒绝结论不适用。
不能仅凭 pristine 快照推断当前内核的控制台状态。

## 单一步骤建议

主线在下一次 R191 host gate 中增加一项只读配方/链接符号核对：确认 patch 应用与
`XNU_NATIVE_UARTDM=1` 后再解释 UART 行为；不要先改 ADT，也不要据本报告宣称真机控制台已工作。

## 证据 SHA-256

| 路径（相对权威工作树） | SHA-256 |
|---|---|
| `patches/xnu/native-uartdm-console.patch` | `c99275dd9ca8785de208a0109c9da779895f584f94a55b4bd52577519c37666a` |
| `scripts/test-uartdm.py` | `aab634b9c710965607f2a83631905bae714cc09c2e97aec8e3430c02f4ebd4c6` |
| `tests/uartdm/test_dispatch.c` | `3bd7c9c5ed80e0bf5893d078f16fe0e49aad5e5b35db592bf72a069595b79c5e` |
| `tests/uartdm/test_uartdm.c` | `8a48ba35a701c1027e53bfced329df8b5ef1b96c46e8fa150d28577f06363f2f` |
| `scripts/build-xnu-4k-baseline.sh` | `99f046563ef4450eadb2b4a4cb25ce3e6cde67ed18c5d02b245b3c09721676cd` |
| `scripts/y35a/make_adt.py` | `d9d4d8874d6b7d8b59bc06094aa396598f672950d0dee762b2ce9ea542af244e` |
| `upstream-refresh/2026-11-11/sources/xnu-ios12/repo/pexpert/arm/pe_serial.c` | `e1884c9d8f79da5912bc7c8ff6d428615290e46e2fe1fb5f9e87c0edfa3f4117` |
| `evidence/y35a-20261102/boot3-20261106/touch-t02-20261109/dtb10-cache/dtb10.dts` | `4b2a7fda53ab9b4a69aa3bf9c1247feb7f767b577612914b353f076b391a8714` |

## 边界

未修改共享状态文件，未触碰设备、USB、fastboot、adb、串口或持久分区。未能直发 Codex thread。
