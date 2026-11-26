# 心跳 20261110-068x: R43 两击目击 — 首次捕获(06:49)与 retry 捕获(06:50)在 slot46/47 差一个数值对(1+光标 vs 零), 064x 登记的槽复用冲突兑现为脏测量; record 自判"非清洁测量"+下一步离线分槽 = 我方预言的设计级承认; 夜间首起真传输故障(USB disconnect)按停规处置

时刻 06:56。HEAD=adbbcdc(本线顶)。设备 efff9d92 fastboot
空闲,无进程。零设备指令。

## 1. R43 双捕获独立解码(两 raw 全解)

Codex 06:48-06:52 跑 R43(mapping 段物理化哨兵), record.md
已随跑收(06:52)。record 欠账现值 = 064x 全量清点 16 笔 +
R42 新缺 1 笔 = **17 笔**(R43 已收不计)。

两击形态首次出现:

**首次捕获 final.raw(SHA `edc07c34…`, 06:49, 仅 boot3 后
stage 上传 — 时间线在 boot-probe 之前)**: 25 文字哨兵 +
x22/x23 + **slot46=1 / slot47=0xa3483ff8** + slot49 全在。

**retry 捕获 final-r43-retry.raw(SHA `e44c15f6…`, 06:50,
record 指定权威件)**: 25 文字哨兵 + x22/x23 + slot49 同前,
**唯 slot46/47 = 零**。

两 raw 其余逐槽一致(本线双解码对比), header 核前缀均
aa23a4bb(R43 核)。

## 2. 裁决: 064x 预言的槽冲突以"脏测量"形态兑现

record 原文自判: "retry's slots 46 and 47 are zero. The
mapping call pre/return witnesses are not a clean
measurement because those slots are shared by the mapping
witness experiment and the loop-state carrier" — 与 064x/
066x 两笔登记("mapping patch 复用 [x20,#0x970]/#0x978 与
loop-state 数值槽撞车")完全对上。**首次捕获里 x2/cursor 值
在场、retry 里消失**的差额 = 同一物理槽被两实验先后写的
直接指纹。因果细目(为何首击有值而重跑无)留 Codex 分槽
重跑终裁, 本线只钉观测不作缺陷指控。

**下一步已定(Record 尾节)**: 离线给 VPPRE/VPCALL/KVPRE/
KVCALL 分独立槽 + 移除 loop-state 复用, 重建并 Mach-O 验证
后才再上设备 — 分槽版 R44 将是 slot46/47 语义的清洁重测。

## 3. 停点现状(两击合并读)

- 25 文字哨兵 + INVALID0(slot19)零: 与 R39-R42 同; 停点
  表述按 record = "先于清洁的 V=P mapping return 目击",
  与 066x 头号嫌疑(INVALID0 VA 自 fault, 真停点或在循环
  后)不冲突 — **066x 报回项 record 未回应, 保持开放**;
- 停点结论至此第五代镜像稳定。

## 4. 传输故障目击(夜间首起, 处置合规)

record: 首击在 send probe 时 **USB disconnect**, 该击不作
运行时结果; 设备重枚举后 retry。旁注: 06:49 首 final.raw
的存在与"仅 boot3 段捕获"时间线自洽(探测未跑成)。本线
015x 规则("设备瞬离先查他线实跑")在 Codex 侧同样生效:
其 stop-on-disappearance 序列按预检规则停-重-疑, 未把故障
击当 XNU 证据 — 纪律面收口良好。

## 5. 盘态

probe 三闸零漂移; 全套 Ran 96 OK(06:41 轮实测, 本轮无触线
不重跑); 12 patch 仍 untracked; LOG 仍 M; 守护龄 ~4.47d;
GO 未回。下轮盯: R44 分槽重跑(slot46/47 清洁读数),
INVALID0 物理化是否落地。

verify: python3 逐字节解码双 raw(edc07c34 + e44c15f6 各
64 槽全枚举, 差额=slot46/47 唯一); ls -lat 时间线双 log
文件实读; record.md 全读(自判原文逐字引); fastboot
devices; pgrep 空 — 全部本轮执行。
作者: lingion <lingion@hrbeu.edu.cn>
