# 心跳 20261109-131x: 叙事对账(r12 不存在 + module-id 引脚更正)+ 库存 DTB pinctrl 真值表入档

时刻 13:1x。HEAD=e61dff2(并行 fixer 活跃,field_bytes 落账)。设备 efff9d92
fastboot 存活,本 turn 零设备指令。probe_rmi.py/readback_native.py 等仍
并行 M — 本文件为唯一写入物。

## 1. 叙事对账(禁静默吞,立案更正)

前两轮本会话叙述中出现两处**无盘面背书**的说法,本轮全仓 grep 裁决:

1. "2026-11-09-touch-r12-cold-boot-design.md"(冷读件 r12 计划):
   docs/superpowers/plans/ 只有 y35a-touch-driver 与 first-boot 两件;
   全仓 grep r12 零命中。**该文件不存在,引用即编造** — 实际代次命名是
   r9(readback)/phase-r11(kernel 插桩)。未落任何 commit,无需清盘,
   但立案留痕:后续汇报禁再使用 "r12" 指代冷读件。
2. "module-id 引脚 21/22"及"库存 DTB 无 8916-GCC 时钟表"：本轮新鲜
   sed dtb10.dts 推翻前半、证实后半:
   - `vivo,ts-module-id1/2-gpio = <0x48 0x00 0x00>` / `<0x48 0x03 0x00>`
     (:8484-8485)= **pin 0 与 pin 3**,不是 21/22;
   - pinctrl@1000000 节点(compatible qcom,msm-tlmm-8916, reg
     0x1000000+0x300000)确认存在(:750-752)——"无 TLMM 表"若被如此
     表述也是错的;不存在的只是独立 GCC clock-controller 节点。
   教训同 04:20 "电视"事故:未查盘面即把记忆当事实输出,同型错误第三次。

## 2. phandle 身份解析(冷读件依赖,本轮实测)

- `0x3f` = pinctrl@1000000/gp(qcom,num-pins 0x7a=122,#pin-cells 1)——
  pinctrl 片段里 `<0x3f N>` 即 TLMM GPIO N;
- `0x48` = 同控制器子节点 msm_gpio(gpio-controller + interrupt-controller,
  #gpio-cells 2)——`<0x48 N flag>` 即 GPIO N。两 phandle 同一控制器,
  DTB 中无任何独立第二 GPIO 控制器。

## 3. 触摸相关 pinctrl 真值表(库存 DTB 权威,冷读件 §5-3 直写依据)

| 组 | 引脚 | func | active | suspend | 行号 |
| --- | --- | --- | --- | --- | --- |
| pmx_i2c_5 | SCL=19, SDA=18 | 0x02 (QUP_5 I2C) | drive 0x02, bias-disable | 同 active(数值相同) | :1236-1256 |
| pmx_ts_int | 13 (attn) | 0x00 (GPIO) | drive 0x10, **bias-pull-up** | drive 0x02, pull-down | :2142-2166 |
| pmx_ts_reset | 12 | 0x00 (GPIO) | drive 0x10, **bias-pull-up** | drive 0x02, pull-down | :2168-2192 |
| pmx_ts_release | 13+12 | — | drive 0x02, pull-down(释放态两脚同拉低偏置) | — | :2194-2203 |
| pmx_ts_id | 0 + 3 | 0x00 | drive 0x02, pull-up | pull-down | :2520-2547 |

对 120x 件"声明侧值(func2/drive2/bias-disable)"的数值**确认无误**
(SCL/SDA);并新增此前未知的三事实:attn/reset active 态是 **pull-up**
(低有效中断线 + 低有效复位的自洽偏置),i2c sleep 与 active 电气配置
相同(总线休眠不改偏置),ts_release 组存在。

## 4. T0.3 部分答案(中断路由)

pinctrl@1000000 `interrupts = <0x00 0xd0 0x00>`(:752):0xd0=**SPI 序号
208**,按本仓既有换算约定(qup_irq SPI 99 = INTID 131,即 +32)得
**INTID 240** — TLMM 聚合中断上送号钉死。plan:27 行"gpio13 INTID
93/131 换算未定"收窄为:13 号脚的 per-pin mux/enable 寄存器(TLMM_INTC_*)
编程仍是 T0.3 剩余项,但聚合目标 INTID 240 已入档;kernel 接 attn 中断 =
armcpu_spi_attach(240) + TLMM 内 per-pin enable,不再需要猜独立 INTID。
注:8916 TLMM 硬件为 pigtail 分组(16 脚一组共享一条 SPI),本 DT 只给
一条 208 — 分组归属细节(13 号脚属哪条 pigtail)标为待核,以 T0 实测
dump 为准,禁在此强断言。

## 5. 盘面重建(心跳规则②,新鲜执行)

- git log:HEAD e61dff2(13:0x fixer 提交);448de3a=本会话 123x 裁决件;
- git status:probe_rmi.py/readback_native.py/build-xnu-4903-kernel.py/
  tests M(并行活跃),协调目录多件 ?? — 全部不碰;
- fastboot devices:efff9d92 在槽;
- BANACH-REPORT(untracked 并行件,只读引用):判定 Y35AXNU2 戳只证
  shim→XNU 交棒不证 panic-header,phase-r11+minimal-boundary 实验需
  新的逐实验用户 GO — 与 CURRENT.md Next Work 0 一致;
- 下一步设备线动作归 owner GO,本会话不排烧写。

verify: 本轮新鲜执行 — grep -rniE "\br12\b" docs/ scripts/ touch-t02
证据件全零命中; sed dtb10.dts :748-778(pinctrl/phandle)/:1230-1300
(i2c5)/:2142-2205(ts 组)/:2520-2547(ts_id)/:8470-8500(touchscreencfg)
全部重读并与本文数值逐字对位; git log/status 实跑; fastboot devices
实跑。无构建/测试轮(本 turn 纯读+证据件)。
作者: lingion <lingion@hrbeu.edu.cn>
