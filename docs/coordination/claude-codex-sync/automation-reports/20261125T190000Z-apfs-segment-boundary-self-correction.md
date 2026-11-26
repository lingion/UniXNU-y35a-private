# APFS 二进制边界自纠：`0x25f01` 只是 `__TEXT`，不是完整 kext

时间: 2026-11-25T19:00:00Z
范围: 仅离线读取；未构建、未探测设备、未修改共享状态文件。

## 影响

上一份报告建议把 `_PrelinkExecutableLoadAddr/_PrelinkExecutableSize` 对应的 155393 字节直接作为完整 `apfs.kext` 与独立文件比较。本轮读取该范围头部的 Mach-O 后确认：这个大小只覆盖 APFS 的 `__TEXT` 段；代码、GOT、数据和 kmod info 分别位于外层 kernelcache 的其他 prelink 段。直接比较该切片会遗漏真正的执行代码，必须撤回该比较方法。APFS bundle 身份本身不变。

## 事实

已导出范围为 kernelcache 文件偏移 `0x94de80/0x25f01`，SHA-256 为 `0cd7d0528ed945be1c46c431739b467c1fe6a1d2eb6c309e76b7f76f79196bb4`。其 Mach-O 头为 arm64、11 条 load command，LC_UUID 为 `3908938A-FDEB-30D1-8B4F-A6366D143DAF`，没有 `LC_MAIN`（kext 形态）。

内层 APFS 段表不能按“切片起点 + 内层 fileoff”直接映射；必须按内层 VM address 穿过外层 kernelcache 的段表：

| 内层段 | VM address | 文件大小 | 外层承载段 | kernelcache 绝对文件偏移 | SHA-256 |
|---|---:|---:|---|---:|---|
| `__TEXT` | `0xfffffff005f71e80` | `0x25f01` | `__PRELINK_TEXT` | `0x94de80` | `0cd7d0528ed945be1c46c431739b467c1fe6a1d2eb6c309e76b7f76f79196bb4` |
| `__TEXT_EXEC` | `0xfffffff0069b4000` | `0x839d8` | `__PLK_TEXT_EXEC` | `0x1390000` | `a012eab3724576926e59c3479fc3e9e566c9f266bb15b3db9b923d6d3e15e84a` |
| `__DATA` | `0xfffffff0077c7080` | `0x1bc0` | `__PRELINK_DATA` | `0x1ab3080` | `b8c371a2f70fe889c8c6628fab8e6e2a4733a55648292a9f9337651a1af3031b` |
| `__DATA_CONST` | `0xfffffff006f7ee40` | `0x5a90` | `__PLK_DATA_CONST` | `0x195ae40` | `da4eab57b9f6bb6f1295de1132e849c3484b59d925361d0b09f272409ac6ddb8` |

`__LINKEDIT` 的 vmsize/filesize 均为零。`__TEXT_EXEC` 含 `__text=0x82838` 与 `__stubs=0x11a0`；`__DATA` 含 `__data`/`__bss`；`__DATA_CONST` 含 `__got`、`__mod_init_func`、`__mod_term_func` 和 `__const`。`_PrelinkKmodInfo=0xfffffff0077c72ec` 位于 `__DATA`，其绝对文件位置为 `0x1ab2bec`，读取到的前缀为 `CIE`，与 kext info 结构一致。

交叉核对：外层 prelink XML 仍唯一声明 `com.apple.filesystems.apfs`、load address、size、UUID 所依附的 Mach-O 头及 kmod info 地址；内层段表又独立证明代码/数据不在该 155393 字节切片内。组件目录 `components.toml` 没有任何 APFS 文本或组件 ID，而 staging 证据明确真实 System 卷为 case-sensitive APFS、`used_bytes=3933454336`。因此“原生 cache 有 APFS 模块”与“项目组件交付链尚未登记 APFS”是两项不同事实。

本轮在 `.cache/firmware`、`out/ipsw`、`out/mnt-j96`、`dl` 范围内未找到可独立比对的 `apfs.kext` 二进制；这不证明整个系统其他位置不存在该文件。

## 待确认

- 尚未取得独立 `apfs.kext` 文件并比较 LC_UUID。
- 尚未比较 `__TEXT_EXEC` 的原始代码字节；预链接重定位可能使字节不相同，不能只做全段哈希相等判断。
- 尚未验证当前 T7000/T7001 package 是否包含上述四个 APFS 段和正确 kmod info。
- 尚未证明运行时 APFS 加载、容器挂载或真实 System 根使用。

## 推断

`0x25f01` 是 prelink 元数据中的 `__TEXT` 可执行 extent 大小，而不是完整链接后 kext 文件大小。上一轮“导出这 155393 字节即可与独立 apfs.kext 对照”的建议不成立；这是本轮发现并明确纠正的边界错误，不影响 bundle identifier 事实。

## 证据与 SHA-256

- `/Users/lingion_k/unixnu-research/UniXNU-y35a/out/ipsw/16G102/kernelcache.decompressed`
  - `70e80388d42fe2376096bb6248073b0380dd87b85b1a792b36205ba60c722ce1`
- `/Users/lingion_k/unixnu-research/UniXNU-y35a/out/ipsw/16G102/kernelcache.decompressed.json`
  - `c66b4df32a10d0ef4a6627df4b89abcc6f40fc98a8a416415e62e73dc2965d91`
- `/Users/lingion_k/unixnu-research/UniXNU-y35a/scripts/data/ios12-root-staging-evidence.json`
  - `77e3bb71680ede73b4c185c14a811de390ab0cff9de91db6f587e837d7198f33`
- `/Users/lingion_k/unixnu-research/UniXNU-y35a/components.toml`
  - `bc0609d126c050650dbe94136cad6071ef73b23d30e99fdbb9faf41f78a9c53a`
- 被纠正的上一报告
  - `/Users/lingion_k/unixnu-research/UniXNU-y35a/docs/coordination/claude-codex-sync/automation-reports/20261125T183000Z-apfs-prelink-executable-identity.md`
  - `4afde9c32230ac3c0a19098d6fab0bc7dea913904496e12884507b3273269371`

## 单一步骤建议

建立一个仅含 APFS 的段级 manifest：以上表四个外层文件范围记录 VM/file offset/size/SHA 和 kmod info，取得独立 `apfs.kext` 后先比 LC_UUID，再按 `__text`/`__stubs` 做重定位感知比较；不要拼接四个段冒充原始 kext 文件。
