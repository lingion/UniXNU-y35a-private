# Corrected T0.2 Probe Bundle

Status: offline-prepared; device authorization pending.

Current repository reconciliation: HEAD `72345786ff9c76053295023a63d689b0bdbaa5fa`; corrected probe source changes are in the shared worktree and the listed image was rebuilt from them in the native container. The final ELF disassembly contains the source-pinned TLMM and GCC address constants.

The original T0.2 image is retained only as a historical SE-timeout witness. Its TLMM, ATTn, and GCC fields are invalid for hardware conclusions because the collector used the wrong TLMM stride, sampled the wrong ATTn address, and stopped the GCC window before QUP5 controls. This corrected candidate preserves the zero-write/SE transaction design and replaces only the raw register collector.

## Artifacts

```text
image
  path: out/y35a/rmi-probe-20261109-t02-corrected3/rmi-probe-not-xnu.img
  sha256: 7a4b8e43d8b0048e8755f184b77948165457c2517e72a8f55437cf24ad9da90b

manifest
  path: out/y35a/rmi-probe-20261109-t02-corrected3/manifest.json
  sha256: 204f87083b7849a003d7a52f75df3b543c6f057946358ed20fca3ee4a89551a2

probe binary
  path: out/y35a/rmi-probe-20261109-t02-corrected3/probe.bin
  sha256: 5fb40cd374f655b3c675f84c278e4fbcd623887f6514cde7e55f31354f342a39
```

## Corrected report layout

Report bytes: `0x124`.

```text
attn_input       0x90   GPIO13 input, four samples
attn_status      0xa0   GPIO13 interrupt status, four samples
tlmm_target      0xb0   GPIO12/13/18/19 ctl/io/intr_cfg/intr_status
gcc_q5           0xf0   GCC+0x6000..0x6024 and GCC+0x45000..0x45008
```

Source-pinned addresses:

```text
GPIO12 ctl/io/cfg/status: 0x0100c000/0x0100c004/0x0100c008/0x0100c00c
GPIO13 ctl/io/cfg/status: 0x0100d000/0x0100d004/0x0100d008/0x0100d00c
GPIO18 ctl/io/cfg/status: 0x01012000/0x01012004/0x01012008/0x0101200c
GPIO19 ctl/io/cfg/status: 0x01013000/0x01013004/0x01013008/0x0101300c
GCC QUP5 RCG/branch/reset: 0x01806000/0x01806020/0x01806018
GCC BLSP1 AHB vote window: 0x01845000/0x01845004/0x01845008
```

## Scope and stop rules

- This candidate performs no GCC, TLMM, reset, PMIC, or BAM writes.
- It performs the existing bounded QUP5 SE reset/clock programming inside the SE window and one page-0 transaction at slave `0x20`, as in the original T0.2 design.
- The corrected raw dump is evidence about the handoff register state; a timeout still does not prove S3202 absence.
- Any result without the exact image and manifest hashes above is discarded.
- Device disappearance, a second fastboot process, unexpected report geometry, or a malformed upload stops the run.

