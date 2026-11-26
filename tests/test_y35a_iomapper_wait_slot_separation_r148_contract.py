import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = ROOT / "patches/xnu/native-y35a-iomapper-wait-slot-separation-r148.patch"
R147 = ROOT / "patches/xnu/native-y35a-iomapper-wait-cursor-r147.patch"


class Y35AIomapperWaitSlotSeparationR148Contract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.patch = PATCH.read_text()
        cls.r147 = R147.read_text()
        cls.added = "\n".join(
            line[1:] for line in cls.patch.splitlines()
            if line.startswith("+") and not line.startswith("+++")
        )

    def test_only_mapper_owner_changes(self):
        paths = re.findall(r"^diff --git a/(.*?) b/", self.patch, re.MULTILINE)
        self.assertEqual(paths, ["iokit/Kernel/IOMapper.cpp"])

    def test_wait_loop_cursors_move_to_slot44(self):
        pairs = re.findall(
            r"native_phase_marker_external\(44,\s*(0x[0-9a-fA-F]+)ULL\);"
            r"\s*/\* (R148\w+) \*/", self.added)
        self.assertEqual(len(pairs), 4)
        self.assertEqual(len({name for _, name in pairs}), 4)
        for value, name in pairs:
            with self.subTest(name=name):
                self.assertEqual(int(value, 16), int.from_bytes(name.encode("ascii"), "little"))
                at = self.patch.index(name)
                guard = self.patch.rfind("#if defined(XNU_Y35A_A53) && XNU_Y35A_A53", 0, at)
                self.assertGreaterEqual(guard, 0)
                self.assertGreater(self.patch.find("#endif", at), at)
        self.assertIn("while ((uintptr_t) IOMapper::gSystem & kWaitMask)", self.r147)

    def test_main_call_cursor_remains_on_slot45(self):
        for marker in ("R147CPRE", "R147CKRT", "R147MAPR"):
            self.assertRegex(self.r147,
                             rf"native_phase_marker_external\(45,\s*0x[0-9a-fA-F]+ULL\);"
                             rf"\s*/\* {marker} \*/")
        self.assertNotIn("R147CPRE", self.added)
        self.assertNotIn("R147CKRT", self.added)

    def test_slot44_codewords_do_not_alias_existing_slot44_owners(self):
        new = {int(value, 16) for value, _ in re.findall(
            r"native_phase_marker_external\(44,\s*(0x[0-9a-fA-F]+)ULL\);"
            r"\s*/\* (R148\w+) \*/", self.added)}
        old = {int.from_bytes(name.encode("ascii"), "little")
               for name in ("R88SPL00", "R90MNTC0", "R90BTASK0")}
        self.assertTrue(new.isdisjoint(old))


if __name__ == "__main__":
    unittest.main()
