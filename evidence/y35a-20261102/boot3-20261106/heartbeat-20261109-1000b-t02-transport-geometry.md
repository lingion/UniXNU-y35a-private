# 心跳 20261109-1000b: T0.2 探针几何采纳 transport-audit 候选 — 零写 pram,双闸全绿(触摸线布局闸转绿)

时刻 10:0x(本会话第二轮,补 38825c4 之后)。HEAD 序列: 38825c4(并行
guard informative-boot 三前置立案)→ 93b7978(本会话几何收编)。设备
efff9d92 fastboot 在槽,零设备操作(在场检查 only,遵台账并发禁令与
逐轮授权规矩)。

## 1. 盘面确定性判据(实跑)

- readback_native.py STAGE_BASE 仍 0x859e0000(committed 态)→
  fixer 生成器迁移未落地,判据不变。
- 新增 Codex 属主两件: CAPTURE-TRANSPORT-AUDIT-20261109.md
  (候选几何: pram 快照 0x95000000 + 报告 0x859f0000 + LK
  stage(0x859e0000,0x11000) 实测契约含 aboot/fastboot.c 源引用)与
  verify_capture_transport.py(全共享图闸)。ownership 规矩: Codex 持
  审计+闸, fixer 持生成器, 触摸线按候选自持探针。
- 38825c4 立案的 informative-boot 三前置(布局闸绿+无并行
  fastboot+用户 GO)与台账 Next-Work #0 并行有效; 触摸线本轮把
  "布局闸绿"前置在自身几何上做成,不代答读回线。

## 2. 交付(93b7978)

rmi_probe.cpp + probe_rmi.py 几何改造:
- 报告基址 = readback_native.py PANIC_LOG_DEST 字面解析
  (0x859f0000,pram 之上),探针写区间 0x859f0000..0x859f0bc4,
  **pram 零写字节**——defect-1 对触摸线从"容忍"变"根除";
- C++ 双 static_assert: REPORT_BASE >= PRAM_BASE+0x10000;
  sizeof(Report) <= 0x1000(LK stage 延伸只留 pram 上 4 KiB,
  报告长大必须同步 lk-stage-size 变更,断言里直说);
- 全部地址派生(报告基/pram 窗/LK stage 延伸/snapshot 候选各从
  readback_native.py、make_adt.py、AUDIT 文档字面),迁移自动跟随,
  -D 缺失故意编译失败;
- manifest.geometry 按审计"Required gates"命名
  (pram_snapshot_pa/report_pa/stage_source_pa + 尺寸),
  pram_snapshot_pa='not_written_by_this_probe'(独立探针无需舞步:
  无 XNU 并发写 EPH、探针不 reset、wfe 终停);
- 双闸每构建跑进 manifest.gates。

## 3. 构建验证(真实输出)

- 容器重打绿: image sha256 295241ce…, probe.bin 3864B,
  llvm-nm -u 空;objdump `movk w19,#0x859f,lsl#16` 证新基址入码,
  entry.S 栈 0x859df000(pram 下派生)。
- layout 闸 ok:true(写区间与 pram 零交,触摸线首个双绿)。
- transport 闸 ok:true(pram/lk_stage/snapshot/report/scratch 全图,
  reserved RAMDisk 域 0x90aea000..0x933ea000 无撞)。
- 读回线自己的布局闸仍红(records 全 overlap)——那是 fixer 的
  迁移作业,与本线无关,禁代做。

## 4. 边界与下一步

探针设备执行仍闸: ① 三前置之"用户 GO"未得; ② 台账 #0(读回线
stage 迁移)不关触摸线的 boot(独立探针不采样 pram),但一次 boot
一个实验的规矩下,RMI 身份实验须单列提案进 LOG/CURRENT 再请批;
③ 本轮零 fastboot 操作。下一轮: 若用户给出 RMI 探针窗口授权,按
README "Per-Experiment Record" 先立案(问题/假设/镜像 sha
295241ce/预期/停止条件)再动设备。

verify: git log/status、STAGE_BASE 字面 grep、容器重打全链 +
nm/objdump/entry.S、双闸输出实录、manifest.geometry 比对审计
Required-gates 命名 — 全部本轮新鲜执行。
作者: lingion <lingion@hrbeu.edu.cn>
