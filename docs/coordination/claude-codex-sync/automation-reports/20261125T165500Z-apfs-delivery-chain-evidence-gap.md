# APFS 交付链证据缺口离线核查

- 时间：2026-11-25（本地周期；UTC 文件名锚点 2026-11-25T16:55:00Z）
- 范围：仅离线读取；未操作设备、USB、fastboot、adb、串口、持久分区，未运行构建或刷机。
- 主线边界：不重复 R167/R168 SCTLR 窗口、触摸/I2C 资产审计、R94–R99、R136 或 R137。

## 证据与 SHA-256

1. `out/ipsw/16G102/kernelcache.decompressed.json`
   - SHA-256：`c66b4df32a10d0ef4a6627df4b89abcc6f40fc98a8a416415e62e73dc2965d91`
   - 该 JSON 是解包摘要，含 `macho.prelink_kext_entries_with_exec`、`macho.prelink_bundle_identifier_entries` 等字段；全文对 `apfs`、`APFS`、`AppleFileSystem`、`filesystems` 的大小写不敏感匹配均为 0。
2. `components.toml`
   - SHA-256：`bc0609d126c050650dbe94136cad6071ef73b23d30e99fdbb9faf41f78a9c53a`
   - 对同一组 APFS/文件系统关键字的匹配为 0。
3. `scripts/data/ios12-root-staging-evidence.json`
   - SHA-256：`77e3bb71680ede73b4c185c14a811de390ab0cff9de91db6f587e837d7198f33`
   - 记录真实 OS 卷为大小写敏感 APFS，`used_bytes=3933454336`；当前 bring-up staged tree 为 58 个 Mach-O 的 HFS+ 根，`hfs_image.bytes=42991616`，并记录 iOS 12 无 `System/Library/KernelCollections`。

## 事实

- 当前本地交付证据明确区分了真实 APFS OS 卷与临时 HFS+ bring-up 根。
- 组件注册表没有显式 APFS 组件项。
- 现有 kernelcache 解包摘要没有列出可识别的 APFS bundle 名称；该文件是摘要而非完整 `__PRELINK_INFO` 导出，因此不能据此断言原始 kernelcache 不含 APFS。

## 待确认

- 精确 16G102 kernelcache 的 `__PRELINK_INFO` 中 APFS KEXT 的 bundle identifier、可执行段 UUID/SHA-256、依赖与启动语义。
- 当前 R154/R159 交付 kernel 是否实际携带该 APFS 组件，以及其与存储控制器层的接口闭合状态。

## 推断与影响

- 两个独立本地证据（staging evidence 与组件注册表）都未提供“APFS 驱动已进入当前交付链”的可复核产物身份；更稳妥的状态是“交付证据缺口”，不是“设备没有 APFS 驱动”。
- 这不阻塞当前 R168 的 RAM-only SCTLR 诊断，但意味着不能把 HFS+ bring-up 根当作耐久 OS/Data 路线已就绪。

## 单一步骤建议

离线从精确解压后的 16G102 kernelcache 导出 `__PRELINK_INFO,__xml`，只记录 APFS KEXT 的 bundle identifier、可执行 UUID/SHA-256 与依赖闭包；在取得这些身份前，不安排 APFS 根设备实验。
