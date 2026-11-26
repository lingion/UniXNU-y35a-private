# 心跳交叉验证 00:1x (2026-11-09): f1 r6 前后两张 retained 快照 0 字节差异——boot3 本次运行对 retained 窗零写入;marker 自衰减实锤(旧写 Y31ARD 1,2bit 翻转,新写完好);r4→r6 36min 163bit 与 23:16 预测曲线同型

f1 在途(00:05/00:07 r6 两文件落盘,readq 仍未跑,livedram-readq.log 还是 23:34 旧内容)。
本会话零设备接触,仅对已落盘文件做只读差分。

## 实测

| 对比 | 时长 | 差异 |
|---|---|---|
| r6-baseline 00:05 → r6-post-boot3 00:07 | 2min + boot3 全程 | **0 字节** |
| r4 23:29 → r6base 00:05 | 36min | 163 字节 / 163 bit(每字节恰 1bit,散点) |
| panic-direct 23:04 头 vs Y35ARD01 标准 | ~100min 滞留 | marker 翻转 2bit → `Y31ARD 1`(b[2] 5→1, b[6] 0→空格) |

## 三条推论

1. **boot3 对 PRAM retained 窗零写入**(post==base 逐字节相等)。结合 §10.9-10.13:
   本轮 boot3(OKAY+70s 回 fastboot)之后,0xa0915000..0xa0926000 无任何新内容。
   panic 路径若到达且 pram 就绪必写正文——现在连 1 字节都没有。
   这把 README-r4 候选 (c)(panic 早于 debug_log_init)与 (a)(kernel 没跑起来)都保住,
   但**基本排除 (b) 的弱形式**(pram 映射成功但 check_for_panic_log 没被调):若是这样,
   至少 panic_save_pram_log 该落字。裁决仍系于 readq——注意 readq 坐标旗标
   (aff138e:0xa026e0a0 成功态=0x140007ee 非 codeword)。
2. **衰减率与饱和曲线吻合**:23:16 心跳实测 28min 312bit,本轮 36min 163bit——
   同电源周期内弱 bit 先翻完、后段变慢,与 DRAM retention 统计一致。
   record-table 区也有 3bit 翻转(探针自写伪影同样在衰减,进一步证明那些不是新证据)。
3. **marker 对照是本盘最干净的"旧写衰减 vs 新写完好"样本**:同一 retained 窗,
   23:04 抓取时 r3 探针旧写的头已翻 2bit,23:29/00:05 探针新写的头两次抓取完好——
   衰减只吃滞留时间,不吃写入者。任何"载体全 0 或残破"的解读先过这把尺子。

## 未决顺延

- readq 三分叉裁决(f1 窗口)。
- r6 post 若与后续 r7 出现非零差 → 说明 boot3 有时能写入(间歇性),另立观察。

verify: sha256(r6 base=post=995333535c9f2c4f…,逐字节相等);bit 级差分脚本
1bit/字节确认;marker 逐位对照 Y35ARD01;正文窗非零数三文件对齐(3995/3995/4116)。全程只读。
