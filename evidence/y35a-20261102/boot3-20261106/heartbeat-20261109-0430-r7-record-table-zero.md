# 心跳 20261109-0430: r7 raw 离线裁决 — stage 记录表全零,"换算错"候选证伪

时刻 04:3x。HEAD=55f8aa5。设备 lk2nd fastboot 槽存活(窗开), 未动。
并行会话在写 builder/patch/readback (M 在途) → 本会话不 boot、不碰其文件,
只做只读 raw 分析。

## 1. 裁决内容 (b5bd946 "新洞: debug_buf 三元组读回 0" 的离线三分支)

三份 r7 raw (baseline/probe2/post-boot3, 各 0x11000, sha 各异见证正常):

- offset 0x40 起 stage 记录表 (物理地址/VA/字数的 .quad 表,
  readback_native.py:298 定义 records 起点=64): 三份全部 u64=0;
- 全窗扫描: 0x44xxxxxx 段 stage 指针命中 0 / gBootPtr 候选值命中 0 /
  Mach-O 魔数 (feedface/feecaf/cafebabe) 命中 0 / 可打印串仅
  Y35ARD01 与 Y35AXNU2 两戳;
- 31 处 0x8-0xA 类 u32-like 值分布在结构体既有字段 (前轮已知内容)。

结论: "debug_buf 读回 0" 的根因 = **记录表从未被填**, 即 stage 的
record 安装环节从未执行 (未插桩内核不写 panic record → records 解析
输入为空 → 表零)。候选 (a) VA→PA 换算错 → **证伪** (换算逻辑再错也
应有非零垃圾指针, 全零=无输入); (b) boot3 未 init → 已由见证件排除
(boot3 确执行); 剩余解释与 0300 轮回撤定罪一致: 内核无插桩, 三元组
本就不该有值。**新洞降级为已知机制的必然结果, 非独立 bug。**

## 2. 交叉核验

- builder 在途件 diff 含 SFLAGS 修复 = 0 行, patch 去 guard diff = 0 行
  → 插桩修复仍未落地 (git show 误报排除: 8cd1678/f33b83c 是 HEAD 可达
  旧提交, 非并行会话新提交);
- 顺序闸 (字面量扫描 0→非0 才谈插桩 boot3) 维持, 无变更;
- 远端 push: lingion 无权限 (55f8aa5 已立案), 待用户裁决 fork+PR 或
  org 授权;
- 守护 cron 12362354 + 保险丝 5f873c8d 均在位, 035x 轮已核验, 本 20 分钟
  间隔不重复核验。

本轮: 未 run fastboot, 未写分区, 未 boot, 未 push, 未碰并行在途文件。

verify: python3 struct 全窗扫描三 raw (输出见 §1); git diff/show 计数;
git status 快照 — 全部本轮新鲜执行。
作者: lingion <lingion@hrbeu.edu.cn>
