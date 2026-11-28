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

最新 package dispatch `46100598017` 在 commit `958df9b5dad9485a55d2beaeb19b1b75420a20e3` 成功，明确消费 native run `46086948983` / artifact `15239965878`，validate 与 package job 均实际成功。RAM-boot package artifact `y35a-ramboot-46100598017` 的 ID 为 `15245323039`，digest 为 `sha256:4981c4c04afd0141afb6f3a0c69f8e4d03f74da94cefb97cc406ed0347a9fc4f`。Root-tree artifact ID `15244974333`，digest `sha256:d3180a272f99da5cf9e36ee1add9e028ab2e396bb1c584bae3738be8fc12e55c`；单文件 `root-tree.tar` artifact ID `15245193498`，digest `sha256:112df00c9b05ca97755c0c91d868c8c443b2607be5598d1849722a6372f31679`。

RAM package 明确为 `launchd-diagnostic-ramboot`，closure 有 58 个 Mach-O，SpringBoard 未包含，触摸未运行，`runtime_qualified=false`。包内 QCDT 来源为 derived DTS，不是 stock PD1502A QCDT；所以此 artifact 不是完整 iOS 系统包，也不是 TF/APFS 生产包或设备启动证据。

本轮 package run `46100598017` 上传的 System-volume source artifact `y35a-ios12-system-root-46100598017`，ID `15245028918`，digest `sha256:3a06bb3c3bc0364dd0ab83e921bda45c89390f1e9226db3118fabb1d5e08ae06`，artifact 大小 `2,826,122,994` bytes。其内部 System image 为 `2,826,117,884` bytes，SHA-256 `f740ff9931061a2adc10d7b1e766cbe907346f11180014fe8ee58a2f554a9880`。Actions schema-2 handoff gate 验证 IPSW identity、GPT/APFS 和关键文件，并记录 `private/var`、`private/var/db`、`private/var/mobile` 在 pinned j96ap 12.4.1 源卷中均为目录。该卷从只读来源测得路径元数据，不能证明可写或已挂载到 Y35A。Apple 的 volume-group 机制适用于 iOS 13 及之后，因此不要把配对 System/Data volume 作为 iOS 12.4.1 必需条件；传统 root 初始化仍待核。

## 未闭合门槛

- pinned j96ap System source 中三个 `/private/var` 相关路径确实存在，但它是只读来源，Y35A 可写 root 与启动时初始化仍未证明。iOS 12.4.1 的 legacy 单根布局须按实际 IPSW/XNU 验证，不能沿用 iOS 13+ volume-group 假设。
- 当前 RAM root 仍由 `scripts/stage-ios12-root.py` 的闭合清单产生 58-file launchd diagnostic tree，不是完整 System tree；单独的完整 System-volume DMG artifact 尚未进入可启动 root package 或 APFS TF image。
- 可信 stock PD1502A QCDT 仍缺失。历史完整 stock boot 记录 SHA 为 `92611f876a022fb5af1138f0591f5dafe2b359a226b2f0b28d292211f2fec012`、大小 `67,108,864` bytes，但原文件已缺失。新 CI intake 只接受精确文件 `evidence/y35a-20261102/stock-boot.img`，由 Actions 校验历史全镜像 SHA 后提取 QCDT；derived QCDT 不得冒充 stock。
- fallback-v3 source candidate 已经过 exact XNU apply 与 native link/static gate，但尚无设备运行证据；stock QCDT、TF/APFS package、card binding 和真实 fallback 行为都未验证。source candidate 的 manifest 已独立于 production manifest。
- 本次上传的 System-volume artifact 不包含 Y35A boot shim、stock QCDT、paired Data image、TF/GPT/APFS device image、root-selection 绑定或 probes。

## 下一步

1. 在 Actions 上创建完整 System-source 的 GPT/APFS 离线控制输入，验证文件树和只读/可写状态，不授予 bootable 或 Y35A 资格。
2. 用户提供原始 stock boot 文件 `evidence/y35a-20261102/stock-boot.img`；必须精确为 `67,108,864` bytes、SHA-256 `92611f876a022fb5af1138f0591f5dafe2b359a226b2f0b28d292211f2fec012`，且来源为 PD1502A_A_1.18.0 的完整 boot 分区读回。CI 将从文件提取并绑定 QCDT。不得用 derived DTS 或第三方 ROM 代替。
3. 将完整 root、stock QCDT、linked root selector/fallback、TF image 和 probes 闭合到 CI 哈希链；满足计划和既有门禁前不操作设备。

## 持久化与恢复边界

- GitHub Actions 是唯一 UniXNU 构建、测试、静态验证、package 和 hash-closure 环境。
- `/Volumes/Portable` 只用于临时保存已下载 artifact 和证据；`/Volumes/Mobile` 保持禁止访问。
- `device_run_allowed=false`；不写 TF、eMMC、GPT 或启动链。全分区备份和 EDL/firehose recovery 仍未验证，持久写入禁止。
