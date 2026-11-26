# Y35A 显示驱动交付链离线核查

- 时间：2026-11-25 离线周期
- 范围：只读本地注册表、驱动计划与 GopFramebuffer 源码；未操作设备、USB、fastboot、adb、串口或持久分区，未运行构建。
- 主线边界：不重复 R172 HID bracket/静态门，不重复审查会话的 QUP I2C/触摸主机测试。

## 证据与 SHA-256

1. `devices.toml`
   - SHA-256：`ef560d4e58226f7ed1102b9e5b7897ee1c7e1310142f56bb41e8ba8afbd2763e`
   - 对 `y35a`、`pd1502a` 的大小写不敏感检索无匹配；`vivo` 仅命中其他设备条目。
2. `components.toml`
   - SHA-256：`bc0609d126c050650dbe94136cad6071ef73b23d30e99fdbb9faf41f78a9c53a`
   - `GopFramebuffer`：`hardware=["UEFI GOP framebuffer"]`、`os_abi=["ipados-17.7.11-21H461"]`、`verified_devices=["sheng"]`。
3. `docs/porting/ios12/drivers-plan.md`
   - SHA-256：`21874187559933adb72d4db95d0dfa89fcb17562c8643752f91c4e0ce89b32b1`
   - Y35A 显示地板引用 lk2nd continuous splash `0x83200000`、720×1280 RGB888、stride 2160，并计划复用 `NativeLegacyDisplay`/`NativeMobileDisplay` ABI。
4. `drivers/GopFramebuffer/NativeLegacyDisplay.cpp`
   - SHA-256：`9d3c7681e262f14f4e4c9222aeb6b22b0b30dcd5fe8125194a35d036306bf283`
   - 源码明确以 firmware GOP framebuffer、GOP mapping 与无 vblank 中断为前提。
5. `drivers/GopFramebuffer/README.md`
   - SHA-256：`c862aa874649f63a5c15fcb3e54ced2b332715a2bfce04ee4895c1381b55207b`
   - 组件自述为 UEFI GOP framebuffer 与 MobileFramebuffer 集成。

## 事实

- 中央 `devices.toml` 没有 Y35A/PD1502A 设备条目，因此没有可复核的“Y35A → 显示组件”选择链。
- 唯一被目录登记的 `GopFramebuffer` 组件绑定 UEFI GOP 硬件、iPadOS 17.7.11 ABI，且只列 sheng 为 verified device。
- Y35A 计划中的输入是 lk2nd 已点亮的 continuous splash，而不是 UEFI GOP；计划明确把 framebuffer+CPU-render 作为 display floor，但未给出 iOS 12 ABI 适配后的组件身份。

## 待确认

- Y35A 的 0x83200000 splash 是否能在 XNU 侧保持连续映射、正确 stride/pixel format，并由选定的 IOMobileFramebuffer 子类安全读取。
- `NativeLegacyDisplay`/`NativeMobileDisplay` 的 vtable、size 与 power/vsync 语义是否与 iOS 12.4.1 的 IOMobileFramebuffer ABI 完全一致。
- 显示组件在 Y35A prelink/package 中的 bundle identity、依赖与链接产物。

## 推断与影响

- 现有证据支持“Y35A 显示地板仍是工程设计计划”，不支持“GopFramebuffer 已是 Y35A/iOS 12 的已验证显示驱动”。
- 这不阻塞当前 R172 早期启动边界；但 SpringBoard/可见 UI 验收前必须先闭合设备选择、iOS 12 ABI 与 splash handoff 三项。

## 单一步骤建议

先新增一份离线 Y35A 显示 profile 草案，只记录设备组件选择、iOS 12 IOMobileFramebuffer ABI 校验点和 lk2nd splash handoff 契约；在通过源码/二进制交叉校验前，不把 `GopFramebuffer` 标记为 Y35A verified。
