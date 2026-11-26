from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = ROOT / "patches/xnu/native-y35a-amfi-slide-witness-r256.patch"


class Y35AAmfiSlideWitnessR256Contract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.patch = PATCH.read_text()

    def test_patch_touches_only_bsd_init(self):
        files = re.findall(r"^diff --git a/(.*?) b/", self.patch, re.MULTILINE)
        self.assertEqual(files, ["bsd/kern/bsd_init.c"])

    def test_runtime_mapping_inputs_are_committed_before_initproc(self):
        call = self.patch.index("load_init_program(p);")
        expected = (
            "native_phase_marker_external(34, (uint64_t)gPhysBase);",
            "native_phase_marker_external(35, (uint64_t)gVirtBase);",
            "native_phase_marker_external(36, (uint64_t)vm_kernel_slide);",
        )
        positions = [self.patch.index(item) for item in expected]
        self.assertEqual(positions, sorted(positions))
        self.assertTrue(all(position < call for position in positions))
        self.assertIn("extern unsigned long gPhysBase;", self.patch)
        self.assertIn("extern unsigned long gVirtBase;", self.patch)
        self.assertIn("extern vm_offset_t vm_kernel_slide;", self.patch)


if __name__ == "__main__":
    unittest.main()
