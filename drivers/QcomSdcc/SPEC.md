# SPEC: QcomSdcc — SDHCI eMMC block driver for vivo Y35A (MSM8916 sdhc1)

Status: draft for approval. No code yet. Scope of this file: drivers/QcomSdcc only,
plus spec'd (not yet made) additions to make_adt.py, build scripts, one personality
patch, and one host/QEMU test harness.

## 1. Objective

Give native XNU on PD1502A a working eMMC block path: resume the controller + card
as handed over by lk2nd (device-proven pattern), read the user area, publish an
IOBlockStorageDevice whose IOMedia the storage stack can see, and — in later
phases — support writes, the RamBlock persistent-store contract (the
`native_ufs_store_*` weak symbols), interrupt-driven completion, and HS timing.
Success looks like: `IOFindBSDRoot` finds real GPT-partitioned media below this
driver on the phone, and a persistent Data overlay survives warm reboot.

Why this driver instead of pure-PIO `emmc_pio.h`: the host-tested PIO model
(scripts/y35a/emmc_pio.h, tests green) is a transport core, not an OS device. The
kernel needs an IOBlockStorageDevice lifecycle (probe/start, work-loop serialized
requests, IOMemoryDescriptor plumbing) and a provider-matched boot path. We keep
`emmc_pio.h`'s register discipline and fold it into the driver's transport layer.

## 2. Measured hardware facts (source-cited; do not re-guess)

Controller = sdhc1, `sdhci@07824000`, compatible `qcom,sdhci-msm`
(PD1502A stock DTB, decompiled `/tmp/qcdtdts/dtb10.dts` in container
unixnu-y35a-native-20261103, lines 5435–5463):

| Item | Value | Source |
| --- | --- | --- |
| core_mem window | 0x07824000 len 0x800 | dtb10.dts:5436 reg pair 2 |
| hc_mem window | 0x07824900 len 0x11c | dtb10.dts:5436 reg pair 1 |
| hc_irq | SPI 123 → INTID 155, type 0x00 | dtb10.dts:5438 `<0x00 0x7b 0x00 ...>` |
| pwr_irq | SPI 138 → INTID 170, type 0x00 | dtb10.dts:5438 second triple `<0x00 0x8a 0x00>` |
| bus width | 8-bit | dtb10.dts:5440 `qcom,bus-width = <0x08>` |
| speed modes | "HS200_1p8v" "DDR_1p8v" | dtb10.dts:5450 |
| iface clk rates | 400k/25M/50M/100M/192M | dtb10.dts:5449 `qcom,clk-rates` |
| vdd / vdd-io | 2.96 V always-on / 1.8 V always-on (0x2c4020 / 0x1b7740 levels) | dtb10.dts:5452–5458 |
| removable | nonremovable | dtb10.dts:5464 |
| card | "Q313MB", 15,634,268,160 bytes = 30,535,680 sectors | device readback (below) |

The pwr_irq triple is unambiguously `<0x00 0x8a 0x00>` for sdhc1. (sdhc2 is the
ambiguous one — its node at dtb10.dts:5468–5498 carries an interrupt-map; it is
NOT this driver's device. do not confuse sdhc2's SPI 221 pwrctl line from
lk2nd platform/msm8916/include/platform/irqs.h:50 with sdhc1.)

Cross-check, lk2nd prior art for this SoC generation
(container /work/lk2nd-y35a-codex/platform/msm8916/include/platform/):
iomap.h:73–76 `PERIPH_SS_BASE 0x07800000`, `MSM_SDC1_BASE (base+0x24000)`,
`MSM_SDC1_SDHCI_BASE (base+0x24900)`; irqs.h:49 `SDCC1_PWRCTL_IRQ = SPI 138`.
target/msm8916/init.c:98–122: slot 1 = 8-bit, max_clk MMC_CLK_177MHZ, hs400 off.
Matches the DTB exactly — the register facts are triple-sourced.

### 2.1 Register map (offsets relative to hc window unless marked core)

Standard SDHCI 3.0 set, confirmed by LK platform/msm_shared/include/sdhci.h:154–177
and by the device-proven host model in scripts/y35a/emmc_pio.h:

```
0x000 ARG2        0x004 BLKSIZE     0x006 BLKCNT     0x008 ARGUMENT
0x00C TRANS_MODE  0x00E CMD         0x010 RESP0..    0x020 DATA FIFO (32-bit)
0x024 PRESENT     0x028 HOST_CTRL1  0x029 PWR_CTRL   0x02C CLK_CTRL
0x02E TIMEOUT     0x02F SOFT_RESET  0x030 INT_STATUS 0x032 ERR_STATUS
0x034 INT_STATUS_EN 0x036 ERR_EN    0x038 INT_SIGNAL_EN 0x03A ERR_SIG_EN
0x03C AUTO_CMD_ERR  0x03E HOST_CTRL2  0x040 CAPS1    0x044 CAPS2
0x054 ADMA_ERR    0x058 ADMA_ADDR
MSM extensions (hc): 0x100 DLL_CONFIG  0x108 DLL_STATUS  0x10C VENDOR_SPECIFIC_FUNC
                     0x11C HC_VND_CAPS0  (sdhci_msm.h:46–48,64, sdhci_msm.c:148,205)
Core window: +0x50 MCI_VERSION  +0x78 HC_MODE (bit0 HC select, bit13 FF_CLK_SW_RST_DIS)
             +0xDC PWRCTL_STATUS  +0xE0 PWRCTL_MASK  +0xE4 PWRCTL_CLEAR  +0xE8 PWRCTL_CTL
             (sdhci_msm.h:116,127; sdhci_msm.c:90–193; iomap.h:82–85; probe absolute
              accesses scripts/y35a/emmc_probe.cpp:23,31–36)
0x1B4 DLL_CONFIG_2 is only defined for post-8x16 controller revisions. On this
part it lies outside both DTB windows (0x7824900+0x11c = 0x7824a1c,
0x7824000+0x800 = 0x7824800); treat it as absent, version-gate it out, never touch it.
```

Measured CAPS1 on device = 0x342dc8b2 → base clock 200 MHz (bits 15:8 = 0xc8,
LK mask SDHCI_CLK_RATE_MASK sdhci.h:219), max block length 512 bytes (bits 17:16
= 1, sdhci.h:249), 8-bit width bit 18 = 1 (sdhci.h:240), ADMA bit 19 = 1
(sdhci.h:251), 1.8 V bit 26 = 1 (sdhci.h:235).
Measured at XNU entry under lk2nd-fastboot (decode of
evidence/y35a-codex-20261103/emmc-handoff-restore-readback-20261104.bin):
PRESENT 0x1f80000 (all cmd/data lines free, clocks stable), HOST_CTRL1 0xb30,
CLK_CTRL 0xf0007 (internal+bus clock enable, divider as left by LK),
INT_STATUS 0, INT_STATUS_EN 0xffff800b, INT_SIGNAL_EN 0xffff000b → 0 after
probe, DLL_CONFIG 0x7a76400, DLL_STATUS 0x1d4, core+0x78 HC_MODE = 0 (LK's
fastboot path calls `sdhci_mode_disable`, target/msm8916/init.c:423).

### 2.2 Device-proven handoff facts

The RAM-only probe (not XNU) run 2026-11-04 proved, on the physical card:

1. Resuming with the preserve-restore sequence around HC_MODE re-enable
   (scripts/y35a/emmc_probe.cpp `enableHostMode`, lines 17–39) succeeds: state 3,
   CMD5/CMD7/CMD8 complete, EXT_CSD read, capacity 30,535,680 sectors,
   34/34 sectors read, response 0x900 (card ready R1), no errors
   (emmc-handoff-restore-readback-20261104.bin).
2. A naive HC_MODE enable without preservation resets power/SDCLK/DLL and fails
   closed with error 7 (emmc-handoff-readback-20261104.bin) — the guard in
   emmc_pio.h `resume()` (checks CLK_CTRL&7==7 && PWR_CTRL&1, error 7) is
   validated by the first run and must stay.
3. The GPT at LBA 0–33 reads correctly, header + entry CRC32 verified,
   userdata at sectors 7,516,160–30,535,646 (emmc-gpt-verified-20261104.json).
   Partition table used later for store windows: cache = 6,946,816–7,254,015,
   persist = 7,254,016–7,319,551, oem = 7,323,648–7,454,719.

## 3. Driver architecture

### 3.1 Two options, and the recommendation

Option A — full IOBlockStorageDevice (adopted). A `NativeSdcc : IOBlockStorageDevice`
matched by personality to the ADT `sdhc1` IOPlatformDevice nub, exactly like
NativeVirtioBlock (drivers/VirtioMmioBlock/NativeVirtioBlock.cpp — the repo's
canonical IOBlockStorageDevice pattern: gate-serialized doAsyncReadWrite,
completion called synchronously, capacity checks, report* overrides, coherent
DMA note). Stock IOBlockStorageDriver + IOApplePartitionScheme/IOGUIDPartitionScheme
run above it from the prelinked original closure (the same stack NativeUfs uses on
sheng; kernelcache contains com.apple.iokit.IOStorageFamily — verified by symbol
scan of out/ipsw/21H461/kernelcache.decompressed), giving real partition IOMedia,
BSD names, and IOFindBSDRoot selection by UUID/name.

Option B — RamBlock store-overlay only (fastest path to persistent Data, kept as
Phase 2 scope, not the alternative). Implement the six weak-imported
`native_ufs_store_*` symbols (drivers/RamBlock/NativeRamBlock.cpp:35–40) inside
this driver over a bounded eMMC window; RamBlock then persists changed pages and
the root stays the RAMDisk. It does not publish media and cannot mount anything
from the card. On sheng this coexists with full UFS media (both paths in one
driver, RootPublication + store contract).

Recommendation: build A as the spine and B as a thin contract on top of the same
transport. A alone is the correct long-term device; A+B gives persistence without
waiting for full APFS-on-eMMC root acceptance. Do not ship B alone — a store
contract with no published media hides the card from every future subsystem
(boot-slot access, userdata) and duplicates the transport if A comes later.

### 3.2 Transport core (shared host/device)

Follow the `template<class IO>` pattern of emmc_pio.h so the register sequences
tested on the host are literally the ones shipped:

```
drivers/QcomSdcc/SdciCore.h      template<class IO> class SdciController
  - resumeFromHandoff()          preserve-restore HC_MODE sequence (probe-proven)
  - coldInit()                   LK sdhci_msm_init + mmc_card_init parity (§3.5)
  - command(index,arg,dir,data)  extended emmc_pio command(): all init cmds, CMD6,
                                 CMD18/CMD25 multi-block, stop transmission CMD12
  - readSectors / writeSectors   PIO (Phase 0–2), SDMA (Phase 3), ADMA2 (Phase 4)
  - waitCardBusy / waitStatus    bounded loops, clock_interval_to_deadline in kernel
  - powerIrqAck()                STATUS→CLEAR→CTL OR-ack (probe lines 31–36)
drivers/QcomSdcc/NativeSdcc.cpp  IOBlockStorageDevice shell + store contract
drivers/QcomSdcc/Test/           host models (g++ -std=c++17 -fsanitize=address,undefined)
```

Kernel-side IO shim: maps both windows with
`provider->mapDeviceMemoryWithIndex(i, kIOMapAnywhere | kIOMapInhibitCache)`,
accessors like NativeVirtioBlock::read32/write32 with `dsb oshst` barriers on
writes and `dmb osh` around DMA buffer handoff. Device-tree `reg` order is
`hc, core` (matches DTB order so index 0 = hc; do not reorder).

### 3.3 Matching, flags, build integration

- New flag `XNU_NATIVE_SDCC=1` consumed by scripts/build-xnu-4k-baseline.sh in the
  personality block (pattern: the XNU_NATIVE_VIRTIO_BLOCK stanza, lines 193–199 —
  requires XNU_NATIVE_AES=1 baseline, appends to PERSONALITY_CFLAGS) and a
  force_load stanza for `build/qcom-sdcc/libNativeSdcc.a` beside the RAM-block one
  (line 755), with the same re-audit of `bindings.json`/object sha256
  (lines 735–749) — the storage ABI bindings of NativeSdcc must match the already
  linked IOBlockStorageDevice closure (IOBlockStorageDevice.cpp compiled reference
  from scripts/audit-storage-interface.py, build/storage-abi/include).
- New patch `patches/xnu/native-sdcc-personality.patch` on KernelConfigTables.cpp
  (same style as native-aes-personality.patch):
  `IOClass=NativeSdcc; IOProviderClass=IOPlatformDevice; IONameMatch='qcom,sdhci-msm';
   IOProbeScore=1000:32` plus a second gated personality with
  `IOMatchCategory=NativeSdccStore` on IOPlatformExpertDevice for the
  board-started store-contract attach if the platform nub is not present
  (mirrors NativeUfs' dual personality, KernelConfigTables stanza lines 39–51).
- `scripts/build-arm-driver.py`: add `NativeSdcc` to the catalog entry and to the
  `-I build/storage-abi/include` branch (line 82) and the component registry in
  components.toml (new entry after RamBlock; build = build-arm-driver.py QcomSdcc,
  outputs build/qcom-sdcc/libNativeSdcc.a).
- `scripts/y35a/build_native.py`: add `XNU_NATIVE_SDCC='1'` to the flags dict
  after the driver is proven, plus build step for the archive.

### 3.4 ADT changes (spec'd here; make_adt.py edited only after approval)

New `arm-io` child node `sdhc1` in make_tree() (children carry reg relative to
SOC_BASE 0x07800000, two address cells, per existing convention):

```
sdhc1:
  compatible        = "qcom,sdhci-msm\0"                       (string list, NUL-term)
  reg               = <0x24900 0x0 0x11c 0x0                   (hc window, relative)
                        0x24000 0x0 0x800 0x0>                 (core window)
  reg-names         = "hc_mem\0core_mem\0"
  interrupts        = <0 123 4   0 138 4>                       (SPI,type; LE cells=3)
  interrupt-parent  = 1 (the intc AAPL,phandle)
  qcom,bus-width    = 8
  qcom,clk-rates    = <400000 25000000 50000000 100000000 192000000>
  qcom,bus-speed-mode = "HS200_1p8v\0DDR_1p8v\0"
  vdd-always-on     = 1     vdd-io-always-on = 1                (presence flags; the
        driver's resume guard checks live CLK/PWR state instead of emulating regulators)
  unixnu,handoff    = 1     (this build requires an lk2nd-configured controller for
        resume mode; cold init is selectable by boot-arg, see §3.5)
```

Notes for encoding: u32 properties are native-endian like every existing
make_adt.py entry; `#address-cells/#size-cells` come from arm-io (2/2 — reg pairs
are each two u32 cells as written above). No `dma-coherent` property: MSM8916's
SDCC busmaster is NOT coherent (see risks); unlike NativeVirtioBlock the driver
must not require the property (VirtioMmioBlock.cpp:501 refuses start without it —
this driver checks for its presence and fails ADMA phases if absent, PIO fine).
test_board_adt.py gains a case: every node with `interrupts` (already checked
globally) and specifically sdhc1 decodes to INTIDs {155,170} and reg resolves to
0x07824900/0x07824000 after ranges translation; the emitted bytes for reg pairs are
<u32 lo,u32 hi?> consistent with how uart0/intc encode (the node uses the same
`node(...)` helper, LE u32 cells).

The interrupt cells: DTB uses type 0x00 for sdhc1 (edge/level as encoded by
qcom's GIC binding; the armcpu_spi_attach `edge` argument is derived by the driver
from the type field: bit 1 (0x02) means level-high; type 0 maps to edge per
existing binding practice). Vdd/pinctrl/clock phandles from the stock DTB are
deliberately NOT reproduced (no PMIC/pinctrl driver exists; regulators are
always-on by hardware strap on this board and LK leaves them configured).

### 3.5 Init paths

Resume path (default, `unixnu,handoff`): exactly the probe-proven sequence —
read HOST_CTRL1/PWR_CTRL/CLK_CTRL/HOST_CTRL2/DLL_CONFIG/VENDOR/DLL_STATUS;
require CLK_CTRL&7==7 and PWR_CTRL&1 else error 7 refuse start; enable HC_MODE
preserving state; PWRCTL ack; CMD5/CMD7 (RCA — the probe resumed LK's RCA 2;
driver reads the live RCA by keeping 2, and a future cold path assigns its own);
CMD8 EXT_CSD; reject non-user partitions (EXT_CSD[179]&7 → error 8); capacity =
EXT_CSD[215..212] and require it == 30,535,680 in diagnostic builds (mismatch is
only acceptable if a different card is fitted; log loudly).

Cold path (later, boot-arg `native-sdcc-cold=1`; only for cards under a live host
without LK): follow register-verified LK order — sdhci_msm_init (sdhci_msm.c:144:
VENDOR=0xA1C, HC_MODE enable + FF_CLK_SW_RST_DIS, full soft reset, power-irq
clear, caps override when minor ≠ 0x11/0x12), DLL init (sdhci_msm.c:304–380,
mclk frequency programming, DLL_RST/PDN/EN/CLK_OUT_EN, poll DLL_LOCK 50 µs),
CMD0 → CMD1 (until busy clears) → CMD2 → CMD3 (RCA=2) → CMD9 → CMD7 → CMD8 →
CMD6 bus-width 8-bit then HS timing switch (EXT_CSD[183]), host clock to 50 MHz
DDR or 100 MHz SDR per qcom,bus-speed-mode, HS200 tuning later (Phase 4). The
cold path is NOT required for Y35A bring-up (lk2nd always precedes XNU here) —
it exists so the driver is not a lab-only artifact; budget it after A+B land.

### 3.6 Requests, interrupts, DMA

Phase 0–2 run polled (like NativeVirtioBlock today and emmc_pio.h): bounded
waitStatus with mach_absolute_time deadlines (100 ms command, 250 ms data,
1 s erase-class — none in v1), INT_SIGNAL_EN=0 for hc (probe line 76:
`write32(0x38, 0)` — poll only), keeping the proven state machine.
Phase 3 adds interrupts: `armcpu_spi_attach(INTID 155, edge=false(level), handler, ctx,
&readback, &router)` (drivers/ArmCpu/ArmCpu.cpp:863 — GICv2 branch configures via
gicV2().configureSpi; slot budget 16, current users: none external; this is the
established non-IOKit path for SPIs in this build since no IODTInterruptController
nub exists). Handler clears a level source (W1C INT_STATUS) before return — the
ArmCpu contract: "handler runs in the primary interrupt context before EOI and
must clear a level source". pwr_irq 170 attached the same way (power events on
this always-on board are expected to be silent; the ack sequence §2.1 stays).
The driver must still poll as fallback (flag XNU_NATIVE_SDCC_POLL only builds
polling; default enables IRQ after Phase 3 acceptance).

DMA: PIO first (512 B × FIFO, no coherency problem at all). Phase 3 SDMA:
IOBufferMemoryDescriptor kIOMemoryPhysicallyContiguous, getPhysicalSegment,
set DATA_LINE address, then explicit `flush_dcache(addr, len, FALSE)`-style
maintenance (EXPORT_HDRS/bsd/libkern/libkern.h:235) — clean before read-
requests, invalidate after completion, with `dmb osh` before doorbell. Buffers
from IOMemoryDescriptor clients must be probed for >4 GB physical (SDMA/ADMA on
this part is 32-bit addressed: reject above 0xfffff000, bounce through the
transfer window). Phase 4 ADMA2 only after SDMA is stable (caps bit proven:
0x342dc8b2 bit19 set; descriptor table 256 B aligned, max segment 64 KiB per
LK sdhci.h:256).

### 3.7 Publication

`start()` on the sdhc1 nub: map windows → resume → EXT_CSD sanity → set
capacity/vendor/product strings ("Q313MB" from CID read at Phase 1 acceptance;
vendor "Qualcomm", product "Y35A eMMC sdhc1", revision from EXT_CSD[264 REV]) →
`reportWriteProtection` false only in write-enabled builds (Phase 3+; Phases 0–2
report true, matching VirtioMmioBlock's read-only discipline) →
registerService(). doAsyncReadWrite mirrors NativeVirtioBlock: validate
block/count/length under capacity, hold the gate, chunk at the transport's
transfer size, `buffer->writeBytes(...)` for reads, completion->action called
synchronously before return kIOReturnSuccess.

Store contract (Phase 2): `native_ufs_store_mode()` returns 2 (read-write
direct mode) when a window is approved; `native_ufs_store_open(pages)` maps the
RamBlock window into the **cache partition** (sectors 6,946,816..7,254,015,
150 MiB — sized to fit persist::windowBlocks for a ≤ 70 MiB disk; refuse if the
window exceeds the partition); `gpt_check` re-reads LBA 0/1 signature; read/
write use the same transport, write path FUA-equivalent (CARD_STATE program
completion + CMD6? eMMC has no FUA in HS SDR — the driver waits for DAT line
release + PRG bit clear in R1 before returning success, which is exactly the
durability PersistOverlay.h promises ("write() returns only when the blocks are
on the medium"); sync = no-op after that wait). Persist state machine and
fail-closed rules are RamBlock's, unchanged; this driver only answers the six
C symbols + a real store.

## 4. Feature phases with acceptance tests

Every device acceptance runs through the proven harness
(fastboot -s efff9d92 boot <image> → panic/get_staged or readback magic Y35ARD01;
TAKEOVER.md §harness). Every offline gate must pass before any device iteration.

Phase 0 — transport folded in, host-only. Files: SdciCore.h + Test/.
Acceptance (host): g++ -std=c++17 -fsanitize=address,undefined test suite passes
— extended model covers resume error 7/8/9, multi-block read, CMD6 switch,
write busy wait, FIFO bounds, and the store window math (off-partition writes
refused). Same command style as the emmc-pio host tests
(evidence/y35a-codex-20261103/emmc-pio-host-tests-20261104).

Phase 1 — resume + read + publish, device iteration #1.
Kernel flag XNU_NATIVE_SDCC=1, ADT node from §3.4, read-only personality.
What the fastboot-boot iteration proves (checkpoints volatile uint32/uint64
native_sdcc_* like native_virtio_*): probe bound the sdhc1 nub; resume success;
EXT_CSD capacity == 30,535,680; sector 0/1/2 read with GPT magic + CRC32 match
of the recorded emmc-gpt-verified-20261104.json; IOBlockStorageDevice started and
≥1 IOMedia child published (walk registry counts via armcpu-style counters);
IOFindBSDRoot log shows the new media offered. Failure closes to "no root change"
(RAMDisk path still wins; rd=md0 untouched) — this iteration cannot brick: it
writes nothing (transport compiled with write refusals, reportWriteProtection
=true).

Phase 2 — store contract, device iteration #2 (write gate #1 — needs explicit
user approval + staged backup of the 150 MiB cache partition before first write;
the backup is produced by the driver itself reading the partition to the
readback/fastboot staging path — see Boundaries). Acceptance: RamBlock
attachStore succeeds (native_data_persist_state == 3 fresh), marker page written,
warm reboot (PS_HOLD path already proven), state == 2 resumed, marker read back;
gpt_check returns "intact" and the cache partition bytes match the staged backup
outside the window. Only after this does "persistent Data" exist.

Phase 3 — write-capable IOBlockStorageDevice + SDMA + interrupts, device
iteration #3. Writes to the card remain confined to the approved cache window
until the user separately approves general partition access. Acceptance:
512-byte and 64 KiB writes land (readback verify), INTID 155 counter > 0 with
bounded IRQ count, unhandled-SPI count == 0 (armcpu_spi_unhandled), timeout path
forces reset and reports error code without panicking, write to LBA ≥ capacity
refused kIOReturnBadArgument.

Phase 4 — HS200/DDR52 + ADMA2 (optional perf), device iteration #4+.
Acceptance: bus-speed-mode switch via CMD6 completes with DLL retune (LK
sdhci_msm.c:457–746 phase-search ported), sustained read ≥ HS rate vs Phase 3
baseline (counters native_sdcc_bytes_per_sec), tuning retry ceiling 3, rollback
to HS-DDR52 on any CRC-class error (auto CMD12 + re-switch).

## 5. Offline proof plan (no hardware required)

1. Host: the Phase 0 suite above; ASan/UBSan; run in container with
   `-I` python isolation where scripts involved.
2. QEMU TCG (cortex-a53, virt,gic-version=2 — the 8.2.2 build in the container
   has `generic-sdhci` available but not MMIO-mappable on virt, and sdhci-pci
   needs a PCI host we do not enumerate). Instead extend the established
   live-GDB pattern (scripts/qemu-entry/live-hid.py precedent: host loop mutating
   guest-visible state while the kernel actually runs):
   `scripts/qemu-entry/live-sdhci.py` — boots the real kernel Mach-O through
   verify_shim/gdb-stop; the ADT's sdhc1 reg points at a reserved RAM page
   (fixture variant `--sdcc-emulation-window 0x85a00000` style), and the host
   loop services the register window with the same card model as the host unit
   tests (GPT image file + write log to a sparse file). The driver runs in
   polled resume mode; assertions read native_sdcc_* symbols via the existing
   GDB observer and compare against the recorded device GPT. This proves:
   personality binding + IOPlatformDevice nub resource resolution +
   IOBlockStorageDevice lifecycle + partition-scheme matching (IOApplePartition/
   IOGUID run for real in the prelinked closure) + IOFindBSDRoot selection +
   (Phase 2 sim) the store overlay round-trip across a simulated warm reboot —
   all on the exact shipped code paths, minus electrical timing.
3. ADT regression: new test_board_adt.py case decodes sdhc1 exactly as §3.4
   (red first, then green — order-locking per the four design iron-rules).

## 6. Risks

- HC_MODE boundary reset: enabling host mode cleared power/SDCLK/DLL once
  (measured, error-7 run). Mitigated by the preserve-restore sequence (measured
  good) + the refuse-to-start guard. Any Phase-4 retune must re-derive the
  sequence, not improvise.
- Non-coherent DMA: MSM8916 SDCC masters without cache coherency; any
  missing invalidate returns stale data silently. Mitigation: PIO until Phase 3,
  explicit maintenance + poison-byte model tests, SDMA size cap 64 KiB.
- Handoff variability: LK `sdhci_mode_disable` leaves the controller in compat
  mode with clocks still running (measured). If a future lk2nd changes the
  teardown, resume guard fails closed (error 7) rather than corrupting — cold
  path (§3.5) is the escape hatch, flagged opt-in.
- Write durability is a promise RamBlock's PersistOverlay.h encodes; an
  eMMC program completes asynchronously (PRG bit). If the write returns early,
  a crash loses pages the bitmap claims. Mitigation: DAT12-busy wait + R1 PRG
  poll before completion; host model covers the delay injection.
- SPI slot budget: armcpu_spi_attach has 16 slots shared with future subsystems
  (touch 131, hsuart 139 will arrive). Two slots here is proportionate; note in
  cross-subsystem ledger.
- Single point of failure: this device serves the only persistent medium. No
  panic-from-driver paths except the VirtioMmioBlock precedent "unverified DMA
  could not be quiesced" — kept for the store window (a store that cannot be
  quiesced must not continue writing); every other failure returns IOReturn and
  degrades to volatile RAMBlock.
- userdata is NOT backed up (board facts). All device write iterations are gated
  behind staged-backup approvals (§4 Phase 2/3), and Phase 1 is compiled
  write-refusing. This is a hard boundary, not a risk to accept.

## 7. Boundaries

- Always: host tests green before any kernel build; verify: lines in commits cite
  real executed commands; ADT edits land with their regression test in the same
  commit; reg property order stays hc,core.
- Ask first (this workflow's owner, i.e. the main session / user): any device
  write iteration; editing make_adt.py (spec here is the ask); adding the
  XNU_NATIVE_SDCC flag to build_native.py's default flag set (keep it opt-in
  until Phase 1 device acceptance passes once).
- Never: write any partition except the user-approved store window; touch sdhc2
  (WiFi subsystem's bus); copy lk2nd/GPL code (register knowledge only, clean
  room); push; add Co-Authored-By trailers; delete user partitions.

## 8. Files to create (plan, none beyond SPEC.md made now)

- drivers/QcomSdcc/{SPEC.md, README.md, AGENTS.md, LICENSE (BSD-2-Clause-Patent
  like siblings), SdciCore.h, NativeSdcc.cpp, PersistStore.cpp, Test/sdcc_host.cpp,
  Test/sdcc_store.cpp}
- patches/xnu/native-sdcc-personality.patch
- scripts/build-arm-driver.py (NativeSdcc branch edits), components.toml entry,
  scripts/build-xnu-4k-baseline.sh flag+archive stanzas, scripts/y35a/build_native.py
  opt-in flag, scripts/y35a/make_adt.py sdhc1 node (+ test_board_adt.py case)
- scripts/qemu-entry/live-sdhci.py + its checkpoint asserts
- docs update line in docs/porting/platform.md block table (after Phase 1 green)

## 9. Open questions for the owner

1. RCA value on resume: adopt LK's 2 (probe-proven) or re-assign via CMD2+CMD3
   each boot? (Recommend adopt-with-verify: CMD2 read, require current-RCA match
   or re-select.)
2. Store window choice: cache (150 MiB, wipes Android cache — safe) vs oem
   (64 MiB, vendor data) vs a carved sub-range of userdata (largest, needs
   userdata backup first). Spec assumes cache.
3. Should Phase 1 also attach the store contract disabled-but-present
   (mode()==0, "blank probe" state 1) to de-risk RamBlock interactions early?
