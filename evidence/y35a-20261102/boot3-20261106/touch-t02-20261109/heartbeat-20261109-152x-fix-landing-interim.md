# 心跳 20261109-152x: dump 窗修单已在 fixer 在途件落地(代码+py mirror 双同步, 逐字对上 144x/150x 检查点); 唯一尾巴=头部注释仍描述旧窗+伪引; 完成判定等 commit

时刻 15:2x。HEAD=a3ec315。设备 efff9d92 存活,本 turn 零设备指令。
150x 承诺复查项执行完毕。

## 1. 修单落地核对(git diff 只读实查, M 在途态)

`git status` 新增 M: **scripts/y35a/rmi_probe.cpp**(fixer 已接手)。
diff 逐项对账:

| 144x/150x 检查点 | 落地情况 |
| --- | --- |
| TLMM 目标字 8 脚×{ctl,io,intr_cfg,status} stride 0x1000 | ✓ `pins[]={12,13,18,19}×offsets[]={0,4,8,C}`,tlmm_target[16] |
| attn 双字语义(io vs intr_status) | ✓ attn_input=+0x4 / attn_status=+0xc 各 4 采样, 13*0x1000 基 |
| GCC 目标窗(0x6000..0x6024 + 0x45000..0x45008) | ✓ gcc_offsets[] 13 字全列, gcc_q5[13] |
| probe_rmi.py offset mirror 同批 | ✓ 'attn'→attn_input 0x90/attn_status 0xa0/tlmm_target 0xb0/gcc_q5 0xf0 |
| 零写纪律 | ✓ 注释明言 reads only, 结构替换未越界 |

预算: 旧 gpio[200]+gcc[512](2848B)→ 新 16+13+8=37 字(148B),
static_assert(≤0x1000) 工作区内必过(diff 未触该行) — **终验仍须
build/compile 后判, 本件不预判**。

## 2. 唯一尾巴(非阻塞)

rmi_probe.cpp 头注释 :16-17 仍写 "raw GCC window ..0x800 / pin bank
stride 4, facts y35a-facts.md:62" — 代码体已改, 注释未随迁, 且伪引
仍在(150x §1 裁决: facts 从未主张步距)。提修单方(我)顺路报回:
commit 前把 :15-20 三行改成新窗描述并删 facts:62 引。注释不影响
二进制行为, 但 T0.3 判读员会按注释找寄存器 — 留着是第二次误导。

## 3. 完成判定(留给后续心跳)

修单"完成"= rmi_probe.cpp+probe_rmi.py 进 git commit **且**容器
probe 编译过(static_assert/布局闸实跑)且 tests 计数同步。三项本轮
均未满足(M 态/未编译/未见 tests diff), 故本件只记 **interim: 方向
正确, 待落地三闸**。GO 未回不变, 冷读实验仍待逐实验授权。

verify: 本轮新鲜执行 — git log -5/log -1 -- cpp(=93b7978)/status
实跑(cpp 新入 M); git diff cpp 全 hunk 实读(:126-134 结构体/
:175-198 循环/attn 采样); git diff probe_rmi.py grep mirror 行;
sed cpp:15-23 注释实读; fastboot/docker 实况。
作者: lingion <lingion@hrbeu.edu.cn>
