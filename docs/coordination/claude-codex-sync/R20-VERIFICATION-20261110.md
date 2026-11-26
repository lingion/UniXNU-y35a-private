# R20 独立核实回执 — Claude Desktop(恢复可用)致 Codex

日期: 2026-11-10 Asia/Taipei。仓库 HEAD `a3f0273`,分支 `fix/readback-panic-globals`,设备 `efff9d92` 在 fastboot。

触发: 用户令"Codex 跑了一晚上到 R20,Claude 去打下手、擦屁股、主动联络"。Claude Desktop 中断一整晚,现按 LONG-RUN-STATE 分工(读 CURRENT/LOG 后再贡献,不改 Codex 控制的设备序列与 shared source)从真实盘面对账 R20。

## 一、核实为真(全部独立实测,非引用 Codex 声称)

| R20 preflight 声称 | 独立实测 | 证据命令 |
|---|---|---|
| kernel `6f5c36f4…` | 实物逐位吻合 | `shasum -a 256 out/y35a/ios12-kernel-phase-r20/kernel-packed.macho` |
| boot3 `cfd4e169…` | 实物逐位吻合 | 同上 boot3.img |
| probe `3fc822b0…` | 实物逐位吻合 | 同上 readback-probe-not-xnu.img |
| host suite 92/92 | **92 OK 零失败** | `python3 -m unittest discover -s tests` |
| phase verifier ok:true | **ok:true / 0 fail** | `verify_phase_instrumentation.py --kernel …r20…` |
| full-readback layout ok:true | **ok:true**(stage-size 须 0x11000) | 见下方缺陷 B |
| full-readback transport ok:true | **ok:true**(lk-stage-size 须 0x11000) | 同上 |

初稿时 R20 只有 preflight 记录、无 device-run 目录(即尚未上设备,设备序列归 Codex,我不抢 fastboot);**00:09 Codex 完成了 R20 设备序列**,结果见第五节补记。

## 二、擦出的两个持久化缺陷(请 Codex 拍板,非我代改)

### 缺陷 A — 盘上 patches/ 与 R20 二进制不自洽,当前不可复现 R20

实测符号:

- R20 kernel 有 `_native_phase_args`(bss),**R18/R19 kernel 没有**。
- 盘上 `patches/xnu/native-phase-markers.patch` 定义的是**两参** `native_phase_marker(uint32_t slot, uint64_t value)`,内部用全局 `native_early_fault_address`,**没有** `native_phase_args`。
- 盘上 `native-phase-c-entry-markers.patch` 与 `native-phase-console-marker.patch` 的调用全是**三参** `native_phase_marker(args, 5/6/7/10, …)`。

结论: 这三份盘上 patch 互相矛盾(两参定义 vs 三参调用),一起 `git apply` 后编译必失败;R20 二进制能存在,说明构建时用的是另一版"三参 + capture 原始 args 到 native_phase_args"的 helpers,而**那一版没有落盘**。`scripts/build-xnu-4903-kernel.py:300-333` 顺序 apply 全部六 patch,当前盘上状态无法重现 R20 的任何一代。

### 缺陷 B — layout/transport 闸的 stage-size 默认值与 R20 真实 staged_bytes 不符

R20 manifest `staged_bytes = 69632 = 0x11000`,但两闸用默认 `0x10000` 跑会报 `staged_bytes=0x11000 exceeds stage-size=0x10000`。preflight 写 "layout gate ok:true" 时必然显式传了 `0x11000`;这是一个口径陷阱:任何复用默认 size 的复跑都会误红。建议闸从 manifest 的 `staged_bytes` 自动取区间,不靠命令行手传 size。

## 三、R20 假设与 R19 结果(供 Codex 解读,我不抢先判)

R19 device-run 实测(我已读 decoded-fields.txt):body `0x40` 起 slot 4=`ARMENTRY`(0x60)仍在,record offset `0x3c0`(`_native_early_fault_address`)= **0**,slot 5(`0x68` ARMINITE)= **0**。即 R19 的 MMU-off 指针修复(`add x16,x16,x22; sub x16,x16,x23`)**证伪**:全局发布仍为零,C 边界仍未到。R20 换方案(C helper 首调抓 args KVA 直写 `args+0x800`,不再依赖该全局)。

按 LONG-RUN-STATE 解释规则: R20 若 slot 5 仍零,是"该 marker 路径"的负观测,不证内核未起;若 slot 5=ARMINITE,则首次证明 C `arm_init` 在真机进入。**这是 device-run 才能定的,归 Codex。**

## 四、需 Codex 决定的单点

R20 三产物 offline 全绿、可上设备。但缺陷 A 使当前 patches/ 不能复现 R20 二进制。**在 Codex 跑 R20 device 序列之前或之后**,需把构建 R20 实际用过的 native-phase-markers 三参版重新落盘(连同其余五个 untracked instrumentation patch 一起按 commit-sop 入库),否则 R20 的证据不可再生。我不擅改,等 Codex 的 shared-source 收口。

## 五、补记(同日 00:2x):R20 device-run 已由 Codex 完成,结果与复现缺陷升级

审计期间 Codex 完成 R20 设备序列(00:09,`phase-r20-carrier-20261110-000920/`)。Claude 独立复算:

- final.raw SHA `21684d73…` 逐位吻合;magic `Y35ARD01`;kernel prefix `6f5c36f4bfac793a` 对 R20 kernel。
- 逐偏移独立解码(不信 decoded-fields.txt):slot 4 = `ARMENTRY`;slot 0-3、5-10 全零;record offset 0x3c0 全零。
- 判定:R20 preflight 自己的证伪条款("若 C arm_init 进入 slot5=ARMINITE")**未满足**。但这不构成 C 未到达的正证明——与 r18 同构的"helper 静默跳过"风险仍在,因为见下。

**缺陷 A 的完整根因(00:4x 二次修正,此前"patch 不在本机任何位置"的断言过强,撤回)**:

- R20 构建树 `.cache/xnu4903-work-r20/osfmk/arm/arm_init.c`(:89-96,:226-248)保留实际构建源码:`static boot_args *native_phase_args;` + 三参 `native_phase_marker(boot_args *args, uint32_t slot, uint64_t value)`,首调捕获 args,写 `native_phase_args+0x800` 的 `record[slot]`,**无早退门**。
- 构建链是两拍:盘上 `native-phase-markers.patch`(digest `2fda1c0d`,已漂移为 `bef63843`)先落地两参版,再由**第七个 patch `native-phase-kva-carrier.patch`** 改造为三参版。该 patch 曾**只存在于容器副本** `/work/UniXNU-y35a/patches/xnu/`(digest `27145ae9…`),本机工作树与 build 脚本 apply 列表都没有它——**已由 Claude `docker cp` 找回落盘本机**(`patches/xnu/native-phase-kva-carrier.patch`,SHA256 逐位核对)。
- R20 哨兵 vs 盘上 digest 比对:`native-entry-witness` `native-phase-c-enable` `native-phase-c-entry-markers` `native-phase-console-marker` 四个 MATCH;`native-early-fault-record`(盘 `4bdf45f3` vs 哨兵 `00004a63`)与 `native-phase-markers`(盘 `bef63843` vs 哨兵 `2fda1c0d`)两个**漂移**——盘上版本在 R20 构建(容器 15:54)之后被继续编辑(本机 mtime 23:49-23:58)且未再入任何构建。
- 新发现的 build 脚本(工作树在途版)已把 apply 列表改为含 `native-handoff-witness.patch`(**不含** kva-carrier)——若照此重建 R20 代次,helper 停在两参 early-fault 门版,R20 语义不会复现。kva-carrier 是否进 R21 构建链需 Codex 明示。

给 Codex 的收口建议(归你拍板):`native-phase-kva-carrier.patch` 已找回,请把它与 `native-handoff-witness.patch`(00:26 新写,MMUON000@0x858 + ARMRET00@0x860)一起纳入 build 脚本 apply 序列与 commit 入库;R20 若需复审,从 `.cache/xnu4903-work-r20` 源码反推重建 patch 序列并核对 SHA `6f5c36f4…` 逐位复现。在 patch 链收口前,slot5=0 仍不得进"arm_init 未到达"的最终解释——注意 kva-carrier 版 helper 无早退门,R20 的 slot5=0 比 r18 更接近真负观测,但 0x800 基址沿用 `native_phase_args` 捕获值,carrier 落点仍依赖 args KVA 有效这一未独立验证前提。

## R19 与 R21 在途状态(顺带核实)

- R19(`phase-r19-carrier-20261109-233239/`):Codex 已跑完。我独立解码:slot4=ARMENTRY、0x3c0(early_fault_addr)=0、slot5=0 → R19 preflight 的证伪条款未满足,MMU-off 全局发布修复失败,该事实与 R20 换 kva-carrier 方案的因果链自洽。**R19 结果目前既不在 CURRENT.md 也不在 LONG-RUN-STATE.md**,两份文档停在 r16-r18 口径,过夜 r12-r20 九轮未回写(LOG.md 在途未提交改动里有部分)。
- R21 在途:`patches/xnu/native-handoff-witness.patch` 本机 mtime 00:26(Codex 正在写),`out/y35a/` 尚无 r21 产物。该 patch 用 `x20+x22-x23` 物理基址直写 `+0x858`/`+0x860` 两个新窗口(MMU 开启后与 ret 进 arm_init 前),不再依赖 0x800 carrier slot——方向正确,等它落地我再核。
- `drivers/AppleKeyStoreState` `drivers/ArmCpu` 两个 untracked 目录与 Y35A 线无关,不入库,留待各自归属。

## 设备面
本轮零设备指令(仅 heartbeat 的只读 `getvar` 健康探针)。任何 boot 前先双查(isRunning + 用户授权文本)。
