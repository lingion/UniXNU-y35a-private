# 验收轮 20261109 ~12:05 — r8 (b579ab4) 接受电池: PASS + 两笔账务备注

触发: fixer 交棒请求(handshake)。全程离线, 零设备指令, 零 push。
隔离: clean detached worktree @ b579ab4 (/tmp/acc-b579ab4, out 软链)。

## 独立复核结论(不采信 fixer 自述, 全 fresh 实测)

| 声称 | 判定 | 证据 |
|---|---|---|
| 三提交只动两文件 | ✅ | git show --name-only d8768b6/e6f5bb6/b579ab4 逐一核 |
| sha=ce63d21a 权威代次 | ✅ bit-identical | worktree 重 build rc=0, shasum 与 r8 目录实物逐位同 |
| ldr w3 死绝 | ✅ | r8 entry.S grep 'ldr w3,[x9]' 零存活 |
| KNUF pram 快照(0xf800,128B)先于 magic str | ✅ | emit 序: snapshot_store(0x2ca) → 首个 marker 写(0x714) |
| stamp 快照(0xf900,64B)先于 copy_bytes | ✅ | ldr x8,=0xf900 块在 copy_bytes: 标签之前; 快照经 x10/x11 暂存读 x3(PA), x1/x2 在块内不动; 块后 ldr x1,=0x859f0000 为拷贝目的地设定 — 顺序合法 |
| 槽位无后写 | ✅ | records end 0xc3c0 < fault 0xf000 < 快照 0xf800/0xf900 < panic dest 0x10000(限 0x1000): 全序无重叠, 头部 FUNK 可测(前置(A)达成) |
| 闸 ok:true on r8 manifest | ✅ | verify_capture_layout → ok:true, failures=[], warning=声明式破坏(full-readback/pram_preserved=False) |
| 1KiB/界检/cbz set_table | ✅ | emit 在位(承前轮, r8 未回退) |

判据修正(采纳 fixer 指出): 阻塞前置从"13-overlaps 清零"改为"当前闸
verdict + 声明式破坏字段齐备" — 磁盘闸面即合同, 1240/0830 旧措辞作废。

## 两笔账务备注(非缺陷, 已回邮)

1. 计数: b579ab4 提交态套件 = 49 OK(skip1), 非 fixer 报的 62。62 含未跟踪
   工作树件(test_capture_layout.py 等)。ordering/width/clobber 锁确在
   提交件 test_readback_names.py 内(git grep 证实) — 引用口径统一为 49。
2. 孤儿闸: scripts/y35a/verify_capture_layout.py 与 tests/test_capture_layout.py
   从未在任何分支提交(全分支 log 空)。packer 发布几何字段
   (readback_native.py:419-429)但读者/闸本体未入库 → clean tree 无闸可跑
   (ModuleNotFoundError)。已请 fixer 在设备线前补提交闸+其 5 测试;
   我侧在提交前不将 r8-gen 见证列为验收合同依赖。

## 设备面

- 本轮零指令。fixer isRunning=true(交棒请求进行中)。
- 下一切设备动作双查: list_sessions isRunning + 用户本轮授权文本。

verify: 见上表命令(git show/shasum 双件比对/grep+sed emit 块/闸 rc+JSON/
unittest 49)。worktree 已清理(验收后 remove)。
