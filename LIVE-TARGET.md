# UniXNU 当前实时目标

更新时间：2026-11-27。每次恢复和每轮开始先读此文件。本文只描述当前阶段，阶段变化必须同步 `STATE.md`、`CURRENT.md`、`LONG-RUN-STATE.md` 和 `LOG.md`。

## 任务状态（最高优先级，不随阶段变化）

MISSION: IN_PROGRESS | D1 NOT_MET | D2 NOT_MET | D3 NOT_MET

- 任何 CI 绿灯、离线闭环、gate 通过、文档同步都不改变 MISSION 状态。
- 只有 Y35A 设备上的 raw 证据能把 D1、D2、D3 改为 MET，且必须附 raw 路径、完整 SHA-256 和独立裁决者。
- D1、D2、D3 全部 MET 前，禁止输出“目标完成”“任务完成”“阶段完成”或 DONE。当前合法状态只能是 IN_PROGRESS 或 HARD_BLOCK。

## 当前目标与策略

最终使命仍是 D1、D2、D3。当前工作阶段为 R208 native kernel build 与输入闭包，设备目标尚未验证。UniXNU 编译、链接、主机验证、静态门禁、package/probe 和哈希闭包只通过 GitHub Actions 执行。所有本机磁盘均禁止 UniXNU 编译或链接。R205、R205b、R205c、R206 不得重跑，R207 v2 builder 不得重启。

## 当前执行状态

- 截至 2026-11-27 07:33 UTC，MISSION 为 `IN_PROGRESS`，D1、D2、D3 均为 `NOT_MET`，`device_run_allowed=false`。
- Native execute run `45956827212` 绑定提交 `bd7615046eb01a42e74fa0a3e6194331e0557a29`，已在实际 native build 步骤失败，没有 kernel artifact。失败后的主线修复正在将 Firehose 输入切回包含 XNU 4903 所需配置 API 的 libdispatch 1477，并为其 atomic private header 补兼容输入。
- Package 分支最新已推送提交为 `c30f0852346a7ec1b9cfcb8c04c83b7fb431a102`。package workflow 的合同验证 run `45957683974` 成功，但 native-run 校验步骤以及 package 和 TF/APFS jobs 被跳过。`workflow_dispatch` 对真实成功 native artifact 的消费仍待验证。
- GitHub Actions 当前能够启动。Billing 不再是当前阻塞条件。stock PD1502A QCDT 仍未取得可核验来源，Mobile 卷读取曾返回 I/O error。该输入影响后续 TF/APFS 设备包闭环，不阻止 native kernel build 继续推进。
- 当前下一步是完成 Firehose 1477 与 atomic compatibility 输入修复，推送后由 GitHub Actions 验证，再以新 native run 的真实终态决定下一步。只有成功且哈希绑定的 kernel artifact 才能进入 package/probe 流程。
- 真机、TF 卡、USB、fastboot、adb 和串口目前均未操作。native build、package、TF/APFS、root selection、eMMC fallback 和设备运行仍需各自证据闭环。

## 历史事实与边界

- R206 已通过 build、static verification、linked guard/order、binding、package 和 probe gates。
- R206 唯一一次 RAM-only paired MVE 在 candidate boot 后断联，candidate/final raw 缺失，设备已回到 `efff9d92 / lk2nd-msm8916 / unlocked fastboot`，无持久写入。
- R204b fresh final 含 `PEBARGRT`，R206 slot `0x52` 无重复 writer，marker carrier transport 尚未被证据定位为根因。
- R207 设计保留首次 `*args` 读取和空值分支，移除 `ARG1RD00` 写入。设计文件为 `/Volumes/Mobile/unixnu-research/reboot-checkpoints/R207-bootargs-read-no-marker-control-design-20261126-01/R207-control-plan-v2.json`。
- R207 v1 已因损坏 patch 失败。R207 v2 外置盘 builder PID 90604 已按用户要求终止，未产生 provenance 或 kernel artifact。R207 不得重启或在任何本机磁盘重新构建。
- 当前 `device_run_allowed=false`。R207 不再是当前主线目标，不能抢占 R208 的 CI 和 TF/SD 工作。
- R208 已完成 SD 协议 host suite、sdhc2 ADT contract、root-selection positive/negative contract、TF/eMMC fallback contract、NativeSdcard object compile、IOStorageFamily-191 combine、确定性 archive 和 Docs CI。main 的 validation run `45884101324` 与 Docs run `45884101618` 均成功；最新 TF validation `45887232679` 全绿，绑定 main commit `425ec007c2973fc14c81f64f14898138340cca3c`; this state correction is included in main `2b45f50`. XNU kernel link、package/probe、TF GPT/APFS image、root mount、eMMC fallback implementation 和设备运行仍未完成。候选 XNU fallback patch 已单独通过 pinned XNU apply-check，但尚未进入 native manifest。
- 本轮对 `/Volumes/Mobile` 的访问返回 `Input/output error`，未对该卷继续扫描或写入。`/Volumes/Portable` 已确认可用，仅作为临时 staging 盘；它不是 canonical 工作树，也不运行 UniXNU 编译。
- 临时 staging `/Volumes/Portable/UniXNU-staging-20261127-0042` 已按提交 `68b2cf91038fedb1ccacdc5950223ef618d8215e` 导出；manifest SHA-256 为 `a4d970a878c88c8e21dbfeeca086f78d2f8fad0b09180584048b4430ee0d8538`，逐文件校验 1424/1424 通过。
- 历史 native run、package run 和早期输入阻塞详见下方历史记录及 `LOG.md`。这些记录不能覆盖“当前执行状态”中的最新 run、最新分支提交和活动修复。
- TF/SD 设备路线当前只允许离线工作。TF 卡容量、sdhc2 协议、card-detect、root mount、回退到 eMMC 和真实卡绑定都没有实机证据。
- R208 CI manifest 已绑定 exact XNU ref、六个 arm-driver patch 的 SHA 和 native build profile。NativeSdcard object SHA-256 为 `47bec72ade1ff792938b9ae468f778a7d7e4c13bb62f97d18e5dbf96242e900e`，combined object SHA-256 为 `0353a170088989517d6634805f16537e26844fa89bd2acf9040dffd3cfa400fd`，确定性 archive SHA-256 为 `f401224182f56a5d27532482c1978528ae1570c3d5b16931b98384a6aaba1e73`。较早的 object/header 失败 runs 保留在 `LOG.md`，不再作为当前状态。

## 同步和编译策略

私有同步仓库为 `https://github.com/lingion/UniXNU-y35a-private`。代码、目标、SOP、skills、CI 配置和证据元数据持续同步到该仓库。移动硬盘只承载源码缓存、run roots、CI 下载产物、设备备份和 raw。所有可复现构建与验证走 GitHub Actions。真机 USB、设备锁和 CI 无法访问的本地输入留在本机，不能触发本地 UniXNU 编译。

## 本轮允许的动作

1. 保持 R207 builder 已终止，不在任何本机磁盘重启构建。
2. 在 GitHub Actions 上补齐 native kernel-link 所需的 fakeroot、SDK overlay、wrapper、source provenance 和 driver archive 输入闭包。
3. 完成 TF GPT/APFS layout、eMMC fallback、sdhc2 card-detect 和 root selection contract 的离线验证。
4. 生成 R208 package/probe plan 和 artifact hash closure，保持 `device_run_allowed=false`。
5. 主线或独立 evidence agent 完成后，更新状态摘要和 lessons。

## 本轮禁止的动作

- 重跑 R205、R205b、R205c 或 R206。
- 在任何本机磁盘复制构建输入后启动 UniXNU 本地编译、链接或大规模构建。
- 操作 Y35A、USB、fastboot、adb、串口或持久分区。
- 在 CI manifest、package、probe、TF image 和回退方案全部通过前写 TF 卡或启动 TF 候选。
- 使用旧 manifest、旧 probe、旧地址或旧 gate SHA 冒充 R207 结果。
- 把 derived DT 或缺失 stock boot provenance 写成 stock 证据。

## 下一条可执行动作

主线完成当前 Firehose 1477 输入修复并通过 CI 后，按最新 native run 推进 package/probe 输入闭包。若同一子任务连续两轮没有新证据或门禁进展，记录根因并转向另一条可执行路径，不重复原地尝试。所有本机磁盘继续禁止 UniXNU 编译和链接，`device_run_allowed=false`。
