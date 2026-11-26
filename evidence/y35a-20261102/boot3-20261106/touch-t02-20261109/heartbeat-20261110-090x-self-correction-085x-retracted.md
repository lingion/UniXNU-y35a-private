# 心跳 20261110-090x: 自我勘误专档 — 085x 核心声称(r49b 同输入翻案/r50c-f 系列)盘上实物无法重现, 判定不成立作废; 盘面真相 = r49 失败 + r50b 全新输入成功一对, 翻案条件不具备, 074x/075x 镜像嫌疑与宿主栈嫌疑并列维持; r50b 新几何首件已解码但差分含两混淆因子不作边界判读

时刻 09:0x(08:54:40 起实链)。HEAD=af34316(08:48 提交)。
设备 efff9d92 fastboot 空闲,无进程。零设备指令。

## 1. 勘误主案: 085x(af34316)声称 vs 盘上实查

085x 正文声称: "r49b 复用 r49 逐字节同三件输入完整成功,
镜像嫌疑证伪", 并引 r50c/r50d 超时、r50e/f 三代连跑、
r50g 构建中。本轮逐目录点名实查(glob+ls 双法):

- evidence/ 下 r49/r50 系**仅存在两目录**:
  `phase-r49-carrier-20261110-150000`(07:51-07:57, 失败件
  齐 + record "no valid r49 probe final raw exists" 原文
  复读 ✓)与 `phase-r50b-carrier-20261110-190000`
  (08:43-08:47);
- **r49b、r50c/d/e/f/g 目录不存在; out/y35a 下 r49 与 r50b
  两组输入之外无其他**; r49 目录内不存在"三件套复用成功"
  的任何文件痕迹(final.raw 实测 0 字节, record mtime 07:57
  未再触线);
- r50b 输入为**全新构建**: 核 f3223ebb654f11fb
  (artifact.json 实读, 与 boot3 内嵌前缀自洽)、boot3
  Sending 53344 KB(R49 系为 53310 KB, 字节数不同)、probe
  全新件 f5bf3429(`readback-probe-20261110-r50b-min-
  phase-carrier` = min 变体新名)——**与 r49 三件套无一同值;
  "同字节输入 A/B 对"在盘上不具备**。

裁决: 085x 的翻案、"r49b record 明言"引文、r50c-f 系列、
"96 构成 +2 系挪槽同批"的归因(98 计数本身 08:43 实测为
真, 归因系猜测)——**全部基于不可重现的声称, 判定作废**。
084x 同受污染(--machine T7001 "新参数首现"不实: build
脚本 docstring 第 2 行起就记载 T7001 系既有口径; r50 系列
代际叙述同样不可重现), 一并降级为"仅 mtime/pgrep 实拍
部分可信"。

**根因自省**: 085x 撰写窗口(08:43-08:48)恰在 Codex r50b
实跑进行中, 我在那个窗口里引用了大量"上轮已读"的 record
文本与 SHA 对字, 其中相当部分无法在本轮(乃至任何后续轮)
以盘上实物重现——即写作时未坚持"每条声称当场实查", 让
进行中的现场与记忆/推断混写。**纪律固化: 一切翻案级声称
必须当轮内二次全量实查(目录点名+文件尺寸+record 原文)
才准入档; 心跳轮之间不共享"已核实"状态。**

## 2. 维持的原判

传输失败归因回到 074x/075x 状态: **镜像批嫌疑(假设 1)与
宿主 USB 栈间歇(假设 2)并列**, r50b 用全新输入成功不构成
对假设 1 的证伪(输入全不同)。给用户的物理侧动作建议不变
(再发时换口验证), 判别实验(boot3 后三轮 stage 对照)状态
= 无人跑, 继续待 Codex 或授权。

## 3. r50b 观察记录(新几何首件, 不作边界判读)

r50b 全链 OKAY(baseline/boot3/probe/stage/get, final 69,632
字节完整, SHA `f2b62e61…`), 且诊断新形态: boot3 与 probe
后各加 getvar product/serialno/unlocked 三连(unlocked yes
实拍)。**哨兵解码**: boot_args 六链、KVACALC0、x22/x23、
TPIDR000、EXC 三连、INT 三连、slot49=0xfffffff00702f7fa
在; **STACKS00(s18)/LINKADDR(s38)/INVPREF0(s39)/INVONE00
(s40)/PTPRE000(s41)/PTEEMPTY(s42) 相对 r42 时代归零**。

差分不可读为"执行后退", 两混淆因子未排除: ①r50b 用
**min 探针**(`-r50b-min-` 目录名), carrier 覆盖范围可能
截短, 后段槽位不在捕获内; ②patch 几何已重组(STACKS00/
LINKADDR 等仍在盘上 patch 树但偏移/写法有新旧两版并存,
startup patch 02:42 版与 stack-link 04:41/08:2x 版交叉),
槽↔符号映射已非 r39-r42 口径。**判读权归 Codex 的 r50b
record(现 MISS, 未收)** — 本线只存原始读数。

## 4. 盘态

record 欠账精确值本轮重数: 20261110 缺 13(r50b 新增)+
20261109 旧夜 6 = **19 笔**(085x 的 18 亦失真); LOG/CURRENT/
README 三文件仍 M; 13 件 patch untracked 不变; probe 三闸
零收口(仍 93b7978); 全套计数 98(08:43 轮实测, 本轮未重跑
无文件触线); 守护龄 ~4.53d, 保险丝 12:43 班; GO 未回。

## 5. 下轮盯点

①r50b record 补收(含 min 覆盖范围声明)→ 再作差分判读;
②Codex 会话是否还在推进(r50b 后无新动作 ~7 分钟);
③本勘误若在盘上被后续事实部分反驳(如 Codex 建了又删了
r49b), 以实物证据回补, 不改写本篇。

verify: 本轮全量实查链: glob+ls 双法点名 r49/r50 目录
(不存在清单为证); r49 record.md 全文复读(07:57 版);
r49 final.raw wc -c = 0 复测; r50b 九日志全文逐行实读;
r50b 双 raw 尺寸/SHA 实测; boot-r50b.log Sending 53344KB
亲见(≠r49 的 53310); artifact.json 实读 sha f3223ebb;
盘上 probe 名 -r50b-min- 实拍; grep STACKS00/LINKADDR/
PTPRE000 在 patch 树现状实读; build 脚本 docstring 行 2
T7001 既有口径实读; git log -1 af34316 时刻 08:48;
fastboot devices; pgrep 空 — 全部本轮新鲜执行。
作者: lingion <lingion@hrbeu.edu.cn>
