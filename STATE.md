# UniXNU Y35A state

Updated: 2026-11-28
Final goal: iOS 12.4.1 running on Y35A; D1/D2/D3 IN_PROGRESS / NOT_MET. No verified iOS or interactive SpringBoard boot is recorded.
Current stage: R208 package CI, offline derived-QCDT GPT/APFS control image only.
Current branch: `codex/unixnu-ci-package-v2`; validated package candidate source commit `23502821148473f4baa411ec4dfe81745a4a9aa7`.
Device: not queried this turn; no device/USB/fastboot/adb/serial/TF operation performed. `device_run_allowed=false`.
Persistent writes: none this turn. Full partition backup and EDL/firehose recovery remain unverified.

## Latest CI facts

- `46047857330` on `a739997` passed `host-validation`.
- `46047857312` on `a739997` passed `Test package contracts` and design contract; its package, TF intermediate and offline-control jobs were skipped because this was a push event.
- `46047971221` on `a739997` ran `tf-apfs-offline-control`. Package identity and both artifact downloads passed; image creation, APFS attach, root-tree copy and earlier metadata checks proceeded. It failed at `hdiutil pmap -simple` with `Resource temporarily unavailable` because the image was still attached. No offline-control artifact was uploaded.
- `46049199580` and `46049199572` on `2350282` passed host-validation and all 64 package contract tests.
- `46049301112` on `2350282` completed successfully, including `tf-apfs-offline-control`, and uploaded `y35a-tf-apfs-offline-control-46049301112`, ID `15224410131`, digest `sha256:4182dbabd5303ffb1a348221150a774ac7b1b308504573afd1c0ec1edadd3c74`.
- Control image SHA-256 `8b7fae9326a0530f231487e1b48735b92780069aa11bef970b38e74c8bf093d4`, 4 GiB; report SHA `62884f559efa7d9861738db5c977f9c82d352fd68467cc2310af4fa5ac50c3cd`; report binding SHA `be14ac1ac9a3feefae4056eaba0bfb37639adb34f671e22f20c7f898c18564cd`.
- The report confirms CI-image scheme `GPT` and whole disk/volume/parent `disk6`/`disk6s1`/`disk6`. This is a GitHub runner disk image, not a physical TF card binding.
- Inputs were package run `46038856167`, package artifact `15218633072` / `sha256:620a39a1d222fb2c2ae2bbe62ad180ca103984e9c325bea870a0aba2e341ea76`, and root-tree artifact `15219732795` / `sha256:2437d3f1cb521dc9a6f39918e4ff6de5dc6171019cc652f9e7f236c19a4638bc`.

## Current work and gates

- Commit `518f8f4` moves pmap inspection after successful unmount/detach; run `46049301112` validates the sequence and uploads the control artifact.
- Current `hdiutil pmap` parser accepts only an explicit top-level GPT/GUID scheme. GPT, APFS, and whole-disk/volume/parent identity are separate required facts.
- Xattr CLI fallback uses `xattr -px` and decodes raw bytes before hashing. Its forced fallback contract test passed in the 64-test Actions validation on `2350282`; the macOS control job also completed the restored-tree metadata check.
- Derived QCDT control images must remain `offline-control-only`, `bootable=false`, `ios_system_image=false`, and `device_run_allowed=false`.
- Trusted stock PD1502A QCDT provenance remains unavailable. No true TF system package, kernel-linked root selection, eMMC fallback implementation, card binding, or device qualification is established.
- No local UniXNU build, test, lint, diff-check, static gate, package or image validation is allowed. Accidental local `git diff --check` output from this turn is explicitly excluded as evidence.

## Next actions

1. Search for trusted stock PD1502A QCDT provenance only in readable repository/cache/CI-artifact sources; do not scan `/Volumes/Mobile` after its prior I/O errors.
2. Close kernel-linked TF root selection and eMMC fallback implementation/contracts, then build the production root/package/probe chain in GitHub Actions.
3. Keep the main goal D1/D2/D3 unmet. The derived-QCDT control artifact does not authorize or prove device/TF boot.

Workspace: `/Users/lingion_k/unixnu-ci-package-worktree` is the active package topic worktree. `/Volumes/Mobile` has previously returned I/O errors; do not scan or write it. `/Volumes/Portable` is temporary staging only.
