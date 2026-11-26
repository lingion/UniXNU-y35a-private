import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = ROOT / "patches/xnu/native-y35a-shared-region-cursor-r139.patch"


class Y35ASharedRegionCursorContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not PATCH.is_file():
            raise AssertionError(f"R139 source patch has not been created: {PATCH}")
        cls.patch = PATCH.read_text()
        cls.added = "\n".join(
            line[1:] for line in cls.patch.splitlines()
            if line.startswith("+") and not line.startswith("+++")
        )

    def test_patch_changes_only_the_early_vm_startup_owner(self):
        paths = re.findall(r"^diff --git a/(.*?) b/", self.patch, re.MULTILINE)
        self.assertEqual(paths, ["osfmk/kern/startup.c"])

    def test_sequential_cursors_use_the_existing_captured_slot(self):
        for marker in ("R139VSR0", "R139CMP0"):
            with self.subTest(marker=marker):
                self.assertRegex(
                    self.added,
                    rf"native_phase_marker_external\(45,\s*0x[0-9a-fA-F]+ULL\);"
                    rf"\s*/\* {marker} \*/",
                )
        positions = [self.patch.index(marker) for marker in
                     ("vm_shared_region_init();", "R139VSR0", "vm_commpage_init();",
                      "R139CMP0", "vm_commpage_text_init();", "R88SHR00")]
        self.assertEqual(positions, sorted(positions))
        self.assertNotIn("R139TXT0", self.patch)

    def test_existing_startup_order_and_terminal_shared_marker_remain(self):
        self.assertIn("vm_shared_region_init();", self.patch)
        self.assertIn("vm_commpage_init();", self.patch)
        self.assertIn("vm_commpage_text_init();", self.patch)
        self.assertIn("native_phase_marker_external(45, 0x3030524853383852ULL); /* R88SHR00 */",
                      self.patch)

    def test_slot45_codewords_are_distinct_from_its_existing_sequential_owners(self):
        new = {int.from_bytes(name.encode("ascii"), "little")
               for name in ("R139VSR0", "R139CMP0")}
        old = {int.from_bytes(name.encode("ascii"), "little")
               for name in ("PTSHIFT0", "R88SHR00", "R90MNTOK", "R90MNTER", "R90VMIL0")}
        self.assertTrue(new.isdisjoint(old))


if __name__ == "__main__":
    unittest.main()
