# R75 原生 XNU 重链命令

记录日期：2026 年 11 月 11 日。

本流程使用仓库原生 Xcode runner 和已准备好的 XNU 4903、fakeroot、iPhoneOS 16.4 SDK overlay。默认输入仍是 runner 中记录的 xnu-4903.270.47 固定源码、v5 的 `source-worktree-diff.patch`、provenance 与本地原生工具链资产。新增 `--patch` 按命令行顺序应用于该基础树；runner 不会自动追加下列补丁。

R75 对应的显式补丁顺序如下：

| 顺序 | 补丁 | SHA-256 |
|---|---|---|
| 1 | `patches/xnu/native-y35a-low-vector-v1.patch` | `daca721143890df805fc3d65d7bb306575e12a736f0a547810b46ed68d12a7ff` |
| 2 | `patches/xnu/native-y35a-a53-no-apple-hid.patch` | `a36060b2f9997b44ea915eb12f28cba3114726939fcd2f52713a57cf25247ef0` |
| 3 | `patches/xnu/native-y35a-low-vector-v2.patch` | `2dc0d59d445d72212140e4256d5d47d7c84eeb88b652955cffbe9cced069cda8` |
| 4 | `patches/xnu/native-y35a-a53-enable-fp.patch` | `a8e813f8a2c7f501ea68a7e7aa6b0d49087c87e2a9d0abcd04fb6c92577962c7` |
| 5 | `patches/xnu/native-y35a-post-console-vector-v3.patch` | `e261ec24eb9050461ac9014f4e722b00a90b36165199d154de949f35409336ef` |
| 6 | `patches/xnu/native-y35a-panic-reason-v1.patch` | `04e2c3cc9717c62270284c7c6a117532a6135e80732ca5e06801979828b465f8` |
| 7 | `patches/xnu/native-y35a-panic-reason-enable.patch` | `c67cee36329ee9fae7cececf68e5c8d3086ee3efb61343eb1ce2dfbf30e44726` |
| 8 | `patches/xnu/native-y35a-no-classic-s2r.patch` | `5f95c60243a858ff7a9586f4587a060a56717a845fbeb7385b17531503a3e17f` |

在仓库根目录执行：

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/build-xnu-4903-native.py \
  --y35a-a53 \
  --y35a-low-vector \
  --patch patches/xnu/native-y35a-low-vector-v1.patch \
  --patch patches/xnu/native-y35a-a53-no-apple-hid.patch \
  --patch patches/xnu/native-y35a-low-vector-v2.patch \
  --patch patches/xnu/native-y35a-a53-enable-fp.patch \
  --patch patches/xnu/native-y35a-post-console-vector-v3.patch \
  --patch patches/xnu/native-y35a-panic-reason-v1.patch \
  --patch patches/xnu/native-y35a-panic-reason-enable.patch \
  --patch patches/xnu/native-y35a-no-classic-s2r.patch
```

runner 为每轮分配新的 `/tmp` 输出目录，并保留失败现场。完成后从该目录的 `kernel-artifact.json` 和 `build-provenance.json` 读取实际产物路径、哈希、工具链、补丁哈希、profile 和命令。不要给重链产物套用旧 kernel SHA 或旧 readback manifest；manifest 必须绑定本轮新内核。

两个 profile 开关默认关闭。R75 命令显式打开后，build make 命令把 `XNU_NATIVE_EARLY_FAULT`、`XNU_Y35A_A53`、`XNU_Y35A_LOW_VECTOR` 一并传入 XNU 4903 实际消费的 `OTHER_CFLAGS`。MakeInc.def 将该变量放入 `CFLAGS_GEN` 和 `SFLAGS_GEN`；genassym 使用 `${CFLAGS}` 编译。命令不再设置 `CFLAGS_EXTRA` 或命令行 `SFLAGS_ARM64`，因此 MakeInc.def 的 ARM64 架构参数和 `SFLAGS_ARM64=$(CFLAGS_ARM64)` 展开关系得以保留。profile 同时记录在 plan 输出及 build provenance。

基础源码、v5 的二十五项变更和补丁文件均由调用者显式选择或由现有默认值指定；本命令不会修改基础源码，也不会隐式加入额外补丁。R76 若包含新的 XNU 源码补丁，应在本序列之后按其独立证据追加 `--patch`，并保留新的产物哈希与验证记录。
