from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = ROOT / "patches/xnu/native-y35a-amfi-stage-witness-r255.patch"


class Y35AAmfiStageWitnessR255Contract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.patch = PATCH.read_text()

    def test_patch_touches_only_loader_result_and_pre_init_snapshot(self):
        files = re.findall(r"^diff --git a/(.*?) b/", self.patch, re.MULTILINE)
        self.assertEqual(files, ["libsa/bootstrap.cpp", "bsd/kern/bsd_init.c"])

    def test_load_result_word_is_not_overlapped_by_the_tag(self):
        self.assertIn("((uint64_t)(uint32_t)load_result << 32)", self.patch)
        self.assertIn("0x4c4f4144ULL", self.patch)
        self.assertNotIn("|\n\t\t\t\t    0x414d46494c4f4144ULL", self.patch)
        # Exact XNU OSReturn bits must survive in the high word.
        result = 0xDC008015
        packed = (result << 32) | 0x4C4F4144
        self.assertEqual((packed >> 32) & 0xFFFFFFFF, result)
        self.assertEqual(packed & 0xFFFFFFFF, 0x4C4F4144)

    def test_stage_values_are_committed_before_initproc_can_fail(self):
        before_call = self.patch.index("load_init_program(p);")
        for slot in range(38, 47):
            marker = f"native_phase_marker_external({slot},"
            self.assertIn(marker, self.patch)
            self.assertLess(self.patch.index(marker), before_call)
        after_call = self.patch.index("native_phase_marker_external(47,", before_call)
        self.assertGreater(after_call, before_call)
        self.assertIn("native_r238_amfi_result", self.patch)
        self.assertIn("native_r253_loadexec_result", self.patch)
        self.assertIn("native_r253_start_result", self.patch)
        self.assertIn("native_r253_macreg_result", self.patch)


if __name__ == "__main__":
    unittest.main()
