# UniXNU CI 运行边界

`unixnu-validation.yml` 已经在 GitHub Actions 上执行 Python 编译检查、实验合同入口检查、目标和 SOP 文件检查，以及已有的主机测试。

XNU native build 需要精确绑定以下输入才能进入 CI。

- XNU source commit 和 source tree hash
- 有序 patch manifest 与每个 patch 的 SHA-256
- SDK、Xcode 和工具链版本
- source provenance、fakeroot、SDK overlay 和 xcrun wrapper
- build profile、jobs、run root 和 expected kernel SHA

这些输入目前仍有一部分只存在移动硬盘的 R207 外置 run root 中。它们进入私有仓库前，不能把本机编译伪装成可复现 CI 编译。目标是先把 `experiment.json` 和有序 patch manifest 同步，再添加 manifest 驱动的 macOS workflow。启用 native build 后，本机只执行真机专属和 CI 无法访问的步骤。
