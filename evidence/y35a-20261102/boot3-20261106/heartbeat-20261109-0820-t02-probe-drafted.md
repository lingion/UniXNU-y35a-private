# 心跳 20261109-0820: T0.2 触摸探针离线起草 — rmi_probe.cpp 编译全绿(设备执行未开始)

时刻 08:2x。HEAD=baf4604(并行会话)。设备 efff9d92 fastboot 在槽。
本轮判定:baf4604 §8 重判已把读回模型收敛为 staging 写 + CNTVCT
新鲜见证 + warm-reset 保持,与 c370b7b 的验收口径注一致;读回机制
已可依赖 → 启动 T0.2 离线起草(纯新文件,零碰并行在途件)。

## 1. 事实侦察(全部本轮实测)

- 库存 DTB 的容器 /tmp/qcdtdts 已不在,但同仓证据
  /Users/lingion_k/unixnu-research/evidence/y35a-20261102/dtb10-stock.dts
  在盘,即 facts 引用的同一文件。手搓 FDT 走查(stock-boot.img QCDT
  entry 10, 206/8/23)解析出 922 节点,与 DTS 文本互证:
  - 总线节点 //soc/i2c@78b9000: clocks=<0x42 0x8caa5b4f 0x42 0xacae5604>
    phandle 0x42 = gcc@1800000(reg 0x1800000);pinctrl-0/1=<0xe1>/<0xe2>
    = pmx_i2c_5 active/sleep,qcom,pins=<0x3f 0x13 0x3f 0x12> →
    **SDA/SCL = TLMM 18/19 实锤**(facts 此前只钉了 12/13);
  - rmi_i2c@20 pinctrl-0=<0xe4 0xe5> = ts_int/reset active,
    attn_polarity=0,reset=GPIO12、irq=GPIO13;
  - GCC 时钟 cell 值是 Linux 时钟名 hash,不是寄存器索引 →
    探针禁做 GDSCR 换算,只 dump 原始窗口(禁猜铁律)。
- **LK 从未配置触摸总线时钟**:容器内
  /work/lk2nd-y35a-codex/platform/msm8916/acpuclock.c:485-515,
  clock_config_blsp_i2c 对 QUP∉{2,4} 直接 ASSERT。BLSP1/QUP5 不在
  LK 清单内 → 时钟大概率门控,NACK/timeout 是合法判据不是探针 bug。
  这正是 T0.2 要取证的问题本身。
- lk2nd hw/gpio/tlmm.c 的控制字布局属 lk2nd supplier 层,不假设等于
  8916 TRM → 探针 raw dump TLMM 0x0..0x31c 全 bank 留作 T0.3 离线解。

## 2. 交付

- scripts/y35a/rmi_probe.cpp(新):只读路径 — SE 窗口 as-found dump
  (12 寄存器,不碰 FIFO),TLMM 200 词 + GCC 512 词 raw dump,attn 四
  采样,setClock(19.2MHz/400kHz)+reset()+对 0x20 一发 page0 读(ACK
  才补一发 0x0e..0x24 F01 候补窗,raw 记录不断言),报告写
  STAGE_BASE=0x859e0000(magic Y35ARD01 小端,t_boot=CNTVCT 新鲜见证,
  cntfrq 记录),sizeof(Report)=0xbc4 远小于窗口,逐行 dc civac 刷洗
  后 wfe。delay()=33 tick(CNTVCT 频率不假设:msm8916 arch timer 常见
  19.2MHz 则 ~1.7us、32768Hz 则 ~1ms;探针记录 cntfrq 与全部 t_*
  时间戳,真实节奏离线判定),有界轮询最坏上界由 dump 出的 cntfrq
  算出,不是猜测。
- scripts/y35a/probe_rmi.py(新):容器内构建配方(entry shim 复刻
  emmc_probe 形态:栈 0x859d0000,MMU-off 闸,daif 全屏蔽),manifest
  含报告字段偏移表 + 读回口径。
- 计划 T0.2 落地注:代码离线绿,设备执行(迭代 #0 RAM boot 烧写)
  等请批窗口。

## 3. 验证(本轮真实执行)

- 容器 clang++ --target=aarch64-none-elf -O2 -nostdlib -Wall -Werror:
  第一轮 3 错(rawRead 整型窄化、qup:: 命名空间、dc 操作数宽度),全
  修;第二轮 BUILD_OK,probe.bin 3856B,llvm-nm -u 未定义符号 0。
- setClock 调用为修复后追加,追加后重跑 draft2 全绿(nm/objdump/
  sha256 输出在案:image a831ff64…,重打 draft2=074542f5…)。
- FDT 走查脚本在 scratchpad,输出与 dtb10-stock.dts 文本互证一致。

本轮:未 run fastboot,未 boot,未写分区,未 push,未碰并行在途文件
(package_native.py/boot_layout.py/build-xnu-4903-kernel.py/patch 均 M
态,零触碰;docker cp 只进新文件 rmi_probe.cpp/probe_rmi.py 与
stock-boot.img 副本 /work/evidence-stock-boot.img)。

## 4. 追记(09:2x,提交 1ecaf0a 后盘面新实证,禁静默)

本文件提交后,共享分支上落定 0cded8a(心跳 0830 双缺陷定罪)与
docs/coordination/claude-codex-sync 台账。与本探针直接相关:

- 缺陷 1 定罪 STAGE_BASE=0x859e0000 与 DT pram(panic log)窗口
  别名(make_adt.py:51)。rmi_probe 的报告基址正是 0x859e0000。
  对独立探针(standalone boot,无 XNU 介入)这不毁当轮证据,但会
  再覆写 pram 残迹(上一世代证据已落盘 panic.raw,毁的是重复取证
  能力),且 fixer(local_c3ce3e96)正在迁移 staging 约定 ——
  探针基址必须跟约定走,单独择址=无地图猜测,禁。
- 决定:rmi_probe 基址对齐等 fixer 迁移落地(改一处 constexpr 即可
  重打);设备执行并入台账 Next-Work 闸:等 phase 工件溯源修复 +
  staging 定案 + 用户逐项请批,三线都不绿不烧。
- 探针源码与容器构建件已逐字节判等(rmi_probe.cpp sha 826434d6 双侧
  一致;重打镜像 074542f5 与 final draft 同 hash,构建可复现)。

作者: lingion <lingion@hrbeu.edu.cn>
