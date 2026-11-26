# vivo Y35A (PD1502A / MSM8916) — measured board facts

Source of truth for all porting work. Every constant below was read from the
phone's own stock boot image (QCDT entry matching platform 206 / variant 8 /
subtype 23, decompiled to `dtb10.dts`, 8699 lines, kept at
`/tmp/qcdtdts/dtb10.dts` inside container `unixnu-y35a-native-20261103`), or
from readback probes run on the device (evidence/y35a-codex-20261103).
Do not substitute other MSM8916 boards' values without citing this file.

## Identity and CPU
- vivo Y35A, model PD1502A, serial `efff9d92`, stock Android 5.0.2, PD1502A_A_1.18.0.
- SoC MSM8916 v2, soc_id=206, hw_platform MTP, platform_subtype 23, 4x Cortex-A53 r0p3.
- MIDR_EL1 `0x410fd030`; ID_AA64ISAR0_EL1 `0x10000` — NO AES/SHA1/SHA2/PMULL
  (software emulation path `XNU_NATIVE_CRYPTO_INSTRUCTIONS` is mandatory for corecrypto).
- ID_AA64MMFR0_EL1 `0x1122`; CurrentEL at handoff = EL1; SCTLR_EL1 = `0xc00800` (MMU off).
- CNTFRQ_EL0 = `0x124f800` (19.2 MHz). Virtual timer PPI 4 = INTID 20.
- GICv2 (QGIC2): distributor 0x0b000000, cpu-iface 0x0b002000, GICD_TYPER = `0x468`
  (SecurityExtn set — group selection must honor it).
- RAM: 2 GB. Usable windows: 0x80000000-0x85ffffff, 0x8c300000-0x9fefffff,
  0xa0000000-0xffffefff (from stock /proc/iomem). LK continuous splash buffer at
  0x83200000.

## eMMC (sdhc1) — root storage
- `sdhci@07824000`, compatible `qcom,sdhci-msm`. hc_mem 0x7824900 len 0x11c,
  core_mem 0x7824000 len 0x800. hc_irq = SPI 123 (INTID 155), pwr_irq = SPI 138 (INTID 170).
- 8-bit bus; bus-speed-mode "HS200_1p8v", "DDR_1p8v"; vdd 2.96 V always-on,
  vdd-io 1.8 V always-on; `qcom,nonremovable`. Card "Q313MB" 15,634,268,160 bytes.
- GPT verified read-only on device 2026-11-04 (emmc-gpt-verified-20261104.json):
  30,535,680 sectors, header + entries CRC32 OK. Key partitions (bytes):
  boot 64 MiB @240736, recovery 64 MiB @371808, survival 64 MiB, system 3 GiB,
  cache 150 MiB, persist 32 MiB, oem 64 MiB, backup 10 MiB, reserved 10 MiB,
  userdata ~11.0 GiB @7516160.

## SDIO (sdhc2) — WiFi/BT combo bus
- `sdhci@07864000`. hc_mem 0x7864900 len 0x11c, core_mem 0x7864000 len 0x800.
  interrupt-names hc_irq / pwr_irq / status_irq, GIC-mapped via interrupt-map:
  hc_irq = SPI 107 (INTID 139), pwr_irq = SPI 238 (INTID 270, shared BAM line),
  status_irq = TLMM GPIO 1 (card-detect routed through 0x48 gpio controller).
  4-bit bus, cd-gpios TLMM 38 (active-low), vdd/vdd-io from PMIC s2/s1 supplies
  (phandles 0x0b/0x0c).
- WCN3620 combo chip (integrated Pronto, SDIO Function 0 = WiFi+BT, BT over UART via
  BLSP2 hsuart@78af000: core_mem 0x78af000 len 0x200 + BAM 0x7884000, core_irq
  SPI 107 mapped, BAM IRQ SPI 238, wakeup GPIO 1; bam tx pipe 0 / rx pipe 1;
  alias "blsp1_uart1" — note DT label calls it uart1 on BLSP1 QUP5).
  wcnss_5wire / wcnss_pmux_gpio pin-ctrl nodes exist — read them for exact TLMM
  pins when bringing the chip up. smdtty-apps-riva-bt-acl alias shows stock routed
  BT over SMD, but direct H4-UART is the portable path.

## Touch — Synaptics S3202 (RMI4) on BLSP I2C
- Bus `i2c@78b9000`, compatible `qcom,i2c-msm-v2`; SE reg 0x78b9000 len 0x600,
  BAM 0x7884000 len 0x23000; qup_irq SPI 99 (INTID 131), bam_irq SPI 238 (INTID 270);
  clk-freq-out 400 kHz, clk-freq-in 19.2 MHz; pinctrl handles e1/e2 (active/sleep).
- Device `rmi_i2c@20` addr 0x20, compatible "synaptics_3202", label
  "synaptics_rmi4_i2c"; reset-gpio TLMM 12, irq-gpio TLMM 13 (attn_polarity 0),
  vdd_ana/vcc_i2c PMIC supplies; ts-dimension 1266x2220 vs lcd 720x1280
  (scale when mapping), lcd-dimension 0x2d0x0x500. vivo,use-ic-list = "synaptics_3202".
- Measured 2026-11-05 from the same DTB (dtb10.dts:6834-6880, container
  /tmp/qcdtdts): qcom,high-time-clk-div 0x17, fs-clk-div 0x16, noise-rjct
  scl/sda 0/0; BAM pipe cons 0x0c / prod 0x0d, master-id 0x56; supplies are
  DT phandles vdd_ana 0xe3 / vcc_i2c 0x49; dclick wake box x 0xa0..0x452,
  y 0xa0..0x80c; five virtual keys in ts-virt-key (first entry 139,117..
  1345,130,100). TLMM controller pinctrl@1000000 (qcom,msm-tlmm-8916, reg
  0x1000000 len 0x300000, 122 pins). The gpio-13-to-INTID routing value is
  NOT derivable from the DTB and is a planned probe measurement
  (docs/superpowers/plans/2026-11-05-y35a-touch-driver.md T0.3) — do not guess.
- iOS 12 cache input-stack census (byte scan of
  out/ipsw/16G102/kernelcache.decompressed, 2026-11-05):
  com.apple.iokit.IOHIDFamily 47, IOHIDInterface 50, IOHIDEventService 14,
  AppleHIDKeyboard 68, MultitouchSupport 1; RMI4/synaptics 0 — no Synaptics
  kext ships in the cache, IOHIDFamily is the consumer face we must satisfy.
  C++ mangled symbols are stripped from the cache (__ZN11IOHIDDevice 0 hits),
  so the IOHIDDevice ABI shim must come from audited public Darwin-18 source
  (audit-storage-interface.py pattern, planned as T3.1).

## Display — MDSS/MDP5 + DSI0, video-mode panel
- DSI ctrl `qcom,mdss_dsi@1a98000`, gcc-mdss clocks @1a98300; MDP5 base 0x1a00000.
- Panel not named in DT compatible (vivo bootanimation splash only; lk2nd brought up a
  720x1280 continuous splash at 0x83200000, 3 bytes/pixel, line stride 2160 — proven
  working under LK; UniXNU v1 must adopt this already-scanning pipeline, not re-init).

## UART console (working on device)
- `serial@78b0000` compatible `qcom,msm-lsuart-v14` (BLSP1 QUP1 low-speed UART),
  reg 0x78b0000 len 0x200, irq SPI 108 (INTID 140), alias serial0. The board's
  HS-UART is `uart@78af000` (BLSP1 QUP5, qcom,msm-hsuart-v14) — that one is for
  BT wcnss, not console. make_adt.py places the console at 0x078b0000 offset from
  SOC_BASE 0x07800000 with the uartdm-v1.4 compatible accepted by the console
  patch; LS-UART and HS-UART share the QUP UARTDM register set.
  TX at 115200 8N1 proven since 2026-11-03; kernel logs so far captured by
  post-mortem RAM readback, live UART streaming not yet used on a real cable.

## Power
- PMIC PM8916 (SPMI), warm reset via PS_HOLD 0x004ab000; RESTART_REASON 0x0860065c.
  lk2nd verified warm-reset type before every probe round (PROGRESS.md 2026-11-02).

## Boot chain as of 2026-11-04
- Boot slot contains experimental lk2nd (sha256 c4782b16...) built with
  `LK2ND_ADTBS= LK2ND_QCDTBS=msm8916-vivo-pd1502a.dtb`, forced fastboot.
- Stock partition backups verified on disk: aboot/boot/tz/hyp/sbl1 + full 1.18.0
  recovery pull (see evidence/y35a-20261102/ with SHA256s in PROGRESS.md).
  userdata is NOT backed up — never flash userdata without a staged backup.
- lk2nd virtualizes boot's first 512 KiB: never flash stock-boot.img through lk2nd
  fastboot; restore must go through stock fastboot or recovery.

## Device-side harness (all proven from Codex session evidence)
```
fastboot -s efff9d92 boot <image>            # RAM boot (never touches storage)
fastboot -s efff9d92 oem y35a panic          # stage 68 KiB panic/pram region @0x859e0000
fastboot -s efff9d92 get_staged panic.bin    # 69,632 bytes; magic KNUF (panic) / Y35ARD01 (readback)
fastboot -s efff9d92 oem y35a layout         # address layout echo
fastboot -s efff9d92 oem log; get_staged lk.log  # LK console
fastboot -s efff9d92 reboot                  # -> lk2nd forced fastboot again
```

## boot2 落点终局钉死 V14.7(2026-11-06,用户授权实 boot,两轮正反对照)
忠实 replica(真 entry.bin 54,431,312 + 真 board.adt 10,988,旧打包器 header
几何,页对齐全对)实跑 `fastboot boot` → **FAILED (remote: 'dtb not found')**。
反向对照:dt 区未页补齐的构造 → FAILED (remote: 'bootimage header fields
are invalid')——3248 自洽闸实证存在且生效。
结论链(全部实测,非推断):
1. boot2 真实落点 = copy_dtb FDT 魔数校验(aboot.c:3236 取 dt_size →
   copy_dtb 拒 XNU ADT);不是 40MB 闸(早已证伪)、不是 splash 地址闸
   (3421 check_aboot_addr_range_overlap 只查 aboot 占用区 0x8f700000
   一带,与 0x80080000..0x83469000 无重叠,V14.5 的 splash 预测被本轮
   实测修正)。
2. V14.3 记录的 boot2 "空串秒拒" 系当年记录截断——本机 host fastboot
   正常回显 remote 串,设备行为与 replica 一致。
3. T-PKG 解法方向已被实验背书:dt_size=0 → dt_actual=0 → copy_dtb
   整段跳过(V14.6 容器源码复核成立);ADT 走 bootconfig(OPTION 区,
   fork 已支持)或 OEM 预装通道。
4. 手机健康,分区未动;两轮均 Send→Booting FAIL,停在 fastboot。
