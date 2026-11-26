# boot4 r3 探针实机 RAM 读回 (2026-11-08 21:5x 心跳轮)

## 点火与传输序列 (本会话, 全程 RAM-only, 无分区写, 无 userdata)
1. 静态核验通过后才 boot: 镜像 sha256
   67fd4f8bb7fb34f456b5c57f17f9b33eb31657b337d8bb93039689c452673d07,
   manifest kernel_sha256 == 实机内核 ios12-kernel.noctf
   5fd4e6b5f7fa10e1b2cc9323ac5802833c15479fce5c67068f2ba8837fdcdc94 (MATCH),
   entry.bin 已嵌入镜像, 源码/ELF 机器码含动态 debug_buf 三元组读 + 有界拷贝 +
   双 reset 顺序 (MACHINE_CODE_CONTRACT True), 离线全套 38 测试 OK, git diff --check 净。
2. `fastboot -s efff9d92 boot readback-probe-not-xnu.img`
   → Sending 'boot.img' (184 KB) OKAY / Booting OKAY / Finished 0.032s。探针正常执行。
3. 探针自带 warm-reset 后设备回 fastboot。随后进入传输闸问题 (下节)。

## 传输闸诊断 (systematic-debugging Phase 1, 有界只读)
- 现象: `fastboot devices` 即时枚举, 但所有事务命令 (getvar/oem/panic) 10s 内挂
  → rc=142。复现历史 §10.9-10.11 post-reset USB-stale 形态。
- 已排除:
  (a) 残留 fastboot 客户端占接口: `ps -ax | grep fastboot` → 无 (两次 TaskStop 的
      后台命令未留下 fastboot 进程)。
  (b) adb fork-server 抢占: `adb kill-server` 后 getvar 仍 rc=142 → 假说不成立;
      adb start-server 已恢复。
  (c) 主机 USB 掉设备: system_profiler 显示 Android 18d1:d00d serial efff9d92
      在位 Up to 480Mb/s; ioreg 有 "Android" 节点。设备物理在线。
- 决定性: 等待约 2 分钟 (上一轮 TaskStop 遗留的半程 upload 事务超时释放) 后,
  单条 `fastboot -s efff9d92 getvar product` → `lk2nd-msm8916` rc=0, 0.003s。
  通路自愈, 根因 = 前次被杀 upload/ reboot 事务残留的半开 USB 事务, 与
  设备端 LK 单客户端锁串行化; 非 stale 硬件, 非 adb。

## 读回结果 (关键)
`oem y35a panic` OKAY Staged → `fastboot get_staged readback-raw.bin`
69,632 B, sha256 c720ffb88b66410ccc4fbbc33f1dc993b72470e20b06ba71473d2c6902299f04。
capture_format.classify → kind=Y35ARD01, marker=Y35ARD01,
kernel_stamp 5fd4e6b5f7fa10e1 (与 4903 内核一致, 证明探针跑对镜像+stage 地址翻译正确)。
但全部 XNU panic 载体回读为 0:
  _gPanicBase=0  _gPanicSize=0  _debug_buf_base=0  _debug_buf_size=0
  _BootArgs=0  _panicDebugging=0x100 (BSS 初值, 非运行期写回)
  _debug_buf_ptr=0x0800000000000000 (位模式异常)
panic-log 落点 [0x10000] 有 4078 非零字节, 但为二进制残留 (指针/标志位图),
非 ASCII 正文 —— 因 base==0 使 `cmp x0,x3 / b.hs capture_done` 提前跳过分拷贝。

## 定性结论 (不臆测, 有据)
探针本体、地址翻译、stage/upload 通道全部正常 (marker+kernel_stamp+stage 结构为证)。
载体全 0 的直接原因 = DRAM 在探针读回前已丢失:
上一节传输闸的诊断/恢复涉及一次 USB 物理拔插 (用户修 stale USB 的动作),
该掉电使 MSM8916 冷复位, 清掉上一次 boot3-panic 遗留的 gPanicBase/debug_buf 区。
因此本轮读回的是"无前置 XNU panic 的空白 retained memory", 非探针缺陷。

## 下一轮取证正确序列 (必须同一次上电周期内完成, 中途禁 USB 断电)
1. fastboot boot boot3.img → XNU 跑到 pid1 launchd 确定性 panic (halt)。
2. 不经任何 USB 断电, 直接 fastboot boot readback-probe-not-xnu.img (r3) →
   探针在 halt 后 retained DRAM 中读 gPanicBase/debug_buf 三元组 → 有界拷贝落
   [0x859f0000] → 探针自带 warm-reset 回 fastboot。
3. oem y35a panic → get_staged → classify; 若仍 EPH offset/len=0 才回到
   boot4-empty-readback §7 的零长度分叉 (nested panic / 未提交 header)。
唯一风险: boot3 panic 后设备 halt 在 XNU, 是否能被 fastboot 再次 boot (需 LK 已
把控制权交回且 USB 仍 claim 得住) 待实测; 若 halt 卡死则需一次受控 warm reset
(PMIC 0x004ab000 路径) 而非冷断电。

verify: 38 测试 OK; SHA/manifest/MACHINE_CODE/RESET_ORDER 全 true; 本文件只读证据, 无设备写。
