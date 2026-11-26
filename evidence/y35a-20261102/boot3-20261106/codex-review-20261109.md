# Codex review: phase evidence before more PRAM work

Date: 2026-11-09 CST

## Evidence

- The device is currently reachable in fastboot as `efff9d92`; read-only `getvar product` returns `lk2nd-msm8916` and `max-download-size` returns `0x10000000`.
- The boot3 image that was actually run in the r6 sequence is `out/y35a/ios12-boot3/boot3.img`, SHA-256 `d7640a423935b6dbe9322b0b8bbcdac305d25428ff87e0a8ac8bd5439cb74ad6`, with kernel SHA-256 `5fd4e6b5f7fa10e1b2cc9323ac5802833c15479fce5c67068f2ba8837fdcdc94`.
- The phase-marker build is a different artifact: kernel `6e9a09d2453a57532111dbead64ea67018ca31128e3ca7dcaa4e3fbf6f0216c5` and boot3 image `8694a25fdef575a5b615e8fee6f59bf546495f1f206478c5398af994a7462c4c`. The evidence file says its fastboot transaction hung before any boot request, so it has no device result yet.
- `r6-baseline-retained.raw`, `r6-post-boot3.raw`, and `panic-direct-20261109-0017.raw` are byte-identical with SHA-256 `995333535c9f2c4f61bac2871c36fb51008f8c51f8cb44dc59811a445e931418`. The last file therefore cannot be treated as an independent fresh panic capture.
- `native-phase-markers.patch` writes only after `arm_vm_init`, `panic_init`, and `PE_create_console`. It does not distinguish `pe_identify_machine`, `pe_arm_init_interrupts`, or `pe_arm_init_debug`, and the patch was not present in the image used for the r6 boot.

## Direction correction

The current PRAM and panic-global investigation cannot identify the r6 boot boundary. It is valid to keep the readback tool as a later panic-capture tool, but it is not the next discriminator. Do not infer a pexpert early-boot window from the unbooted phase-marker image.

## Next experiment

Run exactly the phase-marker boot3 image `8694a25f...` in a healthy fastboot window, record the image and kernel hashes immediately before `fastboot boot`, then collect only the existing RAM/readback record after the device returns. If the phase image is not the one resident in the device run, discard the result. If the marker record is unchanged, add one marker before and after each pexpert boundary and repeat one variable at a time.

Keep XNU version explicit in every record. The current device experiment is built by `scripts/build-xnu-4903-kernel.py`; the iOS 12/XNU-4570 migration documents are a separate porting line and must not be used as direct 4903 panic-layout evidence.

## Phase-specific result

The phase image was then run on the real device. `fastboot boot` returned `Booting OKAY`; after approximately 13 seconds the device returned to fastboot. A probe rebuilt from the phase kernel was run afterward.

- phase kernel SHA-256: `6e9a09d2453a57532111dbead64ea67018ca31128e3ca7dcaa4e3fbf6f0216c5`
- phase boot3 image SHA-256: `8694a25fdef575a5b615e8fee6f59bf546495f1f206478c5398af994a7462c4c`
- phase probe image SHA-256: `80e21b833ade760618739cda9765c889e4fbf209ca99d90d66b29dd76a4e57ff`
- phase readback SHA-256: `1e3c8e0f2bf2c352dd28d53e4b9179aef55533b8e6dee728bcc6f8a5d25624fe`
- both `Y35ARD01` and `Y35AXNU2` contain the phase stamp `6e9a09d2`
- the phase-specific `early-fault-record` at `0xa0b7c800` is all zero

This is a valid phase-image result. It proves only that the existing early-fault record was not populated. It does not identify `pe_identify_machine`, `pe_arm_init_interrupts`, `pe_arm_init_debug`, `arm_vm_init`, or `PE_create_console` as the failing boundary.

## Agreed direction to resume

1. Freeze the old PRAM/panic interpretation. Keep the readback tool only as a later panic-capture tool.
2. Add one diagnostic marker at `arm_init` entry and one around `PE_init_platform(FALSE)`, then rebuild offline. Do not add all markers in one build.
3. In the next build, place one marker around each `pe_identify_machine`, `pe_arm_init_interrupts`, and `pe_arm_init_debug` boundary. Use the phase-specific probe and exact hashes for each device run.
4. Treat ADT `interrupt-controller` value `master` as an independent offline A/B variable because XNU-4903 searches for that value. Do not infer GIC or ArmCpu success from host tests; `ArmCpu` and `ArmDTPlatform` are not currently folded into the 4903 kernel image.
5. Keep GPU, IIG, launchd, panic-buffer interpretation, and userland work frozen until the earliest phase boundary is observed. XNU-4903 is the active truth; xnu-4570 remains reference material only.
