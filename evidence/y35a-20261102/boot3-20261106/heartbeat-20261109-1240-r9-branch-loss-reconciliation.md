# Heartbeat 12:3x reconciliation — r9 workstream LOST from branch, touch-t02 survives untracked (read-only turn, no device operation)

## 信息冲突枚举 (本 turn 实跑)
- linked sessions: `local_c3ce3e96` (fixer, readback_native/段摆放, **isRunning:true** —
  早前"fixer 已完成"判词作废, 其为在途活跃工作流), `local_52360cd9` (Side chat,
  曾报 PID 75241 boot 事务, 现空闲), `local_4de0039c` (t4-3, 空闲)。
- scheduled: threads-daily-pipeline 与本线无关; 守护 cron `6d542c90` 本 turn 未续期
  (**下一自然到期 = 11:07 已过? 实为 2026-11-10 11:07 前仍 ENABLED**, 本 turn
  仅记录不重排, 因 heartbeat 条款只允许提交本轮文件)。
  更正: 11:07+20min=11:27 已过期? CronList 未再跑, 留待下轮 verbatim 重排核查。
- 仓库: HEAD 现 `d8768b6` (本 turn 期间仍随 fixer 漂移); 分支
  `fix/readback-panic-globals`。
- `pgrep fastboot` = 无进程 (read-only 检查, 未跑任何设备命令)。

## 核心事实: 本会话 12:4x 的 r9 迁移被整枝清除, 不可恢复 (fresh 实测)
- 本会话早前提交 `8287f94` (r8 landed + 模式迁移 feat) 与 `e0709e3` (r9 boot
  序列证据) 已从 branch reflog 与 HEAD reflog 双双消失, `git cat-file -t` =
  "Not a valid object name" — 对象已 GC, 无恢复路径。
- 证据树 `evidence/.../r9-readback-20261109/` (含 3×69632B raws + manifest +
  record, 我曾 commit) 已从磁盘消失, find 全盘无命中, 容器 /tmp/r9-run 同灭。
- out/y35a/readback-probe-20261109-r9/ (9a3d893d 镜像) 同灭; 用**当前** tip 源
  重生成 = `bed12182…` ≠ 9a3d893d — 因 tip 的 readback_native.py 是 fixer
  ce168bb 的 `full-readback/pram_preserved=False/0xf800 槽` 版, 我的
  minimal-boundary 迁移 (记录窗外移至 0x95000000) 一并被回退。
- reflog 中 14c64e3 之后存在**空消息 HEAD 条目** (@{0}), 与 fixer 会话 11:16
  提交 ce168bb 交叠 — 清除者身份未证实, 最可能为并行会话 reset/rebase 误伤;
  不指控, 记录事实。
- **推论 (重要)**: 上一轮 12:53 交接中 "boot4-r10 完成/捕获三件套/r7 判据
  (b) 重采样" 等陈述, 其原始凭证 (raws) 已不存在, 按证据优先纪律**降级为
  不可复核**, 禁止在 CURRENT/ROADMAP 复述为既定事实。若 r10 现象真实,
  fixer 会话或仍持有其副本 (其 11:05-11:12 dual-run 记录亦提过同型 boot);
  需其自行落证据方可采信。

## 独立三闸复核 (fresh 实跑, 对当前 tip 重生成的 r8-gen manifest)
- `verify_capture_layout` (manifest bed12182-gen, pram/stage 实测常量):
  **ok:false, 13 overlaps** — 记录表仍在 pram 内, stage 别名 pram 未解。
  → 读回线 informative-boot 前置不成立, 维持"不 boot"。
- `verify_capture_transport` (几何常量: snapshot 0x95000000/report 0x859f0000):
  failures:[] 绿 — 该闸验提案几何而非 manifest, 两闸结论不矛盾。
- `verify_readback_transport.py --mode …` 本 turn 实跑因参数不全未得判词,
  如实记为"未测", 不沿用任何历史绿/红引用。
- 全量测试: `python3 -m unittest discover -s tests` = **53 tests OK** (fresh;
  CURRENT.md 文本仍写 52/52, 系其落笔时点旧数, 无冲突实质)。
- boot3.img mtime 未变 (Nov 6 23:58), 54618112B。

## 触摸线 (本会话独有幸存资产, 磁盘完好未入库)
- `evidence/.../touch-t02-20261109/` 完好: record.md + t02-touch-capture.raw
  (sha fcff2265…, fresh 复核一致) + 并行会话写入的三个 heartbeat-20261109-1130-*.raw。
- 判读不受影响: identity 事务 E_TIMEOUT_STATE, 交棒态 QUP5 clock/pinmux 未配,
  "纯交棒读可用"假定性否定。
- 该目录全部 **untracked**; 本 turn 按"只提交本轮文件"条款不 commit 它们,
  移交下一轮或本会话后续 turn 授权提交。

## CURRENT.md 冲突处置
- tip 的 CURRENT.md (他人 11:1x 重写版) 现陈述 "R8 green / R9 red, 记录仍在
  pram, mode gate 拒" — 与我 fresh 实测 (layout 13 red) **一致**, 无需纠正;
  我 12:53 请求其追加的 "r9 已绿已 boot" 行未进 tip, 恰与证据丢失后的真相吻合。
- 遗留唯一叙述风险: 若 fixer 会话私下持有 r10 raws, 需其自证入库; 本文件已
  立"不可复核"标注, 下游引用前先查此。

## Next Work (信息不冲突部分)
0. 读回线唯一路径不变且更急: fixer (仍在跑) 的 full-readback 模式记录窗
   仍别 pram (13 overlaps) — 迁移工作需重落 (我的实现已被清, 源码思路在
   R9-READBACK-TRANSPORT-RECONCILIATION.md + 本文件 §核心事实 有完整记录可
   复用: 记录窗外移 0x95000000, panic dest 0x859f1000, stage-size 2*0x10000,
   entry.S 双搬运+回写, 同窗先拷后清)。归 fixer 会话, 勿并行重复。
1. 触摸线 T0.3 (clock-enable+pinmux 冷读案) 等用户逐轮 GO; 本 turn 零设备。
2. 守护 cron 6d542c90 到期重排在下一轮执行 (本 turn 禁非文件类改动)。
