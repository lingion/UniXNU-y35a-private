# APFS kernelcache 身份核查（部分完成）

- 时间：2026-11-25 离线周期
- 范围：只读取本地 16G102 kernelcache；未操作设备、USB、fastboot、adb、串口或持久分区，未运行构建。
- 主线边界：与当前 R171 post-SCTLR/page-table 窗口无关；不重复触摸/I2C、R94–R99、R136、R137。

## 证据与 SHA-256

1. `out/ipsw/16G102/kernelcache.decompressed`
   - 大小：30,228,480 bytes
   - SHA-256：`70e80388d42fe2376096bb6248073b0380dd87b85b1a792b36205ba60c722ce1`
   - 与 `out/ipsw/16G102/kernelcache.decompressed.json` 的 `output_sha256` 一致。
2. Mach-O `__PRELINK_INFO,__info`
   - file offset：28,114,944；section size：2,113,536 bytes
   - section SHA-256：`e0deb2f3a692cec56e15f64f5643e1c7598388f8e9dd1d4b4e5f57fd505969fe`
   - 截取到最后一个 `</dict>` 的 XML 为 2,099,530 bytes，其后 padding 14,006 bytes；XML SHA-256：`3d8636ae608213110b51ebd1e3453ddc5a3e94f09155bab6ba6d488a1ae2b756`
3. `components.toml`
   - SHA-256：`bc0609d126c050650dbe94136cad6071ef73b23d30e99fdbb9faf41f78a9c53a`
   - 无显式 APFS 组件项。

## 事实

- 原始 binary 正则独立命中 `CFBundleIdentifier=com.apple.filesystems.apfs` 3 处，以及 `com.apple.filesystems.hfs.kext` 2 处。
- `strings -a` 独立复核命中 `com.apple.filesystems.apfs` 2 处。
- 因此，真实 16G102 kernelcache 的 prelink metadata 中确实出现 APFS bundle identifier；这纠正了“摘要 JSON 无 APFS 字符串即可能无驱动”的不确定性。
- Python `plistlib` 不接受该 XML（即使移除 section 尾部 padding），本轮未取得 APFS 字典的可执行地址、UUID、依赖或 loadable 状态。

## 待确认

- APFS 条目是实际 loadable KEXT、KPI/依赖声明，还是两者皆有。
- 精确 `_PrelinkExecutableLoadAddr`、`_PrelinkExecutableSize`、可执行 UUID/SHA-256 与 `OSBundleLibraries`。
- 当前 R154/R159 交付 kernel 是否携带同一 APFS 组件。

## 推断与影响

- 可确认“stock 16G102 kernelcache 含 APFS 身份 metadata”，不能确认“当前 Y35A 交付链已集成可加载 APFS 驱动”。
- 这不阻塞 R171；耐久 OS/Data 路线仍须保留独立驱动与存储门。

## 单一步骤建议

用能处理该 prelink XML `ID/IDREF` 形式的离线解析器提取 `com.apple.filesystems.apfs` 完整字典，记录其 executable load address、size、UUID/SHA-256 与依赖闭包；在取得这些身份前不安排 APFS 根设备实验。
