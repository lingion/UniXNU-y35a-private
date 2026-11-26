import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = ROOT / "patches/xnu/native-y35a-post-buffer-init-cursors-r143.patch"
R142 = ROOT / "patches/xnu/native-y35a-post-fpx-vnode-cursor-r142.patch"
SOURCE = ROOT / "upstream-refresh/2026-11-11/sources/xnu-ios12/repo/bsd/kern/bsd_init.c"


class Y35APostBufferInitCursorR143Contract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.patch = PATCH.read_text()
        cls.r142 = R142.read_text()
        cls.added = "\n".join(
            line[1:] for line in cls.patch.splitlines()
            if line.startswith("+") and not line.startswith("+++")
        )

    def test_only_bsd_init_owner_changes(self):
        paths = re.findall(r"^diff --git a/(.*?) b/", self.patch, re.MULTILINE)
        self.assertEqual(paths, ["bsd/kern/bsd_init.c"])

    def test_all_markers_are_unique_y35a_slot45_writes(self):
        markers = ("R143TPRE", "R143TRET", "R143UBC0", "R143VFS0", "R143UID0",
                   "R143MBI0", "R143PIP0", "R143PSH0", "R143PSE0", "R143TZN0",
                   "R143SEL0", "R143SOC0", "R143DOM0", "R143IPT0", "R143AUT0", "R143NET0")
        self.assertEqual(len(markers), len(set(markers)))
        for marker in markers:
            with self.subTest(marker=marker):
                self.assertRegex(
                    self.added,
                    rf"native_phase_marker_external\(45,\s*0x[0-9a-fA-F]+ULL\);"
                    rf"\s*/\* {marker} \*/",
                )
                at = self.patch.index(marker)
                guard = self.patch.rfind("#if defined(XNU_Y35A_A53) && XNU_Y35A_A53", 0, at)
                close = self.patch.find("#endif", at)
                self.assertGreaterEqual(guard, 0)
                self.assertGreater(close, at)

    def test_iokit_time_and_vnode_calls_are_bracketed(self):
        ordered = [self.patch.index(s) for s in (
            "R143TPRE", "IOKitInitializeTime();", "R143TRET")]
        self.assertEqual(ordered, sorted(ordered))
        vnode = [self.r142.index(s) for s in (
            "R142VPRE", "vnode_pager_bootstrap();", "R142VRET")]
        self.assertEqual(vnode, sorted(vnode))

    def test_network_cursor_is_inside_networking_configuration(self):
        marker = self.patch.index("R143NET0")
        close = self.patch.index("#endif /* NETWORKING */", marker)
        self.assertLess(marker, close)

    def test_core_subsystem_returns_follow_the_existing_calls(self):
        ordered = [self.patch.index(s) for s in (
            "ubc_init();", "R143UBC0", "vfsinit();", "R143VFS0",
            "proc_uuid_policy_init();", "R143UID0", "mbinit();", "R143MBI0",
            "pipeinit();", "R143PIP0", "pshm_lock_init();", "R143PSH0",
            "psem_lock_init();", "R143PSE0", "time_zone_slock_init();", "R143TZN0",
            "select_waitq_init();", "R143SEL0", "socketinit();", "R143SOC0",
            "domaininit();", "R143DOM0", "iptap_init();", "R143IPT0",
            "bsd_autoconf();", "R143AUT0", "R143NET0")]
        self.assertEqual(ordered, sorted(ordered))

    def test_pinned_source_call_order_matches_instrumentation_plan(self):
        source = SOURCE.read_text()
        calls = [
            'bsd_init_kprintf("calling bsd_bufferinit\\n");',
            'bsd_init_kprintf("calling IOKitInitializeTime\\n");',
            "ubc_init();", "vfsinit();", "proc_uuid_policy_init();", "mbinit();",
            "pipeinit();", "pshm_lock_init();", "psem_lock_init();",
            "time_zone_slock_init();", "select_waitq_init();", "socketinit();",
            "domaininit();", "iptap_init();", "bsd_autoconf();",
            'bsd_init_kprintf("calling vnode_pager_bootstrap\\n");',
            "vnode_pager_bootstrap();",
        ]
        positions = [source.index(call) for call in calls]
        self.assertEqual(positions, sorted(positions))

    def test_codewords_do_not_alias_prior_slot45_owners(self):
        added_values = re.findall(
            r"native_phase_marker_external\(45,\s*(0x[0-9a-fA-F]+)ULL\);"
            r"\s*/\* (R143\w+) \*/", self.added)
        new = {int(value, 16) for value, _ in added_values}
        self.assertEqual(len(new), 16)
        for value, marker in added_values:
            with self.subTest(marker=marker):
                self.assertEqual(int(value, 16), int.from_bytes(marker.encode("ascii"), "little"))
        old = {int.from_bytes(name.encode("ascii"), "little") for name in (
            "PTSHIFT0", "R88SHR00", "R90MNTOK", "R90MNTER", "R90VMIL0",
            "R139VSR0", "R139CMP0", "R140PGM0", "R140CPU0", "R140CPRE",
            "R140CPUS", "R140CAP0", "R140BTM0", "R141MAXP", "R141MAXR",
            "R142BPRE", "R142BRET", "R142VPRE", "R142VRET")}
        self.assertTrue(new.isdisjoint(old))


if __name__ == "__main__":
    unittest.main()
