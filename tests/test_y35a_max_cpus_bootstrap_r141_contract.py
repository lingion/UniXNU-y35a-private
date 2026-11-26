import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = ROOT / "patches/xnu/native-y35a-max-cpus-bootstrap-r141.patch"
SOURCE = ROOT / "upstream-refresh/2026-11-11/sources/xnu-ios12/repo"


class Y35AMaxCPUsBootstrapR141Contract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.patch = PATCH.read_text()
        cls.added = "\n".join(
            line[1:] for line in cls.patch.splitlines()
            if line.startswith("+") and not line.startswith("+++")
        )

    def test_only_commpage_owner_changes(self):
        paths = re.findall(r"^diff --git a/(.*?) b/", self.patch, re.MULTILINE)
        self.assertEqual(paths, ["osfmk/arm/commpage/commpage.c"])

    def test_existing_topology_count_initializes_before_wait(self):
        pre = self.patch.index("R141MAXP")
        setter = self.patch.index("ml_init_max_cpus(ml_get_cpu_count());")
        returned = self.patch.index("R141MAXR")
        wait_pre = self.patch.index("R140CPRE")
        self.assertLess(pre, setter)
        self.assertLess(setter, returned)
        self.assertLess(returned, wait_pre)

    def test_setter_is_y35a_only_and_uses_topology_count(self):
        for marker in ("R141MAXP", "R141MAXR"):
            at = self.patch.index(marker)
            self.assertGreaterEqual(
                self.patch.rfind("#if defined(XNU_Y35A_A53) && XNU_Y35A_A53", 0, at), 0
            )
            self.assertGreater(self.patch.find("#endif", at), at)
        self.assertNotIn("ml_init_max_cpus(1)", self.added)

    def test_topology_count_honors_single_cpu_boot_argument(self):
        routines = (SOURCE / "osfmk/arm64/machine_routines.c").read_text()
        arm_init = (SOURCE / "osfmk/arm/arm_init.c").read_text()
        self.assertIn('PE_parse_boot_argn("cpus", &cpu_boot_arg, sizeof(cpu_boot_arg));', routines)
        self.assertIn("if (avail_cpus > cpu_boot_arg)", routines)
        self.assertIn("ml_parse_cpu_topology();", arm_init)
        self.assertIn("unsigned int\nml_get_cpu_count(void)", routines)

    def test_marker_codewords_are_unique_from_known_slot45_owners(self):
        new = {int.from_bytes(name.encode("ascii"), "little")
               for name in ("R141MAXP", "R141MAXR")}
        old = {int.from_bytes(name.encode("ascii"), "little") for name in
               ("PTSHIFT0", "R88SHR00", "R90MNTOK", "R90MNTER", "R90VMIL0",
                "R139VSR0", "R139CMP0", "R140PGM0", "R140CPU0", "R140CPRE",
                "R140CPUS", "R140CAP0", "R140BTM0")}
        self.assertTrue(new.isdisjoint(old))


if __name__ == "__main__":
    unittest.main()
