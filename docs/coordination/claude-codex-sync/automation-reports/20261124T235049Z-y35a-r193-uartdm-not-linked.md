# R193 UARTDM 配方与链接产物不一致 — 20261124T235049Z

## 影响

`scripts/y35a/build_native.py` 设置 `XNU_NATIVE_UARTDM=1`，但本次核对的 R193 prepared source、applied-patch 清单和链接内核均未出现 UARTDM 实现。该宏本身不会创建后端；不能把配方宏当作控制台已启用。

## 事实（static / binary inspection）

- R193 kernel artifact SHA-256 为 `396f1d7a78ed1948f7ff57b89b27f2e32ba295e09d9bc807f1dffac8d413323d`，与 `kernel-artifact.json` 一致。
- provenance 的 applied patches 不含 `native-uartdm-console.patch`，inputs 补丁也不含 `XNU_NATIVE_UARTDM` 或 `uartdm_probe`。
- prepared source 中找到 2 个 `pe_serial.c`，均不含 `uartdm_probe` / `XNU_NATIVE_UARTDM`。
- 链接内核 bytes 不含 `qcom,msm-uartdm-v1.4`、`uartdm_probe` 或 `uartdm_serial_functions`。

## 待确认

- 主线的 prepared recipe 是否有另一条未反映在 provenance 的 UARTDM 注入路径。
- 真机 TX 行为未验证；runtime qualification 保持 false。

## 推断

若 provenance 完整，则 R193 实际未启用 UARTDM 后端，pristine S3C 兼容分派仍会拒绝生成的 `qcom,msm-uartdm-v1.4` 节点。

## 单一步骤建议

在主线 UART 工作单独认领后，将已有 `patches/xnu/native-uartdm-console.patch` 纳入 prepared source，并用一次 host build 同时核对 applied-patch provenance 与链接内核兼容串；不要为此改动 R193 marker/carrier 或先上机。

## 证据 SHA-256

| 路径 | SHA-256 |
|---|---|
| `/Users/lingion_k/unixnu-research/reboot-checkpoints/R193-page-config-native-build-20261125-01/build-provenance.json` | `67dc13f62224c4636ffed13af04a574a682660f0153c45ad8036d36bcf791ca5` |
| `/Users/lingion_k/unixnu-research/reboot-checkpoints/R193-page-config-native-build-20261125-01/kernel-artifact.json` | `58439dd2ef0fa40f8760afa0c208d566519d146fdd35f47f93f2160c4e23f5a7` |
| `/Users/lingion_k/unixnu-research/reboot-checkpoints/R193-page-config-native-build-20261125-01/obj/DEVELOPMENT_ARM64_T7001/mach.development.t7001.unstripped` | `396f1d7a78ed1948f7ff57b89b27f2e32ba295e09d9bc807f1dffac8d413323d` |
| `/Users/lingion_k/unixnu-research/reboot-checkpoints/R193-page-config-native-build-20261125-01/src/pexpert/i386/pe_serial.c` | `f611f7b6730200d5e7649b03237a9383657c3f3df052ffd34ec9b986eb003ca3` |
| `/Users/lingion_k/unixnu-research/reboot-checkpoints/R193-page-config-native-build-20261125-01/src/pexpert/arm/pe_serial.c` | `e1884c9d8f79da5912bc7c8ff6d428615290e46e2fe1fb5f9e87c0edfa3f4117` |

未运行构建或设备操作；未能直发 Codex thread。
