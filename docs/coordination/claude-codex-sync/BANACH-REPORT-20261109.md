# Banach Sidecar Audit: Y35A Boundary Evidence

Date: 2026-11-09

Scope: read-only audit of the current UniXNU Y35A hardware/upstream evidence and Claude's interpretation of the XNU startup boundary. No device command was run in this audit. No existing source, evidence, or coordination file was modified.

## Executive conclusion

Claude's stronger statement that the current `Y35AXNU2` or legacy carrier proves XNU reached `PE_init_panicheader()` is unsupported. The evidence proves three weaker facts:

1. The RAMBoot shim wrote `Y35AXNU2` immediately before `br x1`, so the shim reached the XNU entry branch and recorded the packaged kernel generation.
2. The readback probe executed and produced a fresh carrier when its CNTVCT witness changed.
3. The older 2026-11-06 `panic.raw` reached a deep path ending in `pid 1: launchd`, but that is a different kernel/image generation and cannot be transferred to phase-r11 or the short 2026-11-09 boots.

There is no current XNU-owned `FUNK`/EPH header observation for the phase-r11 question. The legacy probe also aliases the XNU `pram` window: its `STAGE_BASE=0x859e0000` is the same interval declared by the ADT `pram` node. That probe can destroy the EPH header and panic text before LK uploads them.

The phase-r11 plus minimal-boundary pair is the correct next experiment in principle, but the offline evidence chain still has one contract gap before it should be run: the exact artifact/source provenance and the verifier semantics must be frozen together. The kernel-only phase gate passes and the minimal transport gate passes when the existing LK source range is correctly declared as `0x11000`; the older capture-layout gate still rejects the same minimal manifest because it treats the whole LK source interval as a write interval.

## Current snapshot

The coordination file `CURRENT.md` says it was reconciled at `a58d8f6`, but the actual worktree HEAD is `448de3a` (`docs(evidence): ... TLMM stride ...`). The worktree is dirty:

- modified: `scripts/build-xnu-4903-kernel.py`, `scripts/y35a/probe_rmi.py`, `scripts/y35a/readback_native.py`, `tests/test_readback_names.py`, coordination files;
- untracked: phase patches, verifier scripts, tests, and evidence files;
- nested driver worktrees are present.

The phase-r11 artifact files currently hash as recorded in their own manifest:

| Artifact | Current SHA-256 | Status |
|---|---|---|
| `out/y35a/ios12-kernel-phase-r11/kernel-packed.macho` | `619a6ea03be230529d4eeeaac64a3fd9d44cef8e1d302255a6bd5f70dd70381a` | present; kernel-only phase gate passes |
| `out/y35a/ios12-boot3-phase-r11/boot3.img` | `a98c0b26340b503d05414c2cf9586e52725ffa0e99cb420a63619931dad47e99` | manifest image hash matches |
| `out/y35a/readback-probe-20261109-min-r9/readback-probe-not-xnu.img` | `9466188a5b3f91fedb53525823dea7ced471f5ad1d7e69b1bf4ddbf462d9a405` | manifest image hash matches |

The current minimal manifest file SHA is `488e0c847497ef782cffdcdb25a785fa85dcf929`, while `PHASE-R11-MINIMAL-EXPERIMENT-20261109.md` records `0ae59dac07ed1a7accd8f26a47123633084c6c95c30da3cad9cd64a54d1d4fea`. The image hash is unchanged, but the manifest provenance is not. The exact manifest and dirty source state must be recorded before a new run.

## Direct measurements

### Shim and carrier ownership

The RAMBoot shim writes `Y35AXNU2` at physical `0x859f0000`, writes the entry address at `+0x18`, then branches to the XNU entry at `br x1`:

- `scripts/y35a/package_native.py:74-91` writes the earlier shim marker and watchdog register;
- `scripts/y35a/package_native.py:126-139` writes `Y35AXNU2`, entry, then executes `br x1`.

This is a shim-owned event. It is before any XNU C code and before any panic code.

The readback probe's `Y35ARD01` is likewise probe-owned. `scripts/y35a/readback_native.py:409-423` writes the marker, kernel stamp, CNTVCT, and CPU registers into the stage area. The minimal probe's `Y35ARD02` is written by `minimal_boundary_entry_source()` at the report page, not by XNU (`readback_native.py:513-529`).

The classifier makes this ownership distinction explicit: `Y35ARD01` and `Y35AXNU2` are checked before any EPH search (`scripts/y35a/capture_format.py:53-66`).

### Legacy r7 carrier result

`R7-AUDIT-20261109.md:15-20` records that the three r7 captures differ only in the CNTVCT witness and the `Y35AXNU2` handoff stamp. The symbol-addressed carrier windows are otherwise byte-identical. `CURRENT.md:20-22` further records that the `_BootArgs` carrier equals static Mach-O file bytes at that VA, not an LK-written runtime boot-args structure.

That is evidence of a live probe chain and a lack of observed runtime mutation in those windows. It is not evidence that an XNU panic header was written.

### EPH source contract

The XNU source used by the build container is commit `494ffe1c29d37ca720c37328feb83069c9641b67`, tag `xnu-4903.270.47`.

The packed XNU EPH header is defined in `/work/xnu-4903/osfmk/kern/debug.h:286-322`. Its identifying field is `eph_magic`, whose valid panic value is `EMBEDDED_PANIC_MAGIC = 0x46554E4B` (`FUNK`, bytes `KNUF` in memory). The offsets and lengths at the following fields are meaningful only after that magic is present.

The panic header is written by `PE_init_panicheader()` in `/work/xnu-4903/pexpert/arm/pe_init.c:564-579`; the function clears the header, sets the panic-log offset, writes `FUNK`, and sets the version. That is the required XNU-owned proof for the panic-header claim.

The same source's `check_for_panic_log()` is at `/work/xnu-4903/pexpert/arm/pe_init.c:73-137`. It is called as the first action in `PE_create_console()` and unconditionally clears the mapped panic region after the `SHMC`/`BTRC` early returns and optional `FUNK` diagnostic. Therefore, a probe that writes into the same `pram` interval cannot preserve a clean EPH witness.

### Stage/pram alias

The ADT declares `pram` at `0x859e0000..0x859f0000` (`scripts/y35a/make_adt.py:51`). The legacy readback probe uses `STAGE_BASE=0x859e0000` (`scripts/y35a/readback_native.py:28-31`) and stages records from `stage+0x40` through the pram-backed range. The overlap is independently documented in `CAPTURE-TRANSPORT-AUDIT-20261109.md:17-20`.

Consequences:

- absence of `FUNK` in a legacy capture is not probative;
- the legacy probe can overwrite the XNU panic header and text before LK uploads them;
- old EPH-looking values such as `0xa9/0xa37` must be decoded only from a real `FUNK` header, never from fixed carrier positions.

### Phase-r11 and minimal-boundary offline checks

The phase kernel passes the instrumentation check when the check is run against the kernel artifact alone:

```text
python3 scripts/y35a/verify_phase_instrumentation.py \
  --kernel out/y35a/ios12-kernel-phase-r11/kernel-packed.macho
=> {"ok": true, "failures": []}
```

The optional manifest path is not schema-compatible with the boot image manifest. Running the same verifier with `--manifest out/y35a/ios12-boot3-phase-r11/manifest.json` reports `manifest early-fault-record layout is not offset 64, size 384`, because that manifest records `early_fault_record_physical` and `early_fault_record_bytes`, not a `records` array. This is a verifier contract issue, not proof that the phase kernel lacks instrumentation.

The minimal transport gate passes when the existing LK upload source is declared correctly as `0x11000` bytes:

```text
verify_readback_transport.py --mode minimal-boundary --lk-stage-size 0x11000 ...
=> {"ok": true, "failures": []}
```

The minimal probe's actual writes are confined to the report page above pram; it snapshots `0x859e0000..0x859f0000` to `0x95000000..0x95010000`, writes `0x859f0000..0x859f1000`, then restores pram before reset (`readback_native.py:481-570`).

The older `verify_capture_layout.py` still reports failure for the same minimal manifest because it rejects the entire LK source interval `0x859e0000..0x859f1000` as overlapping pram, even though minimal mode declares only the report page as the write allocation. Its current failure is therefore a stale gate model, not a demonstrated minimal-probe geometry failure.

## Source and hardware cross-checks

### Device DT facts

The cached stock DT transcription gives the following direct facts:

- `pmx_i2c_5` uses pins 19 and 18 with function 2 and drive strength 2 (`evidence/y35a-20261102/dtb10-stock.dts:1236-1255`);
- `i2c@78b9000` is `qcom,i2c-msm-v2`, SE `0x78b9000/0x600`, shared BAM `0x7884000/0x23000`, SPI 99, 19.2 MHz input, 400 kHz output (`dtb10-stock.dts:6834-6855`);
- child `rmi_i2c@20` is `synaptics_3202`, address `0x20`, reset GPIO 12, IRQ GPIO 13, active-low attention (`dtb10-stock.dts:6857-6879`).

These facts establish the intended hardware topology. They do not prove the bus is configured at the lk2nd-to-XNU handoff.

### lk2nd source facts

The container snapshot `/work/lk2nd-y35a-codex` has content hashes:

- `platform/msm8916/include/platform/iomap.h`: `9d6136aaf99b2d9fee...`;
- `platform/msm8916/acpuclock.c`: `98552d12e30ebb811...`;
- `lk2nd/hw/gpio/tlmm.c`: `f4952a988c63f1308...`.

The exact source facts are:

- `iomap.h:97-103`: TLMM per-pin config is `0x01000000 + pin*0x1000`, and input/output is config `+4`;
- `iomap.h:121-128`: the local MSM8916 lk2nd map defines BLSP1 QUP2 clock registers at `GCC + 0x3010/+0x3014/+0x3018` and QUP4 at `GCC + 0x5000/+0x5004/+0x5020`; it does not provide a QUP5 clock macro;
- `acpuclock.c:485-515`: `clock_config_blsp_i2c()` accepts only QUP IDs 1 and 3, which map to QUP2 and QUP4, and asserts for other IDs;
- `tlmm.c:15-71`: config bits are pull, function, drive strength, OE, and hysteresis; input level is read from the separate `GPIO_IN_OUT_ADDR(pin)` register.

This supports the narrow hardware conclusion from the T0.2 run: lk2nd did not configure QUP5 in its normal I2C clock path. It does not identify the QUP5 GCC gate address.

### Local QUP5 driver boundary

The UniXNU catalog marks `QcomQupI2c` as an MSM8916 QUP5 driver, but `verified_devices=[]` (`components.toml:533-551`). Its current driver maps only the SE window and calls the QUP core divider setup (`drivers/QcomQupI2c/NativeQupI2c.cpp:135-165`). The core resets/configures the SE and writes `SE_I2C_CLK_CTL` after state transitions (`drivers/QcomQupI2c/I2cCore.h:138-160`, `:184-224`), but it does not configure TLMM or an external GCC QUP5 clock gate.

The two independent T0.2 boots therefore support this limited statement: the handoff state is not ready for a QUP5 transaction. They do not prove the S3202 is absent, and `clkctl_after=0` alone does not prove a GCC gate failure because the transaction stopped while `SE_STATE.VALID` was not established.

### Upstream facts

The local upstream survey records these source facts:

- mainline `i2c-qup.c` matches `qcom,i2c-qup-v2.2.1`, not the stock `qcom,i2c-msm-v2` (`upstream-survey/input-sensors.md:122-146`);
- the mainline MSM8916 DT uses the same `i2c@78b9000` address and BAM channel pair 12/13, with GCC clock phandles (`input-sensors.md:147-168`);
- mainline has `drivers/clk/qcom/gcc-msm8916.c` and `drivers/pinctrl/qcom/pinctrl-msm8916.c`, but the actual source snapshots are not present locally (`upstream-survey/core-soc.md:47-83`, `:468-499`);
- the survey records a same-SoC same-vendor mainline board and a public RMI4 path, but the stock `synaptics_3202` compatible is not a mainline match (`input-sensors.md:102-118`).

The useful offline hardware check is therefore to recover or locally snapshot the exact upstream `gcc-msm8916.c` and `msm8916.dtsi` revisions cited by the survey, then map the stock DT clock phandles `0x8caa5b4f` and `0xacae5604` to concrete QUP5 command/config/CBCR addresses. Do not infer those addresses from MSM8952 or from the QUP2/QUP4 gaps in lk2nd.

## What Claude should stop claiming

- Stop calling `Y35AXNU2` an XNU phase marker, EPH header, or proof of `PE_init_panicheader()`.
- Stop reading `Y35ARD01`/legacy record offsets as XNU-owned panic evidence.
- Stop using the 2026-11-06 `launchd` panic as proof of the 2026-11-09 phase-r11 or legacy short-return boot.
- Stop using the old `attn` samples as GPIO13 line evidence; the prior probe used the wrong TLMM stride. The corrected GPIO13 input address is `0x01000000 + 13*0x1000 + 4 = 0x1000d004` (`heartbeat-20261109-123x-tlmm-stride-adjudication.md:39-45`).
- Stop treating T0.2 timeout as evidence that the S3202 is absent. It proves the SE did not reach a valid state before the identity transaction.
- Stop changing VA-to-PA translation. The r7 audit found the flat formula agrees with per-segment placement for all checked carriers, including `__BOOTDATA` stacks (`LOG.md:90-110`, `R7-AUDIT-20261109.md:15-28`).
- Stop broad GPU, IIG, userland, and full driver work as the active diagnosis. None can explain the unresolved earliest XNU boundary.
- Stop borrowing QUP5 clock offsets from another Qualcomm generation. The local lk2nd source does not provide that mapping.

## Smallest remaining gap

The smallest runtime gap is one exact-hash, same-power-cycle capture of the phase-r11/minimal-boundary pair with these expected ownership markers:

- body `0x10000`: phase shim `Y35AXNU2` with the phase kernel stamp;
- body `0x10040`: minimal probe `Y35ARD02`;
- body `0x10128`: XNU phase marker, one of `arm_vm_init`, `panic_init`, `PE_create_console`, or zero;
- body `0x00000..0x0ffff`: restored pram snapshot, where any `FUNK` header is XNU-owned evidence rather than probe-owned bytes.

Before that run, the offline contract must be made reproducible: record the actual current minimal manifest hash (`488e0c847497ef782cffdcdb25a785fa85dcf929`), reconcile the stale `verify_capture_layout.py` minimal-mode failure, and record the dirty builder/patch source hashes. The current phase/minimal source is not a clean committed pair: phase patches are untracked and `scripts/build-xnu-4903-kernel.py` / `scripts/y35a/readback_native.py` are modified.

If the marker is zero after a valid capture, the next experiment should not be repeated unchanged. Add one earlier XNU marker around `arm_init` entry or `PE_init_platform(FALSE)` and then one pexpert boundary at a time. The current three markers begin too late to distinguish `pe_identify_machine`, interrupt mapping, timer setup, or debug setup.

## Recommended offline work and device decision

Priority 1: freeze and audit the exact phase-r11/minimal pair offline. Use the kernel-only phase gate, the minimal transport gate with LK source size `0x11000`, and a corrected minimal-aware layout interpretation. Verify the generated `entry.S` ordering: full pram snapshot before writes, report at `0x859f0000`, restore before reset, and marker raw offset `0x10128`.

Priority 2: close the QUP5 clock-map question offline from a concrete upstream source snapshot. The DT and lk2nd sources establish the bus and pin facts, but not the QUP5 GCC gate address. This is the only current hardware-side unknown worth resolving before writing a cold-read path.

I do not recommend a new device experiment yet. After Priority 1 is frozen and the minimal-aware gate discrepancy is resolved, I do recommend exactly one new RAM-only phase-r11/minimal-boundary run with the hashes in `PHASE-R11-MINIMAL-EXPERIMENT-20261109.md`, subject to a fresh per-experiment authorization. No legacy readback image should be used for boundary conclusions.

## Short handoff to Claude

`Y35AXNU2` is shim-owned at `package_native.py:131-139`; `Y35ARD01/02` are probe-owned. Only `FUNK` at the packed XNU EPH header, or an XNU phase marker in the restored minimal report, can support the panic-header claim. The phase-r11 kernel hash is `619a6ea0...`; boot image `a98c0b26...`; minimal probe `9466188a...`. Kernel-only phase verification passes. Minimal transport verification passes with LK source range `0x859e0000..0x859f1000`. The old layout gate still falsely rejects minimal mode because it treats the source range as a write range. Freeze current manifest/source provenance before any boot. Do not infer S3202 absence from the T0.2 timeout; first resolve QUP5 GCC mapping offline or treat it as unknown.
