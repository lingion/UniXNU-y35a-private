# 心跳 20261110-062x: R40 停点跨代稳定复现(逐槽与 R39 一致: x2=1/x1=0xa3483ff8/文字 25 哨兵); R41 目击在跑(final 阶段), 设备瞬离列表 = 实跑中途正常形态; 本线未待终局, 记录中间稳态

时刻 06:2x。HEAD=1857c02(本线顶)。零设备指令。

## 1. R40 独立解码(换代镜像, 结果逐槽复现)

Codex 06:13 前已跑 R40(06:04-06:07, 目录
`phase-r40-carrier-20261110-100000/`, 无 record)。final.raw
SHA `ccf37747c8a6be88…`, 链式 baseline = R39 final
(`a4d29011…`) ✓:

- 文字哨兵 25 道(slot4..45)全复现, 数值槽 x22/x23 +
  slot46=1 + slot47=0xa3483ff8 + slot49=0xfffffff00702f7fa
  全复现 — **R40 与 R39 观测集完全相同**;
- early_fault 零。

裁决: **停点"失效循环中段(x2=1, 光标 0xa3483ff8)"在换代
镜像上稳定复现** — 非单代噪声。x2=1 意味着循环最后一条
目处理点前后是当前边界, INVALID0 完成哨兵仍不达。

## 2. 实跑中途目击(设备瞬离, 01:5x 纪律复用)

06:13:58 `fastboot devices` 有设备; 06:15 复查空 + pgrep 拍到
Codex 活跃 shell: `fastboot -s efff9d92 boot ...r41/boot3.img`
+ 15 轮 ×3s 轮询脚本(pid 85453)。R41 目录 06:15 正写
final-stage.log, final.raw 未落 — 实跑中途, 正常形态。
本线未追解码(等下轮终态), 未发任何设备指令。

## 3. 治理与盘态

- record 欠账 6+1=R40 亦未收(7 笔: R22/R24/R27/R30/R34/
  R39/R40); LOG 回写仍 M(实查);
- probe 三闸零漂移; 守护龄 ~4.45d, CronList 实拍(06:16):
  守护 next 06:21, 保险丝 next 06:43(昨晚 00:43 一班正常,
  本班即将自然触发); GO 未回;
- R39→R40→R41 节奏回稳 ~10min/代(R38 前 3min/代后)。

## 4. 下轮盯点

R41 终态解码(若 INVDONE/TTBR 系翻阳则停点进终局段);
R39/R40/R41 record 补收; LOG 六代回写入库。

verify: python3 逐字节解码 R40 final.raw 64 槽全枚举(sha/
链式/双 header/28 非零槽); ls -lat R40/R41 双目录时间线;
pgrep 实拍 Codex r41 轮询脚本 pid 85453 与命令行全文;
fastboot devices 两轮(06:13 在/06:15 瞬离); git status
LOG=M; record 七笔 MISS 实查 — 全部本轮执行。
作者: lingion <lingion@hrbeu.edu.cn>
