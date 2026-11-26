#!/usr/bin/env python3
"""RED-GREEN gate: host-side classifier for fastboot-staged capture bodies.

The 2026-11-07 boot4 forensics misread eph_panic_log_offset/len at file
offsets 0x14/0x18 of the staged capture. Those bytes are fields of the LK
container header (magic Y35ARD01 = readback wrap, Y35AXNU2 = boot3 handoff
record), not the XNU embedded_panic_header. The true EPH (osfmk/kern/debug.h
:286, __attribute__((packed))):

  0x00 eph_magic u32     0x46554E4B 'FUNK' (bytes KNUF LE-first)
  0x04 eph_crc u32
  0x08 eph_version u32   2
  0x0c eph_panic_flags u64
  0x10 eph_panic_log_offset u32
  0x14 eph_panic_log_len u32
  0x18 eph_stackshot_offset u32
  0x1c eph_stackshot_len u32
  0x20 eph_other_log_offset u32
  0x24 eph_other_log_len u32
  0x28 eph_x86_do_not_use u64
  0x30 eph_os_version[32]
  0x50 eph_macos_version[32]   header total 0x70

Container headers observed on disk (evidence/…/panic.raw, /tmp/captures):
  Y35ARD01 @file 0x0   magic8 + kernel-sha256 first 8 bytes @0x8 (two u32
                       halves 5fd4e6b5 / f7fa10e1 == sha prefix of the booted
                       kernel), own u32 fields at 0x10/0x14/0x18.
  Y35AXNU2 @0x10000    boot3 package_native handoff (magic@0, u64 entry@24),
                       staged as the tail page of the 0x11000 pram read.

A decoder must key on the magic, never on a position, and must reject
container bytes presented as EPH instead of reading their 0x14/0x18 as
log offset/len (the exact stale claim in boot4-empty-readback-20261107.txt).
"""
import struct, sys, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'scripts/y35a'))

import capture_format  # noqa: E402  (the validator under construction)

EPH_MAGIC = 0x46554E4B  # 'FUNK' — bytes KNUF, LE-first

CAPTURE = REPO / 'evidence/y35a-20261102/boot3-20261106/panic.raw'


def synthetic_eph(log_off=0xa9, log_len=0xa37, stack_off=0, stack_len=0):
    # Layout from the actual packed struct in /work/xnu-4903/osfmk/kern/debug.h:
    # 0x00 magic, 0x04 crc, 0x08 version, 0x0c panic_flags u64,
    # 0x14 panic_log_offset, 0x18 panic_log_len, 0x1c stackshot_offset,
    # 0x20 stackshot_len, 0x24 other_log_offset, 0x28 other_log_len,
    # 0x2c x86 u64, 0x34 os_version[32], 0x54 macos_version[32] => 0x74 total.
    h = bytearray(0x74)
    struct.pack_into('<I', h, 0x00, EPH_MAGIC)
    struct.pack_into('<I', h, 0x08, 2)
    struct.pack_into('<Q', h, 0x0c, 0)
    struct.pack_into('<I', h, 0x14, log_off)
    struct.pack_into('<I', h, 0x18, log_len)
    struct.pack_into('<I', h, 0x1c, stack_off)
    struct.pack_into('<I', h, 0x20, stack_len)
    h[0x34:0x54] = b'Darwin Kernel Version 18.7.0'.ljust(32, b'\0')
    return bytes(h)


class ContainerClassification(unittest.TestCase):
    def test_reads_y35ard01_wrapped_capture_as_container_not_eph(self):
        if not CAPTURE.exists():
            self.skipTest('boot3 evidence capture not on disk')
        body = CAPTURE.read_bytes()
        rec = capture_format.classify(body)
        self.assertEqual(rec['kind'], 'Y35ARD01')
        # Kernel-sha prefix must be intact: proves classification keys on
        # structure, and pins the 5fd4e6b5 generation the evidence names.
        self.assertEqual(rec['kernel_sha_prefix'], bytes.fromhex('5fd4e6b5f7fa10e1'))

    def test_eph_fields_only_come_from_true_eph_header(self):
        if not CAPTURE.exists():
            self.skipTest('boot3 evidence capture not on disk')
        rec = capture_format.classify(CAPTURE.read_bytes())
        # The stale reading treated container offsets 0x14/0x18 (0xa9/0xa37)
        # as eph_panic_log_offset/len. The validator must not expose EPH
        # fields at all for a container-kind record.
        self.assertNotIn('eph', rec)


class TrueEphDecoding(unittest.TestCase):
    def test_synthetic_eph_decodes_at_packed_debug_h_offsets(self):
        h = synthetic_eph()
        f = capture_format.parse_eph(h)
        self.assertEqual(f['magic'], EPH_MAGIC)
        self.assertEqual(f['version'], 2)
        self.assertEqual(f['panic_log_offset'], 0xa9)
        self.assertEqual(f['panic_log_len'], 0xa37)

    def test_container_position_0x14_0x18_must_not_be_read_as_eph(self):
        # The actual boot4 misparse: panic.raw file offsets 0x14/0x18 hold
        # container words 0xa9/0xa37 (plausible-looking EPH values); the true
        # EPH at the same position inside the EPH belongs to the SAME field
        # pair only when the header is a real EPH. Validator must key on magic.
        h = synthetic_eph()
        f = capture_format.parse_eph(h)
        self.assertEqual((f['panic_log_offset'], f['panic_log_len']), (0xa9, 0xa37))
        if CAPTURE.exists():
            body = CAPTURE.read_bytes()
            # Container words at the same position mimic EPH values — the trap.
            self.assertEqual(struct.unpack_from('<II', body, 0x14), (0xa9, 0xa37))
            # Magic scan finds no EPH anywhere in the real capture: the kernel
            # never wrote a header; the "0xa9/0xa37" was the container's own.
            self.assertIsNone(capture_format.find_eph(body[0x40:]))

    def test_rejects_magic_less_pram_as_absent_eph(self):
        pram = bytes(0x70)  # all-zero pram: header never written by kernel
        self.assertIsNone(capture_format.find_eph(pram))


class HandoffRecord(unittest.TestCase):
    def test_bare_pram_region_still_exposes_contained_panic_text(self):
        # 2026-11-08 regression: classify(pram) returned kind='unknown' and
        # dropped the one relevant fact — the region holds real panic text
        # (debug_buffer content) even though no EPH header was ever written.
        if not CAPTURE.exists():
            self.skipTest('device evidence absent')
        pram = CAPTURE.read_bytes()[0x40:]
        r = capture_format.classify(pram)
        self.assertEqual(r['kind'], 'debug_text')
        self.assertGreater(r['text_len'], 1000)
        # Content is the XNU zone-info dump; first bytes sit at pram 0x380.
        self.assertIn(b'Zone info', r['text'])
        self.assertEqual(pram.index(r['text']), 0x380)
        # boot3 package_native handoff: magic at 0, entry u64 at +24
        rec = bytearray(0x10000 + 64)
        rec[0x10000:0x10008] = b'Y35AXNU2'
        struct.pack_into('<Q', rec, 0x10000 + 24, 0x859f0000)
        parsed = capture_format.classify(bytes(rec))
        self.assertEqual(parsed['kind'], 'Y35AXNU2')
        self.assertEqual(parsed['entry'], 0x859f0000)
        self.assertNotIn('eph', parsed)


class WidthDrivenRecordDecode(unittest.TestCase):
    """Coordinator guardrail (r8 acceptance, 10:5x): capture_format parses the
    manifest's published offsets/widths; bytes outside field_bytes are
    neighbor, not evidence. The r7 false leads this kills: panicDebugging
    read as 0x800000000100 (u64 over 120B neighbors incl. probe CNTVCT),
    _debug_buf_ptr read as 0x0800000000000000, silently-skipped symbols read
    as zero. Offsets are STAGE-RELATIVE: full-readback records live in the
    pram-backed stage (0x40..0xc3c0, inside the 0x11000 upload), so the
    capture body indexes them directly; minimal-boundary records are already
    uploaded at their report_offset+PANIC_LOG_OFFSET position in the same
    body. A reader MUST consult transport_mode from classify(), never
    assume a body layout."""

    MANIFEST = {
        'transport_mode': 'full-readback',
        'absent_symbols': ['_native_entry_trace'],
        'records': [
            {'name': '_panicDebugging', 'offset': 0x380, 'size': 16, 'field_bytes': 4},
            {'name': '_gPanicBase', 'offset': 0x350, 'size': 16, 'field_bytes': 8},
            {'name': '_debug_buf_ptr', 'offset': 0x3a0, 'size': 16, 'field_bytes': 8},
            {'name': '_const_boot_args', 'offset': 0x1d0, 'size': 384, 'field_bytes': 384},
            {'name': 'early-fault-record', 'offset': 0x40, 'size': 384, 'field_bytes': 384},
        ],
    }

    def body(self, debugging=0x100, panic_base=0x859e0000, buf_ptr=0,
             blob=b'hello', fault=b''):
        body = bytearray(0x11000)
        struct.pack_into('<I', body, 0x380, debugging)
        struct.pack_into('<Q', body, 0x350, panic_base)
        struct.pack_into('<Q', body, 0x3a0, buf_ptr)
        body[0x1d0:0x1d0 + len(blob)] = blob
        # neighbor poison: the old 128B-window trap
        body[0x384:0x390] = b'\xff' * 12
        if fault:
            body[0x40:0x40 + len(fault)] = fault
        return bytes(body)

    def test_decode_consumes_field_bytes_not_the_copy_window(self):
        r = capture_format.decode_records(self.MANIFEST, self.body())
        self.assertEqual(r['_panicDebugging']['value'], 0x100)
        self.assertFalse(r['_panicDebugging']['valid'],
                         'boolean_t holds neither FALSE nor TRUE')
        self.assertEqual(r['_gPanicBase']['value'], 0x859e0000)
        self.assertTrue(r['_gPanicBase']['valid'])
        self.assertEqual(r['_debug_buf_ptr']['value'], 0)
        self.assertTrue(r['_debug_buf_ptr']['valid'])

    def test_boolean_field_accepts_only_false_and_true(self):
        for value in (0, 1):
            r = capture_format.decode_records(self.MANIFEST, self.body(debugging=value))
            self.assertEqual(r['_panicDebugging']['value'], value)
            self.assertTrue(r['_panicDebugging']['valid'])
        r = capture_format.decode_records(self.MANIFEST, self.body(panic_base=0))
        self.assertEqual(r['_gPanicBase']['value'], 0)
        self.assertTrue(r['_gPanicBase']['valid'], 'zero gPanicBase IS meaningful')

    def test_struct_field_returns_full_extent_blob(self):
        r = capture_format.decode_records(self.MANIFEST, self.body(blob=b'hello'))
        rec = r['_const_boot_args']
        self.assertEqual(rec['kind'], 'blob')
        self.assertEqual(rec['raw'], b'hello' + bytes(384 - 5))
        self.assertEqual(rec['size'], 384)
        self.assertEqual(rec['offset'], 0x1d0)

    def test_absent_symbols_decode_as_absent_never_zero(self):
        r = capture_format.decode_records(self.MANIFEST, self.body())
        self.assertEqual(r['_native_entry_trace']['kind'], 'absent',
                         'never-instrumented must not read as trace-all-zero')

    def test_truncated_capture_body_raises_not_silently_short(self):
        # 0x300 ends before _panicDebugging's field at 0x380; raising beats a
        # partial decode a reader trusts as zero.
        with self.assertRaises(ValueError):
            capture_format.decode_records(self.MANIFEST, bytes(0x300))

    def test_decode_consumes_a_real_r8_capture(self):
        """End-to-end against the shipped r7 capture and its real manifest:
        legacy records WITHOUT field_bytes decode as honest blobs (the
        decoder refuses to invent widths it was not told — the blob is the
        migration flag), and adding r8-style field_bytes to the same real
        bytes flips the same code path to precise boolean-validity fields.
        This pins the r7->r8 interpretation shift the coordinator ruled."""
        manifest_path = REPO / 'out/y35a/readback-probe-20261109-r7/readback.json'
        raw_path = (REPO / 'evidence/y35a-20261102/boot3-20261106/'
                    'boot4-r3-20261108/r7-witness-20261109/r7-post-boot3.raw')
        if not manifest_path.exists() or not raw_path.exists():
            self.skipTest('r7 artifact pair not on disk')
        import json
        manifest = json.loads(manifest_path.read_text())
        body = raw_path.read_bytes()
        legacy = capture_format.decode_records(manifest, body)
        debug = legacy['_panicDebugging']
        self.assertEqual(debug['kind'], 'blob')
        self.assertEqual(debug['size'], 128)
        self.assertEqual(int.from_bytes(debug['raw'][:4], 'little'), 0x100)
        self.assertEqual(len(legacy['_excepstack']['raw']), 16384)
        # same bytes, r8-style widths
        upgraded = json.loads(json.dumps(manifest))
        for record in upgraded['records']:
            if record['name'] in ('_panicDebugging', '_gPanicSize', '_debug_buf_size'):
                record['field_bytes'] = 4
            elif record['name'].startswith('_') and record['name'] not in (
                    '_excepstack', '_intstack', '_const_boot_args', '_BootArgs'):
                record['field_bytes'] = 8
        upgraded['absent_symbols'] = ['_native_entry_trace']
        precise = capture_format.decode_records(upgraded, body)
        self.assertEqual(precise['_panicDebugging']['kind'], 'field')
        self.assertEqual(precise['_panicDebugging']['value'], 0x100)
        self.assertFalse(precise['_panicDebugging']['valid'])
        self.assertEqual(precise['_native_entry_trace']['kind'], 'absent')
        self.assertEqual(precise['_BootArgs']['kind'], 'blob', 'struct extent')


if __name__ == '__main__':
    unittest.main()
