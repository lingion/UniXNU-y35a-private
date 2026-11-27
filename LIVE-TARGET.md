# UniXNU 实时目标

更新时间：2026-11-28。项目最终目标是 iOS 12.4.1 在 vivo Y35A 真机启动并可用；当前未证明真机进入 iOS 或可交互 SpringBoard。D1、D2、D3 均为 `IN_PROGRESS / NOT_MET`。

## 最终验收

- D1：同一确定镜像在 Y35A 上连续三次进入 launchd，每次稳定运行十分钟，并有绑定该镜像的现场证据。
- D2：进入 SpringBoard，显示真实系统界面，触摸与实体按键可交互。
- D3：按项目目标完成其余系统/驱动稳定性验收。
- 离线门、CI 绿灯、RAM diagnostic package、APFS control image 都是中间产物，不代表任何设备启动完成。

## 当前子任务：R208 离线 GPT/APFS 控制镜像

所有 UniXNU 编译、测试、静态验证、package 与 image 验证只允许在 GitHub Actions。本机只编辑和被动读取，不运行任何本地 UniXNU 验证命令。设备、USB、fastboot、adb、串口、TF 卡和持久分区本轮均未操作；`device_run_allowed=false`。

当前 topic 分支为 `codex/unixnu-ci-package-v2`；已验证的 package candidate source commit 为 `23502821148473f4baa411ec4dfe81745a4a9aa7`。提交 `fdb3478` 修复 GPT scheme、whole-disk/volume/parent 绑定与 xattr 字节摘要；`a739997` 修订 SOP/lessons；`518f8f4` 将 pmap 查询移到 unmount/detach 之后。host-validation `46049199580` 与 package contract `46049199572` 成功；后者 64 tests passed，但 push 事件按设计跳过实际 package jobs。

失败 run `46047971221` 的原因为镜像仍 attached 时查询 pmap。修复后手动 run `46049301112` 全部成功，实际验证了 scheme 与 parent binding，并上传中间 artifact `y35a-tf-apfs-offline-control-46049301112`：artifact ID `15224410131`，artifact digest `sha256:4182dbabd5303ffb1a348221150a774ac7b1b308504573afd1c0ec1edadd3c74`。镜像大小 4 GiB，image SHA-256 `8b7fae9326a0530f231487e1b48735b92780069aa11bef970b38e74c8bf093d4`；report SHA `62884f559efa7d9861738db5c977f9c82d352fd68467cc2310af4fa5ac50c3cd`，binding SHA `be14ac1ac9a3feefae4056eaba0bfb37639adb34f671e22f20c7f898c18564cd`。GPT scheme 是 `GPT`，该 CI image 的 whole-disk/volume/parent 为 `disk6`/`disk6s1`/`disk6`。这只是 CI 虚拟磁盘关系，不是手机卡绑定。

该控制镜像使用 derived QCDT，报告为 `offline-control-only`、`device_run_allowed=false`、`bootable=false`、`ios_system_image=false`、`springboard_included=false`、`touch_runtime_validated=false`。root selection 和 eMMC fallback 仍为 `unverified`。stock PD1502A QCDT provenance、生产系统 root、TF 卡绑定、真正 TF/APFS system package、boot/probe 资格仍未闭合。不得称为可上机包或 iOS 启动成功。

## 下一步

1. 以成功的 offline-control artifact 为只读中间产物，继续查可信 stock PD1502A QCDT 的来源/哈希；不扫描曾返回 I/O error 的 `/Volumes/Mobile`。
2. 并行闭合 kernel root selection 和首次 TF 读失败时的 eMMC fallback 实现及其 CI gates。
3. 重建 production root 和同一 provenance 闭包中的真正 TF/APFS package/probe；仍不操作设备或 TF 卡，直到目标合同与授权门完整满足。

## 持久化和恢复边界

- 所有本机磁盘禁止 UniXNU 编译、链接、测试、静态门禁、package/image 验证；CI 失败时修复 CI，不回退本地。
- `device_run_allowed=false`。不写 TF、eMMC、GPT 或启动链，不操作设备。
- 备份目录目前只有旧的 `boot.current.img` 与 `lk2nd.current.img` 候选；全分区备份及 EDL/firehose 恢复仍未验证，任何持久写入继续禁止。
