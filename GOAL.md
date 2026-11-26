# UniXNU Y35A 主线执行合同

版本 2026-11-26。本文只保存长期有效的使命、边界和执行规则。轮次、实验号、PID、镜像哈希、当前卡点和下一步只写入 `LIVE-TARGET.md`、`STATE.md` 与账本。

## 恢复和每轮开始

按顺序读取实际文件，再开始构建、打包、回读或设备操作。

1. `GOAL.md`
2. `LIVE-TARGET.md`
3. `STATE.md`
4. `docs/coordination/claude-codex-sync/LOG.md` 末尾 30 条
5. 当前进程、`.device.lock`、最新 provenance、package/probe manifest 和运行计划

权威关系如下。

| 文件 | 作用 | 更新规则 |
| --- | --- | --- |
| `GOAL.md` | 长期使命、边界、状态机和质量门槛 | 规则改变时修改 |
| `LIVE-TARGET.md` | 当前唯一目标、当前阶段、下一步和禁止事项 | 阶段变化立即更新 |
| `STATE.md` | 不超过 40 行的恢复快照 | 每次裁决和阶段变化同步更新 |
| `LOG.md` | 不可变事实、命令、证据和裁决 | 只追加，更正使用 `SUPERSEDES` |
| `CURRENT.md`、`LONG-RUN-STATE.md` | 面向恢复的派生摘要 | 与状态变化同轮更新 |
| `REFERENCES.md` | 本地参考仓库索引 | 参考根变化时更新 |
| `docs/sop/LESSONS.md` | 错误、返工、漏检和修正 | 每次错误后追加 |
| `docs/skills/` | 可重复流程 | 同类操作第二次发生时更新 |

文件互相矛盾时，先以最新原始产物和账本为准，追加同步裁决，再继续。旧摘要不能覆盖新证据。

## 使命和完成条件

使命是让 iOS 12 用户态和 XNU 4903 系内核在 vivo Y35A、MSM8916 真机上启动，再补齐平台驱动。主线优先获得可验证证据，再修复真实功能。

完成必须同时满足以下条件，并由没有产出该证据的执行体独立裁决。

- D1 同一组镜像连续 3 次启动到 launchd PID 1，每次稳定运行至少 10 分钟，没有 panic 或看门狗复位。
- D2 同一组镜像显示 SpringBoard 主屏幕，触摸完成点击或翻页等可观察操作并产生响应。
- D3 P0、P1 驱动逐项取得功能性 `CONFIRMED` 证据。P2 逐项通过，或完成升级阶梯并给出证据充分的暂不可行结论。

Phase A 只追求 D1 和 D2。允许的 stub、绕过和硬编码必须登记为 HACK，并写出替换计划。D1、D2 独立确认后进入 Phase B，逐项替换 HACK 并完成 D3。

## 当前路径和范围

- 活动工作根 `/Volumes/Mobile/unixnu-research/UniXNU-y35a`
- 账本 `/Volumes/Mobile/unixnu-research/UniXNU-y35a/docs/coordination/claude-codex-sync/LOG.md`
- 参考仓库根 `/Volumes/Mobile/unixnu-research/UniXNU-y35a/upstream-refresh/2026-11-11/sources/`
- 备份根 `/Volumes/Mobile/unixnu-research/device-backups/efff9d92-20261119/`
- 设备锁 `/Volumes/Mobile/unixnu-research/UniXNU-y35a/.device.lock`
- Xcode `/Applications/Xcode.app`

同步策略：`https://github.com/lingion/UniXNU-y35a-private` 是当前私有同步仓库，Git remote 名为 `github`，并设置为默认 push 目标。旧 `origin` 继续保留为参考源。代码、目标、SOP、skill、脚本、CI、实验合同和证据元数据持续同步到 GitHub。移动硬盘只保存大体积源码缓存、run root、构建产物、设备备份和 raw。

能在 GitHub Actions 上重现的 lint、contract gate、单元测试、静态分析、文档检查和主机编译必须通过 CI 运行。只有真机 USB、设备锁、私有本地输入或 CI 无法提供的工具链才留在本机。CI workflow 失败时先修 CI 或记录明确阻塞原因，不能默默退回本机编译。

源码、构建输入、临时目录、日志和产物全部留在外置卷。参考仓库只读。主线只针对 Y35A，不能把其他设备或模拟器结果写成 Y35A 结论。

## 设备授权和恢复边界

用户已授权在项目范围内进行 Y35A 的 RAM 启动、重启、fastboot、adb、串口和项目产物操作。每次设备动作仍必须通过当前运行计划和 G0 预检。

启动链分区和 GPT 只有在完整备份已校验，且 EDL/9008 与本机可用 programmer 已实际验证读写后才可写。缺少这两项证据时，只允许 RAM 启动和不会改变持久分区的操作。

禁止熔断 eFuse/QFPROM、写 RPMB 或防回滚计数、重新锁定 bootloader。禁止删除或覆盖备份、LKG、账本和主线正在使用的输入。设备操作只有主线程执行，sub-agent 只做离线工作。

每次设备操作前后记录设备身份、型号、解锁状态、当前模式、持久写入状态和锁状态。运行失败后立即把 `device_run_allowed` 设为 `false`，没有新候选、完整门禁和新运行计划不得重试。

## 主线状态机

候选按以下顺序推进。状态变化后先更新 `LIVE-TARGET.md` 和 `STATE.md`，再进入下一状态。

1. `INTAKE` 读取目标、状态、账本、进程和现有产物，确认相同假设与相同镜像哈希是否已有裁决。
2. `REFERENCE` 读取 `REFERENCES.md`，检索相关本地仓库，记录 `REF path:line commit` 或 `NONE-FOUND query scope`。
3. `DESIGN` 写单一假设、变量、成功条件、失败条件、不可判定条件、次数、时间上限和回退方式。
4. `SOURCE` 固定源树、commit、patch 链和每个 patch 的 SHA，执行精确源树 `git apply --check`。
5. `BUILD` 在独立外置 run root 构建。只有 provenance 成功、产物存在、大小和 SHA 已记录才算完成。
6. `LINKED-GATE` 对实际链接产物反汇编和符号检查，确认顺序、调用契约、地址、owner、segment 和边界。
7. `PACKAGE-GATE` 绑定 kernel、entry、container、DT、rootfs、trustcache、boot args 和 manifest 的完整哈希与来源类型。
8. `PROBE-GATE` 绑定 regular/clear probe、manifest、物理地址、长度、清零窗口、transport 和负对照。
9. `RUN-PLAN` 生成唯一计划，绑定所有 gate SHA，写明只运行一次、最长时间和同输入禁止重试。
10. `G0` 实时核对设备、锁、进程、备份边界和投递方式。
11. `RUN` 只运行计划中的一次设备实验。等待时只做不冲突的离线工作。
12. `ADJUDICATION` 保存 raw、日志、恢复状态和完整哈希，由其他执行体独立裁决。
13. `LEARN` 追加 lessons，必要时更新 gate、SOP、skill 和 references，再生成下一候选。

状态失败会结束当前候选并进入 `ADJUDICATION` 或 `LEARN`。失败候选不能通过改写旧 manifest、复用旧 probe 或修改旧裁决重新变绿。

## 实验合同

每个实验必须是单一假设的最小可验证实验。计划文件必须包含唯一实验号、父候选、假设、竞争假设、输入路径、来源 commit、来源类型、完整 SHA、变量、成功/失败/不可判定条件、设备操作、最长等待时间、次数、重试规则、nonce、目标窗口、正向对照和失败后的下一条离线动作。

同一症状连续两次没有改变时，停止原地重复，至少并行推进参考检索、独立裁决、源码差异或容器差异中的两项。第三次实验必须使用能区分新假设的新输入。连续八次没有信息增益时，升级方法层级或记录暂不可行。

最大内存配置只有在内存几何和 transport 通过离线门禁后才可上机。收缩内存或功能只用于由原始证据直接指向的诊断二分，并在下一候选恢复基线配置。

## 打包、回读和证据门禁

门禁按候选类型分层。不能用旧的“全部脚本通过”替代当前候选的适用门禁。每个门禁结果写入 `evidence/gates/<UTC 时间>/`，记录命令、退出码、脚本 SHA、输入 SHA 和结果。

Source gate 必须确认 patch 格式、精确源树 `git apply --check`、patch 链顺序、父输入、source provenance、commit、tag、工作树哈希、owner、codeword、slot、offset 和目标函数。失败 patch 不得进入 build input。

Linked gate 必须确认 installhdrs、build、适用的 static verifier、实际 linked Mach-O 的 SHA 和大小、segment、符号、调用契约、目标顺序、marker 恰好一次、codeword、owner、offset、宽度、对齐、物理映射、cache 操作和边界。gate 自身必须有负对照，能拒绝错误顺序、错误 slot 或错误哈希。

Package gate 必须确认 package 只由当前 linked kernel、当前 entry、当前 DT、当前 rootfs 和当前 boot args 生成。Android header、page size、entry、args/tree/owned-memory 几何必须一致。每个 payload 和 sidecar 必须有完整 SHA 与大小。DT 必须标记 `stock`、`derived` 或 `unknown`。`unknown` 不能进入运行计划。`derived` 只能用于明确允许的离线控制，设备运行需要额外的独立正向依据。manifest 必须绑定 source provenance、kernel、entry、DT、rootfs、trustcache、boot args 和生成命令。

Probe gate 必须确认 regular/clear probe 绑定同一 kernel 和 package SHA，clear 地址和长度由当前 package manifest 推导，目标窗口、carrier、slot、字段宽度和对齐一致，preclear/baseline 有 fresh raw、zero 结果和完成计数。新 transport 先用已知可运行镜像做 positive control，再解释负结果。负对照必须证明错误地址、错误 slot、错误 kernel 或错误 manifest 会失败。

Run gate 必须确认 plan SHA、实际文件、plan schema、runner 输入类型、G0、设备锁和单一设备操作。`device_run_allowed=true` 只在 G0 通过后短时有效，candidate 结束立即恢复为 `false`。缺 stock boot provenance、使用 derived DT 或缺少 positive control 的计划必须明确标记为离线控制。

Adjudication gate 必须保存 raw、日志、runner summary、设备恢复状态和所有镜像完整 SHA，并区分 `CONFIRMED`、`REFUTED`、`UNVERIFIED` 和 `INCONCLUSIVE`。缺 candidate/final raw 时，不能裁决 marker 是否执行，也不能把断联归因 XNU fault。裁决者不能是产出候选结论的同一执行体。

## 参考仓库和复用

第一次进入项目或参考根变化时生成 `REFERENCES.md`，登记仓库名、本地路径、commit、上游地址、许可证、覆盖硬件或子系统、可复用入口和对应模块。

写代码、设计寄存器访问、解释启动失败或选择 DT 前，先检索 `xnu-ios12`、`xnu-current`、`linux-msm8916`、`lk2nd-msm8916-mainline`、`DarwinBoot`、`ArmCpu` 和 `ArmDTPlatform`。命中记录为 `REF path:line commit`。无命中记录为 `NONE-FOUND query scope`。直接移植或改编优先，对照参考重写其次，从零实现必须说明原因和验证方式。复制代码保留许可证和来源。

失败后先查参考仓库中的错误串、寄存器、compatible、启动顺序和实现，再提出新假设。没有完成参考检索的假设不得进入设备运行计划。

## sub-agent 调度

主线程负责设备互斥、最终整合和关键路径。sub-agent 只做离线工作，每个任务必须有独立输入、输出文件、停止条件和禁止事项。

以下情况至少派发一个 sub-agent。存在两个或更多互不依赖任务时，同时派发两个或三个。

- 搜索多个参考仓库或超过五个文件
- 实验独立裁决或原始回读裁决
- 长构建或长等待超过五分钟
- 源码、容器、probe、日志或参考差异可以并行核查
- 社区、issue、PR 或论文检索

默认角色是 reference agent、evidence agent 和 control agent。主线程不得重复已完成的 sub-agent 任务。sub-agent 返回后，主线程检查输出路径和关键证据，再把复核结果写入账本。没有独立输出或复核的 sub-agent 文字不能成为设备运行依据。没有可并行任务时不强行填满槽位。

## 经验沉淀

所有错误、误判、返工、漏检、gate 自身 bug、计划 schema 错误和路径漂移都追加到 `docs/sop/LESSONS.md`。每条记录现象、根因、影响、错误做法、正确做法、证据路径、对应 gate、是否自动化和下一次触发条件。

同类错误第二次出现时，在同一轮完成以下动作。

1. 加入适用 gate 或负对照。
2. 更新对应 `docs/sop/*.md`。
3. 更新或创建对应 `docs/skills/*/SKILL.md`。
4. 在账本记录修订后的入口和验证命令。

构建、打包、回读解析、哈希绑定、参考检索和实验裁决都必须使用项目级 SOP 或 skill。主线每次恢复先读相关 lessons，再开始工作。

## 长时间运行、恢复和停止

长构建、设备启动和等待操作可以继续运行。主线程每 30 至 60 秒读取真实进程和产物状态，并继续做不冲突的离线工作。进程存在不代表成功，必须以 provenance、退出码、产物和完整哈希确认。

上下文压缩、会话恢复或异常退出后，第一步重新读取本文件、`LIVE-TARGET.md`、`STATE.md` 和账本末尾，再检查进程与锁。不能依据记忆中的轮次、PID、路径、阶段或下一步继续。

合法完成状态只有 `DONE` 和 `HARD_BLOCK`。单个候选失败、工具报错、设备未回读或假设被证伪都结束当前候选并转入状态机下一步。

`DONE` 只在 D1、D2、D3 独立确认后使用。`HARD_BLOCK` 只适用于设备在全部可用模式无法识别且 LKG 恢复失败、必须人工完成且没有自动替代的物理动作、权限或网络使所有有效路径不可执行、平台终止额度或会话。进入 `HARD_BLOCK` 前完成可做的离线参考、证据和 SOP 工作，并写 BLOCKER 账本条目。

## 不可变的驱动目标

- M1 内核入口执行并有 nonce 回读
- M2 MMU、异常向量、早期控制台、定时器和中断控制器
- M3 全量内存、多核和 bsd_init
- M4 eMMC 与根文件系统
- M5 launchd PID 1 与基础用户态
- M6 显示、背光、触摸和 SpringBoard

P0 包含中断、定时器、时钟、电源、pinctrl/GPIO、日志、eMMC、USB、显示、背光、触摸和按键。P1 包含电池、RTC、热管理、振动和音频。P2 包含 Wi-Fi、蓝牙、传感器、相机、基带和 GPS。实际硬件清单以 Y35A 证据为准。
