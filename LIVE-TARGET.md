# UniXNU 当前实时目标

更新时间：2026-11-27。每次恢复和每轮开始先读此文件。本文只描述当前阶段，阶段变化必须同步 `STATE.md`、`CURRENT.md`、`LONG-RUN-STATE.md` 和 `LOG.md`。

## 当前主目标

完成 R208 TF/SD 启动链的离线闭环。所有可复现的 UniXNU 编译、链接、主机验证、静态门禁、package/probe plan 和产物 hash closure 只在 GitHub Actions 执行，并以真实 CI run 及其绑定产物为准。任何本机磁盘都不得运行 UniXNU 编译、链接或大规模构建。R205、R205b、R205c、R206 均为历史候选，不得重跑。R207 v2 builder 已终止，禁止重启。

## 当前事实

- R206 已通过 build、static verification、linked guard/order、binding、package 和 probe gates。
- R206 唯一一次 RAM-only paired MVE 在 candidate boot 后断联，candidate/final raw 缺失，设备已回到 `efff9d92 / lk2nd-msm8916 / unlocked fastboot`，无持久写入。
- R204b fresh final 含 `PEBARGRT`，R206 slot `0x52` 无重复 writer，marker carrier transport 尚未被证据定位为根因。
- R207 设计保留首次 `*args` 读取和空值分支，移除 `ARG1RD00` 写入。设计文件为 `/Volumes/Mobile/unixnu-research/reboot-checkpoints/R207-bootargs-read-no-marker-control-design-20261126-01/R207-control-plan-v2.json`。
- R207 v1 已因损坏 patch 失败。R207 v2 外置盘 builder PID 90604 已按用户要求终止，未产生 provenance 或 kernel artifact。R207 不得重启或在任何本机磁盘重新构建。
- 当前 `device_run_allowed=false`。R207 不再是当前主线目标，不能抢占 R208 的 CI 和 TF/SD 工作。
- R208 已完成 SD 协议 host suite、sdhc2 ADT contract、root-selection positive/negative contract、NativeSdcard object compile、IOStorageFamily-191 combine、确定性 archive 和 Docs CI。main 的最新 validation run `45882596692` 与 Docs run `45882596678` 均成功，绑定 commit `53966d60ea558dae8a12c795736e8418bcc8cca9`。XNU kernel link、package/probe、TF GPT/APFS image、root mount、eMMC fallback 和设备运行仍未完成。
- 本轮对 `/Volumes/Mobile` 的访问返回 `Input/output error`，未对该卷继续扫描或写入。`/Volumes/Portable` 已确认可用，仅作为临时 staging 盘；它不是 canonical 工作树，也不运行 UniXNU 编译。
- 临时 staging `/Volumes/Portable/UniXNU-staging-20261127-0042` 已按提交 `68b2cf91038fedb1ccacdc5950223ef618d8215e` 导出；manifest SHA-256 为 `a4d970a878c88c8e21dbfeeca086f78d2f8fad0b09180584048b4430ee0d8538`，逐文件校验 1424/1424 通过。
- native-link 当前状态：run `45882865622` 在 commit `53966d60ea558dae8a12c795736e8418bcc8cca9` 完成 plan-only，native inputs、source provenance、driver archive binding 和 native command plan 均通过；`execute=false`，未执行 kernel build，也没有 kernel artifact。package workflow 仍等待同一 SHA 的 successful execute run artifact。
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

根据 R208 GitHub Actions 结果补齐 native link 输入并扩展 kernel-link/linked-gate job，直到 XNU link、package/probe 和 hash closure 都有对应 CI 证据。失败先追加 lessons，再修正 CI 或输入。NativeSdcard、TF image、root mount 和 fallback 未闭合前不写卡、不启动设备。任何本机磁盘上的 UniXNU 编译保持关闭。
