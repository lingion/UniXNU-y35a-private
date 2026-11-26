# 心跳 20261109-144x: rmi_probe.cpp 两个寄存器 dump 窗覆盖缺陷 — 恰漏触摸四脚与 QUP5 门控(T0.3 目标寄存器不在采集窗内)

时刻 14:4x。HEAD=7566c88(fixer 又发一笔 feat)。设备 efff9d92 存活,本 turn 零设备指令。
probe_rmi.py 在 fixer M 件列表(其配对件 rmi_probe.cpp 未被标记,但
93b7978/7e33199 显示 cpp 属同活跃线)→ **只裁缺陷提修单,不碰文件**。

## 1. 缺陷一:TLMM dump 用 stride 4,采集不到任何目标脚

rmi_probe.cpp:177 `for i<200: rawRead(0x01000000 + i*4)` — 注释(:17)称
"pin bank stride 4, facts y35a-facts.md:62"。本轮权威源复核
(pinctrl-msm8916.c PINGROUP 宏 :288-325 + 冷读件 source-pinned 表
+ 123x lk2nd 读数三方一致): **每脚 ctl 窗 stride = 0x1000**:

- pin12 ctl @ 0x0100C000(reset)、pin13 ctl @ 0x0100D000 + io/status
  @ +0x4/+0xC(attn)、pin18/19 ctl @ 0x01012000/0x01013000(SCL/SDA)。

当前 dump 物理覆盖 0x01000000..0x010001FC — **四脚全部不在窗内**。
:184 的 attn 采样 `rawRead(0x01000000 + 13*4 = 0x01000034)` 读的是
pin0 域某寄存器,**不是 pin13 状态** — 四发 attn 采样值系统性无效。
若 stride 4 来自 lk2nd supplier-level 布局, 两布局皆非此语义; 该
"facts y35a-facts.md:62" 引用须回源重验(疑似又一条未落地断言)。

## 2. 缺陷二:GCC dump 止于 0x800,QUP5 门控全在外面

rmi_probe.cpp:178 `for i<512: rawRead(0x01800000 + i*4)` → 覆盖
0x01800000..0x018007FF。冷读件(QUP5-COLD-READ-EXPERIMENT)source-pinned
表列明目标: QUP5 RCG @ GCC+0x6000、I2C branch +0x6020、reset BCR
+0x6018、BLSP1 AHB branch +0x45004 — **全部超窗**。该 dump 名为
"evidence for T0.3", 实则 T0.3 需要的字一个不采。

## 3. 提修单(给 fixer 线,或 owner 批示后本会话做)

最小改动(两行循环 + 注释更正),保持零写纪律不变:

```
TLMM 目标字: 基址 + 0x1000*p {ctl,io,intr_cfg,intr_status},
p ∈ {0..3, 12, 13, 18, 19}; attn 采样改读 0x0100D00C(intr_status)/
0x0100D004(io) 双字。
GCC 目标窗: 0x01806000..0x01806024 + 0x018045000..0x018045008
(或整窗 0x0..0x45008 采样步长不变地扩 size, 看 report 0x1000 预算)
```

Report 结构 gpio[200] 语义随之改: 前 16 字 = 8 寄存器×2 脚起步,
不足则加 gcc2[] 数组; static_assert(≤0x1000) 是硬闸, 布局改动
须同步 probe_rmi.py 的 offset 镜像(:234 注明 mirror)与 tests。

## 4. 交叉核验

- 本缺陷不影响"SE 窗口转储 + 页0 事务"主干(其用自己的 regmap),
  冷读实验若先行, 主干结论仍可得; 但 **T0.3(中断路由事实)与
  QUP5 门控实证两个采集目标当前为空转** — 修前跑 = 白跑一轮设备迭代。
- 顺序闸不变: GO 未回, 本件不启动任何烧写。

verify: 本轮新鲜执行 — sed rmi_probe.cpp :10-30/:160-200 实读;
grep TLMM/gpio/gcc 全部行号; pinctrl-msm8916.c PINGROUP 宏(134x 件
:288-325 引用复算 0x1000*12/13/18/19); QUP5-COLD-READ-EXPERIMENT.md
source-pinned 代码块实读; git log --oneline -4/status/fastboot 实跑。
作者: lingion <lingion@hrbeu.edu.cn>
