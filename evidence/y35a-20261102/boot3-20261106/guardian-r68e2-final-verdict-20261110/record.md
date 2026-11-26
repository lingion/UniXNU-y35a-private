# 守护 20:5x — r68e2 final.raw 判决解码: R68EPRE0 新鲜出现 = 本代首个正 XNU 写入; 死亡窗收窄至 MMU-enable 指令边界两侧

## 守护自纠(重要纪律记录)
首轮判读我把 slot56-63 按"carrier 线性映射"(body 0x102c0..)读, 全零后险些误判"publish 未达"——实际 report 按记录顺序布局, 56/57 在 handoff 窗 body 0x104c0, 58-63 在 publish 窗 0x104d0..0x10500(preflight:33 原文即如此)。与 Codex 反复防的槽别名混淆同类, 守护自踩, 已按 preflight 偏移重读, 下述为正确读数。

## 新鲜实测判定(Codex record 尚未写 final 段, 守护先行落账供对撞)
- 身份与新鲜度控制全过: final XNU2/CNTVCT 戳=517fd633…/0x1383eaad ≠ baseline(de4bf940…/0x28e03ad6e2); baseline slot16=PREMMU00 留存且无 R68EPRE0(控制合格)。
- **slot16 = R68EPRE0 新鲜出现(baseline 处为旧 PREMMU00)**。该字仅存在于 r68e2 patch → 本轮 XNU 真实执行了 MSR SCTLR 前的最后一条 store, 且 [x20] 基址在 MMU-off 状态下寻址正确。**x20 基址错候选(b)对 pre-SCTLR 段证伪。**
- slot56 SCTLRWR0 / slot57 ISBCOMP0: final 与 baseline 均零 → MSR 后首条 store 从未出现在任何代次。
- slot58-63(x16/x17/x9 快照+PUBL 对+FPSTOR00)全零; ptr-window 零; efrecord flag/ELR/ESR/FAR 零 → 更早的 fault 发布路径同样未达/未出版。
- 全 raw 差分仅四段: 戳/CNTVCT/**slot16**/0x10288(_BootArgs+8, 见下)。

## 边界判读(归 Codex, 守护只列存活假设)
死亡窗从"fault-publish 之前某处"收窄为 **MMU-enable 指令边界两侧二选一**:
(i) MSR 后首条取指即死(TTBR/TCR 翻译未就绪, 下一条 fetch abort);
(ii) 存活过 MSR, 但 **post-SCTLR 的 [x20,PA] store 死亡**——注意 slot16 的 store 成功只证明 MMU-**off** 时 PA 直写可用; MMU-on 后 0xa0b7c9c0 若无恒等映射, 同一条寻址式会从可用翻成 data abort。fault-publish 主嫌(物理指针 store)恰属此类。**分辨法: 下一条 post-SCTLR 指令改经 KVA 载体写 marker(如 kernel global 或 _BootArgs 窗内偏移), 若 KVA 路径出现而 PA 路径不出现 = (ii) 实锤。**
- 另: _BootArgs+8 值 r68d→r68e2 变 -0xf2(2512→2420, 皆内核 KVA 区)——写入者系 shim 的 boot-args.bin 每代重生成还是 XNU copy_boot_args, 归属未定, 不作 XNU 进度证据, 供 Codex 定名。

## 21:1x 追加 — 判决经权威布局复核成立(守护第二自纠: 复核脚本本身先错一次)
- 首版判读用"report_offset 直接当 raw 偏移"复核 → 读出 raw[0x4c8] 等"非零同值"系伪影——那是 PRAM 区字节(raw 0..0x10000 ↔ PRAM 0x95000000..), 与 carrier 槽无关。该伪影本身反证 PRAM 两次探针逐位稳。
- 修正为 raw = 0x10000 + report_offset 后, 按 manifest 权威 records(early-fault-record/handoff-witness/fault-publish-window 的 PA+size+report_offset 区间)映射: slot16=R68EPRE0 唯一语义差分 ✅; slot56-63 final=baseline=0 ✅; 全 raw 差分仍仅四段(戳/CNTVCT/slot16/_BootArgs+8)。
- 结论: 20:5x 判读与正确偏移一致(当时第二读法已用对 preflight:33 的 body 绝对偏移), 现经独立几何路径双确认。教训入档: 对撞手算的脚本要连基址假设一起对撞。
