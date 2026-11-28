# UniXNU 实时目标

更新时间：2026-11-28。最终目标仍是 iOS 12.4.1 在 vivo Y35A 真机启动并可用。当前没有已验证的 Y35A iOS 启动或可交互 SpringBoard 证据，D1、D2、D3 均为 `IN_PROGRESS / NOT_MET`。

## 最终验收

- D1：同一精确镜像在 Y35A 上连续三次进入 launchd，每次稳定运行十分钟，并有绑定该镜像的新鲜现场证据。
- D2：进入真实 SpringBoard，显示系统界面，触摸与实体按键可交互。
- D3：完成项目目标定义的其余驱动和稳定性验收。
- CI、离线包、完整 System-volume source artifact、derived-QCDT APFS control image 都是中间证据，不能替代设备验收。

## 当前主线阶段：R208 CI 包与系统来源闭环

所有 UniXNU 编译、测试、静态门禁、package/image 验证只在 GitHub Actions 执行。本机不运行 UniXNU build、测试或静态门禁；本轮未操作设备、TF、USB、fastboot、adb、串口或持久分区。`device_run_allowed=false`，无持久写入。

Topic `codex/unixnu-ci-package-v2` 的精确 commit `332843f94ee4eb5cb541a5b956f1c75ba3172eb8` 已通过 native build run `46086948983`。Run 的 installhdrs、build、R208 static verifier、driver force-load 与 kernel artifact contract 全部成功。XNU 为 `494ffe1c29d37ca720c37328feb83069c9641b67`；fallback-v3 manifest SHA-256 为 `f967a2fe75a10c83ac8ec24d55284b1391d9c27bfb58514d42e5dcb30fbc1651`。Kernel SHA-256 为 `ca948860a1e99542d2e4d8e45498a45ecbf1b454d64d672f124415504fdc0137`，大小 `12,828,688` bytes。Native artifact `unixnu-kernel-46086948983` 的 ID 为 `15239965878`，digest 为 `sha256:f388776022526f45628e1d7593adc247a97198eabfbc4a1dece5782402ab5578`。这证明 CI 产出 hash-bound kernel，不证明其在设备上启动。

同一 native artifact 的 package dispatch `46087760341` 成功，validate 与 package job 均实际运行并成功。RAM-boot package artifact `y35a-ramboot-46087760341` 的 ID 为 `15241627599`，digest 为 `sha256:715d81cf98d6bb040f75d52ac0486fbd7a5ebceb2683f8fa1f6e88dc6fca9612`。Root-tree artifact `y35a-root-tree-46087760341` 的 ID 为 `15241652619`，digest 为 `sha256:1d3622c344b4cfb799583e8723feda8cbc9bdb5d082bb42afbe64cd0301ced5a`；单文件 `root-tree.tar` artifact 的 ID 为 `15241732201`，digest 为 `sha256:bde9467831c18f237b4b39a098c650a1087e7ae0e0145123747cf64a68502036`。RAM package 的 28 项 `SHA256SUMS` 已对解出的 artifact 逐项核对一致。

RAM package 明确为 `launchd-diagnostic-ramboot`，closure 有 58 个 Mach-O，SpringBoard 未包含，触摸未运行，`runtime_qualified=false`。包内 QCDT 来源为 derived DTS，不是 stock PD1502A QCDT；所以此 artifact 不是完整 iOS 系统包，也不是 TF/APFS 生产包或设备启动证据。

同一 package run 新增并成功上传完整 iOS 12.4.1 `OS` System-volume source artifact：`y35a-ios12-system-root-46091804871`，ID `15241677649`，digest `sha256:c74e86b815e3a44b618235cad7e856b882d4ccaae2fe37e77b3bae0de67bf66d`，大小 `2,826,122,053` bytes。Actions 在上传前验证 artifact `SHA256SUMS`、与 pinned IPSW OS component 的字节一致、版本 `12.4.1 / 16G102`、j96ap/iPad5,1 identity、GPT/APFS whole-disk/volume/parent 关系，以及 `launchd`、`dyld`、`SpringBoard` 文件存在和 SHA。该 volume 来自 iPad5,1/j96ap IPSW；Y35A 兼容性仍未知。IPS​​W 没有 paired writable Data volume，所以该 artifact 只证明完整 pinned System-volume source 可从 CI 导出，不证明完整安装、可写 `/private/var`、Y35A 启动或 SpringBoard runtime。

## 未闭合门槛

- 完整 System 卷缺 paired writable Data 卷及其格式化、UUID、`/private/var` 挂载来源。不能将 System-only source 升格为完整 iOS 安装。
- 当前 RAM root 仍由 `scripts/stage-ios12-root.py` 的闭合清单产生 58-file launchd diagnostic tree，不是完整 System tree；单独的完整 System-volume DMG artifact 尚未进入可启动 root package 或 APFS TF image。
- 可信 stock PD1502A QCDT 仍缺失。受限只读审查在仓库与当前 CI artifacts 中未找到原始字节；历史 stock boot 的记录 SHA 为 `92611f876a022fb5af1138f0591f5dafe2b359a226b2f0b28d292211f2fec012`、大小 `67,108,864` bytes，但原文件已缺失。derived QCDT 不得冒充 stock。
- fallback-v3 source candidate 已经过 exact XNU apply 与 native link/static gate，但尚无设备运行证据；stock QCDT、TF/APFS package、card binding 和真实 fallback 行为都未验证。source candidate 的 manifest 已独立于 production manifest。
- 本次上传的 System-volume artifact 不包含 Y35A boot shim、stock QCDT、paired Data image、TF/GPT/APFS device image、root-selection 绑定或 probes。

## 下一步

1. 在 Actions 上产出并审查与 System volume 明确配对的 writable Data-volume artifact，绑定 UUID、容量、所需目录与 `/private/var` 生命周期；CI source artifact 通过不等于设备挂载已证。
2. 获取带 PD1502A 来源和 SHA-256 的完整 stock boot image（历史优先匹配 `67,108,864` bytes 与 SHA `92611f876a022fb5af1138f0591f5dafe2b359a226b2f0b28d292211f2fec012`），或可信 stock QCDT 字节及 container provenance。不得用 derived DTS 或第三方 ROM 代替。
3. 继续闭合完整 root/Data、stock QCDT、linked root selector/fallback、TF image 和 probe 的 CI 哈希链；满足计划和既有门禁前不操作设备。

## 持久化与恢复边界

- GitHub Actions 是唯一 UniXNU 构建、测试、静态验证、package 和 hash-closure 环境。
- `/Volumes/Portable` 只用于临时保存已下载 artifact 和证据；`/Volumes/Mobile` 保持禁止访问。
- `device_run_allowed=false`；不写 TF、eMMC、GPT 或启动链。全分区备份和 EDL/firehose recovery 仍未验证，持久写入禁止。
