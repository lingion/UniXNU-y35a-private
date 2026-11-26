# 心跳 20261109-123x: 未知数① TLMM 布局由 lk2nd 权威源码裁决 — 交棒 dump 矛盾消解 + attn 读数证伪

时刻 12:3x。HEAD=a58d8f6(fixer 刚提交 --transport 模式)。设备 lk2nd fastboot
存活,本 turn 零设备指令。probe_rmi.py/builder 仍 M(并行)。本会话不写
rmi_probe.cpp/probe_rmi.py — T02-PROBE-AUDIT-20261109.md 明文其归属 fixer
workstream("This audit is read-only... remain owned by")。本文件是喂给
冷读件的裁决证据,落我自己的证据目录。

## 1. 权威源(容器内 lk2nd,本轮 sed/grep 实测)

/work/lk2nd-y35a-codex/platform/msm8916/include/platform/iomap.h:97-103:

    #define TLMM_BASE_ADDR              0x1000000
    #define GPIO_CONFIG_ADDR(x)         (TLMM_BASE_ADDR + (x)*0x1000)
    #define GPIO_IN_OUT_ADDR(x)         (TLMM_BASE_ADDR + 0x00000004 + (x)*0x1000)
    #define GPIO_OUT_SET_ADDR(x)        (TLMM_BASE_ADDR + 0x200040 + (x/32)*0x04)
    #define GPIO_OUT_CLR_ADDR(x)        (TLMM_BASE_ADDR + 0x200020 + (x/32)*0x04)
    #define GPIO_OUT_OE_SET_ADDR(x)     (TLMM_BASE_ADDR + 0x2000C0 + (x/32)*0x04)

lk2nd/hw/gpio/tlmm.c:20-30(位布局):

    pull bits0-1(0=none,1=down,2=keeper,3=up) | func<<2 | drive_strength<<6
    | OE<<9 | hihys<<10;  IN=BIT(0)/OUT=BIT(1) 在独立的 IN_OUT 寄存器。

## 2. 后果一:HEAD 探针交棒 dump 的"矛盾"消解(不是异常,是 stride 错)

rmi_probe.cpp 按 `0x1000000+pin*4` 采 gpio[200](0x0..0x31c)。真实 stride
0x1000 → 那 200 个词全部落在 **pin0 自己的槽**(config word + 其后 0xC 内
零散)。交棒读数逐项对位:
- word0 = 0x1 = pin0 GPIO_CONFIG(func0)位0 置位,复位/输入态自洽 ✓;
- word1 (offset 0x4) = pin0 GPIO_IN_OUT,实测 0 = pin0 低电平,自洽 ✓;
- word2 (offset 0x8) = 0xe2 — per-pin 槽内 offset 8 在 lk2nd 无定义
  (Linux pinctrl-msm 每引脚组含多词,pin status 候选, 8916 具体待核),
  **禁强解,记为待核实测项**;
- 其余 197 词零 = pin0 槽内其余区域,与 stride 0x1000 自洽 ✓。
结论:此前"与 stride-4 矛盾"的疑团撤销,T02-PROBE-AUDIT 前所有 attn/gpio
证据的解读要按此作废/重述。

## 3. 后果二:attn 采样证伪升级(fe6479e 判读的再修正)

HEAD attn[4] 读 0x1000034 = pin0 槽内地址,**从未采样过 pin13**。
"attn 证据降级为配置字"仍乐观——它是错的引脚。正确采样:
- pin13 电平 = *(0x1000000 + 13*0x1000 + 4) & 1 → 0x1000d004;
- pin12(复位脚)config = 0x1000c000,IN_OUT = 0x1000c004;
- pin18/19(SDA/SCL)config = 0x10012000 / 0x10013000。
冷读件对 pin18/19 直写的配置字值(按 dtb10-cache 声明侧 facts:
func2、drive 2、bias-disable): config = (0<<0 pull-none) | (2<<2) |
(TLMM_DRIVE_STRENGTH 语义按 lk2nd clamp 公式) — 具体数值口径:Linux
msm8916 pinctrl dtsi drive-strength=2mA 在该 SoC 直接写 2(非 lk2nd
helper 换算),落件时以 §1 位域 + dtb10 数值直写,禁混两套 helper。

## 4. 后果三:未知数② 收窄为"QUP5 GCC 门控偏移无表可抄"

- lk2nd msm8916 只定义/只配 QUP2/QUP4 时钟(acpuclock.c:491 ASSERT 实证
  QUP5 从未被 LK 配置 — 与既有交棒态超时定罪链一致);
- 8952 的 QUP5 块(0x601c..)是另一 SoC 内存图,禁搬;
- msm8916 GCC BLSP1 区实测锚点:QUP2 apps_CBCR=+0x3010/QUP4=+0x5020
  (CLK_CTL_BASE 0x1800000)。
裁决路径改实证:冷读件把 gcc dump 窗口从 [0x0,0x800) 扩到含
**0x3000..0x6000**(QUP RCGR 聚集区;HEAD 512 词窗根本没覆盖),一次
boot 拿全区真值,离线以 QUP2/QUP4 已知锚点插桩定位 QUP5 的 CMD/CFG/CBCR
三元组。读全零问题同时复检:若扩窗后 QUP2/QUP4 锚点词非零,则证明
0x1800000 基址与直读通路都对,先前全零只是"窗口没盖到有值的 0x3000+"
—— 该假设可直接用现有 r9 raw 的窗口参数证伪/证实(旧窗 0x800 词=
0..0x7ff,确实没盖到 0x3000)。**未知数②大概率同样消解,剩实测确认。**

## 5. 交接清单(给 fixer 的冷读件,或获批后的本会话)

1. gpio/attn 采样改 stride 0x1000(§3 四地址);
2. gcc dump 窗扩 0x3000..0x6000(§4),保留 0..0x800;
3. pinctrl 直写目标 = pin18/19 config(§3 数值口径),写前读回原值进
   report(交棒态取证),写后再读(写可达性取证);
4. 时钟门:定位 QUP5 CBCR 后 clk enable(置 bit0),再走 SW_RESET →
   MASTER_GEN 轮询;xfer 复用既有路径。
以上 1-4 全在 rmi_probe.cpp/probe_rmi.py 归属件内 — 本会话按纪律只提供
本裁决文件;若 fixer 线未及覆盖,请用户点名归属再动。

verify: 容器 grep/sed 实读 iomap.h:97-103 + tlmm.c:20-30 +
acpuclock.c:485-515(本轮新鲜执行);git log/status 实测 a58d8f6/probe_rmi.py
M;fastboot devices efff9d92;HEAD gpio[200] 窗与 §2 对位推演(纯算,
0x1000000+200*4=0x1000320 < 0x10001000+ 即全部 <pin1 起点)。
作者: lingion <lingion@hrbeu.edu.cn>
