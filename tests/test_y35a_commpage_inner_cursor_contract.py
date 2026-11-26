import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = ROOT / "patches/xnu/native-y35a-commpage-inner-cursor-r140.patch"
BASE_SOURCE = (ROOT / "upstream-refresh/2026-11-11/sources/xnu-ios12/repo/"
               "osfmk/arm/commpage/commpage.c")


class Y35ACommpageInnerCursorContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not PATCH.is_file():
            raise AssertionError(f"R140 source patch is missing: {PATCH}")
        cls.patch = PATCH.read_text()
        cls.added = "\n".join(
            line[1:] for line in cls.patch.splitlines()
            if line.startswith("+") and not line.startswith("+++")
        )

    def test_only_commpage_owner_changes(self):
        paths = re.findall(r"^diff --git a/(.*?) b/", self.patch, re.MULTILINE)
        self.assertEqual(paths, ["osfmk/arm/commpage/commpage.c"])

    def test_sharedpage_and_cpu_info_boundaries_use_slot45(self):
        for marker in ("R140PGM0", "R140CPU0", "R140CPRE", "R140CPUS", "R140CAP0", "R140BTM0"):
            with self.subTest(marker=marker):
                self.assertRegex(
                    self.added,
                    rf"native_phase_marker_external\(45,\s*0x[0-9a-fA-F]+ULL\);"
                    rf"\s*/\* {marker} \*/",
                )

    def test_ml_get_max_cpus_is_bracketed(self):
        cpuinfo = self.patch.index("ml_cpu_get_info(&cpu_info);")
        cpuinfo_cursor = self.patch.index("/* R140CPU0 */")
        pre = self.patch.index("/* R140CPRE */")
        call = self.patch.index("ml_get_max_cpus();")
        post = self.patch.index("/* R140CPUS */")
        self.assertLess(cpuinfo, cpuinfo_cursor)
        self.assertLess(pre, call)
        self.assertLess(call, post)

    def test_capability_and_boottime_boundaries_are_sequential(self):
        names = ("pmap_create_sharedpage();", "R140PGM0",
                 "commpage_init_cpu_capabilities();", "R140CAP0",
                 "commpage_update_boottime(", "R140BTM0")
        positions = [self.patch.index(name) for name in names]
        self.assertEqual(positions, sorted(positions))

    def test_cpu_info_and_max_cpu_wait_have_ordered_cursors(self):
        source = BASE_SOURCE.read_text()
        start = source.index("commpage_init_cpu_capabilities( void )")
        end = source.index("* Updated every time", start)
        helper = source[start:end]
        self.assertLess(helper.index("ml_cpu_get_info(&cpu_info);"),
                        helper.index("cpus = commpage_cpus();"))
        self.assertLess(self.patch.index("ml_cpu_get_info(&cpu_info);"),
                        self.patch.index("/* R140CPU0 */"))

    def test_all_r140_cursor_writes_are_guarded_for_y35a_only(self):
        for marker in ("R140PGM0", "R140CPU0", "R140CPRE", "R140CPUS", "R140CAP0", "R140BTM0"):
            with self.subTest(marker=marker):
                index = self.added.index(marker)
                guard = self.added.rfind("#if defined(XNU_Y35A_A53) && XNU_Y35A_A53", 0, index)
                close = self.added.find("#endif", index)
                self.assertGreaterEqual(guard, 0)
                self.assertGreater(close, index)

    def test_codewords_do_not_alias_known_slot45_writers(self):
        new = {int.from_bytes(name.encode("ascii"), "little") for name in
               ("R140PGM0", "R140CPU0", "R140CPRE", "R140CPUS", "R140CAP0", "R140BTM0")}
        old = {int.from_bytes(name.encode("ascii"), "little") for name in
               ("PTSHIFT0", "R88SHR00", "R90MNTOK", "R90MNTER", "R90VMIL0",
                "R139VSR0", "R139CMP0")}
        self.assertTrue(new.isdisjoint(old))


if __name__ == "__main__":
    unittest.main()
