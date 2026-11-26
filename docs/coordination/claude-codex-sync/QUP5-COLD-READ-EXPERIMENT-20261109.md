# QUP5 Cold-Read Experiment

Status: offline design only; no device authorization and no device writes performed. The predecessor T0.2 register dump is currently invalid for TLMM/GCC/ATTn because its windows use the wrong stride and stop before QUP5 gate registers; repair that probe before treating any new raw dump as a handoff comparison.

This is the follow-up hardware experiment after the phase-r11 boundary run. It tests whether the Synaptics S3202 becomes reachable when the missing QUP5 handoff resources are enabled from source-pinned MSM8916 facts.

## Question and hypotheses

Question: after a bounded clock, reset, and pinmux setup, does QUP5 reach a valid SE state and return an RMI4 page-0 response from slave `0x20`?

- H0: the SE still fails before `VALID`; the clock/reset or ownership model remains incomplete.
- H1: the SE becomes valid but the target NACKs or times out; the bus or target power/reset state is still unresolved.
- H2: the transaction ACKs and the page-0 bytes identify an RMI4/S3202 device.

The old T0.2 timeout cannot distinguish H0 from H1 and cannot support S3202 absence.

## Source-pinned addresses

All values below come from `QUP5-UPSTREAM-MAP-20261109.md` and the sparse Linux snapshot pinned to `7475ea8b58616b33c04afb976cf0fbaad9dd63fb`.

```text
TLMM base                         0x01000000
TLMM GPIO18 control/input         0x01012000 / 0x01012004
TLMM GPIO19 control/input         0x01013000 / 0x01013004
QUP5 SE                           0x078b9000, 0x500 bytes
GCC base                          0x01800000
QUP5 source RCG                  GCC + 0x06000
QUP5 I2C branch                  GCC + 0x06020, bit 0
QUP5 reset BCR                   GCC + 0x06018, bit 0
BLSP1 AHB branch                 GCC + 0x45004, bit 10
QUP5 interrupt                   GIC SPI 99
QUP5 DMA                         channels 12 and 13
TLMM mux for blsp_i2c5           function slot 2 on GPIO18/19
RMI4 target                      7-bit I2C address 0x20
```

The source RCG register address is known, but this document does not invent a new divider value. The first implementation must read and record the RCG state and use the existing measured QUP timing path; a new RCG programming value is a separate hypothesis.

## Per-run sequence

1. Confirm the device is the only `efff9d92` fastboot target and no fastboot process is running.
2. Capture a baseline report containing the QUP5 SE window, TLMM GPIO12/13/18/19 control and input/status registers at `TLMM + pin*0x1000`, GCC ranges covering `0x6000..0x6024`, `0x1000..0x1008`, and `0x45004`, plus the report freshness witness. A `+4` pin stride is forbidden by the source map.
3. Assert QUP5 reset through `GCC + 0x06018` bit 0 and read the register back. The upstream reset controller uses a set-bit assertion, readback, at least 1 microsecond delay, and clear-bit deassertion.
4. Enable BLSP1 AHB at `GCC + 0x45004` bit 10 and QUP5 I2C at `GCC + 0x06020` bit 0, preserving the pre-write values in the report.
5. Configure GPIO18 and GPIO19 to mux slot 2 with the stock DT electrical state (`drive-strength=<2>`, `bias-disable`), preserving both control words before and after the change. Treat `<2>` as the DT electrical value, not a raw register bitfield: the TLMM drive field is bits `[8:6]`, and the exact mA-to-code mapping remains a separate offline/first-run observation. Do not invent a raw drive code from the number 2. Preserve GPIO12/13 state but do not touch their reset/attention lines in this first run.
6. Run exactly one bounded SE-mode page-0 read at `0x20`. Record the raw SE state, all status/error words, ACK/NACK/timeout classification, and the returned bytes without interpreting them as identity unless the transaction ACKs.
7. Capture the post-read registers and stop. Do not add a retry loop, touch reset, PMIC write, or frame read in this experiment.

## Stop conditions

- Device disappears, a second fastboot process appears, or the device leaves the expected state: stop before the next command.
- Any write falls outside the three source-pinned regions (GCC, TLMM GPIO18/19, QUP5 SE): classify as probe violation and discard hardware conclusions.
- SE state never becomes valid within the bounded timeout: stop and preserve the raw report; do not infer target absence.
- Page-0 read NACKs or times out after a valid SE state: stop and classify the target/bus result separately from clock setup.
- Any unexpected register value or response length: classify as malformed report, not a positive identity.
- Any pre-write TLMM/GCC/ATTn evidence produced by the unrepaired T0.2 dump path: discard it as a collector defect and do not use it as the baseline.
- Do not assume a 16-pin TLMM pigtail interrupt layout; the source snapshot exposes one aggregate TLMM interrupt line, DT SPI 208 / architectural INTID 240, with per-pin TLMM interrupt registers still requiring separate programming.
- No partition write, flash, userdata change, or unbounded retry is allowed.

## Required artifacts

The run needs a new probe image and manifest with complete SHA-256 values, source commit/hash, device serial, pre/post raw uploads, and the exact register-write list. It requires a new explicit per-experiment user authorization because it writes clocks, reset, and pinmux registers.

