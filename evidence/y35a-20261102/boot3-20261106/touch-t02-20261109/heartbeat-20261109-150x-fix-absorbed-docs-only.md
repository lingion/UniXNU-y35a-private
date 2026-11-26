# 心跳 20261109-150x: "facts:62" 引用裁决 = cpp 注释伪引; 144x 修单已被 UPSTREAM-MAP 逐字认领但代码未落地; 冷读实验双方独立声明需逐实验授权

时刻 15:0x。HEAD=766227c(我 144x)。设备 efff9d92 存活,本 turn 零设备指令。

## 1. 144x 留置的"facts y35a-facts.md:62 待回源重验" — 本轮裁决

facts.md:58-65 实读(:62 在块内): 原文只说 "TLMM controller
pinctrl@1000000 (qcom,msm-tlmm-8916, **reg 0x1000000 len 0x300000,
122 pins**)" + gpio13→INTID 不可推导禁猜 — **facts 从未主张任何
寄存器间 stride**。rmi_probe.cpp:17 注释 "pin bank stride 4, facts
y35a-facts.md:62" 是**伪引**: 把 "len 0x300000 ÷ 122" 的控制器窗口
误读成了逐脚步距, 再嫁名 facts。仓内现无任何源支持 stride-4;
stride=0x1000 有三源(mainline PINGROUP / UPSTREAM-MAP:43 "base + pin
* 0x1000" / 123x lk2nd)。→ 修单落地时 :17 注释应改为引用
UPSTREAM-MAP:43, "facts:62" 引用删除。

## 2. 修单吸收状态(三分量)

- **文档层: 已吸收** — QUP5-UPSTREAM-MAP:67 逐字列出我 144x 三缺陷
  (stride-4/attn 0x01000034/GCC 止 0x800)并判 "Those old fields are
  superseded"; :43 独立复证 base+pin*0x1000 与 slot-2 功能号。
- **代码层: 未落地** — git status 显示 rmi_probe.cpp 干净(非 M),
  最后触线 93b7978(我 144x 之前); 本轮 grep 实证 :17/:129/:134/:178/:184
  仍是旧 stride-4/旧 attn/旧 GCC 窗。**"superseded" 目前只是纸面**。
- **计划层: 已成形** — UPSTREAM-MAP "next device probe" 四步
  (pre-snapshot→只配 18/19+QUP5 门控→单次有界页0→post-snapshot 停)
  与我 142x 对账的冷读实验件同构; 其自声明 "requires its own explicit
  user authorization" — 与本线顺序闸口径互证, 无旁路。

## 3. T0.2 v2 实现时的两个检查点(登记给实现方, 两码面)

1. attn 采集改双字读: pin13 io=0x0100D004(输入缓冲现值)与
   intr_status=0x0100D00C(中断 pending 态)语义不同, 4 发采样应读
   io 字; 若要中断证据另读 status。
2. report 预算: Report ≤0x1000 是 static_assert 硬闸(rmi_probe.cpp:136)。
   新采集表 = TLMM 8 脚×{ctl,io,intr_cfg,status}(32 字)+GCC 目标窗
   (0x6000..0x6024 10 字 + 0x45000..0x45008 3 字)≈ 45 字 = 180 B,
   替换旧 gpio[200]+gcc[512](2848 B)后预算宽裕; probe_rmi.py 的
   offset mirror(:234)与 tests 必须同批改, 否则宽解码错位。

## 4. 盘态

fixer M 件(build-xnu-4903-kernel.py/probe_rmi.py/coordination 三件)
零接触; 其 HEAD 后无新 commit(15:0x), cpp 未动说明其注意力在
capture/transport 线。守护 cron 12362354(15:01 刚过一轮)+ 保险丝
5f873c8d(18:43)在位, 未到重排窗口。GO 未回。

verify: 本轮新鲜执行 — sed facts.md:50-75; grep UPSTREAM-MAP
:41/:43/:67/:71 行实读 + :60-110 全文读; git log -1 -- rmi_probe.cpp
(=93b7978); grep rmi_probe.cpp 旧循环行号五处复验; git status 干净判定;
git log/status/fastboot 实跑。
作者: lingion <lingion@hrbeu.edu.cn>
