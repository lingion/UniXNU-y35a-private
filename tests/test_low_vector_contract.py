"""Offline binary contracts. Set Y35A_LOW_VECTOR_KERNEL to a newly linked kernel."""
import importlib.util
import os
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('verify_low_vector', ROOT / 'scripts/y35a/verify_low_vector.py')


class LowVectorContract(unittest.TestCase):
    def test_patch_has_independent_switch_and_no_unrelated_targets(self):
        text = (ROOT / 'patches/xnu/native-y35a-low-vector-v1.patch').read_text()
        self.assertIn('XNU_Y35A_LOW_VECTOR', text)
        self.assertEqual([s for s in text.splitlines() if s.startswith('+++ ')],
                         ['+++ b/osfmk/arm64/start.s'])
        self.assertNotIn('+\teret', text)

    def test_real_linked_kernel_and_mutations(self):
        path = os.environ.get('Y35A_LOW_VECTOR_KERNEL')
        if not path:
            self.skipTest('Set Y35A_LOW_VECTOR_KERNEL to run the linked-binary gate and negative cases')
        module = importlib.util.module_from_spec(SPEC)
        SPEC.loader.exec_module(module)
        image = Path(path).read_bytes()
        self.assertEqual(module.verify(image)['failures'], [])
        macho = module.MachO(image)
        # Each mutation changes actual linked machine code, not source text.
        mutations = {
            'EL1h sync lost': ('_y35a_low_vector_base', 0x200, 0x14000000),
            'busy guard lost': ('_y35a_low_vector_record', 0, 0xd503201f),
            'first ELR capture lost': ('_y35a_low_vector_record', 8, 0xd503201f),
            'payload store touches SPSR slot': ('_y35a_low_vector_record', 24, 0xf900127b),
            'payload barrier lost': ('_y35a_low_vector_record', 36, 0xd503201f),
            'arm ISB lost': ('_y35a_low_vector_arm', 24, 0xd503201f),
        }
        if '_y35a_low_vector_retire' in macho.symbols:
            mutations['retire ISB lost'] = ('_y35a_low_vector_retire', 12, 0xd503201f)
        else:
            mutations['C handoff ISB lost'] = ('_y35a_low_vector_c_enter', 12, 0xd503201f)
        for name, (symbol, delta, word) in mutations.items():
            with self.subTest(name=name):
                mutated = bytearray(image)
                offset = macho.offset(macho.symbols[symbol] + delta, 4)
                mutated[offset:offset+4] = word.to_bytes(4, 'little')
                self.assertTrue(module.verify(bytes(mutated))['failures'], name)
        # The MMU boundary must stay adjacent in the linked binary.
        boundary = module.BOUNDARY
        offset = image.index(boundary)
        mutated = image[:offset+4] + bytes.fromhex('1f2003d5') + image[offset+8:]
        self.assertTrue(module.verify(mutated)['failures'])


if __name__ == '__main__':
    unittest.main()
