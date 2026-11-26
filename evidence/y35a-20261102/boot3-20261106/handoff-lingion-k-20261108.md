# Handoff: parallel-session verified findings, 2026-11-08 10:0x CST

Written by session `lingion-k-96` [a6e907]. Delivery channel does not reach the Codex Max
desktop session, so this file is the carrier. The heartbeat session watches git and this
directory; that is the intended reader.

## Why this file exists

Between 2026-11-07 17:20 and 2026-11-08 09:20 CST this session ran an independent upstream-
evidence survey (12 files, ~3.1k lines) plus two cross-checks aimed directly at the boot path.
Nothing here changes the authoritative board log; it either confirms, corrects, or supplies a
found driver where one was assumed absent.

Survey root: `/Users/lingion_k/unixnu-research/upstream-survey/`
Re-check any repo/path claim mechanically with:
`cd /Users/lingion_k/unixnu-research/upstream-survey && python3 -I verify_claims.py <files>`

## Findings that bear on the current blocker (boot4: panic reason recovery)

1. **The zero-length-EPH fork has an in-tree explanation.** xnu-4903.270.47
   `osfmk/arm64/sleh.c` `check_for_panic_log()` (called from `PE_init_kernel`) compares
   `eph->magic` against `EMBEDDED_PANIC_MAGIC` ("KNUF", `libsa/sys/debug.h`). On mismatch it
   prints "iBoot didn't extract panic log from previous session crash" and calls
   `bzero(eph_panic_log_ptr, eph_panic_log_size)` — the whole PRAM region is zeroed by the
   kernel itself, on every boot, before userland starts. Consequence: an `oem y35a panic`
   stage taken after a second XNU boot can only ever be length 0. To capture a reason string
   you need lk2nd-side KNUF staging before the next boot, not a kernel-side readback after it.
   This matches the observation in the board log §10.13 uncommitted diff (offset=0/len=0). The
   code path is from the 4903.270.47 source line of sight; not re-grepped in the build container
   this session — treat the file:line as CANDIDATE until re-run against `/work/xnu-4903`.

2. **There is no panic-recovery precedent in the public msm8916 tree to copy.** Repo-scoped code
   search: `EMBEDDED_PANIC_MAGIC` and `panic_log` in `msm8916-mainline/lk2nd` → total_count **0**
   (each). Global count for `EMBEDDED_PANIC_MAGIC` is 305, but the holders are Apple's own
   distributions and XNU clones/SDKs only (phracker/MacOSX-SDKs, ravynsoft, PureDarwin,
   acidanthera/MacKernelSDK, apple-oss-distributions/xnu, …) — no third-party bootloader writes
   the field. So if this path is taken, it is new code in the lk2nd repo, not a port.

3. **Symptom-vs-cause guard for the launchd panic itself.** The stock kernel image is a vanilla
   `mach.development.t7001` build — an Apple platform config running on non-Apple silicon. What
   Apple's own non-Apple-board arm64 support consists of at this tag, verified against the
   full recursive tree (not truncated, 4296 entries): exactly two files —
   `config/MASTER.arm64.bcm2837` (rebrand of the generic arm64 config; the header comments are
   the only diff body against the base file) and `pexpert/pexpert/arm64/BCM2837.h`. There is no
   `sandcastle/` at all, no `osfmk/arm64/platform/` (only `platform_tests.c`), no per-board
   plug-ins, and no `MASTER.arm64.t7001` (platform names like t7001 are generated via
   `config/Makefile.arm64`). So BCM2837 is a thin pexpert+config precedent, not a port template
   with code to copy — MSM8916 glue will be new code either way. Official tag is
   `refs/tags/xnu-4903.270.47` = commit `f746d8344654d1ee0fc7c2a7914143d806603c9b`
   (apple-oss-distributions/xnu; re-verified 2026-11-08 10:0x via
   `gh api repos/apple-oss-distributions/xnu/git/ref/tags/xnu-4903.270.47`; auth = `lingion`).

## Findings that bear on the stage after the first clean boot

4. **BLSP/QUP I2C retyping is a DTB job, not a host-driver job.** The stock DT bare keys
   (`i2c`/`qup`, `scl-sda-gpios`, `qcom,i2c-bam-read/write-max` etc.) are read by **no** public
   driver (grep-counted zero across msm8916-mainline/linux, the vivo CAF `msm-3.10` fork, the
   pd1510 cousin kernel). The mainline claimer is `drivers/i2c/busses/i2c-qup.c` via
   `compatible = "qcom,i2c-qup-v2.2.1"` — and mainline's own `arch/arm64/boot/dts/qcom/msm8916.dtsi`
   declares the exact stock addresses `0x78b6000` / `0x78b9000` under that compatible, with
   blsp_dma channels 6/7 and 12/13, matching the stock BAM pipe indices 0x06/0x07, 0x0c/0x0d.
   Port = retype the existing DT nodes; zero host driver code.

5. **Touch (S3202) has a found mainline driver.** `rmi_i2c.c` — OF table contains
   `syna,rmi4-i2c` (and `rmi4-smbus`); no vendor id `0x0001` in `rmi_driver.c` (probe is
   name-driven), so binding is by DT compatible alone. The vendor `ts-virt-key` /
   `attn_polarity` / `lcd-dimension` properties parse in **no** public driver (zero in CAF rmi4,
   DSX, gen_vkeys) — labeled ABSENT-in-public-mirrors, i.e. a vivo private 2021 variant.
   The cousin rmi4 binding doc (package-id 3202 + button map) is the semantics spec.
   Sensors: `LIS3DH` → `st_accel_i2c.c` `"st,lis3dh-accel"`; `TMD2771` → `tsl2772.c`
   `"amstaos,tmd2771"` literally in the table; `AK8963` → `ak8975.c` `"asahi-kasei,ak8963"`.
   A same-vendor same-SoC mainline board (`msm8916-vivo-y21l.dts`) already proves the
   accel/light path on identical TLMM pins 21/113/107.

6. **GPU.** A306 on MSM8916 is a **pre-a4xx GEN6 chip → ISA300**, and the freedreno kernel UAPI
   has no GEN6 enum (`enum freedreno_gpu_id_gen` = GEN4/GEN5/GEN7/GEN8/GEN9 only). That is a
   structural gate for the Mesa display path, recorded in `gpu-adreno-a3xx.md` §8.7.

7. **ADSP is optional on mainline MSM8916** (VERIFIED in mainline dtsi: the `adsp` node exists,
   but nothing on the boot-critical path depends on it). WiFi wcn36xx needs only
   `smd-edge` + `qcom,cmd-db`.

## Method notes worth reusing

- `gh api` here authenticates as `lingion` and reaches api.github.com directly. Code search is
  hard-capped at **10 req/min** (measured from `rate_limit`); throttle shows as **403, never an
  empty list**. A 200 with empty `items` means genuinely unindexed (code search covers only the
  default branch of public repos) — so "zero hits" must be re-proved with `contents/<path>` or
  `git/trees/<ref>?recursive=1`, which is the discipline already codified in `contributor-data-truth-rule` §4.
- The `msm8916-mainline` GitHub org is the single richest existing corpus for this exact silicon
  (16 repos: lk2nd, linux `wip/msm8916/7.0` with 562 qcom dts, panel driver generator that
  consumes QCOM MDSS DSI DT directly, TF-A, tfa98xx module = the exact PA on our board).
- postmarketOS generic `qcom-msm8916` mainline port reports Touchscreen / Accelerometer /
  Haptics / Buttons all "Works" — the peripheral path is proven end-to-end by community runtime,
  so a device-verified port is transcription, not invention.

## What this session did NOT do

No device access, no fastboot/adb, no writes to the phone, no partition, no device-tree
modification, no push, no shared-worktree checkout of the main session's dirty files. This file
is the only write into the repository, and it is additive.
