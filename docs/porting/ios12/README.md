# iOS 12.4.1 port (j96ap userland on vivo Y35A / MSM8916) — design set

Decision record for the pivot: `docs/board/pivot-ios12.md`. Board register facts:
`docs/board/y35a-facts.md`. 4570 audit findings: `docs/board/audit-4570-findings.md`.

Baseline note: these design documents were synthesized on 2026-11-04 against xnu-4570. The
active target is XNU-4903, as recorded in `GOAL.md` and `docs/board/pivot-ios12.md`. Treat
kernel API, source-location, ABI, and build-integration details here as historical until
verified against the active XNU-4903 source. Board facts remain tied to their cited captures.

| Document | Scope |
| --- | --- |
| [boot-chain.md](boot-chain.md) | How xnu-4570 boots on non-Apple arm64 (ADT-only device tree, polled console, generic-timer fallback, WT kernel integrity, packed `_PrelinkLinkKASLROffsets`); what the format-1 pipeline (build_native → emit_prelink → package_native → EL1 shim) carries over; delta list D1-D9; boot prerequisites checklist; evidence corrections |
| [drivers-plan.md](drivers-plan.md) | Per-driver engineering for touch (S3202 RMI4 over QUPv2 I2C-5), GPU (Adreno a306, no GMU), WiFi (WCN3620 via sdhc2 + SMD transport), BT (H4 over BLSP1 HS-UART), storage (SDHCI eMMC beyond SPEC.md): register facts with dts line refs, IOKit class contracts, on-disk reference inventory, host-test strategy, build integration, ordered risk list |
| [migration-order.md](migration-order.md) | Gated sequence from "kernel builds in container" to "flashed, all four hardware domains verified on device": Phase 0 blocked-fact resolution, Phase 1 board config + build, Phase 2 boot to launchd, Phase 3 interrupt gate, Phase 4 domain order, Phase 5 flash + acceptance sweep |

All three synthesize four read-only recon reports (labels R1-R4) collected 2026-11-04;
facts not present in those reports are marked (verify).
