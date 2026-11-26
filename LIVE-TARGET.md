# UniXNU 当前实时目标

更新时间：2026-11-26。每次恢复和每轮开始先读此文件。本文只描述当前阶段，阶段变化必须同步 `STATE.md`、`CURRENT.md`、`LONG-RUN-STATE.md` 和 `LOG.md`。

## 当前主目标

完成当前 R207 no-marker 离线控制的 source/build/link/package/probe 门禁，判断去除 `ARG1RD00` 写入后 candidate-stage disconnect 是否仍存在。R205、R205b、R205c、R206 均为历史候选，不得重跑。

## 当前事实

- R206 已通过 build、static verification、linked guard/order、binding、package 和 probe gates。
- R206 唯一一次 RAM-only paired MVE 在 candidate boot 后断联，candidate/final raw 缺失，设备已回到 `efff9d92 / lk2nd-msm8916 / unlocked fastboot`，无持久写入。
- R204b fresh final 含 `PEBARGRT`，R206 slot `0x52` 无重复 writer，marker carrier transport 尚未被证据定位为根因。
- R207 设计保留首次 `*args` 读取和空值分支，移除 `ARG1RD00` 写入。设计文件为 `/Volumes/Mobile/unixnu-research/reboot-checkpoints/R207-bootargs-read-no-marker-control-design-20261126-01/R207-control-plan-v2.json`。
- R207 当前 builder provenance 曾报告 `status=failed`，patch 初版格式损坏。主线正在等待现有 builder 状态终结，再对 `R207-no-arg-marker-control-v2.patch` 进行独立 `git apply --check`。不得重启或并行启动第二个 R207 builder。
- 当前 `device_run_allowed=false`。R207 只有在新的 package/probe gates、运行计划和 G0 全部通过后才可评估设备运行。

## 同步和编译策略

私有同步仓库为 `https://github.com/lingion/UniXNU-y35a-private`。代码和可重现验证持续推送到该仓库。移动硬盘只承载外置源码缓存、run root、构建产物、设备备份和 raw。主机验证、静态门禁、合同检查和能在 CI 复现的编译走 GitHub Actions。真机 USB、设备锁和 CI 无法访问的本地输入留在本机。

## 本轮允许的动作

1. 读取现有 R207 builder 的真实状态和 provenance。
2. builder 结束后，对 v2 patch 做独立格式检查、精确源树 `git apply --check` 和 source diff 检查。
3. 只读核对 R207 设计、源树、patch 链和参考仓库，并把结果写入候选目录。
4. 主线或独立 evidence agent 完成后，更新状态摘要和 lessons。

## 本轮禁止的动作

- 重跑 R205、R205b、R205c 或 R206。
- 在现有 R207 builder 结束前重启、复制输入或启动第二个 builder。
- 操作 Y35A、USB、fastboot、adb、串口或持久分区。
- 使用旧 manifest、旧 probe、旧地址或旧 gate SHA 冒充 R207 结果。
- 把 derived DT 或缺失 stock boot provenance 写成 stock 证据。

## 下一条可执行动作

等待并读取 R207 builder 的最终 provenance。若失败，保存失败原始日志并运行 `git apply --check` 诊断 v2 patch。若成功，读取 kernel SHA 后进入 `LINKED-GATE`，再生成新的 package/probe gates。任何阶段失败都先追加 lessons，再决定下一候选。
