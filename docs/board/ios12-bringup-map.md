# iOS 12 (XNU-4570) bring-up map for MSM8916 / vivo Y35A

Status: P2 design deliverable, 2026-11-04. Every row is cited to
`file:line` in `~/unixnu-research/xnu-4570` (tag `xnu-4570.51.1`, iOS 12.4.1)
or to a measured artifact under `docs/board/y35a-facts.md` /
`evidence/y35a-codex-20261103/` (repo root `/Users/lingion_k/unixnu-research/`).
First artifact pair: `patches/xnu4570/0001-y35a-board.patch` (board config +
machine block + `pexpert/pexpert/arm64/MSM8916.h`), generated deterministically
and verified to apply with `patch -p1` against the tag tree
(dry-run + apply + byte-exact content check, 2026-11-04).

---

## 1. PAGE-SIZE VERDICT (the headline)

**Verdict: the page-size blocker does not exist. iOS 12 arm64 is NOT
"16K-hardware-page". Apple ships A8 (Typhoon, iPad mini 4 — the exact device
whose 16G102 kernelcache we target) with 4K hardware translation granule plus
a 16K *software* page size chosen at runtime. MSM8916's Cortex-A53 can run
the identical regime with zero page-table changes, and in fact the 16K
granule is also architecturally available if we ever want it.**

Evidence chain (all in xnu-4570):

3. `osfmk/arm/proc_reg.h:126-140` — the `APPLETYPHOON` machine block.
   It defines `__ARM64_PMAP_SUBPAGE_L1__` and `__ARM_KERNEL_PROTECT__` but
   **not** `__ARM_16K_PG__`. Only Twister (`:153`) and Hurricane (`:169`)
   — A8X/A9 and later — set `__ARM_16K_PG__`. (iPad mini 4 is A8 Typhoon;
   iPad Pro 9.7 A9X is Hurricane.)
2. `osfmk/arm64/proc_reg.h:706-709` — `ARM_PGSHIFT` = 14 only
   `#ifdef __ARM_16K_PG__`, else **12**. For Typhoon: hardware page = 4K.
3. `osfmk/arm64/proc_reg.h:455-459,489-493` — `TCR_TG0_GRANULE_SIZE` /
   `TCR_TG1_GRANULE_SIZE` take the 4KB branch whenever `__ARM_16K_PG__` is
   undefined; `TCR_EL1_BOOT` is written in the kernel's own early path
   (`osfmk/arm64/locore.s:166-167`, `MAP_KERNEL`), so the granule is
   kernel-fixed, not bootloader-fixed.
4. `osfmk/mach/arm/vm_param.h:56,61-65` + `osfmk/arm64/arm_vm_init.c:177` —
   for a Typhoon-class build `PAGE_SHIFT` = `PAGE_SHIFT_CONST`, a
   **runtime variable** (`extern unsigned PAGE_SHIFT_CONST`).
5. `osfmk/arm/arm_init.c:175-193` — `arm_init()` sets it at boot:
   `memSize > 1GB => PAGE_SHIFT_CONST = PAGE_MAX_SHIFT (14)`; otherwise the
   hardware granule. Comment at `:188` spells it out: "kernel uses hardware
   page size (4KB for H6/H7, 16KB for H8+)". iPad mini 4 (2GB) therefore
   runs **4K hardware tables, 16K software pages** — a page-merge regime
   (one 16K software page = four consecutive 4K hardware PTEs), fully
   supported by `pmap.c` (`:480-481` pt_desc index shift 12 when
   PAGE_SHIFT_CONST != ARM_PGSHIFT; `:3900,4134,5141` per-hw-page loops).
   A 1GB arm64 phone (iPhone 5s/6, same 4570 kernel) runs
   `PAGE_SHIFT_CONST=12` (pure 4K software pages) on the same hardware
   tables — BOTH regimes are shipping-code paths selected solely by the
   memSize we pass; boot-arg overrides `radar_20804515=0` /
   `-use_hwpagesize` (`arm_init.c:194-201`) stay available for bring-up
   experiments.
6. Official cache segment layout proves 4K-granule-era toolchain alignment,
   not 16K hardware: `out/ipsw/16G102/kernelcache.decompressed` segments sit
   at `0x…4000/…78000/…98000` — file offsets are 4K multiples and only
   offset-by-16K from the 4K-aligned `ARM64_LINK_ADDR`
   `0xfffffff007004000` (hard-coded in our build recipe,
   `scripts/build-xnu-4903-kernel.py:24-25` quoting the 4903-era recipe for
   the j96ap layout). The 0x4000/0x8000 "16K-looking" steps are the linker
   recipe's section strides, not a granule statement.
7. Hardware truth: Cortex-A53 implements 4K **and** 16K **and** 64K stage-1
   granules (ARMv8.0 base; `TGran16`/`TGran4`/`TGran64` fields of
   `ID_AA64MMFR0_EL1`, bits 23:20 / 31:28 / 27:24, all 0 = implemented).
   Our probe readback `ID_AA64MMFR0_EL1=0x1122` is **QEMU-model provenance**
   (`evidence/y35a-codex-20261103/qemu-gic-security-working-20261104.json`,
   `qemu_cpu_model: cortex-a53`, tcg) — and decodes to *all granules
   implemented*. A real-device `ID_AA64MMFR0` readback has NOT been captured
   yet (the device readback JSON `readback-cpu-features-20261104.json` only
   carries MIDR/PFR0/ISAR0/CPACR). This matters only as hygiene: the
   architecture says A53 does 16K, the old doc claim did not, and see §7 U1.
8. Where the "MSM8916 = 4K pages only" claim came from: there is **no
   device measurement** behind it. It appears only as an unevidenced line in
   the research scaffold — `~/unixnu-research/SCAFFOLD-msm8916-draft.md:32`
   ("ARM64_PAGE_SHIFT=12（8916 只有 4K，无 16K/64K 变体——比新芯简单）"),
   i.e. a draft-time assertion later copied into task briefs. It is *mostly
   right* (4K is the correct granule to run) and *literally wrong* (16K and
   64K are implemented). Corrected here; the practical consequence is
   positive — even the worst case (if any consumer really needed 16K
   granule) is available on this hardware.

Consequences, stated per interop path:

- **Our own built kernel**: Typhoon shape (4K granule +
  `__ARM64_PMAP_SUBPAGE_L1__`, no `__ARM_16K_PG__`), memSize > 1GB =>
  identical 16K-software-page behavior as the official mini-4 kernel.
  `patches/xnu4570/0001-y35a-board.patch` encodes exactly this.
- **Official 16G102 kernelcache / prelinked kexts**: they are 4K-granule binaries
  too (the j96ap kernel is Typhoon), so the P3 "run the official cache"
  idea is NOT page-size-blocked. What still blocks P3 (deferred to its own
  plan): Image4/kernel-collision trust chain (`AppleImage4` validating the
  cache against sepOS-style root hashes our non-Apple SoC cannot reproduce)
  and the prelinked kexts' Apple-silicon drivers. Page size was never the
  blocker; we retire that fear. (Kext count note: `pivot-ios12.md` says
  "PRELINK kext 条目 502 个"; that is the total number of
  `CFBundleIdentifier` string occurrences in the `__PRELINK_INFO` plist —
  entries nest and duplicate. The authoritative counts from
  `out/ipsw/16G102/kernelcache.decompressed` @ file offset `0x1ad0000` are
  **184 executables** (`_PrelinkExecutableLoadAddr` keys) and **192 unique
  bundle IDs**, including `com.apple.driver.AppleInterruptController`,
  `com.apple.driver.AppleARMPlatform`, `com.apple.security.AppleImage4`,
  `com.apple.filesystems.hfs.kext`, `com.apple.kec.corecrypto`.)
- **iOS 12 userspace (launchd/dyld/cache/malloc)**: user pages are also
  16K *software* pages — `osfmk/arm/commpage/commpage.c:109-111`: under
  `#if __arm64__` the kernel writes
  `_COMM_PAGE_USER_PAGE_SHIFT_64 = SIXTEENK_PAGE_SHIFT` **unconditionally**
  (14 = 16K), independent of PAGE_SHIFT_CONST. Binaries are 16K-aligned;
  a 4K-hw kernel with PAGE_SHIFT_CONST=14 maps them exactly as Apple's A8
  does — the same regime, not a compatibility stretch. (If we ever forced
  PAGE_SHIFT_CONST=12 via a ≤1GB memSize, user VM still advertises 16K —
  the 1GB iPhone 5s/6 shipping case; but then `vm_param.h:94-100` PAGE_MAX_*
  keeps 16K maxima and mach-O/kext alignment logic stays honest. The clean
  statement is: **match Apple, pass memSize > 1GB, take the 14 branch,
  done.** Forcing pure-4K *everywhere* is NOT a supported 4570 mode, since
  the user shift is not a knob.)
- **machine_info / userland page-size query**: userland never bakes page
  size — `libsyscall/mach/mach_init.c:144-153` reads the commpage user-page
  shift (or falls back to `host_page_size`, `osfmk/kern/host.c:994`).
  Nothing in the 12.4.1 root needs recompiling for our page regime.

---

## 2. EARLY-BOOT SURFACE TABLE (4570 arm64, cold boot to kprintf)

Entry contract: EL1, MMU+cache off, x0 = `boot_args *`
(`osfmk/arm64/start.s:221-223 _start -> start_first_cpu`; header comment
`:399-402 "Cold boot init routine. Called from __start" ; x0 - Boot args`).
`start_first_cpu` reads only `BA_VIRT_BASE / BA_PHYS_BASE / BA_MEM_SIZE /
BA_TOP_OF_KERNEL_DATA` (`start.s:420-423`; the `__start` secondary path
repeats them at `:310-313`, offsets from
`osfmk/arm64/genassym.c:411-422`) and builds 4 V=P bootstrap pages
(`:456-470`), then `arm_init` (`osfmk/arm/arm_init.c:139`).

| # | Stage | 4570 code (file:line) | What it does on Typhoon/T7000 | What MSM8916 needs | Gap severity |
|---|-------|----------------------|-------------------------------|--------------------|--------------|
| E1 | `_start` / identity map | `osfmk/arm64/start.s:221,399-566` | 4 bootstrap 4K table pages from `topOfKernelData`; V=P then KVA jump; TCR programmed by `TCR_EL1_BOOT` (`osfmk/arm64/locore.s:166`, `proc_reg.h:591-602`) | None — identical 4K-granule math; entry must keep MMU-off handoff (lk2nd verified `SCTLR_EL1=0xc00800`) | none |
| E2 | Apple-HID early tuning | `start.s:716-724` (`APPLE_ARM64_ARCH_FAMILY`: HID4/EHID4 via `ARM64_READ_EP_SPR`), `start.s:725-765` (`APPLECYCLONE||APPLETYPHOON`: HID0/1/3/5/8 writes) | Typhoon path executes real `msr` of S3_0_c15_* | Our machine block defines **neither** gate: the blocks compile out (that is precisely why `APPLE_ARM64_ARCH_FAMILY` must stay undefined on Y35A — `arm64_common.h:8` scopes all `ARM64_REG_HID*` to it) | resolved by patch 0001 |
| E3 | `arm_init` page regime | `osfmk/arm/arm_init.c:139-211` | PE_init_platform; PAGE_SHIFT_CONST by memSize (:178) | pass `memSize=0x80000000` (2GB full) or any >1GB window so PAGE_SHIFT_CONST=14; currently our shim passes 256MB (:178 false branch => 12; legal but not what Apple runs — set it ≥1GB, see §5 boot-args row B2) | low, boot-arg-only |
| E4 | platform identify | `pexpert/arm/pe_identify_machine.c` `pe_identify_machine():44+`; `pe_arm_get_soc_base_phys():225-243` requires node `arm-io` with `device_type` (`gPESoCDeviceType`, 32-byte buffer `boot.h:63`) + `ranges[1]` = SoC phys base; clocks fall to DT path (`use_dt=1` at :~115, reads `/cpus/cpu*/timebase-frequency:121-131`) | T7000: `arm-io` device_type `t7000-io` selects `t7000_funcs` timer TBDs (:603-607) | our ADT already emits `arm-io device_type=qcom-msm8916` + ranges @ `scripts/y35a/make_adt.py:56-58` (device_type 13 chars + NUL = 14 < 32 OK); timebase-frequency 19.2MHz :42. Clock path OK as-is. | none |
| E5 | PIC map + timer TBD | `pe_arm_map_interrupt_controller():530-549` — `DTFindEntry("interrupt-controller","master")` then `@reg` as **SoC-relative** `soc_phys + reg[0]` (:544); `device_type=timer` node reg -> `gTimerBase` (:552-558); `pe_arm_init_timer():582-668` selects board TBD struct by `gPESoCDeviceType` string — **every Apple branch is `#if defined(ARM_BOARD_CLASS_*)`-guarded; no branch matches => `return 0` at :663 => interrupts never initialized for a non-Apple type** | t7000 branch (:603-607) sets `tbd_funcs=&t7000_funcs = {NULL,NULL,NULL}` (:271) — Typhoon uses **CPU-generic** arch timer (`CNTP_*` via `ml_set_decrementer`, `machine_routines.c:1515`), so null TBDs = "no special FIQ handler, no memory-mapped decrementer", and `ml_init_timebase(args, generic_funcs-or-t7000_funcs, 0, 0)` still runs (:665-666) | add an `ARM_BOARD_CLASS_MSM8916` branch with `{NULL,NULL,NULL}` and eoi 0 (same meaning as Typhoon: CPU-generic timer; virtual timer INTID 20 wired by our GIC kext, NOT FIQ because `fleh_fiq_generic` = `PANIC_UNIMPLEMENTED`, `locore.s:719-720`); also: `gPicBase` will only land if our ADT intc node's `interrupt-controller` **property value** is the string `master` — current ADT writes empty value (`make_adt.py:61`), fix in patch 0003 worklist; reg pairs must be relative to `ranges` child-bus base 0 (current ADT is relative to SOC_BASE `make_adt.py:58` — consistent, keep) | **blocker (DT + 6-line code)** |
| E6 | console / kprintf | `arm_init:313 printf_init; :322 PE_init_kprintf; :324 kprintf("kprintf initialized")` → `pexpert/arm/pe_kprintf.c:38 serial_init()`; `pexpert/arm/pe_serial.c:667-812`: `boot-console`/`uart0`/`uart1` node → `uart_base = ml_io_map(soc_base + reg[0])` (:761-776); under `S3CUART` the node's `compatible` must equal one of `uart,16550`/`uart-16550`/`uart,s5i3000`/`uart-1,samsung` else `return 0` (:791-805). T7000 gets S3CUART via `T7000.h:15` → `pexpert/arm/S3cUART.h:7` | Samsung-style polled UART; `ln2410_uart_init/baud/td` (:62-136) | **do not** include `S3cUART.h` on Y35A (no S3C2410 UART here). Port the proven UARTDM v1.4 driver: `patches/xnu/native-uartdm-console.patch` + `pexpert/pexpert/arm/uartdm.h` (register map verified on lk2nd 23.1; console `serial@78b0000`, 115200 8N1 proven since 2026-11-03, `y35a-facts.md:64-73`). 4570's `pe_serial.c` predates 4903's `serial_functions` table version — port is a rewrite into 4570's `{init,set_baud,tr,td,rr,rd}` struct shape (`pe_serial.c:137-138`), not a copy-paste | **blocker (port needed, solved design exists)** |
| E7 | MMU finalize | `arm_init:306 arm_vm_init()` → `osfmk/arm64/arm_vm_init.c:1072+`: gVirtBase/gPhysBase/gPhysSize from boot args (:1098-1103); `MEM_SIZE_MAX=0x100000000` cap (:208); static maps; `arm_vm_prot_finalize` `ml_static_mfree` of prelink gap (:891-907,992-996) | 4K-granule static tables + subpage-L1 kernel_pmap | works unchanged for Typhoon-shape config; Y35A RAM windows (facts.md:19-20) fit the 32-bit VA split — keep `physical_base` window ≤ its own span and virtBase/physBase offset ≡ mod 2MiB as the shim already enforces (`scripts/y35a/boot_layout.py:7-13`) | none |
| E8 | lowglobals / vectors | `arm_init:213+`, `locore.s:149-167`, `lowmem_vectors.c` | VBAR programmed; `APPLE_ARM64_ARCH_FAMILY`-only ordering ISB skips (:154-161, :1010-1016 `#if !defined(...)` adds standard `isb` for us) | none (non-Apple branch is the *safer* textbook one) | none |
| E9 | secondary CPUs | `cpu.c:790-795` (`MONITOR` → `monitor_call(MONITOR_SET_ENTRY)` = `smc 0x11` via EL3, `machine_routines_asm.s:1035-1049`; `#elif !defined(NO_MONITOR) #error`), `start_cpu_paddr` handoff `cpu.c:206,579`; spin-in contract = write `ResetHandlerData`, WFI/SEV | A7–A11 used an EL3 monitor to park/reset cores | **NO_MONITOR** (in `MSM8916.h`, patch 0001) skips the smc. MSM8916 secondary bring-up = hold cores in WFI, take them out via SGI/pending after writing VBAR+stacks; `ResetHandlerData` reset handler `start_cpu` is plain-EL1 code, safe. 17-era precedent: `patches/xnu/native-smp-secondary.patch` (MPIDR affinity decode for cross-cluster numbering — A53 single cluster Aff0 = our case with the existing `#else` branch `start.s` decode). | medium (design settled, code pending) |
| E10 | interrupts on | `arm_init` → IOKit platform setup; `ml_init_interrupt()` **empty stub** `osfmk/arm64/machine_routines.c:757`; `ml_install_interrupt_handler()` `:727` (stores per-CPU handler tuple `:740-746`; called from `IOCPUInterruptController::enableCPUInterrupt` `iokit/Kernel/IOCPU.cpp:827-834`); `ml_cause_interrupt()` empty stub `:1085` | The **kernel core performs no PIC programming at all**; Apple ships `AppleInterruptController.kext` (strings present in the official 16G102 cache) which acks its own device and calls `cpu_signal_handler` (`osfmk/arm/cpu_common.c:380-382`) for IPIs and per-source dispatch via `cdp->interrupt_handler` (`sleh.c:1308`, `sleh_irq` at `:1297`) | see §4 — we must own a GICv2 controller kext/builtin; without it nothing calls `ml_install_interrupt_handler` and IRQ vector dispatches garbage | **blocker** |

---

## 3. CONSOLE: EXACT INIT NEEDED (deliverable of row E6, as specification)

Polled TX-only init for `qcom,msm-uartdm-v1.4` at `0x078b0000` (retain
lk2nd's already-configured baud/clocks; never reset):

```
word wait:  SR(0xa4) & (TXEMT(8) | (ISR(0xb4) & TX_READY(0x80)))   // budget 100000 iters
NCF_TX(0x40) = count (1..4);  CR(0xa8) = 0x300 (reset TX_READY)
wait SR & TXRDY(4);  TF(0x100) = bytes packed little-endian per FIFO word
guard: if DMEN(0x3c) != 0 -> DMA owns the port: drop bytes, never hang
```

Source: the byte-proven helper `pexpert/pexpert/arm/uartdm.h`
(`uartdm_write_word`/`uartdm_wait`/`uartdm_drain`, lines 49-88 of the file
cached at `UniXNU-y35a/.cache/xnu-work/pexpert/pexpert/arm/uartdm.h`) and
the 4903-era hookup `patches/xnu/native-uartdm-console.patch` (probe via
`SecureDTFindEntry("boot-console")` + compatible whitelist + `ml_io_map`
into `uartdm_base`; `SERIAL_UARTDM=0x20` added to `protos.h`). For 4570 the
hookup is a mechanical rewrite into the old `pe_serial.c` function-table
shape (row E6). RX stays absent in v1 (the 4903 driver deliberately does
TX-only; DMRX lifecycle not needed for logs).

---

## 4. INTERRUPTS / TIMERS

### 4.1 Structural finding (headline #2)

XNU-4570 base **has no GIC and no AIC implementation in the kernel**. The
whole "AIC" layer of the 32-bit era collapsed to two headers only
(`pexpert/pexpert/arm64/AIC.h:11-23` = `aic_read32/_write32` helpers over
`pic_base`; `:27-30` timebase regs). `AIC_init`/`AIC_lock` do not exist
anywhere in the drop (whole-tree grep, 2026-11-04: only `pexpert/arm/
pe_identify_machine.c:584-593` local `pic_base` copies of `gPicBase`). The
kernel's *demand surface* on the interrupt controller is exactly:

| Kernel side (4570, file:line) | Contract |
|---|---|
| `sleh_irq` → `cdp->interrupt_handler(...)` (`osfmk/arm64/sleh.c:1297,1308`, `locore.s:706-709 fleh_irq`) | IRQ exception arrives; the *controller* must have already acked it; per-CPU handler tuple installed by `ml_install_interrupt_handler` (`machine_routines.c:727,740-746`) is then run with (target, refCon, nub, source). On Apple silicon this tuple = `IOCPUInterruptController::handleInterrupt` (`IOCPU.cpp:827-834,924-936`), i.e. the vector source index IS the CPU-tuple source and real per-source dispatch happens in AppleInterruptController.kext |
| `cpu_signal_internal` → `PE_cpu_signal/deferred/cancel` (`osfmk/arm/cpu_common.c:340-374`) → `IOCPU::signalCPU` (`IOCPU.cpp:368-390`) | IPI send surface; base `IOCPU` returns unsupported — an AppleARMIODevice subclass of IOCPU (their kext layer) implements it with AIC SW-rendezvous. **On GICv2: implement as SGI write** (see below) |
| `cpu_signal_handler()` (`cpu_common.c:380`) | IPI receive: the controller calls this after acking the IPI and clearing its pending state |
| `ml_init_interrupt()` (arm64 `machine_routines.c:757`) — empty; `ml_cpu_init_interrupt()` likewise | nothing else |
| `rtclock` / decrementer | `ml_set_decrementer():1503-1518` uses `cpu_set_decrementer_func` if installed else **`CNTP_TVAL_EL0` directly**; `ml_get_hwclock():1526` `CNTPCT_EL0`; `ml_get_timer_pending():1559-1566` reads `CNTP_CTL_EL0` **hard-coded physical**; `rtclock_timebase_func/addr` registered via `ml_init_timebase` (E5) |
| timer FIQ vector | `fleh_fiq_generic` = `PANIC_UNIMPLEMENTED` (`locore.s:717-720`); `sleh_fiq():1340+` expects `ml_get_timer_pending()`; **we must NOT route the timer to FIQ**; route virtual timer INTID 20 as normal IRQ |

### 4.2 GICv2 Y35A design (what patch 0004 must implement)

Two viable homes, in preference order: (a) built-in IOKit driver in our own
kernelcache (`iokit` tree compiles in-tree; simpler trust story than a
vendor kext on day 1); (b) a kext later if we re-introduce prelinking. The
driver must cover the demand surface exactly:

1. **Init** (boot CPU, before enabling IRQs): GICD CTLR enable (both groups,
   respecting GICD_TYPER=0x468 SecurityExtn ⇒ keep SPI targets/groups as
   firmware set; do NOT re-program group sec/non-sec split blindly),
   GICC CTLR enable + priority-binary 0. Bases from `gPicBase`/
   `gTimerBase` mapping (E5) — but note `y35a-facts.md:17` gives the real
   4-window QGIC map: dist `0x0b000000`, **redistributor-style second
   window `0x0b001000`, fourth `0x0b004000`** only exist as address space;
   GICv2 CPU interface is `0x0b002000`. The 17-era `ArmCpu/GicV2.h`
   (repo `drivers/ArmCpu/GicV2.h`, LK2nd qgic-derived, `dist`+`cpu` banks
   with SecurityExtn handling at `hasSecurityExtensions()` and bootTarget
   mask walk :57-63) is the proven logic to reuse.
2. **Ack/EOI in the IRQ entry wrapper**: our driver installs the CPU tuple
   (via `ml_install_interrupt_handler` from its `start()`); inside its
   handler: `ICC_IAR1` read → INTID; INTID 0-15 SGI ⇒ clear pending,
   `cpu_signal_handler()`; INTID 19/20 timer ⇒ `rtclock_intr` path via
   `cpu_data` timer dispatch; INTID ≥32 SPI ⇒ dispatch registered vector
   list for that source, then `ICC_EOIR1` write. (On Apple silicon the
   equivalent ack happens inside their kext before the tuple call; the
   kernel never touches ICC regs itself — so the *entire* ICC surface is
   ours to implement, and `eoi_addr/eoi_value` from E5 may remain 0 for us.)
3. **IPI send**: `signalCPU(target)` ⇒ SGI with target list from MPIDR
   Aff0 (4×A53 single cluster): `GICD_SGIR = (1<<target.Aff0)<<24 |
   AutoTarget=0 | SGIIntId` (use INTID 0 for scheduler IPI, 1 reserved).
   Deferred/cancel map to pending-flag emulation like Apple's software-
   rendezvous, or simply forward-not-defer on v1.
4. **Timer**: CPU-generic, exactly the Typhoon `t7000_funcs={NULL,NULL,NULL}`
   shape (E5): no `cpu_set_decrementer_func` override ⇒ `ml_set_decrementer`
   writes `CNTP_TVAL_EL0` (physical counter/timer). Two honest options, to
   settle in the first device boot (§8 F3): (i) run **physical** timer with
   CNTKCTL/CNTP as 4570 does by default (`_enable_virtual_timer():1750-1757`
   only *enables* CNV_CTL as far as `fiq_context_init` goes — on a
   non-Apple board we skip FIQ entirely and program the physical timer EOI
   via ICC); (ii) switch the three `ml_*` timer helpers to `CNV_*` +
   INTID 20 (facts.md measured PPI 4 = INTID 20 works under stock
   Android). Because MSM8916 runs without EL2, CNV_* is accessible at EL1;
   (ii) matches what we already verified on-device. Documented as a 3-line
   patch (0005) with (i) as fallback if CNV_CTL traps.
5. **Boot CPU IRQ enable**: `ml_init_arm_debug_interface` etc. are gated by
   Apple PMGR regs — keep the `NO_MONITOR`+non-family path; nothing to do.

### 4.3 What the concurrent 4570 build agent must know (interrupt-related)

- Building `MACHINE_CONFIGS=T7000` (or T7001) vanilla: **no change**;
  the E5 selector keeps failing-to-match for `gPESoCDeviceType` only on
  non-Apple device_type strings, so vanilla behavior is untouched by our
  patch (all hunks are either new machine names or `#elif` arms).
- For the Y35A config build, apply `patches/xnu4570/0001-y35a-board.patch`
  and add the E5 `ARM_BOARD_CLASS_MSM8916` branch (6 lines, patch 0002).

---

## 5. PEXPERT / ADT / BOOT-ARGS DIFF

### 5.1 4570 `boot_args` ABI (pexpert/pexpert/arm64/boot.h:42-61)

`Revision=1|2, Version=1|2`; fields in order: virtBase, physBase, memSize,
topOfKernelData, Video{6×uint32}, machineType(uint32), deviceTreeP,
deviceTreeLength(uint32), CommandLine[256], bootFlags(u64, rev-2),
memSizeActual(u64). **There is no Revision-3 padding**: at offsets
`8/16/24/32/40…` the u64s sit un-padded; total 0x180-ish, not 0x480.
No code in 4570 branches on `Revision`/`Version` (grep `pexpert osfmk
bsd`: only the #defines). `start.s` consumes BA_* offsets from
`genassym.c:411-422`; `arm_init.c:150` struct-copies args.

### 5.2 Our current shim mismatch (must fix before first 4570 boot)

`scripts/y35a/boot_layout.py:make_boot_args` packs the **Darwin-23 (iOS 17)
layout** (`Revision=2,Version=2` at `:23`, u32 `Padding` at `:8` shifting all
u64s by 4, `CommandLine[1024]`, size 0x480 — matching
`drivers/DarwinBoot/DarwinBootPkg/Driver/BootArgs.h` STATIC_ASSERTs).
Feeding that to 4570 means virtBase lands at offset 12 not 8, memSize wrong,
Video overlap into deviceTreeP — every field misread.
**Patch 0002 (tooling, not kernel):** emit a true 4570 struct:
`Revision=2, Version=2` (bootFlags valid), then the 4570 field order without
the `Padding`; `CommandLine[256]`; `memSizeActual=memSize`
(`machine_routines_common.c:597-602` prefers it when > memSize);
`memSize ≥ 0x40000001` for the 16K software-page branch (§1.5);
`machineType=0` (no consumer in 4570); `Video` = the 720×1280 24bpp splash
(u32 fields fit) so `arm_vm_init` maps splash FB (`arm_vm_init.c:515`
`round_page(h*rowBytes)` sizing). Consumer inventory of the fields: E1 +
`arm_init.c:178,233` + `arm_vm_init.c:1100-1102,370,644-650` +
`pe_init.c:283-341` + `model_dep.c` boot-info paths.

**4903 终审(2026-11-07,3f4bcd3,取代本节 4570 假设对现内核的适用性):**
4903 的 boot_args 与 4570 不同——`Revision/Version` 之后有 4 字节
`Padding`(osfmk genassym.c 消费面证实 u64 全在 8 的倍数),即前缀
`virtBase@8 … deviceTreeLength@0x68` 与 Darwin-23 布局逐字节一致,
"every field misread" 只适用于 4570,对现 boot 的 4903 不成立;现
`make_boot_args` 的字段位置全部正确,boot3.img 无需重打。真正的
4903 差异只有两处尾场: `CommandLine` 是 `BOOT_LINE_LENGTH=256`
(非 1024),`bootFlags@0x170`/`memSizeActual@0x178`(非 0x470/0x478)。
`memSizeActual` 唯一消费点是 `machine_routines_common.c:658
ml_get_booter_memory_size`(读 0 走舍入回退,对 memSize=0x10000000
算得 0,良性);`bootFlags` 4903 无消费(读 0 = 非 DarkBoot,即意图)。
打包器命令行上界已按 256 锁死(红绿三例入 tests/test_native_pack.py
BootArgsEraContractTest);0x480 缓冲保留——垫片整块刷写且垫片从不
跳转取用尾部字段。重打包必要性已实测证伪:从 boot3.img 原位抽出
0x480 boot-args 域(anchor=virtBase 四字串定位,tree_len=10988、
cmdline 35B),以真实输入过当前 256-界打包器重算,逐字节全等
(IDENTICAL True,2026-11-07 本机 python3.11 实跑)——在产镜像与新
闸门完全一致,零重打。

### 5.3 DT contract inventory (what our `board.adt` must contain, exact)

| Node / query | Kernel site | Required shape | Current ADT state (`make_adt.py`) |
|---|---|---|---|
| `/cpus/cpu@N` with `state=running` (boot cpu), `reg`, `cpu-id` optional, `timebase-frequency` | `machine_routines.c ml_parse_cpu_topology():783-830` (asserts `/cpus` exists) | one running + (for SMP) `enabled`/`boot`/`offline` states; 4570 reads `reg` as u32 phys id; **no `interrupt-handle` needed** (that string is not in 4570 — corrected vs older session belief) | cpu0 running @:39-43; add cpu1-3 for SMP |
| `arm-io` node: `device_type` (<32 bytes), `ranges` (u64 triples; `ranges[1]` = SoC phys base) | `pe_identify_machine.c:225-243` | device_type `qcom-msm8916` (any unknown string ⇒ `use_dt` clock path, fine) | :56-58 OK |
| child of arm-io with property `interrupt-controller` = **"master"** (value-matched), `reg` = SoC-relative (child-bus) `addr,size` pair | `pe_identify_machine.c:541-549` (`soc_phys + *reg_prop`) | gPicBase = dist bank | **:61 value is empty** → DTFindEntry fails → `pe_arm_init_interrupts` returns 0. FIX: property value `master\0` + confirm size math |
| `device_type=timer` node, `reg` SoC-relative | :552-558 | gTimerBase (CPU-generic board ⇒ maps a harmless span; give it the qgic second window `0x0b001000-SOC_BASE,0x1000`) | **absent** → second failure return. FIX: add node |
| console node: `boot-console` property (value ignored — NULL match), `reg` SoC-relative pair, `compatible` accepted by UARTDM whitelist | `pe_serial.c:761-776` + uartdm probe | uart_base absolute after `ml_io_map` | :64-65 uart0 `qcom,msm-uartdm-v1.4` + reg `0x000b0000,0x200` (relative) — the `name=uart0` fallback path already matches today (DTFindEntry("name","uart0") keys on the node *name* property), so no `boot-console` property strictly needed for uartdm probe |
| `/chosen`: `random-seed` (64B; consumer `PE_get_random_seed` reads exactly this property name on `/chosen` — `pexpert/gen/pe_gen.c:119-141`), `dram-base`, `dram-size`, `embedded-panic-log-size`, `memory-map`, `osenvironment` | `pe_init.c:63-100 check_for_panic_log (pram node reg + /chosen embedded-panic-log-size -> ml_io_map_wcomb gPanicBase :91)`; `arm_vm_init` ramdisk lookup via `/chosen/memory-map RAMDisk` | property names verified 4570-era as listed | :33-37 present |
| pram / panic region | node lookup `DTLookupEntry(0, "pram")` then `@reg` (pe_init.c:73-77) | gPanicBase wcomb map; KNUF readback loop already proven | :49-50 present (reg pair 0x859e0000/0x10000) |
| `compatible=arm,armv8-timer` + interrupts triples | informational for us (kernel has no DT timer-interrupt consumer in 4570 base; our GIC kext reads INTID 20 from its own constants) | keep | :46-47 present |
| cpu-debug-interface (`device_type`) | `pe_arm_init_debug():500-524` — only warns when absent | optional | absent = warning only, OK |

### 5.4 Platform selection knobs (no hidden machine switch)

- Chosen platform = compile-time `-DARM64_BOARD_CONFIG_<M>` (there is no
  runtime machineType dispatch in 4570; `board_config.h` is included once at
  `osfmk/arm64/proc_reg.h:79` / `osfmk/arm/proc_reg.h:78-82`).
- `PE_init_platform` (`pe_init.c:283`) never inspects `machineType`; it DTInits
  and calls E4/E5.
- `kPEPlatform` / machine-flags runtime = absent (that is a 32-bit-era
  concept).
- `ARM_BOARD_CLASS_MSM8916` must be defined (patch 0001) because E5's
  selector ladder keys on ARM_BOARD_CLASS_*, not the SoC name.

---

## 6. CONTRACT FOR THE CONCURRENT xnu-4570 BUILD AGENT

1. Vanilla T7000/T7001 builds are **unaffected** by anything in this branch:
   our work lands as new `#elif` arms + a new board file + a new machine
   name. Do not reflow `proc_reg.h` machine blocks.
2. If the build system needs `SUPPORTED_ARM64_MACHINE_CONFIGS`/
   `MACHINE_FLAGS_ARM64_*` (the 4570 tag's `makedefs/MakeInc.def` only
   declares X86_64/X86_64H — the same wall `scripts/build-xnu-4903-kernel.py
   :17-25` documents for ARM64), the Y35A build follows the same
   container-side makedefs extension convention **plus**
   `-DARM64_BOARD_CONFIG_MSM8916` on the compile line (patch 0001 header
   records this). For vanilla T7000, keep injecting
   `-DARM64_BOARD_CONFIG_T7000` exactly as `build-xnu-4903-kernel.py:221`
   does today.
3. Kernel link recipe stays `0xfffffff007004000` /
   `__PRELINK_TEXT 0xfffffff004004000` (4903-script rationale lines 24-25) —
   matches j96ap segment layout; our 4K-granule config keeps that legal.
4. The Y35A config build additionally requires `CONFIG_REQUIRES_U32_MUNGING=1`
   (arm64/4570 `bsd_arm64.c:109 #error` otherwise; 32-on-64 compat is kept).
5. Do NOT define `__ARM_16K_PG__` for MSM8916; do NOT define
   `APPLE_ARM64_ARCH_FAMILY` for MSM8916; do NOT add `MAX_CPUS` overrides
   without rechecking `cpu_data_internal.h:63-69` (MAX_CPUS=CPU_COUNT when
   `__ARM_SMP__` — our CPU_COUNT=4 suffices).
6. Handoff contract for the built kernel image: entry `_start` with x0 =
   4570-shaped `boot_args` (§5.2 fixed), MMU/caches off at EL1, ADT per §5.3.

---

## 7. RISK REGISTER (each with the cheap experiment that settles it)

| ID | Risk | Evidence today | Kill-shot experiment | Cost |
|----|------|---------------|----------------------|------|
| R1 | A53 4K-granule path silently differs from Apple's Typhoon elsewhere (caches_asm non-Apple `dc csw` loops + PoU ops never exercised on ARMv8.0-A53 in 4570) | `caches_asm.s:133 #error CleanPoU_Dcache` is a compile-time admission the path was never finished | Container compile: `MACHINE_CONFIGS=MSM8916` build with patch 0001+0002 (cache ops patch) — first full compile of this config is itself the experiment | 1 build cycle |
| R2 | Official-kernelcache prelink path (P3) still blocked by Image4/trust, not pages | AppleImage4 present in cache strings; no sepOS on Y35A | keep P3 parked; run *our own* kernel + our own minimal kext set first (the pivot doc already orders it this way) | deferred, zero now |
| R3 | Timer physical-vs-virtual (CNTP vs CNV) at EL1 w/o EL2: CNTPCT readable, CNP_TVAL writable, but `CNTKCTL`/`CNTHCTL` nonsecure-trap policies unknown on this hyp (hyp stock partition exists) | facts.md measured CNTFRQ + INTID20 proven under stock; 4570 `ml_get_timer_pending` hard-codes CNTP_CTL `:1559-1566`; lk2nd handoff CurrentEL=EL1 | first-boot probe prints CNTP_CTL/CNV_CTL read/write round-trip + timer interrupt firing via GIC (arm F3) — one boot cycle decides; if CNV traps, patch 0005 three-liner flips to physical | 1 boot |
| R4 | `PAGE_SHIFT_CONST=14` + 4K-hw page-merge path in pmap has zero field history on non-Apple silicon (Apple ran it only on Typhoon/Cyclone); commpage will advertise CPUFAMILY_UNKNOWN (MIDR implementor 0x41 ARM → `osfmk/arm/cpuid.c:126-183` default arms) — acceptable, userland feature checks consult it, none required for boot | `pmap.c:480-481,3900,4134,5141` branches are compiled-in for exactly our shape | run existing pmap unit tests in linux_env container with MSM8916 config + boot-to-mount with `vm_page_size` kprintf assert `== 16384` | build+boot cycle |
| R5 | Our shim caps the *owned window* at 0x10000000 (`boot_layout.py:14-15 OWNED_SIZE`), making arm_init take the **12** branch (§1 item 5) — legal Apple code (iPhone 5s/6) but not the Apple-mini4 parity regime | boot_layout.py:13-15; facts.md:19-20 RAM windows | raise the owned window: `0xa0000000-0xffffefff` (facts.md) is ~1.5GB contiguous — set physical_base 0xa0000000, memSize 0x60000000 (1.5GB, clears the >1GB gate), validate against `RAM_RANGES` in boot_layout (its tuple end 0xfffff000 already covers it); virtBase-physBase congruence mod 2MiB already enforced | packer + ADT edit, 1 boot |
| R6 | QGIC address window ambiguity in facts.md: it lists only "distributor 0x0b000000, cpu-iface 0x0b002000" (line 17) while the QCDT/mainline dtsi expose four windows 0x0b000000/0x0b001000/0x0b002000/0x0b004000; GICv2 has no redistributors — 0x0b001000/0x0b004000 are the qgic aliased/secondary regions (per LK2nd qgic.c lineage cited in our `drivers/ArmCpu/GicV2.h:51-53`) | facts.md:17; mainline `msm8916.dtsi` intc reg-list (SCAFFOLD doc row "中断控制器", cached /tmp/msm8916.dtsi:2503-2510); GICD_TYPER=0x468 readback already proven 2026-11-04 (`device-gic-security-20261104`) | treat dist `0x0b000000/0x1000` + cpu-if `0x0b002000/0x2000` as canonical (facts.md already does); no experiment needed beyond F2 reaching timer ticks | resolved (documentation only) |
| R7 | No real-device `ID_AA64MMFR0` readback yet (only QEMU). Caution found during this audit: a transient uncommitted edit to `y35a-facts.md` claimed "device readback 0x222" superseding the QEMU `0x1122`; the value 0x222 matches no field in any device evidence file — the closest is `PFR0: 0x2222` in `readback-cpu-features-20261104.json` (which stores MIDR/ISAR0/PFR0/CPACR only, no MMFR0 at all). The edit was reverted and no `readback-device-probe-20261105.json` exists on disk. Do not let this mislabel propagate. | facts.md:15 provenance = `qemu-gic-security-working-20261104.json` (qemu_cpu_model cortex-a53) | add MRS ID_AA64MMFR0 to the existing panic/pram readback probe (1 asm line in entry.S probe, get_staged decodes) — closes the hygiene gap | 1 boot |
| R8 | `pe_arm_init_timer` board-branch (E5) — without it nothing ever enables timer TBDs; our `{NULL,NULL,NULL}` variant untested on a board without eoi | :663 `return 0` path | covered by arm F2 below | — |

---

## 8. DECISION SECTION

**D1 Page regime (decided, §1): Typhoon-shape — 4K hardware granule,
`__ARM64_PMAP_SUBPAGE_L1__` on, `__ARM_16K_PG__` off, runtime 16K software
pages via memSize>1GB. Consequence: userspace kext prelink is NOT
page-size-blocked; P3's real blockers remain trust + drivers.**

**D2 Interop path (decided per pivot doc): boot our OWN 4570-built kernel
first; prelink only our own built-in drivers; keep the official-cache
experiment (P3) sequenced after first-login milestones.**

**D3 Interrupt controller home (decided): GICv2 driver as in-tree IOKit
service inside the kernelcache (built-in, name-compatible with Apple's
IOPlatformInterruptController registration path, `IOCPU.cpp:789`
`registerInterruptController(gPlatformInterruptControllerName)`), not a
separate vendor kext in v1.**

**D4 Timer delivery (decided): normal IRQ (INTID 20 virtual preferred, 19
physical fallback), never FIQ (`fleh_fiq_generic` is panic-unimplemented).**

First-experiment ladder (all RAM-boot via `fastboot -s efff9d92 boot`, never
touching storage):

- **F1 (cheapest, kills R1 half)**: linux_env container compile of vanilla
  T7000 vs MSM8916 config (patch 0001 + cache-ops patch 0002). Any compile
  error = ground truth that the non-Apple branches were never taken since
  Apple internal builds stopped shipping them; fix list becomes exact.
- **F2**: RAM-boot the MSM8916-config kernel with the UARTDM console patch +
  E5 board branch: milestone = `kprintf("kprintf initialized")` (arm_init
  :321) then boot-args echo, then panic-region readback if it dies.
- **F3**: timer decision: after F2 reaches scheduler, `rtclock` tick count
  grows ⇒ timer chain proven; CNTP-vs-CNV already decided by then (print
  CTL round-trip in init).
- **F4**: secondary spin-in (SGI to core 1, `cpu_signal_handler` counter in
  pram) — closes E9/§4.2-3.
- **F5**: RAMDisk root + `launchd` exec (milestone = first userland page
  fault logged with correct 16K software-page `vm_page_size`) — settles R4
  end-to-end and §1's userspace claim on real silicon.

---

## 9. OPEN UNKNOWNS (honest list)

- U1: exact `machineType` semantics in 4570 (no consumer found — likely
  dead field; keep 0).
- ~~U2~~ RESOLVED during final citation sweep: 4570 reads `/chosen`
  property name `random-seed` verbatim (`pexpert/gen/pe_gen.c:126`), which
  our ADT already emits (`make_adt.py:33`) — no rename needed.
- U3: `IOPlatformExpert` flavor for a non-Apple platform (4570 `GenericARM
  .kext` equivalent absent; our platform provider plan not yet written).
- U4: whether `__ARM64_PMAP_SUBPAGE_L1__` + no-`KERNEL_PROTECT` combo ever
  compiled in Apple history (BCM2837 in the 4903 tree did with explicit
  overrides) — if link-time asserts fire, the 4903 BCM files are the
  reference answer.
- U5: real-device ID_AA64MMFR0 (R7).

## verify (commands actually run, this session)

```
grep -rn PAGE_SHIFT osfmk/mach/arm/vm_param.h osfmk/arm64/arm_vm_init.c osfmk/arm/arm_init.c  (full-tree PAGE_SHIFT_CONST / __ARM_16K_PG__ inventory)
grep -n "16K_PG\|ARM_PGSHIFT\|TCR_TG" osfmk/arm64/proc_reg.h osfmk/arm/proc_reg.h
sed -n on osfmk/arm/arm_init.c:120-229 / pexpert/arm/pe_serial.c:43-812 / pexpert/arm/pe_identify_machine.c:225-668 / osfmk/arm64/sleh.c(sleh_irq/sleh_fiq) / osfmk/arm64/machine_routines.c:740-830,900-1010,1500-1570,1735-1795 / osfmk/arm/cpu_common.c:330-395 / iokit/Kernel/IOCPU.cpp:368-390,810-845,924-936 / osfmk/arm64/{start.s,locore.s} boot paths / osfmk/vm/vm_fourk_pager.c head
python3 decode of ID_AA64MMFR0 0x1122 field polarities
mach-O segment dump of out/ipsw/16G102/kernelcache.decompressed (all vm/offset pairs)
grep AppleInterruptController/AppleARMPlatform strings in official cache
patch -p1 --dry-run && patch -p1 on /tmp skeleton + byte-exact content compare (patches/xnu4570/0001-y35a-board.patch, generated by /tmp/gen_y35a_patch.py)
```

## 10. DEVICE-TRANSPORT OBSERVATIONS (2026-11-06, measurements only)

Context: the P0-4 V11 transport line. The working tree was checked out at the
421-line committed version of this map; a claimed "V11 段" from an earlier
session was NOT on disk (git log: file committed once, 7a33156). This section
records what was directly measured today, superseding any narrative claim.

**勘误(2026-11-06 07:0x;两段,第二段为对本勘误自身的更正,零设备操作)。**
初稿"40MB 闸未找到、真实闸不明"的说法有错,已定位到 lk2nd 侧;原生
aboot 侧的结论降级为假说:

1. **lk2nd 树里根本没有 40MB 闸。** 全量 grep /work 容器内
   lk2nd-y35a-codex:`flash_from_boot` 零命中,`MAX_SIZE` 零命中
   (只有 SMEM/AVB/OpenSSL 无关同名)。lk2nd 真实闸:
   `cmd_download` 的 `len > download_max`,
   `download_max = target_get_max_flash_size()`(target/msm8916/meminfo.c,
   256MB),SCRATCH_ADDR 0x90000000 恰铺满 1GB 尾段。
   `cmd_boot` 的头一致性闸 image_actual>sz boot2 本应通过(初稿算术没错,
   闸不对)。→ "boot 通路闸在 lk2nd"是错的;闸不在 boot 命令,在下载握手。
2. 假说(最高置信,非本地实证):秒拒的闸在 vivo 原生 aboot 的
   `#define MAX_SIZE (0x2800000)` 40MB。证据:
   (a) boot2 传输阶段必然经过某 fastboot 的 download 闸;
   (b) 驻留 lk2nd 树不存在 40MB 级闸(上条),其唯一 40MB 级以下
       失败路径是头校验,而该闸算术通过;
   (c) 时序:boot1 flash 成功后 lk2nd 驻留即被覆盖,`fastboot reboot`
       后 Android 健康走原生链路——此后的 fastboot 大概率是原生 aboot;
   (d) 宿主机 ~/HarmonyOS-6 fork 的老 CAF LK 确有
       `MAX_SIZE=(0x2800000)`,fail 串 "data too large",与 0.003s
       零传输行为模型吻合。
   **本条初稿写成"时序铁证+已定位"系过度断言,已更正。** 本地无法
   实证的部分:对 stock-aboot.img(ELF32-ARM, CAF 血缘字符串
   data too large/size too large/max-download-size/invalid bootimage
   header 全在场)做了字面池字节扫描,0x2800000 唯一命中 0x71ac6 经
   上下文判读为小整数表误报,常数可能在压缩载荷或取值方式不同;
   本机无 AArch32 反汇编器可追寄存器。判别实验(设备侧,待下令):
   进 fastboot `getvar max-download-size`——256MB=还在 lk2nd(40MB
   说作废,须回查),40MB 级=假说成立且闸重定位到 download 阶段。
3. 推论(P0-4 传输线,重要):**boot1 刷入即覆盖 lk2nd 驻留**;想再用
   lk2nd 的 256MB RAM 下载缓冲(装得下 boot2 全尺寸),必须先恢复
   lk2nd 到其驻留分区 —— 设备侧动作,待用户下令。原生 aboot 路线若
   假说成立则受 40MB 限制:容器必须 ≤40MB。初稿"GPT RAMBoot 30MB
   方案当时实测通过"无本地证据可核(主机零容器产物,见下条 4),
   不得作为互相印证,一并作废待核。
4. 待核项(不影响上面结论):
   - recon-20261105 所称"已验证 v5 GPT RAMBoot 容器"系 Codex 会话
     叙事,主机无容器文件/脚本/日志佐证;find 全盘 `*ramboot*` 仅
     pmos wiki 与 lk2nd 上游文档命中。
   - boot1 刷入前 lk2nd 所在分区(boot_a/boot_b/recovery)。
   - facts.md 设备侧 harness 称 `fastboot boot <image>` "已证"——
     与 boot2 实测秒拒冲突,同属待核。

Hard facts, in order:
1. 06:26:52 `fastboot flash boot out/y35a/ios12-boot1.img` (11,435,648 B,
   sha256 0c251933) → OKAY; `fastboot reboot` → the phone came back into
   Android 11 (PD1502; adb getprop verified 11:56). The boot partition was
   NOT ours anymore at that moment (boot1 was written into it) yet Android
   still booted — vivo aboot's fallback/recovery path is intact but its
   exact mechanism is unexamined.
2. 06:27:25 `fastboot getvar max-download-size` (fastboot session BEFORE the
   flash): `0x10000000` (256MB). So the lk2nd download buffer is 256MB, not
   40MB; the recon doc's "MAX_SIZE 0x2800000" was NOT found in the local
   lk2nd source either (grep across app/aboot: no MAX_SIZE constant).
3. `fastboot boot ios12-boot2.img` (52,651,008 B): FAILED in 0.003s — zero
   bytes transferred. The boot-command path refuses the container
   immediately; the ceiling of THAT path is unidentified (candidate:
   the `flash_from_boot` RAM window, source not located).
4. `fastboot flash userdata <boot2>`: FAILED (no userdata slot in the
   partition table — lk2nd only exposes boot/recovery/vendor_boot/misc).
5. Fastboot-mode availability AFTER the boot1 flash is UNVERIFIED — user
   standing order keeps the phone in Android; do not `adb reboot bootloader`
   without an explicit order.

Transport implications (open, do not act on the device without a user order):
- The flash-boot route carries no ~40MB cap in principle (stock boot.img on
  this phone is 64MB and the partition holds it), BUT aboot's own loader
  places header kernel_addr/ramdisk_addr directly — our boot2 header would
  need a load map that dodges the measured splash buffer at 0x83200000 and
  the 0x85700000..0x85900000 reserved window, and aboot (vivo LK, not lk2nd)
  executes the entry shim, behavior unmeasured.
- The `boot` route stays blocked until its real cap and cap-site are found
  in source; boot2's minimum honest size is 13.6MB fixed (kernel+ADT+TC) +
  12.4MB gzip-HFS+ = ~26MB only after the 40MB-diet analysis, which today's
  numbers put inside reach of a 40MB cap but NOT of whatever produced the
  immediate 0.003s refusal of 52.6MB.
- Referenced-but-absent artifact: the "已验证 v5 GPT RAMBoot 容器" from
  recon-20261105 §路径级发现 exists nowhere on disk (searched evidence/,
  out/, dl/). Either the user holds it, or the claim refers to the
  14,841,856-byte aarch64-register-probe.img era of the same transport —
  must confirm before rebuilding a second GPT stack from scratch.

## V12 传输层复测(2026-11-06 07:5x,守护心跳;全程只读 getvar,零刷写)

盘面重建时发现设备处于 fastboot(非本会话送入;未 reboot,保持现状)。
三条只读取证,直接推翻 §10 勘误的"原生 aboot 假说":

1. `getvar max-download-size` → 0x10000000(256MB)。
2. `getvar product` → **lk2nd-msm8916**,`variant` MTP eMMC。
3. `oem y35a layout` → "(bootloader) Y35A XNU layout v1:
   ramdisk=0x85700000 tags=0x85800000 OKAY" —— 这是我们自己 fork 的
   lk2nd 补丁在应答。boot1 刷入并没有覆盖 lk2nd 驻留(驻留分区
   待核问题 #4 就此关闭:驻留还在,boot1 写的是别处或 aboot 走了
   其它回退路径)。

结论(实测,可直接用):
- 当前 fastboot 就是 lk2nd,下载闸 256MB。boot2(52.6MB)传输
  **不存在闸不足问题**;0.003s 秒拒只可能来自 lk2nd `cmd_boot`
  本体或其前的 host 端 fastboot 工具。
- "vivo aboot MAX_SIZE 40MB"假说作废(§10 勘误条 2 证伪)。
- 下一步(离线可做,不改设备):读 lk2nd cmd_boot 源码路径,对
  boot2 头字段做纸面校验(page_size/kernel_addr/ramdisk_addr 与
  0x85700000 约定),定位真实拒绝点;设备侧复现(再次 boot)需
  用户下令。

### 10.4 V13:lk2nd cmd_boot 通读定论——本地 lk2nd 无任何尺寸闸(2026-11-06,纯源码,无设备)

在容器 /work/lk2nd-y35a-codex(即刷进 boot1 的同源树,版本 23.1-y35a-xnu-layout-v1)逐行读
`app/aboot/aboot.c:3168-3260`(cmd_boot)与 `app/aboot/fastboot.c:427-513,666-677`(cmd_download/
fastboot_init),结论:

1. **lk2nd 本地树不存在 0x2800000/MAX_SIZE 常数**(全树 grep 复核:仅 msm8x60/msm8960 无关的
   MSM_IOMAP_END;app/aboot 零命中)。recon-20261105 §P4 把该常数记在 lk2nd 名下,系张冠李戴。
2. lk2nd 的 download 闸 = fastboot_init(target_get_scratch_address(),
   target_get_max_flash_size()) → download_max,与 getvar max-download-size=0x10000000 同源,
   **256MB,52.6MB 的 boot2 畅过**。
3. cmd_boot 自身只有两类尺寸前拒绝:`sz < sizeof(hdr)`(hdr 是指针,sizeof=8,恒假,上游已知
   小疵)与 `image_actual > sz`(Android boot header 自洽性检查)。我们喂的是 GPT RAMBoot
   容器——**header 字段与 ANDROID! 魔数不是标准 boot image 形状,cmd_boot 对 GPT 容器的
   兼容性本就是待验项;0.003s 秒拒与 header 校验失败的时间特征完全一致,与容量无关**。
4. 推论(待一次设备取证钉死,二选一):
   a. 若拒收发生在 lk2nd 槽:失败串必然出自第 3 条 header 自洽/magic 路径——根因是**格式**;
   b. 若发生在 vivo 原生 aboot 槽(boot1 写入后设备已回退原生):0x2800000 常数属原生侧,
      本地无其源码,维持"假说"级。
   V11 时间线(06:27 getvar 会话先于写 boot1)两案皆可能;那次拒收会话的身份未记录——
   这正是 recon §P4 警告过的"会话未核"。
5. 打包侧含义(不等设备也能推进):若取证落在 4a,RAM boot 的 fastboot-boot 通路要求
   **容器外套 Android boot header(kernel 槽放现 GPT 容器)**,scripts/y35a/package_native.py
   新增 --bootimg 封装;这与 flash_from_boot 无关,是纯主机工作。
6. 下一次设备取证脚本(需用户明令,不在本轮做):进 lk2nd fastboot,同会话跑
   getvar product + `fastboot boot boot2` 记录完整 remote 串;OKAY 后传输失败则评估
   flash-boot 路线。

verify(2026-11-06,容器内只读):
grep -rn MAX_SIZE /work/lk2nd-y35a-codex/{app,platform,include,lib,target} → 无 boot 闸相关命中
sed -n '3168,3260p' aboot.c → cmd_boot 两拒绝分支 + VERIFIED_BOOT_2 条件编译(lk2nd msm8916 关闭)
sed -n '427,513p;666,677p' fastboot.c → cmd_download "data too large" 仅在 len>download_max
grep -rn 0x2800000 /work/lk2nd-y35a-codex → 仅 msm8x60|msm8960 iomap MSM_IOMAP_END(无关)


## 10.5 V14:传输层终局实测——40MB 闸彻底证伪,真实拒绝点是功能闸(2026-11-06 18:12,心跳)

设备当时已在 fastboot(非本会话送入);本节推翻 V11-V13 的"容量不足"叙事,
全部证据实测。

1. **宿主 fastboot 无 40MB 闸**:`fastboot boot fake41.bin`
   (41,984KB,`ANDROID!` 头 + 40MB 零体)→
   `Sending 'boot.img' (41984 KB) OKAY [1.324s]` —— 传输段完整通过。
   V11 的 0.003s 秒拒**不是容量拒收**。
2. **lk2nd 收包后死在功能闸,不是尺寸闸**:同一命令 remote 串 =
   `FAILED (remote: 'dtb not found')`。源码逐闸核过(容器
   /work/lk2nd-y35a-codex/app/aboot/aboot.c):
   - cmd_boot 头自洽闸 `image_actual > sz`(3248):fake41 全零字段算得
     2048+0 > 42991624? 否 —— 过;
   - 地址闸 check_ddr_addr_range_bound/check_aboot_addr_range_overlap
     (3421-3426):零字段平凡过;
   - **copy_dtb(3431)找不到 FDT magic 0xd00dfeed → 3469
     `fastboot_fail("dtb not found")`** —— 唯一拒收点。
   - cmd_boot 不校验 ANDROID! 魔数(memcmp 仅 boot_linux_from_* 路径);
     page_size 默认 BOARD_KERNEL_PAGESIZE=2048。
3. **boot2(52.6MB,真头字段)落点(纸面推导,一次实测可钉死)**:头自洽
   可过;下一站 3421:kernel 域 0x80080000+52.6MB 覆盖 0x8349C000,
   **压到实测 splash framebuffer 0x83200000(V10)**→ 最高置信串
   `kernel/ramdisk addresses are not valid`;再后 copy_dtb 一关
   (board.adt 是 unixnu ADT 非 FDT)。V11 未记录 remote 串,
   "header fields are invalid" 系事后转写,以本节为准。
4. **"vivo aboot MAX_SIZE 0x2800000"叙事全面作废**:V12 product=lk2nd;
   V14 传输 41MB 成功 + max-download-size=0x10000000。recon-20261105
   §P4 张冠李戴、V11 假说、记忆文件三处旧文由实测取代。
5. **打包侧结论(进系统关键路径,纯主机可推进)**:blob 必须按 Android
   header 语义分区放置——kernel 域放 EL1 垫片 + 11.4MB mach kernel
   (≈12MB,避开 splash);**42MB gz-HFS+ 挪进 ramdisk 域**
   (hdr->ramdisk_size=gz_len,lk2nd 解压目标 0x85700000 = fork 补丁
   y35a-xnu-layout aboot.c:412-420 钉死值,entry.S 已按此读取);
   ADT 侧载要么改真 FDT 走 dt 域、要么第二 sidecar 由 boot-args 定位
   (设计待定 = 新任务 T-PKG)。现版 package_native.py 把整块 42MB
   incbin 进 entry.bin → 54MB 单域,重跑实测即撞
   `ValueError: Image overlaps measured continuous-splash framebuffer`
   (0x83200000 守卫,18:0x 复现)——改造一处,结论:boot1 时代
   51MB 容器能 SEND 成功,V11 秒拒另有其因(最可能当时产物头字段
   与 lk2nd 自洽闸不符,待一次真 boot2 实测钉死)。
6. 设备现状:V14 实验后仍在 fastboot(拒收回 fastboot 循环,aboot 零
   写入)。回 Android 需用户下令。

verify(2026-11-06 18:12,实测+源码只读):
fastboot boot /tmp/fake41.bin → Sending OKAY 1.324s + FAILED (remote: 'dtb not found')
fastboot devices → efff9d92 fastboot(实验后仍在)
sed -n '3241,3253p;3416,3440p;3460,3470p' aboot.c → 三闸顺序与串
grep -rn 'dtb not found' app lk2nd platform → aboot.c:3469 唯一命中
sh /work/run-boot2-pack.sh → ValueError: Image overlaps ...(旧打包器不可重出 boot2,佐证 5.)

### 10.6 V15:点火前只读就绪态复核(2026-11-07 03:02,心跳,零写入)

A 段(首次 boot3 实机点火)就绪性坐实,全部只读命令:

1. `fastboot getvar product` = `lk2nd-msm8916`(承 V12:当前 fastboot 即
   lk2nd,非原生 aboot);`max-download-size` = 0x10000000(256 MiB,承
   V14:40MB 假说彻底出局)。boot3.img 54,618,112 B ≪ 上限,尺寸维度无闸。
2. `fastboot oem y35a layout` 应答 `ramdisk=0x85700000 tags=0x85800000`
   ——**fork-pin v1 编译进常驻 fastboot 实证**:这正是 aboot.c:412 钉死值,
   与 manifest `PIN_RAMDISK/PIN_TAGS`、boot_layout 交棒窗口三处一致。
   (注:此应答只证 pin 代码在场,不证 boot3 会命中 pin 触发条件——那要
   真 boot 时的 compatible/cmdline memcmp 全过,V14 已给拒收点几何。)
3. `current-slot` 空——RAM boot 不吃 A/B 槽,符合预期,非异常。
4. `oem help` 枚举出取证通路全在场:`boot` / `upload` / `oem ramoops
   dump|regions|console|raw` / `oem debug readb|readhw`。A 段取证(pram
   0x859e0000 staged + serial)的工具面确认,点火失败即有读回手段,
   无需额外编译探针。readback_native.py 的 Y35ARD01 表正是走 upload。
5. 设备现居 fastboot(efff9d92),工作树净,HEAD=be34a8b(B4 链五笔),
   boot3.img sha256 d7640a42…未动,17/17 打包闸绿。

结论:A 段前置全部坐实,唯缺用户授权点火这一动作。任何"再等等/先补件"
都不比直接 boot 取证更有效——B1-B3 缺件清单本身要靠点火现场才能排序。

verify(2026-11-07 03:02,全部只读):
fastboot getvar product/max-download-size → lk2nd-msm8916 / 0x10000000
fastboot oem y35a layout → ramdisk=0x85700000 tags=0x85800000
fastboot getvar current-slot → (空)
fastboot oem help → boot, upload, oem ramoops *, oem debug read* 全列
fastboot devices → efff9d92 fastboot

### 10.7 V15.1 传输层退化观察(2026-11-07 04:05-04:08,心跳,只读探测)

V15 全部就绪后、本心跳窗口内,fastboot 传输由"瞬答"退化为"无响应":
- 03:41 与 04:01 两轮 `fastboot devices` 均即时返回 efff9d92(在槽);
- 04:05 起 `fastboot oem help` 两次各挂 >30s(03:02 同命令 0.003s 应答);
- 04:08 `fastboot getvar product` 20s perl-alarm 强制击杀 rc=142,
  同刻 ps 全表无第二个 fastboot 进程(排除本机同型进程抢占用);
- USB 枚举层 grep 无 qusb/msm/2fd1 输出(system_profiler 查询本身
  未见设备条目)。
未做任何恢复动作(reboot/拔插均归用户下令)。含义:点火前传输健康是
A 段的隐含前置;下次心跳若仍无响应,先向用户报传输态再谈授权。storage
审计会话(a07c2e)busy 在册,若其设备通路走本 transport,则退化可能
只是串行排队——两种解释都未被证伪,故只记现象不记根因。

复测(2026-11-07 04:22,心跳):`fastboot devices` 即时应答 efff9d92
(枚举层健康),但 `fastboot getvar product` 15s alarm 内仍无 product
行——退化限于 open+transaction 通路,USB 枚举不受影响。与排队说
(其他会话持有接口时 devices 仍可枚举)一致,不构成设备损坏证据。
授权点火前仍应先看一眼 getvar 瞬答。

### 10.8 V15.2 排队假说容器分支证伪 + 主机 adb-server 嫌疑(2026-11-07 05:01,心跳,只读取证)

对 V15.1 "storage 会话串行排队"假说做可证伪测试(全部只读、零设备动作):

1. **容器分支排除**:`docker inspect` 工具链容器
   Devices=[]、Privileged=false,in-container `ps` 无 fastboot、
   无 /dev/bus/usb 直通。容器摸不到 USB,不可能是占用者——排队说的
   "另一进程持接口"只剩主机侧可能。
2. **主机侧嫌疑人**:`ps` 见 `adb -L tcp:5037 fork-server`(pid 62713,
   已运行 3h14m)。ioreg 显示设备以 "Android" AppleUSBDevice 在枚举、
   retain 15、busy 0。adb server 周期性 claim 全部 Android USB 设备,
   与 "devices 读 descriptor 瞬答 / getvar 需 claim interface 挂住"
   的形态吻合——这是目前最强的候选根因(仍未证实:ioreg busy 计数是
   瞬时值,不代表无持有者,retain 15 只证有内核引用、不指明持有者身份)。
3. **不做的事**:`adb kill-server` / USB reset / reboot 全属系统或设备
   状态变更,归用户下令(memory:未经授权禁改系统;不可逆操作闸)。守护
   只报候选根因与验证手段,不自行动手。

决定性测试(待用户授权点火前跑,一条命令即可定性):
`adb kill-server && fastboot getvar product` —— 若瞬答,根因坐实为主机
adb-server 抢占;随后 `adb start-server` 恢复即可,不影响设备。若仍挂,
排除 adb 假说,须拔插 USB 重枚举(=用户拔线动作)。

含义:A 段点火的真实前置是"transaction 通路空闲"。在 getvar 恢复瞬答
前,授权了也点不着(boot 命令同样走 claim interface)。

verify(2026-11-07 05:01 本机实跑):
docker inspect … --format Devices/Privileged → [] / false
docker exec … ps|grep fastboot → 空;ioreg "Android" retain 15 busy 0
ps -ax|grep adb → 62713 adb fork-server(etime 03:14:27)
fastboot devices → efff9d92 即时;getvar product → 12s alarm 无响应 rc=1

### 10.9 V15.3 传输形态改判:间歇 flap,非持续占用(2026-11-07 05:21-05:35,心跳,只读)

同窗口交替实测(单条命令 8-12s alarm 有界):
- `getvar product` 瞬答 lk2nd-msm8916;`oem help` 瞬答全表;
- 稍后 `getvar version` 与 `oem y35a layout` 连挂 rc=142;
- 期间 adb fork-server(62713)一直存活,状态未变。

改判:V15.2 "adb-server 周期 claim"假说不成立——持续持有解释不了
同类命令有时瞬答(持有者不放手就没有事务能过)。现形态 = **间歇性
争用**:有的事务窗口能过,下一窗口挂。存活假说收敛两条:
(a) storage 审计会话(a07c2e busy 在册)与守护探测交替摸同一 USB
接口,fastboot 单客户端锁使撞车方挂;(b) USB/设备端偶发不应答。
(a) 与全部观察相容且不需新实体;(b) 只读手段无法排除。

点火判据升级:需连续 ≥3 轮全瞬答才具备可靠传输 55MB 镜像的条件;
flap 期点火有半程失败风险(可逆但取证被污染)。后续心跳顺带记录
getvar 成功率与 a07c2e busy/idle 的同步性——同步即坐实 (a)。

verify(2026-11-07 05:21-05:35 本机实跑,全部有界):
getvar product → 瞬答 rc=0;oem help → 瞬答 rc=0
getvar version → 8s alarm rc=142;oem y35a layout → 8s rc=142 ×4
ps → adb 62713 存活 etime 03:33:16;ListAgents → a07c2e busy

### 10.10 V15.4 测量自纠+时间戳勘误(2026-11-07 05:21-05:24,心跳,有界只读)

**勘误一(测量假象撤案)**:上轮首采"背靠背四条 rc=1 同秒"系
zsh 无引号参数不拆分所致——`fastboot $cmd` 把 "getvar product"
当单参数传入,fastboot 打 usage 即退 rc=1,根本没碰设备。该
"瞬时失败模式"不存在,10.9 的"claim 竞态二分"判读作废。真实
采样全部 rc=142:本 turn 三条独立 getvar product 各满 8s alarm
(05:24:07/15/23),10.9 里 version/layout 同样 rc=142。传输
形态回归单一描述:**事务通路持续挂起,偶发窗口能过**(10.9
turn 的 product/oem help 确曾瞬答),`devices` 枚举始终即时。

**勘误二(时间戳回推)**:adb 62713 起点 = 05:21:50 − etime
03:53:50 = 01:28:00。据此:10.8(V15.2)的 ps etime 03:14:27
→ 实跑于 **04:42**(节头误记 05:01);10.9(V15.3)的 etime
03:33:16 → 实跑于 **05:01**(节头误记 05:21-05:35)。本节
05:21-05:24 为 date +%T 直读,可信。两处旧节头不回改正文,
以本节为准;结论(假说未裁决、点火前置未满足)不受影响。

现行判读(替换 10.9 的竞态升级):自 04:05 起事务通路挂起为主,
05:01 窗出现成对瞬答(product/help 同 turn 均 rc=0),呈"低
成功率 + 偶发瞬答"形态。(a) storage 会话交替占用与 (b) USB
偶发不应答仍都能覆盖;裁决手段不变:storage 收工看回升,或
拔插一次。点火前置(连续 ≥3 轮全瞬答)远未满足,守护继续只
观察不动手。

verify(2026-11-07 05:21-05:24 本机实跑,单命令 8s 有界):
背靠背四条 rc=1 → zsh 不分词产物,未触设备(撤案)
getvar product 独立三条 → rc=142 ×3(05:24:07/15/23)
ps → adb 62713 etime 03:53:50@05:21:50 → 起点 01:28:00
fastboot devices → efff9d92 即时

### 10.11 V15.5 跨会话证词裁决:(a) 会话争用假说基本证伪(2026-11-07 07:41-07:55,心跳)

向 a07c2e「UniXNU storage interface audit」发只读取证询问(明确要求
对方不动任何状态),得第一方时间线证词:
- 该会话最后一次 **事务性** fastboot 操作 = **01:40 CST 的
  `fastboot upload`**(取 panic2.raw);04:08-04:09 有两次
  `fastboot devices` 只读枚举(当时正常返回);04:09 后无任何
  fastboot 命令,ps 无 fastboot/adb 客户端进程。
- 守护侧挂起起点 = **04:05**(V15.1:同刻 devices 枚举正常,
  与证词无冲突)。01:40 与 04:05 相隔近 2.5h,期间 03:02 全轮
  瞬答——对方事务时间线覆盖不了挂起窗口。

裁决:V15.4 的 (a) "storage 会话交替占用" 版本 **基本证伪**
(第一方证词 + 03:02 全瞬答事实双杀)。对方另提常驻争用嫌疑
= adb fork-server(62713,01:28 起):macOS 下 adb/fastboot 同走
libusb,server 或周期性 claim 高通 PID 干扰事务。守护侧已有
事实部分反证——adb 01:28 存活而 03:02-04:05 事务全通;除非
04:05 后轮询模式改变,否则解释不了挂起起点。残余低概率嫌疑,
定性测试 = `adb kill-server && fastboot getvar product`(一条
命令即可裁决,但属本机服务状态变更,按"未经授权禁改系统"闸
**待用户批准**,守护与 peer 均不动手)。

现行最优假说: **(b) USB 层/设备端 stale**——04:05 起事务通路
挂起而枚举健在、两会话均无对应操作、flap 后转恒挂,与设备端
状态漂移一致。首选裁决动作相应变为**拔插 USB 重枚举**(用户
物理动作);拔插后若 getvar 连续瞬答,即恢复点火条件(判据
不变:连续 ≥3 轮全瞬答)。

verify(2026-11-07 07:41-07:55):
SendMessage 取证询问 → peer 第一方证词收到(01:40 upload/
04:08-09 devices/之后无 fastboot,ps 自证)
挂起点 04:05(V15.1 原始记录,devices 正常并存)
03:02 全轮瞬答(V15 verify 原文)
07:55:50 本机独立复核:ps → 无 fastboot 客户端,adb 62713 存活
etime 06:27:17(→起点 01:28:33,与证词及 10.10 回推一致);
getvar product → rc=142 仍挂;devices → rc=0 即时枚举

### 10.12 V16 boot3 实机点火取证:内核跑到 pid 1 launchd,确定性 panic;原因串不在捕获区(2026-11-07 06:30-08:30,本会话)

**点火结果(传输层大案就此结案)。** 两次 `fastboot boot
out/y35a/ios12-boot3/boot3.img`(00:07 与 01:40 CST 前后)均:
`Sending 'boot.img' (53338 KB) OKAY [1.680s] / Booting OKAY
[0.033s]`(boot3-serial.log 原文,163B)。54,618,112B 容器全收,
V10-V15.5 传输线关闭。0x859f0000 处 Y35AXNU2 尾记录
(panic.raw@0x10000)给出 CurrentEL=EL1、entry=0xa026e0a0
(=boot3 manifest kernel_entry_physical)、sha 前缀 5fd4e6b5f7fa10e1
(=在跑内核)——交棒闭环全证。

**panic 事实。** `oem y35a panic` 读回 69,632B 两次,panic.raw 与
panic2.raw `cmp` 逐字节全等:确定性逻辑故障,非竞态。正文
`Panicked task 0xfffffff35f1bb230: 3 pages, 1 threads: pid 1:
launchd`——XNU-4903 已挂载根、bsd_init 已 spawn launchd,死在
pid 1 上下文,tid 178。Zone map/TPIDR/Compressor 各段齐全,
`** Stackshot Incomplete ** Bytes Filled 240 **`。

**有界符号化(推翻此前 nm 最近前缀假象)。** 用 lldb STABS
`image lookup -a` 逐帧(与 /tmp/k4903.noctf 同一构建
5fd4e6b5):可靠代码帧全部是 panic 机器本身——
mach_absolute_time+368(panic_display_times 里)、
arm_debug_set32+908、thread_state64_to_saved_state+180。
落在 `__DATA.__common`/`__LINKEDIT` 的 5 帧(realhost/kdp_*
+数据段、两处 LINKEDIT)是 fp 链越过栈底的陈旧垃圾;
pf_frag6cache/pf_map_addr/pf_pptp_handler/pf_nat64_ipv4 一串是
静态函数被剥离后的最近前缀假命中(12 秒用户态不可能跑包过滤)。
结论:**回栈本身不含新信息,信息在缺失的前缀里。**

**原因串为何缺席(结构定案)。** 4903 `save_panic_log`
(osfmk/arm/model_dep.c:370-430)写序 = message(reason) → Kernel
Boot UUID → iBoot version → Paniclog version → ASLR →
`panic_display_times`(mach_absolute_time → Epoch Boot/Sleep/
Wake → **Calendar**)→ Zone。捕获正文从 `Calendar:`(文件
0x3c2)起,其前全零;即 Calendar 之前的半行时间戳与整个前缀
(含 panic reason、Boot/Sleep/Wake)未落入读回区或写在了别处
偏移。捕获头 64B 是 Y35ARD01 格式(Magic+sha+EL+MIDR@56=
0x410fd030 与 Nov-4 探针头同族)但 0x20/0x24 处两 u32
(0xa9/0xa37)与 readback_native.py 的 ID 寄存器布局不符——
头部写入者存疑,已单列待查;0x1c8-0x238 的 9 个 u64 指针簇
全部落在 `__cstring` 的 ml_dbgwrap_strerror 表(osfmk/arm/
dbgwrap.h:53-66),是 CPU 停机状态字符串,佐证 panic 路径执行了
多核 halt 流程(cpus=1 下 CORE 0 那行也印了)。

**EPH / panic 保存状态（2026-11-07 21:52 更正）。** 旧有效 capture 头
字段为 `eph_panic_log_offset=0xa9`、`eph_panic_log_len=0xa37`，因此正文
物理范围是 `[pram+0xa9, pram+0xae0)`；文件偏移 0x3c2 对应
`pram+0x382`。readback manifest 实际把 early-fault 与全局变量槽位
依序写入 pram 偏移 `[0x40,0x640)`，异常栈又写 `[0x640,0x4640)`，
intstack 写 `[0x4640,0xc640)`。因此旧正文前段被 early-fault/全局槽位
覆盖，后段被异常栈覆盖；只剩 `Calendar` 及 Zone/回栈等后缀，原 panic
message 无法从现有两份 dump 恢复。

XNU-4903 的 `PE_create_console()->check_for_panic_log()` 若看到
`EMBEDDED_PANIC_MAGIC` (`KNUF`, `debug.h:322`)，会打印“iBoot didn't
extract panic log from previous session crash”并 bzero 整个 64 KiB PRAM。
当前 lk2nd `oem y35a panic` 只 stage `0x859e0000..+0x11000`，源码没有
KNUF 提取器；历史 readback 写的 `Y35ARD01` 也不是 KNUF。因此旧有效
panic capture 可能来自更早一次 boot 前已有 KNUF 状态，但现有 evidence
不能证明其来源。

最新 clean boot3 的直接 stage（未运行 readback probe）显示 EPH
`eph_panic_log_offset=0`、`eph_panic_log_len=0`，panic 正文全缺。LK log
确认 boot3 -> reset -> `oem y35a panic` -> upload，中间无第二轮 XNU boot。
与旧有效 capture（offset `0xa9`、len `0xa37`）不同；新的零长度分叉仍待
根因定位，不能归结为 BSS读回或 reset-only stage。

reset-only probe 的两次 staging SHA 均为 `e946dd27…`，byte-identical，
说明该 reset-only/fastboot_stage 序列没有进一步改写 PRAM。证据文件：
`evidence/y35a-20261102/boot3-20261106/boot4-empty-readback-20261107.txt`。

verify(2026-11-07): `fastboot boot` boot3 SHA `d7640a42…` → OKAY；直接
`oem y35a panic`/`get_staged` → 69,632 B, SHA `054f4a90…`, EPH offset/len=0；
reset-only stage SHA `e946dd27…` 与先前 boot4 readback 一致；离线测试
readback 4/4、package 17/17 通过。

verify(2026-11-07 06:30-08:30,本会话,全程无设备写):
cmp panic.raw panic2.raw → IDENTICAL
lldb --batch image lookup ×14 帧 → 上文分段(__text vs
__DATA.__common vs __LINKEDIT)
python3 u64 扫描 0x40..0x400 → 0x1c8-0x238 九指针簇
lldb image lookup 0xfffffff0070329cc…ab3 → __cstring
ml_dbgwrap_strerror 串表
docker exec readlink manifest.json → entry 0xa026e0a0 == 记录
Nov-4 十五个 readback/probe dump:grep 'lr: 0x' 全 0 命中,
Calendar/Panicked task 全无 → Y35ARD01 头格式与 XNU 正文的
共存体仅此两次 boot3 捕获(头部来源存疑项)

### 10.13 V15.6 传输恢复+裁决终局:跨会话争用(变体)坐实(2026-11-07 09:41-09:42,心跳,有界只读)

**点火前置达成。** 09:41:53 起三连探全瞬答——getvar product →
lk2nd-msm8916 (rc=0)、oem y35a layout → ramdisk=0x85700000
tags=0x85800000 (rc=0)、getvar product 再瞬答 (rc=0)。V15.4
判据(连续 ≥3 轮全瞬答)满足,事务通路恢复。

**裁决终局(证据权重反转,V15.5 的判读被时间线推翻):**
挂起窗 04:05→09:26 与 a07c2e 的点火取证操作窗(其自述 06:30-
08:30 + 09:03 交 V16 + 09:26 仍在交证据后处理)完全重叠;守护
09:26 探测仍挂、09:41 恢复瞬答,恰在其操作收尾后。a07c2e 证词
"04:09 后无 fastboot 命令"与其 04:05 起守护侧观测矛盾、与其
V16 自述时间窗也矛盾(06:30 起显然在用)——更可能证词表述的是
"没有独立跑过命令行 fastboot",而其会话内的设备交互(含点火
与读回)持续持有接口。**macOS libusb 单客户端独占 + a07c2e 会话
操作期持口 = 挂起窗的唯一全覆盖解释;(b) USB stale 假说失去
必要性。** adb-server 嫌疑同步出局(01:28 存活 vs 01:28-03:02
全瞬答)。

**操作规程修正(写入判据):** ①守护心跳的设备探测改为先 ListAgents
——a07c2e busy 时跳过 fastboot 探测(不争口,也不把对方持口误判
为退化);②boot4 点火/读回窗口期内(任何会话声明在途设备操作),
守护只观察 git/证据文件,不做设备侧动作;③传输健康判据继续有效,
但仅在"无其他会话声明在用设备"时才有裁决力。

**boot4 前置状态:** 传输已恢复瞬答;a07c2e 的 V16 判据(读回
_panicstr)仍有守护 09:21 提交的符号核验待定(4903 无 _panicstr,
载体应为 debug_buf 三元组,已跨会话送达,未获回应)——守护继续
不代做,等其处置或用户调停。

verify(2026-11-07 09:41-09:42,本机实跑,三连全部单命令 8s 有界):
09:41:53 getvar product → rc=0
同命令块内随后两探(约 09:41:54-09:41:58,未各自打点):
oem y35a layout → rc=0(应答含 0x85700000/0x85800000)
getvar product 二探 → rc=0;devices → efff9d92 即时
时间线对照:a07c2e V16 verify 自述 06:30-08:30、提交 09:03/09:04
(30fbfa4);守护 09:26 rc=142、09:41 rc=0

### 10.14 V17 r4 同电源周期取证:探针自我覆盖缺陷修复 + 载体回读分叉定案(2026-11-08 21:30-23:4x,心跳,用户明示授权设备操作)

**静态缺陷(TDD 先红后绿)。** r3 生成顺序 = record-table 先拷(写 PRAM+0x40..0xc640
= panic 正文窗口),debug_buf 捕获后跑 → 探针覆盖自己的证据;§10.12 旧正文残缺
(0x3c0 前全零)即此缺陷在 Nov-7 捕获上的投影。修复 = readback_native.py 重排
(copy_bytes 先于 table,守卫失败 b.* set_table 落空仍拷 records),新闸
test_panic_log_copy_precedes_record_staging RED→GREEN,全套 39/39。

**同电源周期实机序列(全程 fastboot boot,无断电,无分区写)。**
r3(旧序)boot→OKAY,stage+get_staged=readback-raw.bin(c720ffb8…):
marker/stamp 正确,但载体全 0,0x10000 落点 4078B 全为不可打印残留(
printable_ratio 0.018,含 Y35AXNU2 头)。boot3(d7640a42…)→OKAY+70s 回
fastboot → 立即 boot r4(新序 3658efc7…)→OKAY,stage=get_staged=
readback-r4-raw.bin(bdb2cbc2…):载体值与 r3 逐项相同(全 0,
_panicDebugging=0x100,_debug_buf_ptr=0x0800000000000000),正文区同一份
不可打印残留 → 顺序修复改变覆盖时序但未改变结论:本次 boot3 运行没有在
PRAM 留下新文本。对照(boot3 后不跑探针直接 stage):panic-direct-20261108.raw
(85a999df…)文本区全零,0x1c8..0x240 有 120B 非零簇(与旧 panic.raw dbgwrap
指针簇同位,残留/新写未辨)。

**新事实与假说裁决。**
1. panicDebugging 文件初值 0、实读 0x100(__DATA,PA 平移对 delta=0 段有效,
   与 boot3 manifest kernel_physical_base=0xa0000000 同基)→ 本次 boot3 的
   XNU 确实执行并写过 __DATA(非纯 DRAM 冷残)。但 debug_buf 三元组全 0,
   而 §10.12 源码链(PE_create_console→check_for_panic_log 后 debug_log_init
   立即设 debug_buf_base=gPanicBase+0x74)若跑过则 base≠0 → 新分叉候选:
   本次 boot3 未跑到 debug_log_init/未再进 launchd,或 gPanicBase 映射失败。
   _BootArgs=0 同样反常(LK 写 boot-args 页 0xa0b7c000 非零,XNU 复制进
   __DATA_CONST 的 _BootArgs 应为非零指针)。
2. __BOOTDATA 段 fileoff/vmaddr delta=-0x90000 ≠ 0:探针线性公式对
   _excepstack/_intstack 的 PA 在"文件线性加载"下错位 0x90000(本项待核,
   不影响上述 __DATA 结论)。
3. 探针回读值与 Nov-7 panic.raw 同槽对比:Nov-7 探针槽里是 ASCII 正文串
   (自覆盖),今日两代探针槽值互等且与文本无关 → r4 修复后槽数据干净,
   读的是真物理初值。
4. 传输新形态:`oem debug readq` 在 getvar 瞬答成功后立即 e00002ed,两轮
   脚本(单条有界)全同 → 命令级失败而非链路争用;裁决载体实值需另一通道
   (扩展探针 records 直读 PA 0xa026e0a0/0xa0b7c000 正合此用,下一轮)。

verify(2026-11-08 本会话,全部实录):
python3 -m unittest discover -s tests → Ran 39 tests OK
fastboot boot r3/r4/boot3 → Sending/Booting OKAY(见上列 sha)
oem y35a panic/get_staged → rc=0 三轮(69632B)
getvar product 瞬答 vs readq 即挂 → livedram-readq.log(23:34:04 recovered,
4×readq e00002ed)
