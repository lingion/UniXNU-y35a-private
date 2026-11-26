# 冷读件(T0.2 第二路径)设计事实与未知数立案 — 20261109-120x

时刻 2026-11-09 12:0x。HEAD=c19ed87(并行会话)。设备 lk2nd fastboot 存活,
本 turn 零设备指令。目的:上轮 1130 判读(fe6479e)把下一实验钉为
"pinctrl 直写 + clock enable 冷读";本文件把该件开工所需的全部声明侧
事实钉死,并登记仅剩的两个寄存器侧未知数。落地写件等
scripts/y35a/rmi_probe.cpp 从并行 WIP 释放(纪律:两写者不碰同文件)。

## 1. 事实源已入树免疫容器清空

/tmp/qcdtdts(容器 unixnu-y35a-native-20261103)本轮实测仍在,但 0820
轮清空事故证明其不可靠 → dtb10.dts 全文已 docker cp 入证据树:
evidence/.../touch-t02-20261109/dtb10-cache/dtb10.dts
(249371 B, sha256 前缀 4b2a7fda53ab9b4a —— 本轮 shasum 实测)。
以下行号全部指该文件,后续判读只准用树内缓存。

## 2. 冷读件声明侧事实(全部本轮从缓存实测行号提取)

| 项 | 值 | 源(dtb10-cache/dtb10.dts) |
| --- | --- | --- |
| I2C5 信号脚 | `qcom,pins = <0x3f 0x13 0x3f 0x12>` → TLMM pin19/pin18;`qcom,pin-func = <0x02>` | :1236-1239(pmx_i2c_5) |
| active/sleep state | drive-strength 0x02,bias-disable;phandle e1/e2 | :1242-1257 |
| 触摸中断脚 | pin13:drive-strength 0x10 + bias-pull-up(ts_int_active, phandle e4) | :2145-2152 |
| 复位脚 | pin12:drive-strength 0x10 + bias-pull-up(ts_reset_active, phandle e5) | :2171-2178 |
| SE reg | 0x78b9000 len 0x600;BAM 0x7884000(不用) | :6839 |
| 中断 | `interrupts = <0x00 0x63 0x00 …>` → SPI 99(0x63)=INTID 131 | :6841 |
| rmi 从机中断 cells | `interrupts = <0x0d 0x00>`,interrupt-parent 0x48(TLMM) → pin 13, type 0 | :6861-6862 |
| 时钟源 | `clocks = <0x42 …>`,phandle 0x42 = xo 节点(clock-names "xo\0xo_a",#clock-cells 1) → core_clk 从 XO 派生 | :6840,:5171-5174 |
| 分频 | clk-freq-in 0x124f800=19.2 MHz,out 0x61a80=400 kHz;fs-clk-div 0x16,high-time 0x17 | :6843-6848 |

## 3. 与失败定位的合流(设计口径)

1130 判读钉死:交棒 SE_STATE=0x1c 不含 VALID(bit2),`reset()`
首步 pollState(idle) 超时(err=0x1000004|0x01000000),事务未上总线;
`clkctl_after=0` 自洽(RUN 迁移才写,I2cCore.h:223)不构成时钟门定罪。
冷读件序列(I2cCore 既有 API,不改核心):
1. TLMM 直写 pin18/19 → func 2 + drive 2 + bias-disable(§2 数值);
   pin12 保持输入上拉复位语义,pin13 输入上拉(§2)。
2. SE 窗口: SW_RESET=1 → IO_MODE 配 I2C → OPERATIONAL clear →
   **不经 xfer 直接落 CLK_CTL**(fs_div 按 T0.1 线契约=0x16,hs=3)→
   pollState(MASTER_GEN)。
3. MASTER_GEN 仍不来 → 才轮到时钟门假说,冷读件须在同一次 boot 内
   先 dump 后写:GCC cfg 观测(§4 未知②)+ SW_RESET 前后 STATE 演变
   进 report 新字段(扩 Report 结构须过 CAPTURE-TRANSPORT-AUDIT 的
   0x1000 尺寸 static_assert,rmi_probe.cpp HEAD 注释)。
4. 身份事务与 f01 读复用 HEAD 探针第 3 节路径,零新逻辑。

## 4. 寄存器侧未知数(立案,禁猜)

① **TLMM v1 per-pin 配置字布局**:HEAD 探针按 `0x1000000+pin*4` 假设
(gpio[200] dump);交棒实测 word0=0x1、word2=0xe2 而其余零 —— 与
stride-4 连续布局矛盾(122 引脚应有密集非零区),该 dump 的解释力
存疑。权威源=Linux pinctrl-msm 8916 驱动或 lk2nd msm_pinmux;本仓
无 lk2nd 源码(refer/ 仅 Apple 件,实测),需镜像克隆或在冷读件里
先做 0x0-0x300000 稀疏采样定位真实 stride。T0.3 的 gpio→INTID 换算
同受此未知数牵连。

② **GCC QUP5 core 时钟 cfg 可达性**:0x01800000 512 词直读全零(两
样本复现)。可能:基址不对(APQ8016 GCC 寄存器分区)、EL1 非安全访问
被 RBCPR 视角挡、或读路径问题(TLMM 同法直读有值,排除映射本身)。
冷读件必须把"GCC 真实基址/cfg 偏移"作为 dump 目标而非写目标——
时钟门未定罪前不写 GCC。

## 5. 收口条件

冷读件开工 = ①②有权威值(文档或实测 dump 二选一)→ rmi_probe.cpp
释放后落件 → probe_rmi.py 重建(其当前 WIP 归并行会话,本会话等其
落地后另件另 sha)→ mode/layout 双闸 → RAM boot 请批(新镜像新闸)。

verify: docker exec ls /tmp/qcdtdts 实测件在;docker cp + wc -c 249371
+ shasum 前缀 4b2a7fda53ab9b4a;grep/sed 提取 §2 全部行号本轮新鲜执行;
git show HEAD:scripts/y35a/rmi_probe.cpp 序列核对(未读工作树 WIP 件);
git status 实测 rmi_probe.cpp=干净、probe_rmi.py/builder/tests/LOG/CURRENT
=并行 M(未碰)。
作者: lingion <lingion@hrbeu.edu.cn>
