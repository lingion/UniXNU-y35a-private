# 心跳 20261109-142x: stock-boot.img "absent" 说法证伪 — 文件在本机且 sha 三处历史记录吻合; 冷读实验输入完备性对账

时刻 14:2x。HEAD=720fe59(fixer 其后无新 commit,工作树 M 件仍活跃)。
设备 efff9d92 存活,本 turn 零设备指令。触发:QUP5-COLD-READ-EXPERIMENT
与 PHASE-R11-BUNDLE 文件声称 "the local inventory does not currently
contain the required stock-boot.img" → 本轮实测**证伪**。

## 1. stock-boot.img 实测存在(新鲜执行)

- 路径: `/Users/lingion_k/unixnu-research/evidence/y35a-20261102/stock-boot.img`
- 大小: 67108864 B(=0x4000000,boot 分区全尺寸)
- sha256(本轮 shasum 实算):
  `92611f876a022fb5af1138f0591f5dafe2b359a226b2f0b28d292211f2fec012`
- 历史记录吻合(本仓 grep 实得): heartbeat-1000 §2 "stock-boot sha
  92611f87…"、heartbeat-0150 "stock-boot=92611f87 件"、
  docs/board/boot3-container-layout.md:336 "stock-boot sha256 92611f87…"
  — 三处前缀一致,文件即当年提取件本体,非替代品。
- 误报机制推测(不定罪): bundle 的 "inventory" 若指 worktree 子目录
  UniXNU-y35a/evidence/y35a-20261102/, 则文件实际在**父仓**
  unixnu-research/evidence/y35a-20261102/ — 两目录同名不同物。

## 2. r11 产物完备性对账(新鲜执行)

- out/y35a/ios12-boot3-phase-r11/boot3.img = 54620160 B,manifest 完整:
  kernel_sha256=619a6ea0…(= kernel-packed.macho 实算吻合)、
  boot_image_sha256=a98c0b26…、RAMdisk 54c07a60…(与历代一致)、
  TrustCache d0e4ee05…、gate 几何/scratch 齐全。
- 即: **实验所需 boot3.img 已在场**, "无法重新打包"只影响从零复跑
  package_native.py 的再生路径(--stock-boot 参数有现成输入, §1),
  不阻塞任何烧写排期。

## 3. 冷读实验件(QUP5-COLD-READ-EXPERIMENT)对账 — 与本线 131x/134x 裁决的关系

实验件 source-pinned 表逐项核对(pinctrl-msm8916.c + 厂商 DTB,均本仓
实测):
- GPIO18/19 ctl 窗 = 0x01012000/0x01013000(stride 0x1000)✓ 与 123x/134x 一致;
- "TLMM mux for blsp_i2c5 = function slot 2 on GPIO18/19" ✓ 与 134x
  driver funcs 表逐值吻合(pin18/19 f2=blsp_i2c5);
- step 5 "drive strength 2 + bias disable" ✓ = 厂商 pmx_i2c_5 active
  态原值(drive-strength=<0x02>, bias-disable, dtb10.dts:774-803 区段
  前轮实测),io 字 = 0x000(134x §2.3);
- QUP5 SPI 99(GIC 原生号)✓ 与 INTID 131 并存记录一致;
- **缺口提示(登记不代做)**: 实验件序列未含 attn pin13/GPIO12 reset
  配置(§5 只动 18/19), 与 H1"target reset state unresolved"自评一致 —
  首轮纯 I2C 可达性测试设计成立, 若 H1 失败则 134x 的 attn/reset io
  值(0x1C3/0x001)即第二发装药;
- 页 0 读回后判读须按 S3202 家族字段(0x0e 函数表起点、Product ID 仅
  断言家族), 同 plan 风险表。

## 4. 盘态与纪律

fixer M 件(build-xnu-4903-kernel.py/capture_format.py/probe_rmi.py/
readback_native.py/tests)+ 新协调件(BANACH/CAPTURE-TRANSPORT-AUDIT/
LONG-RUN-STATE/PHASE-R11-*/QUP5-* 未跟踪)零接触; 测试计数以 LOG 尾
84/84 为其自报, 本会话未代跑(其文件在途)。本会话唯一写入 = 本件。
GO(逐实验授权)仍未回, 本件不启动任何烧写。

verify: 本轮新鲜执行 — shasum -a 256 stock-boot.img 全值 + 大小 stat;
grep 三处历史 sha 记录; manifest.json python 解析 + kernel-packed.macho
实算比对; ls -la out/y35a/ios12-boot3-phase-r11; grep/sed 对账引用
(pinctrl-msm8916.c 前轮行号 + dtb10.dts 前轮缓存); git log/status/
fastboot devices 实跑。
作者: lingion <lingion@hrbeu.edu.cn>
