# UniXNU 本地参考仓库索引

索引根 `/Volumes/Mobile/unixnu-research/UniXNU-y35a/upstream-refresh/2026-11-11/sources/`。以下 commit 为当前本地目录读取结果，使用前重新核对。

| 仓库 | 本地路径 | 当前 commit | 主要用途 |
| --- | --- | --- | --- |
| ArmCpu | `sources/ArmCpu/repo` | `81a77736d32d980ad65fd1a55cafcf7ced3c0f10` | GIC、timer、IPI、多核启动 |
| ArmDTPlatform | `sources/ArmDTPlatform/repo` | `81a77736d32d980ad65fd1a55cafcf7ced3c0f10` | DT platform 入口 |
| DarwinBoot | `sources/DarwinBoot/repo` | `81a77736d32d980ad65fd1a55cafcf7ced3c0f10` | arm64 loader、RAM disk handoff、entry |
| linux-msm8916 | `sources/linux-msm8916/repo` | 81a77736d32d980ad65fd1a55cafcf7ced3c0f10 | MSM8916 DT、clock、pinctrl、regulator、MMC、USB、display |
| lk2nd-msm8916-mainline | `sources/lk2nd-msm8916-mainline/repo` | 81a77736d32d980ad65fd1a55cafcf7ced3c0f10 | LK/lk2nd 启动路径和 fastboot 行为 |
| xnu-current | `sources/xnu-current/repo` | 81a77736d32d980ad65fd1a55cafcf7ced3c0f10 | XNU 当前对照 |
| xnu-ios12 | `sources/xnu-ios12/repo` | `494ffe1c29d37ca720c37328feb83069c9641b67` | XNU 4903 / iOS 12 对照 |

## 使用规则

写代码或解释失败前，先在相关仓库中查函数名、符号、compatible、寄存器、错误串和启动顺序。账本记录具体 `path:line`、commit 和许可证。无命中记录 `NONE-FOUND` 与检索范围。
