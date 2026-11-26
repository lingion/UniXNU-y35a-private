#!/usr/bin/env python3
"""Validate the terminal early-C vector against linked code and probe geometry.

This observer does not return from exceptions. It uses no incoming GPR, stack,
thread object or global pointer. Nested exceptions use the original spin table.
The checks establish a binary contract, not runtime routing or persistence.
"""
import argparse
import hashlib
import json
from pathlib import Path

from verify_low_vector import MachO, BOUNDARY, adrp_add, branch_target, signed


def add_x19_imm(word, base, shifted):
    """Decode one 64-bit ADD X19,X19,#imm instruction with a fixed shift."""
    expected = 0x91400273 if shifted else 0x91000273
    if word & 0xffc003ff != expected or ((word >> 22) & 1) != int(shifted):
        raise ValueError('Version 3 carrier ADD instruction is malformed')
    immediate = (word >> 10) & 0xfff
    return base + (immediate << (12 if shifted else 0))


def verify(image, manifest=None):
    failures = []
    result = {'kernel_sha256': hashlib.sha256(image).hexdigest(), 'failures': failures}
    def check(ok, message):
        if not ok:
            failures.append(message)
    try:
        m = MachO(image)
        version = (7 if '_y35a_low_vector_v7' in m.symbols else
                   6 if '_y35a_low_vector_v6' in m.symbols else
                   5 if '_y35a_low_vector_v5' in m.symbols else
                   4 if '_y35a_low_vector_v4' in m.symbols else
                   3 if '_y35a_low_vector_v3' in m.symbols else 2)
        names = ('base', 'record', 'halt', 'arm', 'warm', 'ready', 'c_enter', 'c_ready', 'v' + str(version))
        a = {n: m.symbols['_y35a_low_vector_' + n] for n in names}
        old = m.symbols['_LowExceptionVectorBase']
        check(old % 4096 == 0 and a['base'] == old + 2048 and a['v' + str(version)] == a['base'],
              'Diagnostic must use the second half of the original low vector page')
        extra = {2: 0, 3: 4, 4: 0, 5: 0, 6: 0, 7: 0}[version]
        if version >= 4:
            check(a['record'] == a['base'] + 4 and a['halt'] == a['base'] + 120,
                  'Version 4 recorder must stop before the next vector slot')
            check(m.word(a['halt']) == 0x14000000 and m.word(a['base'] + 124) == 0xd503201f,
                  'Version 4 terminal sink and remaining EL1t vector slots must remain closed')
        else:
            check(a['record'] == a['base'] + 4 and a['halt'] == a['record'] + 116 + extra,
              'Recorder must end before the next 128-byte vector slot')
        for off in range(0, 2048, 128):
            check(m.word(old + off) == 0x14000000, 'Nested exception sink changed')
            target = branch_target(a['base'] + off, m.word(a['base'] + off))
            check(target == (a['record'] if off in (0, 512) else a['base'] + off),
                  f'Unexpected vector destination at {off:#x}')
        r = a['record']
        check(adrp_add(r, m.word(r), m.word(r + 4), 18) == old,
              'Recorder must select original spin vectors without a memory read')
        # Exact prefix rejects memory access before the syndrome bank and rejects
        # dependence on a register that a C function could have overwritten.
        prefix = [0xd518c012, 0xd5033fdf, 0xd5384038, 0xd5385219,
                  0xd538601a, 0xd538401b]
        carrier_virtual = None
        if version >= 3:
            # ADRP to the same vector page naturally follows the handler's
            # low/high runtime alias. ADD immediates carry the package-specific
            # physical location of the early-fault record.
            word = m.word(r + 32)
            check(adrp_add(r + 32, word, 0x91000273, 19) == old,
                  'Version 3 carrier must anchor to the original vector page')
            high_add, low_add = m.word(r + 36), m.word(r + 40)
            carrier_virtual = add_x19_imm(low_add,
                add_x19_imm(high_add, old, True), False)
            prefix += [word, high_add, low_add]
        else:
            prefix += [0xd2890013, 0xf2b41733]
        if version >= 4:
            prefix += [0xa900e678, 0xa901fa7a, 0xd5033f9f]
        else:
            prefix += [0xf9000678, 0xf9000a79, 0xf9000e7a, 0xd5033f9f]
        check([m.word(r + 8 + i * 4) for i in range(len(prefix))] == prefix,
              'Nested routing, register snapshot or fixed carrier initialization changed')
        if version >= 4:
            tail = [0x91002272, 0xd50b7a32, 0x91006272, 0xd50b7a32,
                    0x91008272, 0xd50b7a32]
        else:
            tail = [0x91002272, 0xd50b7a32, 0x91004272, 0xd50b7a32,
                    0x91006272, 0xd50b7a32]
        tail += [0xd5033f9f, 0xd2866b31, 0xf2a826b1, 0xf2cac991,
                 0xf2e6e611 if version == 7 else 0xf2e6c611 if version == 6 else 0xf2e6a611 if version == 5 else 0xf2e68611 if version == 4 else 0xf2e66611 if version == 3 else 0xf2e64611,
                0xf9000271, 0xd5033f9f, 0xd50b7a33, 0xd5033f9f, 0x14000000]
        tail_offset = 4 if version == 3 else 0
        check([m.word(r + 56 + tail_offset + i * 4) for i in range(len(tail))] == tail,
              'Payload-before-commit, clean sequence, v2 magic or terminal halt changed')
        if version >= 4:
            check([m.word(r + offset) for offset in (120, 124)] == [0xd503201f, 0x14000000],
                  'Version 4 must end before the EL1t IRQ and lower-EL slots')
        arm = a['arm']
        check(m.word(arm) & 0xff00001f == 0xb5000015 and
              branch_target(arm, m.word(arm)) == a['warm'], 'Warm boot must bypass cold arm')
        check(m.word(arm + 4) == 0x91200293, 'Cold invalidation carrier changed')
        check(adrp_add(arm + 12, m.word(arm + 12), m.word(arm + 16), 0) == a['base'],
              'Cold path must install the runtime-relative diagnostic vector')
        check([m.word(arm + i) for i in (20, 24, 28, 32, 36, 40)] ==
              [0xd518c000, 0xd5033fdf, 0xf900027f, 0xd5033f9f, 0xd50b7a33, 0xd5033f9f],
              'Cold vector installation or stale commit invalidation changed')
        check(branch_target(arm + 44, m.word(arm + 44)) == a['ready'],
              'Cold arm must skip the high thread-dependent VBAR')
        c = a['c_enter']
        check(adrp_add(c, m.word(c), m.word(c + 4), 16) == a['base'],
              'C handoff must keep the self-contained diagnostic vector')
        check([m.word(c + i) for i in (8, 12, 16)] ==
              [0xd518c010, 0xd5033fdf, 0xd65f03c0] and a['c_ready'] == c + 16,
              'C handoff must install VBAR, synchronize and return to arm_init')
        body = image[m.offset(a['ready']):m.offset(c)]
        check(body.count(BOUNDARY) == 1, 'SCTLR/ISB/MRS/first STR must remain adjacent')
        check(not any(m.word(p) & 0xffffffe0 == 0xd518c000
                      for p in range(a['ready'], c, 4)), 'Unexpected VBAR writer before C')
        if version >= 3:
            start = m.symbols['_arm_init']
            end = m.symbols['_arm_init_cpu']
            writes = [p for p in range(start, end, 4)
                      if m.word(p) & 0xffffffe0 == 0xd518c000]
            check(len(writes) == 1, 'Post-console C path must re-arm VBAR exactly once')
            if len(writes) == 1:
                pc = writes[0]
                reg = m.word(pc) & 31
                adr = m.word(pc - 8)
                imm = (((adr >> 5) & 0x7ffff) << 2) | ((adr >> 29) & 3)
                check(adr & 0x9f00001f == 0x10000000 | reg and
                      pc - 8 + signed(imm, 21) == a['base'] and
                      m.word(pc - 4) == 0xd503201f and m.word(pc + 4) == 0xd5033fdf,
                      'Post-console VBAR must use linked high diagnostic address and ISB')
                calls = [(p, p + 4 * signed(m.word(p) & 0x3ffffff, 26))
                         for p in range(start, end, 4)
                         if m.word(p) & 0xfc000000 == 0x94000000]
                console = [p for p, target in calls if target == m.symbols['_PE_create_console']]
                idle = [p for p, target in calls if target == m.symbols['_cpu_machine_idle_init']]
                check(len(console) == len(idle) == 1 and console[0] < pc < idle[0],
                      'High re-arm must be after console creation and before idle setup')
                result['high_rearm_pc'] = hex(pc)
        if manifest is not None:
            check(manifest.get('kernel_sha256') == result['kernel_sha256'],
                  'Probe manifest must bind this kernel hash')
            records = [x for x in manifest['records'] if x['name'] == 'early-fault-record']
            check(len(records) == 1, 'Exactly one fault carrier is required')
            if len(records) == 1:
                record = records[0]
                record_physical = int(str(record['physical']), 0)
                check(record['size'] >= (40 if version >= 4 else 32),
                      'Probe carrier is too small for the fault record')
                if version >= 3:
                    va = int(manifest['kernel_virtual_base'], 0)
                    pa = int(manifest['kernel_physical_base'], 0)
                    kernel_va_base = min(segment[0] for segment in m.segments if segment[3])
                    check(va == kernel_va_base, 'Probe kernel_virtual_base disagrees with Mach-O')
                    check(pa + carrier_virtual - va == record_physical,
                          'PC-relative carrier delta does not match package layout')
                else:
                    check(record_physical == 0xa0b94800,
                          'Version 2 probe carrier does not match its fixed address')
                result['carrier_physical'] = hex(record_physical)
        result['linked_addresses'] = {n: hex(v) for n, v in a.items()}
        result['sctlr_linked_pc'] = hex(a['ready'] + body.find(BOUNDARY))
        result['carrier_virtual'] = hex(carrier_virtual) if carrier_virtual is not None else None
        if version == 2:
            result['carrier_physical'] = '0xa0b94800'
        result['magic'] = 'Y35ALV0' + str(version)
        result['terminal_link_register_slot'] = 4 if version >= 4 else None
        result['limitations'] = ('Only first synchronous EL1 exception can be retained. '
            'Nested exceptions spin; no ERET or normal exception recovery. SPSR remains '
            'in x27 only. Requires the selected low/high mapping and writable carrier; a later '
            'VBAR write or translation change can end coverage. No full GPR snapshot.')
    except (KeyError, ValueError) as error:
        failures.append(str(error))
    result['ok'] = not failures
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kernel', required=True, type=Path)
    parser.add_argument('--manifest', type=Path)
    args = parser.parse_args()
    report = verify(args.kernel.read_bytes(), json.loads(args.manifest.read_text()) if args.manifest else None)
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report['ok'] else 1)
