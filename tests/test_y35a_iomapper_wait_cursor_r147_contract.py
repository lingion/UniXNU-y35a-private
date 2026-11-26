import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = ROOT / "patches/xnu/native-y35a-iomapper-wait-cursor-r147.patch"
R146 = ROOT / "patches/xnu/native-y35a-mbuf-allocation-cursors-r146.patch"
SOURCE = ROOT / "upstream-refresh/2026-11-11/sources/xnu-ios12/repo/iokit/Kernel/IOMapper.cpp"


class Y35AIOMMapperWaitCursorR147Contract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.patch = PATCH.read_text()
        cls.r146 = R146.read_text()
        cls.added = "\n".join(
            line[1:] for line in cls.patch.splitlines()
            if line.startswith("+") and not line.startswith("+++")
        )

    def test_only_mapper_owner_changes(self):
        paths = re.findall(r"^diff --git a/(.*?) b/", self.patch, re.MULTILINE)
        self.assertEqual(paths, ["iokit/Kernel/IOMapper.cpp"])

    def test_wait_state_and_return_markers_match_states(self):
        expectations = {
            "R147UNT0": "mapper_state == 1",
            "R147REQ0": "mapper_state == 2",
            "R147WHT0": "R147WHT0",
            "R147WRT0": "R147WRT0",
            "R147CPRE": "R147CPRE",
            "R147CKRT": "R147CKRT",
            "R147MAPR": "R147MAPR",
        }
        for marker, nearby in expectations.items():
            with self.subTest(marker=marker):
                self.assertIn(marker, self.patch)
                at = self.patch.index(marker)
                guard = self.patch.rfind("#if defined(XNU_Y35A_A53) && XNU_Y35A_A53", 0, at)
                close = self.patch.find("#endif", at)
                self.assertGreaterEqual(guard, 0)
                self.assertGreater(close, at)
                if marker in ("R147UNT0", "R147REQ0"):
                    self.assertIn(nearby, self.patch)

    def test_call_order_separates_wait_from_mapping(self):
        self.assertLess(self.added.index("R147CPRE"), self.added.index("IOMapper::checkForSystemMapper();"))
        self.assertLess(self.added.index("IOMapper::checkForSystemMapper();"),
                        self.added.index("R147CKRT"))
        source = SOURCE.read_text()
        positions = [source.index(s) for s in (
            "IOMapper::checkForSystemMapper();", "ret = kIOReturnUnsupported;",
            "iovmMapMemory(", "if (kIOReturnSuccess == ret)")]
        self.assertEqual(positions, sorted(positions))
        self.assertIn("while ((uintptr_t) IOMapper::gSystem & kWaitMask)", self.patch)
        self.assertIn("sMapperLock.sleep(&IOMapper::gSystem);", self.patch)

    def test_r147_follows_the_r146_iovm_pre_call_boundary(self):
        self.assertIn("R146IPR0", self.r146)
        self.assertIn("IOMapperIOVMAlloc(mcl_pages)", self.r146)
        self.assertIn("R146IRT0", self.r146)

    def test_codewords_are_unique_from_prior_slot45_owners(self):
        pairs = re.findall(
            r"native_phase_marker_external\(45,\s*(0x[0-9a-fA-F]+)ULL\);"
            r"\s*/\* (R147\w+) \*/", self.added)
        self.assertEqual(len(pairs), 7)
        new = {int(value, 16) for value, _ in pairs}
        for value, marker in pairs:
            self.assertEqual(int(value, 16), int.from_bytes(marker.encode("ascii"), "little"))
        old = {int.from_bytes(name.encode("ascii"), "little") for name in (
            "PTSHIFT0", "R88SHR00", "R90MNTOK", "R90MNTER", "R90VMIL0",
            "R139VSR0", "R139CMP0", "R140CPRE", "R141MAXP", "R142BRET",
            "R143UID0", "R144MBP0", "R145CPU0", "R146IPR0")}
        self.assertTrue(new.isdisjoint(old))


if __name__ == "__main__":
    unittest.main()
