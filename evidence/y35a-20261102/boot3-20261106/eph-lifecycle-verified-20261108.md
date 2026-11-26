# EPH 生命周期源码核实 (2026-11-08 心跳轮, build container 实测)

容器 unixnu-y35a-native-20261103:/work/xnu-4903 (= xnu-4903.270.47)。
全树 grep EMBEDDED_PANIC_MAGIC 持有者仅 4 处:
kern/debug.h(定义)、pe_init.c(消费+写)、tools/lldbmacros(调试脚本)。
kdp_core.c 不含该宏(handoff finding 2 里"Apple 自家分分布"范围之外无第三方)。

## 1. 清零点修正: 不在 sleh.c, 在 pexpert/arm/pe_init.c

check_for_panic_log() = pe_init.c:73; 调用点 PE_create_console() 内
pe_init.c:423, 源码注释自证 "Do this before the VRAM is trashed"。
handoff-lingion-k-20261108.md finding 1 记的 sleh.c 系误标, 本条修正;
其推论(XNU 每次启动自己清 pram)成立, 位置更正为:

- DT "pram" 节点 reg → ml_io_map_wcomb → gPanicBase (pe_init.c:88-110)
- /chosen embedded-panic-log-size 提供长度 — 注意: 我们 ADT(make_adt.py:51)
  有 pram reg, 但 /chosen 是否有该 property 未核; 缺 property 时函数
  提前 return, gPanicBase 不初始化, 整条清零/读头路径全灭 (待核 CANDIDATE)
- 'SHMC' → panic_console_available=TRUE, return (不清零)
- 'BTRC' → return (不清零)
- 'FUNK' → 仅打印 "iBoot didn't extract panic log..."
- 以上全落空后 bzero(gPanicBase, gPanicSize) 全区清零 (pe_init.c:136)

## 2. 写头顺序 (推翻本轮初稿的错误认知)

panic 路径头先写、文本后写, 成对出现:
- Debugger(DBOP_PANIC) → debug.c:882 PE_init_panicheader()
  (只由 began_writing_paniclog 静态位控一次, 嵌套走
  PE_update_panicheader_nestedpanic)
- PE_init_panicheader (pe_init.c:564-581): bzero 头 0x74 →
  eph_panic_log_offset = debug_buf_base 偏移 → eph_magic='FUNK' → version
- debug_log_init (debug.c:357): debug_buf_base = gPanicBase + 0x74,
  即 panic 文本(含 zone info、Stackshot Incomplete 行)全部在头之后
- 内核里没有任何"提交/定稿"步骤把 magic 最后才写 — 头在第一条文本落盘前
  就已含 FUNK

## 3. 对 panic.raw 观测的重新定性

boot3-20261106 capture: pram 窗口头 0x74 无 FUNK, 但窗口内 0x380 起有
0x720B zone-info 文本 + "Stackshot Incomplete Bytes Filled 240"。
按 §2 顺序, 真实 XNU panic 不可能"有文本无头" — 二者必配对。
两个候选解释:
(a) 旧 boot4 的采样窗口基址错位: 旧实现"只拷 scalar slots"(09cfea3 提交
    message 自证), 其 payload 未必从物理 pram+0 起, 头部区根本没被采样,
    我们对着错位窗口找 FUNK 当然找不到 — 与"0xa9/0xa37 是容器字段
    伪影"(5d5bbc2)同源一类错误
(b) 文本来自更早一次会话残留而非本次 panic — 被 §1 的 boot 清零否定
    (本次 boot3 启动即清零, 文本若是残留则活不过清零), 除非 §1 的
    /chosen property 缺失使清零没跑

裁决手段: 跑新 boot4(HEAD 的 debug_buf 三元组 + 边界校验拷贝, 另一会话
在途改动未提交), 采样窗锚定 _gPanicBase 物理值。若头 FUNK + 文本
pram+0x74 起 → (a) 坐实, 取证闭环; 若 /chosen 缺 property → 补 ADT。

## 4. 取证路线定论 (不变, 且更强)

XNU 完整 boot 会在 PE_create_console 清 pram; 二次 XNU boot 后读上一会话
日志物理不可行。唯一窗口 = panic 后、下一次 XNU 启动前, 由 LK 侧
(oem y35a panic stage + fastboot 读回)采样, readback_native.py 通道已实现。

verify: 容器内 sed pe_init.c:55-175/405-428/550-600, debug.c:261/352-362/860-895;
grep -rln EMBEDDED_PANIC_MAGIC → 4 文件; grep eph_magic= → pe_init.c:578 唯一写点。

## 5. §1 待核 CANDIDATE 核销 + 传输层复测 (2026-11-08 18:3x 心跳轮, 只读)

- `/chosen embedded-panic-log-size` **存在**, 非缺失: make_adt.py:36 生成
  (`struct.pack('<I',0x10000)`), 编译件 out/y35a/board.dtb grep 命中 1 次,
  出货件 out/y35a/ios12-boot3/boot3.img 命中 2 次。清零/读头路径的前提成立,
  §1 那条"缺 property 则全灭"的担忧解除 (VERIFIED, 本机实物)。
- 传输层复测: `fastboot -s efff9d92 getvar product` → `lk2nd-msm8916`,
  3ms 响应 (18:2x 时同命令曾无响应挂死)。健康窗口现在打开。
- **但关键件未就绪**: boot3.img manifest kernel_sha=5fd4e6b5… 即 18:16
  跑出 zone-init panic 的旧 build; 新 kernel.macho (20:02 编出) 尚未打包。
  package_native.py 当前在另一会话在途修改 (git M), 心跳轮不碰并行件。
  下一步执行序 = 等并行会话落定 → 重打包 → RAM boot → 抓带原因新 panic
  (采样窗锚 _gPanicBase; §2 已证头文本配对, 抓回即取证闭环)。

## 6. §5 事实盘 20:5x 心跳轮复测: 出货件已重打但内核出处断链 (只读)

§5 那段"关键件未就绪"已过期, 且其点名件已改名搬家, 逐条对盘更新:

- **重打包已发生**: out/y35a/ios12-boot4/boot3.img 与 manifest.json 的
  mtime 从 11-07 14:01 变为今日 ~20:2x (§5 复测时同为 14:01, 两小时内被
  并行会话重写)。新 manifest kernel_sha256=2c42056a…, 与
  kernel-packed.macho 实文件逐字节一致 (python 直读两文件互验),
  不再是 5fd4e6b5 的 zone-init-panic build。boot4/manifest 自洽。
- **但 2c42056a 的原始内核已不在盘**: 主机与容器全量 find (Nov7 19:00 后
  的 *.macho / *kernel*) 皆零命中; 主机 ios12-kernel.noctf 仍是 5fd4e6b5,
  容器 /work/ios12-kernel.noctf 是第三份 1af155f2 (11-07 08:49, 比主机还旧)。
  逐 16B 块比对: packed(2c42056a) 对主机件 490653/713937 块不同, 对容器件
  700181/713160 块不同——非同一 build 的重封装。"20:02 编出的新 kernel"
  (即 §5 等的东西) 疑似即 packed 的源, 但原始件已被清理, 无法从盘上复核
  其二进制来源 (CANDIDATE: 出处断链, 重打前需并行会话或用户给出 build 记录)。
- **r3 探针已入库**: out/y35a/readback-probe-20261108-r3/ (19:04,
  readback.json 2416B: adt/panicString=null, pramFirstBytes 全零——not-XNU
  对照件)。r2/r3 目录 untracked, 属并行会话在途件, 心跳轮不动。
- **设备与进程**: fastboot efff9d92 仍在场, 无在跑构建/打包/读回进程;
  package_native.py 与 build-xnu-4903-kernel.py 仍 git M (在途未落定),
  HEAD 最新一笔 4352cbb 为打包守卫修正, 今日 19:29 后无新提交。
- **下一可核事实 = 20:2x 重打的 build 记录落在何处 (manifest 有 hash 无出处)。**

## 7. §6 断链根因追踪: 2c42056a = 5fd4e6b5 的去日志兄弟 build (21:1x 心跳轮)

systematic-debugging Phase 1 逐层比对后, "出处断链"降级为 PARTIAL:

- 假设"移位头切片"被否: packed 对 host/容器两份 noctf 在 0..8192 全偏移
  无整段切片匹配; offset 0 仅前 136B 相同 (Mach-O 头+load command 公共前缀)。
- **字符串表差异定案**: __cstring 区 (0x14c00-0x15300) 集合 diff——
  host-only 三串: `>waiting == FALSE`、`z->async_prio_refill == FALSE`、
  `"zdestroy: Zone caching enabled for zone %s"` (0x14c30, len 44);
  packed 全缺这三串, 其后所有串 (vm_page_diagnose 起) 相应前移。
  缺失字节数 ≈45×2+余量, 与 184B 总长差同量级。三串均属 zone 销毁/
  异步补充的调试断言与日志 → **packed 是同一 XNU 源、关掉这些调试串所在
  条件分支 (assert/zdestroy 日志开关) 重新编译的 build**, 即 19:27 证据
  "容器构建中 (16:1x→20:02 kernel.macho)" 的 20:02 产物。
- 其余锚点串 (pe_init/embedded-panic/bootargs/sleh@0x2d370/WDT@0x2e64c)
  偏移逐一相同或同步移位, 证明代码基一致。
- **仍缺的一环 (CANDIDATE)**: 编译时用的开关/patch 记录未落 commit
  (native-phase-markers.patch 与两脚本仍 git M), 原始 kernel.macho 中间件
  已清理。重打/boot 前建议并行会话把该 flavor 的来源写进 manifest 字段。
- **对 boot4 的含义**: boot4.img 内核实为 panic build 的改动版而非同一件,
  18:16 的 zone_init_done panic 结论不自动适用于它; RAM boot 抓新 panic
  的证据价值不变。
