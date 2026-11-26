# 心跳 20261110-020x: R21 负观测已收 record.md 且逐字节独立复核吻合; XNU 停点收窄 = ARMENTRY 后、SCTLR_EL1 写前; probe 三闸零漂移

时刻 02:0x。HEAD=4a1ff17(本线顶)。设备 efff9d92 在 fastboot。零设备指令。

## 1. 上轮承诺兑现: R21 收尾核对(独立解码, 非转述)

Codex 已于 01:55 给 `phase-r21-carrier-20261110-014546/` 收
record.md。本线按复查纪律直接对 final.raw 逐字节实解:

- 文件 69,632 字节, SHA-256 `bef01803…` 与上轮见证及
  input-hashes.txt 一致;
- body 0x60 = `ARMENTRY` — slot4 入口哨兵在;
- body 0x98 = 全零 — **MMUON000 未到**(SCTLR_EL1 写+ISB 后哨兵);
- body 0xa0 = 全零 — ARMRET00 未到(下游, 不构成独立信息);
- C slots 0x68..0x90 全零, 0x3c0 早退记录地址全零;
- header 0x10000=`Y35AXNU2`, 0x10040=`Y35ARD02`,
  核前缀 9c44033b68034181 = r21 kernel SHA 首 8 字节 ✓。

裁决: **record 八项声称逐条吻合, R21 负观测成立**。停点较
r18-r20 再收窄一级: `_start_first_cpu` 执行过 ARMENTRY 写入后,
死在(或异常于)`SCTLR_EL1` 写/ISB **之前**。R22 计划(归 Codex,
record 尾节)在 pre-MMU 引导段加四道物理 carrier 哨兵: entry→
common_start 前、bootstrap 映射建后、TTBR 发布/屏障后、
SCTLR_EL1 写前即刻。

## 2. probe 三闸零漂移

双 M 触线(cpp 15:15 / py 14:54)、contract 三件(kernel_build
01:21 / phase_instr 00:48 / probe_rmi 14:54)与 01:5x 完全一致;
板上收尾声明仍在, 不记 stalled。无新 commit 进入探针路径。

## 3. 盘态

- GO 定义仍按板上流程(R21 序列 Codex 自行判定已获授权执行,
  设备现回 fastboot 空闲);
- 守护 12362354 龄 ~4.24d(闸 5.2d), 保险丝 5f873c8d 下轮
  06:13; untracked 在途件全他线所有, 零接触。

verify: git log/status 实跑; ls -la 两目录 mtime; python3 直接
解码 final.raw 八项(本轮新鲜逐字节); input-hashes.txt 实读;
record.md 全读; fastboot devices — 全部本轮执行。
作者: lingion <lingion@hrbeu.edu.cn>
