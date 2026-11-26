# R155 AMFI graft design: geometry solved, API closure remains

Date: November 15, 2026.

R154 directly measured `__mac_syscall("AMFI", 90)` returning `ENOPOLICY` because no AMFI policy name or callback was registered. The next candidate must therefore carry the original iOS 12 security extensions and preserve their signature and TrustCache behavior.

## What is ruled out

The existing in-place legacy emitter cannot accept either the R154 DEVELOPMENT kernel or the R153 T7000 RELEASE kernel. It requires matching kernel segment and sized-section geometry. The 16G102 cache is `out/ipsw/16G102/kernelcache.decompressed`, SHA-256 `70e80388d42fe2376096bb6248073b0380dd87b85b1a792b36205ba60c722ce1`. R153 is `/private/tmp/xnu4903-r153-release-20261115-piy14xxp/obj/RELEASE_ARM64_T7000/mach.release.t7000.unstripped`, SHA-256 `a9e87e323522877e91c414432766f845c94dee265ad69309a338ab9991530003`.

R153 already has the correct `__TEXT` base, but its `__TEXT` is `0x7c000` rather than `0x74000`; its `__DATA_CONST`, `__TEXT_EXEC`, `__KLD`, `__DATA`, `__BOOTDATA`, `__LINKEDIT`, and sized sections also differ. Linker flags alone cannot satisfy the current emitter's exact-layout contract.

## Host-only graft result

A reproducible planner at `kits/XnuPrelink/legacy_graft_plan.py` uses the legacy 16G102 metadata and the R153 export table. The minimal security closure is exactly these three original components:

* `com.apple.driver.AppleMobileFileIntegrity`
* `com.apple.kext.CoreTrust`
* `com.apple.kec.corecrypto`

For that closure, the original KASLR table contains 261 component-to-component bindings and 530 resolvable kernel bindings against R153. The planner records eight unresolved exports and zero address collisions. It also runs the existing PC-relative instruction inventory over the selected KEXTs: 10,273 encodings resolve within the selected component extents. This supports that a common slide preserves those relative references, but register dataflow remains unqualified. A uniform prelink slide of `0x2000000` avoids every non-empty R153 kernel segment and the complete original prelink segment ranges. This shows that a relocation-aware graft emitter is a credible host experiment; it does not make the result bootable.

The full 170-root closure is unsuitable for this first candidate because it introduces unrelated networking and accelerator APIs. The three-component closure is the correct first security experiment.

## Existing XNU 4903 early-security load hook

The 4903 source already contains the intended early loading path. `libsa/bootstrap.cpp` installs `bootstrapLoadSecurityExtensions` in `KLDBootstrap` construction (around line 179). `osfmk/kern/startup.c:351` calls `mac_policy_init()`; later `startup.c:630-631` calls `mac_policy_initmach()`. `security/mac_base.c:399-411` invokes `load_security_extensions_function()` before setting `mac_late=1`. The bootstrap loader walks `OSKext::copyKexts()`, filters Apple bundle IDs with `AppleSecurityExtension=true`, and calls `OSKext::loadKextWithIdentifier(..., false)` (`bootstrap.cpp:733-771`).

The 16G102 `__PRELINK_INFO` entry for `com.apple.driver.AppleMobileFileIntegrity` has `AppleSecurityExtension=true`; it declares `com.apple.kext.CoreTrust` and `com.apple.kec.corecrypto` dependencies. The host planner records these exact fields. Thus the loader hook does not need a new early-init patch: a correct prelinked metadata dictionary and the original executable KEXTs are the required inputs. This source order makes early AMFI registration plausible, but only a successful device run can prove the opaque Apple KEXT registers `AMFI` as expected.

## Hard blocker

The three-component closure requires these R153 kernel exports:

* `_pmap_is_trust_cache_loaded`
* `_pmap_load_image4_trust_cache`
* `_pmap_load_legacy_trust_cache`
* `_pmap_lookup_in_loaded_trust_caches`
* `_pmap_lookup_in_static_trust_cache`
* `_pmap_claim_reserved_ppl_page`
* `_pmap_free_reserved_ppl_page`
* `_pmap_in_ppl`

The exact XNU 4903 tree used by R154 has no ARM or ARM64 implementation for any of them. The two loader names have only x86 refusal stubs in `osfmk/x86_64/pmap.c`; the lookup and PPL names are declarations in the build overlay, and `pmap_is_trust_cache_loaded` has no declaration or definition in the searched tree. The kernel also has no `trustcache.c`; `osfmk/kern/trustcache.h` only declares the legacy data structures and lookup helpers.

Returning success, “found”, or a constant PPL state would fabricate security semantics and is prohibited. The next implementation gate therefore needs a matching ARM64 source or a reviewed, byte- and behavior-compatible TrustCache implementation. Until that exists, no R155 device boot is justified.

## Separate UI blocker

Even a successful AMFI graft would only move the current 42,991,616-byte RAM HFS root past the dyld policy check. SpringBoard, the 1,269,743,616-byte dyld shared cache, and the launch daemon set remain on the 16G102 APFS system volume. The APFS volume cannot fit in the current RAM boot window or Android `system`, and the Y35A eMMC write/mount path has no Phase 1 device proof. Therefore the graft is the next security milestone; a visible iOS SpringBoard boot still requires the storage/root milestone afterward.

Status: host design only. No source, build, package, device, fastboot, or persistent-storage change was made by this record.
