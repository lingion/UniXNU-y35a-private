import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = ROOT / "patches/xnu/native-y35a-mcache-mbinit-cursor-r144.patch"
R142 = ROOT / "patches/xnu/native-y35a-post-fpx-vnode-cursor-r142.patch"
R143 = ROOT / "patches/xnu/native-y35a-post-buffer-init-cursors-r143.patch"
SOURCE = ROOT / "upstream-refresh/2026-11-11/sources/xnu-ios12/repo/bsd/kern/bsd_init.c"


class Y35AMcacheMbinitCursorR144Contract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.patch = PATCH.read_text()
        cls.r142 = R142.read_text()
        cls.r143 = R143.read_text()
        cls.added = "\n".join(
            line[1:] for line in cls.patch.splitlines()
            if line.startswith("+") and not line.startswith("+++")
        )

    def test_only_bsd_init_owner_changes(self):
        paths = re.findall(r"^diff --git a/(.*?) b/", self.patch, re.MULTILINE)
        self.assertEqual(paths, ["bsd/kern/bsd_init.c"])

    def test_mcache_and_mbuf_calls_are_bracketed(self):
        for marker in ("R144MCB0", "R144MCR0", "R144MBP0", "R144MBR0"):
            self.assertIn(marker, self.added)
        ordered = [self.patch.index(s) for s in (
            "R144MCB0", "mcache_init();", "R144MCR0", "R144MBP0", "mbinit();", "R144MBR0")]
        self.assertEqual(ordered, sorted(ordered))

    def test_all_markers_are_y35a_guarded_slot45_stores(self):
        pairs = re.findall(
            r"native_phase_marker_external\(45,\s*(0x[0-9a-fA-F]+)ULL\);"
            r"\s*/\* (R144\w+) \*/", self.added)
        self.assertEqual(len(pairs), 4)
        for value, marker in pairs:
            with self.subTest(marker=marker):
                self.assertEqual(int(value, 16), int.from_bytes(marker.encode("ascii"), "little"))
                at = self.patch.index(marker)
                guard = self.patch.rfind("#if defined(XNU_Y35A_A53) && XNU_Y35A_A53", 0, at)
                close = self.patch.find("#endif", at)
                self.assertGreaterEqual(guard, 0)
                self.assertGreater(close, at)

    def test_r144_follows_r143_uid_and_precedes_pager(self):
        self.assertIn("R143UID0", self.r143)
        self.assertIn("R143VFS0", self.r143)
        self.assertIn("R142VPRE", self.r142)
        source = SOURCE.read_text()
        ordered = [source.index(s) for s in (
            "proc_uuid_policy_init();", "mcache_init();", "mbinit();",
            "pipeinit();", 'bsd_init_kprintf("calling vnode_pager_bootstrap\\n");')]
        self.assertEqual(ordered, sorted(ordered))

    def test_codewords_do_not_alias_prior_slot45_owners(self):
        new = {int(value, 16) for value, _ in re.findall(
            r"native_phase_marker_external\(45,\s*(0x[0-9a-fA-F]+)ULL\);"
            r"\s*/\* (R144\w+) \*/", self.added)}
        old = {int.from_bytes(name.encode("ascii"), "little") for name in (
            "PTSHIFT0", "R88SHR00", "R90MNTOK", "R90MNTER", "R90VMIL0",
            "R139VSR0", "R139CMP0", "R140CPRE", "R140CPUS", "R141MAXP",
            "R141MAXR", "R142BPRE", "R142BRET", "R143TPRE", "R143TRET",
            "R143UID0", "R143NET0")}
        self.assertEqual(len(new), 4)
        self.assertTrue(new.isdisjoint(old))


if __name__ == "__main__":
    unittest.main()
