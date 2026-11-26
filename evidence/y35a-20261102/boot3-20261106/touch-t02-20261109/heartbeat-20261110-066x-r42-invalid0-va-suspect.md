# 心跳 20261110-066x: R42 观测集四代全同(停点锁死失效循环末条目); slot46/47 冲突未兑现(映射段 store 未达, 无覆盖可观察); 本线自勘 — 062x "INVALID0 写点 0x988" 误记, grep 实证 INVALID0 store 仍系 VA 算术(x14=x20+x22-x23)残留, "循环完成后 INVALID0 不达"的头号嫌疑浮出

时刻 06:4x(06:41:43 实跑)。HEAD=75a7a57(本线顶)。设备
efff9d92 fastboot 空闲,无构建/烧写进程。零设备指令。

## 1. R42 独立解码(第四代全同)

Codex 06:38-06:41 跑完 R42(final.raw SHA `a2f005bc…`,
baseline = R41 final `cdf3cd75…` 链式 ✓, 核前缀
facbcbe018a0532e)。**观测集与 R39/R40/R41 逐槽完全相同**:
25 文字哨兵 + x2=1 + 0xa3483ff8 + slot49。停点结论第四代
镜像复现: 失效循环最后条目处理点前后。record 未收(欠账
+1)。

## 2. 上轮登记冲突的实测裁决: 未兑现, 无需裁决

064x 登记 mapping patch 复用 [x20,#0x970]/#0x978 与
loop-state 数值槽撞车的风险。R42 实测: slot46/47 **仍是
数值**(x2/x1 原样) — 即若 R42 真应用了 mapping patch, 其
0x970/0x978 文字 store 没执行到; 其 0x8a0/0x8a8 映射段槽
(body 0xe0/0xe8)同样零。**冲突不可观察, 因为执行根本未到
映射段 store 点** — 该观察本身反证停点前于映射段(与 R41
时代"映射段 VA 零"一致)。风险登记转为"待执行到达时再验"。

## 3. 本线自勘 + 新头号嫌疑(重要)

勘误: 062x 正文写 "INVALID0 完成哨兵(写点 0x988 在 startup
patch)" — **本轮 grep 全 patch 树无任何 [x20,#0x988] 写点,
该说法证伪**。实读 native-startup-witness.patch 第 42-44
行: INVALID0 注释后紧跟 `add x14,x20,x22 / sub x14,x14,x23`
— **INVALID0 的 store 至今仍是 VA 相对写法**(x14 = 核 VA
减 PA), 从未被物理化。

新嫌疑(观察直推, 终证归 Codex): R39-R42 四代 x2=1 意味着
循环条目极少, INVONE00 命中后一轮即应收尾; 若循环**实际已
完成**, 紧接的 INVALID0 VA-store 在 pre-MMU 下**自 fault**
(同 R24 ARGSLOAD 伪零机制, 034x 实锤过同款), 则"INVALID0
永不出现"非停点证据, 而是**探针缺陷** — 真停点可能已在
循环之后。判别法: 下一版把 INVALID0 也物理化(x20 直写),
若其翻阳, 停点立推过循环完成; 若仍零且 x2 回写值出现, 
才是真停在循环内。登记为报回项(Codex 线, 文件所有权不碰)。

## 4. 治理与盘态

record 欠账 17 笔(R42 新增 MISS); 12 件 patch 仍全
untracked; LOG 六代回写仍 M; probe 三闸零漂移; 全套新鲜
`Ran 96 OK`; 守护龄 ~4.47d, 保险丝 06:43 班即将自然触发。

verify: python3 逐字节解码 R42 final.raw 64 槽+链式;
grep 0x988 全树证伪(空结果即证据); startup patch 42-44 行
VA 算术实读; slot46/47/0xe0/0xe8 零值实测; record R42
MISS; unittest discover 新鲜(Ran 96 OK); git status 计数
12; fastboot devices; pgrep 空 — 全部本轮执行。
作者: lingion <lingion@hrbeu.edu.cn>
