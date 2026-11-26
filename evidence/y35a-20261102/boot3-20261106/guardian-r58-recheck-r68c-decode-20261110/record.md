# 守护 17:5x — r58 声称复核为真 + r68c 独立解码 + slot49 悬案根因定位

全程离线零设备(r68d 正在跑,未碰 fastboot)。

## r58 record 四声称独立复核: 全部为真
boot3 3f60dacce5bd753f / probe a9f64d86aa2f627f / final dcf6f27f44958f41 实物逐位吻合。解码: slot38-40 三标记在位, 其中 39/40 为 FRESH(baseline 零→final 非零), 38 系留存; 高窗 0x10480..0x104c0 非零字节数 0; 全 raw 差分仅戳/见证/0x10238-0x10248 三段。r58 record "已过 INTSP000+link adrp/pageoff, 停在首个高偏移 carrier store 前" 判定与实测一致, 采信。

## r68c 独立解码(Codex 未写 record)
- 传输真: XNU2 final 戳 04fb2763b5a547c1 = r68c manifest kernel 前缀; CNTVCT 新鲜。
- 观测: 与 baseline 差异仅三段——戳、见证、**slot49(0x7032604→0x7032512, 本轮唯一新鲜运行时写入)**。slot4-47 全 residual; 高窗口(含 fault-publish 窗)零。
- 判定: r68c 停在比 r58 更早的位置(r58 尚有 slot39/40 FRESH, r68c 连 38-45 段都无新写入)。若 r68c 意图是修高偏移 store, 则修复代次反而回退——停在 link adju 段之后、LR 标记段之前。等 Codex 构建意图说明。

## slot49 跨代悬案根因定位(093x 起留账, 现结)
写者 = patches/xnu/native-header-adjust-witness.patch:28 `str x15, [x20, #0x988]`, r68c 构建树 start.s:877 实证在案。"同值六代再现"因同 patch 确定性写同一 header-adjacent KVA; "r51d 曾变 32604→32512、r51g/i 恒定、r68c 又变回 32512→…→2512" 因不同代核 text 布局漂移, 写的值本来就是随镜像变的地址。非幽灵写者, 属已声明 witness; 建议 Codex record 归档销案。

## 17 连投心跳根因
积压追平所致(会话忙时 */20 cron 照常入队), 非 cron 重复: scheduled_tasks.json 实查任务数=1。已合并处理。
