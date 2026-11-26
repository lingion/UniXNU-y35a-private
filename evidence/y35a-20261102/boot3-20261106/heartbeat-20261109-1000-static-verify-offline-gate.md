# 心跳 1000 — 静态核验 r7-lineage 候选 + 设备只读闸记录 (无 RAM boot)

工作件: `fix/readback-panic-globals` HEAD `6daa7a0`。本轮只读+离线, 无 fastboot boot, 无分区写, 无 userdata。

## 盘点 (fresh)
- linked sessions: 在跑的相关会话 = fixer `local_c3ce3e96`(readback, bypassPermissions, 我上轮 endorsed 消息仍 QUEUED, 它正在另一轮)。其余 running 会话 (启动器/视觉断言/rockbase) 与本任务无关。触摸会话 `t4-3`、`unixnu-storage-interface` 已 idle。
- 设备事务窗口: `pgrep fastboot` → NONE (本轮无人在操作设备 USB)。`adb` fork-server 常驻, 非设备事务。
- 定时任务: 仅 threads-daily-pipeline, 与本任务无关。
- 并行写冲突: `git status` 显示 `scripts/y35a/{readback_native.py 已净, probe_rmi.py, rmi_probe.cpp, boot_layout.py, package_native.py}`、`patches/xnu/*`、`drivers/{AppleKeyStoreState,ArmCpu}`、协调文档 均为 fixer 在途 (M)。故本轮**不 commit 这些件**, 只提交本证据文件。

## 静态核验 (不信 Build 绿, 逐项实测)
1. `python3 -m unittest discover -s tests` → **Ran 42 tests OK** (fresh, HEAD)。
2. 生成候选 (HEAD generator, stock-boot sha `92611f87…`, kernel `5fd4e6b5…`):
   - 两次独立生成 → 镜像 sha256 **相同** `2aaf092cfa15a28a45694ca878c7e59b7a023a751494766c39ff958899479932` (可复现)。
   - `readback.json`: 12 records, `staged_source=0x859e0000 size=0x11000`, `panic_log_offset=65536`。
3. `entry.S` 读+有界拷贝路径**实存** (非假设):
   - `ldr x9,=0xa0713890 / ldr x0,[x9]` 读 `_debug_buf_base`; `0xa07138a0` 用 `ldr w2`(4B size); `0xa07726b0` 用 `ldr w4`(4B gPanicSize)。
   - 四路 range-check (`cmp/b.lo..b.hi set_table`) + `csel` 把长度夹到 `min(w2, x1-x0, 0x1000)`。
   - `copy_bytes:` 逐字节 `ldrb/strb` 循环, dest `0x859f0000`。
   - freshness witness `mrs x11,cntvct_el0` 在 (91ab4a1)。
4. `verify_capture_layout.py --manifest <guardian> --pram-base 0x859e0000 --pram-size 0x10000 --stage-base 0x859e0000 --stage-size 0x11000 --panic-dest 0x859f0000` → **列出 stage 及每条 record 与 pram 重叠** (缺陷A 未修)。

## 判词: 不满足 boot 条件, 记录阻塞
- (b) 静态核验通过: 候选可复现、Assembly 确含读取+有界拷贝。
- (a) 当前无并行 fastboot, **但** informative boot 物理上不成立: stage `0x859e0000` == DT pram 窗, records/markers 覆写 EPH 头 — 正是 0830/0945 定罪、ledger Next Work #0 阻断的缺陷。r8 字段宽 + stage 去别名未落 (`field-width records: NONE`, `_native_entry_trace record: False`)。
- (c) 本轮无用户对"该次 RAM-only 探针"的逐轮显式授权; README/ledger 明确既往 RAM boot 非普适授权。
→ 结论: **本轮不 boot**, 只推进离线。boot 的真正前置是 fixer 落 r8(字段宽)+ stage 去别名 且 `verify_capture_layout` 绿; 届时仍需用户逐轮授权。

## 下一 informative 实验 (待 r8)
候选 = r8 (字段宽 8B/4B + entry_trace 显式 absent)。闸: (1) `verify_capture_layout` 对 r8 manifest 无 pram-overlap, (2) 无并行 fastboot, (3) 用户对本轮 RAM boot 显式 GO。抓回后: 若 `_debug_buf_*` 给出运行时非零值 → 本世代确写日志(翻 0830 §6B); 头区因去别名可读 → EPH 取证闭环。
