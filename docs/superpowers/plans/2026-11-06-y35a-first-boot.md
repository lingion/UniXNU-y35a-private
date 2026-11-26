# Implementation Plan: Y35A 首次开机关键路径(2026-11-06 起)

## Overview

唯一目标:iOS 12.4.1(XNU-4903 自研内核 + P4 rootfs)在 vivo Y35A 上第一次
跑进系统。进系统之前,GPU/WiFi/蓝牙全部停止;触摸 T4.3 已并行在途(会话
t4-3,subordinate)。本文件是心跳的未勾项索引,盘面以 git/文件为准。

## 已达成(记要,勿重做)

- [x] P1 内核 4903 构建+验证(5fd4e6b5,host out/y35a/ios12-kernel.noctf)
- [x] P4 rootfs: 58-binary closure → ramdisk-hfs.raw(54c07a60)+
      recovery trustcache(695f912e),closure 闸红绿过
- [x] boot2 终局取证: lk2nd 拒收点 = copy_dtb 功能闸(QCDT),40MB 闸证伪
      (真上限 256MiB);fork-pin aboot.c:412 条件从源重引
- [x] T-PKG: 四域 boot3 容器实装 + 产物
      out/y35a/ios12-boot3/boot3.img(54,618,112B d7640a42),闸 14/14 绿,
      字节级域验证过(569770c → … → 4352cbb)
- [x] 布局/决策文档: docs/board/boot3-container-layout.md(含 §6 实测)

## 关键路径任务

### A. 首次 boot3 实机点火(下一棒,设备操作)

- [ ] `fastboot boot out/y35a/ios12-boot3/boot3.img`(RAM-only,lk2nd
      fastboot 槽常驻,可逆;需用户在场或明确指令)
- [ ] 预期路径: lk2nd 收编 → pin 生效 → 解压 rootfs 入 ADT 窗口 →
      shim 进 XNU → early-fault/panic 记录入 pram(0x859e0000)/UARTDM
- [ ] 取证: `oem y35a panic` staged + serial 日志;判定 P3 缺件清单
      (GICv2 PIC?timer board 分支?console 早挂?)

### B. P3 板级 glue(按 A 的取证排序,先做被堵的那个)

- [ ] GICv2 pic 挂 4903 ArmCpu 抽象(Y35A board header 增补)
- [ ] pe_arm_init_timer board 分支(19.2MHz, INTID 20 已定)
- [ ] UARTDM 4903 版移植(17 世代补丁后移)
- [x] boot-args/ADT 契约复核(4903 布局 vs 打包器 4570 注释——若 boot
      停在 cmdline 解析即在此)
      结案 2026-11-07 3f4bcd3/ab204a0:4903 前缀逐字节正确(假 misread
      仅 4570 适用);真差异两尾场已锁——命令行上界 256(红绿三例
      BootArgsEraContractTest)、bootFlags/memSizeActual@0x170/0x178
      读 0 良性;ADT 半边由 test_board_adt 9/9 在 T4.1 收。boot3.img
      不需重打(cmdline 35B<256)。B 节剩余三项以 A 取证排序,离线不排。

### C. 进系统后(暂不动)

- [ ] eMMC 持久根(写分区前逐项用户确认,userdata 绝不动)
- [ ] 触摸 → GPU → WiFi → 蓝牙

## 风险与已知缺口

- rootfs 两代件哈希分叉(54c07a60 vs 4690a936):若挂载失败先回查 HFS
  repack 差异(cpio 同,体积同,UUID/时间戳级)。
- `--command-line "-v serial=3 cpus=1 debug=0x8 rd=md0"`:rd=md0 的 md0
  路径依赖 IOKitBSDInit 读 ADT RAMDisk——ADT 已给,若 root= 挂载报错,
  优先查 memory-map 节点形状而非内核。
- 若 lk2nd 仍拒收(理论上 QCDT+pin+256MiB 三条全过):读 fastboot 失败
  字符串定位到 cmd_boot 具体分支,禁止盲改容器。
