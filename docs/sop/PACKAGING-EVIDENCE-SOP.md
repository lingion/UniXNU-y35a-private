# UniXNU 打包与证据 SOP

## 单一实验合同

每个候选必须有一个 JSON 实验合同。所有后续入口只接受该合同中的路径和 SHA。

```json
{
  "identity": {"run_id": "Rxxx", "revision": 1},
  "source": {"root": "...", "commit": "...", "tree_sha256": "...", "patches": []},
  "build": {"provenance": "...", "kernel": {"path": "...", "sha256": "..."}},
  "package": {"manifest": "...", "image": {"path": "...", "sha256": "..."}, "dt": {}},
  "probe": {"regular": {}, "clear": {}, "record_map": {}},
  "controls": {"positive": {}, "negative": {}},
  "run": {"device_run_allowed": false, "max_seconds": 600, "runs": 1},
  "verdict": {"status": "offline-only"}
}
```

## 检查顺序

1. 校验所有输入存在、大小和完整 SHA。
2. 校验 source commit、tree hash、patch 顺序和 `git apply --check`。
3. 校验 build provenance 与 kernel SHA。
4. 校验 linked order、symbol、marker owner、slot、offset、宽度和对齐。
5. 校验 package manifest 的 kernel、entry、DT、boot args、rootfs、trustcache、container 和命令闭包。
6. 校验 DT `source_type`。derived DT 必须包含原始来源和 derived 文件的双向 SHA。
7. 校验 regular/clear probe 绑定 package 和 kernel，地址从 manifest 推导。
8. 校验正对照和负对照。
9. 只有以上全部通过，才允许生成运行计划。运行计划只能把统一 gate 计算出的许可写成 true。
10. runner 不得修改许可。candidate 结束后许可立即回落为 false。

macOS metadata scans may encounter root-owned or sealed files whose xattrs are not readable by the hosted runner user. Preserve xattrs in the tree identity; only retry an explicit permission-denied xattr read with non-interactive privileged read-only access. Do not convert unreadable metadata to an empty attribute list.

## 判定

- `CONFIRMED` 需要原始证据、完整镜像哈希、可复制命令和停止条件对照。
- `REFUTED` 需要同等证据证明假设不成立。
- 缺 raw、缺 positive control、缺来源闭包或 gate 不适用时，写 `UNVERIFIED`。
- candidate/final 缺失时，禁止判断 marker 是否执行。
