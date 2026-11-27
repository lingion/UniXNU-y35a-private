# UniXNU 实时目标

更新时间：2026-11-28。项目最终目标是 iOS 12.4.1 在 vivo Y35A 真机启动并可用；当前未证明真机进入 iOS 或可交互 SpringBoard。D1、D2、D3 均为 `IN_PROGRESS / NOT_MET`。

## 最终验收

- D1：同一确定镜像在 Y35A 上连续三次进入 launchd，每次稳定运行十分钟，并有绑定该镜像的现场证据。
- D2：进入 SpringBoard，显示真实系统界面，触摸与实体按键可交互。
- D3：按项目目标完成其余系统/驱动稳定性验收。
- 离线门、CI 绿灯、RAM diagnostic package、APFS control image 都是中间产物，不代表任何设备启动完成。

## 当前子任务：R208 离线 GPT/APFS 控制镜像

所有 UniXNU 编译、测试、静态验证、package 与 image 验证只允许在 GitHub Actions。本机只编辑和被动读取，不运行任何本地 UniXNU 验证命令。设备、USB、fastboot、adb、串口、TF 卡和持久分区本轮均未操作；`device_run_allowed=false`。

当前 topic 分支为 `codex/unixnu-ci-package-v2`。提交 `fdb347873c765cec278cb1c4ac554606a7e9f711` 加入 GPT scheme 与设备关系校验、xattr fallback 字节一致性；`a739997574207411b916c0c04b10849f3e9ac508` 同步 SOP/lessons；`518f8f4` 修复 pmap 查询时镜像仍 attached 的时序。后两项 run `46047857330` host validation 成功，`46047857312` package contract 成功并运行 63 个测试，但其实际 package jobs 按 push 事件跳过。`518f8f4` 的具体 Actions 验证仍待执行。

手动 offline-control run `46047971221` 使用已绑定输入：package run `46038856167`、RAM artifact `15218633072`，root-tree artifact `15219732795`。输入身份、下载、APFS image 创建、root-tree 写入和前置 metadata 检查均通过；在 image 仍 attached 时调用 `hdiutil pmap -simple` 失败，stderr 为 `Resource temporarily unavailable`。没有上传 control artifact。提交 `518f8f4` 已改为先成功 unmount/detach，再读取 image partition map，并加入命令顺序测试；仍待 Actions 验证。

该控制镜像使用 derived QCDT，只能标为 `offline-control-only`。stock PD1502A QCDT provenance、生产系统 root、kernel root selection、TF 卡绑定、eMMC fallback 实现、真正 TF/APFS system package、boot/probe 资格仍未闭合。不得称为可上机包或 iOS 启动成功。

## 下一步

1. 将 detach-before-pmap 修复与 R208 状态记录提交并推送私有 topic 分支。
2. 先确认该精确 SHA 的 Actions validation 成功，再用同一已验证 package/root-tree artifacts 跑一次离线控制镜像。
3. 按 run 的真实终态更新状态和账本。若 control image 上传成功，仍保持 offline-only；下一关键外部输入是可信 stock PD1502A QCDT 来源及 kernel 内 TF root/fallback 实现闭环。

## 持久化和恢复边界

- 所有本机磁盘禁止 UniXNU 编译、链接、测试、静态门禁、package/image 验证；CI 失败时修复 CI，不回退本地。
- `device_run_allowed=false`。不写 TF、eMMC、GPT 或启动链，不操作设备。
- 备份目录目前只有旧的 `boot.current.img` 与 `lk2nd.current.img` 候选；全分区备份及 EDL/firehose 恢复仍未验证，任何持久写入继续禁止。
