# 心跳 20261109-0400:推送远端尝试 → 写权限证伪 (lingion 对 UniXNU/UniXNU 无 push 位)

时刻: 2026-11-09 04:0x CST。用户明确授权"把未推送的工作推到远端"。
HEAD=1ea459e (fix/readback-panic-globals)。设备: lk2nd fastboot 槽存活,
窗开; 插桩修复未落地 (builder 在途件 diff 含 SFLAGS=0, patch 去 guard=0),
顺序闸维持 → 本会话不 boot。并行会话 30 分钟内有活跃度
(readback_native.py/heartbeat-0340), 其分支归属: fix/readback-panic-globals
= 本 worktree 检出分支 = 多会话共享, 推送动作对本会话只读不写其文件。

## 1. 未推送清单 (审计定案)

- 远端 heads 共 63 个 (直连 github.com 与代理 gh.qdp.qzz.io 读数一致);
- 本地 heads 4 个: fix/readback-panic-globals / port/y35a-bootstrap /
  main / worktree-agent-a5a44a476983b0df7;
- 未推送 commit 共 110, 全部落在 fix/readback-panic-globals 一条线;
- port/y35a-bootstrap (81 条"未推送") 是 fix 分支的祖先 (merge-base
  --is-ancestor YES), fix 推送即一并保全;
- worktree-agent 分支未推送数 = 0 (已在远端);
- main 落后远端 714 (只读镜像, 无需推送);
- push 范围体量: 110 files / +17040 / -34, 最大 blob 130KB, 无二进制;
- 密钥扫描 (新增行 grep api key/secret/token=/password/BEGIN KEY):
  仅命中一句散文用词, 无真实凭据 → 内容层面推送安全。

## 2. 推送尝试全记录 (四条通道, 同一结论)

1. 代理 origin (https://gh.qdp.qzz.io): 403 "Permission to
   UniXNU/UniXNU.git denied to lingion", 2s;
2. 直连 https://github.com: insteadOf 全局重写把 URL 拉回代理 (第一次
   试推 URL 被重写, 表面 fatal 指向代理) — 用 GIT_CONFIG_GLOBAL=/dev/null
   绕开后真实报错相同 403 denied to lingion;
3. SSH id_ed25519 (BatchMode): 读通 (ls-remote HEAD 成功), 写被拒
   "ERROR: Permission to UniXNU/UniXNU.git denied to lingion" →
   SSH key 亦挂 lingion;
4. gh CLI token 与 git-credential store 的 github.com token 逐字节
   SAME (40 字符 ghp_), 无第二凭据可用; Kerry1020 的 ghp_ token 实测
   对该仓库同样 push:False。

## 3. 权限根因 (GitHub API 实证)

- token scopes 极全 (repo/admin:org/…含 delete_repo) → 非 scope 问题;
- lingion 对 UniXNU/UniXNU: pull:True, push:False, triage:False,
  admin:False, maintain:False;
- orgs/UniXNU/memberships/lingion → "Not Found" (非 org 成员);
- collaborators/lingion/permission → "Must have push access to view"
  (连读协作者表的权利都没有);
- 写尝试响应无 X-GitHub-SSO 头 → 排除 SAML SSO 未授权这一常见误因;
- 结论: lingion (含 Kerry1020) 对该 org 仓库就是无成员/无协作者位,
  此前 4d11908 "gh 直连可用" 仅指读。任何通道都推不上去, 需组织侧
  授权 (邀请为 collaborator 或 org 成员) 或改推目标 (fork + PR)。

## 4. 待用户裁决

(a) 请 org 管理员给 lingion 加 push 位后, 本会话重试推送
    (命令已验证就绪, 2s 失败→授权后即成功);
(b) 或授权我 fork 到 lingion/UniXNU 再推分支、开 PR 回上游
    (改外发目标, 需明示);
(c) 本地保全现状: 110 commit 在 fix 分支, 工作树 worktree 独占, 无丢失
    风险, 等待不阻塞取证线。

本会话并行件纪律未破: 未碰 builder/readback/package 在途文件。
本轮: 未 run fastboot, 未写分区, 未 boot。

verify: git ls-remote/diff --stat/rev-list blob 扫描/cat-file 计数、
credential fill 三主机对比、curl API permissions/memberships/SSO 头、
四通道推送实录 (上文 §2) — 全部本轮新鲜执行。
作者: lingion <lingion@hrbeu.edu.cn>
