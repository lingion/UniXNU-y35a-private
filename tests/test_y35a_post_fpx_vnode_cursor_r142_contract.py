import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = ROOT / "patches/xnu/native-y35a-post-fpx-vnode-cursor-r142.patch"
SOURCE = ROOT / "upstream-refresh/2026-11-11/sources/xnu-ios12/repo/bsd/kern/bsd_init.c"


class Y35APostFpxVnodeCursorR142Contract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.patch = PATCH.read_text()
        cls.added = "\n".join(
            line[1:] for line in cls.patch.splitlines()
            if line.startswith("+") and not line.startswith("+++")
        )

    def test_only_bsd_init_owns_changes(self):
        paths = re.findall(r"^diff --git a/(.*?) b/", self.patch, re.MULTILINE)
        self.assertEqual(paths, ["bsd/kern/bsd_init.c"])

    def test_buffer_and_vnode_boundaries_are_bracketed_in_source_order(self):
        for marker in ("R142BPRE", "R142BRET", "R142VPRE", "R142VRET"):
            self.assertIn(marker, self.added)
        sequence = [
            self.patch.index('bsd_init_kprintf("calling bsd_bufferinit\\n");'),
            self.patch.index("R142BPRE"),
            self.patch.index("bsd_bufferinit();"),
            self.patch.index("R142BRET"),
            self.patch.index('bsd_init_kprintf("calling vnode_pager_bootstrap\\n");'),
            self.patch.index("R142VPRE"),
            self.patch.index("vnode_pager_bootstrap();"),
            self.patch.index("R142VRET"),
        ]
        self.assertEqual(sequence, sorted(sequence))

    def test_each_marker_is_y35a_guarded(self):
        for marker in ("R142BPRE", "R142BRET", "R142VPRE", "R142VRET"):
            at = self.patch.index(marker)
            guard = self.patch.rfind("#if defined(XNU_Y35A_A53) && XNU_Y35A_A53", 0, at)
            close = self.patch.find("#endif", at)
            self.assertGreaterEqual(guard, 0)
            self.assertGreater(close, at)

    def test_codewords_do_not_alias_prior_slot45_owners(self):
        new = {int.from_bytes(name.encode("ascii"), "little")
               for name in ("R142BPRE", "R142BRET", "R142VPRE", "R142VRET")}
        old = {int.from_bytes(name.encode("ascii"), "little") for name in (
            "PTSHIFT0", "R88SHR00", "R90MNTOK", "R90MNTER", "R90VMIL0",
            "R139VSR0", "R139CMP0", "R140PGM0", "R140CPU0", "R140CPRE",
            "R140CPUS", "R140CAP0", "R140BTM0", "R141MAXP", "R141MAXR")}
        self.assertTrue(new.isdisjoint(old))


if __name__ == "__main__":
    unittest.main()
