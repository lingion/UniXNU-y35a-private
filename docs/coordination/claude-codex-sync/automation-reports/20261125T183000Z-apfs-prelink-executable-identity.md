# APFS 预链接可执行身份已闭合，交付与运行资格仍未闭合

时间: 2026-11-25T18:30:00Z
范围: 仅离线读取；未构建、未探测设备、未修改共享状态文件。

## 影响

原生 16G102 kernelcache 不仅包含 `com.apple.filesystems.apfs` 字符串，还在标准 `_PrelinkInfoDictionary` 中给出了唯一、完整的 APFS kext 可执行元数据。后续 APFS 交付审计可以直接核对地址、大小、可执行文件名和依赖，不必再把“驱动是否存在”作为开放问题；但该元数据不证明当前 T7000/T7001 XNU 构建实际携带或加载了 APFS。

## 事实

主线最新活动为 R172-03：原生构建和静态 instrumentation verifier 均通过，内核 SHA-256 为 `22c2fa08c911afc9f5ed57c6f272f1a19b0b4b75bac5b6a5f2465c1d173db6f8`；当时正在准备匹配 package/probe。审查会话已把主线 `systemError` 与测试失败分歧发回。本轮未触碰该构建链、触摸/I2C 或显示审计。

对 kernelcache 的 Mach-O `LC_SEGMENT_64` 顺序解析得到：

- 段: `__PRELINK_INFO`
- section: `__info`
- VM address: `0xfffffff0077e4000`
- file offset / size: `28114944` / `2113536`
- XML 实际长度: `2099530`；尾部 padding: `14006` 字节

XML 顶层是标准 plist；`_PrelinkInfoDictionary` 是直接字典数组，不含 `ID`/`IDREF`。共有 193 个条目，其中 184 个具有 `_PrelinkExecutableLoadAddr`。APFS 条目唯一：

- `CFBundleIdentifier`: `com.apple.filesystems.apfs`
- `CFBundleExecutable`: `apfs`
- `_PrelinkExecutableRelativePath`: `apfs`
- `_PrelinkBundlePath`: `/System/Library/Extensions/apfs.kext`
- `_PrelinkExecutableLoadAddr`: `0xfffffff005f71e80`
- `_PrelinkExecutableSize`: `0x25f01`（155393 字节）
- `_PrelinkKmodInfo`: `0xfffffff0077c72ec`
- 版本: `945.272.3`
- SDK / platform: `iphoneos12.4.internal` / `iPhoneOS`；`MinimumOSVersion=12.4`
- `OSBundleRequired`: `Local-Root`
- 依赖: `com.apple.kpi.mach`, `libkern`, `bsd`, `iokit`, `unsupported`, `private`, `AppleEffaceableStorage`, `IOStorageFamily`
- personality: `AppleAPFSContainer`（`Content Hint=7C3457EF-0000-11AA-AA11-00306543ECAC`）及 `com_apple_filesystems_apfs`

交叉核对：kernelcache 原始字节中 bundle identifier 出现 5 次，而结构化字典中恰好只有 1 个 APFS kext 条目；其余出现属于 personality/依赖等文本。独立 staging 证据确认真实 OS 是 case-sensitive APFS、`used_bytes=3933454336`，因此 APFS 是后续真实系统根的必要组件，而不是可选驱动。

## 待确认

- 该地址/大小对应的可执行字节尚未按段几何导出并计算 SHA-256。
- 尚未与 IPSW 中提取的独立 `apfs.kext` 二进制做字节或 UUID 对照。
- 尚未验证依赖在当前 T7000/T7001 包中的闭包、实际 prelink 包含关系和运行时加载。
- 当前 HFS+ bring-up root 仍不能当作真实 APFS System 卷。

## 推断

原生 16G102 cache 已提供可信的 APFS 身份与链接元数据，可作为后续移植/交付的参考基线。它不能推出 R172 或任何当前设备候选已经携带 APFS，也不能推出存储运行资格已经获得。

## 证据与 SHA-256

- `/Users/lingion_k/unixnu-research/UniXNU-y35a/out/ipsw/16G102/kernelcache.decompressed`
  - `70e80388d42fe2376096bb6248073b0380dd87b85b1a792b36205ba60c722ce1`
- `/Users/lingion_k/unixnu-research/UniXNU-y35a/out/ipsw/16G102/kernelcache.decompressed.json`
  - `c66b4df32a10d0ef4a6627df4b89abcc6f40fc98a8a416415e62e73dc2965d91`
- `__PRELINK_INFO,__info` section
  - `e0deb2f3a692cec56e15f64f5643e1c7598388f8e9dd1d4b4e5f57fd505969fe`
- 去除尾部 padding 后的 XML
  - `3d8636ae608213110b51ebd1e3453ddc5a3e94f09155bab6ba6d488a1ae2b756`
- `/Users/lingion_k/unixnu-research/UniXNU-y35a/scripts/data/ios12-root-staging-evidence.json`
  - `77e3bb71680ede73b4c185c14a811de390ab0cff9de91db6f587e837d7198f33`
- `/Users/lingion_k/unixnu-research/UniXNU-y35a/components.toml`
  - `bc0609d126c050650dbe94136cad6071ef73b23d30e99fdbb9faf41f78a9c53a`

## 单一步骤建议

扩展现有离线 prelink 审计：由 `__PLK_TEXT_EXEC` 段几何把 `0xfffffff005f71e80/0x25f01` 映射到 kernelcache 文件范围，导出并哈希这 155393 字节，再与 IPSW 独立提取的 `apfs.kext` 做 UUID/字节对照；完成前不要将其标记为已交付 APFS 驱动。
