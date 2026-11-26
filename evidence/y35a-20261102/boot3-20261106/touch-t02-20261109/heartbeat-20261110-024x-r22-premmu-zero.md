# 心跳 20261110-024x: R22 pre-MMU 四哨兵实跑完毕且独立解码全零 — 停点再收窄至 ARMENTRY→common_start 之间; witness patch 四件仍 untracked(缺陷 A 同型风险重演)

时刻 02:4x。HEAD=b98f67a(本线顶)。设备 efff9d92 已回 fastboot
空闲,无 fastboot 进程。零设备指令。

## 1. R22 实机序列独立复核(不转述)

Codex 02:25-02:28 跑完 `phase-r22-carrier-20261110-022528/`
(九件+decoded-fields.txt, record.md 未写归其收尾)。preflight
布局: slot13 COMMON00(映射前入口) / slot14 MAPDONE0 /
slot15 TTBRDONE / slot16 PREMMU00(SCTLR 写前即刻)。

本线 python 直接解码 final.raw(SHA-256
`1408bb2401be5333…` 全值对 decoded-fields.txt ✓):

- 0x60 = `ARMENTRY` ✓;
- 0x98 MMUON000 = 0; 0xa0 ARMRET00 = 0;
- **0xa8/0xb0/0xb8/0xc0 四道 pre-MMU 新哨兵全 = 0**;
- C 槽 0x68..0x90 全零; 0x3c0 早退记录零;
- header `Y35AXNU2`/`Y35ARD02`, 核前缀 d7e0f5169d08e158 =
  r22 kernel SHA 首 8 字节 ✓;
- baseline 对照: 恰为 R21 final(`bef01803…`), 链式新鲜度 ✓;
- changed_ranges 仅 CNTVCT 见证字段(0x8/0xf808)与核前缀
  (0x10008)+1 字节杂项 — 无 carrier 内容漂移。

裁决: **XNU 停点 = `_start_first_cpu` 写 ARMENTRY 之后、
`common_start` 入口之前**。四道 pre-MMU 哨兵一把掐死了
"死在 MMU 激活"假设——连 common_start 都没进。下一刀归
Codex: 该区间内(入口到 common_start 之间还有何指令序列被执行
/异常)加更细哨兵或读异常向量落地态。

## 2. 治理观察: 缺陷 A 同型风险正在重演(登记, 不代改)

R22 的构建输入 `native-pre-mmu-witness.patch`(02:06)等**四件
witness patch 全部 untracked**(entry/handoff/pre-mmu/startup)。
00:5x LOG 勘误刚记过 kva-carrier patch 只存活于容器副本、本机
丢失、靠 docker cp 找回的教训(e466e02)——同一模式再次裸露:
实机证据 R22 的部分输入不在 git 里, 不可再生风险活着。R20
段结论"六个 instrumentation patch 里五个 untracked"至今未收口。
文件所有权归 Codex/fixer, 本线只登记提醒收口时按 commit-sop
入库。

## 3. probe 三闸与套件

双 M 触线原样(cpp 15:15 / py 14:54), contract 两件 02:34 又
被编辑(计数不变), 全套新鲜 `Ran 95 OK`。不记 stalled。

## 4. 盘态

守护 12362354 龄 ~4.27d(闸 5.2d), 保险丝 06:13 在位。GO 未回;
R21/R22 设备序列系 Codex 线自有授权形态, 与本线纪律不冲突。

verify: ls -la R22 目录 mtime; python3 逐字节解码 final.raw 八
位点+header; baseline.raw 哈希对照 R21 final; decoded-fields.txt
与 shasum 全值互证; patch 目录 git log/untracked 实查;
python3 -m unittest discover 新鲜(Ran 95 OK); fastboot devices;
pgrep fastboot — 全部本轮执行。
作者: lingion <lingion@hrbeu.edu.cn>
