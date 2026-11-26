# boot4 panic 读回线终裁 + 设备闲置登记 (2026-11-09 05:4x)

## 1. 一手源核验: 交接 #1 的机制为真, 文件与结论两处须修正

官方 tag f746d834 (xnu-4903.270.47) pexpert/arm/pe_init.c 实拉:
- check_for_panic_log() 在 **:73** (交接说 sleh.c, 错; sleh.c 全文
  grep 无此符号, gh search 亦 0);
- 调用点 **:423**, 在 **PE_create_console()** 内 (交接说 PE_init_kernel, 错);
- **:136 `bzero(gPanicBase, gPanicSize)` 是无条件执行的** — 三分支
  return ('SHMC'/'BTRC'/魔数打印) 之外, 魔数是否为 KNUF 都清零;
- 前提条件: :88 `DTLookupEntry(0,"pram")` 与 :100 "embedded-panic-log-size"
  缺失即提前 return, 不清零不映射。
→ EPH 区的生命周期写入者 = osfmk/kern/debug.c (gPanicBase 使用点:
  model_dep.c/kdp_common.c/kdp_core.c/debug.c/ext_paniclog.c/pe_init.c)。

## 2. 裁决: Codex 评审 "冻结旧 PRAM 解读" 成立

boot4 = "跑完一次干净启动之后" 的捕获阶段。PE_create_console 的无条件
bzero 使任何 XNU 完整启动过的 EPH 区必为零 → boot4 读回空文本与该机制
一致。"第二次启动后再取 reason" 的路线 (handoff #1 表述) 与自家 bzero
矛盾, 修正后只剩两条可行路线, 均在 bzero 之前:
- (a) 崩溃当时/重启前由外部读回 (现有 oem panic 手段已覆盖);
- (b) 真值核验: stock boot 一次, 读回应仍为 KNUF 戳+旧文本 (旧文本
  被 bzero 但 magic 先于检查为真时走 return 打印路径 — 需实测区分
  'SHMC'/'BTRC'/KNUF 三分支);
- (c) iBoot/lk2nd 侧 staging (先提取再 boot) — 公共 msm8916 树 0 先例
  (gh 代码搜索实证), 属新代码工作量。
下一判别器仍是评审 §4 计划 (arm_init 入口+PE_init_platform 两点插桩),
PRAM 线保持冻结。

## 3. 设备占用登记 (用户指令: 无人驱动必须上报)

实测 05:4x: fastboot devices = efff9d92 "fastboot" (lk2nd), 无 adb;
fastbootd-20261109/.lk2nd-flash.lock 不存在, tv_lock 无活 claim;
并行会话最后活动 04:40 提交; 本会话全程只读设备标识。
→ **设备自昨夜空窗起无人驱动**。boot4 终裁已给出, 下一步 (a/b/c
路线选择 + §4 插桩 build) 需要用户或新会话认领, 本会话不代跑。

## 4. push 受阻补记

gh api orgs/UniXNU/memberships/lingion = 404 (非成员),
collaborators/permission = 403 — 与前轮四通道 403 同因。恢复途径唯一:
org 管理员授予 collaborator (write)。等用户处置。

verify: curl raw pe_init.c 行号实证 / gh search 两次 (1 count/min 配额内)
作者: lingion <lingion@hrbeu.edu.cn>
