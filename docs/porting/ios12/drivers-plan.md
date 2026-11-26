# Drivers plan: touch, GPU, WiFi, BT, storage on Y35A (MSM8916) under xnu-4570

Synthesized 2026-11-04 from the four read-only recon reports (R1/R2/R3/R4 as labelled in
`boot-chain.md`). DTB refs: `evidence/y35a-20261102/dtb10-stock.dts` (8699 lines). Board
facts: `docs/board/y35a-facts.md` (95 lines). Cache offsets: `out/y35a/ios12-kc/kernel.macho`
(sha256 70e80388…). Unsupported items marked (verify).

## 0. Two facts that gate everything

- **No interrupt consumer.** xnu-4570 has no GIC driver; `ml_init_interrupt()` is an empty
  stub (`machine_routines.c:754-759`); the only IRQ ABI is `fleh_irq`→`sleh_irq` (`sleh.c:1297`)
  →`cdp->interrupt_handler` set by `machine_install_interrupt_handler` (`machine_routines.c:743`)
  by AppleARMInterruptController, whose source is absent (R2). Touch/GPU/WiFi/BT are all
  IRQ-driven → a hand-written `IOInterruptController` provider kext on the ADT
  `interrupt-controller` node is a prerequisite, not a follow-up (R2 row 3). Polled drivers
  (console, eMMC init) boot without it.
- **No kext to piggyback, no DT shortcut.** The j96ap PRELINK plist has zero `compatible`
  personalities matching any qcom node; Apple ones key off `AppleARMIODevice` + `arm-io`/
  `APPL,` tokens absent here (R3 §3). Verified absent in cache (0 hits): Synaptics/RMI4/3202,
  adreno/kgsl/Oxyl/8916/qcom, SDHCI/IOSDCard/mmcsdc host, AppleGIC/GICv, IOBluetoothFamily/
  BCMBT/HCIController/AppleH4 (R3 §2). Reusable *sinks* present: IOHIDFamily, IOStorageFamily,
  IO80211Family 1200.12.2, IONetworkingFamily, IOSkywalkFamily, IOSerialFamily +
  AppleOnboardSerial, IOSurface, IOAcceleratorFamily2, IOMobileGraphicsFamily (R3, R4 §2).
- IRQ numbers: tables use SPI; INTID = SPI + 32 reconciles R4's "SDHC1 INTID 155/170" with
  R3's "SPI 123/138" and "touch INTID 131" with "SPI 99".

## 1. Register facts table (per block)

| Block | Node (dts line) | Registers | IRQs (SPI) | Clocks | Supplies | Pinmux |
|---|---|---|---|---|---|---|
| eMMC host | `sdhci@07824000` L5434 | hc 0x7824900+0x11c, core 0x7824000+0x800 | hc 123, pwr 138 | GCC phandle 0x42 (L5163) iface+core | vdd 8916_l8 (0xc0,L5949, 2.85V), vdd-io 8916_l5 (0xc1,L5866, 1.8V) | sdc bank 0x40 L979 |
| WCN SDIO host | `sdhci@07864000` L5467 | hc 0x7864900+0x11c, core 0x7864000+0x800 | hc 9, pwr 221, card-detect TLMM GPIO 38 | GCC iface+core | vdd 8916_l11 (0x0b,L6012), vdd-io 8916_l12 (0x0c,L6033) | pmx_sdc2_* L1043ff; bus-width 4; 100k/400k/25M/50M |
| BT UART | `uart@78af000` L5264 | core 0x78af000+0x200, BAM 0x7884000+0x23000 | core 107, bam 238, wake TLMM GPIO 1 level | GCC core+iface; blsp1_uart1 | (none) | pinctrl 0xb9/0xba L5287-88; BAM TX0/RX1, master-id 0x56 |
| Touch I2C | `i2c@78b9000` L6834 | QUP 0x78b9000+0x600, BAM 0x7884000+0x23000 | qup 99, bam 238 | GCC iface+core; 400kHz out (0x61a80), 19.2MHz in | — | pmx_i2c_5 L1236: GPIO 19 SDA + 18 SCL func 2 |
| Touch device | `rmi_i2c@20` L6857 (addr 0x20) | props L6858-6881 | attn TLMM GPIO 13 falling/level0 (parent 0x48 msm_gpio; TLMM `pinctrl@1000000` reg 0x1000000+0x300000 L751, GIC SPI 208 L752) | — | vdd_ana 8916_l16 (0xe3,L6113), vcc_i2c 8916_l6 (0x49,L5887) | ts_int GPIO13 drive16mA pull-up (0xe4 L2151), ts_reset GPIO12 (0xe5 L2177) |
| GPU core | `qcom,kgsl-3d0@01c00000` L3346 | regbase 0x1c00000+0x10000, shader 0x1c10000+0x10000, qfprom 0x5c000+0x204 | 33 edge | GCC 0x42 ×6 (core/iface/mem/mem_iface/alt_mem_iface/gtcu_iface) | vdd 0x57 = gdsc_oxili_gx (0x185901c L3096-3104) — GDSC not PMIC rail | pwrlevels 400/307.2/200/19.2 MHz (L3382-3404); top 467.2; chipid 0x3000600 (A3xx CP3) |
| GPU IOMMU | `qcom,iommu@1f00000` L3121 (gfx_iommu, MMU-500) | 0x1f00000+0x10000; ctx gfx3d_user 0x1f09000, gfx3d_priv 0x1f0a000 | global NS 43 / S 42; ctx 241 (SID 0) / 242 (SID 1) | iface+core | GPU iommu=<0x58> L3136 | — |
| MDSS MDP | `qcom,mdss_mdp@1a00000` L3446 | 0x1a00000+0x90000, 0x1ac8000+0x3000 | (not extracted — unknown) | gcc-mdss `@1a98300` L5177 | — | — |
| DSI | `qcom,mdss_dsi@1a98000` L3863 | ctrl 0x1a98000+0x25c, phy 0x1a98500+0x2b0, mmss_misc 0x193e000+0x30 | — | mdp_core/iface/bus/byte/pixel/core | gdsc 0x59 gdsc_mdss (0x184d078 L3070); vdda 8916_l2 (0x43,1.2V); vdd 0x60 8916_l17; vddio l6 | reset GPIO25, enp GPIO97, enn GPIO98, backlight-en GPIO8 (L3887-3890) |
| BAM | no standalone node; mapped in hsuart L5266, i2c L6838 | 0x7884000+0x23000 (three-way shared) | bam 238 shared hsuart+i2c5 | — | — | hsuart TX0/RX1; i2c5 cons 0x0c prod 0x0d |
| GIC | `interrupt-controller@b000000` L5061 qcom,msm-qgic2 phandle 0x01 | dist 0xb000000+0x1000, cpu-if 0xb002000+0x1000 | arch timer L5090: PPIs 2/3/4/1, 19.2 MHz | — | — | — |
| PMIC | `qcom,spmi@200f000` L7021 (spmi-pmic-arb), `qcom,pm8916@0` L7036 | arb reg not read — unknown | unknown | — | all rails = **RPM-SMD** regulators (e.g. L6012) → over SMD to RPM (APSS), not the local SPMI arb; PM8916 MPP L7082, GPIO 0-3 L7122, RTC L7158, TZ L7349 | — |
| GCC | `qcom,gcc@1800000` L5163 | 0x1800000+0x80000, apcs 0xb016000+0x40; phandle 0x42 | — | hashed cells (GCC_DUAL) | vdd_dig s1_corner (0x5a,L5670), s1_corner_ao (0xb2,L5681), l7_ao (0xb3,L5925) | no separate gfxcc node |
| Reboot | `restart@4ab000` L5079 qcom,pshold | 0x4ab000+4 (TCSR), 0x193d100+4 (wdog status) | — | — | — | — |
| WCN glue | `smp2p-wcnss` L587, `smd-wcnss` L5614 | `qcom,wcnss-wlan@0a000000` pronto bank (reg-names pronto_phy_base/a2xb/ccpu/mcu L6700-6723) | — | — | — | wcnss_5wire L1547 GPIO 40-44 func 01 (FIND/WAKE/SLEEP/CLKREQ/STATE); alt L1568 |
| GMU | **absent** — `grep -ic gmu` = 0 over 8699 lines (R3) | — | — | — | — | CP-based bring-up only, no GMU/HFI |

Conflict (resolve before coding, do not pick silently): R3 decodes SDHC2 children as hc SPI 9 /
pwr SPI 221 / card-detect GPIO 38; R4's WiFi paragraph states SPI 107/238/GPIO 1 — those are the
**hsuart** values (R3 L5264). Re-read `dtb10-stock.dts:5467-5500`; adopt one. (verify)

## 2. TOUCH — Synaptics S3202 RMI4 over BLSP1 QUPv2 I2C-5

Write from scratch (no RMI4/Synaptics in cache; `AppleMultitouchSPIJ96` idx 64 speaks Apple's
SPI multitouch — provider `AppleARMSPIDevice`, IOClass `AppleMultitouchN1SPI`; wrong bus, wrong
IC; R3). Two stages: (1) QUPv2 I2C master for `qcom,i2c-msm-v2` @0x78b9000 (SE 0x600, BAM
0x7884000, qup SPI 99, bam 238, pipes 12/13, GPIO 18/19 func 2); publishes an `IOPlatformDevice`
nub with a `compatible` our device driver matches. (2) RMI4 function driver for S3202 at 7-bit
0x20: reset GPIO 12, attn GPIO 13 falling, attn_polarity 0, rails 8916_l16 + 8916_l6 over
RPM-SMD; F00/F01/F13 page addressing (RMI4 spec, no local copy). Map ts 1266x2220 → lcd 720x1280
(L6858-6881), vivo virtual-key table, dclick x[160:1106] y[160:2060] (R3).
IOKit: subclass **IOHIDEventService** (prelinked; IOHIDEventService+UserClient/Queue ×14,
IOHIDInterface ×1, IOHIDPointing ×1, offsets 0x6bfac8/0x6c012b), publish a digitizer HID report
descriptor via `kIOHIDReportDescriptorKey` ("HIDReportDescriptor" literal count 0 is not
counter-evidence); in-cache `IOHIDEventDriver` + backboardd discover it. DSC tokens proven:
`IOHIDManager*` (8 symbols), `IOHIDServiceClient` (152), `MTEvent*`. Headers absent from tarball →
hand-pin vtable (GopFramebuffer pattern) or extract from the in-cache kext (R4 3.2).
Reference: lk2nd `platform/msm_shared/i2c_qup.c` (786 L GPLv2) is the only QUPv2 I2C sequencer on
disk (register knowledge only, clean room per `QcomSdcc/SPEC.md` §7). **QcomGeniSpi not reusable**
(GENI vs QUPv2); community `unixnu-nativefocaltechtouch` is FT8203-over-GENI-SPI (wrong);
`ShengNovatekTouch` catalogued (`components.toml` L170-184) but its checkout is absent here.
Host test: QUPv2 register model like `Test/geni-spi.c` (`struct sim` `reg[]` + `tick()` FSM + error
injection) + BAM pipe model + RMI4 device model (F01 query, attn IRQ, F13 frames); then
`live-hid.py` QEMU GDB fixture. Acceptance: affine-checked event stream.

## 3. GPU — Adreno 306 (a3xx CP3, chipid 0x3000600)

Write from scratch: cache ships AGX only (`com.apple.AGXG4P` 133.6 idx 3, IOClass
`AGXAcceleratorG4P_B0`, provider `AppleARMIODevice`, string 0x921451; `AGXFirmwareKextG4P`) —
different model; `adreno`/`kgsl`/`Oxyl`/`qcom` = 0 hits (R3). No a3xx reference on disk (grep
`a3xx|A3XX|a306` in kits/AdrenoPM4 + drivers/Adreno740 = 0 in Ring.h/Raster.h; soc.toml +
msm8916.config say so; no freedreno/rgsl vendored, no mesa checkout — only
`patches/mesa/freedreno-tools-nir.patch`). Register spec from freedreno `a3xx.xml`/rgsl — **not
local, external fetch at implementation time** (R4 3.3).
- **Display floor (proven design).** lk2nd continuous splash @0x83200000 720x1280 RGB888 stride
  2160 under `GopFramebuffer` `NativeLegacyDisplay : IOMobileFramebufferLegacy` /
  `NativeMobileDisplay : IOMobileFramebuffer`, ABI hand-pinned `OriginalMobileFramebufferABI.h`;
  userspace `IOMobileFramebuffer*` (404 DSC strings) + legacy ChangeFrameInfo API (R4 3.3).
- **Command submission (write-it).** RSCC + core 0x1c00000/0x1c10000, qfprom 0x5c000, IRQ SPI 33,
  GX via gdsc_oxili_gx (0x185901c), **no GMU** → CX/GX gdsc + pwrseq0/1/2 register writes.
  Reusable: `kits/AdrenoPM4` (type-4/7 decode compatible back to a2xx, MIT, headers verified).
  Not: `kits/AdrenoFirmware` (a7xx GMU/HFI/ZAP). `drivers/Adreno740/` = structure ref (three
  `IOPlatformDevice` personalities @probe 1000, tests + host shim).
- **SMMU.** gfx_iommu@0x1f00000 (MMU-500): ctx1 0x1f09000 SID 0, ctx2 0x1f0a000 SID 1, ctx IRQ
  241/242, global 43/42, GPU iommu=<0x58>. `kits/AirNir` + `ArmSmmu4K` are format-1 refs; the
  non-apple iommu-bootstrap (`pmap.c`) + pmap-field (`pmap.h`) patch intents carry (R1).
- **Acceleration surface.** Publish `IOAcceleratorFamily2` (398.9) / `IOSurface` (255.2.1,
  IOSurfaceRoot 0x70f458) shape so CoreGraphics reaches it. Honest: **unknown** how far non-AGX
  gets — DSC tokens `AGX*`/`IOAccelerator` are AGX-shaped. Framebuffer+CPU-render is the shipped
  floor; PM4/a306 submission is the milestone. (verify)
Host test: mirror `drivers/Adreno740/tests/` (23 `test_*.cpp` + `hostsim/host_iokit_shim.cpp`,
`xcrun clang++ -fsanitize=address,undefined`, kernel obj `-target arm64-apple-ios<ver> -Werror`)
driven by `scripts/check-adreno-raster.py`; new `NativeAdrenoA3xx/tests/test_rscc.cpp` + RB-register
host model; PM4 stream tests via `scripts/check-adreno-pm4.py` (R4 3.3).

## 4. WiFi — WCN3620 (Pronto) on SDIO host 2

Write from scratch / port wcn36xx. Cache has `AppleBCMWLANCore` idx 17 +
`AppleBCMWLANBusInterfacePCIe` idx 16 + IO80211Family 1200.12.2 idx 146; the SDIO bus personality
is *declared* but **no SDIO bus kext ships** (SDIO string hits 0x8516fa/0xa7b0b3 are log text;
`AppleSDIO*`/`EmbeddedSDIO` = 0) (R3). Neither host nor attach point exists.
Port seed: `~/unixnu-research/wcn36xx-priorart/` (ISC, Krasnikov) — `src/` complete: main.c 46.9KB
(platform_driver, `MODULE_DEVICE_TABLE(of, wcn36xx_of_match)`, deps `smem_state.h`+`wcnss_ctrl.h`
→ Linux ~4.4-4.8), dxe.c/h (SMD mailbox 29/18KB), smd.c/h (99KB SMD/QMI), txrx, firmware, pmc,
**hal.h 127KB datasheet-grade WCN3620 HAL**, wcn36xx.h; `src44/` = earlier subset (main.c 29.5KB,
no smem_state) — simpler association-only baseline (R4 §1, 3.4).
Consequence: wcn36xx binds **over SMD/QMI, not raw SDIO func 0** (R4 3.4) → WCNSS power-up + SMD
edge protocol must exist first (`qcom,smd`+`smp2p`+wcnss-pil, none local outside lk2nd-none) as an
"SMD transport" mini-driver. Glue: smp2p-wcnss L587, smd-wcnss L5614, pronto bank L6700-6723,
5-wire GPIO 40-44 L1547. SDIO host = §1 sdhc2.
IOKit: **IO80211Controller** subclass inside IO80211Family (`IO80211Controller` ×45 in binary;
family headers not in 4570/`refer/`), deliver `en0`. wifd side proven: `Apple80211*` +
`IO80211Controller`/`IO80211API`, names en0..en4/awdl0/sktap. AWDL/Skywalk out of v1 scope; whether
IO80211Family attaches cleanly without an IOSkywalk provider is unknown (verify). Hand-pin ABI.
Host test: dxe/SMD channel + HAL message tick model against `hal.h` wire structs; then live-hid QEMU
fixture for the SDIO/SMD windows (R4 3.4).

## 5. BT — WCN3620 H4 over BLSP1 HS-UART

Two layers: (1) **transport (best win)** — QUPv2 HS-UART `uart@78af000` (core 0x200, shared BAM
0x7884000, pipes TX0/RX1, master-id 0x56, core IRQ SPI 107, BAM 238, wake GPIO 1). Same register
family as the proven console uartdm (`tests/uartdm/`); lk2nd `uart_dm.c` (468 L)+`uart_dm.h` as
knowledge (R4 §1, 3.4). Write a QUP-HS-UART kext whose nub publishes **AppleOnboardSerialSync** so
stock prelinked `AppleOnboardSerial` (idx 66, IOClass `AppleOnboardSerialBSDClient` provider
`AppleOnboardSerialSync`, string 0x6d6313) + `IOSerialFamily` (idx 166) create the callout device.
`usr/sbin/bluetoothd` opens `cu.bluetooth`/`uart.bluetooth` (strings in `dl/mnt-j96/`) — exact name
is runtime `IOCalloutDevice`, inference not a cache string (R3). (2) **HCI (write from scratch)** —
`IOBluetoothFamily`/`IOBluetoothHCIController`/BCMBT/`AppleH4` all 0 hits; IOBluetoothFamily is
**not prelinked** (DSC only) → on-demand kext load is the open risk (R4). `com.apple.driver.AppleBluetooth`
idx 24 is only a `BTReset` GPIO helper. H4 framing = Core Spec vol 4 part D. Fallback: H4 loop + HCI
via our thin user-client until kextd path proven. DSC: `IOBluetoothHCIController`, `IOBluetoothBNEPDriver`,
`IOBluetoothMAC`, `IOBluetoothNoHCIController`; on-device `Bluetooth-212.21` binaries unknown (not in
extract) (R3, R4 3.4). Host test: H4 packetizer round-trip like `tests/uartdm/`, then QEMU UART fixture.

## 6. Storage — beyond the existing SPEC.md

`drivers/QcomSdcc/SPEC.md` is current and disk-verified but **spec only**: no `components.toml`
entry (grep 0), absent from `profiles/arch/arm64/profile.toml` `[components]` include, no
`sdhci*`/`msm_sdmmc*`/`NativeSdcc*`/`SdciCore*` file anywhere (R1). SPEC §8 lists intended files
(SdciCore.h, NativeSdcc.cpp, Test/) — none made; §3.2 says lift PIO ops from `scripts/y35a/emmc_pio.h`
(`template<class IO> class EmmcPio`) + `probe_emmc.py`/`emmc_probe.cpp` into the driver. Work, in order:
(1) register the component + create NativeSdcc.cpp/SdciCore.h for sdhc1 (0x7824900+0x11c hc,
0x7824000+0x800 core, IRQ SPI 123/138, HS200, rails L8/L5). (2) publish **IOBlockStorageDevice**
(`refer/IOStorageFamily/IOBlockStorageDevice.h:42` kIOBlockStorageDeviceClass, `:395 doAsyncReadWrite`;
`IOStorage.h:388`) so stock `IOBlockStorageDriver`+`IOGUIDPartitionScheme`+`IOMediaBSDClient` build
media and `IOFindBSDRoot` mounts over `/chosen boot-device` (`IOPlatformExpert.cpp:1155`,
`IONVRAM.cpp:876`). iOS12 ABI proof now in-hand: IOStorageFamily idx 1 + IOSCSIArchitectureModelFamily +
IOSCSIBlockCommandsDevice + EncryptedBlockStorage; strings `IOBlockStorageDriver`×11 /
`IOBlockStorageDevice`×4 (R4 3.1, R3). (3) keep polled init so storage skips the missing GIC (R2 row 8).
(4) pattern `drivers/VirtioMmioBlock/NativeVirtioBlock.cpp`; store weak symbols
`drivers/RamBlock/NativeRamBlock.cpp:35-40` (`native_ufs_store_mode/open/read/write/sync/gpt_check`);
headers from `scripts/prepare-storage-headers.py` audited by `scripts/audit-storage-interface.py` →
`build/storage-abi/include` (R4 3.1). (5) SPEC §9 open questions (RCA, store window, Phase-1 blank probe)
remain; geometry Q313MB 30,535,680 sectors + GPT at
`evidence/y35a-codex-20261103/emmc-gpt-verified-20261104.json`. Stock expects ANS/NVMe-style storage
(`AppleNVMeController`/`AppleEmbeddedNVMe`/ANS2 are class-name tables only, 0x6b7c2d/0x7a04e4, no
controller kext; no S5D/ANS id in cache) → block depth past IOBlockStorageDevice is (verify).
Host test: Phase 0 extends `test_emmc_pio.cpp` model into `drivers/QcomSdcc/Test/sdcc_host.cpp`
(ASan/UBSan g++); ADT regression in `test_board_adt.py`; `verify_shim.py` unchanged (loader, not driver).

## 7. Build integration (all five)

- Catalog: each `drivers/*` is its own submodule; registry `components.toml`. Copy the QcomGeniSpi
  entry shape (`:187-205` scope=controller, build_stage=embedded, `build=[]` — compiled by the
  *consumer*, pattern of `ShengNovatekTouch` `:170-184` `deps=["QcomGeniSpi"]`). One controller
  component per bus (I2C, SDHCI, HS-UART, SMMU/GFX) + one device component per function
  (RMI4, WCN3620, H4, a306), each declaring deps.
- Compile: extend `scripts/build-arm-driver.py` (122 L) with iOS-12 mode. Today it pulls the clang
  record from `build/xnu/ios-obj/DEVELOPMENT_ARM64_BCM2837/iokit/DEVELOPMENT/IOPlatformExpert.cpo.json`,
  swaps in the `.cpp`, adds `-Wall -Wextra -Werror -I .cache/xnu-work/osfmk` (storage `-I
  build/storage-abi/include`), audits magic `0xfeedfacf`/cpu `0x0100000c`/filetype 1/**deployment
  (platform 2, 0x110000 = iOS 17.0)**, archives `xcrun ar rcs` (R4 §1). For 4570: deployment `0xc0000`
  (matches measured `LC_BUILD_VERSION` minos/sdk 0xc0400=12.4) + a recipe harvested from a 4570 tree
  that does not exist yet. Whether the BCM2837 `build/` tree is present: unknown (R4 3.5) (verify).
- Fold-in: `kits/XnuPrelink/emit_prelink.py` injects our kexts, but on iOS12 the point is the
  reconstructed KPP cache and `dl/kpp-payloads/...fused` is **missing** → reproduce first (R4 3.5,
  blocked). `emit_prelink.py` `COALESCED` map targets the modern layout (R4 §1); needs D2-D5.
- ADT: every driver needs a node whose `name`/`compatible` equals its published personality +
  `reg`/`interrupts`/`#*-cells` per `IODeviceTreeSupport.cpp:119-146` (R2 row 2, R3 §3). Added in
  `make_adt.py:make_tree`; regression `scripts/y35a/test_board_adt.py`.
- IRQ budget: see `armcpu_spi_attach` (`drivers/ArmCpu/ArmCpu.cpp:863`, SPEC §3.6) with 16-slot
  ledger — touch 99, GPU 33+ctx 241/242+global 42/43, SDHC1 123/138, SDHC2 9/221(+GPIO38), hsuart
  107/238(+GPIO1), TLMM cascade 208 (R4 3.2).
- Host harness inventory (all on disk, R4 §1): `Test/geni-spi.c`, `emmc_pio.h`+`test_emmc_pio.cpp`,
  `drivers/Adreno740/tests/`+`hostsim/host_iokit_shim.cpp`, `tests/uartdm/`, `drivers/RamBlock/Test/`,
  `test_board_adt.py`, `live-hid.py`. `verify_shim.py` (QEMU `-M virt,... -cpu cortex-a53 -accel tcg
  -m 2048` + gdbstub + QMP `pmemsave`, `hardware_boot_demonstrated=False`) is a loader verifier — leave it.

## 8. Ordered risk list

1. **No GIC interrupt consumer in xnu-4570** — gates GPU/WiFi/BT/Touch; needs a hand-written
   `IOInterruptController` provider + `machine_install_interrupt_handler` wiring. Most
   under-specified area of the plan (R2 §3).
2. **Missing KPP-reconstructed payload** — nothing foldable into a bootable image until re-run (R4 3.5).
3. **Prelink kind/plist mismatch** — `native_prelink.py:135` MH_EXECUTE assert vs legacy
   `_PrelinkInfoDictionary` + packed `_PrelinkLinkKASLROffsets`, zero chained fixups; the two 10063
   ABI markers must be re-authored against 4570 `kalloc.c`/`OSKext.cpp`; reports disagree on cache
   filetype (boot-chain §6) (R1 risks 1-3, R2).
4. **PMIC supply dependency** — all rails (L2/L5/L6/L8/L11/L12/L16/L17/s1_corner) are RPM-SMD,
   commanded over SMD/GLINK to RPM (APSS), not the local SPMI arb; PM8916 SPMI base and arb reg/IRQs
   unread (unknown) (R3). Touch reset / WCNSS power-up / GX gdsc stall without it. Do GDSCs first
   (gx 0x185901c, mdss 0x184d078) — GCC-side, cheaper.
5. **No AES/SHA hardware** (ID_AA64ISAR0=0x10000 per pivot) — `native-crypto-instructions`
   (`osfmk/arm64/native_crypto.h`+`sleh.c`, `XNU_NATIVE_CRYPTO_INSTRUCTIONS=1`) + `SoftwareAES` carry
   as intent but re-apply to 4570 where `sleh.c`/corecrypto differ (R1).
6. **BAM/DMA sharing** — BAM 0x7884000+0x23000 shared three ways (hsuart, i2c5, mapped in sdhc2),
   bam IRQ 238 shared hsuart+i2c5, fixed pipes (hsuart TX0/RX1, i2c5 0x0c/0x0d). Needs one owner
   model per pipe or IRQ storms / cross-driver corruption (R3).
7. **IOBluetoothFamily not prelinked** — on-demand load on our custom image is the BT risk;
   mitigations in §5 (R4 3.4).
8. **GPU userspace semantics** — iOS12 Metal/GL expects AGX; non-AGX depth unknown → framebuffer+CPU
   is the floor, PM4/a306 the milestone (R4 3.3).
9. **Header/ABI gaps** — IOHID/IO80211/IOStorage/IOMobileFramebuffer headers outside the tarball;
   hand-pinned ABI is the route but each pin is its own correctness risk (R4).
10. **No a3xx register source on disk** — freedreno `a3xx.xml`/rgsl must be fetched; GPU is the only
    block with no local start material beyond structure (R4 3.3).
11. **Board-config bring-up unverified** — soc.toml lists GICv2 acceptance by the XNU platform expert
    as the UNVERIFIED first question; `patches/xnu/series` empty; ArmCpu is GICv3-oriented and
    Adreno740/AdrenoMetal are 740-specific/inapplicable to a3xx (R4 §1).
12. **Container/volume drift** — `/work` is a named docker volume with independent copies, not a bind
    mount; host↔volume sync unknown, so a green container build says nothing about host sources (R4 §0) (verify).
13. **lk2nd GPLv2** — register knowledge only, clean-room per `QcomSdcc/SPEC.md` §7 (R4 §1).
14. **wcn36xx vintage dependency** — binds over SMD/QMI + smem_state/wcnss_ctrl → SMD transport
    mini-driver lands before WiFi; `src44/` reduced-scope fallback (R4 3.4).
