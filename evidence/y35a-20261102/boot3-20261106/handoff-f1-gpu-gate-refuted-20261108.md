# Handoff Finding 6 "GPU GEN6 结构闸门"复核: 引用的符号不存在, 归因段落也不存在 (2026-11-08 21:4x)

上一轮 (21:2x) 复核过 handoff 的 Findings 1/2/3; 其证据文件里写了"建议下轮
优先核 GPU 闸门"。本轮对该声明 (handoff Finding 6) 逐件机械化核实, 结论:
**原句不成立——它引用的内核 UAPI 枚举在可查各处均不存在; 它自称的出处
§8.7 在该文件里没有此节 (该串最接近的实存是 §7 一处小写 gen6, 语义相反,
疑为失真源头)。其引用的枚举与"ISA300"均为幻影。** 真实约束另有三条,
调查文件本身反而记录对了。

## 检查项与实跑证据

| # | 声明要素 | 复核命令 | 结果 |
|---|---------|---------|------|
| 1 | handoff 称"闸门记录在 gpu-adreno-a3xx.md §8.7" | sed -n '137,175p' + grep §目录 | 该文件 §8 是微代码问题, §9 是可行性判词, **无 §8.7**; `ISA300` 与 `freedreno_gpu_id_gen` 全文 **零命中**。唯一近似串在 §7 第 134 行(小写): kits/AdrenoFirmware 的 "AdrenoHfi… = **gen6/gen7 GMU boot** — NOT applicable to a3xx"——**疑即 Finding 6 失真源头**: "gen6 GMU 不适用于 a3xx"(陈述其不适用)被转述成了"GEN6 枚举缺失构成 a3xx 结构闸门"(反向引用)。 |
| 2 | 符号 `enum freedreno_gpu_id_gen`(值 GEN4/GEN5/GEN7/GEN8/GEN9) | gh api search/code 全库 `total_count`; repo-scoped torvalds/linux 两次 | 全库 **0**, repo-scoped **0**, "enum adreno_gen in include/uapi" **0** |
| 3 | 现行内核 UAPI 是否有任何 gen 枚举 | gh api contents include/uapi/drm/msm_drm.h @master (23175 B 成功落盘) | grep `gen` 零行、grep `GEN` 零行; 参数表止于 MSM_PARAM_UCHE_TRAP_BASE 0x14, 内核只透传 CHIP_ID |
| 4 | 板引用树 msm8916-mainline/linux @wip/msm8916/7.0 同 header | 同法落盘 528 行 | 无 gen 枚举 (仅 MSM_PARAM_GPU_ID 0x01) |
| 5 | Mesa 侧 a3xx 现实支持 | survey §3.1/§3.2 (f1 已 VERIFIED: gallium a3xx 子目录 fd3_* 26 文件实存) + 本轮 GitLab isa 目录 listing (14 件全 ir3*) | Gallium GL 有 fd3 (a3xx 可用); ir3/turnip (Vulkan) 仅 a6xx+ |

## 判读

- **"Mesa display 路径的 GEN6 结构闸门"这句话是幻影引用**: 被引符号查无
  此物、被引段落查无此节。按 contributor-data-truth-rule 应整条降级为
  UNVERIFIED, 不得作为路线依据。(与 handoff 自身方法注记的"zero-hit 必须
  用 contents/trees 重证"纪律一致——本轮正是这么做的, 且本地有全文落盘
  佐证, 强于搜索计数。)
- **该路径真实的结构约束是三条, 且调查文件 §9 自己写对了**:
  (a) 显示 scanout 归 MDP5, framebuffer 里程碑不依赖 GPU (survey §9.3a);
  (b) a3xx 无 Vulkan (turnip=a6xx+), GL 侧 fd3 存在 (survey §3.3);
  (c) 对 XNU 项目最根本的一条: **Mesa 整体跑不了 XNU** (gallium winsys 绑
  Linux DRM/GEM), 3D 只能项目侧走 AdrenoMetal/AdrenoPM4 形状——这才是
  "结构闸门", 与 GEN6 枚举无关 (survey §9.2/9.3)。
- handoff Finding 6 疑是把 (b) 的 "ir3/Vulkan 仅 a6xx+" 转述串位成了内核
  UAPI 枚举缺失。方向提醒没错 (GPU 3D 是远期深坑), 但依据链必须重写。

## 对总盘的影响

- 上游证据调查 (12 文件) 质量总体过硬 (§3/§8 的本轮抽查项均与其 VERIFIED
  标记自洽), 唯 handoff 摘要文件的 Finding 6 一句失真——引用它时按本文件
  判读为准。
- 不改变当前阻塞 (boot4 panic 取证 = lk2nd 侧 boot 前取 FUNK, 上轮定案)。
- f1 会话的 handoff 本体与 untracked 文件仍归其所有者, 本心跳未动。
