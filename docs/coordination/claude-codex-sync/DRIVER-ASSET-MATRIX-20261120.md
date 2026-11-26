# Y35A driver and platform asset matrix — 2026-11-20

The source snapshots below were fetched into `../upstream-refresh/2026-11-20/sources/` through the configured Git mirror and pinned by commit in `source-provenance.json`. The local SearxNG query corpus is `searx-results.json`. Linux and Android sources are hardware references; they are not automatically portable into XNU and their GPL obligations must remain separate.

## Highest-value same-class prior art

| Asset | Commit | License boundary | Relevant paths | Use in Y35A |
|---|---|---|---|---|
| `tadashiutau/coreprime-ios` | `3af5f9c089a3936eda2018dbf0bbc46335d2935f` | No license file in repository; preserve provenance and treat as reference until rights are clarified | `loader/loader.c`, `loader/mmc-readonly.c`, `shim/phone.dts`, `hakios-patches/new-files/hakios.coreprime_input.c`, `hakios-patches/new-files/coreprime_crypto_emul.h`, `docs/REPORT.md` | Closest MSM8916 end-to-end shape: external APFS System, read-only SD, framebuffer inheritance, touch/buttons, four-core bring-up, crypto emulation. Hardware results are repository testimony, not independently shipped raw evidence. |
| `oosexgang/hakios-xnu-kernel` | `63fc2b4633bac3af8e57dadab9f5a8d4cb940438` | `xnu/hakios.patch`, `xnu/files/`, and `drivers/` are APSL-2.0 derivative work; loader/tools/docs/devices are MIT per its `LICENSE` | `drivers/input/`, `drivers/audio/`, `drivers/wifi/`, `drivers/bluetooth/`, `drivers/power/`, `drivers/storage/`, `drivers/gpu/`, `drivers/camera/`, `drivers/modem/`, `drivers/core/`, `xnu/hakios.patch`, `wifi/lx/` | Strongest XNU driver architecture reference. Port subsystem by subsystem, retaining Apple notices and checking the driver review docs before reuse. |
| `oosexgang/hakios-metal` | `d36f329e2684a1968b7c1a0ceee1661472cb707a` | MIT | `window-server/xnu/files/iokit/Kernel/MiniIOMobileFramebuffer.cpp`, `src/`, `include/` | Display/IOKit shape reference; not an MSM8916 panel implementation by itself. |

## Boot, display and input

| Asset | Commit | Relevant paths | Status |
|---|---|---|---|
| `msm8916-mainline/lk2nd` | `cf45aefd22d744b2bf9b39455afae697ce430063` | `app/aboot/aboot.c`, `arch/arm/cache-ops.S`, `arch/arm/mmu.c`, `platform/msm_shared/`, `lk2nd/display/simplefb.c`, `target/*/target_display.c`, `dev/gcdb/display/` | Public lk2nd reference. It is not proof of the resident Y35A fork identity. Its framebuffer/simplefb and handoff code are the first source comparison for the measured `0x83200000`, 720x1280, RGB888, stride 2160 contract. |
| `msm8916-mainline/linux-mdss-dsi-panel-driver-generator` | `28c4df25628f6241ce925af15637a443ea2b3bb5` | GPL-2.0; `COPYING` | `panel.py`, `mipi.py`, `driver.py`, `dtsi.py`, `lk.py` | Generates panel init data from QCOM MDSS DSI device trees; use to identify the Y35A panel sequence, then implement a clean XNU/IOKit driver rather than copying GPL code into XNU. |
| `msm8916-mainline/linux-panel-drivers` | `0f01341dd6d18294615ebbe6a86ac237d4c48cad` | GPL-2.0; `COPYING`, DT license | `dtb/`, `config/`, `generate.sh` | Panel configuration reference; no direct XNU reuse. |
| Samsung MSM8916 kernel | `2c1ef8b1a50c7a67403a786b9056d3cd60bb5c7d` | GPL-2.0; `COPYING` | Sparse snapshot includes `arch/arm/boot/dts/`, `drivers/gpu/`, `drivers/input/touchscreen/`, `drivers/mmc/`, `sound/soc/`, and DT bindings | Best device-family Linux source currently persisted for panel, touchscreen, SD/MMC and audio register names. Exact SM-G360T1 binding still needs board-level verification. |

## Storage, Wi-Fi and Bluetooth

| Asset | Commit | Relevant paths | Status |
|---|---|---|---|
| `tadashiutau/coreprime-ios` | `3af5f9c...` | `loader/mmc-readonly.c`, `loader/loader.c` | Direct same-SoC read-only SDHCI/eMMC loader reference; reported CMD18 multi-block path and retained-state handling. Requires independent Y35A register derivation before use. |
| `oosexgang/hakios-xnu-kernel` | `63fc2b...` | `drivers/storage/`, `drivers/wifi/`, `drivers/bluetooth/`, `wifi/lx/`, `docs/driver-review/wifi-*` | XNU-side integration shape. `drivers/bluetooth/hakios.bt.c` is a research/read-only starting point; Wi-Fi has a Linux compatibility layer and firmware path. |
| `prototype74/android_hardware_qcom_wlan` | `1bd2e2c8286cd4d11edd327cc83ca013e24388b9` | `wcnss-service/`, `qcwcn/wifi_hal/`, `cld80211-lib/` | Android HAL/QMI reference, not XNU code. Useful for WCNSS service protocol and firmware control surface. No top-level license file was found in the snapshot; audit file-level headers before reuse. |
| `msm8916-mainline/linux` | `ea3a5c52f8f62f6464b6cdc06b700f0704f1c04a` | Full Linux source; MSM8916 DTS and Qualcomm drivers | GPL-2.0 WITH Linux syscall note. Use as register, DT, clock, IRQ and firmware reference only. |

## Audio, camera, power and other peripherals

| Asset | Commit | Relevant paths | Status |
|---|---|---|---|
| `oosexgang/hakios-xnu-kernel` | `63fc2b...` | `drivers/audio/`, `drivers/camera/`, `drivers/power/`, `drivers/modem/`, `drivers/core/` | Existing XNU-side subsystem implementations are the fastest architecture reference. Driver review docs classify what was compiled, emulated or run; they are not proof of Y35A hardware support. |
| Samsung MSM8916 kernel | `2c1ef8b...` | Sparse `sound/soc/`, DT bindings, GPU/input/MMC paths | GPL reference for codec, clocks, GPIO/PMIC and board wiring. No direct copy into APSL XNU without a clean-room or compatible licensing decision. |
| `oosexgang/hakios-metal` | `d36f329...` | Adreno/Metal user and kernel-side references | MIT reference for higher-level display/GPU shape; Y35A Adreno 306 support remains a separate hardware task. |

## Immediate reuse order

1. Keep R326 AMFI boundary as the measured control.
2. Close real AMFI/CoreTrust registration from the persisted R158/R159 work before changing UI claims.
3. In parallel, derive Y35A DT/panel/touch/MMC identities from the Samsung kernel and lk2nd sources, then implement clean XNU drivers in disjoint files.
4. Use the CorePrime loader and HakiOS input/storage contracts as architecture references, preserving license boundaries.
5. Do not label a subsystem attached or working until a fresh current-generation witness is bound to the exact boot package and a real device result.
