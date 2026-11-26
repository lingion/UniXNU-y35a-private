# 心跳 20261109-050x: r7 stage 读回裁决 — "记录表全零"证伪; 新定罪: 探针读到的是静态影像, 从未见 XNU 运行时写

时刻 05:0x (getvar 实测响应 3ms, 设备在 lk2nd 槽, 无并行 fastboot — pgrep 空)。
HEAD=55f8aa5。readback_native.py/test_readback_names.py 本会话干净 (仅 boot_layout.py M 在并行件, 不碰)。

## 1. 候选镜像核验 (verification-before-completion, 本轮新鲜执行)

- tests/test_readback_names.py: 16/16 OK (含 panic_log_copy 先于记录表拷贝、CNTVCT 见证在表拷贝前两条新闸测试)。
- test_native_pack 17/17, test_kernel_build_contract 3/3, test_capture_format 6/6 OK。
- 确定性重生成: git archive HEAD → 用 out/y35a/ios12-kernel.noctf (5fd4e6b5) + ios12-boot3-phase/boot3.img 重打,
  产物 image_sha=2aaf092c… 与 out/y35a/readback-probe-20261109-r7 完全一致, entry.S/manifest diff 空。
  → "容器生成的候选镜像 = HEAD 代码" 成立; Assembly 含 CNTVCT 见证 (str x11,[x10,#16]) + 有界拷贝环 (copy_bytes)。
- r3 manifest kernel_sha=5fd4e6b5 (= noctf 实测), 与 r7 头戳 5fd4e6b5 同代; 04:30 轮记的 "r7 头 6e9a09d2"
  实为 Y35AXNU2@0x10000 (boot3 交棒戳, 上代 6e9a instrumented boot3 所写), 非探针戳 — 已在 0430 文内被正确区分, 此处补强。

## 2. 对 04:30 "记录表全零" 的证伪 (同一批 raw, struct 重扫)

r7-baseline/probe2/post-boot3 (0x11000 各, sha 各异): offset 64 起记录区并非全零 —
_BootArgs 15/16 u64 非零, _panicDebugging 8/16, debug_buf 三元组 10/7/11, excepstack 1114/2048,
intstack 1764/4098; 记录区首个非零在 0x1c8。三份 raw 在 64..0x10000 区间逐字节相同 (0 diff)。
04:30 轮只扫了 0x44xxxxxx/魔数/可打印串, 未直接测 u64 非零密度, 结论"表从未被填"不成立:
探针拷贝环确实填了表 (stage 非零 = 探针执行了, 与 CNTVCT 见证递增互相印证)。

## 3. 真正的洞 (定罪级): 读回值 = 加载区静态影像, 非运行时

关键对照 (本轮新做):
- stage[_BootArgs] 与 kernel.noctf 文件 @同 voff 的 128B 逐字节相同 (r3/r7 两代 raw 均 True)
  — 含 0xfffffff0070329cc/e9/13 三个 __cstring 指针, 且这三个 .quad 确实存在于该文件内;
- 但 stage[_const_boot_args] = 全零, 而文件同 voff 非零 → 不是"整片读错到别的影像";
- 运行时预期值全面对不上: Revision=0 (应为 2), debug_buf_ptr=0x4000000/base=0 (debug_log_init 后应
  为 gPanicBase+0x74 量级指针), panicDebugging=0x100000000 (4903 里是 int32_t, debug.c:166);
  panicDebugging=256 (slot1) 同样非法 → 非合法运行时。
- 三份 raw 记录区 0 diff: **post-boot3 与 baseline 完全一致** → 上次 XNU boot3 的运行
  没有在探针读的这些 PA 上留下任何写入痕迹。

推论 (假设需下轮裁决, 本轮不定罪):
(a) boot3 的 MMU 把 kernel VA 0xfffffff0_07xxxxxx 映射到了与线性加载区 (0xa0004000+voff)
    不同的物理页 (arm64 pmap 重映/搬迁), 探针按线性翻译读到的永远是 boot3 拷入的原始影像;
(b) 或 boot3 在到达这些写入点 (debug_log_init 等) 之前已挂, 但历史轮 (panic.raw/文本、
    走到 pid 1) 与此矛盾。
(a) 更自洽: 能同时解释 "post-boot3==baseline 全等" + "boot3 确曾深度运行"。
若 (a) 成立, 则此前一切 "globals 读回 0/异常" 均无证据力, XNU panic 根因仍未取证;
顺序闸 (字面量 0→非零) 的目标应改为: 先让探针读到可证伪为"运行时"的值 (Revision=2)。

## 4. 下轮最小推进 (离线优先, 不 boot)

1. 读 boot3 entry shim 的 MMU 建表代码 (package_native generate_entry_source) 与 4903
   pmap bootstrap: 确认 XNU 运行时 kernel VA→PA 是否仍等于 boot3 线性加载映射;
   容器内可 grep pmap_block_map / BOOT_PMAP / arm_mmu_init。
2. 若被重映: 探针翻译公式改为 "boot3 建表的最终 L1/L2 映射" (entry 里直接算), 或改用
   boot-args 里物理→虚拟已知的载体 (device tree 0xa0b7d000 侧证)。
3. 若线性成立: 回到 (b), 要求重跑一次带 lk console 全量日志的 boot3 定运行深度。
4. 设备在 lk2nd, RAM boot 门禁三条件 (无并行/实际静态核验/用户本轮明确授权) 未集齐
   (授权未获, 且 §3 使现探针无信息增益), 本轮继续不 boot。

并行在途 (不碰): boot_layout.py M, patches/xnu/native-early-fault-record.patch M (-104/+60 重构中),
build-xnu-4903-kernel.py M (新增 22 行), package_native.py M (APCS 看门狗喂食 + trustcache 剥壳,
属设备面风险改动, 等其落定核验)。
远端 push: 仍待用户裁决 (55f8aa5 立案), 本轮未 push。
cron: 守护 12362354 + 保险丝 5f873c8d 在位; 另见 483afcf9 (session-only 20min 同文案心跳) —
与 12362354 双跑, 建议保留全局件删 session-only, 待用户确认。

verify: python3 tests/{test_readback_names,test_native_pack,test_kernel_build_contract,test_capture_format}.py
(16+17+3+6, 全 OK); git archive HEAD 重打 r7 → sha 2aaf092c… 与在库件全等, entry.S/manifest diff 空;
struct 三 raw 非零密度/0-diff 对照 + kernel 文件 voff 逐字节对照 (输出即本文 §2/§3);
docker exec unixnu-y35a-native-20261103 cat /work/ios12-boot3/entry.S+manifest.json (segment_table 语义);
fastboot getvar product (3ms) — 全部本轮新鲜执行。

## 5. 门禁三条件核验 (本轮)

1. 无并行 fastboot/adb: pgrep 空 (05:0x 新鲜执行)。✓
2. 候选实际静态核验: HEAD 重打全等 §1。✓ (readback 件干净; builder/patch/package/boot_layout M 在并行, 其产物不 boot)
3. 用户本轮明确授权 RAM-only fastboot boot: **未获得** (本 turn 系统消息=自动心跳, 无用户指令)。✗
→ 不 boot。且 §3 表明现探针即使 boot 也无信息增益, 门禁与证据双重支持本轮离线。

## 6. 追加裁决 (同轮新鲜): 假设 (a) 限定成立 — 仅 __BOOTDATA 起错位; 栈记录读错页, debug_buf 页对但非运行时

boot3 实际摆放 (container /work/ios12-boot3/entry.S segment_table, 逐条核对):
PA = 0xa0000000 + 段文件偏移(foff), 而 voff==foff 仅对前六个段成立:
- __DATA_CONST(voff=foff=0xc4000): 探针 PA 0xa00ce6f0 = 摆放位 ✓ → _BootArgs 读到的是正确页;
  其值==文件字节合理: arm_init 只拷贝 boot_args 不改原件, 原件在正确页静置属预期。
- __BOOTDATA(voff 0x7a0000, foff 0x710000, delta -0x90000): 摆放 PA=0xa0710000..0xa0728000,
  探针读 0xa07a8000/0xa07b0000 = **另一页** → excep/intstack 记录读错 (raw 非零数==与错页文件差数,
  1114/1114、1764/1764 全等, 证明读到的是含写痕的其他 __DATA 页, 非栈本体)。
- debug_buf 三元组/gPanicBase/__panicDebugging 在 __DATA (voff==foff) 页对: 读到的
  0/0x4000000/0x10000000 既非文件 (该区文件为零) 也非合法 XNU 指针 → 是启动早期其他写者
  (boot3 shim zero_loop 后残留/lk 搬运痕迹) 或 XNU 未达 debug_log_init 即挂。
  与 18:16 zone-init panic 观测自洽: 真因仍待插桩内核给出。

→ 候选缺陷立案 (下轮离线修): readback_native.py 物理翻译须按 boot3 段摆放表 (PA=0xa0000000+foff)
  而非 base+voff 线性; 影响 __BOOTDATA/__LINKEDIT 起的所有记录 (excepstack/intstack 现值无证据力)。
  _BootArgs/debug_buf/gPanic* 记录 PA 本就正确, 其 0-diff 结论 (post-boot3==baseline) 不受影响。
