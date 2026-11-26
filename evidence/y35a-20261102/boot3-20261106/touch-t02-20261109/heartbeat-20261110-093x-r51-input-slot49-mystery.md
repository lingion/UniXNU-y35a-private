# 心跳 20261110-093x: R51 输入落件 — fault-publish patch 四标记阶梯(FPA0/FPB0/FPT0/FPR0 → slot 56/57/58/59)精确兑现 r50b record 的三窗承诺; record 欠账全量重数 19→18(r50b 已收); 跨代悬案登记: slot49=0xfffffff00702f7fa 数值在 r39→r50b 各代表同一物理点恒定, 现 patch 树无写者

时刻 09:3x(09:34:56 实链)。HEAD=04897fa(本线顶)。设备
efff9d92 fastboot 空闲,无构建/烧写进程。零设备指令。

## 1. R51 输入可读(patch 09:32, 新第 14 件)

`native-fault-publish-witness.patch` 实读, 四标记阶梯全
物理直写(x20 基, 恒差 0x7c0 换算槽号):

    FPA0 [x20,#0x9c0]=slot56: KVA 已物化, 存 x16 低物理操作数
    FPB0 [x20,#0x9c8]=slot57: 物理目标就绪(store 前), 存 x15
    FPT0 [x20,#0x9d0]=slot58: 存算得的物理 carrier 地址 x17
    FPR0 [x20,#0x9d8]=slot59: `str x17,[x16]` 完成后标记

判读表(下代 final 到手即用): 56 零 → 死在 KVA 物化窗;
56 有 57 零 → 死在物理转换; 56/57 有 58 零 → 死在操作数
就绪→store 间隙; **56/57/58 有 59 零 → 实锤死在物理指针
store 本身(r50b 主嫌)**; 59 有 → store 后段, 前推。与
r50b record 尾节承诺("independent operand snapshots for
x16 and x17 plus pre-store and post-store physical
markers")逐项对得上, 兑现度=高。注意 r50b record 曾提
槽位 48/49+56/57, 实际落件用了 56..59 四点且 48/49 归
header 合同 — 微偏差, 归 Codex 账。

## 2. record 欠账全量重数(carryover 承诺兑现)

循环实查: 20261110 代缺 **12**, 20261109 旧夜缺 **6**, 总
**18**(090x 记 19 → r50b carrier record 09:12 收录, −1;
pointer-window 无独立 record 但其结论并述于 r50b record,
不另计)。085x 时代的 r49b/r50c-g 目录经再查确认不存在,
090x 勘误维持有效。

## 3. 跨代悬案登记(不猜, 只钉事实)

**slot49 恒值**: body 0x1c8(=物理 x20+0x988)读数
`0xfffffff00702f7fa` 在 r39/r40/r41/r42/r50b/rw 六件解码
中同值再现(本线全部亲解)。数值形态 = x22 基
(0xfffffff007004000)+0x2b7fa, 核 KVA 空间; 现 patch 树
唯一 0x988 写者是 header-adjust 的 HDRADJ00(ASCII 文本,
非数值)且 r39 时代该 patch 尚不存在 — **写者缺位**。可能
涉 boot shim 清零边界/留存页残值/未落盘旧写法, 本线不作
解释, 留 Codex r51+ record 或后续解码窗口定案。

## 4. 09:40 勘误(本文件 §1 判读表更新, append 不重写)

fault-publish patch 09:40 二次触线, 标记改名+语义调整:
四槽新布局 = **slot56 存 x16(算得目标地址快照)、slot57
存 x17(payload 快照)、slot58=`FPBEFOR0` 文字(操作数已存,
store 下一步)、slot59=`FPSTOR00` 文字(store 已返回)**。
原 FPA0/FPB0/FPT0/FPR0 四段阶梯作废为本二段+双快照形态。
判读表同步更新: 58 有 59 零 → 死在 `str x17,[x16]` 本身
(主嫌窗不变); 58/59 都有 → store 过, 56/57 值直接告诉你
当时用的目标地址与 payload 是什么(比旧版信息更强); 58 零
→ 死更早, 56/57 值界定断点。§1 阅读时以本节为准。

verify(本节): grep -E "//|str x1[5-7]" 实读 09:40 版全文
(改名 FPBEFOR0/FPSTOR00+双操作数 str x16/x17 亲见); 两
标记 movk 序列逐字节重算(行 17-20/24-27 实取): FPBEFOR0 =
46 50 42 45 46 4f 52 30, FPSTOR00 = 46 50 53 54 4f 52 30
30 — **均与注释名逐字符一致, 无 HDRLAOD0 类换位陷阱**;
四槽位号复算(0x9c0/0x9c8/0x9d0/0x9d8 −0x7c0 = body
0x200..0x218 → slot 56/57/58/59 ✓); store 本体 str x17,
[x16] 恰夹在 FPBEFOR0 写行与 FPSTOR00 写行之间(行 21/22/
28 亲验) — 58/59 对 store 的括夹是字面成立的。

## 5. 盘态

probe 三闸零收口(cpp/py 双 M 原样); 14 件 witness 类
patch untracked(fault-publish 新计, 但 r50b 系七输入逐
SHA 已入 record = 免疫模板在续); LOG/CURRENT 仍 M; 守护
龄 ~4.55d(<5.2 闸), 心跳 09:21 班即本轮, 保险丝 12:43;
GO 未回。下轮盯: r51 构建/实跑与判读表落地, slot49 悬案
是否被 record 认领。

verify: patch 全文 grep 标记/str 行实读(四写点+store 本
体亲见); 槽号 0x9c0-0x9d8 经 0x7c0 恒差手算(56/57/58/59);
r50b record 尾节承诺原文对读; 欠账双日循环计数(miss=12/
6 实跑); pw 无独立 record 实查; ls 目录 r50 系仅 carrier+
pw 两目录(085x 幽灵再查); unittest 上轮 09:0x 已 Ran 98
无触线不重跑; fastboot devices; pgrep 空; 六件 slot49 同
值=各轮本线解码记录对字 — 全部本轮或当轮新鲜执行。
作者: lingion <lingion@hrbeu.edu.cn>
