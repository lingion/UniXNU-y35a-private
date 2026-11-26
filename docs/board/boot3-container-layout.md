# boot3 RAMBoot container layout — passing the resident lk2nd `fastboot boot` path

Status: T-PKG design + implementation record, 2026-11-06. No device was touched
by this task; every "gate" below is arithmetic re-executed from the source of
the resident lk2nd tree (container `unixnu-y35a-native-20261103`,
`/work/lk2nd-y35a-codex`, version 23.1-y35a-xnu-layout-v1, the same source as
the boot1 slot). Line numbers cited from that tree.

Supersedes: the boot2 container shape (54 MB single kernel domain + ADT in the
dt domain), which V14.7 measured to die at `dtb not found`.

---

## 0. Answers to the two questions the brief asks

Q1: does the 42 MB rootfs go through the Android **ramdisk domain** (decompress
semantics, target address?) or stay **sidecar-copied by the shim**?

Neither. It goes into the **second ("extra") domain**, which the resident
`cmd_boot` treats as inert bulk bytes that simply stay in the download buffer
at SCRATCH (0x90000000); the shim then copies it from
`SCRATCH + second_off` into the owned window, exactly like the boot2 sidecar
but without bloating the kernel domain. Three source facts force this:

1. lk2nd's `cmd_boot` never decompresses the ramdisk domain on the fastboot
   boot path. The only gzip handling in `cmd_boot` is for the kernel domain
   (`aboot.c:3374` `is_gzip_package(data+page, hdr->kernel_size)`); the
   ramdisk is delivered by one raw `memmove(hdr->ramdisk_addr, ptr+page+
   kernel_actual, hdr->ramdisk_size)` (`aboot.c:3467`). A gz rootfs in the
   ramdisk domain would arrive gzipped at best, and XNU has no consumer for a
   Linux-style initrd anyway. (Correction to bringup-map §10.5 V14 item 5:
   "lk2nd decompresses gz into 0x85700000" is wrong — there is no decompress;
   0x85700000 is only an address pin.)
2. The fork patch `update_ker_tags_rdisk_addr` (`aboot.c:412-420`) pins
   `ramdisk_addr=0x85700000, tags_addr=0x85800000` only while
   `hdr->ramdisk_size == 1` (plus cmdline, `text_offset==0x80000`,
   `kernel_size <= 0x3180000`). Putting a real-size rootfs into the ramdisk
   field breaks the pin, after which the stock policy applies
   `ABOOT_FORCE_RAMDISK_ADDR = DDR_START+0x20000000/0x2000000 = 0x82000000`
   (`platform/msm8916/include/platform/iomap.h:49-52`,
   `build-lk2nd-msm8916/config.h:16` sets `ABOOT_IGNORE_BOOT_HEADER_ADDRS`),
   and a 43 MB copy from 0x82000000 runs straight through the live splash
   framebuffer at 0x83200000. Keeping `ramdisk_size = 1` means **no lk2nd
   rebuild/reflash is needed** — device-side work stays zero.
3. The kernel domain must shrink below `0x3180000` (51.75 MB) to keep the pin;
   boot2's 54,431,312-byte entry.bin already failed that condition on paper
   (and its ADT-in-dt-domain failed `copy_dtb` in the V14.7 measurement).
   The 42,991,616-byte rootfs is what made it 54 MB; moving it to the second
   domain drops the kernel domain to about 11.44 MB, far below the splash
   start at 0x83200000.

Q2: does the layout require a change to the lk2nd patch?

No for the chosen path. The dt domain is a real minified QCDT built by the
existing `select_device_dt()` from the device's own stock boot image; that
satisfies `copy_dtb` with the patch v1 pin still firing (verified per-gate
below). A patch v2 would only be needed for the rejected ramdisk-domain
variant; the draft diff is recorded in `refer/`-style section 8 anyway,
marked "awaiting main control rebuild and flash, NOT required for boot3".

---

## 1. ASCII layout map (physical RAM, during and after cmd_boot)

```
0x80000000 +---------------------------+ DDR start (2 GiB, ends 0x100000000)
           |  ... hole 0x800000..      |
0x80080000 +---------------------------+ kernel_addr (forced by patch: text_offset 0x80000)
  ~0x80B79000 | KERNEL DOMAIN = entry3.bin |  shim + Image-header + mach(11.44MB)
           |  (about 11.44 MB, page-aligned end) + 00 pad |
           +---------------------------+
           |            ...            |
0x83200000 +---------------------------+ splash FB start (measured V10)
0x83E48000 +---------------------------+ splash FB conservative end
           |            ...            |
0x85700000 +---------------------------+ ramdisk_addr pinned by fork patch
           | 1 byte '\0' (ramdisk_size=1), rest untouched|
0x85800000 +---------------------------+ tags_addr pinned by fork patch
           | stock FDT (179,134B) copied by copy_dtb,    |
           | grown in place by update_device_tree to     |
           | about 180.4 KB total, still < 0x85840000    |
0x85900000 +---------------------------+ reserved window end (0x85700000..0x85900000)
0x859E0000 |  pram staging (oem y35a layout hook)        |
0x859F0000 |  shim magic page 'Y35AXNU*'                 |
           |            ...            |
0x8F600000 +---------------------------+ MEMBASE (LK resident text+data+bss+heap, MEMSIZE 1 MiB)
0x8F700000 +---------------------------+ MEMBASE+MEMSIZE = only region the overlap gate protects
           |            ...            |
0x90000000 +---------------------------+ SCRATCH_ADDR = fastboot download buffer (256 MiB budget)
           | header(2048)                               |
           | ROUND(kernel domain)                       |
           | ROUND(1) = 2048 (ramdisk placeholder)      |
0x90AE3000 | SECOND DOMAIN = 42,991,616 B raw HFS+      |  <-- shim reads rootfs from here
           |  ...                                       |      (stays inert to lk2nd)
0x933E3000 | ROUND(dt) = 182,272 B minified QCDT        |
0x9340E800 +---------------------------+ container end (sz = image_actual)
           |            ...            |
0xA0000000 +---------------------------+ owned XNU window start (physical_base)
           | mach kernel text/data, boot_args, ADT,     |
           | RAMDisk copy @0xa0b84000, TrustCache       |
0xB0000000 +---------------------------+ owned window end (OWNED_SIZE 256 MiB)
```

Nothing written above by lk2nd collides with anything below that XNU owns;
the container itself lives in SCRATCH, which the ADT never maps.

## 2. Container geometry and every header field (boot3, v1)

Page size is taken from the header by lk2nd (`aboot.c:3226`,
`target_is_emmc_boot()` is true, `_EMMC_BOOT=1` in config.h) — we ship 2048.

Field offsets are the v0 `boot_img_hdr` (`app/aboot/bootimg.h:45-70`;
`OSVERSION_IN_BOOTIMAGE` is not defined in this build, so the `dt_size`
slot lives at byte 40 — `aboot.c:3238` reads exactly that).

| offset | field | value | why |
|---|---|---|---|
| 0 | magic | `ANDROID!` | not checked by cmd_boot, checked by host tool |
| 8 | kernel_size | len(entry3.bin) (about 11,439,6xx) | must be `<= 0x3180000` for the pin; `text_offset` gate below |
| 12 | kernel_addr | 0x80080000 | informational; lk2nd overwrites (see gate walk) |
| 20 | ramdisk_size | 1 | pin condition; memmove copies 1 byte |
| 24 | ramdisk_addr | 0x85700000 | overwritten to same by patch |
| 32 | second_size | 42,991,616 | rootfs; inert to cmd_boot |
| 36 | second_addr | 0x90AE3000 | SCRATCH+second_off, informational only (lk2nd ignores it here) |
| 40 | tags_addr | 0x85800000 | overwritten to same by patch |
| 44? | page_size (off 30? see list) | 2048 | see below |
| 40 | tags_addr | ... | |

Exact pack order (as in code): `struct.pack('<10I', …, kernel_size, 0x80080000,
1, 0x85700000, second_size, 0x90AE3000, 0x85800000, 2048, dt_size, 0)` at byte 8.

| offset | field | value |
|---|---|---|
| 8 | kernel_size | len(entry3.bin) |
| 12 | kernel_addr | 0x80080000 |
| 16 | ramdisk_size | 1 |
| 20 | ramdisk_addr | 0x85700000 |
| 24 | second_size | len(rootfs) = 42,991,616 |
| 28 | second_addr | SCRATCH + second_off (0x90AE3000 for entry3.bin of 11,439,6xx B) |
| 32 | tags_addr | 0x85800000 |
| 36 | page_size | 2048 |
| 40 | dt_size | len(minified QCDT) = 182,272 |
| 44 | unused | 0 |
| 64 | cmdline | `y35a-native-xnu-experimental` (pin condition, memcmp of 29 bytes incl NUL) |
| 576 | sha1 over kernel+ramdisk+second+dt each with `<I` length suffix | v0 layout, recomputed |

Domain byte map (total sz == image_actual, no trailing slack):

```
[0,2048)               header page (zero-padded remainder)
[2048, 2048+ROUND(k))  kernel domain entry3.bin + 00 pad
[…, …+2048)             ramdisk domain: single 0x00 byte + 2047 pad
[…, …+ROUND(42991616)) second domain: raw HFS+ (page-aligned already)
[…, …+182272)           dt domain: minified QCDT v3 (page-aligned already)
```

`ROUND(x) = align to 2048`. With the boot2 kernel domain minus the 42 MB
incbin, k = 11,439,6xx, ROUND(k) = 0xAE6000 (11,440,128):

```
sz = 2048 + 11,440,128 + 2048 + 42,991,616 + 182,272 = 54,618,112 B = 0x3413800
```

(final numbers are recorded in section 7 once the artifact is built).

## 3. Gate-by-gate paper verification (resident lk2nd, source-pinned)

Constants: `page_size=2048`, `page_mask=2047` (`aboot.c:3226-3228`),
DDR = [0x80000000, 0x100000000) (2 GiB, `check_ddr_addr_range_bound` uses
`smem_get_ddr_size()`), LK resident protected region
[MEMBASE, MEMBASE+MEMSIZE) = [0x8F600000, 0x8F700000)
(`build-lk2nd-msm8916/config.h:32-33`), download buffer base = SCRATCH =
0x90000000, budget 256 MiB (`target/msm8916/meminfo.c:79,84` —
`target_get_max_flash_size() == 256*1024*1024`; `fastboot.c:666-677`
`fastboot_init(base, size)` stores them; `fastboot.c:578` dispatches
`cmd->handle(arg, download_base, download_size)` — so `data == 0x90000000`,
`sz == len(boot3.img)`, confirmed by the V14 fake41 measurement).

1. `sz < sizeof(hdr)` (`aboot.c:3216`) — `hdr` is a pointer, sizeof==8,
   sz is 52 MiB. False. Pass.
2. Header self-consistency (`aboot.c:3248`): `image_actual =
   page + ROUND(kernel_size) + ROUND(ramdisk_size) + ROUND(second_size)
   + ROUND(dt_size) = 54,618,112 == sz`. Gate is `image_actual > sz` —
   equality passes. This is the gate V14.7 proved alive (unpadded replica
   reproduced `bootimage header fields are invalid`).
3. `image_actual` vs buffer (`aboot.c:3317`): `(256 MiB − 2048) <
   54,618,112`? No. Pass. (`target_use_signed_kernel()` is false on msm8916
   lk2nd — no der parsing path; `MDTP_SUPPORT`/`VERIFIED_BOOT*` are not in
   config.h, all compiled out.)
4. Kernel domain is not gzip (`aboot.c:3374`): first two bytes of entry3.bin
   are the ELF-ish `b enter` word (0x…14), not 1f 8b. `out_len = 0`,
   `kernel_start_addr = data + 2048`, `kernel_size = hdr->kernel_size`.
5. `kptr->text_offset = 0x80000` (kernel bytes 8..15) is not `> 2 MiB`, so
   it is kept (`aboot.c:3393`), `magic_64` at bytes 56..59 is `ARMd`
   (0x644D5241), so `IS_ARM64(kptr)` is true.
6. `update_ker_tags_rdisk_addr` (`aboot.c:400-445`):
   stock policy sets kernel_addr = `DDR_START + 0x80000 = 0x80080000`,
   ramdisk_addr = `DDR_START + 0x2000000 = 0x82000000`, tags = 0x81E00000;
   then the fork block fires because compatible=="vivo,pd1502a" (resident
   device tree, V12 `oem y35a layout` answered it), `text_offset==0x80000`,
   `kernel_size ≈ 11.44 MiB <= 0x3180000`, `ramdisk_size==1`, cmdline equal:
   ramdisk_addr→0x85700000, tags_addr→0x85800000. Then the image_size block
   (bytes 16..23 of entry3 = image length, nonzero) remaps
   kernel_addr = (0x80080000 & ~0x1fffff) + 0x80000 = **0x80080000**
   (fixed point — boot2 relied on the same arithmetic). `VA()` is identity
   1:1 (`platform/msm8916/platform.c:150-158`).
7. Address gates (`aboot.c:3421-3426`):
   - kernel: [0x80080000, 0x80080000+ROUND(11,439,6xx)=0x80B66000…0x80B79000)
     — `check_aboot_addr_range_overlap` only fails inside
     [0x8F600000,0x8F700000); we are far below. Pass.
   - ramdisk: [0x85700000, 0x85700800) — same reasoning. Pass.
   - both inside DDR bound. Pass.
   (V14.7 confirmed experimentally that this gate does NOT know the splash
   framebuffer; avoiding the splash is our own invariant, enforced by the
   packer guard, and the layout honors it with 36 MB of margin.)
8. `copy_dtb` (`aboot.c:3073-3167`, called from `aboot.c:3431` with
   `scratch_offset = image_actual + page + out_len` — out_len=0):
   `dt_size = 182,272 != 0`; `dt_image_offset = 2048 + ROUND(k) + ROUND(1)
   + ROUND(second)` (second_size != 0 branch, matches packer), table at
   `boot_image_start + dt_image_offset` = 0x933E3000.
   `dev_tree_validate`: magic `QCDT` (0x54444351) ✓ version 3 ✓ entries 1 ✓
   `dt_hdr_size = ROUNDUP(12+40, hdr->page_size=2048) = 2048 <=
   ROUND(dt_size) = 182,272` ✓.
   `dev_tree_get_entry_info`: entry (platform 206, variant 8, subtype 23)
   vs board (soc_id 206, HW_PLATFORM MTP=8, subtype 23, PMIC PM8916) — the
   single-entry table was produced by `select_device_dt()` from the device's
   own stock QCDT, i.e. the exact tuple stock LK matched; `offset=2048`,
   `size=180,224` inside table bounds ✓.
   entry bytes start `d0 0d fe ed` → not gzip; `check_*` on
   tags_addr [0x85800000, 0x85800000+180,224) → pass; `memmove` copies the
   stock FDT to 0x85800000. Returns 0 → `dtb_copied=1`, the appended-DTB
   search and the `dtb not found` fail at `aboot.c:3469` are skipped.
9. tags gate (`aboot.c:3445`): `check_ddr_addr_range_bound(tags_addr,
   kernel_actual)`: 0x85800000 + 0xAE6000 = 0x862E6000 < DDR end. Pass.
10. Loads (`aboot.c:3467-3468`): 1 byte to 0x85700000; kernel domain
    `memmove(0x80080000, 0x90001000, ROUND(kernel_size))`. The second domain
    at 0x90AE3000 is never touched — it stays in DRAM (USB writes are
    completed before the command runs; V14 measured exactly this buffer
    persistence with fake41).
11. `boot_linux` (`aboot.c:1218-1324`): cmdline has no `androidboot` and is
    not `lk2nd` → `GENERATE_CMDLINE_ONLY_FOR_ANDROID` keeps it verbatim.
    `update_device_tree(0x85800000, …)`: stock FDT has `/memory`
    (dtb10.dts:8555) and `/chosen` (dtb10.dts:8528) — the two hard failure
    nodes; `fdt_open_into` grows it by `DTB_PAD_SIZE(1024)+29` bytes into
    the still-free 0x85800000+ window (V14.7 reserved window ends
    0x85900000, 1 MiB). `initrd-start/end` are written pointing at the
    1-byte placeholder — harmless, XNU ignores this FDT entirely.
    `target_display_shutdown()` then `scm_elexec_call(0x80080000,
    0x85800000)` → EL3 monitor jumps EL1 shim with x0 = 0x85800000
    (shim ignores x0, same as boot2).

Every gate: green on paper, and all but step 8's content match are the same
gates V14.7 already exercised with a real device pass-through to
`dtb not found` (boot3 supplies precisely what boot2 lacked there).

## 4. Conflict table (region × owner × boot3 use)

| region | owner | boot3 touches? | verdict |
|---|---|---|---|
| [0x80080000, 0x80B79000) | kernel domain (shim+mach copy target) | lk2nd memmove writes; shim runs here | clear of everything below |
| [0x83200000, 0x83E48000) | live splash FB until `target_display_shutdown` (just before jump) | never written by kernel/ramdisk/tags domains | preserved; packer guard keeps kernel end `<= 0x83200000` |
| [0x85700000, 0x85900000) | fork-pinned ramdisk+tags window | 1 byte at 0x85700000; FDT +1024 pad at 0x85800000 (end about 0x85830000) | inside window, ends 816 KB before 0x85900000 |
| 0x859E0000/0x859F0000 | pram staging + shim magic page | shim only (post-jump) | outside the pinned window; LK never writes it before jump |
| [0x8F600000, 0x8F700000) | LK text+data+bss+heap | never | the only region the overlap gate protects — no domain intersects |
| [0x90000000, 0x93413800) | SCRATCH download buffer = the container itself | second domain read by shim before it is duplicated into owned memory | SCRATCH is never mapped into the ADT; XNU cannot see it after the copy; no lk2nd consumer writes inside it after `cmd_boot` (no decompress, no dtbo, no vbmeta on this build) |
| [0xA0000000, 0xB0000000) | owned XNU window (ADT dram-base/size) | mach text 0xa0000000, boot_args 0xa0b7c000, ADT 0xa0b7d000, RAMDisk copy 0xa0b84000 (+42,991,616), TrustCache 0xa3484000 (+3,875) | identical to boot2/manifest; end 0xa3484F23 < 0xb0000000 |

No overlap among the first three columns; the container's five domains occupy
pairwise disjoint intervals, and no domain intersects a live LK region.

## 5. What changes on the host side

1. `scripts/y35a/package_native.py`
   - `android_container(kernel, dt, second=b'', ramdisk=b'\0')`: four-domain
     builder; guards = Image-header magic, kernel end `<= 0x83200000`,
     `kernel_size <= 0x3180000` (patch pin budget), `ramdisk_size == 1`
     (patch pin condition, explicit error otherwise), total `<= 256 MiB`
     download budget, dt-entry sanity; `image_actual == len(image)` by
     construction; sha1 covers kernel/ramdisk/second/dt with length suffixes;
     every domain page-padded (V14.7's negative replica proved padding is a
     hard requirement). Old 50 MB budget constant replaced by the
     source-verified 256 MiB.
   - `build()`: rootfs is no longer `incbin`'d into `entry.S`; it is written
     as the second domain. A fixed-point loop resolves `second_off` (it
     depends on `len(entry3.bin)`, and `entry3.bin` embeds the SCRATCH
     address derived from it — `ldr =literal` width is value-independent, so
     the loop converges, verified in-container). The generated shim copies
     the rootfs with `ldr x0,=0x90AE3000` instead of `sidecar_0`, and the ADT
     `/chosen/memory-map RAMDisk` entry keeps pointing at the *destination*
     0xa0b84000 (XNU contract unchanged).
   - The entry-source template is factored into `generate_entry_source()` so
     the tests can assert the shim contract without a cross-compiler.
   - `probe_emmc.py` / `readback_native.py` call sites keep working through
     the new keyword defaults (they pass no second domain; geometry stays
     header+kernel+1B-ramdisk+dt, the exact boot1-era shape).
2. `out/y35a/ios12-boot3/entry.S` (build output; new file): shim copy logic
   change is only the RAMDisk source address (SCRATCH second domain) — all
   destinations, sizes, segment table, args/adt/tc copies, magic writes and
   the `br` to the kernel entry are byte-for-byte the boot2 logic.
3. `tests/test_native_pack.py` (new, tracked): a from-source re-implementation
   of every gate model above (constants re-quoted, not imported from the
   packer, so the tests can contradict the implementation), asserted against
   synthetic four-domain containers, the real minified QCDT built from the
   device stock boot.img, and the shipped `boot3.img` artifact.

## 6. What would have been wrong (rejected options, kept for the record)

- gz 42 MB in ramdisk domain: no lk2nd decompress (fact 1), breaks pin
  (fact 2), 0x82000000 + 43 MB tramples splash (fact: 0x82000000..0x849C0000
  covers 0x83200000), and XNU 4570 has no md(4) in this drop
  (`/work/xnu-4570/bsd/dev/` has no `md.c`) so a Linux-style initrd has no
  consumer either. Rejected.
- Bare FDT in dt domain with `dt_size != 0`: `copy_dtb` calls
  `dev_tree_validate` first, which rejects anything not `QCDT` —
  returns -1, then `dev_tree_appended` scans the kernel domain for FDT
  magic at `DTB_OFFSET` (0x2C = upper half of `res5` = 0 in our header →
  scans at kernel start → fails) → `dtb not found`. The brief's phrasing
  "dt domain carries a bare FDT" is corrected by source: it must be a QCDT
  table; `select_device_dt` already emits exactly that. Rejected variant
  of the same idea: `dt_size=0` + appended FDT at the tail of the kernel
  domain with header byte 44..47 patched to the append offset would also
  pass (aboot.c:3449-3467 special case "only one appended non-skales DTB,
  select it"), but it grows the kernel domain by 176 KB for no benefit and
  couples the shim's image_size to the DTB — kept as plan B only.
- Second domain copied by lk2nd somewhere: `cmd_boot` has no second-domain
  handling on this path (`aboot.c:3168-3500` reads second only for size
  arithmetic), so "let lk2nd place it" is not available without a reflash.

## 7. Artifact record (filled by the build step)

- entry3.bin: `out/y35a/ios12-boot3/entry.bin` (path), sha256, length
- boot3.img: `out/y35a/ios12-boot3/boot3.img`, sha256, length
- inputs: kernel `out/y35a/ios12-kernel.noctf` sha256
  5fd4e6b5f7fa10e1b2cc9323ac5802833c15479fce5c67068f2ba8837fdcdc94,
  rootfs (host `out/y35a/ios12-root.work/ramdisk-hfs.raw`) sha256
  54c07a60…, trustcache sha256 695f912e…, stock-boot sha256 92611f87…
- lk2nd rebuild needed for boot3: **NO** (patch v1 pin fires, section 3
  step 6). Device step left to main control: single
  `fastboot -s efff9d92 boot boot3.img` attempt once the user orders it.

## 8. Optional patch v2 (NOT needed for boot3; only for a future real-ramdisk variant)

For the record, `y35a-xnu-layout-v2.patch` would widen the pin to accept a
real-size ramdisk by matching `text_offset==0x80000 &&
kernel_size<=0x3180000 && cmdline=="y35a-native-xnu-experimental"` without
the `ramdisk_size==1` clause, and pinning `ramdisk_addr=0x8f800000`… — that
address sits in LK's own shadow zone; a sound v2 would need its own
meminfo change and a reflash + re-verification pass. Marked: awaiting main
control decision, deliberately not produced as a buildable patch now,
because boot3 passes with the resident bootloader as-is.

## 6. 产物实测记录(2026-11-06 23:59,主机侧)

- `out/y35a/ios12-boot3/boot3.img` 54,618,112 B,sha256
  d7640a423935b6dbe9322b0b8bbcdac305d25428ff87e0a8ac8bd5439cb74ad6
  (容器 manifest 同值;输入 kernel 5fd4e6b5…,ramdisk 54c07a60…,
  trustcache 695f912e…)。
- 几何: kernel 域 11,439,696 B(<0x3180000 ✓ pin 条件), ramdisk 域 1 B,
  second 域 42,991,616 B @SCRATCH+0xaea000(逐字节 == P4 staged
  ramdisk-hfs.raw ✓), dt 域 magic QCDT ✓;second_addr 字段
  0x90aea000 与 shim 立即数收敛一致。
- 产物闸: BOOT3_IMG/BOOT3_MANIFEST 注入后 14/14 全绿(0 skipped)。
- 纠正一条历史误读: `ios12-boot2/entry.bin` 54,431,312 B 是
  kernel-packed.macho(kernel+43MB cpio.gz incbin),不是编译 shim;
  boot2 的 shim 只有 ~11.4MB。boot2 死于 copy_dtb 与 V14.7 记录一致。
- ramdisk 域基准选择: 容器旧 /work/ramdisk-hfs.raw(4690a936, 11-06
  03:17)与主机 P4 权威件(54c07a60,staging evidence)哈希分叉,同体积
  42,991,616 B;两件生成链未逐一追溯,HFS+ repack 本就非字节可再现
  (evidence 自记)。boot3 以主机件为准(docker cp 为
  /work/ramdisk-boot3.raw,不动旧件)。首 boot 若挂载异常,先比两件
  HFS 超级块/卷 UUID 再查闭包。
