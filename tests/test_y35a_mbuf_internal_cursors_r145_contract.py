import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = ROOT / "patches/xnu/native-y35a-mbuf-internal-cursors-r145.patch"
R144 = ROOT / "patches/xnu/native-y35a-mcache-mbinit-cursor-r144.patch"


class Y35AMbufInternalCursorsR145Contract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.patch = PATCH.read_text()
        cls.r144 = R144.read_text()
        cls.added = "\n".join(
            line[1:] for line in cls.patch.splitlines()
            if line.startswith("+") and not line.startswith("+++")
        )

    def test_only_mbuf_owner_changes(self):
        paths = re.findall(r"^diff --git a/(.*?) b/", self.patch, re.MULTILINE)
        self.assertEqual(paths, ["bsd/kern/uipc_mbuf.c"])

    def test_internal_markers_are_unique_guarded_slot45_stores(self):
        pairs = re.findall(
            r"native_phase_marker_external\(45,\s*(0x[0-9a-fA-F]+)ULL\);"
            r"\s*/\* (R145\w+) \*/", self.added)
        self.assertEqual(len(pairs), 13)
        self.assertEqual(len({marker for _, marker in pairs}), 13)
        for value, marker in pairs:
            with self.subTest(marker=marker):
                self.assertEqual(int(value, 16), int.from_bytes(marker.encode("ascii"), "little"))
                at = self.patch.index(marker)
                guard = self.patch.rfind("#if defined(XNU_Y35A_A53) && XNU_Y35A_A53", 0, at)
                close = self.patch.find("#endif", at)
                self.assertGreaterEqual(guard, 0)
                self.assertGreater(close, at)

    def test_internal_boundaries_follow_mbuf_stages(self):
        ordered = [self.patch.index(s) for s in (
            "microuptime(&mb_start);", "R145TIM0", "R145RND0", "mbuf_table_init();",
            "R145TAB0", "R145LCK0", "R145SLB0", "R145LEK0", "ml_get_max_cpus();",
            "R145CPU0", "IOMapperIOVMAlloc(mcl_pages)", "R145IOV0", "R145FRE0",
            "R145WKR0", "R145CAC0", "R145DMP0", "R145END0")]
        self.assertEqual(ordered, sorted(ordered))

    def test_internal_cursor_follows_r144_mbuf_pre_call(self):
        self.assertIn("R144MBP0", self.r144)
        self.assertIn("R144MBR0", self.r144)
        self.assertLess(self.r144.index("R144MBP0"), self.r144.index("R144MBR0"))

    def test_codewords_do_not_alias_previous_slot45_owners(self):
        new = {int(value, 16) for value, _ in re.findall(
            r"native_phase_marker_external\(45,\s*(0x[0-9a-fA-F]+)ULL\);"
            r"\s*/\* (R145\w+) \*/", self.added)}
        old = {int.from_bytes(name.encode("ascii"), "little") for name in (
            "PTSHIFT0", "R88SHR00", "R90MNTOK", "R90MNTER", "R90VMIL0",
            "R139VSR0", "R139CMP0", "R140CPRE", "R140CPUS", "R141MAXP",
            "R141MAXR", "R142BPRE", "R142BRET", "R143UID0", "R143MBI0",
            "R144MCB0", "R144MCR0", "R144MBP0", "R144MBR0")}
        self.assertTrue(new.isdisjoint(old))


if __name__ == "__main__":
    unittest.main()
