#!/usr/bin/env python3
"""Fail-closed binary checks for the bounded Y35A low-vector experiment.

Versions through 6 retire to the original spin vectors before C. Version 7
keeps the terminal observer through early C and uses the C-entry gate. These
checks do not establish hardware fetch or persistent store behavior.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import sys


BOUNDARY = bytes.fromhex('001018d5df3f03d50b1038d58be604f9')


class MachO:
    def __init__(self, image):
        self.image = image
        if len(image) < 32 or struct.unpack_from('<II', image) != (0xfeedfacf, 0x100000c):
            raise ValueError('Expected arm64 Mach-O')
        count, size = struct.unpack_from('<II', image, 16)
        end = 32 + size
        if end > len(image):
            raise ValueError('Truncated load commands')
        self.segments, self.symbols = [], {}
        offset = 32
        symtab = None
        for _ in range(count):
            cmd, length = struct.unpack_from('<II', image, offset)
            if length < 8 or offset + length > end:
                raise ValueError('Invalid load command')
            if cmd == 25:
                va, vmsize, fileoff, filesize = struct.unpack_from('<QQQQ', image, offset + 24)
                if fileoff + filesize > len(image):
                    raise ValueError('Segment outside image')
                self.segments.append((va, vmsize, fileoff, filesize))
            elif cmd == 2:
                symtab = struct.unpack_from('<IIII', image, offset + 8)
            offset += length
        if not symtab:
            raise ValueError('Missing symbols')
        so, n, st, sl = symtab
        if so + n * 16 > len(image) or st + sl > len(image):
            raise ValueError('Invalid symbol table')
        for i in range(n):
            name, kind, section, desc, va = struct.unpack_from('<IBBHQ', image, so + i * 16)
            if kind & 0xe0 or name >= sl:
                continue
            stop = image.find(b'\0', st + name, st + sl)
            if stop < 0:
                raise ValueError('Unterminated symbol')
            self.symbols[image[st + name:stop].decode('utf8', 'replace')] = va

    def offset(self, va, size=4):
        for base, _, off, extent in self.segments:
            if base <= va and va + size <= base + extent:
                return off + va - base
        raise ValueError(f'No file-backed bytes at {va:#x}')

    def word(self, va):
        return struct.unpack_from('<I', self.image, self.offset(va))[0]


def signed(value, bits):
    return value - (1 << bits) if value & (1 << (bits - 1)) else value


def branch_target(pc, word):
    if word & 0xfc000000 == 0x14000000:
        return pc + 4 * signed(word & 0x3ffffff, 26)
    if word & 0x7e000000 == 0x34000000:
        return pc + 4 * signed((word >> 5) & 0x7ffff, 19)
    raise ValueError('Expected a direct branch')


def adrp_add(pc, first, second, register):
    if first & 0x9f00001f != 0x90000000 | register:
        raise ValueError('Expected ADRP')
    if second & 0xffc003ff != 0x91000000 | register << 5 | register:
        raise ValueError('Expected same-register ADD immediate')
    imm = ((first >> 5) & 0x7ffff) << 2 | ((first >> 29) & 3)
    return (pc & ~0xfff) + (signed(imm, 21) << 12) + ((second >> 10) & 0xfff)


def verify(image, manifest=None):
    failures = []
    report = {'kernel_sha256': hashlib.sha256(image).hexdigest(), 'failures': failures}
    try:
        m = MachO(image)
        sym = m.symbols
        if '_y35a_low_vector_v7' in sym:
            helper_path = Path(__file__).resolve().with_name('verify_c_vector.py')
            helper_spec = importlib.util.spec_from_file_location(
                '_y35a_verify_c_vector_v7', helper_path
            )
            if helper_spec is None or helper_spec.loader is None:
                return {'kernel_sha256': report['kernel_sha256'], 'ok': False,
                        'failures': ['could not load version-7 C-vector verifier']}
            helper = importlib.util.module_from_spec(helper_spec)
            helper_directory = str(helper_path.parent)
            inserted = helper_directory not in sys.path
            if inserted:
                sys.path.insert(0, helper_directory)
            try:
                helper_spec.loader.exec_module(helper)
                return helper.verify(image, manifest)
            finally:
                if inserted:
                    sys.path.remove(helper_directory)
        version7 = '_y35a_low_vector_v7' in sym
        names = ('base', 'record', 'halt', 'arm', 'warm', 'ready') + (
            ('c_enter', 'c_ready') if version7 else ('retire', 'retired')
        )
        a = {n: sym['_y35a_low_vector_' + n] for n in names}
        old = sym['_LowExceptionVectorBase']
        def check(condition, message):
            if not condition:
                failures.append(message)
        check(old % 4096 == 0 and a['base'] == old + 2048,
              'Diagnostic table must occupy the original page second half')
        check(a['record'] == a['base'] + 4 and a['halt'] < a['base'] + 128,
              'Recorder must fit entirely in the first 128-byte vector slot')
        for off in range(0, 2048, 128):
            check(m.word(old + off) == 0x14000000, 'Original spin vector changed')
            target = branch_target(a['base'] + off, m.word(a['base'] + off))
            expected = a['record'] if off in (0, 512) else a['base'] + off
            check(target == expected, f'Diagnostic vector {off:#x} target invalid')
        r = a['record']
        check(m.word(r) & 0xff00001f == 0xb500001c and
              branch_target(r, m.word(r)) == a['halt'], 'Missing x28 recursion guard')
        expected_prefix = [0xd280003c, 0xd5384038, 0xd5385219, 0xd538601a,
                           0xd538401b, 0xf9000678, 0xf9000a79, 0xf9000e7a, 0xd5033f9f]
        check([m.word(r + 4 + i * 4) for i in range(len(expected_prefix))] == expected_prefix,
              'First syndrome bank, payload stores, or payload barrier changed')
        expected_tail = [0x91002272, 0xd50b7a32, 0x91004272, 0xd50b7a32,
                         0x91006272, 0xd50b7a32, 0xd5033f9f,
                         0xd2866b31, 0xf2a826b1, 0xf2cac991, 0xf2e62611,
                         0xf9000271, 0xd5033f9f, 0xd50b7a33, 0xd5033f9f, 0x14000000]
        check([m.word(r + 40 + i * 4) for i in range(len(expected_tail))] == expected_tail,
              'Payload clean, unique commit, final clean, or halt changed')
        check(a['halt'] == r + 100, 'Unexpected recorder extent')
        arm = a['arm']
        check(m.word(arm) & 0xff00001f == 0xb5000015 and
              branch_target(arm, m.word(arm)) == a['warm'], 'Warm path must bypass arm')
        check(m.word(arm + 4) == 0x91200293 and m.word(arm + 8) == 0xd280001c,
              'Cold carrier/latch initialization changed')
        check(adrp_add(arm + 12, m.word(arm + 12), m.word(arm + 16), 0) == a['base'],
              'Cold VBAR does not use runtime-relative low vector')
        check([m.word(arm + i) for i in (20, 24, 28, 32, 36, 40)] ==
              [0xd518c000, 0xd5033fdf, 0xf900027f, 0xd5033f9f, 0xd50b7a33, 0xd5033f9f],
              'VBAR/ISB or stale-commit invalidation changed')
        check(branch_target(arm + 44, m.word(arm + 44)) == a['ready'],
              'Cold path does not skip high VBAR write')
        if version7:
            c_enter = a['c_enter']
            check(adrp_add(c_enter, m.word(c_enter), m.word(c_enter + 4), 16) == a['base'],
                  'R83 C handoff must reinstall the self-contained diagnostic vector')
            check([m.word(c_enter + i) for i in (8, 12, 16)] ==
                  [0xd518c010, 0xd5033fdf, 0xd65f03c0] and
                  a['c_ready'] == c_enter + 16,
                  'R83 C handoff must install VBAR, synchronize and return')
            body_end = c_enter
            report['diagnostic_window'] = 'retained through early C; a later production VBAR write ends it'
        else:
            retire = a['retire']
            check(adrp_add(retire, m.word(retire), m.word(retire + 4), 16) == old,
                  'Retirement must use original low spin vectors')
            check([m.word(retire + i) for i in (8, 12)] == [0xd518c010, 0xd5033fdf],
                  'Retirement VBAR/ISB changed')
            check(a['retired'] == retire + 16, 'Unexpected retirement extent')
            body_end = retire
            report['diagnostic_window'] = 'retired to original spin vectors before C'
        body = image[m.offset(a['ready']):m.offset(body_end)]
        check(body.count(BOUNDARY) == 1, 'SCTLR/ISB/MRS/first-store must remain adjacent')
        check(not any(m.word(p) & 0xfc000000 == 0x94000000
                      for p in range(a['ready'], body_end, 4)),
              'A call may clobber the borrowed registers before the diagnostic handoff')
        check(not any(m.word(p) & 0xffffffe0 == 0xd518c000
                      for p in range(a['ready'], body_end, 4)),
              'VBAR overwritten inside the diagnostic window')
        report['linked_addresses'] = {n: hex(v) for n, v in a.items()}
        report['sctlr_linked_pc'] = hex(a['ready'] + body.find(BOUNDARY)) if BOUNDARY in body else None
        report['limitations'] = 'Static instruction contract only; does not prove runtime translation, exception routing, or persistence. The terminal observer is not a normal recoverable handler.'
    except (KeyError, ValueError, struct.error) as error:
        failures.append(str(error))
    report['ok'] = not failures
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--kernel', required=True, type=Path)
    p.add_argument('--manifest', type=Path)
    args = p.parse_args()
    report = verify(
        args.kernel.read_bytes(),
        json.loads(args.manifest.read_text()) if args.manifest else None,
    )
    print(json.dumps(report, indent=2))
    return 0 if report['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
