# 心跳 20261109-0830: stage⊂pram 全同构覆盖定罪 — 现行 r7 布局物理拿不到 panic 正文

时刻 08:3x。HEAD=baf4604, 分支 fix/readback-panic-globals。
并行 fixer 会话 local_c3ce3e96 (标题"修复 readback 探针的段摆放翻译") 开工,
生成器/打包器/测试文件归其所有, 本会话零写入除本 evidence 文档。

## 1. 判词 3(a) 终局: 符号 PA 换算全对, 定罪解除 (本轮实测)
- boot_layout 重算 layout base=0xfffffff007004000 end=0xfffffff007b7c000,
  physical_base_for → 0xa0004000 == boot3 manifest kernel_physical_base,
  delta=0x0; entry VA 0xfffffff00726e0a0 == manifest kernel_entry_physical
  0xa026e0a0 换算 == Mach-O LC entry。
- _BootArgs/_const_boot_args/_gPanicBase/_gPanicSize/_debugger_panic_str/
  _panicDebugging/_debug_buf_base/ptr/size: probe-PA 与 manifest-PA 逐一
  delta=0x0。⇒ "VA→PA 换算错" 假设出局。

## 2. 读回通道本身正常 (文件镜像字节 == DRAM 采样)
- r7-post-boot3 raw[448:448+48] 与 ios12-kernel.noctf 该 VA 对应 fileoff
  0xca6f0 前 48 字节逐字节全等 (match-to-file True), 与 boot3.img 内嵌
  slice (slice@0x4940) 同区也全等。
- _BootArgs 窗 120/128 非零, 15/16 u64 槽落在内核 VA 域 (0xfffffff0070329cc
  型指针, 指向 __TEXT cstring "CPU attempted to halt itself" 等) —
  这是该 VA 处镜像文件的静态内容, 不是运行期 boot_args 结构
  (Revision 魔数/AllDDRV 全 raw 扫描零命中)。

## 3. 决定性架构缺陷: STAGE_BASE == DT pram reg 基址
make_adt.py:51 `node('pram',[('reg',struct.pack('<QQ',0x859e0000,0x10000))])`
== readback_native.py STAGE_BASE=0x859e0000 (0x11000 有界)。同一物理区。
探针执行序: 先写 marker/stamp/regs 到 stage+0x0..0x38, 再按 record 表从
0x859e0040 起顺序拷贝 (_BootArgs→…→excepstack→intstack, 累计覆盖到
stage+0xC640), 每一笔都是对 pram 同址的覆写:
- panic 头 (pram+0x0..0x74, EMBEDDED_PANIC_MAGIC 所在) — 被 marker+regs+
  early-fault-record(0x40..0x1C0) 碾过, 先毁后采;
- debug_buf 正文 (pram+0x74 起) — 被 record 流逐段碾过;
- 探针"拷贝正文"目标 PANIC_LOG_DEST=0x859f0000 == pram+0xf000, 同时是
  RAMBoot 垫片 stamp 落点 (package_native.py:76/131 Y35AXNU1/2 + sha),
  三方共写同页; 且 base==0 时 cbz 直接跳过, 从未写入。
存活窗口: 仅 pram[0xC640,0xF000) ≈10KiB 未被 record 流覆盖;
r7 三份该窗全等且无 ≥16B ASCII run ⇒ 正文 (若有) 在 0xC640 之前, 已被毁。
⇒ 判词: 现行布局的 get_staged 物理上不可能回带 panic 正文, 与三元组是否
为 0 无关。11-06 panic.raw 有正文是因旧代 r3 record 集更小/窗口错位,
其"无 FUNK"观测同样是被自覆盖后的伪影 — baf4604 "死于头写完第一条文本
未到" 的收窄判定建立在被覆盖区上, 不可再引用。

## 4. 判词 3 剩余分叉 (移交 fixer)
- _BootArgs 无运行期结构 + gPanicBase/debug_buf 三元组全 0, 而 stamp 翻转
  证明 boot3 垫片跑过 ⇒ 候选收窄为: (i) XNU 经自身页表把写落进别处 PA
  (非 flat, "段摆放"正是 fixer 任务名); (ii) boot3 死得极早 (start.s 级,
  未到 SaveBootArgs)。区分器: 探针应直读 pram 存活窗 + 把 LK 侧 RAMBoot
  段表目标 PA 打进 stage (package_native segment_table 是 .quad 三元组,
  可静态解出 dst 列表与 Mach-O 段表对照, 离线可做)。
- 修复硬约束 (给 fixer): stage 必须离开 pram 域, 或拷 pram[0..0xF000)
  到一个非重叠 scratch 先于 marker/records 落笔; stamp 落点须与 EPH 头/
  正文区解耦; 三元组为 0 时应有 fallback 直采 [gPanicBase,gPanicBase+gPanicSize)
  或整窗快照。

## 5. 设备闸与边界
- 本轮无人对 RAM boot 授权 (心跳指令要求逐轮显式确认), 且 §3 定罪使现行
  探针跑了也白跑 ⇒ 不 boot。fastboot devices=efff9d92 在槽; pgrep fastboot
  空; t4-3 idle; fixer working (已发协调消息: 本会话只读+核验+闸,
  生成器文件归 fixer)。
- 未写分区, 未碰 userdata, 未 push。守护 cron: 12362354 */20 存活,
  483afcf9 */20 session-only 并存, 5f873c8d 6h 保险丝存活 — 无需新排。

## 6. 判词修正 (同轮 panic.raw 复核, 防过断言)
11-06 panic.raw (69632B, Y35ARD01+5fd4 头, ==panic2.raw) 实测: 载体窗
_debugger_panic_str/_panicDebugging/_debug_buf_base/ptr/size (960..1600)
窗内 128/128 全非零且连续 ASCII 正文 ("Calendar:", "Zone map:",
"Metadadata:", 0xfffffff05 型 VA) — 证明 record 窗采样通路在正文存在时
能完整带回, §3 "物理拿不到正文" 仅适用于 pram 头区/EPH 路径, 不适用于
kernel-PA 载体窗。修正后双缺陷定案:
(A) stage⊂pram 别名 = 探针自毁 panic 头/FUNK 采样 (生成器缺陷, fixer 修);
(B) r6/r7 载体窗全零+match-to-file = 11-09 世代 boot3 在写到 kernel 静态
    debug buffer 之前即死 (正文路径活着但无正文) — XNU 侧新问题,
    与 11-06 "跑到 pid1 launchd 完整 zone-info" 世代行为分叉,
    分叉源=11-06→11-09 间的构建差异 (并行 dirty 件正含
    build-xnu-4903-kernel.py/boot_layout.py/patch — fixer 域)。
旧证据引用规则更新: "无 FUNK"观测 = (A) 伪影; "无正文"观测 = (B) 真信号。

verify: python3 -m unittest discover -s tests -> Ran 42 tests OK (08:2x);
manifest kernel_sha/image_sha == 盘上 True/True; nm+boot_layout 重算 delta
全 0x0; r7 raw[448:496]==noctf fileoff 0xca6f0 逐字节 True; AllDDRV 魔数
全 raw find=-1; pram reg (0x859e0000,0x10000) 实取自 make_adt.py:51。
作者: lingion <lingion@hrbeu.edu.cn>
