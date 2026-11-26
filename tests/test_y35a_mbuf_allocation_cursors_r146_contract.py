import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = ROOT / "patches/xnu/native-y35a-mbuf-allocation-cursors-r146.patch"
R145 = ROOT / "patches/xnu/native-y35a-mbuf-internal-cursors-r145.patch"


class Y35AMbufAllocationCursorsR146Contract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.patch = PATCH.read_text()
        cls.r145 = R145.read_text()
        cls.added = "\n".join(
            line[1:] for line in cls.patch.splitlines()
            if line.startswith("+") and not line.startswith("+++")
        )

    def test_only_mbuf_owner_changes(self):
        paths = re.findall(r"^diff --git a/(.*?) b/", self.patch, re.MULTILINE)
        self.assertEqual(paths, ["bsd/kern/uipc_mbuf.c"])

    def test_all_markers_are_unique_guarded_slot45_stores(self):
        pairs = re.findall(
            r"native_phase_marker_external\(45,\s*(0x[0-9a-fA-F]+)ULL\);"
            r"\s*/\* (R146\w+) \*/", self.added)
        self.assertEqual(len(pairs), 6)
        for value, marker in pairs:
            with self.subTest(marker=marker):
                self.assertEqual(int(value, 16), int.from_bytes(marker.encode("ascii"), "little"))
                at = self.patch.index(marker)
                guard = self.patch.rfind("#if defined(XNU_Y35A_A53) && XNU_Y35A_A53", 0, at)
                close = self.patch.find("#endif", at)
                self.assertGreaterEqual(guard, 0)
                self.assertGreater(close, at)

    def test_allocations_and_iovm_call_are_bracketed_in_order(self):
        ordered = [self.patch.index(s) for s in (
            "R145CPU0", "R146BPR0", "MALLOC(buf,", "R146BRT0",
            "MALLOC(mcl_paddr,", "R146PRT0", "R146IPR0",
            "IOMapperIOVMAlloc(mcl_pages)", "R146IRT0", "R145IOV0")]
        self.assertEqual(ordered, sorted(ordered))

    def test_r146_starts_inside_the_r145_cpu_to_iovm_window(self):
        self.assertIn("R145CPU0", self.r145)
        self.assertIn("R145IOV0", self.r145)
        self.assertLess(self.r145.index("R145CPU0"), self.r145.index("R145IOV0"))

    def test_codewords_do_not_alias_prior_slot45_owners(self):
        new = {int(value, 16) for value, _ in re.findall(
            r"native_phase_marker_external\(45,\s*(0x[0-9a-fA-F]+)ULL\);"
            r"\s*/\* (R146\w+) \*/", self.added)}
        old = {int.from_bytes(name.encode("ascii"), "little") for name in (
            "PTSHIFT0", "R88SHR00", "R90MNTOK", "R90MNTER", "R90VMIL0",
            "R139VSR0", "R139CMP0", "R140CPRE", "R140CPUS", "R141MAXP",
            "R141MAXR", "R142BPRE", "R142BRET", "R143UID0", "R144MBP0",
            "R145CPU0", "R145IOV0")}
        self.assertTrue(new.isdisjoint(old))


if __name__ == "__main__":
    unittest.main()
