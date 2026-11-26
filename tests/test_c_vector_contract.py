"""Fault injection against the actual linked early-C observer."""
import importlib.util
import json
import os
import copy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts/y35a'))
from verify_c_vector import MachO, verify


class CVectorContract(unittest.TestCase):
    def test_linked_kernel_rejects_broken_capture_and_nested_routing(self):
        path = os.environ.get('Y35A_C_VECTOR_KERNEL')
        if not path:
            self.skipTest('Set Y35A_C_VECTOR_KERNEL for binary fault injection')
        image = Path(path).read_bytes()
        self.assertEqual(verify(image)['failures'], [])
        macho = MachO(image)
        version3 = any(name in macho.symbols for name in
                       ('_y35a_low_vector_v3', '_y35a_low_vector_v4',
                        '_y35a_low_vector_v5', '_y35a_low_vector_v6',
                        '_y35a_low_vector_v7'))
        version4 = any(name in macho.symbols for name in
                       ('_y35a_low_vector_v4', '_y35a_low_vector_v5',
                        '_y35a_low_vector_v6', '_y35a_low_vector_v7'))
        cases = [
            ('base', 0x200, 0x14000000),
            ('record', 8, 0xd503201f),  # no switch to nested spin table
            ('record', 12, 0xd503201f), # missing context synchronization
            ('record', 16, 0xf9400018), # memory before saving syndrome
            ('record', 36, 0xd503201f), # C may have clobbered x19
            ('record', 40, 0xf9000278), # overwrite commit with ELR
            ('record', 68, 0xd503201f), # omit ESR cache clean
            ('record', 100 if version3 else 96, 0xf2e62611), # reject v1 commit
            ('halt', 0, 0xd69f03e0),    # return instead of terminal capture
            ('c_enter', 12, 0xd503201f),
        ]
        for name, delta, word in cases:
            with self.subTest(name=name, delta=delta):
                altered = bytearray(image)
                pos = macho.offset(macho.symbols['_y35a_low_vector_' + name] + delta)
                altered[pos:pos+4] = word.to_bytes(4, 'little')
                self.assertFalse(verify(bytes(altered))['ok'])
        if version3:
            pc = int(verify(image)['high_rearm_pc'], 0)
            for delta in (-8, 4):
                with self.subTest(high_rearm_delta=delta):
                    altered = bytearray(image)
                    pos = macho.offset(pc + delta)
                    altered[pos:pos+4] = (0xd503201f).to_bytes(4, 'little')
                    self.assertFalse(verify(bytes(altered))['ok'])
        if version4:
            record = macho.symbols['_y35a_low_vector_record']
            self.assertEqual(macho.word(record + 44), 0xa900e678)
            self.assertEqual(macho.word(record + 48), 0xa901fa7a)
            self.assertEqual(macho.word(record + 72), 0x91008272)
            altered = bytearray(image)
            pos = macho.offset(record + 48)
            altered[pos:pos+4] = (0xf9000e7a).to_bytes(4, 'little')
            self.assertFalse(verify(bytes(altered))['ok'])
        import hashlib
        manifest_path = os.environ.get('Y35A_C_VECTOR_MANIFEST')
        if manifest_path:
            manifest = json.loads(Path(manifest_path).read_text())
        else:
            report = verify(image)
            manifest = {'kernel_sha256': hashlib.sha256(image).hexdigest(),
                        'kernel_virtual_base':'0xfffffff007004000',
                        'kernel_physical_base':'0xa0004000', 'records':
                        [{'name':'early-fault-record',
                          'physical':hex(0xa0004000 + int(report['carrier_virtual'], 0) - 0xfffffff007004000),
                          'size':384}]}
        valid_manifest = copy.deepcopy(manifest)
        self.assertTrue(verify(image, valid_manifest)['ok'])
        original_physical = int(manifest['records'][0]['physical'], 0)
        manifest['records'][0]['physical'] = hex(original_physical + 8)
        self.assertFalse(verify(image, manifest)['ok'])
        if version3:
            altered = bytearray(image)
            pos = macho.offset(macho.symbols['_y35a_low_vector_record'] + 36)
            altered[pos:pos+4] = (macho.word(macho.symbols['_y35a_low_vector_record'] + 36) ^ (1 << 10)).to_bytes(4, 'little')
            self.assertFalse(verify(bytes(altered), valid_manifest)['ok'])


if __name__ == '__main__':
    unittest.main()
