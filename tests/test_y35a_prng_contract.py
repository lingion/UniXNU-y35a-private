"""Binary contract checks for early Y35A PRNG registration."""
import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/y35a"))
from verify_y35a_prng import direct_bl_targets, verify
from verify_phase_instrumentation import (
    Y35A_BOOTSTRAP_PHASES, classify_y35a_bootstrap_phase,
)


class Y35APrngContract(unittest.TestCase):
    def test_bootstrap_phase_freshness_requires_known_changed_codeword(self):
        self.assertEqual(len(Y35A_BOOTSTRAP_PHASES), 19)
        self.assertEqual(
            Y35A_BOOTSTRAP_PHASES[int.from_bytes(b"R82ARM00", "little")],
            "R82ARM00",
        )
        self.assertEqual(
            Y35A_BOOTSTRAP_PHASES[int.from_bytes(b"R84ARM00", "little")],
            "R84ARM00",
        )
        self.assertEqual(
            Y35A_BOOTSTRAP_PHASES[int.from_bytes(b"R84LATE0", "little")],
            "R84LATE0",
        )
        self.assertEqual(
            Y35A_BOOTSTRAP_PHASES[int.from_bytes(b"R81UCP00", "little")],
            "R81UCP00",
        )
        self.assertEqual(len(set(Y35A_BOOTSTRAP_PHASES)), 19)
        for codeword in Y35A_BOOTSTRAP_PHASES:
            with self.subTest(stage=Y35A_BOOTSTRAP_PHASES[codeword]):
                self.assertEqual(classify_y35a_bootstrap_phase(codeword, 0), "fresh")
                self.assertEqual(classify_y35a_bootstrap_phase(codeword, codeword), "unchanged")
                self.assertEqual(classify_y35a_bootstrap_phase(codeword, None),
                                 "present-freshness-unknown")
        self.assertEqual(classify_y35a_bootstrap_phase(0, 0), "zero")
        self.assertEqual(classify_y35a_bootstrap_phase(0xDEADBEEF, 0), "unknown")
        self.assertEqual(
            Y35A_BOOTSTRAP_PHASES[int.from_bytes(b"R81RD005", "little")],
            "R81RD005",
        )

    def test_direct_bl_decoder_accepts_only_bl_words_and_sign_extends(self):
        from verify_low_vector import MachO
        kernel = ROOT / "evidence/y35a-20261102/boot3-20261106/phase-r77-lock-caller-20261112/kernel/kernel.macho"
        if not kernel.exists():
            self.skipTest("linked Y35A kernel is unavailable")
        macho = MachO(kernel.read_bytes())
        pc = macho.symbols["_kernel_bootstrap_thread"]
        targets = direct_bl_targets(kernel.read_bytes(), pc, pc + 4)
        self.assertEqual(targets, [])

    def test_r77_fixture_is_rejected_without_prng_provider(self):
        kernel = ROOT / "evidence/y35a-20261102/boot3-20261106/phase-r77-lock-caller-20261112/kernel/kernel.macho"
        if not kernel.exists():
            self.skipTest("linked Y35A kernel is unavailable")
        result = verify(kernel.read_bytes())
        self.assertFalse(result["ok"])
        self.assertTrue(any("_y35a_prng_bootstrap_init" in failure
                            for failure in result["failures"]))

    def test_linked_y35a_kernel_registers_provider_before_random_consumers(self):
        path = os.environ.get("Y35A_PRNG_KERNEL")
        if not path:
            self.skipTest("Set Y35A_PRNG_KERNEL to the linked Y35A kernel")
        result = verify(Path(path).read_bytes())
        self.assertTrue(result["ok"], result)
        self.assertLess(int(result["registration_call_pcs"][0], 0),
                        int(result["idle_thread_create_call_pcs"][0], 0))
        self.assertLess(int(result["registration_call_pcs"][0], 0),
                        min(int(value, 0) for value in result["read_random_call_pcs"]))

    def test_readback_layout_exports_the_initialization_witness(self):
        import readback_native
        for name, width in (("_y35a_prng_bootstrap_entered", 4),
                            ("_y35a_prng_bootstrap_returned", 4),
                            ("_y35a_prng_registration_started", 4),
                            ("_y35a_prng_initialized", 4),
                            ("_y35a_prng_lock_pointer", 8),
                            ("_y35a_bootstrap_phase", 8),
                            ("_native_read_random_lock_after_marker_direct", 8)):
            self.assertIn(name, readback_native.NAMES)
            self.assertIn(name, readback_native.BOUNDARY_NAMES)
            self.assertEqual(readback_native.field_bytes(name), width)
            self.assertEqual(readback_native._record_size(name), 16)


if __name__ == "__main__":
    unittest.main()
