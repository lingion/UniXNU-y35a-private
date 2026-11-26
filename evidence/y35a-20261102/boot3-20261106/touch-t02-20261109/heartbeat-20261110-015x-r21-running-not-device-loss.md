# 心跳 20261110-015x: probe 三闸零漂移; fastboot 列表瞬空目击 = Codex R21 实机序列在跑, 非设备失联(勿据此立案)

时刻 01:5x。HEAD=f765efd(本线 01:2x 证据顶)。零设备指令。

## 1. 设备"消失"疑云与裁决过程(记全过程防后人误读)

- 01:42:xx `fastboot devices` = `efff9d92 fastboot` — 在;
- 01:50:15 同命令 = **空列表**;
- 处置(确定性探测优先, 模型不判死): 复检三层 — fastboot 仍空、
  adb 只有 emulator、USB 枚举无 Qualcomm 节点、`pgrep fastboot`
  无进程 → 表象与"拔线/失联"一致;
- 但 evidence/ 新目录 `phase-r21-carrier-20261110-014546/`
  (01:46 建)正逐分钟长文件: 01:48 baseline.raw → 01:50
  boot-r21.log → 01:51 boot-probe-r21.log → 01:52 final.raw;
- 01:53 复检: `efff9d92 fastboot` **回来了**, final-get-staged
  尾行 OKAY。裁决 = RAM-boot 序列中途设备必然离开 fastboot 列表
  (booting→运行→重启回 fastboot), 瞬空是**正常形态**, 非事故。
- 纪律沿用: 列表空先查他线实机序列目录 mtime 与进程, 再谈设备
  健康; 本线只读不碰 Codex 的实验目录与 record.md 写权。

## 2. R21 序列状态(归 Codex 收尾)

preflight 记录(离线闸 95/95 全绿, 假设 = MMUON000/ARMRET00 双
汇编哨兵区分 MMU 致能 vs 装配-C 边界)与 device-run 九件已齐,
唯缺 record.md 收尾。final.raw SHA-256
`bef018039dcda4ca7cbed697ae3aad93d72c8c0e3becc698e24f56517f09b406`
已见证(本轮实算)。下轮核对 slot 解码与 LOG 回写即可。

## 3. probe 三闸零漂移

双 M(cpp 15:15 / py 14:54)、四 contract untracked、计数构成
与 01:2x 逐字节一致, 不重复展开。fixer 近 30 分钟无落盘 — 有
板上收尾声明在前, 维持不记 stalled。

verify: fastboot devices 三轮实跑(01:42 在/01:50 空/01:53 在);
adb devices; system_profiler USB grep; pgrep fastboot;
ls -la R21 目录逐文件 mtime; tail final-get-staged.log;
shasum -a 256 final.raw; git log/status/mtime 全套 — 本轮新鲜。
作者: lingion <lingion@hrbeu.edu.cn>
