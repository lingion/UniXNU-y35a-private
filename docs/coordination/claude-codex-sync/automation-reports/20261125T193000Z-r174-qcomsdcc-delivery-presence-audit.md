# 当前 R174 代际未携带 QcomSdcc，历史存储链接不能继承为验收

时间: 2026-11-25T19:30:00Z
范围: 仅离线读取；未构建、未探测设备、未修改共享状态文件。

## 影响

当前 R174 HID4 微边界内核不是存储驱动候选。其实际 Mach-O 全局符号表没有 QcomSdcc/IOStorageFamily/ArmDTPlatform/ArmCpu，构建 provenance 也没有 driver integration。任何关于 R174 的存储、eMMC、IOMedia 或平台驱动结论都必须保持“未测试”；这不构成 Qcom 硬件失败证据，也不否定历史 R193/R194/R319 的独立结果。

## 事实

主线最新运行已把 R174 边界收窄到 `ARM64_IS_PCORE` 后、HID4 读取完成前，并在修正 8 字节 marker 文案契约。本轮未复查或重做该设备证据。

对当前 R174 原生内核做只读 `xcrun nm -g -j` 审计：

- 内核: `/Users/lingion_k/unixnu-research/reboot-checkpoints/R174-hid4-micro-native-build-20261125-01/obj/DEVELOPMENT_ARM64_T7001/mach.development.t7001.unstripped`
- SHA-256: `87286c16d10072f38d4b40f66430ee2cd945126a92dd9fa2274f4a6a358b0304`
- `NativeSdcc` 匹配数: 0
- `native_sdcc_` 匹配数: 0
- `IOBlockStorageDevice` 匹配数: 0
- `ArmDTPlatform` / `ArmCpu` 匹配数: 0 / 0
- `_gIOKernelConfigTables` 存在，说明符号表读取有效；该单一内核配置符号不代表三个驱动组件已链接。

独立构建 provenance SHA-256 为 `005c12c102099f84a0f40a559515035a2da521470b163196b2c3abef3a5c962f`，状态 `complete`，但没有 `driver_integration` 字段，staged inputs 中也没有 driver/archive 项。kernel 符号审计与 provenance 相互印证：R174 没有走 QcomSdcc 的强制加载路径。

现有交付契约明确要求显式输入：

- `components.toml` 将 QcomSdcc 标为 `force_load=true`、`integration_role=userdata-window`，4903 consumer 为 `scripts/build-xnu-4903-native.py`。
- `scripts/build-xnu-4903-native.py:39-44` 要求 role `userdata-window`，并检查 `_native_sdcc_probe_bound`、`_native_sdcc_started`、`_native_sdcc_store_attached` 三个符号存在。
- `scripts/y35a/build_arm_driver_4903.py:59-64` 定义同一 role/force_load/consumer 契约。
- `scripts/y35a/make_adt.py:66-80` 会生成 `sdhc1` 节点，compatible 为 `qcom,sdhci-msm`，reg 顺序为 hc/core。ADT 节点存在不等于匹配驱动存在。

驱动源码当前仍是只读 Phase 1：`NativeSdcc.cpp:121` 报告写保护，`:222` 拒绝非输入方向，`:108-109` 拒绝格式化/弹出。历史 LOG 已记录 R193/R194 链接和 R88 前未观察 attach、R319/R326 全回读 BSS 为零；本轮没有重复这些实验。

## 待确认

- 未来存储候选是否重新链接当前 QcomSdcc、IOStorageFamily、ArmDTPlatform 和 ArmCpu。
- 重新链接后能否通过新的 source/link/package/probe 哈希门。
- StartIOKit/platform/provider 路径是否能让 `probe()`/`start()` 产生新鲜、可绑定的证据。
- eMMC 容量、GPT、IOMedia 发布和只读挂载仍未在当前代际验收。

## 推断

R174 的 driver-free 状态符合其 HID 诊断构建目的，不应视为回归；但它也意味着不能用 R174 的后续 HID 成功来推进“存储驱动已验收”的结论。历史 QcomSdcc 对象/链接成果只能作为未来独立存储候选的输入。

## 证据与 SHA-256

- `/Users/lingion_k/unixnu-research/UniXNU-y35a/components.toml`
  - `bc0609d126c050650dbe94136cad6071ef73b23d30e99fdbb9faf41f78a9c53a`
- `/Users/lingion_k/unixnu-research/UniXNU-y35a/drivers/QcomSdcc/NativeSdcc.cpp`
  - `e99058e3a2227190fa7ab1ccbe65e3bf4e236c806359925c1e067ae0c4685815`
- `/Users/lingion_k/unixnu-research/UniXNU-y35a/drivers/QcomSdcc/SdciCore.h`
  - `e8d7061a24ddb35de6a3a8ffa0b4b6103b7c719763599599d95957fb7b57ef00`
- `/Users/lingion_k/unixnu-research/UniXNU-y35a/drivers/QcomSdcc/PersistStore.h`
  - `4927e5f72c5985445de9a408d45414742cbc37de4c7817b2eab69f6d096b9bd6`
- `/Users/lingion_k/unixnu-research/UniXNU-y35a/scripts/build-xnu-4903-native.py`
  - `89860d84982fa6ed7c571dc168869ab9088859c84087c0a4965f6d85a5b269ca`
- `/Users/lingion_k/unixnu-research/UniXNU-y35a/scripts/y35a/build_arm_driver_4903.py`
  - `23e79a8ce39edf3b4ccce132dac67f14e1661f368fbc00ede964a9acb6c630e7`
- `/Users/lingion_k/unixnu-research/UniXNU-y35a/scripts/y35a/make_adt.py`
  - `d9d4d8874d6b7d8b59bc06094aa396598f672950d0dee762b2ce9ea542af244e`
- R174 `build-provenance.json`
  - `005c12c102099f84a0f40a559515035a2da521470b163196b2c3abef3a5c962f`
- R174 内核
  - `87286c16d10072f38d4b40f66430ee2cd945126a92dd9fa2274f4a6a358b0304`

## 单一步骤建议

为下一次独立 QcomSdcc 存储候选增加一个生成门：只有构建 provenance 记录匹配的 `userdata-window` driver manifest/archive SHA，且最终内核 nm 含三个 `native_sdcc_*` 必需符号时，才允许生成存储 package/probe；未满足时在 manifest 明确标注 `storage_driver_present=false`。
