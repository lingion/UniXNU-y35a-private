# 外部审计建议 — Qoder 辅助会话 — 2026-11-22 23:40 CST

来源：用户委托的独立 Qoder 审计会话（非 Claude/Codex 主线）。本文件为**只读审计后的新增建议**，
不修改 CURRENT.md / LOG.md / LONG-RUN-STATE.md，不拥有任何结论的所有权。
证据等级按治理规范标注：`static` / `measured(host)` / `advisory`。未执行任何设备操作。

---

## 1. [static·高置信] 当前 idle 边界实验的结果可以预先裁决：`cpu_machine_idle_init(TRUE)` 会 panic("No sleep token buffer")

正在进行的 `IDLEBEF0/IDLERET0` 实验（kernel `9f0b947d…`，外置 r326-idle-source-build-20261122-01）
预期结果：**IDLEBEF0 fresh、IDLERET0 缺失**，原因不是挂死，而是确定性 panic。证据三要素（全部已核实）：

1. **panic 路径已编译进正式内核**：被接受的 source-level FP 内核
   `/Users/lingion_k/unixnu-research/reboot-checkpoints/r326-cpudata-fp-source-build-20261122-01/obj/DEVELOPMENT_ARM64_T7001/mach.development.t7001.unstripped`
   （SHA 前缀 `32f937357f81738b9e53`，与账本一致）中 `strings` 命中 `"No sleep token buffer"`（1 处）。
   即 `WITH_CLASSIC_S2R` 为真。新 idle-cursor 内核只加了两个 marker，该路径同样存在。
2. **ADT 无 `stram` 节点**：正式包
   `r326-cpudata-fp-source-package-20261122-01/board.adt` 的 strings 只有 `chosen` 等，无 `stram`。
   `sleep_token_buffer_init()`（arm_init.c:453 调用，cpu.c:946 实现）查不到 `stram` 时**静默返回**，
   `sleepTokenBuffer` 保持 NULL。
3. **代码路径**（pinned source，osfmk/arm64/cpu.c:833 起）：
   `cpu_machine_idle_init(from_boot=TRUE)` → `#if WITH_CLASSIC_S2R` 块 →
   `cpu_data_ptr == &BootCpuData` 成立 → `sleepTokenBuffer == NULL` →
   **`panic("No sleep token buffer")`**（cpu.c:913 附近）。
   调用点在 arm_init.c:507，恰在 `PE_init_printf`（POSTPRT00, 0xb58）之后、
   POSTIDL00（0xb60）之前——与账本当前边界"POSTCNS00/POSTPRT00 fresh、POSTIDL00 缺失"**完全吻合**。

注意：`jtag=`/`wfi=` boot-arg 只影响 `idle_enable`/`wfi`，**不能绕过该 panic**。

### 廉价证伪/证实方法（复用 R152 已有能力）
panic_init 已在 arm_init.c:444 完成，panic log 可用。给 final probe 增加对 panic-log /
`_smsg_bufc` 区域的读回（R152 曾成功捕获 panic 字符串），预期看到 `"No sleep token buffer"`。
一次 paired run 即可把"before or inside"裁决为确定性结论，无需再逐字段加 cursor。

### 修复选项（供所有者裁决，均非安全类 stub，不违反 AMFI/CoreTrust/PPL 约束）
- **A（推荐，保真）**：在 board.adt 增加 `stram` 节点，`reg` 指向一个**显式保留、不与 XNU/载体/report page 冲突的 RAM 页**；
  `sleep_token_buffer_init` 会 `ml_io_map` 它，后续 `bcopy_phys(running_signature…)` 写入该页。
  需要在内存布局清单中登记该页并加入 probe 保护窗口。
- **B（bring-up 最小改）**：在 cpu.c 的 S2R 块把 `panic(...)` 改为 `sleepTokenBuffer==NULL` 时跳过
  sleep-token 写入（S2R 睡眠不在 bring-up 关键路径上）。改动小，但属于行为修改，须按治理规范记录补丁与 SHA。
- **C（配置级）**：以 `WITH_CLASSIC_S2R=0` 重建，整体禁用 classic S2R。语义最干净，但需要确认
  `SleepToken`/`resume_idle_cpu` 相关引用在该配置下全部闭合。

## 2. [static·待核] 次级风险：`monitor_call(MONITOR_SET_ENTRY, …)`（Apple 私有 SMC 0x800）

cpu.c:880 附近 `#ifdef MONITOR` 分支会发 SMC。本次审计未能在头文件/构建日志中定位 `MONITOR`/`NO_MONITOR`
的定义点（构建成功说明二者必居其一）。若 MONITOR 生效：lk2nd 对未知 SMC ID 通常返回 SMC_UNK(-1)，
大概率无害，但建议对新内核反汇编 `cpu_machine_idle_init` 确认是否含 `smc`，一次排除。
若 panic 修复后边界仍停在 idle 内部，这是第二嫌疑。

## 3. [measured(host)] 迁移状态文件已过期：rsync 进程不存在

23:14–23:37 CST 多次采样：`ps` 无任何 rsync/make/clang 进程；设备 `efff9d92` 空闲于 fastboot。
`WORKSPACE-MIGRATION-STATUS.json` 仍为 `status=copying`、`final_hash_verification=false`（15:32 启动）。
源树文件计数 **783,593**（已完成）；目标树计数仍在进行（外置卷 I/O 慢）。
`/private/tmp` 已从中午的 15GB/364 目录增长到 **23GB/630 目录**，重启丢失风险在扩大。
建议：完成目标计数与抽样哈希比对 → 更新状态文件 → 再执行已授权的 symlink 切换与 tmp 根迁移。
**在此之前不要删除源目录**（与既有约束一致）。外置卷为 ExFAT 上的 sparsebundle，非独立备份，注意弹出安全。

## 4. [measured(host)] 并行 sidecar 配置失效（3 并发额度实际只有 1 个可用）

- `ccs-terra/grok-4.7` → HTTP 404 "Model grok-4.7 is not available for this group"（今日 11:37、14:00 两次）。
- 另一分支 429 超出重试上限（13:00）。
- cc-switch 中 codex 侧 terra provider 实际配置为 `gpt-6.1-terra @ devsail.site`；主线 `gpt-6.2-astra` 正常。
建议：用 `gpt-6.1-terra`（或主线同款模型）重开 sidecar；grok-4.7 已不可用，别再重试。
LONG-RUN-STATE.md Ownership 中的 Grok 4.7 侧车名单需要相应更新。

## 5. [measured(host)] Claude 侧技能闸 hook 存在硬编码过期任务文案

`~/.claude/hooks/skill-gate.sh:123` 把"当前任务为：调查、分析和重写 Claude CLI 技能闸的拒绝消息"
写死在拒绝消息模板里，并附一组与该任务绑定的技能建议。实际任务（UniXNU 真机 bring-up）与之无关，
导致 Claude 侧被误导、反复拦截 Bash/Edit/Write（用户粘贴的转录中可见连续两次拦截）。
建议（需用户批准后修改 hook）：把任务描述改为从本轮用户消息动态提取或改为通用文案，技能建议改为按任务类别通用化。

## 6. [advisory] 战略与流程建议（不改变任何既有约束）

1. **明确两条内核谱系的收敛决策**。账本接受的最远边界仍是 R154（11-20 replay）：launchd/dyld 已运行、
   `__mac_syscall("AMFI",90)=ENOPOLICY(103)`。R326 是平行的 native 谱系，近两日在重走 early boot
   （今日真实进展：A53 FPEN 缺失被定位并修复）。iOS 12 跑通的真正前沿是 AMFI/CoreTrust 闭合
   （8 个缺失 pmap/PPL 导出）+ 持久存储 + 显示，而不是 early boot。建议显式记录：R326 达到/超过 R154
   边界后合并回 AMFI 主线，或说明 R326 取代 R154 的理由与验收点，避免两条线各自无限细化。
2. **把"一次 build 一个边界"改为"一次 build 一批边界"**。今日 FPEN 修复后，idle→PE_init_platform→
   cpu_timebase_init→fiq_context_bootstrap→machine_startup 的 marker（0xb60..0xb80）已在源码中；
   修复 sleep-token 后一次 run 可能直接推进多个边界。全量 clean build 在 USB 外置盘上约 1 小时/次，
   建议评估内置 SSD scratch 构建（剩余 204GiB）+ 产物归档外置，或增量构建。
3. **投资 UART 轮询 TX 控制台**（pexpert 层对接 lk2nd 已用的 BLSP UART），让 printf/panic 直接可读，
   逐步替代大部分 readback probe 仪式。这是把每边界成本从"build+package+4 次 fastboot+解码"降到
   "build+一次启动+串口"的最高杠杆基础设施。
4. **目标文本内部冲突建议由用户澄清**："批准一切破坏性工作/刷写分区" vs 账本"RAM-only、持久写入需具体恢复目的"；
   "不要拘泥细节、结果导向" vs "只接受完整哈希+fresh witness"。当前执行侧选择了最重仪式路径，
   与"最快速度"诉求相悖。建议用户明确：证据标准保持，但实验粒度放宽（批量 marker、允许 host-only 预裁决）。
5. **"禁止私自停下直到 iOS 12 跑通"在物理上可能不可达**（AMFI 真实闭合 + APFS OS 卷 3.9GB > 3GiB system 分区 +
   2GiB RAM 的布局问题、显示/触摸驱动均为研究级难题）。建议改为里程碑制：M1=XNU 到 launchd 主循环、
   M2=可见 Apple Logo、M3=SpringBoard、M4=触摸/存储/Wi-Fi。每个里程碑有停止条件与升级决策点，
   避免无限循环消耗（本线程已 ~9.8 亿 token、36 次压缩、522 个 checkpoint）。

---
审计方法：只读检查 rollout 记录（3 段）、共享账本、pinned source、正式内核二进制 strings、
board.adt strings、进程/设备/磁盘状态、cc-switch 数据库（readonly）。
本文件不构成 fresh device witness；第 1 节的设备验证按第 1 节方法执行后方可升级为 measured。