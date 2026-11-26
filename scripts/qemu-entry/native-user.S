// SPDX-License-Identifier: BSD-2-Clause-Patent
// A signed, static Darwin test process. No Apple userspace bytes or MMIO.
.text
.p2align 2
.global _start, _checkpoint
_start:
  mov x16, #20
  svc #0x80
  adrp x19, _results@PAGE
  add x19, x19, _results@PAGEOFF
  str x0, [x19]
  mrs x9, nzcv
  str x9, [x19, #16]
  adrp x0, _mib@PAGE
  add x0, x0, _mib@PAGEOFF
  mov x1, #2
  adrp x2, _user_page_size@PAGE
  add x2, x2, _user_page_size@PAGEOFF
  adrp x3, _old_length@PAGE
  add x3, x3, _old_length@PAGEOFF
  mov x4, #0
  mov x5, #0
  mov x16, #202
  svc #0x80
  str x0, [x19, #8]
  mrs x9, nzcv
  str x9, [x19, #24]
#ifdef NATIVE_FP_CONTEXT_PROBE
#include "native-fp-context.inc"
#endif
#ifdef NATIVE_APFS_LAUNCHD_PROBE
#include "native-apfs-launchd.inc"
#endif
#ifdef NATIVE_APFS_FILE_PROBE
#include "native-apfs-mount.inc"
#endif
#ifdef NATIVE_CACHE_LEAF_PROBE
#include "native-cache-leaf.inc"
#endif
#ifdef NATIVE_FILE_PROBE
#include "native-file-probe.inc"
#endif
.p2align 2
_checkpoint:
#ifdef NATIVE_DEVICE_EXIT_PROBE
  // Deliberate init exit provides the standard kernel panic as a serial-less
  // hardware observation. 73 means all checked syscall results matched.
  mov x0, #81
  ldr x9, [x19]
  cmp x9, #1
  b.ne device_exit
  mov x0, #82
  ldr x9, [x19, #16]
  tbnz x9, #29, device_exit
  mov x0, #83
  ldr x9, [x19, #8]
  cbnz x9, device_exit
  mov x0, #84
  ldr x9, [x19, #24]
  tbnz x9, #29, device_exit
  mov x0, #85
  adrp x9, _user_page_size@PAGE
  ldr x9, [x9, _user_page_size@PAGEOFF]
  cmp x9, #4096
  b.ne device_exit
#ifdef NATIVE_FP_CONTEXT_PROBE
  mov x0, #86
  ldr x9, [x26]
  cbnz x9, device_exit
  mov x0, #87
  ldr x9, [x26, #8]
  cmp x9, #32
  b.ne device_exit
  mov x0, #88
  ldp x9, x10, [x26, #56]
  cmp x10, x9
  b.ls device_exit
  mov x0, #74
#else
  mov x0, #73
#endif
.p2align 2
device_exit:
  mov x16, #1
  svc #0x80
#endif
  b _checkpoint
.data
.balign 8
.global _results, _user_page_size, _old_length
_results:
  .quad 0, 0, 0, 0
_mib:
  .word 6, 7 // CTL_HW, HW_PAGESIZE from Darwin 23 sys/sysctl.h
_user_page_size:
  .quad 0
_old_length:
  .quad 8
