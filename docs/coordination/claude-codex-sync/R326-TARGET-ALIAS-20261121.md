# R326 target alias boundary — 2026-11-21

Paired evidence shows the physical alias calculated for `_native_early_fault_address` (`x9 = 0xa0762488`) does not return through the direct store/cache-maintenance path. The same control flow reaches fresh `ARGSLOAD` when the direct target accesses are skipped, redirected to a known bootargs carrier, or performed through the high alias `x16 = fffffff007762488`. This is a measured address-path boundary, not a claim that all later startup is working.
