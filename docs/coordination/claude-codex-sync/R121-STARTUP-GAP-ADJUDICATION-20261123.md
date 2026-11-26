# R121 startup-gap adjudication

Run: `/Users/lingion_k/unixnu-research/reboot-checkpoints/r326-r121-startup-gap-paired-run-20261123-01/`
Device: `efff9d92` / `lk2nd-msm8916`; RAM-only; `persistent_writes=false`; returned to fastboot.

Inputs:

- kernel `3fb0e8311dc2f275724aaad17fac880094cb6052b72966483911df6bb0d20366`
- boot `06a049d0290ec2804a8b9957bc1b52092a8bd6ae23473e384d639a8094743f51`
- regular probe `b812c4aeba27e94356685903a61334159246de326f11cbd77f502e9ffed26cb1`
- clear probe `45d56c47d960b654400662cd856b6a4a8cd8d91e1af178fd74d4690cd9289eda`

Raw evidence:

- preclear `c4ac3bc9a1130715d791d329d7cb5250d106f59187dc7c8aea5b746921231f9b`
- baseline `0c58346fcba8f358b9ccf9cacdc552c74a0c677f7d707202cbb02c29ef78c342`
- candidate `580256035074ec9bbae1b312fb76d3faeef918145eaa53a0ea8cf2902ee05e9d`
- final `01b4a0c7d5d69b7e22ca015c3b9993c15c53a73d227517a0fd1649c04fb7906c`

Fresh final contains `VNGAFTR0`, `DTRAFTR0`, `SDTAFTR0`, `KEXTRET0`, `LOCKAFTR`, `VMPROT00`, and `PRERAND0`. `RAND0010` is absent.

**CONFIRMED boundary:** after `arm_vm_prot_finalize()` and before return from the first `read_random(&vm_kernel_addrperm, sizeof(vm_kernel_addrperm))` call. The result does not prove a fault inside `read_random`; it only localizes the missing return marker to that call or its immediate path.

Next MVE: add entry, lock-before, lock-after, generation-success, and return cursors inside `read_random()`; preserve maximum memory and the paired clear/baseline/final discipline.
