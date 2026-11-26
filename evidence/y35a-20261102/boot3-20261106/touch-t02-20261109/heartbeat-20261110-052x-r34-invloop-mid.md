# 心跳 20261110-052x: R34 十四连阳 — INVPREF0/INVONE00 双失效循环哨兵命中, 停点推进到 bootstrap 页表 invalidation 循环中部(Linvalidate_bootstrap 内首次 store 后); Codex 已到 R36 构建; LOG 六代回写仍 M

时刻 05:2x。HEAD=739d533(本线顶)。设备 efff9d92 fastboot
空闲。零设备指令。

## 1. R34 独立解码(阳性十四连)

Codex 05:09-05:11 实跑 `phase-r34-carrier-20261110-070000/`
(计划时戳 070000; R34 无 preflight 目录 — 预检记录未单独落,
归其 R35 收尾一并处理)。final.raw SHA `4c0d27d3ad2836bb…`:

- 链式: baseline = R33 final(`f1270383…`) ✓; 核前缀
  d49e9d3e801a57d8 = r34 kernel SHA 首 8 字节(record 未写,
  SHA 全值待收)✓; 双 header ✓;
- R33 十二连全复现(slot4/17/18/22..38) ✓;
- **新阳: slot39@0x178 = `INVPREF0`(失效循环即将开始)
  + slot40@0x180 = `INVONE00`(首张 bootstrap 表 store
  完成)** — 两道新增哨兵全命中;
- slot41.. 起仍零(含后续循环条目/完成哨兵/映射/MMU/C 系);
  early_fault 零。

**几何自洽核验**(防错位): 失效两件 patch
(`native-invalidation-setup-witness.patch` /
`native-invalidation-witness.patch`)的写点
`[x20,#0x938]`(INVPREF0)与 `[x20,#0x940]`(INVONE00)对应
carrier body `0x178/0x180`, 恒定差 `0x7c0` — 与 ARGSLOAD
(`0x888→0xc8`)、STACKS00(`0x8d0→0xd0`)同一映射, 无槽位错位。
patch 落点语义: INVPREF0 在 `Linvalidate_bootstrap:` 标号前,
INVONE00 在首次 `str x0,[x1]` 之后、`subs entries--` 之前。

裁决: **执行确证进入 bootstrap 页表失效循环并完成首次
store**, 停点 = 循环内首次 store 后、后续条目/循环完成哨兵
前。R33 的"INVALID0 前"再进一级: 现在挂死候选在循环体中段。

## 2. Codex 已到 R36 构建(进程实测)

pgrep 实拍: `build-xnu-4903-kernel.py --output ...-r36
--fresh` 容器进程(pid 75265)在跑 — R35 编号在途/可能跳过,
R36 内核构建中。Codex 节奏从 ~25min/代 提到更快, 收尾
record/LOG 跟不上的纸面欠账同步扩大。

## 3. 治理与三闸

- R34 record 未收(实跑结束 10+ 分钟); R22/R24/R27/R30 四笔
  仍缺; **LOG.md 六代回写仍 M 未入库**(实查); witness patch
  计数 10(新点名: args-physical/bootargs/entry/handoff/
  invalidation-setup/invalidation/kva-calc/pre-mmu/stack-link/
  startup 十件全 untracked; 其中失效两件 = invalidation-setup
  + invalidation 为本轮新现);
- 全套新鲜 `Ran 96 OK`(kernel_build 10 不变);
- probe 双 M 原样, 收口未发生, 不记 stalled。

## 4. 下轮盯点

R36 实跑结果(预期: 失效循环完成哨兵 INVDONE0/映射构建
MAPDONE0 的阳性或定位); R35 是否跳号; LOG 回写是否入库;
第 11 件后 patch 清单。

verify: python3 逐字节解码 R34 final.raw(48 槽非零筛+sha+
链式 baseline=R33 final+双 header); decoded-fields.txt
slot_39/40 互证; patch 两件写点 0x938/0x940 与 body 0x178/
0x180 差 0x7c0 恒等算术实算; grep INVPREF0/INVONE00 落点
语义实读; pgrep build-xnu r36 进程实拍; git status LOG=M
实查; unittest discover 新鲜(Ran 96 OK); fastboot devices —
全部本轮执行。
作者: lingion <lingion@hrbeu.edu.cn>
