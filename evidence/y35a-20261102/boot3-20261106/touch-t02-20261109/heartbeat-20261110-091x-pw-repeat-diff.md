# 心跳 20261110-091x: Codex 现场连动 — r50b-pointer-window 第二探针全链 OKAY, 读数集与 r50b-min **完全相同**(19 哨兵+slot49 同位同值), 差分可重复性成立; 目录当场被改名(去 -200000 后缀)系整理动作, 日志内旧路径为改名前写入; record 双欠(r50b+pw)

时刻 09:1x(09:14:28-09:17 实链)。HEAD=928cff4(本线顶)。
设备 efff9d92 fastboot 空闲。零设备指令。

## 1. pointer-window 实验事实(当轮全量实查, 守 090x 纪律)

09:10-09:11 Codex 实跑 `phase-r50b-pointer-window`(新探针
目录 `readback-probe-20261110-r50b-pointer-window`, entry.S/
elf/img/readback.json 齐, 无核/boot3 新件 = 复用 r50b 输入
f3223ebb 系实拍 hdr 前缀 ✓)。全链: baseline OKAY →
pre-pointer getvar 三连(product lk2nd-msm8916/serialno
efff9d92)→ probe Sending/Booting OKAY → stage "Staged."
OKAY → get_staged OKAY **69,632 字节完整**。无传输失败。

**解码对比(双件同法)**:
- r50b-min final(`f2b62e61…`)与 pw final(`34cc5237…`)
  raw 不同(CNTVCT 新鲜度见证, 同 094x 口径), 但
  **非零槽集逐位相同**: ARMENTRY/ARGSLOAD/PREARGS0..
  BAFLAG00/KVACALC0/x22/x23/TPIDR000/EXC 三连/INT 三连/
  slot49=0xfffffff00702f7fa, 19 项; STACKS00/LINKADDR/
  INVPREF0/INVONE00/PTPRE000..PTSHIFT0 同样归零;
  early_fault 双零。

判读: **两枚不同探针独立跑, 读数集复现** — 我 090x 登记的
混淆因子①(min 覆盖截短)对该差分解释力下降(若 pw 覆盖
与 min 不同而读数仍同, 归零更像真实现); 混淆因子②(patch
几何重组致槽↔符号映射变化)**未排除, 仍是主解释候选** —
pw 实验名本身(pointer window)暗示 Codex 正在查写点窗口/
指针类问题, 与其 record 收口前本线不作边界结论。

## 2. 现场连动目击(记过程)

09:14 首见目录名 `...-200000`(实验时戳命名), 09:16 读取报
no such file, 09:17 find 实拍目录已改名 `...20261110`(去
后缀)——Codex 实时整理产物命名; `final-get-staged-pw.log`
内路径仍写旧名(-200000), 系改名前写入。后人核对以现名+
日志内容为准, 勿因路径不一致疑证据链断裂。

## 3. 治理与盘态

- record 欠账: r50b carrier 与 pointer-window 两笔均未收
  (实查 MISS×2), 总数较 090x 的 19 或增至 20(等 Codex
  整理落定下轮重数, 不猜);
- Codex 活跃(09:10 实验+09:12-15 改名), 距 r50b 已连做
  两实验, 传输病未复发; LOG/CURRENT 仍 M; 13 件 patch
  untracked; probe 三闸零收口; 守护龄 ~4.54d; GO 未回。

## 4. 下轮盯点

①pw/r50b 双 record 补收(含 pointer-window 假设声明);
②目录整理落定后 record 欠账重数; ③若 Codex 换探针覆盖
重跑, 差分三判点(STACKS00 系/PT 系/0x980 HDR 系)按新
映射表读。

verify: pointer-window 14 件目录 ls -lat 实拍; 五份日志
全文逐行(pre/probe/stage/get 全 OKAY 亲见, 无新错误码);
双 raw 69632 实测+sha 对比(f2b62e61 vs 34cc5237); python3
双件逐槽对比 19 非零项全同; hdr 前缀 f3223ebb 复用 r50b
核实拍; 目录改名时间链(09:14 见旧名/09:17 见新名)两轮
命令实拍; pgrep 无进程+fastboot 在列 — 全部本轮执行。
作者: lingion <lingion@hrbeu.edu.cn>
