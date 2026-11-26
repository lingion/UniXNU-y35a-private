# 守护 19:0x — r68e 构建中静态预审: 一个采纳好评 + 两个跑前缺陷(零设备, 不碰构建)

## 采纳好评(判决实验地基已修)
PREMMU00 字样被改成唯一字 **R68EPRE0**(x14 立即数逐字节重算='R','6','8','E','P','R','E','0' 正确)。slot16 物理 0xa0b7c880 落在 early-fault-record 捕获窗(0xa0b7c800..0xa0b7c980)内 → 若清零真执行, 旧 PREMMU00 留存被清; 若 r68e 核到达, 新 R68EPRE0 出现。**"本轮 vs 留存"混淆被这步消掉**, 守护 18:4x 提的问题在源头解决(疑似吸收接管条目或守护报告)。

## 缺陷 1(判决六字全部落在捕获窗外)
r68e 新见证写 [x20+0x9d0..0x9f8] 六字(slot58-63 物理 0xa0b7c9d0..0xa0b7c9f8), 但盘上 r68d probe manifest 最大记录只到 handoff-witness 0xa0b7c9c0..0x9d0(16B), 其后**无任何窗**; readback_native.py 与 git diff 均未见 0x9d0+ 扩窗配置。Codex 接管条目自己写"capture that aligned 40-byte window plus slot 63 ... as one named --extra-pa window"——行动项尚未见于盘上。r68e 核在构建中, **probe manifest 若沿用 r68d 配置, 六个判决字在 final.raw 里根本没有对应字节, 实验空转**。跑前必须扩 --extra-pa ≥ 0xa0b7c9d0/0x30(注意对齐与 pram 边界)并过 layout/transport 双闸。

## 缺陷 2(HDRLAOD0 同款 movk 陷阱二次命中)
两个新 marker 的注释名与立即数字面不符(逐字节重算):
- 注释 PUBLPR00 → 实写 **PUPBRE00**(m16=0x4250 应为 0x4C42, m32=0x4552 应为 0x5250; 'BL' 对位翻成 'UP'+'PB')。
- 注释 PUBLPS00 → 实写 **PUPBTS00**(m16 同错, m32=0x5354 应为 0x5350)。
后果: 解码方按注释字面搜索必空, 会把"marker 未触发"读错(071x HDRLOAD0/HDRLAOD0 教训原样重演)。修法二选一: 改立即数就注释名, 或 record 判读表按实写值登记——守护建议前者, 并给这两字加 contract 测试锁字面(093x 纪律)。

## 其余静态项
x9=sub(x16,x22)+add(x23) 转换候选式与接管条目声明一致, 无新疑点。x16/x17 快照直存(0x9d0/0x9d8)是判"adrp/add 生成物理地址对不对"的正确取材。
