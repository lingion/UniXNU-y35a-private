# 心跳 1115 — 三闸制对读回线首判: R9 #1 即红(无 transport_mode 声明), r8 三轮未落; 不 boot

HEAD `afa002b`, 分支 `fix/readback-panic-globals`。全程离线, 零设备操作, 无分区写, 无 userdata。

## 盘点 (fresh)
- linked sessions: fixer `local_c3ce3e96` 仍 running(10:25 最后活动)。存储线 `unixnu-storage-interface`、`t4-3` idle。守护双活。
- fastboot 进程: NONE。
- fixer 新工: 0e269ec(T0.2 manifest 声明 minimal-boundary+pram_preserved, 三闸入构建) + afa002b(R9 收编心跳)。**读回线 r8 未动**: git diff readback_native.py/tests 均空 —— 无在途 WIP, 三轮同判 (STAGE_BASE 字面 0x859e0000 仍在, 无字段宽, entry_trace 仍在 NAMES 无 absent 处理)。

## R9 判词(Codex 属主文件, fixer 已收编)要点
93b7978 几何仅对独立触摸探针有效; 读回线 full 模式(payload 16K+32K 栈 > 0x1000 报告页, 全 pram 复原会擦记录表)是**另一契约, 禁混用绿灯**。Required-gates #1 = 每 manifest 自证 transport_mode。

## 本轮实测 (读回线在新三闸制下的真实位置)
1. `unittest discover -s tests` → **OK** (fresh, afa002b)。
2. HEAD 生成器重打 readback 候选: sha256 前缀 **2aaf092c 与心跳1000(6daa7a0)/1020(54401a0) 三点一致** —— 生成器语义自 r7 未变, r8 确未落。
3. `verify_capture_layout` raw: **rc=1, 13× overlaps pram** (stage 别名未修, 与前两轮同)。
4. **新闸 `verify_readback_transport.py`**(10:15 落盘)对读回 manifest: `transport_mode` 字段 **不存在**(json 实读 False/None) ⇒ 即便补齐几何, R9 #1 仍红 —— 读回线尚未接入自证模式声明, 属 fixer 待做。entry.S 读+有界拷贝块实存(csel/copy_bytes ×4), 42 tests OK 不含此新闸回归(闸本体 untracked)。
5. 触摸线按其 1045 verify 行为三闸绿+构建判等 295241ce; 本会话未独立重打(不碰 fixer 属主件, 且其注记含容器实录)。

## 设备闸: 不 boot (本轮用户消息仍无逐轮授权)
- 读回探针: informative 前提红(别名+无模式自证), 抓回必伪影。
- 触摸探针: 几何+模式三闸绿、独立于读回迁移(fixer 1045 明确"先行不需要读回落地"), 是**当前唯一可 informative 的 RAM boot**; 但目标顺序固定 iOS 首发在先、触摸在后, 且本轮无 GO ⇒ 不动。
- 决策点重申(待用户): ① GO 触摸探针单发(README Per-Experiment 立案, 零 pram 写, 拿 RMI4/QUP5 一手数据); ② 等 fixer 落读回迁移(去别名+字段宽+mode 自证)后 GO 读回抓 panic 头/文配对 → 符号化 → 最小修复。二者可并行排队, 都要"无并行 fastboot + 逐轮授权"。

verify: pgrep fastboot=NONE; git diff 两读回件=空; unittest discover OK; 重生成 sha256 前缀 2aaf092c(三点一致); verify_capture_layout rc=1 计 13 行 overlaps; json 实读 transport_mode=False; grep -c csel|copy_bytes entry.S=4
