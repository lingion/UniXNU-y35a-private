# r7 三连捕获冻结内容裁决 + §6 自我证伪 (2026-11-09 06:0x 心跳轮)

## 0. 前置协议事实 (r6 README 实证, 本轮复核)

探针 stage 机制: 探针把 records 写进 0x859e0000 staging → warm reset 后
DRAM 保持 → 下一次 stage 读回拿到的是**上一次探针运行的产物**, 不是本次
PA 现读。r7 三连 (04:00/04:01/04:12) 若首帧 baseline 已是"上次探针"的冻结
staging, 三连互等就完全自然。r6 00:17 定案同样据此: 直接 stage 不经探针
= 读到 r6 探针残留, 与 boot3 是否跑到 check_for_panic_log 的判别绑定在
"探针残留是否被 boot3 抹掉"上, 不是 PA 直读。

→ **本文件此前 (0500/0520 两份) 把 r7 records 说成 "boot3 本次启动现读 PA"
是过强表述, 修正为: 是 staging 镜像, 反映"该 staging 最后一次被填充时"
的 PA 内容; boot3 每次都真跑了 zero+placement (未抹 staging 只说明它
没跑到 check_for_panic_log)。

## 1. 自我证伪: 0520 §6 "栈记录读错页" 不成立

boot3 segment_table 8 段目标 PA 全部 = 0xa0004000+voff (线性一致):
__BOOTDATA dest=0xa07a4000, _excepstack/_intstack voff 落位无误。
探针 PA 翻译正确。撤案。

## 2. 记录窗口尺寸伪影: "MISMATCH" 多数是邻位 RAM 溢出

REQUIRED 全局的 record size=128B, 但字段只有 8B(u32 者 4B):
[_panicDebugging+128] = 8B 本体 + **120B 邻居**。此前逐 u64 比对把
邻居字节当成本体判 "不匹配", 错误。首 u64 真值 (5fd4 世代 r7-post3):
gPanicBase=0 gPanicSize=0 debug_buf_base=0 debug_buf_size=0
debugger_panic_str 窗口=全零(且其 packed 初值本就是零) — 与
"boot3 未达 PE_create_console/debug_log_init" 一致, 与 XNU 运行时
写入矛盾消解。panicDebugging 首 u64=0x800000000100 非初值非清值,
待 8B-only 重判 (见 §5)。

## 3. __DATA_CONST 三窗口 "PLACE-MATCH" 的定性降级

_BootArgs/const/panic_str 与 placed image 相等, 在 staging 模型下有
平凡解释: staging 是探针最后一次填充时的 PA 拷贝, 而 boot3 每次都
placement 覆盖 image 字节 → 拷到 image 态毫不意外。**不再构成
"XNU 没运行" 的独立证据**; 也**不构成 "拷贝了 image" 的证据** —
信息量归零, 等 §5 重拍。

## 4. panic.raw (11-06) 与 r7 (11-09) 世代对比 — 唯一活证据线

- _BootArgs/const/panic_str 窗口: 逐字节全等 (两世代 staging 同内容)
- debug 三连 + 栈窗口: 不等。panic.raw 内含真 XNU panic 文本
  ("Zone info:", "Calendar: 0x00002c89...") — 11-06 那次 boot3 的
  panic 文本进入了 staging。
- r7 无文本、debug 首 u64 全 0: 与 "当前 boot3 死亡窗口在
  PE_create_console 之前" (r6 定案) 一致。

## 5. 0x380/0x720B 观测证伪 (本轮 python 实测)

boot3.img u32@0x380 = 0x0, panic.raw u32@0x380 = 0x0。"0x720B"
不在容器也不在捕获 — handoff §2 该数值系 11-07 轮转录错误
(真实 panic 文本从 0x3c2 "Calendar:..." 起, 前导恰有 0x0a0a 换行)。
5d5bbc2 当时把它类比 0xa9/0xa37 容器字段判为伪影, 结论方向对但
依据 (字节位置) 错, 现在以实测覆盖。

## 6. panic.raw 真身: 11-06 boot3 跑到了 pid 1

panic.raw 文本完整可读: "Zone info:" + 全部 zone map 行 +
"Panicked task 0xfffffff35f1bb230: ... pid 1: launchd" + 完整
lr/fp 回溯 + "** Stackshot Incomplete ** Bytes Filled 240"。
→ 11-06 那次 boot3 进入 XNU 深路径 (vm_fault 区域 panic on
launchd 启动), 与今日 "PE_create_console 之前死" (r6 定案) 是
两个不同死亡点, 非同一确定性故障重放 — r6 README 已述, 本轮
补实据。panic.raw 的 pram 文本在 records 区 0x3c2..0xb17:
旧探针把 pram 窗放在 records 尾部, 11-09 探针未采 pram 文本区
(0x10000 目的窗仅 Y35AXNU2 头+零), "无文本"是采样布局差异,
不是新 boot3 没写文本的证据 (它根本没到写文本的那步)。

## 7. 下一步 (按 r6 定案推进, 不重复)

a) 探针 record size 修成字段宽度 (8/4B) + 记录间 padding 显式化,
   消除邻位溢出伪影 (RED→GREEN, tests 先行)。
b) 相位标记 build (6e9a09d2 在途) + r6 --extra-pa _native_entry_trace
   系直读 — 判 boot3 死亡是否早于 arm_init。
c) 每轮 boot3 前必须先跑一次"清零探针"或换新 stage 区基线,
   否则 staging 冻结继续污染判读 (本轮教训入规)。

## 8. CNTVCT 见证重判 (07:0x 轮, 推翻 §0 过强部分)

91ab4a1 见证件实拍 (r7-witness-20261109/, 三 raw 逐字节 diff):
全 69632B 仅两处不同 ——
1. off 0x10 CNTVCT: baseline 0x301c463579 / probe2 0x350020c6 /
   post3 0x453784c — 互异且跨捕获递减 → 探针确实重跑 3 次, 且
   递减说明三段之间发生过掉电重启(CNTVCT 随电源周期归零重计)。
   §0 的 "staging 冻结/未重跑" 假设被见证件直接否定: 不是冻结 buffer。
2. off 0x10008 Y35AXNU2 交接头 kernel-stamp: baseline/probe2=6e9a
   (phase 探针头 0x8 也是 6e9a → 04:00 首帧由 6e9a 世代探针拍),
   post3=5fd4e6b5 = d7640a42 boot3 内嵌真 kernel 的 sha。
   → boot3 真运行并把自家 Y35AXNU2 头写进 debug 窗口, 头之后
   全零无 panic 文本 = 死于头写完、文本落盘前 (PE_init_panicheader
   已过, 第一条 kprintf 未到, 或 panic 字符串本身为空)。
3. 其余 records 区三帧全等 = 每次从 PA 重拷而 PA 未变 ——
   与 boot3 同死点重放完全一致。

修正 §0: r7 records 是 PA 现读 (探针重跑证实), 非上次探针残留;
r6 "00:17 直读 stage==r6-post-boot3 逐字节全等" 的既有观察
同样兼容 "PA 稳定" 解释, r6 定案 (死窗在 PE_create_console 前)
继续成立且被 §8.2 收窄: d7640a42 boot3 实际走到了 panic 头
初始化之后 —— 它是在 panic 中死的, 死因待下一条真文本。
下一发 RAM boot 的目标 = 带 §5a 字段宽度修正 + _native_entry_trace
extra-pa 的记录版, 直接读相位符号判 "谁触发的 panic"。

verify: 本文件全部比对为 python 只读实测 (segment_table 解码、
16B/8B pattern 在 5fd4/6e9a/noctf/boot3.img 搜索: panicDebugging
8B pattern 命中两镜像 fileoff 0x6cb187=__DATA 邻位, 非符号位);
lk-console-2.raw 复读; r6/r7 raw 逐字节 diff 全量。
作者: lingion <lingion@hrbeu.edu.cn>
