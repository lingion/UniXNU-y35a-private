# Original iOS 12 ARM64 pmap ABI audit — 2026-11-20

The local 16G102 kernelcache was disassembled directly:

- Input: `/Users/lingion_k/unixnu-research/UniXNU-y35a/out/ipsw/16G102/kernelcache.decompressed`
- SHA-256: `70e80388d42fe2376096bb6248073b0380dd87b85b1a792b36205ba60c722ce1`
- Architecture: ARM64 Mach-O kernelcache

The eight missing exports from the R155 plan are present in the original kernelcache at these linked addresses:

| Symbol | Address | Measured behavior |
|---|---:|---|
| `_pmap_claim_reserved_ppl_page` | `0xfffffff0071b6048` | Acquires a lock, pops a page from a reserved-page linked list, clears the lock, and returns the page. Panics if the pool head is null. |
| `_pmap_free_reserved_ppl_page` | `0xfffffff0071b60e4` | Acquires the same lock, pushes the supplied page onto the reserved-page list, clears the lock, and returns through the machine policy hook. |
| `_pmap_load_image4_trust_cache` | `0xfffffff0071b6160` | Validates sizes, alignment, overflow and Image4-related inputs, calls opaque Image4/security interfaces, validates the v1 trust-cache payload, and updates protected runtime state. It is not reducible to a constant return. |
| `_pmap_load_legacy_trust_cache` | `0xfffffff0071b6958` | Requires module size greater than 31, stores the module pointer in a protected linked list, compares the 16-byte UUID at module offset 8 against existing entries, returns `0` on insertion and `11` on duplicate. It uses a lock and a real list head. |
| `_pmap_is_trust_cache_loaded` | `0xfffffff0071b6b54` | Compares a 16-byte UUID against the static TrustCache and then the loaded TrustCache list; returns `1` on a match and `0` otherwise. |
| `_pmap_lookup_in_loaded_trust_caches` | `0xfffffff0071b6e00` | Traverses loaded TrustCache records, checks the entry count and hash type, compares 20-byte CDHashes, and returns a boolean result. |
| `_pmap_lookup_in_static_trust_cache` | `0xfffffff0071b7240` | Performs a binary search over the static v1 cache. On a match it returns the encoded found bit, hash type and flags; otherwise it returns `0`. |
| `_pmap_in_ppl` | `0xfffffff0071b7484` | `mov w0,#0; ret`; the original iOS 12 ARM64 implementation genuinely reports false on this platform. |

The legacy and lookup functions are therefore concrete port candidates. A valid XNU 4903 port must preserve the v1 record layout, UUID duplicate behavior, 20-byte CDHash comparisons, sorted-cache binary search, lock ordering, and the reserved-page pool lifecycle. A fixed success, fixed “found”, or fabricated PPL state would not match the original behavior.

The original `_pmap_load_image4_trust_cache` remains a separate gate. Its body calls platform-specific Image4/security interfaces and performs protected memory and random-token operations. The disassembly proves the ABI and validation shape but does not provide enough evidence to implement those opaque dependencies safely on Y35A.

This audit is host-only. It created no kernel, package, probe, or device result. The next implementation gate is to port the legacy/static/lookup/page-pool subset against the XNU 4903 types, then prove its ABI and TrustCache semantics in a host harness before considering a kernel link. Image4/PPL monitor behavior remains unresolved.

## Follow-up pointer-table and ownership audit — 2026-11-20

The same kernelcache was checked against `__PRELINK_LINKKASLROffsets` to bind the function-pointer slots to their owning KEXTs. In `__PLK_DATA_CONST,__data`, the table at file offset `0x17d8508` / VA `0xfffffff006dfc508` lies in the `com.apple.kec.corecrypto` `__DATA_CONST` range and contains `_pmap_claim_reserved_ppl_page`, `_pmap_free_reserved_ppl_page`, and `_pmap_in_ppl`. A second table at file offset `0x17fbf48` / VA `0xfffffff006e1ff48` lies in the `com.apple.driver.AppleMobileFileIntegrity` `__DATA_CONST` range and contains `_pmap_is_trust_cache_loaded`, `_pmap_load_image4_trust_cache`, `_pmap_load_legacy_trust_cache`, `_pmap_lookup_in_loaded_trust_caches`, and `_pmap_lookup_in_static_trust_cache`. This independently confirms the R155 v6 missing-import grouping: three CoreCrypto imports and five AMFI imports. The table entries prove original linked bindings, not a particular boot-time call path.

The R155 v6 graft plan's owner classification is independently corroborated by those pointer tables. A linear scan of the kernel `__TEXT_EXEC,__text` found no direct `BL` to the six scanned pmap API addresses; that is not a no-call result because indirect calls remain possible and the prelinked KEXT call paths have not been qualified.

The original claim/free routines use the same BSS list head at `0xfffffff00764ab58` and lock word at `0xfffffff00764af58`: claim removes the head and panics if it is empty; free links the supplied node back at the head. The Image4 loader also manipulates that head and contains indirect security-interface calls. The host `ReservedPagePool` model in `r158_trustcache_harness.py` checks only pop/push behavior; it is not an implementation of this shared ownership, lock, or Image4 lifecycle. R158 remains host-only and cannot be used as an AMFI security closure or device candidate.

The AMFI executable also contains five local veneers at `0xfffffff0061f4800` through `0xfffffff0061f4838`. Each uses `ADRP x16, 0xfffffff006e1f000; LDR x16, [x16,#slot]; BR x16`, with slots `0xf48`, `0xf50`, `0xf58`, `0xf60`, and `0xf68` respectively for the five AMFI pmap imports. This proves the original import veneer shape and slot-to-symbol mapping; it does not prove that a boot run reached any veneer. The repeatable audit is `/Users/lingion_k/unixnu-research/UniXNU-y35a/scripts/y35a/audit_r158_pmap_bindings.py`, SHA-256 `dc605c1cfd04bf59a68e2752ba9db538c17d3abe0ce88ba2b1adf0702cae2a53`; its JSON output is preserved in the R158 checkpoint as `r158-pmap-binding-audit.json`.

The local newer XNU source provides a dependency-shape reference, not a drop-in 4903 implementation. In `upstream-refresh/2026-11-11/sources/xnu-current/repo/osfmk/arm/pmap/pmap.c` (SHA-256 `03caf98130be25f3acd3e2b0f9882aadcc912024fa9b1c2e5397ab055ecd82a0`), lines 13065–13138 reserve a CoreCrypto page, validate and lockdown the Image4 payload and manifest, obtain a writable TrustCache structure, call `amfi->TrustCache.load`, unlock the ranges, and release the page. The same source imports `vm/pmap_cs.h` (SHA-256 `8f6a0e3b0f4d9da2337333c8410c14031b9abc2967a51f96bd424c5b48b9c6f6) and uses `TrustCacheRuntime_t`, `pmap_cs_*`, `amfi->TrustCache`, PPL page reservation, and Image4-specific types absent from the 4903 R158 patch. This confirms why returning `PMAP_TC_UNKNOWN_FORMAT` or using the Python page model would not close the real API.
