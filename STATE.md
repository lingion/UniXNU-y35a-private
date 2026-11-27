# UniXNU Y35A state

Updated: 2026-11-28
Final goal: iOS 12.4.1 running on Y35A; D1/D2/D3 IN_PROGRESS / NOT_MET. No verified iOS or interactive SpringBoard boot is recorded.
Current stage: R208 package CI, offline derived-QCDT GPT/APFS control image only.
Current branch: `codex/unixnu-ci-package-v2`; source fix commit `518f8f4` contains the detach-before-pmap change; Actions validation pending.
Device: not queried this turn; no device/USB/fastboot/adb/serial/TF operation performed. `device_run_allowed=false`.
Persistent writes: none this turn. Full partition backup and EDL/firehose recovery remain unverified.

## Latest CI facts

- `46047857330` on `a739997` passed `host-validation`.
- `46047857312` on `a739997` passed `Test package contracts` and design contract; its package, TF intermediate and offline-control jobs were skipped because this was a push event.
- `46047971221` on `a739997` ran `tf-apfs-offline-control`. Package identity and both artifact downloads passed; image creation, APFS attach, root-tree copy and earlier metadata checks proceeded. It failed at `hdiutil pmap -simple` with `Resource temporarily unavailable` because the image was still attached. No offline-control artifact was uploaded.
- Inputs were package run `46038856167`, package artifact `15218633072` / `sha256:620a39a1d222fb2c2ae2bbe62ad180ca103984e9c325bea870a0aba2e341ea76`, and root-tree artifact `15219732795` / `sha256:2437d3f1cb521dc9a6f39918e4ff6de5dc6171019cc652f9e7f236c19a4638bc`.

## Current work and gates

- Commit `518f8f4` unmounts and detaches the APFS image before reading `hdiutil pmap`; a regression test asserts command order. This exact change still needs CI validation.
- Current `hdiutil pmap` parser accepts only an explicit top-level GPT/GUID scheme. GPT, APFS, and whole-disk/volume/parent identity are separate required facts.
- Xattr CLI fallback now uses `xattr -px` and decodes raw bytes before hashing. The structural fallback test passed in the 63-test Actions validation on `a739997`; the byte-equivalence change is pending Actions validation.
- Derived QCDT control images must remain `offline-control-only`, `bootable=false`, `ios_system_image=false`, and `device_run_allowed=false`.
- Trusted stock PD1502A QCDT provenance remains unavailable. No true TF system package, kernel-linked root selection, eMMC fallback implementation, card binding, or device qualification is established.
- No local UniXNU build, test, lint, diff-check, static gate, package or image validation is allowed. Accidental local `git diff --check` output from this turn is explicitly excluded as evidence.

## Next actions

1. Commit/push the detach-before-pmap ordering fix and its CI regression test; wait for exact-SHA host/package validation.
2. If validation passes, run one offline-control dispatch against the same verified package and root-tree artifacts; record actual job result and artifact hashes.
3. Keep the main goal D1/D2/D3 unmet. Do not claim device readiness or start device/TF work from an offline-control result.

Workspace: `/Users/lingion_k/unixnu-ci-package-worktree` is the active package topic worktree. `/Volumes/Mobile` has previously returned I/O errors; do not scan or write it. `/Volumes/Portable` is temporary staging only.
