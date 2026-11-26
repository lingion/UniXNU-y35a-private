# 心跳 20261109-1025: T02-PROBE-AUDIT 响应 — 判词系 7e33199 快照,Required-correction 已被 93b7978 全项满足(实测)

时刻 10:2x。HEAD=54401a0。设备 efff9d92 fastboot 在槽,零设备操作。
fixer 生成器迁移仍未落地(readback_native.py STAGE_BASE 字面仍
0x859e0000,committed)。find -newermt 25min 空 = 各线静默轮。

## 1. 判据(确定性核对,非主观)

Codex 落了 docs/coordination/claude-codex-sync/T02-PROBE-AUDIT-
20261109.md(mtime 09:50),定罪"探针报告仍写 pram、Y35A_REPORT_BASE
只在注释不在代码路径"。逐条比对代码时间线:

- 该判词的事实基 = 7e33199(09:4x): 彼时确有
  `-DY35A_STAGE_BASE` 单址、`rep=(Report*)STAGE_BASE`——判词当时成立;
- 93b7978(10:0x,晚于 audit mtime)即该 audit 的 Required correction
  本身: 双址派生传入、报告指针与刷洗环全用 REPORT_BASE。audit
  是对已闭合中间态的滞后反应,非新缺陷。

## 2. 对 Required correction 逐项实测复核(HEAD 54401a0)

| audit 要求 | 现状(本轮新鲜证据) |
|---|---|
| 派生并传两址 | probe_rmi.py:140 `-DY35A_REPORT_BASE={rb} -DY35A_PRAM_BASE={pb}`,rb=parse PANIC_LOG_DEST, pb=parse make_adt pram reg |
| 报告指针用 report base | rmi_probe.cpp:151 `(volatile Report*)REPORT_BASE` |
| 刷洗环用 report base | rmi_probe.cpp:236 `dc civac,(REPORT_BASE+o)` |
| manifest 记两值 | geometry.pram_base=0x859e0000 report_pa=0x859f0000 stage_source_pa=0x859e0000(json 实读) |
| 布局闸查报告区间 vs pram | gates.layout ok:true(写区间 0x859f0000..0x859f0bc4,实跑) |
| 独立探针免快照、报告出 pram | 已如此设计,二进制 objdump `movk #0x859f,lsl#16` 命中 1 处 |

命名差一处,是设计差异非缺口: audit 要 `-DY35A_STAGE_BASE`(LK 源
约定),本线传 `-DY35A_PRAM_BASE`(make_adt 的 pram reg,即"禁写"
对象)+ manifest 单列 stage_source_pa(readback STAGE_BASE 派生)。
两概念在现值重合(0x859e0000),但语义正交: fixer 若把 STAGE_BASE
迁离 pram 而 pram 不动,"禁写 pram"断言必须跟 pram 走,上传范围
必须跟 LK stage 走——拆开才对迁移免疫。C++ static_assert
`REPORT_BASE >= PRAM_BASE+0x10000` 直接钉死。

## 3. 台账动作

LOG.md 追加响应条目(append-only 规矩);LOG.md/CURRENT.md 的他人
在途 M 态照旧不代提交,本证据文件只引用。构建件不变: image
295241ce 即当前 HEAD 源码的产物,无需重打(判据: probe_rmi.py/
rmi_probe.cpp 自 93b7978 后零改动)。

## 4. 边界

本轮零设备操作、零 fastboot、未 boot、未写分区、未 push。触摸线
离线可推进项至此全闭: 下一动作=等 informative-boot 三前置之
"用户 GO"(38825c4 立案);给 GO 则按 README Per-Experiment Record
先立案(问题/假设/镜像 sha 295241ce/预期/停止条件)再动设备。

verify: git log、grep STAGE_BASE/PANIC_LOG_DEST 字面、find
-newermt "25 min ago"(空)、ls -la audit mtime、grep 双址入
probe_rmi.py/rmi_probe.cpp 行号实录、容器内 objdump grep -c +
manifest json 实读(gates 双 true, geometry 三址)——全部本轮
新鲜执行。
作者: lingion <lingion@hrbeu.edu.cn>
