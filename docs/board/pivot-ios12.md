# 换道决策记录:目标用户态从 iPadOS 17.7.11 改为 iOS 12.4.1(j96ap / XNU-4903)

日期 2026-11-04。用户定令:"我只在乎在这个手机上跑到最合适的 iOS 系统,与其在错误的道路上越走越远,不如赶紧换到正确道路上。"

## 为什么 12.4.1 是"最合适"

| 维度 | iPadOS 17.7.11(21H461,旧目标) | iOS 12.4.1(16G102,新目标) |
| --- | --- | --- |
| Apple 官方对应用硬件 | iPad Pro(A10X,3GB,有加密指令) | iPad mini 4(A8X,2GB,无加密指令) |
| Y35A 实配 | A53×4,2GB,无 AES/SHA(实测 ID_AA64ISAR0=0x10000) | 同 ISA 代(armv8.0),同内存档 |
| 内核特性依赖 | arm64e、KTRR/pxo、IOGPU、KernelCollections、cryptex | 全都不需要;老式 PRELINK kext 一步到位 |
| 用户态体量 | dyld 共享缓存 1GB 级,APFS+双 cryptex | HFS+ 根,共享缓存约 300MB |
| 加密指令缺失的代价 | 每次软件模拟走异常路径,已实测 160 万次 | 同样需要模拟(corecrypto),但调用密度低、路径简单 |
| 2GB 内存现实 | Apple 从未在 2GB 以下非 arm64e 设备跑过 17 | Apple 亲自把 12.4 跑在这档硬件上 |
| 预期体验 | 分钟到小时级开机,"无实用价值" | Apple 当年即秒级-十秒级,系统完整可用 |

12.4.1 是 mini4 的 12.x 终版(目录实测 11 个 12.x 构建,12.4.1/16G102 收尾)。mini4 理论天花板是 iOS 15.8.8,作为已文档化的升级阶梯保留:届时只需换 kernelcache 物料与对应 XNU tag(7195.x),管线不变。先 12 后 15,不回头路。

## 已验证的实物(全部 adler/SHA 硬校验)

- IPSW:dl/iPad_64bit_12.4.1_16G102.ipsw,3,053,369,741 字节,SHA256 8a7f0750…(与 api.ipsw.me 目录逐字一致)。
- kernelcache:out/ipsw/16G102/kernelcache.decompressed,30,228,480 字节。
  arm64 MH_EXECUTE,构建自 iphoneos12.4 SDK;缓存内嵌 t7000(A8)+t7001(A8X)
  双机器码,IPSW 含 DeviceTree.j81ap/j96ap —— 一款通用缓存覆盖
  iPad Air 2(j81ap)与 iPad mini 4(j96ap)两款板型。
  结构实测(2026-11-05 05:20 定稿,otool+字节切片+35 绿测试三重背书,
  此前三个 agent 口径的 MH_KEXT_BUNDLE/21 段/6 段/42 段/CDATA 皆错):
  MH_EXECUTE(type=2)、22 条 load command、15 个段(__TEXT..__LINKEDIT,
  含 __PRELINK_TEXT/INFO/DATA 三段老式 PRELINK 布局)、TEXT vmaddr
  0xfffffff007004000(读 segment_command+24,+16 是 vmsize——0xc4000 为
  字段误读)。__PRELINK_INFO: fileoff 0x1ad0000(28114944),
  vmsize=filesize 0x204000,有效载荷为 **2,099,530 字节裸 `<dict>` 老式
  plist**:无 `<?xml` 头、无 `<![CDATA[`、无 `_PrelinkKextPList`、无
  `bplist00`(全文件 0 命中,regex 复核);整数用 `<integer ID= size=>`
  宽松方言,plistlib 拒收,专用解析器 kits/XnuPrelink/legacy_prelink.py
  (943 行,35 项测试在 3.10/3.12 双绿)。主键集:`_PrelinkInfoDictionary`
  (185 模块数组,含 Mach Kernel Pseudoextension)、`_PrelinkKmodInfo`×184、
  `_PrelinkKCID`、`_PrelinkLinkKASLROffsets`、`_PrelinkExecutable*` 系列。
  计划数实测:roots=170、loadable=177、codeless=8、pruned=1、
  KASLR sites=251829。内核 TEXT 基址与 8102 世代 ARM64_LINK_ADDR 同值,
  XnuPrelink 管线基址约定可沿用;但 iOS12 无 CDATA/kextPList 双写,
  emit_prelink.py 的 17 世代 plist 序列化必须为老方言重写(= P2 工作)。
  185 模块内含全部关键 kext 家族(string 命中复核:HFSPlus 47、
  IOStorageFamily 20、IO80211Family 125、IOHIDFamily 62、AppleKeyStore 70、
  corecrypto 42、AppleImage4 28)——旧文"502 个 kext"是把 InfoDictionary
  里 504 处嵌套 CFBundleIdentifier(模块 Info 的 OSBundleLibraries 等)
  错当模块数。
- 容器:complzss = 大端头(adler32/raw/cmp/ver)+ 0x180 起 HaPuff 流,解码器已入库
  tools/uncomplzss.py(提交 92eccd8)。
- XNU 源码(2026-11-05 更正):P1 主源码 = xnu-4903.270.47(公开 tag,iOS 12.4
  世代 Darwin 18.7,16G102 真身 xnu-4903.272.1 的最近公开点);内核已构建并
  字节级验证(out/y35a/ios12-kernel.noctf,vmaddr 0xfffffff007004000==官方 j96ap)。
  xnu-4570.51.1 克隆仍在 ~/unixnu-research/xnu-4570,但它是 iOS 11.3 世代
  (Darwin 17.4)线,F1 实验(2026-11-05,out/y35a/ios12-4570-f1)判决 4570
  为死路:同工具链
  68 源文件全量计数 2038 错 vs 4903 的 141 错,MIG 生成器还是 py2
  (import __builtin__),19 个 .x 接口一个都产不出。原行文"标签
  xnu-4570.51.1,即 12.4.1 内核源"系错,以此条为准。

## 不作废清单(设备层成果,ABI 线以下)

lk2nd boot 槽与强制 fastboot、EL1 交棒 shim、boot-args/ADT 打包管线
(package_native.py,基址换算 2MiB 块恒等仍然成立)、GICv2 SecurityExtn 修复、
定时器 INTID20、UARTDM 控制台、PS_HOLD 暖复位、panic/pram 取证回路、
eMMC 只读 GPT 探测与分区表、板级事实文档(docs/board/y35a-facts.md)。

## 换道工作清单(本记录的待办索引)

1. 4903 构建管线:✅已完成——scripts/build-xnu-4903-kernel.py 在 linux_env
   容器产出 DEVELOPMENT mach 内核(见上条源码更正与 recon-20261105 §P1)。
   MSM8916 board header 工作仍在 P3 线上(增 ARM_ARCH_TIMER 保留、
   AIC 换 ArmCpu GICv2 抽象的 4903 版补丁)。
2. XnuPrelink 对 16G102 cache 的适配验证:__已完成(2026-11-06,
   kits/XnuPrelink 分支 port/ios12-legacy-prelink 三笔 982e9ea/8ec6220/41fb484)。
   emit_legacy.py 发射线 + p2_schema 布局探针(常量全部实测出处)+
   真 payload 字节级 roundtrip + emit→legacy 读回器逐键全等闸 +
   合成父 cache 四类分型闸;test_legacy_emit 15 测 54 subtests 绿,
   kit 全量 41 测绿,双 Python 3.10/3.12 同绿。遗留(不在本条验收内):
   emitter 接真实构建输入的组装调用方、KPI stub 生成对接 native_prelink。
3. 驱动代际移植:ArmCpu/ArmDTPlatform 的 4903 版(IOService API 旧代,
   无 OSSharedPtr;IOPICEvents 接口挂 GICv2);uartdm/early-fault/crypto 补丁后移。
4. 根与用户态:官方 System.dmg(HFS+)解出 launchd 与静态 trustcache
   (IPSW 内 048-78033-095.dmg.trustcache 即根卷签名集);先 RAMDisk 小根,
   后 eMMC 持久根(目标分区待定,userdata 绝不动)。
5. 实机验证顺序不变:RAM boot 先行,写分区之前必须逐项向用户确认。

## P4 落地记录(2026-11-04 晚,RAMDisk 小根物料定案)

上条 4 的行文有两处需要按实物修正,均已实测:

1. 16G102 的 System DMG(048-78033-095.dmg,SHA1 与 BuildManifest OS 条目逐字
   一致)不是 HFS+,是 GPT 上的区分大小写 APFS 卷(卷名 PeaceG16G102.…OS,
   用量 3.93GB)。macOS 主机 hdiutil+mount_apfs 只读挂载即可全量检视。
2. 该根卷是被 dyld 共享缓存剥空的:libSystem.B/libobjc/各 framework 二进制
   在盘上没有实体文件,只存在于 1,269,743,616 字节的
   System/Library/Caches/com.apple.dyld/dyld_shared_cache_arm64 里。把缓存塞进
   RAMDisk 必然爆预算,所以小根改走 Apple 自家 customer Restore RamDisk
   (048-78047-096.dmg,IM4P 'rdsk' 包一个无分区表的原始 HFSX 卷,91,602,944
   字节)同款形态:实体 dylib、无共享缓存、62MiB/370 文件。其 launchd、dyld、
   mount、mount_hfs 与系统卷逐字节同哈希,闭包直接照抄成立。
3. 闭包实物:58 个 Mach-O(sbin/launchd 与 usr/lib/dyld、mount 系列取系统卷,
   49 个 dylib/framework 取恢复卷),otool 传递闭包 406 条边全部解析,红绿验证
   过(抽掉 libobjc 即红)。cpio.gz 7,408,823 字节(sha256 cba2e3f0…,newc、
   uid/gid/ino/mtime 全零、双名 rootfs.gz),HFS+ 映像 42,991,616 字节页对齐。
4. 开机形状:XNU-4903 的 md0(IOKitBSDInit 从 /chosen/memory-map RAMDisk 建
   bdev,bsd_init 挂载)要的是文件系统本身,不是 Linux 式 cpio 解包;所以
   package_native.py --ramdisk 应喂 ramdisk-hfs.raw,cpio.gz 只是可搬运源。
5. trustcache 陷阱(最重要的发现):静态缓存 048-78033-095 有 1737 条目,
   但只覆盖上面 9 个取自系统卷的二进制;49 个 dylib 只在恢复卷缓存
   048-78047-096(174 条目)里。两缓存并集才覆盖全部 58 个,单独喂静态缓存
   会让 AMFI 在 dlopen 时杀掉 49 个。首 boot 打包必须带恢复缓存(或并集)。
   条目格式实测:IM4P 'trst',载荷 = u32 版本 1 + 16B UUID + u32 条目数 +
   每条目 20B SHA1 cdhash + u16 kind(0x0001/0x0002/0x0102)。
6. 其它小事实:12.4.1 没有 KernelCollections;LaunchDaemons 322 个;盘上
   不存在 mdns.conf;系统卷 master.passwd 权限 0600 主机不可读,恢复卷副本
   0644 可用。DeviceTree.j96ap.im4p(明文 'dtre',131,223 字节)已落
   out/y35a/ios12-kc/,与 kernel.macho 同目录。
7. 工具:打包器实为容器内 /work/UniXNU-y35a/scripts/y35a/package_native.py
   (主机镜像 scripts/y35a/package_native.py,docker cp 同步);容器/主机
   物料实测 sha256(2026-11-06): /work/ios12-kernel.noctf 5fd4e6b5… ==
   主机内核; /work/root.trustcache 695f912e… == 主机
   out/y35a/ios12-root/.trustcache; /work/ramdisk-hfs.raw 4690a936… ≠
   主机 out/y35a/ios12-root.work/ramdisk-hfs.raw 54c07a60… ——同体积
   (42,991,616B)两代 HFS+ repack,repack 非字节可再现(evidence 自记),
   boot3 以主机 P4 件 54c07a60 为准喂第二域。容器内无 cpio 件;主机
   rootfs.cpio 62d933bc…、权威可搬运件 rootfs.cpio.gz cba2e3f0…。
   闭包工具 scripts/stage-ios12-root.py(幂等,cpio 双跑同哈希)、
   tools/check-ios12-closure.py(红绿闭包闸);全量证据
   scripts/data/ios12-root-staging-evidence.json。IPSW 的 sha256 权威值
   8a7f0750b9ba…(api.ipsw.me iPad5,1/5,2 一致);当日任务书里给的
   …10128aee… 前四字节相同其后不同,系转写错误,以实物+官方目录为准。
