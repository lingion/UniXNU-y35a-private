# R326 entry transfer diagnostics — 2026-11-21

The device was serial efff9d92, product lk2nd-msm8916, unlocked=yes. Every run used fastboot boot; no persistent partition or userdata write occurred. The device returned to fastboot after each paired run.

Durable assets are under /Users/lingion_k/unixnu-research/reboot-checkpoints/2026-11-21-r326-entry-transfer-diagnostics/. The durable asset index is asset-index.json.

## Measured boundary

The matched paired V14 run proved the following current-generation sequence:

- __start transferred to _start_first_cpu.
- _start_first_cpu executed the R84FS00 store at boot_args+0xa00.
- The original DC CIVAC, DSB, LDR readback, STR to boot_args+0xa08, and second clean sequence were tested by V17.
- The shim entry_return path executed after the branch-back.

The decisive V14 candidate bound records were fresh: raw 0x106e0 = R84FS00 and raw 0x106f0 = RRET0GR0. Baseline bound records were zero and final records were zero in the fresh V14 capture.

V17 used a probe that cleared boot_args+0xa00 and boot_args+0xa08 before capture. Its candidate also produced fresh R84FS00 and RRET0GR0 in the bound report records. This confirms the XNU readback sequence was executed after the R84FS store, subject to the exact V17 manifest mapping.

The next measured marker, PREARGS0, was then reached in V18. V18 candidate raw has fresh PREARGS0 at the bound report record; baseline and final are clear. V19 similarly produced fresh BAVIRT00.

## Evidence limits

The current ladder does not prove AMFI, launchd, root mount, Apple Logo, display, SpringBoard, touch, storage, or a complete iOS boot. It only proves the early _start_first_cpu instruction ladder through BAVIRT00 for the paired diagnostic variants.

Report offsets must be decoded from each probe readback.json. Do not infer raw offsets by adding a fixed 0x10000 to every manifest offset. The paired probes use custom report clearing and explicit record destinations to avoid stale retained values.

## Formal object audit

A separate host-only formal object audit is preserved at /Users/lingion_k/unixnu-research/reboot-checkpoints/2026-11-21-r326-formal-object-audit/.

- pmap.o: SHA-256 90912b686542a15183a5655eefdc278b88726abcc5ade5f3cd533686c39d56e8
- arm_vm_init.o: SHA-256 fa8070cd99d20e68262ab0a6c17e95d91d106539c22d0bcf793ee94faea895c7
- verification-final.json: SHA-256 19f8065f6da6c6afd3b14f5108d0e64731c8dc5a3193fb8c114b68189f26d248

The report states LC_BUILD_VERSION platform 2, minimum OS 12.4, SDK 16.4, CONFIG_PGTRACE enabled, zero UBSan-minimal undefined symbols, and no link or device qualification. The objects remain host artifacts.
