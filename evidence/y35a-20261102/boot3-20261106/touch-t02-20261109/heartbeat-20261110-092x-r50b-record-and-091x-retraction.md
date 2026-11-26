# 心跳 20261110-092x: r50b record 到手且信息极重 — 本线 091x 判读当场二次勘误(pw 非独立执行, 差分复现不成立); 边界真推进 = INTSP000(s37)后、LINKADDR(s38)前的回归窗, Codex 主嫌 = r50b 新增 x16 物理转换 store; record 引本会话 090x 为 HEAD(勘误已达受众)

时刻 09:2x。HEAD=33ae764(本线顶)。设备 efff9d92 fastboot
空闲。零设备指令。

## 1. 091x 判读当场作废(自证链, 三条)

091x(33ae764, 数分钟前)称 "pw 与 r50b-min 读数集逐位
相同 = 差分可重复, min 覆盖截短解释力下降"。本轮读到
r50b record 后自证其误:

- pw final 与 rb final 的 carrier 区(0x40 基扫描域)逐字节
  同, **含 0x10 的 CNTVCT 新鲜度见证也同(8d5efe0200)** —
  同一场 XNU 执行的留存内容, pw 探针只是又抄了一遍;
  差分唯一点 = 0x10050(pw 自身报告的 CNTVCT, 新值);
- pw 目录**无 boot3 镜像 boot 日志**(序列缺重跑 XNU 步骤);
- record 原文定性: "The entire preserved PRAM prefix in
  the follow-up raw matches the prior r50b final raw;
  this confirms the pointer probe did not alter that
  retained region" — pw 目的 = 回读
  `_native_early_fault_address` 全局(KVA
  0xfffffff0076d2108→物理 0xa06d2108), 结果该全局**零**。

"两枚探针独立跑复现"一句作废; 090x 纪律(翻案级声称当轮
二次全量实查)本轮第 2 次救场 — 且这次是提交后 6 分钟内
自纠。

## 2. r50b record 的正题(边界与回归诊断)

carrier 合同(record 明文档): loop state=46/47, header
checkpoints=48/49, mapping=50..55; boot shim 进 XNU 前
清零 512 诊断字节。**090x/091x 悬置的"几何混淆因子"就此
排除** — 我的 0x40 基读数与 record 的 0x10100 基槽表逐项
同(4,17,22-37,49; 38/39-45/50-55/46-47 零), 归零是真实
读数非映射伪影。

**边界判定(record Decision 原文转述+对槽)**: 确证到达
_start_first_cpu、六 boot_args 装载、x22/x23 基址、TPIDRRO
+ 异常栈三连 + 中断栈三连(s31..37 阳)。**s18 STACKS00 与
s38 LINKADDR 双双归零 vs r33/r42 时代阳性 = r50b 代际
回归**, 挂死窗 = INTSP000 之后、link/early-fault store
一段。record 主嫌: r50b **新增**的 x16 物理地址转换
(用 x22/x23 换算后 store 经该地址)即回归源; 未证(故障
记录零不能排除异常)。下代实验 = x16/x17 操作数快照 +
store 前后标记, 区分"算术死/store 死/store 后死"。

**旁证收口两笔**: ①r50 首稿被 Mach-O 闸拒(常量编码错,
record 自白)= r50 系离线代际真实存在, 但从未上设备;
②r50b 成功跑中 boot3 后首读 serialno 亦遇 e00002ed 一次,
等待即恢复 — 假设 2(宿主 USB 间歇)在成功件里留了现形照,
R47 连挂/R49 连挂是同一间歇的坏运串; Codex 政策已采纳
"传输失败即停不作 XNU 证据"(与本线 015x 纪律同构)。
**判别注意**: 各探针镜像 n=1, 尚无干净 A/B, 假设 1 未被
单独证伪, 只是不再是必需假设。

## 3. 治理观察(两条正向)

- **r50b record 引用 HEAD 928cff4(本会话 090x 勘误)** —
  Codex 在读并锚定我们的勘误链, 协同闭环首次肉眼可见;
- record 内置 **7 个输入文件逐 SHA 钉版**(含五个 patch +
  build/package/readback 三脚本) — untracked patch 的不可
  再生风险在 r50b 上被"哈希存档"实质缓解(缺陷 A 型事故的
  免疫模板, 值得后来各代沿用)。
- record 欠账: r50b carrier HAS(09:12 收), pw 段并入该
  record 视同已收; 总欠账待下轮全量重数(090x 记 19, r50b
  +1 收 −1 新账, 大致持平)。LOG/CURRENT 仍 M; 13 patch
  untracked 不变(哈希已存档); probe 三闸零收口; 守护健康
  (下轮 CronList 例查); GO 未回。

## 4. 下轮盯点

x16/x17 快照代(r51?)实跑与三窗判别; 若再卡传输, 换口
对照可提请用户; pw/rb 双 record 若拆分补写, 账目再对。

verify: python3 双 final 逐字节差分(off 清单+0x10/0x10050
字段实值)当轮实拍; r50b 新址目录 grep 无 boot3-boot 日志
实查; record.md 全文实读(合同/Decision/pw 段/七 SHA 逐字);
091x 判读与 record 原文对撞引用; host suite 98/98 与本轮
08:43 Ran 98 交叉一致; ls 目录改名后新名(phase-r50b-
carrier-20261110 / phase-r50b-pointer-window-20261110)
实拍; fastboot devices; pgrep 空 — 全部本轮新鲜执行。
作者: lingion <lingion@hrbeu.edu.cn>
