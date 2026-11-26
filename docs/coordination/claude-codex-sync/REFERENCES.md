# UniXNU local reference audit

Audit date: 2026-11-23
Scope: read-only inspection of /Users/lingion_k/unixnu-research and the explicitly requested local reference paths.
Excluded: device access, fastboot, builds, containers, project ledgers, repository edits, recursive scans of external volumes.
Evidence basis: filesystem paths, local Git metadata, README/license files, and existing build-entry source names.

## Summary

- XNU 4903 source: FOUND.
- XNU 4570 source: FOUND.
- Linux MSM8916 sparse upstream source: FOUND.
- lk2nd MSM8916 source: FOUND in three dated snapshots; all resolve to the same commit.
- UniXNU main repositories: FOUND.
- Independent UniXNU driver and kit repositories: FOUND.
- MSM8916 UniXNU SoC scaffold: FOUND, but no Git repository/commit.
- UniXNU QEMU device tree: FOUND, but no Git repository/commit.
- wcn36xx prior-art source: FOUND as a directory, but no Git repository/commit and no license file was established.
- No separate lk2nd source outside the dated snapshots was found.
- No separate Linux MSM8916 checkout outside the pinned sparse snapshot was found.

## XNU references

### XNU 4903 / iOS 12 baseline

- Path: /Users/lingion_k/unixnu-research/UniXNU-y35a/upstream-refresh/2026-11-11/sources/xnu-ios12/repo
- Commit: 494ffe1c29d37ca720c37328feb83069c9641b67
- Tag/commit description: xnu-4903.270.47
- Remote: https://gh.qdp.qzz.io/apple-oss-distributions/xnu.git
- License: Apple Public Source License 2.0, /Users/lingion_k/unixnu-research/UniXNU-y35a/upstream-refresh/2026-11-11/sources/xnu-ios12/repo/APPLE_LICENSE
- Reusable entry points:
  - Generic XNU build: make SDKROOT=<sdkroot> ARCH_CONFIGS=<arch> KERNEL_CONFIGS=<variant>
  - Native Y35A build contract: /Users/lingion_k/unixnu-research/UniXNU-y35a/scripts/build-xnu-4903-native.py
  - Generic/Linux-oriented builder: /Users/lingion_k/unixnu-research/UniXNU-y35a/scripts/build-xnu-4903-kernel.py
  - Source build rules: Makefile, makedefs, ARCH_CONFIGS=ARM64, MACHINE_CONFIGS=T7001, KERNEL_CONFIGS=DEVELOPMENT
- Reuse note: this is the pinned clean XNU 4903 source used by the current Y35A research tree. It is the relevant XNU source reference.

### XNU 4570 historical reference

- Path: /Users/lingion_k/unixnu-research/xnu-4570
- Commit: 06f694a16ebc1dd153f6d037ad5c615166c93369
- Commit description: xnu-4570.51.1
- Remote: https://gh.qdp.qzz.io/apple-oss-distributions/xnu.git
- License: Apple Public Source License 2.0, /Users/lingion_k/unixnu-research/xnu-4570/APPLE_LICENSE
- Reusable entry points: top-level Makefile, SETUP/Makefile, config/Makefile, tools/remote_build.sh
- Reuse note: historical comparison only. Current project memory and local documentation identify XNU 4903 as the iOS 12.4.1 research baseline.

## Linux MSM8916 reference

### Pinned sparse Linux snapshot

- Path: /Users/lingion_k/unixnu-research/upstream-snapshot/linux-7475ea8-msm8916/repo
- Commit: 7475ea8b58616b33c04afb976cf0fbaad9dd63fb
- Reported source version: Linux 7.4-rc2
- Remote: https://gh.qdp.qzz.io/torvalds/linux.git
- License: GPL-2.0 WITH Linux-syscall-note, with additional per-file licenses; commit object contains COPYING.
- Sparse paths present:
  - arch/arm64/boot/dts/qcom/msm8916.dtsi
  - arch/arm64/boot/dts/qcom/pm8916.dtsi
  - drivers/clk/qcom/gcc-msm8916.c
  - drivers/clk/qcom/reset.c and reset.h
  - drivers/clk/qcom/clk-branch.c and clk-branch.h
  - drivers/pinctrl/qcom/pinctrl-msm8916.c
  - drivers/i2c/busses/i2c-qup.c
  - drivers/input/rmi4/rmi_i2c.c
  - include/dt-bindings/clock/qcom,gcc-msm8916.h
  - Documentation/devicetree/bindings/i2c/qcom,i2c-qup.yaml
- Reusable entry points: source-level DTS and driver references; no complete kernel build entry is present in this sparse snapshot.
- Reuse note: authoritative local hardware-map reference for the MSM8916 scaffold. It is not a full Linux checkout.

### UniXNU MSM8916 SoC projection

- Path: /Users/lingion_k/unixnu-research/UniXNU-msm8916-common
- Commit: NONE-FOUND; directory is not a Git repository.
- License: NONE-FOUND in this directory.
- Reusable entry points:
  - dts/msm8916.dtsi
  - configs/msm8916.config
  - soc.toml
  - patches/xnu/series
  - README.md
- Reuse note: research scaffold only. README states it is not a working port, has not been booted on hardware, and is derived from the pinned Linux MSM8916 source. AGENTS.md requires hardware facts to be reverified against the cached Linux DTS before edits.

## lk2nd references

### Dated snapshots

All three paths below contain the same Git commit and the same upstream repository identity.

- Path: /Users/lingion_k/unixnu-research/UniXNU-y35a/upstream-refresh/2026-11-10/sources/lk2nd-msm8916-mainline/repo
- Commit: cf45aefd22d744b2bf9b39455afae697ce430063
- Snapshot note: source directory also has SNAPSHOT.txt

- Path: /Users/lingion_k/unixnu-research/UniXNU-y35a/upstream-refresh/2026-11-11/sources/lk2nd-msm8916-mainline/repo
- Commit: cf45aefd22d744b2bf9b39455afae697ce430063
- Snapshot note: source directory also has SNAPSHOT.txt

- Path: /Users/lingion_k/unixnu-research/UniXNU-y35a/upstream-refresh/2026-11-20/sources/lk2nd/repo
- Commit: cf45aefd22d744b2bf9b39455afae697ce430063
- Remote: https://gh.qdp.qzz.io/msm8916-mainline/lk2nd.git
- Commit description: dts: msm8974: Add Samsung Galaxy S5 (SM-G900M)
- License: mixed open-source tree. Top-level LICENSE states original LK MIT, substantial LK code BSD-3-Clause with non-infringement language, and additional component licenses. lk2nd-specific code is BSD-3-Clause in lk2nd/LICENSE; GPL, Apache-2.0, and MIT files are also present.
- Reusable entry points:
  - Project definition: project/lk2nd-msm8916.mk
  - Target: msm8916
  - Build contract: top-level makefile
  - Typical form from README: make TOOLCHAIN_PREFIX=arm-none-eabi- lk2nd-msmXXXX; for this tree use the MSM8916 project target exposed by project/lk2nd-msm8916.mk.
  - Expected outputs: build-<project>/lk.bin, lk, and lk_s.elf
  - Source areas: lk2nd/, project/, target/, platform/, scripts/
- Reuse note: this is the only local lk2nd source tree found. The other local lk2nd matches are dated copies of the same commit, not separate revisions.

## UniXNU main repositories

### Current Y35A research checkout

- Path: /Users/lingion_k/unixnu-research/UniXNU-y35a
- Commit: 81a77736d32d980ad65fd1a55cafcf7ced3c0f10
- Remote: https://gh.qdp.qzz.io/UniXNU/UniXNU.git
- License: BSD-2-Clause-Patent, /Users/lingion_k/unixnu-research/UniXNU-y35a/LICENSE
- Working tree: dirty; existing modifications were observed and were not changed.
- Reusable entry points:
  - /Users/lingion_k/unixnu-research/UniXNU-y35a/scripts/build-xnu-4903-native.py
  - /Users/lingion_k/unixnu-research/UniXNU-y35a/scripts/build-xnu-4903-kernel.py
  - /Users/lingion_k/unixnu-research/UniXNU-y35a/scripts/build-unixnu.sh
  - /Users/lingion_k/unixnu-research/UniXNU-y35a/scripts/unixnu/package.py
  - /Users/lingion_k/unixnu-research/UniXNU-y35a/package/build.sh
  - components.toml, devices.toml, profiles/, drivers/, kits/

### Earlier UniXNU checkout

- Path: /Users/lingion_k/unixnu-research/UniXNU
- Commit: f0721e9745c45ad2600cd69c74730f1cca55d56a
- Remote: https://gh.qdp.qzz.io/UniXNU/UniXNU.git
- License: BSD-2-Clause-Patent, /Users/lingion_k/unixnu-research/UniXNU/LICENSE
- Working tree: dirty; existing modification observed in scripts/linux/setup-toolchain.py.
- Reusable entry points: same top-level package and driver structure, but this checkout is older than the Y35A research checkout.

### QEMU device repository

- Path: /Users/lingion_k/unixnu-research/UniXNU-qemu
- Commit: NONE-FOUND; directory is not a Git repository.
- License: BSD-2-Clause-Patent, /Users/lingion_k/unixnu-research/UniXNU-qemu/LICENSE
- Reusable entry points:
  - scripts/make-qemu-adt.py
  - scripts/run-qemu.py
  - scripts/qemu-input.py
  - scripts/build-os-root.py
  - scripts/build-darwinboot-efi.py
  - board.toml and configs/
- Reuse note: local work-in-progress device source; no commit can be used as provenance.

## Driver and kit assets

The following are independent Git repositories nested under the Y35A checkout. Parent build entry is the UniXNU component catalog plus scripts/unixnu/package.py and package/build.sh. License is read from each repository's LICENSE file; several repositories also carry file-level MIT or BSD headers.

### Drivers

- Adreno740 — path /Users/lingion_k/unixnu-research/UniXNU-y35a/drivers/Adreno740; commit 5c8c1453c67d6ef6b10ec43ab1f8fc570a2f33e1; license MIT; entry README.md, tests/, parent component/package builder.
- AdrenoMetal — path /Users/lingion_k/unixnu-research/UniXNU-y35a/drivers/AdrenoMetal; commit ce5e19e33e05e1873d38d818e23cabfe0ac708c3; license MIT; entry README.md, bridge/, tools/, shaders/.
- AppleKeyStoreState — path /Users/lingion_k/unixnu-research/UniXNU-y35a/drivers/AppleKeyStoreState; commit 42ff83e08b2265fe741d4adaf084bebe003452ba; license BSD-2-Clause-Patent; entry README.md.
- ArmCpu — path /Users/lingion_k/unixnu-research/UniXNU-y35a/drivers/ArmCpu; commit a05a364d4dfb024a6dd31fb9893d31ed48717bfa; license BSD-2-Clause-Patent; entry README.md, PORT-REPORT.md, tests/.
- ArmDTPlatform — path /Users/lingion_k/unixnu-research/UniXNU-y35a/drivers/ArmDTPlatform; commit 9ad4e865f9ea30d9612b9a4d63093150179d6637; license BSD-2-Clause-Patent; entry README.md.
- ArmVirtPlatform — path /Users/lingion_k/unixnu-research/UniXNU-y35a/drivers/ArmVirtPlatform; commit d1423a8bceac4be0478a93d9173587111c040084; license BSD-2-Clause-Patent; entry README.md.
- DarwinBoot — path /Users/lingion_k/unixnu-research/UniXNU-y35a/drivers/DarwinBoot; commit 3325e352d7df68a9f9ad74832ed94a6acbbd7390; license BSD-2-Clause-Patent; entry README.md, DarwinBootPkg/, Test/.
- GopFramebuffer — path /Users/lingion_k/unixnu-research/UniXNU-y35a/drivers/GopFramebuffer; commit 33e941a878dcf01b98dbd9160d798bd56e7551ea; license BSD-2-Clause-Patent; entry README.md, Test/.
- QcomGeniSpi — path /Users/lingion_k/unixnu-research/UniXNU-y35a/drivers/QcomGeniSpi; commit eac47baefe6a5d2368a70351e6ad1b6361bedbe2; license BSD-2-Clause-Patent; entry README.md, Test/.
- RamBlock — path /Users/lingion_k/unixnu-research/UniXNU-y35a/drivers/RamBlock; commit 25c57e0e9b68bf452dd1986914525edc9d2320bc; license BSD-2-Clause-Patent; entry README.md, Test/.
- SoftwareAES — path /Users/lingion_k/unixnu-research/UniXNU-y35a/drivers/SoftwareAES; commit 4a45326da5c2cd6fe6813d79ee43db20805628af; license BSD-2-Clause-Patent; entry README.md.
- VirtioMmioBlock — path /Users/lingion_k/unixnu-research/UniXNU-y35a/drivers/VirtioMmioBlock; commit 8ee3a5ab5a3726b0641990228346aec338246eaf; license BSD-2-Clause-Patent; entry README.md.
- VirtioMmioConsole — path /Users/lingion_k/unixnu-research/UniXNU-y35a/drivers/VirtioMmioConsole; commit 70253216890b2afcaa6333948726f896f84fc757; license BSD-2-Clause-Patent; entry README.md.

### Kits and reusable low-level assets

- AdrenoFirmware — path /Users/lingion_k/unixnu-research/UniXNU-y35a/kits/AdrenoFirmware; commit 20ad3d7aca14bd46aecab6335c780f5413fa054b; license BSD-2-Clause-Patent; entry README.md, AdrenoFirmware.c, tests.
- AdrenoPM4 — path /Users/lingion_k/unixnu-research/UniXNU-y35a/kits/AdrenoPM4; commit 282606b528b2595bc4274ea7490b62b323f35a5f; license MIT; entry README.md, AdrenoPM4.c, test_*.c.
- AirNir — path /Users/lingion_k/unixnu-research/UniXNU-y35a/kits/AirNir; commit b356371a74cd158c2902f4886f373ebb0f833a36; license MIT at repository level; some source files carry BSD-3-Clause headers; entry README.md, AirNir.h, tests/.
- ArmSmmu4K — path /Users/lingion_k/unixnu-research/UniXNU-y35a/kits/ArmSmmu4K; commit 3ba92451bd44bb742d11758fbfcd3a446ecad685; license MIT; entry README.md, ArmSmmu4K*.c/.h, tests.
- VerifiedRoot — path /Users/lingion_k/unixnu-research/UniXNU-y35a/kits/VerifiedRoot; commit def026642c6c6e71be0dea267d989df1d29ddc64; license BSD-2-Clause-Patent; entry README.md, src/, adapters/, tools/, tests/.
- XnuPrelink — path /Users/lingion_k/unixnu-research/UniXNU-y35a/kits/XnuPrelink; commit 41fb484912e4d9aa564f4f7583387d28ffa5a411; license BSD-2-Clause-Patent; entry README.md, tools/, patches/, evidence/.

### Local assets without an independent Git repository

- /Users/lingion_k/unixnu-research/UniXNU-y35a/assets
  - Found: logo-dark.svg, logo-light.svg.
  - Commit: inherited from parent only; no independent repository.
  - License: governed by parent checkout unless file-specific terms say otherwise; no separate asset license was established in this audit.
- /Users/lingion_k/unixnu-research/device-backups and /Users/lingion_k/unixnu-research/evidence
  - Found: lk2nd images, DTBs, logs, and other experiment artifacts.
  - Commit/license: NONE-FOUND for the individual artifacts.
  - Reuse: evidence/reference only; not source repositories.
- /Users/lingion_k/unixnu-research/wcn36xx-priorart
  - Found: source/listing directories.
  - Commit: NONE-FOUND.
  - License: NONE-FOUND in inspected top-level path.
  - Reuse: prior-art reading only until provenance and licensing are separately established.

## Provenance cautions

- Do not treat /Users/lingion_k/unixnu-research/reboot-checkpoints, runs, evidence, or device-backups as source repositories.
- Do not use the dirty Y35A or UniXNU working trees as clean source provenance without recording their worktree state.
- Do not treat the MSM8916 scaffold as a working port; its README explicitly states it is a research scaffold and not hardware-booted.
- Do not infer a single license for mixed-license lk2nd or Linux files; preserve per-file notices.
- The three local lk2nd snapshots resolve to the same commit cf45aefd22d744b2bf9b39455afae697ce430063.
- NONE-FOUND means the requested fact was not established from the local inspected paths; it does not assert that no upstream fact exists.

