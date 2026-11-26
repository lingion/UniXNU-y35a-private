# 心跳 20261109-134x: TLMM 中断结构/drive 编码/mux 值由本地内核快照裁决 — 131x pigtail 断言证伪, 123x drive 口径更正; xenoptic_x86 容器已消失立案

时刻 13:4x。HEAD=e434dc9(fixer 活跃)。设备 efff9d92 存活,本 turn 零设备指令。

## 0. 容器失踪事实(证据链完整性)

`docker ps -a` 全列无 xenoptic_x86 — **容器已被删除**(非 stop,列表消失)。
123x 件引用的 /work/lk2nd-y35a-codex/... iomap.h:97-103 与 tlmm.c:20-30
**不可容器内重跑**。本轮改用本地权威快照(见 §1)完成同类裁决,结论与
123x 的 stride-0x1000 部分互相印证。教训:任何"容器内实测"引用必须
同轮把源文件缓存入树,dtb10-cache 模式应推广到 lk2nd/mainline 头文件。

## 1. 权威源(本地,新鲜 grep/sed 实测)

`unixnu-research/upstream-snapshot/linux-7475ea8-msm8916/repo/drivers/
pinctrl/qcom/pinctrl-msm8916.c`(986 行,本仓钉死的 mainline 快照):

- PINGROUP 宏(:288-325):每脚独立窗口 `ctl=0x1000*id, io=0x4+0x1000*id,
  intr_cfg=0x8+0x1000*id, intr_status=0xc+0x1000*id`(与 123x 读的
  lk2nd iomap.h 数值一致);位域: mux_bit=2(bits[4:2]), pull_bit=0
  (bits[1:0]), drv_bit=6(bits[8:6]), intr_status_bit=0, intr_polarity=1,
  intr_detection=2(bits[3:2]), intr_target_bit=5。
- `msm8916_pinctrl` 结构(:944-950)**无 .irq_groups 字段** —
  **msm8916 TLMM 无 16 脚 pigtail 分组**(那是老 SoC/apq8064 形态):
  per-pin cfg/status/enable 寄存器齐全,全部引脚的中断经**单一聚合线**
  上送 = 厂商 DTB pinctrl@1000000 `interrupts=<0 0xd0 0>`(SPI 208,
  按 SPI+32 约定 = **INTID 240**)。attn pin13 收中断 =
  armcpu_spi_attach(240) + pin13 窗内 intr_cfg 编程 + 读 pin13
  intr_status 判源。
- mux 值表(:806-826 PINGROUP 宏 funcs 序 = {gpio,f1..f9} 即 code
  0,1,2,...):
  - pin18: {gpio, blsp_spi5, **blsp_i2c5**, atest_gpsadc1} → i2c5=2 ✓
  - pin19: {gpio, blsp_spi5, **blsp_i2c5**} → i2c5=2 ✓
    (厂商 DTB pmx_i2c_5 qcom,pin-func=0x02 逐值吻合);
  - pin12: {gpio, blsp_spi4, gcc_gp2_clk_b, atest_combodac} → gpio=0 ✓
  - pin13: {gpio, blsp_spi4, gcc_gp3_clk_b, atest_combodac} → gpio=0 ✓
  - pin0/pin3(module-id): func 0=gpio ✓(且 0/3 属 blsp_i2c1 脚位 —
    module-id 脚复用域与 I2C1 总线脚位重叠,纯 gpio 输入无冲突)

## 2. 前件更正(禁静默)

1. **131x §4 注"8916 TLMM 硬件为 pigtail 分组(16 脚一组共享一条 SPI)"
   — 记忆断言,被本地权威源证伪**:无 irq_groups,单一聚合中断线。
   该句作废,以 §1 为准。
2. **123x 引文"Linux msm8916 pinctrl dtsi drive-strength=2mA 直接写 2"
   — 口径修正**:8916 drive 域是 3-bit 码(bits[8:6]),非 mA 直写。
   厂商 DTB 的 drive-strength 值是 **mA 数**(2/4/…/16),写寄存器须
   查码表。0x10=16mA 装进 3-bit 的事实本身就排除"直写"读法(16>7)。
   lk2nd clamp 公式(容器源已不可重跑)与此不矛盾,但"直写 2"表述禁再用。
3. 冷读件直写 io 寄存器数值换算(依 mainline qcom_config_driving_strength
   常规映射 2mA→0,4→1,6→2,8→3,10→4,12→5,14→6,16→7):
   - SCL/SDA io = pull-none(0) | drv2mA(0<<6) = **0x000**;
   - attn/reset active io = pull-up(3) | drv16mA(7<<6) = **0x1C3**;
   - attn/reset sleep io = pull-down(1) | drv2mA(0) = **0x001**;
   - ctl mux 域: attn/reset = 0(func gpio), SCL/SDA = 2<<2 = 0x8。
   码表方向标"待 T0 实测复核"(3-bit 码与 mA 单调对应是惯例,未在本仓
   找到逐值断言源,禁当定论)。

## 3. T0.3 状态收口

plan:27 行的 gpio13→INTID 换算问题:**主干已闭** — 目标线 INTID 240,
per-pin 寄存器路径 §1 全数定样,余下仅"码表方向"一个待测项(§2.3),
并入冷读件 dump 即可顺带闭环,不阻塞排期。

## 4. 盘态(规则②,新鲜实跑)

git log: HEAD e434dc9(fixer feat), 9f49723=本会话 131x, e61dff2(fixer fix);
git status M 件: build-xnu-4903-kernel.py/capture_format.py/probe_rmi.py/
tests — 并行活跃,零接触; fastboot devices: efff9d92; 容器: unixnu-y35a-
native-20261103 Up(构建容器健在), xenoptic_x86 已不存在。
lk2nd v23.1 权威源现成路径: pmos-research/pmaports/main/lk2nd/APKBUILD
(url=lk2nd v23.1, github msm8916-mainline)— 外拉须 owner 明示,未动。

verify: 本轮新鲜执行 — docker ps -a 全列; grep/sed pinctrl-msm8916.c
:288-325(PINGROUP 宏)/:806-826(pin0-3,12-13,18-19 行)/:944-950(soc
data 无 irq_groups)/APKBUILD; grep dtb10.dts interrupts=<0 0xd0(前轮
已对位,引用之); git log/status/fastboot 实跑。无构建/测试轮。
作者: lingion <lingion@hrbeu.edu.cn>
