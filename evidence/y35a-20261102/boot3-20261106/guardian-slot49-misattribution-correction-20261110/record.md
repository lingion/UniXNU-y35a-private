# 守护 20:0x — 自我更正: "slot49 悬案销案"误归因撤回 + r68e2 真 carrier slot48/49 捕获缺口报告

## 更正 1(守护侧,影响 17:5x 结论)
17:5x 我把 final.raw body 0x10288 的值(0xfffffff007032512/604 系)命名为"carrier slot49"并据 start.s:877 `str x15,[x20,#0x988]` 宣布悬案根因定位销案。本轮三证据复核发现观察点身份错:
- roff 0x288 落在 `_BootArgs` 记录区间(roff 0x280..0x290,size 16),即核全局 `_BootArgs`(VA fffffff0070ce6f0,nm 实证)拷贝的 +8 字段, 与 LK shim 的 args 页无关。
- 真·物理 carrier slot49 = args_pa+0x800+392 = 0xa0b7c988, **不在任何捕获窗内**: efr 窗 0x800..0x980(止于 slot47), mapping-carrier 窗自 0x990 起。
- 因此"header-adjust-witness 是 slot49 值来源"判据链断, **销案撤回**; 该值随代次变(604↔512)的事实保留, 新解释候选: _BootArgs 拷贝 +8 字段由核 boot_args 初始化路径写(下轮核 boot.h 字段表定名, 不猜)。

## 更正/缺口 2(Codex 侧, 影响其 adjudication 条目)
Codex "r68d freshness adjudication" 声明 "Slot 49 is a fixed HDRADJ00 marker, not expected to vary with text layout" ——按当前 manifest, 0xa0b7c988 不被捕获, 该声明**无读数来源**; 若其判读实际引用了 roff 0x288 区间, 则是把 _BootArgs 拷贝字段读成 carrier marker(与我 17:5x 同款混淆)。同时他"PREMMU00/slot41-44 跨代同值"的观察与我实测一致(窗内成立)。他撤回两条旧结论与守护 18:2x 方向吻合, 好评。

## r68e2-final 就绪度(新鲜实测)
19:58 打包; kernel_sha256=517fd633… boot3/probe 一致; fault-publish-window 0x9d0..0xa00 在, 判决槽 56-63 全覆盖; 全套 111 OK(19:4x 复跑)。**尚未上机**(evidence 无 r68e2 目录, 设备 fastboot, 无进程)。判决三态判读表已在案: R68EPRE0(efr 窗内)=清零+到达双证; PUBL 对=发布 store 生死; slot58-60=操作数实值。
