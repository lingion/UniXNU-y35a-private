# Boot chain: iOS 12.4.1 (xnu-4570.51.1) on vivo Y35A (MSM8916)

Synthesized 2026-11-04 from four read-only recon reports (R1 boot-chain audit, R2 xnu-4570
boot recon, R3 DTB/kext facts, R4 driver ground truth); file:line refs are as those reports
read them. Unsupported items are marked (verify). Companions: `drivers-plan.md`,
`migration-order.md`.

## 1. How xnu-4570 boots on a non-Apple arm64 board

- **Entry contract.** `struct boot_args` carries `deviceTreeP`/`deviceTreeLength`,
  Revision/Version, virtBase/physBase/memSize/topOfKernelData/Video/machineType/
  CommandLine/bootFlags (`pexpert/pexpert/arm64/boot.h:44-58`; read `start.s:415-420`,
  snapshotted read-only `osfmk/arm/arm_init.c:150`). The format-1 byte-verified layout
  (offsets 0x08/0x10/0x18/0x20/0x60/0x6c/0x478, size 0x480) is stable 12→17 (R1; R2 row 1).
- **Device tree is ADT, never FDT.** `pe_init.c:293/310` passes `deviceTreeP` straight to
  `DTInit`, which casts to an ADT node and pointer-walks with no magic check and no byte
  swap (`pexpert/gen/device_tree.c:160-164`; layout `pexpert/pexpert/device_tree.h:67-95`).
  Grep `0xd00dfeed`/`fdt_` tree-wide: zero matches (R2). A dtc-built stock DTB fails
  `DTFindEntry`, so `pe_identify_machine` returns at `:55-56` with soc_base 0 and boot dies
  before `printf_init` (`arm_init.c:313`). `dtb10-stock.dts` is a facts source, not an input.
- **Hard-required ADT nodes** (R2): `arm-io` (name, `device_type`, `ranges` with reg[1] =
  SoC phys base — `pe_identify_machine.c:225-244`); `/cpus` children with `reg`, `cpu-id`,
  `state`="running", `clock-frequency`/`timebase-frequency`/`bus-frequency`
  (`machine_routines.c:783-860`, `pe_identify_machine.c:110-165`); `chosen`
  (`debug-enabled`, `firmware-version`, `/chosen/iBoot` — `pe_init.c:345-380`); root
  `device-tree` with `target-type`+`model` (`pe_init.c:322-344`); console uart via
  `boot-console` (preferred) else uart0/uart1, `reg` **relative** to the arm-io ranges base
  (`pe_serial.c:762`).
- **IOKit plane.** `StartIOKit(deviceTreeHead,...)` (`pe_init.c:310`) builds `gIODTPlane`
  keyed on `name`/`compatible`/`reg`/`interrupts`/`#*-cells`/`ranges`
  (`IODeviceTreeSupport.cpp:114-146`), matching at `:859-860`; root nub
  `IOPlatformExpertDevice` (`IOStartIOKit.cpp:120,1611`). `DTGetProperty` returns native-endian
  values with no conversion (`device_tree.c:362-382`). Root mount uses `/chosen`+NVRAM
  `boot-device` (`IOPlatformExpert.cpp:1155`, `IONVRAM.cpp:876`).
- **Early console is polled and board-tabled.** `arm_init` → `printf_init`/`PE_init_kprintf`
  (`arm_init.c:313,322`) → `serial_init()` (`pe_kprintf.c:37-40`) → `gPESF` dispatch
  (`pe_serial.c:30-37,812-818`). No arm64-usable 16550 exists: the generic branch is gated to
  a Marvell board (`pe_serial.c:799-800`) and the S3CUART register map does not match a
  Qualcomm GSBI/BLSP 16550, so `ln2410_td0` would write the wrong register (R2).
- **Interrupts: none in the open tree.** `ml_init_interrupt()` is an empty stub
  (`machine_routines.c:754-759`); `pe_arm_map_interrupt_controller` maps Apple AIC/S3c MMIO
  only (`pe_identify_machine.c:520-565`); the only IRQ ABI is `fleh_irq`→`sleh_irq`
  (`sleh.c:1297`)→`cdp->interrupt_handler` installed by `machine_install_interrupt_handler`
  (`machine_routines.c:743`) — normally by AppleARMInterruptController, whose source is absent
  (`iokit/Families/` has only IONVRAM + IOSystemManagement). `fleh_fiq_generic` = PANIC
  (`locore.s:718-720`). So the ArmCpu kit does work the kernel cannot finish: IRQ-driven
  drivers need our own `IOInterruptController` provider (R2 point 3).
- **Timebase: generic-timer fallback is the live path.** `ml_get_hwclock` = `mrs CNTPCT_EL0`,
  decrementer `CNTP_TVAL_EL0`/`CNTP_CTL_EL0` (`machine_routines.c:1520-1759`), used when
  `cdp->{get,set}_decrementer_func` are NULL — which they are, because `pe_arm_init_timer`
  returns 0 before `ml_init_timebase` for non-listed SoCs (`pe_identify_machine.c:583-669`).
  Nothing programs `CNTFRQ_EL0` (EL3/bootloader duty); lk2nd must set it (19.2 MHz here) and
  ADT `/cpus timebase-frequency` must match or `mach_absolute_time` scales wrong. The
  CNTKCTL event timer is compiled out off-Apple (`#if APPLE_ARM64_ARCH_FAMILY`).
- **Kernel integrity = write-through.** `config/MASTER.arm64:82` `CONFIG_KERNEL_INTEGRITY`;
  mode picked per SoC in `pexpert/pexpert/arm64/board_config.h`. KPP-era A7/A8 boards are
  `KERNEL_INTEGRITY_WT`; KTRR guards are `#if`-inactive under a WT board
  (`start.s:44/116/375`, `pinst.s:54/107`, `arm_vm_init.c:210/241/608/678/1016/1120`) and
  `KERNEL_INTEGRITY_CTRR` does not exist in 4570 (grep 0 in `osfmk/arm/pmap.c` — that is
  iOS 13+ RootOLKE). KPP/SMC/serrano enforcement lives entirely outside XNU: tree-wide grep
  for `serrano`/`kern_kptr` is empty (R2).
- **KASLR and relocations.** `vm_kernel_slide = segTEXTB - 0xfffffff007004000`
  (`arm_vm_init.c:1336`); the j96ap TEXT base is exactly that value, so `ARM64_LINK_ADDR`
  carries (R1, R2, `docs/board/pivot-ios12.md`). Measured `out/y35a/ios12-kc/kernel.macho`
  (sha256 70e80388…, 30228480 bytes): 22 load commands, `LC_BUILD_VERSION` platform 2 with
  minos/sdk 0xc0400 (12.4), one `LC_DYLD_INFO` with rebase_off/size 0/0, **zero**
  `LC_DYLD_CHAINED_FIXUPS` (0x2e) (R2/R3/R4). iOS 12 slides kext pointers with the packed
  `_PrelinkLinkKASLROffsets` table, not chained fixups.
- **Prelinked-image loader.** `libsa/bootstrap.cpp:219` reads its own `__PRELINK_INFO/__info`
  section (keys `libkern/libkern/prelink.h:32-53`). Non-empty → `readPrelinkedExtensions`
  (XML plist via `OSUnserializeXML` `:346`, `_PrelinkInfoDictionary` array `:395-401`,
  per-kext `OSKext::withPrelinkedInfoDict` `:474`, slide applied `:457`, `OSKext.cpp:1575-1597`).
  Empty → `readBooterExtensions` (`:222,587`). Measured: `__PRELINK_INFO` fileoff 0x1ad0000,
  vmsize 0x204000, plist opening `_PrelinkInfoDictionary`→`<array>`; census
  `_PrelinkBundlePath`×193, `_PrelinkExecutableRelativePath`×185,
  `_PrelinkExecutableLoadAddr`/`SourceAddr`/`Size`/`KmodInfo` ×184, `_PrelinkInterfaceUUID`×7,
  plus top-level `_PrelinkLinkKASLROffsets` and `_PrelinkKCID` (R3). Segments:
  `__PRELINK_TEXT` 0xfffffff005ca0000/0x488000, `__TEXT` 0xfffffff007004000, `__TEXT_EXEC`
  0xfffffff007098000/0x530000, `__DATA` 0xfffffff0075d0000/0xa8000, `__KLD`
  0xfffffff0075cc000, `__PLK_TEXT_EXEC` 0xfffffff006128000/0xcc4000, `__PLK_DATA_CONST`
  0xfffffff006dec000/0x218000, `__PRELINK_DATA` 0xfffffff0076f4000/0xf0000, `__LINKEDIT`
  0xfffffff007690000/0x62e68 (R2/R3).
- **Open-build gap.** `makedefs/MakeInc.def:333-339` creates the three prelink segments from
  `/dev/null`, so a stock build lands `prelinkInfoSect->size == 0` and boots via
  `readBooterExtensions`. No `PRELINK_KEXTS` list, no DEPCONF anywhere in the drop (grep/find:
  none), therefore no KPP-board config to copy; board selection is compile-time
  `-D ARM64_BOARD_CONFIG_<NAME>` through `board_config.h:8-96` (S5L8960X…T8011; no BCM2837,
  no msm8916) → a new board block is mandatory (R2 point 8).

## 2. Current format-1 pipeline (three stages plus the device loop)

Per R1: (A) `scripts/y35a/build_native.py` sets 11 flags (`:32-38` `XNU_BOOTSTRAP=0`,
`XNU_SOURCE_CORECRYPTO14=1`, `XNU_CRYPTO_BOOTSTRAP=prelinked`, `XNU_ARMCPU=1`,
`XNU_SOURCE_PTHREAD=1`, `XNU_NATIVE_EARLY_FAULT=1`, `XNU_NATIVE_CRYPTO_INSTRUCTIONS=1`,
`XNU_ARM_DT_PLATFORM=1`, `XNU_NATIVE_UARTDM=1`, `XNU_NATIVE_ARCH_TIMER=1`,
`XNU_DT_PANIC_REGION=1`), sha256-pins the original cache (`:46-47`), builds
`libArmDTPlatform.a`/`libArmCpu.a` via `scripts/build-arm-driver.py` (`:50-52`), then
`scripts/build-xnu-4k-baseline.sh` (`:56`) → MH_EXECUTE force-loaded at
`ARM64_LINK_ADDR=0xfffffff007004000` (`build-xnu-4k-baseline.sh:654,663-672,815`).
(B) `kits/XnuPrelink/emit_prelink.py` grafts the Apple kext closure onto that kernel:
plist read `:128-131`, roots selection `native_prelink.py:146-159`, segment copy into empty
coalesced `__PRELINK_*` `:181-204`, KASLR table rebind `:209-210`, module/kmod rewrite
`:213-238`, sparse `__macho_list` `:239-251,273-291`, new `__PRELINK_INFO` `:263-272` —
hard-requiring two 10063 ABI markers (`:120-126,138-145`).
(C) `scripts/y35a/package_native.py` parses it (`:55`→`boot_layout.py:31`), picks a
2 MiB-aligned RAM base (`:56`, `boot_layout.py:8-13`), lays boot_args + ADT (`:76-82`,
`make_adt.py:28` `device-tree` root with `/cpus`,`/timer`,`/arm-io`→`intc`/`uart0`,
defaults, options, chosen+NVRAM proxy), emits the EL1 handoff shim (`:91-201`; enter kernel
at `0x80080000`, `:203`), wraps `ANDROID!` with a filtered QCDT DTB partition for
MSM8916/MTP/subtype 23 (`:40-52,18-38`, 50 MiB budget `:44`). On device lk2nd loads the
container, the shim jumps into XNU `start.s`; console is BLSP UART-DM
(`patches/xnu/native-uartdm-console.patch`, gated on `pe_serial.o`,
`build-xnu-4k-baseline.sh:513`); GICv2/timer/psci from ArmCpu
(`port/msm8916-gicv2-y35a`). Bring-up telemetry is the early-fault record at
`args_pa+0x800` (`package_native.py:215`, `native-early-fault-record.patch` into
`locore.s`/`start.s`) read back by `readback_native.py`.

## 3. Carries over unchanged (format-agnostic)

`boot_layout.py` (`parse_macho:34` already accepts MH_EXECUTE 2 **and** MH_KEXT_BUNDLE 0xc);
`package_native.py` + `make_adt.py` + EL1 shim in full (built from measured MSM8916/Y35A
facts; `pivot-ios12.md` lists them as not-scrapped); DarwinBoot boot_args ABI (R2 row 1);
patch intents uartdm-console, arch-timer-entry, dt-panic-region, early-fault-record,
crypto-instructions (scalar ARMv8 for the AES/SHA-less A53), arm-pan, non-apple cache-monitor /
iommu-bootstrap / pmap-field — generic arm64/Qualcomm targets, but re-applied to 4570 contents,
not replayed as 10063 patches; ArmCpu (GICv2) + ArmDTPlatform scaffolding (`dependencies=[]`,
no SM8550 tie); SoftwareAES; RamBlock; VerifiedRoot kit (pure sha256/rsa3072);
XnuPrelink engine concept. Caveat: QcomGeniSpi is reusable as a component/test *template*
only — MSM8916 is pre-GENI QUPv2, so its programming does not apply here (R4 3.2 overrides
R1's carry claim for this SoC). The iBoot-side QCDT partition stays for the stock bootloader;
XNU never reads it.

## 4. Delta list (ordered)

- **D1 board config**: add `ARM64_BOARD_CONFIG_MSM8916` in `board_config.h` — WT integrity,
  `ARM_ARCH_TIMER`, not `APPLE_ARM64_ARCH_FAMILY`; replace `MACHINE_CONFIGS=BCM2837`
  hard-wiring (`build-xnu-4k-baseline.sh:815`; `source-machine-layer.patch` targets
  `config/MASTER.arm64.bcm2837`, absent in 4570). Re-derive `ARM64_PLKSEG_ADDR` and the
  segment/plkseg split; TEXT base carries.
- **D2 prelink kind assert**: `native_prelink.py:135` requires MH_EXECUTE on **both** sides
  (`emit_prelink.py` inherits via `plan`); the j96ap cache is reported MH_KEXT_BUNDLE by all
  four reports while R2/R4 header walks read filetype 0x2 (§6) → resolve, then relax.
- **D3 legacy plist**: `native_prelink.py:141-159,197-201` was qualified on iOS 17; iOS 12
  needs the legacy `_PrelinkInfoDictionary` array + top-level packed
  `_PrelinkLinkKASLROffsets`; slide/geometry in `emit_prelink.py:197-268` and the 32-bit fit
  check `:265-266` are 17-generation.
- **D4 ABI markers**: the two symbols `emit_prelink.py:120-145` demands are injected by
  `kits/XnuPrelink/patches/xnu-10063.141.1-{sparse-index,security-init}.patch` into 10063
  `osfmk/kern/kalloc.c` and `libkern/c++/OSKext.cpp`; re-author against 4570 or drop the
  sparse index and emit a dense module list.
- **D5 no chained fixups**: anything touching `LC_DYLD_CHAINED_FIXUPS`/`fixup.chains`/
  `LC_KEXT_*` is iOS 13+ and does not apply (R2).
- **D6 security-init constructs**: no Image4/AMFI/CTRR/KTRR/KernelCollections/cryptex path;
  trust-cache runtime patch (`osfmk/kern/startup.c`), `XNU_OWNER_ROOT_*`, union-root,
  work-interval, mockfs, GPU-mount, sandbox-grant are format-1 iOS 14+ legacy and out of scope
  (R1 patch table tail; R2; pivot doc "old-style PRELINK kext, one step"). `profile.toml`
  `roots` (IOGPUFamily, IOMobileGraphicsFamily, apfs, AppleImage4, IOHIDFamily-2031, …) and
  `early_security_init` must be re-resolved against the 193 j96ap bundle IDs (R1 risk 4).
- **D7 driver ABI**: `build-arm-driver.py` compiles from the 10063 `IOPlatformExpert.cpo.json`
  recipe and audits deployment 0x110000 (iOS 17.0) — needs an iOS-12 mode (0xc0000) and a 4570
  recipe; 4570 IOKit is old-generation (no OSSharedPtr, IOPICEvents shape differs) and family
  headers are outside the tarball → hand-pinned ABI (`OriginalMobileFramebufferABI.h` pattern)
  (R1 risk 5; R4 1/3.5).
- **D8 interrupt consumer gap**: ArmCpu programs GICv2 but 4570 has no `IOInterruptController`
  base or consumer → new provider kext gates every IRQ driver (R2).
- **D9 console**: new polled 16550/GSBI `pe_serial_functions` table + `boot-console` ADT node
  (reg relative to arm-io base), or boot blind via framebuffer console + early-fault record (R2).

## 5. Boot prerequisites checklist

| # | Requirement | Kernel evidence | Format-1 piece | iOS 12 status |
|---|---|---|---|---|
| 1 | boot_args at entry, rev 1/2 | boot.h:44-58; arm_init.c:150 | DarwinBoot/shim | same |
| 2 | Synthesized ADT (arm-io, /cpus, chosen, per-device compatible/reg/interrupts) | pe_identify_machine.c:55-56,110-165,225-244; IODeviceTreeSupport.cpp:114-146 | ArmDTPlatform + make_adt.py | same; raw DTB hard NO |
| 3 | GIC bring-up + IOInterruptController provider | machine_routines.c:754-759 stub; no source | ArmCpu partial | blocker, new kext |
| 4 | lk2nd sets CNTFRQ_EL0 19.2 MHz; ADT timebase matches | machine_routines.c:1520-1759; pe_identify_machine.c:583-669 | ArmCpu arch timer | same, generic fallback |
| 5 | Polled console (16550 table + boot-console) | pe_serial.c:668-848,799 | uartdm patch | needs new table |
| 6 | KERNEL_INTEGRITY_WT board config | config/MASTER.arm64:82; board_config.h | XnuPrelink/ADT | differs from 17 CTRR/KTRR |
| 7 | Packed `_PrelinkLinkKASLROffsets`; no chained fixups | bootstrap.cpp:399,457; arm_vm_init.c:1336; rebase 0/0 | XnuPrelink | differs, D3-D5 |
| 8 | Root block: polled SDHCI eMMC publishing `/chosen boot-device`; HFS+ root | IOPlatformExpert.cpp:1155; IONVRAM.cpp:876; bootstrap.cpp:222,587 | QcomSdcc + VerifiedRoot | same shape, driver unwritten |
| 9 | Touch/GPU/WiFi/BT kexts authored with matching ADT compatible | PRELINK: no Synaptics/Adreno/SDIO-BCM/GIC/IOBluetooth | Adreno/AirNir/Qcom kits as structure ref | same shape, gated on #3 |

## 6. Evidence corrections against the working context

- `feat/y35a-driver-branches@4b31236` with native `sdhci.c`/`msm_sdmmc.cpp`: does not exist —
  `git cat-file -t 4b31236` fails in the parent and all 19 submodules, no matching remote ref
  (R1), `github.com/UniXNU/QcomSdcc` 404s (R4). `drivers/QcomSdcc/` holds only `SPEC.md`
  (R1 26630 bytes / R4 436 lines); no `components.toml` entry.
- `tools/prelink_dump.py`, `fixup_chain.py`, `macho_parse.py`: absent; `tools/` has only
  `uncomplzss.py` (R3, R4). All PRELINK parsing was ad-hoc inline.
- `~/unixnu-research/ios12-root/` (717 MB / 122-file closure): absent. The rootfs is
  `~/unixnu-research/dl/mnt-j96/` (ProductVersion 12.4.1, ProductBuildVersion 16G102 read from
  SystemVersion.plist); framework binaries there are dangling stubs, so userspace class
  evidence came from the 1269743616-byte `dyld_shared_cache_arm64` instead (R3, R4).
- `dl/kpp-payloads/kernelcache.reconstructed.release.fused`: absent (R4). The KPP run must be
  reproduced before any driver folds into a bootable image.
- `~/unixnu-research/lk2nd-y35a-codex`: not on the host; only `/work/lk2nd-y35a-codex` inside
  container `unixnu-y35a-native-20261103`, and `/work` is a named docker volume with its own
  copies of `UniXNU-y35a`, `xnu-4570`, `lk2nd-y35a-codex` — not a bind mount of
  `~/unixnu-research` (R4). Host↔volume sync state: unknown (verify).
- Kext census: pivot doc claims 1559 LC_KEXT commands / 502 entries; this-session parses found
  22 load commands, 502-503 raw `CFBundleIdentifier` strings, 184-193 plist dicts (R2 502/184,
  R3 193/184, R4 503 raw/193 unique with the tail cut by section padding, so 193 is a floor).
  A 22-command header cannot contain 1559 LC_KEXT commands. Publish "≈184 loadable kexts, 193
  unique bundle IDs" and re-derive with a committed tool.
- Mach-O filetype: R2/R4 read filetype 0x2 (MH_EXECUTE) while all reports call the image
  MH_KEXT_BUNDLE (0xc) — D2 starts with one authoritative header dump (verify).
- `TEST_READY.md`/`TEST_INFRA.md` assert 46/46 PASS, gpio915, Novatek NT35521, "Adreno 306
  software rendering fallback", xnu-10063 baseline — contradicted by board facts (touch is
  TLMM 12/13) and the absence of those drivers: untrusted prior-agent output (R4 3.5).
