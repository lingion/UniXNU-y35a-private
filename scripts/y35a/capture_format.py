#!/usr/bin/env python3
"""Classify fastboot-staged 68 KiB capture bodies and decode true XNU EPH.

Positions never identify the header here: the LK container magics
(Y35ARD01 readback wrap, Y35AXNU2 boot3 handoff) share file offsets with
what an EPH decoder would read as panic-log offset/len. Key on the magic.

See tests/test_capture_format.py for the byte-level evidence of both
container shapes and the osfmk/kern/debug.h:286 packed EPH layout.
"""
import re
import struct

EPH_MAGIC = 0x46554E4B  # 'FUNK' — stored little-endian, appears as KNUF
# Exact packed layout of osfmk/kern/debug.h struct embedded_panic_header in
# xnu-4903 (verified in build container /work/xnu-4903, 2026-11-08):
#   0x00 magic u32, 0x04 crc u32, 0x08 version u32, 0x0c panic_flags u64,
#   0x14 panic_log_offset, 0x18 panic_log_len, 0x1c stackshot_offset,
#   0x20 stackshot_len, 0x24 other_log_offset, 0x28 other_log_len,
#   0x2c x86 u64, 0x34 os_version[32], 0x54 macos_version[32] => 0x74.
EPH_PANIC_LOG_OFFSET = 0x14
EPH_PANIC_LOG_LEN = 0x18
EPH_SIZE = 0x74


def parse_eph(header_bytes):
    if len(header_bytes) < EPH_SIZE:
        raise ValueError('short EPH header')
    magic, crc, version = struct.unpack_from('<III', header_bytes, 0)
    if magic != EPH_MAGIC:
        raise ValueError(f'not an EPH: magic {magic:#x}')
    flags = struct.unpack_from('<Q', header_bytes, 0x0c)[0]
    (log_off, log_len, ss_off, ss_len, other_off, other_len) = \
        struct.unpack_from('<IIIIII', header_bytes, EPH_PANIC_LOG_OFFSET)
    return dict(magic=magic, crc=crc, version=version, flags=flags,
                panic_log_offset=log_off, panic_log_len=log_len,
                stackshot_offset=ss_off, stackshot_len=ss_len,
                other_log_offset=other_off, other_log_len=other_len)


def find_eph(pram):
    for off in range(0, len(pram) - EPH_SIZE + 1, 4):
        if struct.unpack_from('<I', pram, off)[0] == EPH_MAGIC:
            try:
                f = parse_eph(pram[off:off + EPH_SIZE])
            except ValueError:
                continue
            f['file_offset'] = off
            return f
    return None


# Host-side semantics table: width alone cannot distinguish boolean_t from
# unsigned int, and misreading panicDebugging's 0x100 as a value was the r7
# false lead. Only names listed here face the FALSE/TRUE validity rule.
BOOLEAN_FIELDS = ('_panicDebugging',)

def decode_records(manifest, body):
    """Width-driven host decode (coordinator guardrail #2): offsets and field
    widths come from the manifest, never from eyeballed windows. field_bytes
    is the logical XNU object; size is the 16-aligned copy window. Bytes
    outside field_bytes are neighbor, not evidence. Symbols listed in
    absent_symbols decode as kind='absent', so never-instrumented can never
    be read as trace-all-zero (r7 confusion killed here)."""
    out = {}
    for name in manifest.get('absent_symbols', []):
        out[name] = {'kind': 'absent'}
    for record in manifest.get('records', []):
        name = record.get('name')
        if name is None:
            continue
        if out.get(name, {}).get('kind') == 'absent':
            continue
        offset = int(record['offset'])
        window_size = int(record['size'])
        has_field_bytes = 'field_bytes' in record
        width = int(record['field_bytes']) if has_field_bytes else window_size
        if offset + width > len(body):
            raise ValueError(f'capture body truncated before record {name} '
                             f'(need {offset + width:#x}, have {len(body):#x})')
        raw = body[offset:offset + width]
        if width in (4, 8):
            value = int.from_bytes(raw, 'little')
            valid = True
            if name in BOOLEAN_FIELDS:
                valid = value in (0, 1)
            out[name] = {'kind': 'field', 'value': value, 'valid': valid,
                         'offset': offset, 'size': window_size}
            if has_field_bytes:
                out[name]['field_bytes'] = width
        elif name == '_native_entry_trace':
            nonzero = [i for i in range(0, width, 8)
                       if int.from_bytes(raw[i:i + 8], 'little')]
            out[name] = {'kind': 'trace', 'nonzero_offsets': nonzero,
                         'offset': offset, 'size': window_size}
            if has_field_bytes:
                out[name]['field_bytes'] = width
        else:
            out[name] = {'kind': 'blob', 'raw': raw, 'offset': offset,
                         'size': window_size}
            if has_field_bytes:
                out[name]['field_bytes'] = width
    return out


def classify(body):
    if len(body) < 0x10020:
        return {'kind': 'short', 'size': len(body)}
    head8 = body[:8]
    if head8 == b'Y35ARD01':
        return {'kind': 'Y35ARD01',
                'kernel_sha_prefix': body[8:16],
                'fields': struct.unpack_from('<III', body, 0x10)}
    if body[0x10000:0x10008] == b'Y35AXNU2':
        return {'kind': 'Y35AXNU2',
                'entry': struct.unpack_from('<Q', body, 0x10000 + 24)[0]}
    eph = find_eph(body)
    if eph is not None:
        return {'kind': 'eph', 'eph': eph}
    # No header: still surface debug_buffer-style printable content, since a
    # pram region can hold text the kernel wrote (zone-info dump) without
    # ever committing an EPH. Discarding it loses the one relevant fact.
    runs = list(re.finditer(rb'[\x20-\x7e\t\n\r]{32,}', body))
    if runs:
        m = runs[0]
        return {'kind': 'debug_text', 'text_offset': m.start(),
                'text_len': len(m.group()), 'text': m.group()}
    return {'kind': 'unknown', 'size': len(body)}
