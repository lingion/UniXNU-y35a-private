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

## 长任务

长任务只启动一个明确的 run root。每 30 至 60 秒核对真实进程、退出码和产物。进程存在不等于成功。等待期间只做与当前输入不冲突的参考检索、日志分析或独立裁决。

## 状态同步

每次状态变化同时更新 `LIVE-TARGET.md`、`STATE.md`、`CURRENT.md`、`LONG-RUN-STATE.md` 和追加式账本。失败候选写入裁决后，所有摘要必须标记已失败、禁止重复和下一条离线动作。

## 结束

候选成功、失败或不可判定都必须生成裁决。缺 candidate/final raw 时只能写 `UNVERIFIED` 或 `INCONCLUSIVE`。禁止把 transport 断联直接写成 XNU fault。
