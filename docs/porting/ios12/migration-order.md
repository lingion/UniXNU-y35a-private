# Migration order: container build to four verified hardware domains

Synthesized 2026-11-04 from the four read-only recon reports (R1/R2/R3/R4 labels as in
`boot-chain.md`). Sequenced so each gate closes with evidence that is either a host
command output or a device readback; no gate may be declared passed on reasoning alone.
Companion docs: `boot-chain.md` (deltas D1-D9), `drivers-plan.md` (per-driver detail).

Two standing rules for every gate below:
- Observability first. The only bring-up telemetry that exists is the early-fault record
  at `args_pa+0x800` (`package_native.py:215`, written by `native-early-fault-record.patch`
  into `osfmk/arm64/locore.s`+`start.s`) read back by `scripts/y35a/readback_native.py`,
  plus whatever console we make work (R1). A gate with no console is still readable —
  but only through that record, so it must be working before we start guessing.
- Never trust a number that was not recomputed this session. Reports earlier in this
  project were caught fabricating SHAs, kext counts, and a wrong board id; the
  `TEST_READY.md`/`TEST_INFRA.md` pair at repo top contradicts board facts (gpio915 does
  not exist on MSM8916; touch is TLMM 12/13 per the DTB) and is untrusted output
  (R4 3.5, working context).

## Phase 0 — resolve the blocked facts (no device work possible until then)

| Step | Work | Gate closes on |
|---|---|---|
| 0.1 | Regenerate the missing KPP payload: re-run the kernelcache reconstruction so `dl/kpp-payloads/kernelcache.reconstructed.release.fused` exists (R4 3.5: absent; context claimed 54 MB) | file present with recorded sha256; nothing downstream is trusted without it |
| 0.2 | Settle the j96ap Mach-O identity: authoritative header dump of `out/y35a/ios12-kc/kernel.macho` (R2/R4 read filetype 0x2 = MH_EXECUTE, every report calls it MH_KEXT_BUNDLE = 0xc) | single quoted `flags:` line, plus load-command count (22 measured) and the exact absence of `0x2e` LC_DYLD_CHAINED_FIXUPS |
| 0.3 | Settle the kext census with a committed tool (today only `tools/uncomplzss.py` exists; the three parse tools named in the working context are absent, R3/R4). Publish measured numbers: 22 load commands, 502-503 raw CFBundleIdentifier strings, 184-193 plist entries, tail cut by section padding so 193 is a floor | tool in `tools/`, output reproducible from the pinned sha256 `70e80388...` |
| 0.4 | Resolve the SDHC2 IRQ conflict (R3: hc SPI 9 / pwr SPI 221 / card-detect GPIO 38; R4's WiFi paragraph states SPI 107/238/GPIO 1, which are the hsuart values) by re-reading `dtb10-stock.dts:5467-5500` | one line quoted per child, adopted into `drivers-plan.md` §1 |
| 0.5 | Decide host-vs-container source of truth: container `unixnu-y35a-native-20261103` mounts `/work` as a **named docker volume** holding independent copies of `UniXNU-y35a`, `xnu-4570`, `lk2nd-y35a-codex` — not a bind mount of `~/unixnu-research` — and `~/unixnu-research/lk2nd-y35a-codex` does not exist on the host at all (R4 0) | a stated rule (which tree builds) plus a diff of the two trees' HEAD shas; a green container build proves nothing about host sources until this is closed |

Phase 0 gate: all five items have quoted output. Nothing in Phase 1 is a design decision
anymore — D2/D3/D4 shapes depend on 0.2 and 0.3.

## Phase 1 — kernel builds in the container

| Step | Work | Gate closes on |
|---|---|---|
| 1.1 | Add `ARM64_BOARD_CONFIG_MSM8916` in `pexpert/pexpert/arm64/board_config.h:8-96` — `KERNEL_INTEGRITY_WT` (KPP-era, per R2), `ARM_ARCH_TIMER`, deliberately **not** `APPLE_ARM64_ARCH_FAMILY` (it compiles in the Apple FIQ/event-timer path and `fleh_fiq_generic` is PANIC_UNIMPLEMENTED at `locore.s:718-720`) | preprocessor dump showing the resolved macro set for the new board |
| 1.2 | Introduce a 4570 machine config replacing the `MACHINE_CONFIGS=BCM2837` hard-wiring (`build-xnu-4k-baseline.sh:815`, `config/MASTER.arm64.bcm2837` does not exist in 4570); keep `ARM64_LINK_ADDR=0xfffffff007004000` (kernel TEXT base measured identical, R2) and re-derive `ARM64_PLKSEG_ADDR` / the segment-plkseg split from the j96ap map in `boot-chain.md` §1 | object built; `vm_kernel_slide = segTEXTB - 0xfffffff007004000` (`arm_vm_init.c:1336`) evaluates to 0 for a base load |
| 1.3 | Re-apply the boot-critical patch intents **against 4570 sources** (they are 10063 patches; the files differ): uartdm console (`pe_serial.c`/`protos.h`/new `uartdm.h`), dt-panic-region (`pe_init.c`), arch-timer entry (`start.s`), early-fault record (`locore.s`+`start.s`), native crypto instructions (`sleh.c` + new `native_crypto.h`), non-apple cache monitor (`arm_vm_init.c`, `caches_asm.s`), non-apple iommu bootstrap + pmap field (`pmap.c`/`pmap.h`) (R1 patch table) | each patch applies with fuzz 0; the 11 `build_native.py:32-38` flags all set |
| 1.4 | Add a polled 16550/GSBI `pe_serial_functions` table to 4570 `pe_serial.c` — the in-tree generic 16550 branch is gated to a Marvell board (`pe_serial.c:799-800`) and the S3CUART offsets do not match the Qualcomm 16550 map (R2 point 2) | host unit test of the register table, then gate 2.3 on device |
| 1.5 | Decide the kext delivery route. An open `make` writes `/dev/null` into the three prelink segments (`makedefs/MakeInc.def:333-339`) and there is no `PRELINK_KEXTS` list and no DEPCONF in this drop (R2 point 8), so a stock build always lands `prelinkInfoSect->size == 0` and boots via `readBooterExtensions` (`bootstrap.cpp:222,587`) | a written choice: (a) external prelink onto the KPP cache via the patched `emit_prelink.py`, or (b) ship a mkext to the booter and take the dynamic path. Option (b) is the shorter first boot; option (a) is what our drivers eventually need |

Phase 1 gate: a `mach.development.*` MH_EXECUTE kernel links in the container with the
new board config and force-loaded ArmCpu/ArmDTPlatform archives. Device evidence: none
yet, and the doc must not imply any.

## Phase 2 — boot to a root and launchd

| Step | Work | Gate closes on (device evidence) |
|---|---|---|
| 2.1 | ArmCpu GICv2 attach for real hardware: `interrupt-controller@b000000` dist 0xb000000+0x1000 / cpu-if 0xb002000+0x1000 (`qcom,msm-qgic2`, phandle 0x01), arch timer PPIs 2/3/4/1 at 19.2 MHz (dtb L5061, L5090). `UniXNU-msm8916-common/soc.toml` lists XNU-platform-expert acceptance of GICv2 as the unverified first-bring-up question | lk2nd + `readback_native.py` register readback of GICD_CTLR / GICD_ISSETGER after ArmCpu init, serial console printing the values |
| 2.2 | lk2nd sets `CNTFRQ_EL0` to 19.2 MHz and the ADT `/cpus timebase-frequency` matches — nothing in the kernel programs CNTFRQ (EL3/bootloader duty, R2 point 4), and the generic-timer fallback (`CNTPCT_EL0`/`CNTP_TVAL_EL0`/`CNTP_CTL_EL0`, `machine_routines.c:1520-1759`) is the live path because `pe_arm_init_timer` returns 0 without installing tbd ops (`pe_identify_machine.c:583-669`) | `mach_absolute_time` advances at the expected rate on device (two timestamps across a known sleep, measured error under one percent) |
| 2.3 | Synthesize the ADT through `make_adt.py:make_tree` — hard-required nodes: `arm-io` (+`device_type`, `ranges` reg[1] = SoC phys base), `/cpus` children (+`reg`,`cpu-id`,`state`="running",`clock-frequency`,`timebase-frequency`), `chosen` (+debug props, `boot-device`), root `device-tree` (+`target-type`,`model`), `boot-console` uart with `reg` **relative** to the arm-io ranges base (`pe_serial.c:762`) (R2 point 1, checklist row 2). Feed **no** raw DTB to `deviceTreeP`: `DTInit` casts straight to ADT and there is zero FDT code in the tree (R2) | `scripts/y35a/test_board_adt.py` encode/decode regression passes; on device the console comes up and `pe_identify_machine` returns a non-zero soc_base (proven by reaching `printf_init`, `arm_init.c:313`) |
| 2.4 | Boot the packaged container: `package_native.py` layout (2 MiB-aligned RAM base, boot_args, ADT, sidecars, EL1 shim entering at `0x80080000`, `ANDROID!` wrapper with the filtered QCDT partition, 50 MiB download budget) — all of it already measured on MSM8916/Y35A and carried unchanged (R1 §2 of carry list) | first boot attempt: either console output, or an early-fault record read back at `args_pa+0x800`. A silent boot with no record means the shim never handed off, which is a different bug and must be diagnosed separately |
| 2.5 | Polled SDHCI eMMC (Phase 3 driver work can run in parallel from here): publish `IOBlockStorageDevice` so stock `IOBlockStorageDriver`+`IOGUIDPartitionScheme`+`IOMediaBSDClient` build media, and mount the HFS+ root over `/chosen boot-device` (`IOPlatformExpert.cpp:1155`, `IONVRAM.cpp:876`) | `launchd` starts from the mounted root on device console (pivot doc: iOS 12 root is HFS+, shared cache ~300 MB) |

Phase 2 gate, and it is the biggest single gate: XNU userland reachable with the root
mounted and `launchd` running. Note the QEMU path cannot substitute: `verify_shim.py`
is a **loader** verifier with `hardware_boot_demonstrated=False` (R4 1) — it proves
segments land, not that msm8916 hardware works.

## Phase 3 — the interrupt gate (before any IRQ-driven domain)

| Step | Work | Gate closes on |
|---|---|---|
| 3.1 | Write the `IOInterruptController` provider kext. xnu-4570 has **no** GIC driver and **no** interrupt controller source at all: `ml_init_interrupt()` is an empty stub (`machine_routines.c:754-759`), `pe_arm_map_interrupt_controller` maps Apple AIC/S3c MMIO only (`pe_identify_machine.c:520-565`), the sole IRQ ABI is `fleh_irq`→`sleh_irq` (`sleh.c:1297`)→`cdp->interrupt_handler` set by `machine_install_interrupt_handler` (`machine_routines.c:743`), and the stock cache carries no `AppleGIC`/`GICv` (only Apple's own per-board `AppleInterruptController`, idx 53) (R2 point 3, R3 section 2) | a device test with no driver dependency: arm a software-generated or freely-toggling GPIO interrupt (PM8916 SPMI GPIO 0-3, dtb L7122) through the new controller and observe the handler fire on console. This is the one gate that must pass before Phase 4 opens |
| 3.2 | SPI ledger: touch 99, GPU 33 + gfx ctx 241/242 + global 42/43, SDHC1 123/138, SDHC2 9/221, hsuart 107, hsuart/i2c5 shared BAM 238, TLMM cascade 208 — allocated through `armcpu_spi_attach` (`drivers/ArmCpu/ArmCpu.cpp:863`, SPEC §3.6) with its 16-slot ledger note respected (R4 3.2) | ledger printed at boot; no duplicate INTID; no slot overflow |
| 3.3 | Power-path decision. Every rail the drivers need (L2, L5, L6, L8, L11, L12, L16, L17, s1_corner) is an **RPM-SMD** regulator (`qcom,rpm-smd-regulator`, e.g. dtb L6012), commanded over SMD/GLINK to RPM (APSS), not through the local `spmi-pmic-arb` at 0x200f000 — and the arb register base, its IRQs, and the PM8916 SPMI regulator base were all not read (unknown, R3 table + unknowns) | either an SMD/RPM request path proven on device (raise one rail, read it back), or a documented direct-SPMI fallback with the base actually measured. GDSCs first where possible (gx 0x185901c, mdss 0x184d078) since they are GCC-side and cheaper |

## Phase 4 — hardware domains, in this order

Order rationale: the display floor is the only thing already designed and partially
proven, so it buys observability for everything after; touch is the smallest
single-IC job that exercises the new interrupt path end to end; WiFi and BT share the
WCNSS power-up and SMD transport, and BT's serial consumer already exists in-cache; the
GPU command path is last because its userspace depth is the least certain.

| Order | Domain | Gate closes on (device evidence) |
|---|---|---|
| 4.1 | **Display floor** (not one of the four, but a prerequisite for judging the rest) — `GopFramebuffer`'s `NativeLegacyDisplay : IOMobileFramebufferLegacy` over the lk2nd-verified continuous splash at 0x83200000, 720x1280, RGB888, stride 2160; ABI hand-pinned in `OriginalMobileFramebufferABI.h` (R4 3.3) | pixels on the panel; a userspace `IOMobileFramebuffer*` call (ChangeFrameInfo family, 404 DSC strings) returns success against our service |
| 4.2 | **Touch** — QUPv2 I2C master provider (SE 0x78b9000/0x600, BAM 0x7884000, qup IRQ SPI 99, pipes 12/13, GPIO 18/19 func 2), RMI4 S3202 at 7-bit 0x20, reset GPIO 12, attn GPIO 13 falling, rails L16/L6; publish `IOHIDEventService` with a digitizer report descriptor via `kIOHIDReportDescriptorKey`; map 1266x2220 to 720x1280 (R3, R4 3.2) | one finger drag produces an event stream that in-cache `IOHIDEventDriver` and `backboardd` consume; coordinate affine check passes at both screen edges; the vivo virtual-key region and dclick box x[160:1106] y[160:2060] behave |
| 4.3 | **BT transport first** — QUP-HS-UART kext on `uart@78af000` (core 0x200, shared BAM, pipes TX0/RX1, master-id 0x56, core IRQ SPI 107, BAM 238, wake GPIO 1) publishing an `AppleOnboardSerialSync` nub so the stock prelinked `AppleOnboardSerial` (idx 66) + `IOSerialFamily` (idx 166) create the callout device | `/dev/uart.bluetooth`-equivalent node appears; `bluetoothd` (present in `dl/mnt-j96/usr/sbin/`) opens it; an H4 reset/read-version command over the wire returns a well-formed HCI packet. The `cu.bluetooth`/`uart.bluetooth` name is runtime `IOCalloutDevice` inference, not a cache string (R3) |
| 4.4 | **WiFi** — needs the SMD transport mini-driver first (`qcom,smd` + `smp2p` + wcnss-pil; `smp2p-wcnss` L587, `smd-wcnss` L5614, pronto bank `qcom,wcnss-wlan@0a000000` L6700-6723, 5-wire GPIO 40-44 L1547), then wcn36xx port over sdhc2, then an `IO80211Controller` subclass delivering `en0` (R4 3.4). Scope v1 to association using `src44/` as the simpler baseline | `en0` appears; scan returns the network list; association plus a ping through the interface. If `IO80211Family` needs an IOSkywalk provider to attach at all, that is a finding to report, not to design around silently |
| 4.5 | **GPU** — the part that is *not* gated by userspace uncertainty: RSCC + RGX core 0x1c00000/0x1c10000, qfprom 0x5c000, IRQ SPI 33, GX via gdsc_oxili_gx, **no GMU** (0 DTB hits) so CP-based bring-up, pwrseq0/1/2, ladder 400/307.2/200/19.2 MHz; `gfx_iommu@0x1f00000` ctx1 SID 0 / ctx2 SID 1 with ctx IRQs 241/242 (R3, R4 3.3). Requires the freedreno `a3xx.xml`/rgsl fetch (not on disk) | PM4 submission completes: a rendered frame lands in an `IOSurface` and is blitted to the 4.1 display path; `chipid` 0x3000600 read back over the register bus |
| 4.6 | **Acceleration surface** (separate gate from 4.5 on purpose) — publishing `IOAcceleratorFamily2` (398.9 in closure) / `IOSurfaceRoot` (0x70f458) shapes so CoreGraphics can reach the driver. Honest state: **unknown** how far a non-AGX IOAccelerator goes, because the DSC accelerator tokens (`AGX*` user-client names, `IOAccelerator`) are Apple-AGX-shaped (R4 3.3) | either an in-cache IOAccel client completes a context against our driver, or the attempt is documented as a dead end with the specific failure — framebuffer + CPU render remains the shipped floor either way |
| 4.7 | **Fold drivers into the image** — `kits/XnuPrelink/emit_prelink.py` after the D2-D5 deltas, onto the Phase 0.1 payload; iOS 12 relocation input is packed `_PrelinkLinkKASLROffsets`, never chained fixups | a flashed image where every 4.2-4.5 domain is present as a prelinked kext, not loaded out of band |

## Phase 5 — flash and the acceptance sweep

| Step | Work | Gate closes on |
|---|---|---|
| 5.1 | Flash the final container through lk2nd fastboot (device serial `efff9d92`; USB fastboot is currently in lk2nd forced-fastboot; the network adb `192.168.1.10:5555` is a TV, **not** this phone). Treat every device write as a gated, user-approved action — the working tree is otherwise read-only research | the flashed image boots from a cold start with no host-side re-flash loop |
| 5.2 | Re-run the whole sweep on the flashed build, no partial credit | touch event stream, GPU-rendered frame to panel, WiFi association + ping, BT HCI exchange, root mounted, `launchd` up, `mach_absolute_time` rate error under one percent, SPI ledger clean |
| 5.3 | Evidence bundle: recomputed sha256s of kernel, payload and flashed image; the early-fault record empty across the sweep; the four-domain device outputs captured | a report where every number traces to a file read or a command run in the reporting session — the standing rule from the context, enforced by the fabricated-report history |

## Stop conditions worth naming up front

- Phase 3.1 failing means none of 4.2/4.4/4.5 can close, and the fallback for the whole
  project is polled-mode bring-up only. Plan that as a reported outcome, not a silent
  downgrade (aesthetics-over-performance and no-silent-degradation rules both apply).
- Phase 4.6 failing does **not** fail the mission: the display floor plus CPU render is
  an already-chosen path, and it is honest to ship it while the accel gap is reported.
- Phase 0.1 and 0.5 failing blocks everything else; do not design past a missing payload
  or an unresolved host/container divergence (R4 0 and 3.5 both flag this explicitly).
