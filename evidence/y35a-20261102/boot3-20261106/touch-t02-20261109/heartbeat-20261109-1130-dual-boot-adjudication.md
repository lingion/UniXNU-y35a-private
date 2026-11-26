# 心跳 20261109-1130: 双 informative boot 判读 — 交棒态失败可复现×2,读回 r8 世代见证成立,attn 证据质量降级

时刻 11:1x–11:4x(接棒两轮 API 中断后复测完成,本文件所有数字为复测轮新鲜实测)。
HEAD 基线=bc64e6f(并行会话)。设备 lk2nd fastboot 槽存活(efff9d92),
boot 前后 pgrep fastboot 均空。本会话零分区写、零 userdata、未碰并行在途文件。
序列与停止条件按 14c64e3 立案执行(用户 GO「都跑」)。

## 1. 捕获(全部 69632 B = 0x11000, staging 布局)

| 文件 | sha16 | 来源 |
| --- | --- | --- |
| heartbeat-20261109-1130-baseline.raw | fcff22652013ee5d | 开跑前捕获。实测与并行会话 10:5x 件 t02-touch-capture.raw 逐字节相同 → 它不是"上代残迹",本身就是一次真实触摸探针捕获;本会话将其计为第一次独立 boot 样本 |
| heartbeat-20261109-1130-touch-probe.raw | 4e640c54b3b6fe1f | `fastboot boot` 容器件 295241ce…(docker cp 后 sha 实测相符),~32 s lk2nd 看门狗回 fastboot |
| heartbeat-20261109-1130-readback-probe.raw | fb71fd38c6050a72 | `fastboot boot` r8 世代件 2aaf092c…(本地件 sha 实测相符),同样 ~32 s 回收 |

## 2. 触摸线判读(两次独立 boot, 硬件读数逐位复现)

report@body 0x10000: magic=Y35ARD01。两样本 report 区差异字节**仅**
0x10008–0x1000c(t_boot)与 0x10050/0x10058/0x10060(三个事务时间戳);
status/err/se_dump[12]/clkctl_after/err2/page0[8]/f01[21]/attn[4]/
gpio[200]/gcc[512] 全部逐字节相同(python 区间实测)。t_boot 不同
(0x213e698243 vs 0x2d56b702b)= 两次真实执行,非残留。

钉死事实(两轮一致):
- `status=0x80000008`(S_DONE|S_PAGE0_TIMEOUT), `err=0x01000004`
  = E_TIMEOUT_STATE | xfer-failed 位(I2cCore.h:60-62 枚举, :94-98
  pollState 超时路径)。失败定位: reset()(I2cCore.h:142-152)第一步
  pollState(0) 等 SE_STATE 的 VALID 位 — 交棒 SE_STATE=0x1c 不含 bit0,
  20000 次轮询不立 → 身份事务从未上总线。page0/f01=预清零、err2=0
  为短路位置旁证。
- `clkctl_after=0`: setClock 的 CLK_CTL 按设计只在 RUN 迁移时落写
  (I2cCore.h:223), xfer 从未进入 → 0 属自洽;**不能**据此单独定罪时钟门。
- TLMM 直读: 触摸四脚 pin12/13/18/19 控制字全 0 → LK 交棒态 I2C5
  pinctrl 未配置(与 record.md 判词一致, 本轮由孤证升级为双证复现)。
- SE 交棒原值(供 fixer/后续件参照): CONFIG=0, STATE=0x1c, IO_MODE=0xa5,
  SW_RESET=0, OPERATIONAL=0xc0, ERROR_FLAGS=0, ERROR_FLAGS_EN=0x3c,
  MX_*=0, CLK_CTL=0, I2C_STATUS=0x0c000000。
- GCC@0x01800000 512 词全零: 同法直读 TLMM 有值(词 0=0x1, 词 2=0xe2)
  而 GCC 无值 — 原始事实照录, 解释待定, 禁推断。
- 全程耗时 span=t_end−t_boot: baseline 1043031 ticks(54.3 ms)、本会话件
  1030785 ticks(53.7 ms)@cntfrq 19.2 MHz — 两次独立 boot 同量级复现,
  与失败路径自洽(≈2×20000 轮询上限在 delay 节流下的大致开销)。

**裁决(计划 §T0 预留二选一定格)**: "纯交棒读可用"假设被两次独立实测
否定, 失败机制已定位到 SE 状态机 VALID 不立(先于时钟/pinmux 之争)。
下一实验 = plan §T0 第二路径: pinctrl 直写 + clock enable 的冷读
(新件新闸, 需重建镜像并再次请批 boot)。

### attn 证据质量降级(本轮新发现)
attn[0..3] 与 gpio[13] 读同一地址 0x01000000+13*4(TLMM pin 配置字,
rmi_probe.cpp:184), 四次采样恒等且全零(实测相等) → 探针记录的是
pin 配置寄存器,**不是**输入电平。attn 全零不构成"线静默"证据。
input-status 寄存器偏移 = T0.3 待钉项; record.md 判词 2 中
"attn 4 采样全 0"一句按此口径更正。

## 3. 读回线判读(r8 世代 = 见证捕获, 非验收)

- records 区 CNTVCT@0x10: 两触摸件同为 0x453784c, 读回件为
  **0x1c6bfa20**(4 字节刷新, 其余不变) → 读回探针确在设备执行,
  自带新鲜性见证; 与 r7 判词 3 的 staging 模型自洽。
- 读回件 report 区(0x10000..0x10bc4)与触摸件逐字节相同(实测 True)
  → 探针只写 pram 内记录区, 不触 0x859f0000 报告区 — 布局预期证实。
- records 区两触摸样本间零差异 → stage 低区跨 boot 保持, 只被写者更新。
- 按 14c64e3 立案边界: 本件是 transport/witness 结果, 不构成任何 XNU
  启动边界结论。layout 闸 13 overlaps 前置未修(parallel bc64e6f 实测
  仍红), 读回 informative-boot 线维持 blocked, 修复归 fixer 会话,
  本会话不碰其文件。

## 4. 设备收尾

三次捕获后 `fastboot devices` 在场; 探针 wfe 挂停由 lk2nd 看门狗回收
(实测 ~32 s/次); 零 reset/flash 路径执行; userdata/分区零接触。

verify: python3 -I struct 解析三 raw + 逐区间 diff + attn/gpio 相等断言
(§1-§3 全部数字为本轮新鲜实测, 判据 A-I); shasum -a 256 三 raw +
docker cp 件与立案 sha 逐字节相等; fastboot boot×2(Sending/Booting OKAY)
+ oem y35a panic×3 + get_staged×3(69632 B); pgrep fastboot boot 前后各测
= 空; fastboot devices 终态在场。
作者: lingion <lingion@hrbeu.edu.cn>
