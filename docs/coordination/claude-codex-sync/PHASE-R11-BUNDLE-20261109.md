# Phase-r11 Experiment Bundle

Status: offline-prepared; device authorization pending.

The bundle is the exact pair described by `PHASE-R11-MINIMAL-EXPERIMENT-20261109.md`. The current repository HEAD is `766227ca84ffa6bfb1bb855b30824167613087fb`. The current-source readback generator was copied into the existing native container together with the phase kernel and the verified stock boot input (`stock-boot.img` SHA-256 `92611f876a022fb5af1138f0591f5dafe2b359a226b2f0b28d292211f2fec012`). It produced a new manifest with absent-symbol provenance; the entry source, entry binary, and Android image are byte-identical to the historical candidate.

## Artifacts

```text
phase kernel
  path: out/y35a/ios12-kernel-phase-r11/kernel-packed.macho
  sha256: 619a6ea03be230529d4eeeaac64a3fd9d44cef8e1d302255a6bd5f70dd70381a

phase boot image
  path: out/y35a/ios12-boot3-phase-r11/boot3.img
  sha256: a98c0b26340b503d05414c2cf9586e52725ffa0e99cb420a63619931dad47e99

minimal readback image
  path: out/y35a/readback-probe-20261109-min-r9/readback-probe-not-xnu.img
  sha256: 9466188a5b3f91fedb53525823dea7ced471f5ad1d7e69b1bf4ddbf462d9a405

minimal manifest
  path: out/y35a/readback-probe-20261109-min-r9-host-e434/readback.json
  sha256: 39574d2fdab3b336f859fc2d0e814f9ea6779c294244e26bd07d1876eed44371

historical minimal manifest
  path: out/y35a/readback-probe-20261109-min-r9/readback.json
  sha256: 0ae59dac07ed1a7accd8f26a47123633084c6c95c30da3cad9cd64a54d1d4fea

entry source
  path: out/y35a/readback-probe-20261109-min-r9/entry.S
  sha256: 90c500b6ee574e3eef9879e6cab410effd1878b2f96268d7e18e1b978e727e02

entry binary
  path: out/y35a/readback-probe-20261109-min-r9/entry.bin
  sha256: 18fe593424f6918f51152576fc13647babc5ddd79f31e1b413c9c454e8b92fd8
```

## Source hashes

```text
scripts/y35a/readback_native.py                  5b3f4012a8a03a976e36d201edeeb7b1d6708218b4cd9bcc05e8b710fae90817
tests/test_readback_names.py                     540ebaa17e1a935e2f35f8245ee5f95558b858995ef399b444a828e56bcf4403
scripts/build-xnu-4903-kernel.py                 9c9e2c9aeef02f4c363e816e722234046a48338ad9794b178efd5c8f07efe721
patches/xnu/native-phase-c-enable.patch          15500d67eef5bf435a6db6fccabb0c361c364f884ecfb27d460403c9add6cfc0
patches/xnu/native-phase-console-marker.patch    a563b6ffb0c3f6b9a66c5c38f35d8ae025563dd50905a089e73410c90f57275a
patches/xnu/native-phase-markers.patch           295a326a46856dc977d4bb430555fbba6123f36e32aace32e9fcfba22649015c
```

## Acceptance and stop rules

- `verify_phase_instrumentation.py` must return `ok:true` for the phase kernel.
- The minimal layout gate must validate the report write interval `0x859f0000..0x859f1000`.
- The minimal transport gate must validate the LK upload source `0x859e0000..0x859f1000` and the snapshot `0x95000000..0x95010000`.
- The body marker positions are `Y35AXNU2` at `0x10000`, `Y35ARD02` at `0x10040`, and the XNU marker slot at `0x10128`.
- No `fastboot boot`, `fastboot oem y35a panic`, reset, flash, partition, or userdata operation is allowed until a new per-experiment user authorization names this exact pair.

