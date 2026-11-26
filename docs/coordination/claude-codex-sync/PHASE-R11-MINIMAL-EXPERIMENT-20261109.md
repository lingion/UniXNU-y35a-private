# Phase-r11 plus minimal-boundary experiment

Status: offline-prepared; awaiting a new per-experiment user authorization.

This is a new kernel and transport pair. It does not reuse the 11:30 `都跑` authorization.

## Inputs

- Phase kernel: `out/y35a/ios12-kernel-phase-r11/kernel-packed.macho`
- Kernel SHA-256: `619a6ea03be230529d4eeeaac64a3fd9d44cef8e1d302255a6bd5f70dd70381a`
- Phase boot image: `out/y35a/ios12-boot3-phase-r11/boot3.img`
- Phase boot image SHA-256: `a98c0b26340b503d05414c2cf9586e52725ffa0e99cb420a63619931dad47e99`
- Minimal readback image: `out/y35a/readback-probe-20261109-min-r9/readback-probe-not-xnu.img`
- Minimal readback image SHA-256: `9466188a5b3f91fedb53525823dea7ced471f5ad1d7e69b1bf4ddbf462d9a405`
- Current-source minimal manifest: `out/y35a/readback-probe-20261109-min-r9-host-e434/readback.json`
- Current-source manifest SHA-256: `39574d2fdab3b336f859fc2d0e814f9ea6779c294244e26bd07d1876eed44371`
- Historical minimal manifest SHA-256: `0ae59dac07ed1a7accd8f26a47123633084c6c95c30da3cad9cd64a54d1d4fea` (same image and entry bytes)

## Sequence

1. Confirm `fastboot devices` shows only `efff9d92` and no fastboot process is running.
2. Capture a baseline `oem y35a panic` upload.
3. RAM-only boot the phase-r11 image.
4. Wait for the device to return to fastboot; stop if it does not return within the bounded watchdog window.
5. RAM-only boot the minimal-boundary readback image.
6. Wait for fastboot, capture `oem y35a panic`, and retain the raw upload under a new timestamped path.

No partition write, flash, userdata operation, or unbounded retry is allowed.

## Expected report layout

The LK upload is 69,632 bytes. The phase boot shim writes its `Y35AXNU2` handoff stamp at body offset `0x10000`; the minimal probe preserves the first `0x40` bytes of the report page and writes its own `Y35ARD02` header at body offset `0x10040`.

The phase marker record is the early-fault record at report offset `0x100`, so the shared marker slot is body offset `0x10128` (`0x10000 + 0x100 + 5*8`). Its value must be one of:

- `0x41524d564d494e49`: `arm_vm_init` completed.
- `0x50414e4943494e49`: `panic_init` completed.
- `0x434f4e534f4c45`: `PE_create_console` completed.
- zero: no C phase marker reached the record before reset, which is a valid negative observation.

The `_native_early_fault_address` record and the CPU witness records are secondary evidence. The marker slot is the primary boundary discriminator for this run.

## Stop conditions

- Device disappears or another fastboot process appears: stop before the next command.
- Phase image does not return to fastboot in the bounded window: stop and preserve the last state.
- Minimal capture lacks `Y35ARD02` at body `0x10040`: classify as minimal transport failure.
- Marker value is outside the four values above: classify as report corruption, not XNU progress.
- Any result lacking the exact input image hashes above is discarded from boundary conclusions.
