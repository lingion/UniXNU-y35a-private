# 证据旗标 00:5x (2026-11-09): check_for_panic_log 真实位置+行为从容器源码钉死——bzero 无条件,PE_create_console 第一行执行;连带推翻"残留完好⇒未到 create_console"推理(前提"残留存在"本身不成立:探针 stage 写从未落 DRAM,§10.12 未解 23:0x 正是此洞)

## 一、源码事实(容器 /work/xnu-4903 全文 grep,首次完整核实)

handoff finding #1 自称 CANDIDATE,现修正 + 加强:

1. `check_for_panic_log()` 在 **pexpert/arm/pe_init.c:73**(static;非 handoff 的
   osfmk/arm64/sleh.c——grep 全文 0 命中),调用点 = **PE_create_console() 第一行**(pe_init.c:416-423)。
2. 主体 pe_init.c:75-137:
   - `PLATFORM_PANIC_LOG_PADDR` 未定义时走 **DT 路径**:查 `pram` 节点 reg +
     `/chosen embedded-panic-log-size`。**我们两个都有**(make_adt.py:51 reg=0x859e0000:0x10000;
     :41 size=0x10000)→ 非 early-return。
   - 映射后:magic=='SHMC'→return;'BTRC'→return;==EMBEDDED_PANIC_MAGIC('FUNK',
     osfmk/kern/debug.h:322)→printf;**然后 bzero(gPanicBase, gPanicSize) —— 无条件**
     (FUNK 分支只打印,照样清零;magic 不符不豁免)。
3. **窗口重合是设计内的,不是巧合**:readback_native.py:28-30 STAGE_BASE=0x859e0000、
   PANIC_LOG_DEST=0x859f0000,注释(:123-125)明说探针 records 就 stage 进内核
   [gPanicBase,+0x10000) 窗内。⇒ **任何 XNU boot 执行到 PE_create_console,探针留在
   retained 窗的一切必被抹零。** README-r4 "boot2 窗全 0"由此获得比"livedram 未注入"
   更简单的解释:**boot2 自己 bzero 的**。§10.11 的"未 power-cycle 窗保内容"假设作废。

## 二、对 r6 定案判词的影响:证据无法二选一(不撤回,但降级)

README-r6 判"本次 boot3 未执行到 check_for_panic_log",依据"0017 里探针残留原封不动"。
但同文件 §1 自证矛盾:**r6 baseline(无 boot3)读回 kernel-entry 首字=0**,而探针文件值应为
0x52800062d65f03c0——baseline 时"残留"并不完好。即 baseline 说"被抹",0017 说"完好",
两处对同一 retained 窗判词相反。

bzero 发现给出两个竞争解释,现有数据无法区分:
- **H1 写不落地**:探针 stage 从未写进 DRAM(§10.12 23:0x 未解同一现象)。⇒ baseline 的 0
  是"从没写过",0017 的"完好"实为"读到同一份从未变过的旧 DRAM",残留证词力归零,
  boot3 到没到 create_console 无从判定。
- **H2 bzero 抹除(更简洁)**:baseline 之前已有任一 XNU boot 跑到 PE_create_console bzero 全窗
  ⇒ baseline=0 是正常行为,**不需要任何写 bug**;若 0017 的"完好"其实也读自 boot3 之后,
  则 boot3 恰恰**跑到了** create_console——与 f1 "未跑到"判词**方向相反**。

⇒ f1 的死亡窗口收窄判词(bootargs_init 之后、create_console 之前)**不能从现有 retained 数据成立**:
H2 直接把方向翻转。f8d9829/34da32c 两旗标统一重述为:"三文件全等可由 boot 后 bzero+读到同一旧内容
平凡解释,不必是 staging 缓存假象"。**不撤回 f1,但判定其证据不足,须先做下面的区分实验。**

## 三、给 f1 的区分实验(一步,按此顺序)

1. **决定性:先 power-cycle 再读 baseline。** 冷重启会重置 PRAM(f1 自己的注记"RAM 窗不过冷启动"
   已证),故 power-cycle 后窗内只可能有:旧 DRAM 残留(未初始化值)或探针 stage 落地的值。
   baseline 若读到 **kernel-entry 首字=0x52800062d65f03c0(探针文件值)** ⇒ 写正常落 DRAM,
   r6base 的 0 就是此前 boot 的 bzero(H2 成立,f1 判词方向需重新校准);
   若仍 **=0** ⇒ 探针 stage 写从未落 DRAM(H1,retained 证据链整体作废,修写是第一优先)。
   一条 --extra-pa name=kernel-entry 对照即可裁决,无需 boot3。
2. 若走 H2(写正常):retained 读回恢复为可信证人,f1 原死亡窗判词**反转**为
   "boot3 跑到了 PE_create_console(bzero 发生)"——下一个收窄目标改成 create_console 之后的
   阶段(相位标记内核此时才真正有用,写点须在 bzero 之后的阶段或每 boot 由 lk2nd 重打)。
3. 若走 H1(写不落):先修 fastboot 时 STAGE_BASE 0x859e0000 的可写性(lk2nd stage 实现 vs
   host buffer),修好前一切 retained 结论(含我的两旗标与 f1 的定案)全部悬置。

verify: 容器 grep/sed 输出全文引用;make_adt.py:41/51、readback_native.py:28-30/123-125 直读;
全程只读,未触设备(efff9d92 在 fastboot,f1 持有)。

## 四、对抗验证结果(01:0x,workflow wf_3f76860b 全部 3/3 CONFIRMED)

三 skeptic 独立读真实源码,全部裁决 CONFIRMED,无一反驳成功:
1. **control-flow**:FUNK 分支无 return 落 :136 bzero;SHMC/BTRC 是仅有两个跳零出口;
   4 个 DT-lookup early return(pram 缺/reg 缺/chosen 缺/size 缺)全在 gPanicBase
   赋值(:109)前——我们的 ADT 四件齐全,不触发。
2. **dt-path**:树级 grep 确认 PLATFORM_PANIC_LOG_PADDR 唯一定义 BCM2837.h:79;
   board_config.h:37-49 T7001 块只含 T7000.h(→AIC/typhoon/S3cUART,无此宏);
   MakeInc.def:55 MACHINE_FLAGS_ARM64_T7001=-DARM64_BOARD_CONFIG_T7001;
   **实时预处理器探针**(clang -E)证实 T7001 解析到未定义分支。
   细节修正:gPanicBase 是 ml_io_map_wcomb 的 **WCOMB 虚拟映射**,非物理地址本身——
   bzero 打的仍是同一段 DRAM,结论不变;探针侧物理直访(MMU-off)与内核 VA 映射同窗。
3. **window-overlap**:STAGE_BASE/PANIC_LOG_DEST 与 pram reg 逐字节重合;
   记录表实际末尾 0xca40(kernel_log 变体 0xda40)< 0x10000,**任何记录不可能逃出 bzero 跨度**;
   RECORD_LIMIT=0xf000 上限也 <0x10000。
   **额外收获**:调用链 pe_init.c:417-423(PE_create_console 首行)→
   **osfmk/arm/arm_init.c:433 调用 PE_create_console** ——死亡窗下界从
   "PE_create_console 之前"具体化为 arm_init 里的这个位置。

⇒ 旗标 §一/§三 的推断基础全部经对抗验证成立;H1/H2 二选一的区分实验(§三.1
power-cycle 后单读 baseline)仍是下一步唯一决定性动作,归 f1。

## 五、01:4x 守护轮:T4.3 闸门现场复验 GREEN + 两项盘面更正

1. **T4.3 触摸构建集成闸门现场重跑,全部真绿**(更正我 00:2x 口头"不绿"误报):
   - `scripts/y35a/test_board_adt.py` 9/9 OK(此前跑错目录 tests/ 报 ImportError,是我的调用错误非回归);
   - `tests/test_kernel_build_contract.py` 3/3 OK(在途未提交,f1 的);
   - personality 补丁对本仓 apply 失败属设计如此——其目标是容器内 xnu-4903 树
     (iokit/KernelConfigTables.cpp 不在本仓),4ae86c4 verify 行记录当时容器内 rc=0。
   ⇒ "推 PR 会假绿合入"的担忧撤销;离线面 T1–T4.3 完整可提交评审。
2. **gh 实际可达 github.com**:gh api repos/UniXNU/UniXNU 正常返回(open_prs=32)。
   旧记忆"镜像无 PR 体系、gh 404"已过时——UniXNU/UniXNU#66 真实存在
   (closed merged, c932f64a xVanTuring 10-22, 与 refs/pull/66/head 逐字节吻合)。
   PR 通道对本分支打开,但按 commit-sop §6 push 归用户批准闸门。
3. **分支保全风险登记**:fix/readback-panic-globals 领先 origin/main 104 commit,
   **0 个在任何远端**。API 中断若吞掉 worktree 即全灭——推送/开 PR 是最便宜的保命,
   等用户点头。
4. **f1 现场**:设备 efff9d92 在 fastboot;工作树有 f1 在途未提交改动
   (board-map/patch/build 脚本/phase-markers.patch/契约测试),本心跳一律未触碰。
   codex-review-20261109.md 定案方向 = 相位标记逐边界单变量构建(先 arm_init 入口
   + PE_init_platform 一对),属 f1 车道。
