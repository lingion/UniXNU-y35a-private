# 心跳 20261109-0945: T0.2 探针基址派生化收口 — staging 迁移自动跟随,布局闸复现 r7 判词

时刻 09:4x。HEAD=8cc3950(本会话)+ 并行在途。设备 efff9d92 fastboot 在槽,
本轮零设备操作。

## 1. 盘面确定性判据(全实跑)

- fixer(local_c3ce3e96)+ Codex 分工新实证: Codex 落了独立闸
  `scripts/y35a/verify_capture_layout.py`(untracked,09:0x),只读验证
  不碰生成器;CURRENT.md Next-Work #0 升级为"gate 不绿禁任何 device
  run"。生成器迁移仍未落地(readback_native.py STAGE_BASE 仍
  0x859e0000,committed 态)。
- 闸本轮真实复现两次: r7 manifest 13 项全 overlap(rc=1,判词同构);
  触摸探针自身 manifest 1 项 stage-overlaps-pram。红=迁移前预期,
  拒绝权在台账不在构建。
- 台账(README 规矩: 只读 fastboot 在场检查;并发 fastboot 禁)。

## 2. 交付(7e33199)

rmi_probe.cpp/probe_rmi.py 基址改**派生**,单一真源:
- STAGE_BASE 从 readback_native.py 字面正则解析;pram 窗从
  make_adt.py 的 node('pram',...) struct.pack 字面解析;
- fixer 迁移一落地,下轮重打自动跟随,触摸线零编辑零择址;
- entry shim 栈 = stage-0x1000 派生(emmc 一页下方法,不再是独立
  魔数 0x859d0000);
- C++ 侧故意无 fallback 宏默认值: 漏 -DY35A_STAGE_BASE 直接编译失败,
  禁静默吃陈旧地址;
- layout_gate 每构建跑进 manifest.layout_gate 字段。

## 3. 构建验证(真实输出)

- 容器首打报 STAGE_BASE not found — 根因=容器签出落后
  (readback_native.py 无 91ab4a1 witness 行);docker cp 同步 host
  committed 版三件后绿。这坐实"容器 /work/UniXNU-y35a 是陈旧快照,
  构建输入必须逐文件 cp 同步"操作纪律。
- 新镜像 sha256 71be64a4…(旧 074542f5→ 变因: 基址由编译期字面量
  改运行时参数物化,probe.bin 3856→3864B,非行为变化;两 hash 都
  在案可追)。
- objdump 交叉证派生生效: `movk w19,#0x859e,lsl#16` 入码,
  entry.S 栈 = 0x859df000;llvm-nm -u 未定义符号 0。

## 4. 边界

未 run fastboot(仅在场检查),未 boot,未写分区,未 push;未碰
readback_native/package_native/boot_layout/patch 等 fixer 在途件与
台账在途编辑(CURRENT.md/LOG.md 的 M 态留给其属主提交,本文件只
引用其 committed 部分 0cded8a 与本会话 8cc3950)。

verify: git log/status、grep STAGE_BASE 双态、闸实跑 r7+自 manifest、
容器重打全链+nm/objdump/entry.S 检查、docker cp 同步记录 — 全部本轮
新鲜执行。
作者: lingion <lingion@hrbeu.edu.cn>
