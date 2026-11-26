# 验收电池 第二轮 20261109 ~12:4x — e434dc9+7566c88 (r9 护栏): PASS + 1 遗留账务

触发: fixer 交 r9 护栏六声称。全程离线, 零设备指令, 零 push。
隔离: clean detached worktree @ 7566c88 (/tmp/acc-7566c88, out 软链)。
本轮仅两文件入提交: capture_format.py+test (7566c88) / readback_native.py+test (e434dc9)。

## 六声称独立复核

| # | 声称 | 判定 | 证据(fresh) |
|---|---|---|---|
| 1 | 双代次 lineage 零漂移 | ✅✅ | tip 重建 frb=**ce63d21a…**、mb=**7f81f759ccf33779…** 与 r8/mb1 目录实物**逐位同**; 护栏提交后汇编字节零漂移坐实 |
| 2 | 61-red→84-green | ⚠️ 口径 | **提交态 7566c88 干净树 = 69 OK(skip1)**; 84 含未跟踪件。delta 即 NOTE-A |
| 3 | 护栏(field_bytes/absent/fence/无硬编/0x100 拒解) | ✅ | tip frb manifest: widths {early-fault=384,_BootArgs=8,const=384,gPanicBase=8}; absent 8 件含 _native_entry_trace+_original_faulting_state; purpose 含 fence/alias; **0xa0004000 全树零命中**; capture_format.py:84-89 valid=False on 非布尔, e2e r7 实测 |
| 4 | defect(C) 修 + 死码判定 | ✅ | readback_native.py:409-441: str x0,[x9] 在双 guard 之后, fault_invalid 路径 str xzr,[x9]; **nm 5fd4 = 0 命中 _original_faulting_state**, 无 patch 携该符号 → vanilla emit 此块死码(b579ab4 r8 emit 已证不含); test:284-289 锁 guard 序 |
| 5 | LEGACY 竞态澄清 | ✅ 非我 | HEAD 无 LEGACY_FIELD_BYTES; 本会话全程未触 capture_format.py → 那份 in-flight 表回退**不是我编辑**, 无需按我语义重立 |
| 6 | 闸双模式 | ✅ | frb: --stage-base 0x859e0000 → ok:true failures=[]; mb: **须 --stage-base 0x859f0100**(报告页, 非全量 stage)→ rc=0 ok:true failures=[]。首跑误用 frb 的 stage 基址故 mb 报 overlap, 换正确基址即过 |

## NOTE-A(遗留账务, 上一轮 NOTE 2 未落地)

**验收合同的闸本体仍未入库**: `verify_capture_layout.py`、`verify_readback_transport.py`、
`tests/test_capture_layout.py` 三者 git ls-files @ 7566c88 = **空**(从未提交, 全分支无)。
packer 现发布几何字段且 manifest 齐备, 但读者/闸孤儿化 → clean tree 无闸可跑,
提交态套件 69(非 84), +15 全在那些未跟踪文件里。
**这是连续第二轮同一缺口**; 若 r9-gen 见证列为验收合同依赖, 请先补提交闸+其测试。

## mb 指针问题(fixer 求表态)

裁定: **暂不加** pointer+bounded-copy 到 mb 报告。理由 = claim 4 同源的实证:
vanilla 5fd4 携 0 个 _original_faulting_state, 加进 mb 亦为死码; 0x18 语义本就属
仪器化内核线(_native_entry_trace 类), 待 instrumented kernel 真发该符号再作。

## 设备面

本轮零指令。device client 探针: none active。任何后续设备动作先双查
(list_sessions isRunning + 用户本轮授权文本)。

verify: 见表内命令(git show --name-only; worktree 双模式重 build shasum 逐位;
unittest 69; grep field_bytes/absent/fence/0xa0004000; nm 0 命中; 源码 fault 块 409-441;
双闸 ok:true 含 mb 正确 stage 基址)。worktree 待清。
