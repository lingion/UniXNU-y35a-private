# 守护独立解码 r51g + r51i — 11:4x,离线零设备(Codex 未写 record)

## 传输与新鲜度(两代全真)
- 两代 boot/probe/stage/upload 全 OKAY,final.raw 69632B。
- Y35AXNU2 戳(final): r51g=`77b616e4…`, r51i=`3c8cae85…` —— 与各自 manifest kernel_sha256 前缀逐位吻合; baseline 戳=上一代值, 链式自洽。shim 交接与图像代次身份坐实。
- CNTVCT final≠baseline: 探针本轮真执行。

## 核心观测: 仪器化核三代零新写入
- r51g/r51i 的 final 与 baseline 差异段**仅有** XNU2 戳与 CNTVCT 两段; carrier 全部 19 个非零槽(含 slot49=0xfffffff007032512)与 baseline 逐位同值。
- 即: 两代新核的 fault-publish 判读槽 **56-59 全零(连 FPBEFOR0 store-前标记都没出现)**, slot5/6/7 亦零; 现有非零槽全部是 f2a7c015 旧代核的 DRAM 留存。
- 与 092x "边界=INTSP000 后 LINKADDR/early-fault store 回归窗" 判定一致并收紧: 执行流根本没到 store-前标记, 主嫌窗内连"到达证据"都没有。两种待分辨: (a) 新核在更早处停/崩; (b) 新核 marker store 落错物理地址(写出到别处, carrier 自然干净)。093x 设计的 56/57 双操作数快照正是为分辨 (b), 但 58(=store 前)零说明连 (b) 的入口都没执行到——**(a) 升为唯一存活假设, 除非 store-前标记本身在盘上 patch 里就没进构建**。

## 建议 Codex record 采纳
1. r51g/r51i 判读请显式写"carrier 与 baseline 逐位同=零新运行时写入", 勿把留存阶梯当本轮证据(10:5x 口径的第三次兑现)。
2. 先离线核 r51i 实际构建用树上 FPBEFOR0 store 是否真在(哨兵 digest 对比, 防盘上编辑未入构建的 r50b 教训重演), 再决定下一代实验。
3. slot49 变化写者悬案: r51d 曾变(32604→32512), r51g/i 不再变(恒 32512)——写者最后活跃在 f2a7c015 代次窗口内, 后续代次核未触及。留账。

verify: python struct 两代 final/baseline 全量差分+64 槽逐位; Y35AXNU2 对 manifest 前缀逐字符; 设备零指令(只读 fastboot devices)。
