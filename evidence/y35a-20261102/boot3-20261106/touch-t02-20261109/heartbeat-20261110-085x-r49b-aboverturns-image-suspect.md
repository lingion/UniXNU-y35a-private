# 心跳 20261110-085x: R47/R49 传输失败根因翻案 — r49b 用与 r49 逐字节同一组三件输入(核 f2a7c015/boot3 4c40962b/probe b041cfd4)完整成功, 镜像嫌疑证伪, 宿主 USB 重枚举间歇性实锤; r50 修复链三代跑通; 全套 98(+2 落点钉死)

时刻 08:4x。HEAD=c62b621(本线顶)。设备 efff9d92 fastboot
空闲,无进程(08:45 实拍)。零设备指令。

## 1. 翻案主证: 同字节输入的失败/成功 A/B 对

时间线(Codex 复工后全程目录/日志/record 实读):

- 08:22-23 header/mapping 挪槽修复落 patch(084x 已录);
- 08:24+ r50 系列反复: r50b 构建、r50c(核 6a475761)
  **boot3+probe 均 Sending/Booting OKAY 后等 fastboot 超时
  放弃**(无 final), r50d(核 20d14252)同型超时;
- **08:31-08:40 r49b**: 弃新构建, **直接复用 r49 的三件
  原输入**(record 明言"existing r49 kernel, boot3, and
  probe images": 核 f2a7c015、boot3 4c40962b、probe
  b041cfd4 — 与 075x 我记录的 r49 失败三件 SHA **逐字节
  同值**)重跑: baseline OK → boot3 OK → probe boot
  **两次发送**(第一次后设备未回, 重试即成)→ stage OKAY
  + 783ms 等待 → get_staged **OKAY 69,632 字节完整**;
- 08:34-08:41 r50e/r50f 修复版核三代连跑(boot/probe/
  stage/get 全 OKAY, final 69,632 完整) — 但 r50f 用
  **新 probe e4280074 + boot3 56a10730 + record 内核
  SHA(5a138871)与盘上 kernel-packed(4150a57a)不一致
  待 Codex 对账**, 故 r50 系成功不能单独归因修复;
- 08:43 r50g 构建中。

**裁决(推翻本线 074x/075x 旧判)**: 同一组字节输入,
07:52 全挂(e00002ed×2 + 空壳), 08:40 全成 — 失败与镜像
内容**无关实锤**。根因 = probe boot 引发的设备重枚举与
宿主 USB 栈/轮询时序的**间歇性窗口**(假设 2 升为实锤,
假设 1 证伪); r50c/r50d 的"等 fastboot 超时"同源(且 Codex
自己的 boot-probe 双发日志显示第一次也可能没回 — 重试
策略即解)。**连带修正**: 084x"镜像嫌疑随 r50 实测坐正"
的预备判词作废; 挪槽修复(R43 承诺)仍是真实且必要的
输入卫生改进, 但与传输病无关。给用户的物理侧建议升级:
若再发, 换 USB 口/线可直接验证宿主栈假设。

## 2. r49b 数据价值声明

r49b final.raw(旧输入版)哨兵读数 = R39/R40 口径的第五代
复现件; r50f final.raw = 挪槽新几何(HDR 链 0x980-0x990 +
0x970/0x978 归还)的**首个可解码件**。两件的逐槽解码若
执行边界推进(HDR 链出现文字/INVALID0 变化), 将另立专档;
本轮先钉翻案, 解码下轮做(r50g 在跑, 设备可能再进窗口期)。

## 3. 盘态与账目

- 全套新鲜 **`Ran 98 OK`**(+2 落点钉死: kernel_build
  10→11(mtime 08:26, 与挪槽契约同批) + phase_instr
  4→5); 构成 75 提交树 + 23 untracked(11+5+3+4);
- probe 三闸: **无收口** — cpp/py 双 M, probe_rmi
  contract untracked, 最后 commit 仍 93b7978(昨日 09:57);
- LOG 仍 M(r49 段 07:54 至今未 commit); 13 件 patch 仍
  untracked; record 欠账 18 未变(r49b/r50 系已随跑随收);
- r50f 的 record/盘上核 SHA 不一致点已登记(等 Codex 对账,
  不代查容器);
- 守护龄 ~4.53d(<5.2 闸), 保险丝 next 12:43, 心跳正常。

## 4. 下轮盯点

①r50f 逐槽解码(新几何首件; 预登记判读表: 0x970/0x978
应回数值系 x2/cursor, 0x980/0x988/0x990 为 HDRLOAD0/
HDRADJ00/L1ALLOC0 字面即真值(084x 重算已修), 0x990 若现
L1DONE00 系 mapping 先写后 L1ALLOC0 覆盖链); ②r50g 终态;
③LOG/record 入库是否补; ④传输再发时用户物理侧动作。

verify: r50b/c/d/e/f/g + r49b 七目录全量 record/log 实读
(三轮 record.md 全文, boot/stage/get 日志逐行, 错误码与
OKAY 链亲见); r49b 三件 SHA 与我 075x 记录逐项对字; 盘上
r50 kernel-packed sha 实测(4150a57a vs record 5a138871
不一致点实拍); python3 逐目录 raw 尺寸/哈希实测; unittest
discover 新鲜(Ran 98 OK)+ 四 contract 单跑分解(11/5/3/4);
git log probe 历史; pgrep r50g 构建实拍; fastboot devices —
全部本轮执行。
作者: lingion <lingion@hrbeu.edu.cn>
