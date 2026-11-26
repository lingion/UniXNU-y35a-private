# 守护 18:0x — r68d 独立解码: 全 raw 零新鲜运行时写入(13 字节差异全为戳+见证)

前提实查(Codex 空闲、r68d 件齐、record 未写): boot/probe/final 全 OKAY; XNU2 final 戳 de4bf9407c994bee = r68d manifest kernel 前缀(实物对账); CNTVCT fresh。传输链与图像身份为真。

## 核心观测
- final-vs-baseline 差异字节共 **13 个**: 0x10008-0x1000f(8B, shim XNU2 戳换代)+ 0x10050-0x10054(5B, 探针 CNTVCT)。**carrier 与全部记录窗零新鲜写入**, 连 r68c 都有的 slot49 新鲜(header-adj store)在 r68d 也没出现。
- 标记字节扫描(正序, final+baseline 双件): PREMMU00@0x10180 与 ARGSLOAD@0x10188 存在但**两代同偏移同值=旧代留存**; SCTLRWR0/ISBCOMP0/MMUON000/LRPRE000/PRESSGRP **全 raw 零出现(连留存都没有)**。
- r68d 构建树前提在案: start.s 32 条 carrier store 指令, LRPRE000(:648)/FPBEFOR0(:690)文字在。

## 边界事实(判读归 Codex)
r68d 意图 = "checkpoint 做边界后首条指令, 预载值, 物理 x20"。实测两候选未分辨:
(a) 执行流比 r58/r68c 任何一代都早停(早于 ARGSLOAD 新鲜写入点, 即 early-fault store 窗都没到);
(b) r68d 的 carrier 基址(x20 独立捕获)整个错了, 所有 marker store 写到别处, DRAM 报告窗自然干净。
分辨法(供采纳): 让下一代的**第一条** marker store 之前先 store 一个 CANARY00 到 [x20] 首槽——若连首条都不出现, 而 PREMMU 前的任何既有 store 也全灭, (b) 权重升; 或在 LK 阶段先抓一次 x20 值进 header。另一独立线索: 本轮 slot49 零新鲜(它写者 start.s:877 在 r68c 是新鲜的), 说明 r68d 连 r68c 到过的点都没到过——倾向 (a), 但 (b) 未排除, 因 r68d 改过基址来源。

## 其余核对
- preflight 声称 offline: 105 测试/phase 9/build 13/extended 1/verifier ok — 本守护未复跑构建侧(设备与构建归 Codex 忙闲窗口), 仅解码实物证据。
- 心跳规④: cron 81442044 单条健康, 下轮 18:25。
