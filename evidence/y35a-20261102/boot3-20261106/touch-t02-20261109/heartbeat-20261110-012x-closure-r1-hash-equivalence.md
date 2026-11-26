# 心跳 20261110-012x: corrected3 与 closure-r1 双构建产物逐字节一致(15:15 末编辑不改镜像), 全套计数 94→95(kernel contract 01:21 写入, 静默中断), probe 双 M 有收尾声明不记 stalled

时刻 01:2x(11-10)。HEAD=3a0f7bc。设备 efff9d92 存活,零设备指令。
上轮(164x/17:0x 档)工具调用两次被打断未落地,本轮并案收口。

## 1. T0.2 corrected bundle 对盘核验(全真)

板上 T02-CORRECTED-BUNDLE-20261109.md 声明三 offline 闸全绿、
镜像可由工作树源重产。本轮实核:

- corrected3 三件盘上 SHA-256 与文档逐字节一致
  (image 7a4b8e43 / manifest 204f8708 / probe.bin 5fb40cd3);
- 源钉地址在 cpp 工作树实存: TLMM 引脚 ×0x1000 步距
  (GPIO12/13/18/19 ctl/io/intr_cfg/intr_status),
  GCC+0x6000..0x6024 + 0x45000..0x45008,QUP5 base 0x078b9000;
- 旧错证(步距 +4 广Dump、错误 ATTn 采样、GCC 窗截短)确认已被
  在途 diff 功能性替换(非注释改动: 双 M 内容是 collector 重写
  + REPORT_BYTES 0xbc4→0x124 + CCC_OVERRIDE_OPTIONS 环境隔离)。

## 2. 构建时序疑点: 用字节一致性裁决, 不凭 mtime 排序

疑点: corrected3 目录文件 mtime 14:57 **早于** cpp 最后写入
15:15 —— 按 mtime 排序产物似乎漏掉末次编辑。

裁决证据: 发现第二构建目录 `rmi-probe-20261109-closure-r1`
(16:01, 晚于 15:15), 其 image/probe.bin/manifest 三件哈希与
corrected3 **逐字节相同**。即 15:15 的编辑对产物无影响
(或闭包重建即末次固化), 板上"从工作树可重产"声称成立。
macOS objdump 无 aarch64 反汇编能力, ELF 反汇编 witnesses 这条
路径本机不可行, 已改用哈希对比, 记此防后人重复尝试。

## 3. probe 三闸盘点(闸③最新触线是 fixer 活着的最强信号)

- 闸①(cpp/py+contract 同批 commit): 未过 — 双 M 持续,
  py+contract 最后触线 11-09 14:54, cpp 15:15;
- 闸②(容器编译): **已过**(板声明+双构建目录盘上实证);
- 闸③(contract 测试入库): 未过, 四件 contract 全 untracked:
  probe_rmi 3 / kernel_build **9(昨夜为 5)** /
  phase_instrumentation 4 / readback_transport 4。
- **静默裁决**: 板上 T02-CORRECTED-BUNDLE 即收尾声明 → 按规则
  ">2h 静默**且无收尾声明**再记 stalled" — 不记。且 01:21
  test_kernel_build_contract.py 刚被写入, 在途线昨夜活跃,
  16:2x 那轮观察到的 ~70min 静默是其转向他线(R20/device-run
  整夜)而非停摆。

## 4. 全套计数变化 94→95

- 01:0x 实跑: Ran 94 OK(构成: 提交树 75 + untracked 四件
  3+5+4+4 = 19, 75+19=94; kernel_build 当时为 5 条);
- 01:2x 实跑: **Ran 95 OK**;
- 逐文件分解(01:22 新鲜): capture_format 12 + capture_layout 6
  + kernel_build **9** + native_pack 17 + phase_instr 4 +
  probe_rmi 3 + readback_names 40 + readback_transport 4 = 95。
- 裁决(非推测): 单文件之和恰等全套数 → tests/ 无隐藏套件;
  kernel_build 文件 mtime 01:21 且板记昨夜为 5 条, 01:0x→01:2x
  之间 +1 只能落在该件(5→6 时点我无逐条实测, 但 94=75+19 的
  19 分解与 01:0x 时 probe_rmi 3/readback_transport 4/
  phase_instr 4 均为板上旧值吻合)。收口时预期: 四件入库后
  提交树计数跳至 95 口径附近。

## 5. 盘态

- R20 device-run 已完成(新 commit 086c80b/256e3e5: 负观测落档,
  kva-carrier patch 找回 e466e02) — 他线整夜推进, 本线无冲突;
- GO 未回; 四步序不变; untracked 41 件(多为 docs/coordination
  新审计文档与 evidence, 所有权在他线, 不动);
- 守护 12362354 龄 4.20d(换班闸 5.2d 未到), 保险丝 5f873c8d
  昨夜 00:43 报 guard ok。

verify: git log/status 实跑; shasum -a 256 三产物×两目录
逐字节对比; git diff -U0 双 M 功能性分类; ls -la mtime 两组;
python3 -m unittest discover 两轮新鲜(94 OK → 95 OK) +
逐文件单跑计数 8 项; fastboot devices; 本文件落盘即 commit。
作者: lingion <lingion@hrbeu.edu.cn>
