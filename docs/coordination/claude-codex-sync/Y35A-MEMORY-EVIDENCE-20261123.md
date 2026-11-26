# Y35A memory evidence reconciliation — 2026-11-23

This record separates physical-memory identity, a recorded `/proc/iomem` window
summary, and the memory span selected by one offline XNU candidate.

## Direct staged-DTB evidence

`/Users/lingion_k/unixnu-research/evidence/y35a-20261102/lk2nd-runtime.dtb`
was read back through the lk2nd staged interface, as recorded by
`evidence/y35a-20261102/PROGRESS.md:69`. Its SHA-256 is
`36555c5e66b4a09cd38506706b0a301c2c8b8d6b883de51c51b89971825e9709`.

The root model is `msm8916-vivo-pd1502a`, with two-cell address and size
fields. Its only memory node reports:

* `0x80000000..0xc0000000` — 1 GiB;
* `0xc0000000..0x100000000` — 1 GiB.

The two ranges total 2 GiB. The FDT reserve map is empty. This is direct
evidence about that staged runtime DTB and its earlier loader handoff. It is
not the final DTB or boot argument block of the current maximum-memory
candidate, and it does not prove that every byte is usable by XNU.

## Recorded usable-window evidence

`evidence/y35a-20261102/PROGRESS.md:11` records these `/proc/iomem` windows:

* `0x80000000..0x86000000`;
* `0x8c300000..0x9ff00000`;
* `0xa0000000..0xfffff000`.

The original `/proc/iomem` dump is not present in the current host evidence
tree. These ranges therefore remain a recorded summary, not a byte-bound raw
capture. The old recon statement that one `/memreserve/` interval proves a
1 GiB device is withdrawn; the staged DTB and official Y35A specification
support 2 GiB physical capacity, subject to final-boot binding.

## Offline candidate gate

Candidate directory:
`/Users/lingion_k/unixnu-research/reboot-checkpoints/r326-max-contiguous-memory-audit-20261123-241/`

The candidate manifest SHA-256 is
`910956a9a16986af0ebf50c2ba7cc210f9995d935d9c8d7604c6c32e1063528c` and the
boot image SHA-256 is
`3ba46278151e42ae2258b203e42b18b087dec92d45bb224716d43abc6ab15a78`.
Its final boot arguments and ADT agree on:

* physical base `0xa0004000`;
* contiguous XNU-owned size `0x5fe00000`;
* end `0xffe04000`;
* `memory_profile=max-contiguous-measured`;
* `multi_bank_supported=false`.

The offline verifier is
`scripts/y35a/verify_memory_configuration.py`. A run against the candidate
and the staged DTB returned `ok=true` with no failures. The report explicitly
labels the staged DTB as prior-loader evidence and the `/proc/iomem` source as
recorded-summary evidence. The saved report is
`reboot-checkpoints/r326-max-contiguous-memory-audit-20261123-241/memory-gate.json`,
SHA-256 `e83a8f4c503a8da37566f7563d31c8d41be363e4273df32bbbf3e6cb570041d9`.

## What this permits and what it does not

The candidate is internally consistent as an offline single-span memory
configuration and is compatible with the recorded high usable window. It is
not yet a device-validated maximum-memory boot. Device use remains stopped
until the startup-marker ownership gate and the final-DT/bootargs binding for
the exact candidate are both green.
