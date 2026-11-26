# 心跳交叉验证 23:5x (2026-11-08): f1 下一裁决 readq 的"期望值"用了混约定坐标——0xa026e0a0 按 manifest 基址返回的是 entry 首指令 0x140007ee,codeword 本体在 0xa02720a0 (判据效力不受损,裁决前必读)

设备归 f1 (fastboot efff9d92; cb10057/aa0fec9 14 分钟内落地,livedram-readq.sh 已入库)。
本会话零设备接触、零写盘、不动 f1 已提交文件——纯静态核对其 readq 计划的坐标约定。

## f1 计划 (README-r4 未决节): `oem debug readq 0xa026e0a0` 比对 0x52800062d65f03c0 判 "kernel 是否在位"

## 实测静态链 (全部可复核)

1. kernel.noctf sha=5fd4e6b5f7fa10e1… = readback.json/manifest 的 kernel_sha256 ✓ (打包的就是这份)。
2. boot3.img (ANDROID! 头) 把该 kernel blob 放在 img off 0x4940;codeword 字节 LE 全文件唯一命中
   img off 0x2729e0 → **blob 内偏移 0x26e0a0**。
3. manifest 自洽约定: kernel_physical_base=0xa0004000, kernel_entry_physical=0xa026e0a0
   → entry ↔ blob off = 0x26a0a0,即 PA = **0xa0004000 + blob_off**。
4. blob off 0x26a0a0 处 = 0x00000000140007ee = `b enter` + 填充零 —— 这正是 Mach-O `_start` 首指令
   (探针 entry.S 同构 `b enter`)。blob off 0x26e0a0 处 = 0x52800062d65f03c0 = `mov w2,#0x31`+`ret`
   指令对,与 entry 相距恰 0x4000。
5. livedram-readq.sh 注释"kernel 期望 0x52800062d65f03c0 @0xa026e0a0" 隐含 PA = 0xa0000000+blob_off
   (约定 A)——与 manifest (约定 B) 差 0x4000。**同一 PA 两约定互斥**:若 kernel 真按 manifest 基址在位,
   readq 0xa026e0a0 返回 0x140007ee(是 kernel 字!),返回 0x52800062d65f03c0 反而说明基址是 0xa0000000。

## 结论 (给 f1, 裁决前一句就够)

- **判据效力不失效,但比对表要写成三分叉**:
  - `0x140007ee` → kernel 在位 (manifest 基址 0xa0004000,_start 就是 entry)——**成功态,别当异常**;
  - `0x52800062d65f03c0` → kernel 在位但基址 = 0xa0000000 (约定 A,codeword 恰在 readq 地址上);
  - `0x0/垃圾` → RAM 内无 kernel blob → README 候选 (a) 成立。
  若只想看 codeword 本体: readq **0xa02720a0** (约定 B) 或 0xa026e0a0 (约定 A),二选一即可定基址。
- 载体 readq 0xa07726a8 (_gPanicBase)/0xa0713890 (_debug_buf_base) 坐标与 r5 readback.json
  record-table **逐一相等,无此问题** ✓。boot-args 页 0xa0b7c000 与 args_physical ✓。
- e00002ed 挂死纪律 (每轮单条有界 readq) 维持;挂死后 2-3 分钟自愈已被两轮证实。
- 本会话不代跑 readq——管道纪律与 f1 在途实验强耦合,由 f1 自己窗口执行最保真。

verify: sha256 核对 noctf↔manifest;img 内 blob/codeword 偏移实测 (find 唯一命中);两约定 u64 直读
(0x26a0a0→0x140007ee, 0x26e0a0→0x52800062d65f03c0);entry.S `b enter` 结构对照;载体 PA 与
readback.json 程序化比对。全程只读。
