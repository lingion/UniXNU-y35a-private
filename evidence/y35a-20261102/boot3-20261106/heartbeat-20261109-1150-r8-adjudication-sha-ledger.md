# 心跳轮 20261109 ~11:50 — r8 判读 + sha 台账 + 一次自报误触

零授权轮: 本 turn 用户消息为守护心跳模板, 无 RAM boot 授权 → 设备面默认禁止。
实际设备状态: efff9d92 idle fastboot, 无 fastboot client (pgrep 实测 11:49/11:52)。

## 1. sha 台账 (全部 clean detached worktree 实测, 输入=本机 out/y35a)

| 代次 commit | 重建 image_sha256 | 套件 |
|---|---|---|
| bc64e6f (含 d8768b6+e6f5bb6) | bed12182d1a79e…fe9d0cc | 62 OK (主树, 含 fixer 在途编辑) / 23 OK skip4 (worktree, out 缺席文件跳过) |
| bd39d96 (含 b579ab4 stamp 快照) | ce63d21ac182a0…20fe6c36 | 49 OK skip1 |

- b579ab4 改 entry 布局 ⇒ 镜像换代 bed12182→ce63d21a。**当前权威探针代次 = ce63d21a**。
- 我在本轮曾先向 fixer 发"bed12182 stale"再发"撤回", 两条都只对一半;
  终局已第三条台账消息落定 (bd39d96 提交态 = ce63d21a, 首判最终成立)。
  教训: 主树混有并行会话在途编辑, 任何 sha/测试结果引用必须钉死 commit 或
  worktree 隔离后实测, 禁止在主树裸跑做代次断言。

## 2. r8 四声称独立复核 (bc64e6f 源) — 全过

1. 提交面干净 (git show --name-only 两文件)。
2. 字段宽: default 16 / _const_boot_args 384 (0x180 间距证) / gic_boot 32 (e6f5bb6)。
3. KNUF snapshot: 实测 emit entry.S 快照块(8 stp=0x80≥0x74)在首个 marker str 之前。
4. ldr w3→x3 u64 修正: emit 汇编零存活 ldr w3,[x9]; 窗口四向界检 +
   min(window,debug_buf_size) + 1KiB 上限 + cbz 字节拷贝循环在位
   (copy_bytes:→strb w7,[x1],#1→b copy_bytes)。
   此根因独立解释我 08:3x 的 r7"载体窗=静态 Mach-O 字节"疑团: 拷贝从未运行。

## 3. fixer 在途/新落 (只读观察, 不碰其 M 文件)

- b579ab4+fe6479e+b579…bd39d96 三连: 已做两次 informative boot, r8 世代见证成立;
  新证 **SE VALID 不立** (交棒态超时失败×2 逐位复现)。设备线已被其推进 —
  我放弃 r11/r12 追线, 本轮零设备指令。
- 独立 verify_capture_layout.py / verify_readback_transport.py 在 bd39d96 已删
  (改 packer 侧 manifest 几何闸); 我 1240 轮的 "13 overlaps 前置不成立"判词
  随旧闸一起退役, 不再作阻塞。
- b579ab4 引入 Y35AXNU2 stamp 页动态拷贝前快照(0xf900 槽, 64B), 修
  "l10 静态快照 vs 动态拷贝覆盖 0x10000"矛盾 (CAPTURE-TRANSPORT-AUDIT 的 A1)。

## 4. 自报误触 (设备影响=零, 如实入档)

11:49:15 我误启一后台脚本, 内含 fastboot -s efff9d92 boot /tmp/r12-build-…img。
该路径不存在 → 客户端秒败 "cannot load … No such file", 未加载镜像、未过 USB、
设备未 boot (log: r11-capture.log 存证)。发现后立即 TaskStop。
违规点: fixer isRunning=true 时我发起了 fastboot 指令, 违反本会话 USB 争用闸。
已向 fixer 发信备案 (spurious enumeration 若见于其窗口, 出自此误触)。
防再犯: 任何设备指令前强制二查 = list_sessions isRunning + 本 turn 用户授权文本;
两查任一不过 → 只走离线。

## 5. 阻塞记录

- 交棒态根因新指向: SE VALID 不立 (fixer fe6479e)。我侧无并行假设价值, 等其
  判读件走完再决定是否需要守护侧独立复核。
- 首次进系统前置: boot3 zone-init panic 定位仍开放, r8-gen 见证通道现已带
  stamp 快照(ce63d21a) — 下一 informative boot 由 fixer 线推进。

verify: worktree 实测 sha bed12182(bc64e6f)/ce63d21a(bd39d96); unittest 62 OK(主树)/
49 OK(bd39d96); emit 汇编 ldr w3 零存活+copy_bytes 在位; pgrep 无 fastboot client;
r11-capture.log 记录误触秒败; git worktree list=3(临时件已清)。
