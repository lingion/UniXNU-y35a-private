# 心跳轮 2026-11-09 01:50 CST — r6 readback 候选离线全链核验 (GREEN), RAM boot 阻塞待授权

工作区: fix/readback-panic-globals @ e9488a0。全程离线只读+再生, 零设备操作。

## 1. 巡检
- linked sessions: unixnu-storage-interface (idle, 末活 17:40Z), t4-3 (idle, 11-06)。
- 本机 `pgrep -fl fastboot` = 空; 容器 load 0.16, 仅僵尸 make。设备事务窗口开放, 但本轮无授权动件 (§5)。

## 2. 测试 (fresh)
`python3 -I tests/test_readback_names.py` → **15/15 OK, 0.315s**。
覆盖: debug_buf 三元组+gPanic 窗五载体加载与边界、panic 正文先拷于记录落表
(aa0fec9 修自我覆盖)、set_table 兜底可达、extra-pa 几何拒绝、RESET_R3
复位顺序、REQUIRED 硬拒、manifest 往返。
工作树 diff: readback_native.py / test_readback_names.py 均 **无未提交改动**,
所测即 HEAD (6580f7c)。

## 3. 候选再生一致性 (防"Build 成功就有效"假设)
命令 (kernel=5fd4e6b5 即 boot3 manifest kernel_sha, stock-boot=92611f87 件):
`python3 readback_native.py --kernel out/y35a/ios12-kernel.noctf --stock-boot
~/unixnu-research/evidence/y35a-20261102/stock-boot.img --extra-pa
kernel-entry=0xa026e0a0:128 --extra-pa bootargs-page=0xa0b7c000:256 --extra-pa
dtb-page=0xa0b7d000:32` → exit 0, 1.3s。
- entry.S: 与 out/y35a/readback-probe-20261109-r6/entry.S **逐字节相同 (diff 空)**。
- 镜像: 与盘上 readback-probe-not-xnu.img **cmp 全等**, sha256 8407f821e2887be5…,
  与 manifest image_sha256 自洽。
- manifest 六字段+15 records 逐项 MATCH。
- kernel_sha256 戳 = 5fd4e6b5 = boot3-native-manifest 同一代 kernel。

## 4. Assembly 语义核验 (生成物直读)
- 载体加载: 五路 ldr x9,=0xa0713890/898/8a0/0xa07726a8/b0 = nm 实算物理地址逐一对上
  (_debug_buf_base/ptr/size, _gPanicBase/_gPanicSize)。
- 边界: 4 守卫 (x0≥w3, x1≥x0, x0<x3+w4, x1≤x3+w4) 全失败路径 b.* set_table,
  记录表兜底必落; 长度 w2=min(size, ptr−base, 0x1000) 双 csel 钳位。
- 顺序: copy_bytes→0x859f0000 在 set_table(adr x19,table) 之前;
  capture_done 在 0x0860065c(RESET_R3) 之前, 后者在 0x004ab000 之前。
- panic_log_offset=0x10000 与 ldr x1,=0x859f0000 自洽 (STAGE+0x10000 在窗外)。

## 5. 阻塞记录 (授权闸, 不推进即此)
`fastboot boot` 三条件: 无并行 fastboot ✔(本轮实测) / 镜像静态核验 ✔(§3–4) /
**用户对本 RAM-only 探针流程的当前明示授权 ✘** — 本 turn 心跳令明确
"不得因历史授权推定当前破坏性操作获批"。零写入分区/userdata 承诺不改变
需逐轮授权的事实。下一轮若用户点头, 直接:
`fastboot -s efff9d92 boot out/y35a/readback-probe-20261109-r6/readback-probe-not-xnu.img`
→ stage → 取 0x859f0000 区 (PANIC_LOG_DEST) 正文并按 debug.c 符号化。
注意: r6 探针读的是 debug_buf 三元组描述的活动窗正文; 它与 00:2x 定案
"boot3 死在 PE_create_console 前" (PE_init_panicheader 未跑, debug_buf 系
debug_log_init 于 panic_init 后设置) 的预期交互 = 大概率载体全 0 走 set_table
兜底 → 记录表照收, 结论不阻塞, 仅正文通道可能空手。相位盲区另案 (插桩从未
编译, 见 01:20 轮结论), 属构建侧修复, 非本探针验证范围。

verify: python3 -I tests/test_readback_names.py (15/15 OK);
diff/cmp 再生件 vs 盘上 r6 (全等); pgrep/ps 设备窗口实测。
