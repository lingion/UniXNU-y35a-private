# 心跳 20261110-075x: R49 以纯传输失败收场(Codex record 自判 transport-only 并停手)— 失败模式精确化为"probe boot 后首条 oem 命令必挂", 074x 镜像嫌疑升回头号并给出判别实验; XNU 推进已被传输问题卡住两代

时刻 07:5x。HEAD=7ad23cf(本线顶)。设备 efff9d92 fastboot
在列(07:58 复验),无 fastboot 进程 — Codex 已停手。零设备
指令。

## 1. R49 全链事实(逐份日志实读)

r48b 构建消失无产物(r48 编号弃), r49 于 07:48-07:51 构建
(kernel f2a7c015 / boot3 4c40962b / probe b041cfd4), 07:51-
07:52 实跑, **07:57 record.md 随跑收**(Codex 未欠账):

- baseline stage+get_staged: **OKAY**(69,632 字节完整)✓;
- boot-r49: Sending 53310KB OKAY + Booting OKAY, 设备重枚举
  ✓;
- boot-probe-r49: Sending 184KB OKAY + Booting OKAY(此仅
  宿主侧发送完成, 不证设备执行)✓;
- **final-stage(`oem y35a panic`): usb_write e00002ed
  FAILED** — probe boot 后第一条命令即挂;
- final-get-staged: 再败 e0004061; final.raw 0 字节;
- record 尾注: "A later retry was not started" — Codex 停;
- record 自评: transport evidence only, 不扩不撤 XNU 边界;
  离线四闸全绿 96/96。

## 2. 模式精确化与 074x 裁决重评

**失败定位: baseline(boot3 后)两次成功, probe boot 后必
失败**(R47: probe 连 boot 3 次 + stage 两败一成一空; R49:
同型)。R47/R49 换了两批 inputs(含全新 probe 镜像)仍同型
→ 074x 我写"设备端/镜像状态事件"方向仍对, 但候选排序更新:

1. **头号(升): probe 镜像使设备 boot 后进入异常**(USB 半
   死/非 fastboot 态), 宿主重枚举后靠 LK 超时恢复 — 与
   "R44-46 跳号 + header/L1 哨兵批引入 + Codex R47 连 boot
   三次自救"全链吻合;
2. 次: macOS 对二次重枚举的驱动绑定竞争(与镜像无关)。

**判别实验(报回项, 零新设备指令即可离线设计)**: 只 boot
boot3 后立刻连发 3 轮 oem panic+get_staged — 若稳定 OKAY,
再单跑一次 probe boot 后立即 stage — 若必挂, 假设 1 实锤,
应回退 probe inputs。回退目标实测在案: 盘上
`out/y35a/readback-probe-20261109-r43-phase-carrier/` 现件
SHA `e743c5ef9513727e…`(本轮 shasum 实拍, R43 实跑用件,
当时 final 传输成功; 同 session 06:38 重建)。Codex 停手期间
此实验无人跑, 已登记。

## 3. 盘态与治理

- record 欠账 18(16@064x 全量 + R42 + R47 新增; R43 与
  R49 均已收不计); 13 件 patch 仍 untracked; LOG 停
  R43 段仍 M;
- **XNU 推进已卡两代**(R47/R49 无新边界), 若 Codex 持续
  停手, 下一条离线可推 = probe inputs 回退复现(纯构建侧);
- probe 三闸零漂移; 全套 96 OK(R49 record 亦报 96/96 互
  证); 守护龄 ~4.50d, 心跳正常; 保险丝 next 12:43。

## 4. 报回用户(非指令)

连续两代传输失败集中在 probe boot 后, 头号嫌疑是近期哨兵
批的 probe 镜像状态异常而非线缆; 物理侧用户可做的最小动作
= 换 USB 口/重插线以排除假设 2, 但按判别实验顺序, 软件侧
回退验证优先且无需用户动手。Codex 若长停, 建议唤醒其会话
续判。

verify: R49 五份 .log 全文实读(错误码 e00002ed/e0004061
亲见); record.md 全读(sha 三件+自评逐字); baseline 69632/
final 0 字节 stat 实测; ls -dt r48/r49 目录实查(r48 全无
产物实拍); docker exec 容器内 *r48* 空 glob 实查; fastboot
devices 07:58 复在; pgrep 空实拍 — 全部本轮执行。
作者: lingion <lingion@hrbeu.edu.cn>
