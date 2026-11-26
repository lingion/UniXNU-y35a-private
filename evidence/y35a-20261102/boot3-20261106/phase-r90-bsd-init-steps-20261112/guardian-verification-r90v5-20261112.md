# 守护核实回执 — R90 v5 独立验证 + v6 设计输入(20261112 22:3x)

执行人: Claude 守护会话。全程离线只读,零设备指令(仅 `fastboot devices` 与 getvar 类只读探针);构建容器 docker daemon 停止,未代起(归 Codex 错峰管理)。

## 一、v5 核实结论:声称全部独立复现

| 声称 | 实测 |
|---|---|
| baseline raw `df148fac…` | 逐位吻合 |
| final raw `7abd8fa2…` | 逐位吻合 |
| 设备序列独占 | 日志逐行核查:单 baseline probe→单 XNU RAM boot→单 final probe,全程 serial 唯一;22:24 pgrep 无 fastboot 进程 |
| progress=R90FPX00 | 我独立解码 slot 窗 38–47:仅 slot38–41 变化(R90PNAM0/LOCK0/SUBM0/FPX00 覆盖 R88 残值),42+ 全部保持 baseline 值;全 raw 差异 41 字节,与判定完全一致 |
| patch 绑定 | 盘上 `r90-bsd-init-steps-v5.patch` SHA `6effe722…` 与 source-inputs 声明逐位吻合,mtime(21:25)早于 linked kernel(21:35),绑定链闭合 |

初读疑点已消解:raw@0x00 无 magic、@0x10000 是 Y35AXNU2 shim 戳——v5 为 minimal-boundary 记录顺序布局(early-fault-record report_offset=0x10100),非旧 full-readback 容器;0x10010 处 cntvct 字段两处均 0x4 属记录布局差异,Codex experiment json 记录的 `0x186675fc5a→0x213dcde2` 才是探针 CNTVCT 新鲜度对,方向正确。

**边界判读:bsd_init 进入并走完前 4 个 v5 游标,停在 `fpxlog_init()` 返回之后、`vnode_pager_bootstrap()`(slot42 R90VPG00)之前。**

## 二、v6 实时状态观察

22:07:52 Codex 同时更新 `scripts/build-xnu-4903-kernel.py`、`scripts/y35a/readback_native.py`、`tests/test_native_pack.py`、`CURRENT.md`——正在造 v6/R91,盘上尚无 v6 产物。`/tmp/xnu4903-r90-bsd-init-steps-20261112/src/bsd/kern/bsd_init.c`(构建后状态)已出现 R91 单游标段(全复用 slot37):R91BBEG0→bsd_bufferinit→R91BEND0→IOKitInitializeTime→R91TIME0→ubc_init→R91UBC00→vfsinit→R91VFS00→…→R91PIPE0→…→R91PTHR0。与 source-inputs 的 reused-slot 解释规则自洽(仅最终字为直接证据)。注意:该 R91 串不在 v5 patch 内,是当前在途源码改动,勿与 v5 归档件混淆。

## 三、给 v6 的离线源码分析输入(高优先候选)

FPX00→VPG00 区间约 220 行、30+ 初始化调用。源码级风险排序:

1. **`bsd_bufferinit()`(bsd_init.c:745 注释原文:"SIDE EFFECT: Starts a thread for bcleanbuf_thread(), so must…")**——内核线程创建+调度路径,`kernel_thread_start` 挂或新线程与当前 boot 线程争用都会停在这段之后;R91BBEG0/BEND0 游标已正确覆盖它,是 v6 关键分辨点。
2. `vfsinit()`/`ubc_init()`——ubc 涉及 pager 初始化,与 slot42 目标 vnode_pager_bootstrap 同域,失败模式相关。
3. `audit_init()`、`dtrace_postinit()`——条件编译路径多,注意实际 T7001 DEVELOPMENT 配置下哪些被编进。
4. `kmstartup()`/`sysctl_mib_init()`——低风险。

若 v6 观测到 R91BBEG0 新鲜而 R91BEND0 缺席,`bsd_bufferinit` 内部再分辨建议直接读其子步(bdevvp/核线程 start),不必再加代次。

## 四、账务

- 工作树在途未提交改动(CURRENT/LOG 16:12 版、scripts、tests、patch 等)全部归 Codex 收口,我未代提。
- 守护心跳 cron 与保险丝 cron 在位;设备 idle 于 fastboot。

verify 行: shasum 双 raw 逐位; python struct 独立解码 slot38–47+全文件差分 41B; 盘上 patch SHA=source-inputs 声明; 设备日志 grep boot 计数=3; pgrep 空; /tmp 源树 awk 调用序列提取。
