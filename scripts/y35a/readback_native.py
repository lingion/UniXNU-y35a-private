#!/usr/bin/env python3
"""Build a RAM-only diagnostic that reads retained kernel globals then resets.

This is not XNU. Run only after verifying the Y35A PMIC warm-reset settings.
The original kernel must match the preceding boot. No storage writes occur.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
from boot_layout import parse_macho, physical_base_for
from package_native import select_device_dt, android_container, align

NAMES = ('_BootArgs', '_const_boot_args', '_gPanicBase', '_gPanicSize',
         '_debugger_panic_str', '_panicDebugging', '_debug_buf_base',
         '_debug_buf_ptr', '_debug_buf_size',
         '_armdt_platform_configured', '_armcpu_registered',
         '_armcpu_timer_interrupts', '_armcpu_gic_boot', '_native_entry_trace',
         '_original_faulting_state', '_native_early_fault_address', '_excepstack', '_intstack',
         '_native_crypto_emulations')
# Keep the name-addressed readback allocation inside lk2nd's 0x11000-byte stage.
RECORD_LIMIT = 0xf000
PANIC_LOG_LIMIT = 0x1000
STAGE_BASE = 0x859e0000
STAGE_BYTES = 0x11000
PANIC_LOG_DEST = 0x859f0000
PANIC_LOG_OFFSET = PANIC_LOG_DEST - STAGE_BASE
# R9 minimal-boundary transport: pram is snapshotted to verified LK scratch
# before ANY write, every probe byte lands in the 0x1000 report page above
# pram, and pram is restored before the forced reset. The upload then
# carries untouched XNU-owned pram (a real KNUF answer) plus the report.
# 0x95000000 is inside lk2nd download scratch (0x90000000..0xa0000000) and
# clear of the boot3 RAMDisk placement (0x90aea000..0x933ea000).
SCRATCH_PRAM_BACKUP = 0x95000000
SCRATCH_PRAM_BACKUP_BYTES = 0x10000
REPORT_BASE = PANIC_LOG_DEST
REPORT_BYTES = 0x1000
# Report head 0x00..0x40 is never written: it holds the boot3 shim Y35AXNU2
# stamp (package_native.py writes 24 bytes there before branching to XNU),
# which the generation-witness chain reads back.
REPORT_HEAD_PRESERVED = 0x40
REPORT_RECORDS_OFFSET = 0x100
# CNTVCT_EL0 is monotonic within one power cycle: two distinct probe executions
# can never stamp the same value. Offset 16 was reserved-zero padding before
# this witness; readers compare it across captures to distinguish a re-run
# probe from a re-read of the same staged buffer.
FRESHNESS_WITNESS_OFFSET = 16
# STAGE_BASE == pram reg base == 0x859e0000: the marker/header writes below
# would destroy an XNU-written embedded panic header (KNUF, 0x74 packed bytes
# at pram+0) in-place before the host could read it. The probe snapshots the
# header to this stage-tail slot FIRST. 0xf800 keeps it clear of the
# fault-state staging slot (0xf000, 1024B reserved) and of PANIC_LOG_DEST
# (0x10000).
EPH_SNAPSHOT_OFFSET = 0xf800
EPH_SNAPSHOT_BYTES = 0x74
EPH_SNAPSHOT_WRITE_BYTES = 0x80  # 8 ldp/stp pairs actually written by entry
# PANIC_LOG_DEST is also the RAMBoot shim's Y35AXNU2 stamp page
# (package_native.py:76/131) — the generation witness read back at staged
# offset 0x10000 (baf4604 §8). The dynamic debug-buffer copy is the first
# code in this probe that can legitimately write there, so the first 64
# stamp bytes are snapshotted to this free stage-tail slot before the copy.
STAMP_SNAPSHOT_OFFSET = 0xf900
STAMP_SNAPSHOT_BYTES = 64
EPH_MAGIC_WORD = 0x46554E4B  # 'FUNK' little-endian
# gPanicBase is ml_io_map_wcomb(pram_phys) (pe_init.c): the panic window's PA
# is this constant regardless of the VA the kernel stored in its carriers.
PRAM_PHYS = STAGE_BASE
# Purpose-field fence the host reader requires: stage base IS the DT pram reg
# base, and the panic-log copy is fenced ahead of table staging (order in
# preservation_entry_source). Exported so manifest and tests share one truth.
PRAM_FENCE_NOTE = 'stage aliases DT pram; panic copy fenced ahead of table staging'
REQUIRED = ('_BootArgs', '_gPanicBase', '_gPanicSize', '_debugger_panic_str',
            '_panicDebugging', '_debug_buf_base', '_debug_buf_ptr', '_debug_buf_size')
DEBUG_BUFFER_CARRIERS = ('_debug_buf_base', '_debug_buf_ptr', '_debug_buf_size')
PANIC_WINDOW_CARRIERS = ('_gPanicBase', '_gPanicSize')
# Field-width reads that fit the minimal-boundary report page: the REQUIRED
# carriers, the pointer-table siblings, and the patch-time glue flags. Stacks
# and debug-text windows are full-readback-only by construction.
BOUNDARY_NAMES = REQUIRED + ('_const_boot_args', '_armdt_platform_configured',
                             '_armcpu_registered', '_armcpu_timer_interrupts',
                             '_armcpu_gic_boot', '_native_entry_trace',
                             '_native_crypto_emulations')


def validate_required_symbols(symbols):
    missing_required = sorted(set(REQUIRED) - set(symbols))
    if missing_required:
        raise ValueError('Required 4903 carriers missing from kernel symbols: ' + ', '.join(missing_required))


# Logical field widths from xnu-4903.270.47 source types (this repo builds
# with BUILD_DSYM=0, so the table is the derivation record; when a .dsym is
# present it wins and the table must agree — see the dsym test's file:line
# citations). Windows in copy tables stay 16-aligned via _record_size; the
# manifest publishes field_bytes so the host never reads neighbors as field.
FIELD_BYTES = {
    '_panicDebugging': 4, '_gPanicSize': 4, '_debug_buf_size': 4,
    '_armdt_platform_configured': 4, '_armcpu_registered': 4,
    '_native_crypto_emulations': 4,
    '_gPanicBase': 8, '_debug_buf_base': 8, '_debug_buf_ptr': 8,
    '_debugger_panic_str': 8, '_BootArgs': 8,
    '_native_early_fault_address': 8, '_armcpu_timer_interrupts': 8,
    '_original_faulting_state': 8,
    '_const_boot_args': 0x180,
    '_armcpu_gic_boot': 32,
    '_intstack': 32768, '_excepstack': 16384,
    # Coordinator 10:2x ruling: the rebuilt instrumented kernel's entry-trace
    # array is 512 bytes; width only matters when the symbol exists.
    '_native_entry_trace': 512,
}


def field_bytes(name):
    """Logical field width, exactly the 4903 source type (coordinator
    ruling): 4 for boolean_t/unsigned int, 8 for pointers/vm_offset_t,
    sizeof for structs and arrays, full extents for stacks. Copy windows
    stay 16-aligned via _record_size for the ldp/stp table; field_bytes is
    what the host decode must consume — anything outside it is neighbor."""
    return FIELD_BYTES.get(name)


def read_field_bytes(name, symbols, dsym=None, dsym_path=None):
    """Authoritative logical width: real DWARF (.dsym) when provided, else
    the table above. _native_entry_trace exists only if the symbol table
    carries it — entry-trace symbol not resolved means NO record, never a
    hard-coded physical fallback. Absent names with no table entry return
    None (caller skips); REQUIRED presence is enforced separately."""
    if name == '_native_entry_trace' and name not in symbols:
        return None
    if dsym is not None:
        size = dsym.type_size(name)
        if size is not None:
            return size
        # DWARF silent (no such symbol in this build's debug info): fall
        # back to the source table. Entry-trace absence is already decided
        # by the symbol-table guard above, never here.
    if dsym_path is not None:
        return _dsym_field_bytes(dsym_path, name) or field_bytes(name)
    return field_bytes(name)


def parse_dwarf_type_size(dump_text, pointer_size=8):
    """Pure parser over one llvm-dwarfdump DIE printout: return the logical
    byte size if this DIE answers it, else None. Handles DW_AT_byte_size
    (base types, structs, most arrays), DW_TAG_pointer_type, and arrays
    without byte_size by element size times upper bounds (resolved by the
    caller via nested dumps). Kept narrow on purpose: only the question
    'what is the field width' is asked; anything else falls back to the
    source table."""
    m = re.search(r'DW_AT_byte_size[^(]*\((0x[0-9a-f]+)\)', dump_text, re.I)
    if m:
        return int(m.group(1), 16)
    if 'DW_TAG_pointer_type' in dump_text:
        return pointer_size
    if 'DW_TAG_subrange_type' in dump_text or 'DW_TAG_array_type' in dump_text:
        bounds = [int(b, 16) for b in re.findall(r'DW_AT_upper_bound[^(]*\((0x[0-9a-f]+)\)', dump_text, re.I)]
        if bounds and 'DW_TAG_array_type' in dump_text:
            return ('array', bounds)
    return None


def _dsym_offset_die(dsym_path, offset):
    try:
        return subprocess.check_output(
            [_tool_path('llvm-dwarfdump'), '--offset', f'{offset:#x}', str(dsym_path)],
            text=True, stderr=subprocess.DEVNULL)
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return None


def _dsym_field_bytes(dsym_path, name):
    # DWARF lookup: variable -> DW_AT_type -> size, with one array element
    # round and typedef deref; any gap answers None and the table rules.
    try:
        out = subprocess.check_output(
            [_tool_path('llvm-dwarfdump'), '--name', name, str(dsym_path)],
            text=True, stderr=subprocess.DEVNULL)
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return None
    m = re.search(r'DW_AT_type\s+.*<0x([0-9a-f]+)>', out)
    if not m:
        return None
    size = _resolve_dsym_offset(dsym_path, int(m.group(1), 16), 0)
    return size


def _resolve_dsym_offset(dsym_path, offset, depth):
    if depth > 6:
        return None
    die = _dsym_offset_die(dsym_path, offset)
    if die is None:
        return None
    parsed = parse_dwarf_type_size(die)
    if isinstance(parsed, tuple):
        elem_m = re.search(r'DW_AT_type\s+.*<0x([0-9a-f]+)>', die)
        if not elem_m:
            return None
        elem = _resolve_dsym_offset(dsym_path, int(elem_m.group(1), 16), depth + 1)
        return None if elem is None else elem * (parsed[1][0] + 1)
    if parsed is not None:
        return parsed
    if 'DW_TAG_typedef' in die:
        ref = re.search(r'DW_AT_type\s+.*<0x([0-9a-f]+)>', die)
        if ref:
            return _resolve_dsym_offset(dsym_path, int(ref.group(1), 16), depth + 1)
    return None


def decode_field(window, width, boolean=False):
    """Host-side exact decode: read only the logical field bytes, never the
    padded window. panicDebugging is boolean_t — only FALSE(0)/TRUE(1) are
    valid; the r7 0x100 must surface as invalid, not be reinterpreted."""
    raw = window[:width]
    if boolean:
        if len(raw) < 4:
            raise ValueError('boolean field window too short')
        value = int.from_bytes(raw[:4], 'little')
        if value not in (0, 1):
            raise ValueError(f'boolean_t field holds {value:#x}, neither FALSE nor TRUE')
        return value
    return int.from_bytes(raw, 'little')


def parse_extra_pa(spec):
    """Parse a raw physical-address record 'name=0xADDR:SIZE'. These bypass
    the symbol table: they let a run settle residency questions whose
    addresses live outside symbol-derived VA translation (e.g. the kernel
    entry codeword, the LK-written boot-args page)."""
    name, _, rest = spec.partition('=')
    if not name or ':' not in rest:
        raise ValueError('extra record must be name=0xADDR:SIZE: ' + spec)
    addr, _, size = rest.partition(':')
    try:
        addr_i, size_i = int(addr, 16), int(size, 10)
    except ValueError:
        raise ValueError('extra record needs hex ADDR and decimal SIZE: ' + spec)
    if not addr_i or not size_i or size_i % 16:
        raise ValueError('extra record needs nonzero 16-aligned SIZE and nonzero ADDR: ' + spec)
    return dict(name=name, physical=hex(addr_i), size=size_i)


def validate_stage_footprint(records):
    if not records:
        raise ValueError('Readback has no records')
    total = 64 + sum(r['size'] for r in records)
    if total > RECORD_LIMIT:
        raise ValueError('Readback exceeds the bounded diagnostic allocation')
    if PANIC_LOG_OFFSET + PANIC_LOG_LIMIT > STAGE_BYTES:
        raise ValueError('Panic log does not fit in bounded staged allocation')
    return PANIC_LOG_OFFSET


def write_manifest(path, manifest):
    path.write_text(json.dumps(manifest, indent=2) + '\n')


def _tool_path(name):
    candidates = [
        shutil.which(name),
        f'/Library/Developer/CommandLineTools/usr/bin/{name}',
        f'/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/{name}',
        f'/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/native/llvm/bin/{name}',
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return candidate
    raise FileNotFoundError(f'Unable to locate required tool: {name}')


def _compiler_path():
    candidates = [
        shutil.which('clang'),
        f'/Library/Developer/CommandLineTools/usr/bin/clang',
        f'/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/clang',
        f'/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/native/llvm/bin/clang',
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return candidate
    raise FileNotFoundError('Unable to locate required tool: clang')


def _linker_environment():
    llvm_dir = '/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/native/llvm/bin'
    path = os.environ.get('PATH', '')
    if llvm_dir not in path.split(os.pathsep):
        path = os.pathsep.join((llvm_dir, path)) if path else llvm_dir
    return dict(os.environ, PATH=path)


def _record_size(name):
    # Copy window: 16-aligned minimum for the ldp/stp table, full extents
    # for structs/stacks. The LOGICAL width is field_bytes (see
    # read_field_bytes); neighbors inside a padded window are never evidence.
    return {
        '_intstack': 32768,
        '_excepstack': 16384,
        '_native_early_fault': 384,
        '_smsg_bufc': 0xd000,
        '_const_boot_args': 384,
        # ArmCpu.cpp:33 uint32_t armcpu_gic_boot[8] = 32B: entries 4..7 are
        # GIC PMR/IG/SRE state, a 16B window drops them silently.
        '_armcpu_gic_boot': 32,
        # Phase-marker array in the rebuilt instrumented kernel (absent from
        # the vanilla 5fd4 table, where it contributes no record at all).
        '_native_entry_trace': 512,
    }.get(name, 16)


def preservation_entry_source(*, records, symbols, layout, physical_base, kernel_sha256):
    """Emit the entry shim from the resolved records and kernel symbol addresses.

    Ordering contract: STAGE_BASE is the pram physical base itself, so the
    probe's own marker stores land on panic-header bytes — the KNUF snapshot
    at the very top of enter precedes every stage write. The dynamic
    debug-buffer capture reads the PRAM window [gPanicBase, +gPanicSize),
    and the record table stages kernel globals INTO that same window at
    offsets 0x40..; the panic bytes must therefore move to PANIC_LOG_DEST
    (outside PRAM) BEFORE the record copies run, or the probe overwrites
    its own evidence (boot4-empty-readback section 5 proved the valid text
    range sat under the record + excepstack writes). Guard failures fall
    through to set_table so the scalar records — the fallback when carriers
    read zero — are still staged.
    """
    validate_stage_footprint(records)
    table = '\n'.join(
        f" .quad {r['physical']}, {STAGE_BASE + r['offset']:#x}, {r['size'] // 16}"
        for r in records
    )
    indirect = ''
    if all(name in symbols for name in DEBUG_BUFFER_CARRIERS + PANIC_WINDOW_CARRIERS):
        dbg_base = physical_base + symbols['_debug_buf_base'] - layout['base']
        dbg_ptr = physical_base + symbols['_debug_buf_ptr'] - layout['base']
        dbg_size = physical_base + symbols['_debug_buf_size'] - layout['base']
        panic_base = physical_base + symbols['_gPanicBase'] - layout['base']
        panic_size = physical_base + symbols['_gPanicSize'] - layout['base']
        # gPanicBase is vm_offset_t (64-bit): r7 read it with ldr w3, which
        # zero-truncated a KVA to its low 32 bits, so every window comparison
        # below was garbage and the copy never ran. The carriers hold kernel
        # VAs with the MMU OFF here, so translate by offset into the pram
        # window: pram is mapped 1:1 at its physical base (ml_io_map_wcomb),
        # hence panic PA == PRAM_PHYS and (VA - gPanicBase) is the offset.
        indirect += f'''
 ldr x9,={dbg_base:#x}
 ldr x0,[x9]
 ldr x9,={dbg_ptr:#x}
 ldr x1,[x9]
 ldr x9,={dbg_size:#x}
 ldr w2,[x9]
 ldr x9,={panic_base:#x}
 ldr x3,[x9]
 ldr x9,={panic_size:#x}
 ldr w4,[x9]
 add x5,x3,x4
 cmp x0,x3
 b.lo set_table
 cmp x1,x0
 b.lo set_table
 cmp x0,x5
 b.hs set_table
 cmp x1,x5
 b.hi set_table
 sub x6,x1,x0
 cmp w2,w6
 csel w2,w2,w6,lo
 mov w6,#0x1000
 cmp w2,w6
 csel w2,w2,w6,lo
 sub x0,x0,x3
 ldr x3,={PRAM_PHYS:#x}
 add x0,x0,x3
 // Preserve the Y35AXNU2 stamp page before the copy overwrites it (first
 // 64 bytes = magic, kernel hash, CurrentEL, entry, and slack). Read via
 // x3 = the page's physical base: x1 still holds debug_buf_ptr's kernel VA
 // here and the MMU is off. x2 is the copy length and must not be touched.
 ldr x3,={PANIC_LOG_DEST:#x}
 ldr x8,={STAGE_BASE + STAMP_SNAPSHOT_OFFSET:#x}
 ldr x10,[x3]
 ldr x11,[x3,#8]
 str x10,[x8]
 str x11,[x8,#8]
 ldr x10,[x3,#16]
 ldr x11,[x3,#24]
 str x10,[x8,#16]
 str x11,[x8,#24]
 ldr x10,[x3,#32]
 ldr x11,[x3,#40]
 str x10,[x8,#32]
 str x11,[x8,#40]
 ldr x10,[x3,#48]
 ldr x11,[x3,#56]
 str x10,[x8,#48]
 str x11,[x8,#56]
stamp_store:
 dsb sy
 ldr x1,={PANIC_LOG_DEST:#x}
copy_bytes:
 cbz x2,set_table
 ldrb w7,[x0],#1
 strb w7,[x1],#1
 sub x2,x2,#1
 b copy_bytes
'''
    if '_original_faulting_state' in symbols:
        pointer = physical_base + symbols['_original_faulting_state'] - layout['base']
        # Fault-state witness semantics (coordinator defect (C) fix): the
        # stage+0x18 marker is stored only AFTER the range guards pass, and
        # every rejection path stores explicit zero — an orphaned pointer
        # from a skipped branch must never masquerade as a captured fault
        # state. EPH slot and fault slot are mutually exclusive success
        # surfaces: the EPH snapshot is unconditional, this one is guarded.
        indirect += f'''
 ldr x9,={pointer:#x}
 ldr x0,[x9]
 ldr x9,={STAGE_BASE + 0x18:#x}
 ldr x10,={layout['base']:#x}
 cmp x0,x10
 b.lo fault_invalid
 ldr x11,={layout['end'] - 1024:#x}
 cmp x0,x11
 b.hi fault_invalid
 str x0,[x9]
 sub x0,x0,x10
 ldr x11,={physical_base:#x}
 add x0,x0,x11
 ldr x1,=0x859ef000
 mov x2,#64
fault_copy:
 ldp x3,x4,[x0],#16
 stp x3,x4,[x1],#16
 subs x2,x2,#1
 b.ne fault_copy
 b fault_done
fault_invalid:
 str xzr,[x9]
fault_done:
'''
    kernel_stamp = int.from_bytes(bytes.fromhex(kernel_sha256)[:8], 'little')
    return f'''.section .text
.global _start
_start:
 b enter
 .word 0
 .quad 0x80000
 .quad image_end-_start
 .quad 0,0,0,0
 .word 0x644d5241,0
enter:
 msr daifset,#15
 mrs x9,sctlr_el1
 tbnz x9,#0,halt
 // KNUF magic snapshot: PE_init_panicheader puts the 0x74-byte header at
 // gPanicBase+0 == stage+0, and STAGE_BASE == pram base, so the marker
 // stores below would overwrite header bytes 0x00..0x38 in place before the
 // host could read them. Copy the first 8 pairs (0x80 >= EPH 0x74) of pram
 // to the pram-tail preservation slot FIRST. This keeps a compact header
 // witness only; record staging still overwrites pram by design
 // (transport_mode=full-readback, pram_preserved=false).
 ldr x8,={PRAM_PHYS:#x}
 ldr x0,={STAGE_BASE + EPH_SNAPSHOT_OFFSET:#x}
 mov x2,8
snapshot_store:
 ldp x10,x11,[x8],#16
 stp x10,x11,[x0],#16
 subs x2,x2,#1
 b.ne snapshot_store
 dsb sy
 ldr x10,={STAGE_BASE:#x}
 ldr x11,={int.from_bytes(b'Y35ARD01','little'):#x}
 str x11,[x10]
 ldr x11,={kernel_stamp:#x}
 str x11,[x10,#8]
 mrs x11,cntvct_el0
 str x11,[x10,#{FRESHNESS_WITNESS_OFFSET}]
 mrs x11,id_aa64isar0_el1
 str x11,[x10,#32]
 mrs x11,id_aa64pfr0_el1
 str x11,[x10,#40]
 mrs x11,cpacr_el1
 str x11,[x10,#48]
 mrs x11,midr_el1
 str x11,[x10,#56]
{indirect}
 dsb sy
set_table:
 adr x19,table
 mov x20,#{len(records)}
next:
 ldp x0,x1,[x19],#16
 ldr x2,[x19],#8
copy:
 ldp x3,x4,[x0],#16
 stp x3,x4,[x1],#16
 subs x2,x2,#1
 b.ne copy
 subs x20,x20,#1
 b.ne next
 dsb sy
capture_done:
 dsb sy
 ldr x9,=0x0860065c
 // Normal boot reaches the forced-fastboot loader in the boot partition.
 // Recovery now contains stock firmware, so never request recovery here.
 str wzr,[x9]
 dsb sy
 ldr x9,=0x004ab000
 str wzr,[x9]
 dsb sy
halt:
 wfe
 b halt
 .ltorg
 .balign 8
table:
{table}
image_end:
'''


def minimal_boundary_records(payload):
    """Pack (name, physical_address, size) reads into the report page after
    the preserved shim stamp and probe header. Offsets carry both keys the
    independent gates read: report_offset for the transport gate and
    stage_offset (== offset) for the layout gate; 16B alignment keeps the
    ldp/stp copy loop valid."""
    records = []
    cursor = REPORT_RECORDS_OFFSET
    for name, pa, size in payload:
        if size % 16:
            size = (size // 16 + 1) * 16
        if cursor + size > REPORT_BYTES:
            raise ValueError('minimal-boundary payload exceeds the report page')
        records.append(dict(name=name, physical=hex(pa), size=size,
                            report_offset=cursor, stage_offset=cursor + PANIC_LOG_OFFSET,
                            offset=cursor + PANIC_LOG_OFFSET))
        cursor += size
    return records


def minimal_boundary_entry_source(*, records, kernel_sha256):
    """Snapshot pram to scratch FIRST, write everything into the report page
    above pram, restore pram before the forced reset. Report head 0x40 bytes
    stay untouched (boot3 Y35AXNU2 stamp); probe marker starts at +0x40."""
    validate_report_footprint(records)
    table = '\n'.join(
        f" .quad {r['physical']}, {REPORT_BASE + r['report_offset']:#x}, {r['size'] // 16}"
        for r in records
    )
    kernel_stamp = int.from_bytes(bytes.fromhex(kernel_sha256)[:8], 'little')
    return f'''.section .text
.global _start
_start:
 b enter
 .word 0
 .quad 0x80000
 .quad image_end-_start
 .quad 0,0,0,0
 .word 0x644d5241,0
enter:
 msr daifset,#15
 mrs x9,sctlr_el1
 tbnz x9,#0,halt
 // pram snapshot FIRST: read only, no stage or report write yet
 ldr x10,={PRAM_PHYS:#x}
 ldr x11,={SCRATCH_PRAM_BACKUP:#x}
 mov x12,#0x10000
pram_snapshot:
 ldp x13,x14,[x10],#16
 stp x13,x14,[x11],#16
 subs x12,x12,#16
 b.ne pram_snapshot
 // report header at +0x40: the head keeps the boot3 Y35AXNU2 stamp
 ldr x10,={REPORT_BASE:#x}
 ldr x11,={int.from_bytes(b'Y35ARD02','little'):#x}
 str x11,[x10,#64]
 ldr x11,={kernel_stamp:#x}
 str x11,[x10,#72]
 mrs x11,cntvct_el0
 str x11,[x10,#80]
 mrs x11,id_aa64isar0_el1
 str x11,[x10,#96]
 mrs x11,id_aa64pfr0_el1
 str x11,[x10,#104]
 mrs x11,cpacr_el1
 str x11,[x10,#112]
 mrs x11,midr_el1
 str x11,[x10,#120]
 dsb sy
 adr x19,table
 mov x20,#{len(records)}
next:
 ldp x0,x1,[x19],#16
 ldr x2,[x19],#8
copy:
 ldp x3,x4,[x0],#16
 stp x3,x4,[x1],#16
 subs x2,x2,#1
 b.ne copy
 subs x20,x20,#1
 b.ne next
 dsb sy
 // restore pram from the pre-write snapshot, then reset
 ldr x10,={SCRATCH_PRAM_BACKUP:#x}
 ldr x11,={PRAM_PHYS:#x}
 mov x12,#0x10000
pram_restore:
 ldp x13,x14,[x10],#16
 stp x13,x14,[x11],#16
 subs x12,x12,#16
 b.ne pram_restore
 dsb sy
capture_done:
 ldr x9,=0x0860065c
 // Normal boot reaches the forced-fastboot loader in the boot partition.
 // Recovery now contains stock firmware, so never request recovery here.
 str wzr,[x9]
 dsb sy
 ldr x9,=0x004ab000
 str wzr,[x9]
 dsb sy
halt:
 wfe
 b halt
 .ltorg
 .balign 8
table:
{table}
image_end:
'''


def validate_report_footprint(records):
    if not records:
        raise ValueError('Minimal-boundary readback has no records')
    if any(r['report_offset'] < REPORT_RECORDS_OFFSET for r in records):
        raise ValueError('Minimal-boundary record overlaps the preserved report head')
    end = max(r['report_offset'] + r['size'] for r in records)
    if end > REPORT_BYTES:
        raise ValueError('Minimal-boundary records exceed the bounded report page')
    return end


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--kernel', type=Path, required=True)
    p.add_argument('--stock-boot', type=Path, required=True)
    p.add_argument('--directory', type=Path, required=True)
    p.add_argument('--kernel-log', action='store_true', help='Capture static kernel log instead of bootstrap stacks')
    p.add_argument('--extra-pa', action='append', default=[],
                   help='Raw physical record name=0xADDR:SIZE (repeatable); bypasses symbol translation')
    p.add_argument('--transport', default='full-readback',
                   choices=('full-readback', 'minimal-boundary'),
                   help='full-readback stages records into the pram-backed stage (destroys EPH text); '
                        'minimal-boundary snapshots pram to LK scratch, writes only the 0x1000 report '
                        'page above pram, and restores pram before reset')
    p.add_argument('--dsym', type=Path, default=None,
                   help='Optional .dsym bundle: when present, DWARF type sizes take '
                        'priority over the source-type table for field widths')
    a = p.parse_args()
    a.directory.mkdir(parents=True, exist_ok=False)
    kernel = a.kernel.read_bytes()
    layout = parse_macho(kernel)
    base = physical_base_for(layout['base'])
    symbols = {}
    names = NAMES
    if a.kernel_log:
        names = tuple(n for n in names if n not in ('_excepstack', '_intstack')) + ('_msgbuf', '_smsg_bufc', '_initproc_spawned')
    for line in subprocess.check_output([_tool_path('llvm-nm'), str(a.kernel)], text=True).splitlines():
        fields = line.split()
        if len(fields) == 3 and fields[2] in names:
            symbols[fields[2]] = int(fields[0], 16)
    validate_required_symbols(symbols)
    kernel_sha256 = hashlib.sha256(kernel).hexdigest()
    # Symbols the probe wants but this kernel does not carry. Recorded
    # explicitly so a missing record is never read as a zero field:
    # entry-trace absent means never instrumented, not "trace all zero".
    absent = sorted(n for n in names if n not in symbols)
    if a.transport == 'minimal-boundary':
        # Field-width scalars + the early-fault record only; stacks and the
        # debug-text window cannot fit the 0x1000 report page and are exactly
        # what made the pram overlap unavoidable.
        efr_pa = align(base + layout['end'] - layout['base'], 16384) + 0x800
        payload = [('early-fault-record', efr_pa, 384)]
        for name in BOUNDARY_NAMES:
            if name not in symbols:
                continue
            va = symbols[name]
            if not any(s['address'] <= va for s in layout['segments']):
                raise ValueError('Readback symbol outside kernel: ' + name)
            payload.append((name, base + va - layout['base'], _record_size(name)))
        for spec in a.extra_pa:
            extra = parse_extra_pa(spec)
            payload.append((extra['name'], int(extra['physical'], 16), extra['size']))
        records = minimal_boundary_records(payload)
        entry_source = minimal_boundary_entry_source(records=records, kernel_sha256=kernel_sha256)
        (a.directory / 'entry.S').write_text(entry_source)
        subprocess.run([_compiler_path(), '--target=aarch64-none-elf', '-nostdlib', '-fuse-ld=lld',
                        '-Wl,-Ttext=0x80080000', '-Wl,-e,_start', '-o', 'entry.elf', 'entry.S'],
                       cwd=a.directory, check=True, env=_linker_environment())
        subprocess.run([_tool_path('llvm-objcopy'), '-O', 'binary', 'entry.elf', 'entry.bin'], cwd=a.directory, check=True)
        stock = a.stock_boot.read_bytes()
        v = struct.unpack_from('<10I', stock, 8)
        page = v[7]
        offset = page + align(v[0], page) + align(v[2], page) + align(v[4], page)
        image = android_container((a.directory / 'entry.bin').read_bytes(), select_device_dt(stock[offset:offset + v[8]]))
        (a.directory / 'readback-probe-not-xnu.img').write_bytes(image)
        manifest = dict(purpose='minimal-boundary retained-memory diagnostic, not XNU; '
                                'pram snapshotted to LK scratch and restored before reset',
                        kernel_sha256=kernel_sha256,
                        image_sha256=hashlib.sha256(image).hexdigest(), records=records,
                        absent_symbols=[n for n in BOUNDARY_NAMES if n not in symbols],
                        transport_mode='minimal-boundary', pram_preserved=True,
                        report_bytes=max(r['report_offset'] + r['size'] for r in records),
                        staged_source=hex(REPORT_BASE), staged_bytes=REPORT_BYTES,
                        snapshot_base=hex(SCRATCH_PRAM_BACKUP),
                        snapshot_bytes=SCRATCH_PRAM_BACKUP_BYTES,
                        report_records_offset=REPORT_RECORDS_OFFSET,
                        cpu_registers={'ID_AA64ISAR0_EL1': 96, 'ID_AA64PFR0_EL1': 104,
                                       'CPACR_EL1': 112, 'MIDR_EL1': 120})
        write_manifest(a.directory / 'readback.json', manifest)
        print(json.dumps(manifest, indent=2))
        return
    # This is the reserved, initially zeroed remainder of the boot-args page.
    record_pa = align(base + layout['end'] - layout['base'], 16384) + 0x800
    records = [dict(name='early-fault-record', virtual=hex(layout['base'] + record_pa - base),
                    physical=hex(record_pa), offset=64, size=384, field_bytes=384)]
    for name in names:
        if name not in symbols:
            continue
        va = symbols[name]
        size = _record_size(name)
        if not any(s['address'] <= va and va + size <= s['address'] + s['size'] for s in layout['segments']):
            raise ValueError('Readback symbol outside kernel: ' + name)
        records.append(dict(name=name, virtual=hex(va), physical=hex(base + va - layout['base']),
                            offset=64 + sum(r['size'] for r in records), size=size,
                            field_bytes=read_field_bytes(name, symbols,
                                                         dsym_path=a.dsym)))
    for spec in a.extra_pa:
        extra = parse_extra_pa(spec)
        records.append(dict(extra, offset=64 + sum(r['size'] for r in records)))
    panic_log_offset = validate_stage_footprint(records)
    kernel_sha256 = hashlib.sha256(kernel).hexdigest()
    entry_source = preservation_entry_source(records=records, symbols=symbols, layout=layout,
                                             physical_base=base, kernel_sha256=kernel_sha256)
    (a.directory / 'entry.S').write_text(entry_source)

    subprocess.run([_compiler_path(), '--target=aarch64-none-elf', '-nostdlib', '-fuse-ld=lld',
                    '-Wl,-Ttext=0x80080000', '-Wl,-e,_start', '-o', 'entry.elf', 'entry.S'],
                   cwd=a.directory, check=True, env=_linker_environment())
    subprocess.run([_tool_path('llvm-objcopy'), '-O', 'binary', 'entry.elf', 'entry.bin'], cwd=a.directory, check=True)
    stock = a.stock_boot.read_bytes()
    v = struct.unpack_from('<10I', stock, 8)
    page = v[7]
    offset = page + align(v[0], page) + align(v[2], page) + align(v[4], page)
    image = android_container((a.directory / 'entry.bin').read_bytes(), select_device_dt(stock[offset:offset + v[8]]))
    (a.directory / 'readback-probe-not-xnu.img').write_bytes(image)
    manifest = dict(purpose='retained-memory diagnostic, not XNU; ' + PRAM_FENCE_NOTE,
                    kernel_sha256=kernel_sha256,
                    image_sha256=hashlib.sha256(image).hexdigest(), records=records,
                    absent_symbols=absent,
                    panic_log_offset=panic_log_offset,
                    # Transport honesty (R9 gate): records stage INTO pram, so
                    # EPH panic text is sacrificed by design; only the 0x74-byte
                    # header survives via the pram-tail witness slot, and the
                    # bounded debug_buf capture at PANIC_LOG_DEST (the report
                    # page outside pram) holds at most 0x1000 bytes.
                    transport_mode='full-readback', pram_preserved=False,
                    # make_adt.py gives XNU pram reg=(0x859e0000,0x10000) ==
                    # STAGE_BASE: the stage window IS the panic window. Header
                    # bytes survive via the 0xf800 snapshot; panic TEXT beyond
                    # 0x74 is probe-overwritten by design. Never read stage
                    # bytes as EPH truth without this note.
                    stage_aliases_pram=True, stage_alias_note='STAGE_BASE==DT pram reg base 0x859e0000',
                    report_bytes=PANIC_LOG_LIMIT,
                    panic_log_limit=PANIC_LOG_LIMIT,
                    staged_source=hex(STAGE_BASE), staged_bytes=STAGE_BYTES,
                    eph_snapshot_offset=EPH_SNAPSHOT_OFFSET,
                    eph_snapshot_bytes=EPH_SNAPSHOT_BYTES,
                    # The entry code stages 8 ldp/stp pairs (0x80) while the
                    # logical header is 0x74; the layout gate validates the
                    # physical write extent against records/slots.
                    eph_snapshot_write_bytes=EPH_SNAPSHOT_WRITE_BYTES,
                    stamp_snapshot_offset=STAMP_SNAPSHOT_OFFSET,
                    stamp_snapshot_bytes=STAMP_SNAPSHOT_BYTES,
                    cpu_registers={'ID_AA64ISAR0_EL1': 32, 'ID_AA64PFR0_EL1': 40,
                                   'CPACR_EL1': 48, 'MIDR_EL1': 56},
                    fault_state_pointer_offset=24, fault_state_offset=61440, fault_state_bytes=1024)
    write_manifest(a.directory / 'readback.json', manifest)
    print(json.dumps(manifest, indent=2))


if __name__ == '__main__':
    main()
