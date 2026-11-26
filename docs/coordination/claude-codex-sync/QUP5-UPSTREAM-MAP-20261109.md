# MSM8916 QUP5 Upstream Map

Date: 2026-11-09

## Source pin

The source is the sparse Linux snapshot at `/Users/lingion_k/unixnu-research/upstream-snapshot/linux-7475ea8-msm8916/repo`.

- Repository: `torvalds/linux`
- Commit: `7475ea8b58616b33c04afb976cf0fbaad9dd63fb`
- Ref observed: `master`
- Version string: `Linux 7.4-rc2`

Relevant file hashes:

```text
msm8916.dtsi                         5f1ecdba92303696ee36da1bbc55a94142800ca3b6c6b890f7732652693314d4
gcc-msm8916.c                        827fe9fd32d9db29d9f4f40afc79b0c4e823101875d02f6205ddb07360082250
pinctrl-msm8916.c                    45767bdc194a8585f25d7e97261d652373fd780a58d1a788eae9801dee4d24ab
i2c-qup.c                            22311b93c01855bf5e01622caca4338581c4b0428cd745a71b64a83d6ba23004
rmi_i2c.c                            56581b09ccd9e90a9b8d0a2b9f5a3de07f9d0d32c389f0c5763df2e709c9c70a
qcom,i2c-qup.yaml                    fdeafcbe88a9ad4858394d32771e3818474f4c4ef1bd45a1c7340979cdcbc042
qcom,gcc-msm8916.h                   3f064f11a46d6c217799e912d9e24ec1d64295cbb0ec6f0cbecd116172106af4
reset.c                              434e63a159118f20a49114f5b184f405739e5ba4cda4148f4e101bf6b36326e8
reset.h                              ee4ae7a90e5e3544ffa5335ad96511cee659bad16f09f1fa9fc28f1d10db06a3
clk-branch.c                         d29259eb77a5d1d6a07adf4aa835588f8e04d1fa3c14be2b7d4162cce737abfa
clk-branch.h                         bac7dcf51a0da5b27eaa0d4dc276f540fec80013bd4862cfbbc115a50161ef72
```

## Direct source facts

The mainline `msm8916.dtsi` declares `blsp_i2c5: i2c@78b9000` with:

- compatible `qcom,i2c-qup-v2.2.1`;
- register base `0x078b9000`, size `0x500`;
- interrupt `GIC_SPI 99`;
- clocks `GCC_BLSP1_QUP5_I2C_APPS_CLK` and `GCC_BLSP1_AHB_CLK`;
- DMA channels 12 and 13;
- default and sleep pinctrl states for GPIO 18 and GPIO 19.

The mainline TLMM driver maps `blsp_i2c5` to GPIO 18 and GPIO 19. This agrees with the stock Y35A DT extraction and the local QUP5 driver design.

For the raw TLMM path, the source defines the TLMM base as `0x01000000`, each GPIO control register at `base + pin * 0x1000`, and the input register at control plus `0x4`. In the `PINGROUP(18/19, ...)` entries, `blsp_i2c5` is the second function slot after the GPIO slot, so the mux field value is `2`; the upstream default state uses drive strength `2` and bias disable. The stock DT's `qcom,pin-func=<0x02>` is therefore source-consistent, not a guessed function number.

The mainline GCC source gives the following QUP5 controls:

| Function | Register or ID | Evidence |
|---|---:|---|
| QUP5 I2C source RCG command register | `GCC + 0x06000` | `blsp1_qup5_i2c_apps_clk_src.cmd_rcgr` |
| QUP5 I2C application branch enable | `GCC + 0x06020`, bit 0 | `gcc_blsp1_qup5_i2c_apps_clk.enable_reg` and `enable_mask` |
| QUP5 reset | `GCC + 0x06018` | `GCC_BLSP1_QUP5_BCR` reset map |
| BLSP1 AHB branch enable | `GCC + 0x45004`, bit 10 | `gcc_blsp1_ahb_clk.enable_reg` and `enable_mask` |
| QUP5 I2C clock ID | `64` | `GCC_BLSP1_QUP5_I2C_APPS_CLK` |
| BLSP1 AHB clock ID | `54` | `GCC_BLSP1_AHB_CLK` |
| QUP5 I2C source clock ID | `24` | `BLSP1_QUP5_I2C_APPS_CLK_SRC` |

The reset implementation is also source-verified. The Qualcomm reset controller derives the reset mask as `BIT(map->bit)` when no explicit mask is present, writes the asserted value, reads the register back, waits at least 1 microsecond for a reset operation, and then deasserts it. The MSM8916 QUP5 reset map has no alternate bit field, so the default reset bit is the bit-zero mask at `GCC + 0x06018`.

The Linux branch implementation enables a branch with a read-modify-write on its `enable_reg` and `enable_mask`; the QUP5 I2C branch is therefore the bit-zero write at `GCC + 0x06020`. The source RCG uses `cmd_rcgr=0x06000` and the common QUP5 I2C frequency table includes 19.2 MHz and 50 MHz parents.

This closes the offline address question that remained after the T0.2 timeout. It does not claim that these writes have been tested on the Y35A device.

## Interpretation

The previous T0.2 result remains narrow: the handoff state did not produce a valid QUP5 transaction, and the old probe did not establish S3202 absence. The upstream map now supplies a same-SoC, source-pinned candidate for a controlled cold-read experiment. Do not copy offsets from MSM8952 or another Qualcomm generation.

The later T0.2 audit found that its raw TLMM/GCC/ATTn fields were not collected from the target registers: the TLMM loop used a `+4` stride instead of `+0x1000`, the ATTn sample used `0x01000034` instead of the GPIO13 input/status window, and the GCC loop stopped at `GCC+0x800` before the QUP5 controls. Those old fields are superseded; the SE timeout itself remains a separate observation.

The next device probe should vary one factor at a time:

1. snapshot the pre-write TLMM/GCC/QUP state;
2. configure only the GPIO 18/19 BLSP1 I2C5 function and the exact QUP5 clock/reset controls above;
3. perform one bounded page-0 read at slave `0x20`;
4. snapshot the post-read state and stop on timeout, NACK, or invalid SE state.

The write-capable sequence must assert and deassert the QUP5 reset using the verified bit-zero semantics, enable the BLSP1 AHB and QUP5 I2C branches, then configure GPIO 18/19 for `blsp_i2c5` before the SE transaction. The exact order remains a device experiment variable; keep one order fixed per run and retain the pre/post register dumps.

This is a new write-capable device experiment and requires its own explicit user authorization. No device action was performed while producing this map.

