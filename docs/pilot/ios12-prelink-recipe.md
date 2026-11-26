# iOS 12 legacy-prelink recipe (16G102 / j96ap)

Operational facts proven against the on-disk cache
`out/ipsw/16G102/kernelcache.decompressed` (sha256
`70e80388d42fe2376096bb6248073b0380dd87b85b1a792b36205ba60c722ce1`, 30,228,480 B,
arm64 MH_EXECUTE, 22 load commands, 15 segments) by `kits/XnuPrelink/legacy_prelink.py`
and `tests/ios12-prelink/test_ios12_prelink.py`. Evidence JSONs:
`evidence/y35a-20261102/ios12-prelink-{roundtrip,plan,real-p1-refusal}-20261105.json`.

## __PRELINK_INFO dialect

- Segment `__PRELINK_INFO`: fileoff `0x1ad0000`, filesize `0x204000` (2,113,536 B);
  effective payload is a 2,099,530 B **bare `<dict>` body** — no `<?xml?>`, no DOCTYPE,
  no `<plist>` wrapper, no CDATA — then exactly one NUL and all-zero padding.
- Top level is exactly three keys: `_PrelinkInfoDictionary` (193 entries),
  `_PrelinkLinkKASLROffsets` (`<uint32 count=251829, uint32 offsets[]>`), `_PrelinkKCID`
  (16 B, top level only; **no** per-module `_PrelinkKCID`, **no** `_PrelinkKextPList`,
  **no** KernelCollection keys anywhere in the file).
- Integers: `<integer size="64">lowercase-hex</integer>`; references are the **bare**
  `<integer IDREF="n"/>` — `size=` appears on definitions only (all 1,827 references in
  the bytes carry no `size=`). Negatives render `-0x…`.
- Interning (kextc OSSerializer): integers intern by VALUE globally (389 definitions),
  strings intern only by OBJECT identity (2,106 `string IDREF` uses; `KEXT` appears 193
  times as distinct instances and never gets an ID; `English` interns). One counter is
  shared across both kinds in write order. dict/array/data/bool never intern.
  Byte-exact re-encode roundtrip reproduced on CPython 3.10/3.12/3.13 — no small-int
  identity dependency (the earlier 3.12-only claim was wrong).

## Component plan (derived, not hardcoded)

193 entries = 184 with executable addrs (7 KPI stubs on the 128-byte stride grid +
177 MH_KEXT_BUNDLE modules) + 8 codeless (personalities, no exec fields) + 1 pruned
(no personalities, no exec fields). KASLR sites: 251,829 = 75,712 component→component +
171,556 component→kernel-export + 4,561 in dropped modules + 0 NULL (this build ships
none; do not assume NULL sites exist). Excluded (pointer-opaque, derived): 4 interior-
pointer sources (ASIOKit, FairPlayIOKit, LSKDIOKit, LSKDIOKitMSE) + 3 transitive
(IOAudioCodecs pointer-edge, IOTextEncryptionFamily and AppleVXD393 via
OSBundleLibraries). Roots = 170. `DispAlg`/`AppleMultiPath`/`AVECore`/`AppleMg2Controller`
do not exist in this cache.

## Emit contract

- In-place rewrite (no relink): kernel slice replaced segment-by-segment; parent header
  `[0, 32+sizeofcmds)` + unreferenced `__TEXT` gap, entire `__LINKEDIT`, and all prelink
  bytes stay cache-owned. Native kernel must match cache kernel-slice geometry
  (vmaddr/vmsize/fileoff/filesize per segment; sized-section file extents) or emit
  refuses naming the segment. slide must be 0 (iOS 12 ships unslid; boot adds
  `vm_kernel_slide` through the table).
- Kernel-bound KASLR sites are name-relinked to the fresh kernel's exports; retained
  sites into excluded modules raise `Undeclared pointer dependency`; opaque interior
  sites raise `Unresolvable pointer target`.

## Open gate (link-edit, blocker for a runtime candidate)

- The built P1 `out/y35a/ios12-kernel.noctf` (xnu-4903.270.47 T7001 DEVELOPMENT,
  sha256 `5fd4e6b5f7fa10e1b2cc9323ac5802833c15479fce5c67068f2ba8837fdcdc94`, 15 segments,
  `__TEXT` vmaddr already `0xfffffff007004000`) is refused today at `__TEXT` vmsize
  `0xc4000` vs cache `0x74000`. Link-edit P1 to the cache slice layout (or rebuild with
  matching segment sizing) before any `--command emit --kernel` run.
- 16G102 ships xnu-4903.272.1 (iPad mini 4 was **not** built from 4570/iOS 11.3); the
  recipe's kernel source baseline is the 4903 line.
