# UniXNU 主线执行 SOP

## 目标

让每个候选从设计到裁决使用同一份实验合同，避免状态、哈希、权限和下一步分裂。

## 开工

1. 读取 `GOAL.md`、`LIVE-TARGET.md`、`STATE.md` 和账本末尾 30 条。
2. 读取 `docs/sop/LESSONS.md` 中相关条目。
3. 检查活动进程、设备锁和当前候选目录。
4. 检查相同假设和相同镜像哈希是否已有裁决。
5. 检查 `REFERENCES.md`，再检索本地参考仓库。没有命中就写 `NONE-FOUND`。
6. 写 `experiment.json`，冻结输入、假设、变量、停止条件和后续动作。

## 本机执行限制

UniXNU 的编译、测试、静态门禁、diff 检查、package/image 验证只能在 GitHub Actions 执行。本机仅可编辑文件和被动阅读代码、日志与状态；不得运行 `git diff --check`、测试、lint、verifier、构建或 package 命令。误执行的结果必须明确排除，不能作为验收证据。

运行本机只读 Git 盘点前，先逐条审阅将执行的 shell 命令；`git diff --check` 无论单独执行还是附在 `git status`/`git diff --stat` 命令串后面都属于被禁止的静态验证。需要核对空白错误时，只使用 GitHub Actions 中的 `Check tracked text` 步骤。

为避免 shell 批次意外混入静态门禁，本机 UniXNU 工作树盘点只允许独立执行 `git status --short --branch`、`git rev-parse`、`git log`、`git diff --stat` 和指定路径的只读 `git diff -- <path>`。每条命令在工具调用前单独核对参数；不得将多个命令用 `;`、`&&` 或其他 shell 控制符串联，不得将 `git diff --check` 与状态或 diff 命令串联，也不得使用汇总脚本或别名隐藏检查项。若误执行，立即把该结果排除为证据、记录精确命令和 lesson，再继续以 Actions 为准。

## 长任务

长任务只启动一个明确的 run root。每 30 至 60 秒核对真实进程、退出码和产物。进程存在不等于成功。等待期间只做与当前输入不冲突的参考检索、日志分析或独立裁决。

## 状态同步

每次状态变化同时更新 `LIVE-TARGET.md`、`STATE.md`、`CURRENT.md`、`LONG-RUN-STATE.md` 和追加式账本。失败候选写入裁决后，所有摘要必须标记已失败、禁止重复和下一条离线动作。

## 结束

候选成功、失败或不可判定都必须生成裁决。缺 candidate/final raw 时只能写 `UNVERIFIED` 或 `INCONCLUSIVE`。禁止把 transport 断联直接写成 XNU fault。
