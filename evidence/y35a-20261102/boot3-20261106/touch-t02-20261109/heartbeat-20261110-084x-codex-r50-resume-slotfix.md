# 心跳 20261110-084x: Codex 复工实拍 — r50 构建中, R47/R49 传输失败的输入侧修复三件落地(HDR 哨兵挪槽 0x980-0x990 + HDRLAOD0 字节瑕疵已修 + loop-state 0x970/0x978 归还), 064x→075x 观察链获第二次设计级承认; 新第五笔同址观察(L1DONE00×L1ALLOC0 撞 0x990)登记; INVALID0 仍 VA 写法(报回三度未答)

时刻 08:4x(08:30:04 实拍)。HEAD=8f55eb6(本线顶)。设备
efff9d92 fastboot 空闲。零设备指令。

## 1. 复工与修复目击(输入侧, 构建未完无 final 可解)

pgrep 实拍 pid 16069: `build-xnu-4903-kernel.py --machine
T7001 --output ...-r50 --fresh` 容器构建中(08:2x 起)。
**新形态**: build 脚本首次带 `--machine T7001` 参数(此前
r11-r49 全无) — 脚本本身被改(tracked 文件), 具体语义留
Codex record。

嫌疑批(patch mtime 08:22/08:23 实拍)两件的修复逐项核实:

- **header-adjust**: 三哨兵写点 0x970/0x978/0x970 → **改
  0x980(HDRLOAD0)/0x988(HDRADJ00)/0x990(L1ALLOC0)** —
  离开 loop-state 数值槽; 且 python 逐字节重算 mov/movk:
  新立即数字面 = **`HDRLOAD0`**(0x414f 修正, 旧件算出
  HDRLAOD0 的换位瑕疵已修), HDRADJ00/L1ALLOC0 亦字面一致;
- **mapping**: 六槽 0x990/0x998/0x9a0/0x9a8/0x9b0/0x9b8
  (L1DONE00 起) — 同样离开 0x970/0x978;
- **loop-state**: 独占 0x970/0x978 归还, R39 的 x2/cursor
  数值目击恢复干净语义。

裁决: **R43 record 承诺的分槽("remove the loop-state slot
reuse")在 r50 输入上兑现**, 064x/068x/071x/075x 四笔同址
观察链闭合为设计级承认。传输失败是否随之消失待 r50 实测
(record 里若 probe boot 后 stage 恢复 OKAY, 则 R47/R49 卡
两代的镜像嫌疑实锤坐正)。

## 2. 新观察第五笔(同址双写者, 登记不代判)

build 脚本 apply 链实拍: mapping(line 410)**先** apply,
header-adjust(line 416)**后** apply — 两 patch 同批共存时,
**L1DONE00(mapping)与 L1ALLOC0(header)同写 [x20,#0x990]**。
运行时按 start.s 行序后者覆盖, 槽值仍可互斥判读(读到
L1ALLOC0=到 L1 分配未入映射循环; 读到 L1DONE00=映射循环
已过 store), 系"可判读链"而非硬 bug 的可能性大 — 但若
执行流恰卡两哨兵之间, 前值保留会遮蔽后段信息。登记归
Codex, r50 解码时按 0x990 读数分辨。

## 3. 报回项追踪(三度未答)

**INVALID0 仍 VA 写法实查**: startup patch(mtime 02:42 未
触线)第 42 行段仍是 `add x14,x20,x22 / sub x14,x14,x23 /
str x15,[x14,#0x898]` — 062x 登记的"循环或已完成而
INVALID0 自 fault"头号嫌疑, 066x/075x 两度报回, r50 输入
修复仍未物理化 INVALID0。**若 r50 传输恢复而 INVALID0 仍
零, 该嫌疑升格为对 Codex 的明示报回**(比 header/L1 更该
先修 — 它是当前停点判定的关键负读数)。

## 4. 盘态

LOG 仍 M(07:54 值, R49 段未 commit); record 欠账 18 不变
(r50 未完); probe 三闸零漂移; 守护龄 ~4.52d(<5.2 闸),
心跳 08:41 下一班; 保险丝 next 12:43。GO 未回。

**一处旧判自我修正**: 074x 曾以"同 session baseline OKAY"
排除线缆/宿主因素 — 该推理对单次成立, 但"boot3 后 baseline
成、probe boot 后败"在两代重复出现的模式, 同样兼容**宿主
macOS USB 栈在 probe 重枚举后的绑定失败**(假设 2), 未必
是镜像(假设 1)。r50 传输若恢复, 只能证明输入改动与之相关,
两假设的最终分离仍需判别实验或换物理口对照。权重重估登记,
r50 解码时一并裁决。

## 5. 下轮盯点

r50 final 落地 → 解码三件事: ①0x970/0x978 数值是否回归
(判 loop-state 修复), ②0x980-0x990 HDR 链读数(判传输
恢复 + 执行是否过失效循环), ③INVALID0 终判。传输若再挂,
镜像嫌疑之外的假设 2(macOS USB 栈)权重重估。

verify: pgrep 容器构建命令行全文实拍(含 --machine T7001
新参数亲见); patch mtime 08:22/08:23 实拍; grep str.x20
写点三点/六点全列; python3 重算三哨兵新立即数字面;
build 脚本 apply 行序 grep 实读(410/416); startup patch
INVALID0 段实读 + mtime 02:42 实拍; mapping L1DONE00 名
grep 实取; LOG=M+mtimes 实查; fastboot devices — 全部
本轮执行。
作者: lingion <lingion@hrbeu.edu.cn>
