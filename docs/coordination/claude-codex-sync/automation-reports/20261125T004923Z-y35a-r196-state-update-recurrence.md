# R196 STATE atomic-update recurrence — 20261125T004923Z

## 影响

上一份 R195 报告建议原子重建 STATE；R196 同步时仅再次更新 milestone，Device、Current gates、Next 仍为 R190。下一会话若沿正文操作，仍可能重复 R190 或忽略 R196 的有效边界。这是同一流程缺陷在新一代裁决上的复发，不是重报 R195 数据。

## 事实（static）

1. `STATE.md:4` 为 R196 milestone；`STATE.md:6` 仍以 R190 为最后设备观测，`STATE.md:10-12` 仍仅列 R190 gates，`STATE.md:16-17` 仍以 R190 为 Next。
2. R196 JSON 状态为 `adjudicated`，final raw SHA 与本地 `final.raw` 实测一致：`8f5206cf75c1eb0c8c59f283ec73dba0ce461f930822529ea9cdf83f9751e828`。
3. R196 裁决边界为：Final contains ARMPGBEG but not ARMRADR0 or ARMPGSZ0. Boundary is after ARMPGBEG and before ARMRADR0.
4. CURRENT、LONG-RUN-STATE、LOG 最新标题均已到 R196；STATE 仅标题领先。
5. 上一份 `20261125T002000Z-y35a-r195-state-mixed-generation.md` 已给出原子更新建议；本报告确认该问题在 R196 复现。

## 待确认

- 主线是否会把 STATE 正文作为单独后续操作；若是，本报告只记录采样时状态。
- R197 正在构建，不在本报告范围内，也未复制其调查。

## 推断

手工只改 STATE 标题不足以完成同步；缺少“标题与正文同一次写入并复核”的收尾门。该推断由 R195、R196 两次相同模式与各自独立裁决交叉支持。

## 单一步骤建议

主线所有者在 R197 设备阶段前，用一次写入更新 STATE 的 Device、Current gates、Next，并在同一离线检查中确认正文不再含 R190 操作指令；保留 R190 为明确历史记录。

## 证据 SHA-256

| 路径 | SHA-256 |
|---|---|
| `/Users/lingion_k/unixnu-research/UniXNU-y35a/STATE.md` | `cdc46e9968da294999b6b1e32bcb78ff11aa056265e32eefc888bf98a518efa4` |
| `/Users/lingion_k/unixnu-research/UniXNU-y35a/docs/coordination/claude-codex-sync/CURRENT.md` | `f303687c3a13848b47acebf606030ab284b8e6ea1995ecca82ddb72ae748339a` |
| `/Users/lingion_k/unixnu-research/UniXNU-y35a/docs/coordination/claude-codex-sync/LONG-RUN-STATE.md` | `c63f8375e7ae7cf96d75c46a215dcf78cb73a26c0994f9ab568060a72fdfe980` |
| `/Users/lingion_k/unixnu-research/UniXNU-y35a/docs/coordination/claude-codex-sync/LOG.md` | `04b2d85f5b2658356c7786bddb67f58b18b9b9e87612e62c0368f80d12c4d8eb` |
| `/Users/lingion_k/unixnu-research/reboot-checkpoints/R196-page-config-entry-paired-run-20261125-01/R196-adjudication.json` | `05d420833bd300fae89387fb1df3b3bdfee44418150951e46477a1fe1e907b6d` |
| `/Users/lingion_k/unixnu-research/reboot-checkpoints/R196-page-config-entry-paired-run-20261125-01/R196-adjudication.md` | `1986128333f5453de477bbbd0bf15f145f7b4962e6b88a0e2990441b592b4fd4` |
| `/Users/lingion_k/unixnu-research/UniXNU-y35a/docs/coordination/claude-codex-sync/automation-reports/20261125T002000Z-y35a-r195-state-mixed-generation.md` | `9165330012d43d60c4060e8dc0e74221a29204051abce6e146cec41999f661b5` |

未修改共享文件、未运行构建或设备操作；未能直发 Codex thread。
