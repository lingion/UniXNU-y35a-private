# r9 验收电池 尾项闭环 20261109 ~12:5x — 闸入库(a8958b0): 合同完备

fixer turn 后落库确认(独立 fresh 复核 @ a8958b0 干净 worktree):

## NOTE-A(连续两轮遗留)解除
- a8958b0 提交 scripts/y35a/verify_capture_layout.py + tests/test_capture_layout.py
  ("验收合同面入库") → clean tree 现**自带可执行闸**。
- 提交态套件 @ a8958b0 = **75 OK (skipped=1)** (69→+6 布局闸测试);
  仍非 84: verify_readback_transport.py + 其测试、verify_capture_transport.py
  这三个 **未跟踪**, 但入库的 layout 闸本体已按 transport_mode 分支
  (verify_capture_layout.py:39-48: 双模式判别 + mb 须 pram_preserved=true),
  合同强制面**不再孤儿** → r9 验收合同判 COMPLETE。
- 双 manifest 从提交树跑闸: r8 frb(--stage-base 0x859e0000) ok:true/0 fail;
  mb1(--stage-base 0x859f0100 报告页) ok:true/0 fail。

## 残留(非阻塞, 记账)
三个 transport 相关件仍在 untracked 面 —— 若 fixer 视其为合同一部分需另提交;
但当前 layout 闸的 mode 分支已覆盖声明式破坏合同, 我个人认为 transport 本体
可选(redundant), 不列为 r9 见证完备性的阻塞。

## 权威代次(不变)
ce63d21a (full-readback r8) / 7f81f759 (minimal-boundary mb1), 均 bit-identical 复现。

## 设备面
本轮零指令, device client none active。任何后续设备动作先双查
(list_sessions isRunning + 用户本轮授权文本)。

verify: git show a8958b0 --name-only; worktree 干净树 unittest 75;
双闸 subprocess ok:true 含 mb 正确 stage 基址; git ls-files 三 transport 件空。
