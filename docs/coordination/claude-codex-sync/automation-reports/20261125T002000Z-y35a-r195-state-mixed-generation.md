# R195 STATE mixed-generation handoff — 20261125T002000Z

## 影响

`STATE.md` 的 milestone 已更新为 R195，但 operational body 仍以 R190 为最后设备状态、Current gates 和 Next。沿正文操作的下一会话可能重复已封存 R190，或忽略 R193–R195 的既有裁决。该问题不改变 runtime qualification，也不授权设备操作。

## 事实（static）

1. `STATE.md:4` 为 `Milestone: R195 boundary after PECFGRET and before ARMRADR0.`
2. 同文件 `STATE.md:6` 仍称 R190 是最后设备观测；`STATE.md:10-12` 的 Current gates 仅列 R190；`STATE.md:16-17` 仍要求不重复 R190 并添加 PEFCGOK0 与 ARMARGOK 之间的 marker。
3. `CURRENT.md:1-3` 与 `LOG.md` 最新条目均已记录 R195；R195 final raw 为 `cf92157bb7e5a4aff7e995831cec1682263caf8f227f398b1a52a14e8aed5e44`。
4. `R195-adjudication.json` 的 `device.last_observed` 是 `verified unlocked fastboot`，`persistent_writes=false`；`R195-adjudication.md` 确认有效边界仍在 PECFGRET 后、ARMRADR0 前。
5. 本次只读核对时，CURRENT/LOG 刚完成同步而 STATE 仅更新标题；未修改任何共享文件。

## 待确认

- 主线是否仍在进行后续 STATE 原子更新；若是，本报告只描述采样时的不一致。
- R196 尚未被本报告提升为当前里程碑。

## 推断

STATE 发生了非原子部分更新：milestone 标题领先于设备状态、当前门和下一步正文。独立本地证据（R195 JSON/Markdown 与 CURRENT/LOG）一致支持 R195，而非正文的 R190 操作队列。

## 单一步骤建议

由主线所有者在启动 R196 前原子重建 `STATE.md`：以 R195 的 kernel/raw 绑定、最后观测设备和边界替换 Current gates/Next，把 R190 明确降为历史记录；保持 `device_run_allowed=false`。

## 证据 SHA-256

| 路径 | SHA-256 |
|---|---|
| `/Users/lingion_k/unixnu-research/UniXNU-y35a/STATE.md` | `5b5375e02ff639a4904949d1fff5fc8385b5d26016c006c15c5ebb638e67a1fb` |
| `/Users/lingion_k/unixnu-research/UniXNU-y35a/docs/coordination/claude-codex-sync/CURRENT.md` | `266b853852ebf7d6447e2df0c732adf02cfd77eadb4d6807cffa7b4c62a21ae1` |
| `/Users/lingion_k/unixnu-research/UniXNU-y35a/docs/coordination/claude-codex-sync/LONG-RUN-STATE.md` | `5401eb1e4258e0b3f221799a4f237376ffc435800965968f0faf4c828c75d23a` |
| `/Users/lingion_k/unixnu-research/UniXNU-y35a/docs/coordination/claude-codex-sync/LOG.md` | `bc7fe817cc1088b51e37e3a5279417b4bd751c4c30472464abc95e8c806d923d` |
| `/Users/lingion_k/unixnu-research/reboot-checkpoints/R195-radar-parse-paired-run-20261125-01/R195-adjudication.json` | `8f89dbccba4dc70a634f135015e1302230b568cf4d4e384df500c176dc40458f` |
| `/Users/lingion_k/unixnu-research/reboot-checkpoints/R195-radar-parse-paired-run-20261125-01/R195-adjudication.md` | `b2b963d972acf396bbee7d6af3f9f6705bbfdb16fc8ab106c6320089ccc2fbe4` |

未运行构建或设备操作；未能直发 Codex thread。
