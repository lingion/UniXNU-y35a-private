# 心跳 1020 — 读回线判词不变(r8 未落), T0.2 触摸线双闸首绿待授权; 不 boot

HEAD `54401a0`, 分支 `fix/readback-panic-globals`。全程离线只读, 无 fastboot, 无分区写, 无 userdata。

## 盘点 (fresh)
- fastboot 进程: NONE。fixer `local_c3ce3e96` 仍在跑, 最近两提交 93b7978/54401a0(09:57-10:0x)出自该线; 自认"读回线红仍归 fixer"。无需再投递 endorsed 消息(其提交注记已体现吸收)。
- 我上轮 endorsed 的三点(字段宽优先/entry_trace 显式 absent/缺陷A 不受 r8 闭合)与 fixer 现状一致: 迁移未落地。

## 静态实测 (不信 fixer 注记, 逐件重跑)
1. `unittest discover -s tests` → **OK** (current tree)。
2. readback 候选以 HEAD 生成器重生成: 镜像 sha256 前缀 **2aaf092c 与心跳1000完全相同** ⇒ 93b7978 确实未触读回线, r8 未落。
3. 布局闸 raw 输出: **ok:false, rc=1, 13 failures** (stage 重叠 + 全部 12 records 重叠 pram)。
   - 自我更正: 快速解析时我误报 `overlaps=0`(键名猜错静默默认), raw JSON 复核为 13 failures —— 判词以 raw 为准, 与心跳1000一致。
4. `STAGE_BASE = 0x859e0000` 字面仍在(ast.literal_eval 实测), PANIC_LOG_DEST=0x859f0000(pram 上 0x1000 报告窗, 与 transport-audit 候选同基)。字段宽表/ABSENT 处理: 无。

## T0.2 触摸线新事实 (93b7978, 只动 probe_rmi.py/rmi_probe.cpp)
- 报告基址派生至 0x859f0000(pram 之上), 触摸探针**零写 pram**, static_assert 双锁 + 全址单一真源 ⇒ fixer 日后迁移读回 stage 时重打自动跟随, 无图面漂移。
- fixer verify 行记录其双闸 ok:true + 容器重打 295241ce。触摸线现属"几何已闸, 等设备授权"状态。

## 设备闸判定: 本轮不 boot (三前置, 读回线 #1 仍红; 触摸线授权也未给)
- 读回探针: informative 前提未变 —— stage 别名 EPH 头, 抓回必伪影。阻塞维持。
- 触摸探针: 几何自安全, 但 (a) 本轮用户消息未授权任何 RAM boot; (b) 目标顺序固定为先进 iOS 12.4.1, 触摸适配在后续项; (c) fixer 正操作同一 repo/可能随时上设备验证。故不动。
- 下一 informative boot 的决策点(留用户): ① 等 fixer 落 stage 迁移+字段宽 → 读回探针抓 panic 头/正文配对; ② 或先行授权 T0.2 触摸探针 RAM boot(不碰 pram, 拿 RMI4 身份/QUP5 事务一手数据, 为后续触摸适配铺路)。二者互不依赖, 但都要求"无并行 fastboot + 逐轮授权"。

verify: pgrep fastboot=NONE; unittest discover OK; 重生成 sha256 前缀 2aaf092c==心跳1000件; verify_capture_layout raw ok:false rc=1 13 failures; ast 读 STAGE_BASE=0x859e0000 字面
