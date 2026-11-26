# R1D embedded strict entry audit — 2026-11-20

The R1D direct-entry experiment was rerun with a probe and package bound to the bytes actually copied by the shim.

The shim copies its `kernel_data` region from `entry-obf.bin + 0x328` for `12,288,976` bytes. That region has SHA-256 `93f95e079b39469f2dc2d4c5f4077fe4caeba6a64084e59963a7a119f8e374b9`.

The strict paired artifacts are boot `95f47dc50f82e92078fa0becf34582cdeedbf521236bbf8b8da20a0bca7f7385`, probe `fd0f47adf5fa8089db6a8f9fdad7af33bbd95b86627e56338ca92651bfb31386`, baseline `95ab878337f6a4e154cc39c66a105b77eeaab4745810cbb8382c9a29ef0c5e57`, and final `34f3e1ee4d67e8e99f54a50dfa8adedc3e6a34f33c460d2cc78e605a93936bfd`.

The paired run was RAM-only on serial `efff9d92`; `persistent_writes=false`. The final raw contains the shim header and old retained strings, including `Y35AXNU2`, `R260CPY0`, `R84ENT00`, `R84FS00`, and `R90FPX00`. Those same values are present in baseline and final, so they are not fresh current-run XNU witnesses. There is no fresh `R1DENT0`, `R117EN00`, early-fault record, or current entry trace.

The strict run corrects the earlier invalid R1D probe binding but remains a negative observability result. It does not prove current XNU entry or identify a fault location. The next productive path is the persisted R154 userspace-reaching control and a real AMFI/CoreTrust registration closure.
