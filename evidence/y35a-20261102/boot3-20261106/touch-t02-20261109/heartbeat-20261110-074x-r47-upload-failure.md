# 心跳 20261110-074x: R47 终传三连败目击 — boot 链全 OKAY 但 probe 段 no data staged + get_staged 双 USB e00002ed, 两 final raw 均 0 字节空壳; baseline 同 session 上传成功排除线因; R44-46 跳号; 设备瞬离 = Codex 拔插重枚举

时刻 07:3x。HEAD=cb92c59(本线顶)。设备 efff9d92 已回
fastboot(07:36 复在), adb 仅 sleepy 仿真器无涉。零设备指令。

## 1. R47 失败形态独立取证(不代判根因)

Codex 07:32 构建 R47(R44/45/46 无目录, 三连跳号), 07:34-
07:35 实跑。本线逐份读传输日志+python 哈希:

- `boot-r47.log` boot3: 53310 KB Sending OKAY + Booting
  OKAY ✓;
- `boot-probe-r47.log`: probe 被**连 boot 三次**, 全
  Sending/Booting OKAY — 异常操作形态(重试?), 归 Codex
  解释;
- `final-stage.log`: 前两轮 `oem y35a panic` stage 命令
  **usb_write e00002ed FAILED ×2**(设备此刻掉线), 第三轮
  成功返回 "Staged.";
- `final-get-staged.log`: 拉取报 **`remote: 'no data
  staged'` FAILED** — stage 说成功了但设备上无货;
- `final-r47-retry.raw`: 重试再败 usb_write e00002ed;
- **两个 final raw 均 0 字节**(SHA e3b0c442… = 空文件
  标准哈希, 双件实测);
- baseline 同 session 早前上传 **OKAY**(`e44c15f6…` = R43
  retry 链式 ✓)— USB 线/口当时是通的。

## 2. 裁决: 设备端/镜像状态事件, 非宿主传输

baseline OK + probe 后 stage/get 交替 usb_write 失败 + "说
Staged 却 no data staged" 的组合, 指向 **R47 probe 执行后
设备状态异常**(bootloop/半死/USB 重枚举抖动)而非线缆。
三次 boot probe 暗示 Codex 当时已察觉并自救。**R44-46 跳号
+ R47 失败**合读: header/L1 哨兵实验(moving to 0x970/0x978
复用槽那批)可能引入了 probe 镜像自身问题 — 假设级, 不作
结论, 归 Codex; 若下轮 R48 恢复 + record 补写则自愈确认。

## 3. 盘态

record 欠账 17+R47(未写)≈ 18; LOG 仍 M; 13 件 patch 仍
untracked; probe 三闸零漂移; 全套计数无触线不重跑(06:41
实测 Ran 96 OK); 守护龄 ~4.50d(<5.2 闸), 心跳 07:21 班正常
(本次即其后继)。GO 未回。

## 4. 下轮盯点

①R47 是否 Codex 主动补 record/判废; ②R48 起传输恢复与
HDRLAOD0 预登记仍有效(若 slot46/47 出文字按实际字节对);
③设备若再现长跑不在列表且无 boot 日志新增, 按失联升级
路径报告用户。

verify: 六份 .log 全文逐份实读(final-stage 的 e00002ed×2 +
"Staged." OKAY 同档并存亲见); python3 双 raw 哈希实测 =
e3b0c442(0 字节); baseline e44c15f6 链式对照 R43 retry;
ls -dt R44-46 glob 无匹配实查; fastboot/adb 双列表复在;
pgrep 无 fastboot 残留 — 全部本轮执行。
作者: lingion <lingion@hrbeu.edu.cn>
