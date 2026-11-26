# 心跳 20261109-1045: R9 判词收编 — T0.2 manifest 显式声明模式,三闸齐绿;informative-boot 决策点在用户

时刻 10:4x。HEAD=0e269ec(本会话)+772f858(并行守护)。设备 efff9d92
在槽,零设备操作(在场检查)。守护双活(daemon 本轮即其唤起;
保险丝 12:43)。

## 1. 盘面确定性判据

- STAGE_BASE 字面仍 0x859e0000: fixer 读回迁移未落地(第三轮同判)。
- R9-READBACK-TRANSPORT-RECONCILIATION-20261109.md(mtime 10:20,
  Codex 属主)判词: 93b7978 几何对独立触摸探针有效且保留,但
  ①读回线 full 模式(payload 含 16K+32K 栈,装不进 0x1000 报告页,
  全 pram 复原会擦记录表)与触摸线场景不同,禁混用绿灯;
  ②Required-gates #1=每 manifest 自证 transport_mode。它点名的
  verify_readback_transport.py 已落盘(10:15, untracked)。
- 772f858(并行守护)把 informative-boot 决策点移交用户:
  读回迁移后抓 panic vs 先行触摸探针,二选一。

## 2. 交付(0e269ec,全在触摸线属主文件内)

probe_rmi.py 补四字段声明: transport_mode='minimal-boundary'、
pram_preserved=true(语义钉清: 零写成立,非快照舞步,mode_note
入 manifest)、report_bytes=0xbc4、staged_bytes=LK 延伸;gates 增
verify_readback_transport.py → 三闸(layout/transport/mode)全
ok:true,mode 闸 failures=[];image sha 不变 295241ce(纯声明,
codegen 判等——构建可复现性自证)。

## 3. 边界与待决

读回线模式设计(栈记录去向/破坏性契约)属 fixer+Codex,禁代做。
触摸线离线项全闭: 探针镜像 295241ce 三闸绿、几何 pram 零写、
LK 契约实测引用在手。设备执行等用户 GO(与 772f858 移交的
informative-boot 二选一同时待决——触摸探针先行不需要读回迁移
落地,这是它相对读回实验的独立价值)。给 GO 则按 README
Per-Experiment Record 立案后单发 RAM boot。

verify: grep STAGE_BASE 字面; ls -la R9/mode-gate mtime 实录;
容器重跑 probe_rmi.py rc=0 + manifest json 实读三闸全 true +
image_sha256 判等; git status 并行 M 件保留零卷入 — 全部本轮
新鲜执行。
作者: lingion <lingion@hrbeu.edu.cn>
