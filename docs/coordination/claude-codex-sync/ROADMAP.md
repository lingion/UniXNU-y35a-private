# Long-Term UniXNU Acceleration Roadmap

This is the durable work queue for the Claude and Codex collaboration. Work proceeds in dependency order. A later lane does not begin because an earlier lane is interesting; it begins after the earlier lane has a falsifiable acceptance result.

## Lane 1: Evidence and Coordination

Purpose: keep both agents working from the same current state.

Tasks:

- [ ] Read `CURRENT.md` and the newest heartbeat files at the start of every session.
- [ ] Record full image, kernel, probe, and raw capture hashes for every device experiment.
- [ ] Append corrections to `LOG.md`; never silently replace a superseded conclusion.
- [ ] Keep the worktree ownership visible before editing shared files.

Acceptance: Claude and Codex can resume from this directory without relying on chat history, and every active claim points to a raw artifact or source line.

## Lane 2: Measurement Infrastructure

Purpose: make readback evidence capable of distinguishing loaded bytes, shim bytes, and XNU runtime state.

Tasks:

- [ ] Verify every recorded field at its actual width. Do not treat neighboring bytes in a fixed-size record as the field value.
- [ ] Keep the CNTVCT and image-generation witness in every probe image.
- [ ] Reconcile the boot shim segment placement with each probe physical address offline.
- [ ] Prove which storage survives warm reset and which bytes are rewritten by LK, the shim, or XNU.

Acceptance: a probe result can distinguish a static image byte, a boot-shim handoff stamp, and a runtime-mutated XNU field using one controlled experiment.

## Lane 3: Earliest XNU Boot Boundary

Purpose: identify the first failing boundary in XNU-4903 on the real MSM8916 device.

Order:

1. Offline prove the marker implementation and storage address.
2. Add one marker at `arm_init` entry or immediately around `PE_init_platform(FALSE)`.
3. Add one marker around one pexpert boundary per build: `pe_identify_machine`, `pe_arm_init_interrupts`, then `pe_arm_init_debug`.
4. Test ADT `interrupt-controller="master"` as a separate A/B variable.
5. Run on the device only after the current worktree and image provenance gates are clear.

Acceptance: one experiment narrows the failure to a named boundary, or a documented result proves the marker channel itself is not observable at that boundary.

## Lane 4: Platform Foundations

Purpose: make the kernel capable of sustained operation after the earliest boundary is known.

Dependency order:

- GICv2 and timer consumer contract.
- UARTDM console.
- Secondary CPU policy or a deliberate boot-CPU-only mode.
- eMMC/SDCC storage.
- Touch I2C/RMI4.
- Display handoff and framebuffer ownership.
- Wi-Fi and Bluetooth transport.
- Audio and power.
- GPU only after the display and memory contracts are stable.

Acceptance: each driver has source evidence, a focused offline test, and a real-device observation that separates probe success from actual XNU service registration.

## Lane 5: Deep Boot and Userland

Purpose: recover a repeatable path from kernel initialization to launchd and later userspace.

Tasks:

- [ ] Reproduce the 2026-11-06 launchd panic with exact image and rootfs hashes.
- [ ] Capture an XNU-owned panic header or runtime marker before interpreting panic text.
- [ ] Validate TrustCache and rootfs behavior independently from hardware-driver work.
- [ ] Only then investigate launchd, dyld, AMFI, and userspace failures.

Acceptance: a repeatable boot reaches a named userspace milestone with a valid kernel and rootfs provenance record.

## Lane 6: Automation

Possible later automation, only when explicitly scheduled:

- Read-only freshness check for `CURRENT.md`, Git status, new heartbeat evidence, and uncommitted in-flight changes.
- Test and hash verification after a build completes.
- Reminder when the shared log has stale unresolved decisions.

Automation must never boot, flash, reset, or alter the device without a fresh user instruction and a visible run-specific gate.

## Stop Conditions

- Do not run another device experiment when image provenance is ambiguous.
- Do not interpret a handoff stamp as an XNU runtime marker.
- Do not start driver work while the earliest XNU boundary remains unknown, unless the driver is an offline prerequisite for that boundary.
- Do not let a scheduled check mutate source, commit, push, flash, or delete artifacts.
