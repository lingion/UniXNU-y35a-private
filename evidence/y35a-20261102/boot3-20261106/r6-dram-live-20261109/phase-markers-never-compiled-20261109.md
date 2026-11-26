# 关键否证: 相位插桩从未编译进任何内核 (2026-11-09 01:2x 审计轮)

结论: 至今所有 "phase" 实验跑的都是无插桩内核。record[5] 读回恒 0
不是时序问题, 是代码从未存在。r6 的 ARMVINI/PANICINI/CONSOLE 全 0 由此完全解释。

## 证据链 (全部只读)

1. 三件编译产物扫描 0 命中 (movz/movk halfword 机器码 + 8 字节小端字面量双模式):
   - out/y35a/ios12-boot3/kernel-packed.macho (5fd4e6b5, 出货 boot3)
   - out/y35a/ios12-boot3-phase/boot3.img 内嵌 kernel (c3110cd6, Nov 7 17:00 代)
   - 容器 /work/UniXNU-y35a/out/y35a/ios12-kernel/mach...noctf (70eec34f, Nov 9 00:31 新 build)
2. 6e9a09d2 (phase "packed") vs vanilla 5fd4e6b5: 全件 diff 仅 2375 字节,
   逐点聚类核对 = version[] 时间戳串 (Nov 4→Nov 7) + 头部对齐噪声。
   即 17:00 phase build 与 vanilla 代码等同。
3. 源码侧: /work/xnu-4903 (src) grep native_phase_marker = 0 处;
   .cache/xnu4903-work (work) 存在定义+ARMVINI(396)+PANICINI(408) 但
   CONSOLE 调用点缺失 (434f4e534f4c45 计 0) → patch hunk 4 实际未落地
   (本轮对该 patch 的 dry-run 亦只报 Hunk#2/#3)。
4. 机制候选 (未定罪): builder make 行携带 arm_init.o_CFLAGS_ADD=
   -DXNU_NATIVE_EARLY_FAULT=1, build.log 静默规则无逐文件 CC 行, 无法从日志
   证实 flag 进入编译; 00:27 的 arm_init.o 与终件均无 marker 符号/字面量
   → 实际效果 = 宏在编译期不可见。无论根因是变量传递还是 rsync 覆盖时序,
   "guard 依赖 make 宏" 这一设计已被证伪不可靠 → 步骤 4 改为默认开启插桩。
5. sleh.c 无插桩 = 正常: native-early-fault-record.patch 本就只触
   locore.s/start.s (guard 计数 2/1); pe_init.c 才是魔数生命周期主体 (前轮已证)。

## 影响与下一步

- §3(a)/(b) 之争 ("文本在、头不在"): 相位实验从未开始, boot-order 结论
  (XNU 启动清零 pram) 不受影响; "有文本无头" 的定性仍需真插桩内核裁决。
- 00:31 build (70eec34f) 从未打包/上机 (无 00:3x boot4-r3 记录, 设备仍持
  11-07 代)。
- 下一步 (需用户放行): 去 guard (native_phase_marker/record 写入默认编译,
  仅动 work+src 的 arm_init.c 并补 hunk 4), 增量重建 → nm 必须见
  _native_phase_marker 调用效果 (字面量扫描过 0→非 0) → 重打包 → RAM boot。
- 本轮不碰 package_native.py (并行会话在途件), 不 run fastboot, 不 commit。

verify 命令: 见本轮 Bash 记录 (mov-halfword 扫描脚本 + diff 聚类 + grep -c 计数)。
