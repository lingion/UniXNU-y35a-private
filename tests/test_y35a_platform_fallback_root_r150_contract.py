import re
import unittest
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = ROOT / "patches/xnu/native-y35a-platform-fallback-root-r150.patch"
MARKERS = {
    "R150PENT": 20,
    "R150MPYE": 20,
    "R150MPNO": 20,
    "R150PSOK": 21,
    "R150PSNO": 21,
    "R150MRIN": 22,
    "R150MROK": 22,
    "R150MRER": 22,
    "R150RVOK": 23,
    "R150UKEN": 24,
    "R150UKRT": 24,
}


class Y35APlatformFallbackRootR150Contract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.patch = PATCH.read_text()
        cls.added = "\n".join(
            line[1:] for line in cls.patch.splitlines()
            if line.startswith("+") and not line.startswith("+++")
        )

    def test_patch_touches_only_platform_mapper_and_bsd_root_boundaries(self):
        files = re.findall(r"^diff --git a/(.*?) b/", self.patch, re.MULTILINE)
        self.assertEqual(files, [
            "bsd/kern/bsd_init.c",
            "iokit/Kernel/IOMapper.cpp",
            "iokit/Kernel/IOPlatformExpert.cpp",
        ])

    def test_marker_names_slots_and_codewords_are_exact(self):
        found = re.findall(
            r"native_phase_marker_external\((\d+),\s*(0x[0-9a-fA-F]+)ULL\);"
            r"\s*/\* (R150\w+) \*/",
            self.added,
        )
        names = [name for _, _, name in found]
        self.assertEqual(Counter(names), Counter({name: 1 for name in MARKERS}))
        for slot, value, name in found:
            self.assertEqual(int(slot), MARKERS[name], name)
            self.assertEqual(int(value, 16), int.from_bytes(name.encode("ascii"), "little"), name)
            self.assertEqual(len(name), 8, name)

    def test_y35a_fallback_calls_generic_base_and_keeps_other_build_panic(self):
        self.assertIn("native_phase_marker_external(20, 0x544E455030353152ULL); /* R150PENT */", self.added)
        self.assertIn("bool started = IOPlatformExpert::start(provider);", self.added)
        self.assertIn('!strcmp(platform_name, "vivo,pd1502a")', self.added)
        self.assertIn("if (started) {", self.added)
        self.assertIn("native_phase_marker_external(21, 0x4B4F535030353152ULL); /* R150PSOK */", self.added)
        self.assertIn("native_phase_marker_external(21, 0x4F4E535030353152ULL); /* R150PSNO */", self.added)
        panic_hunk = self.patch[self.patch.index("IOPanicPlatform::start(IOService * provider)"):]
        guard_start = panic_hunk.index("#if defined(XNU_Y35A_A53) && XNU_Y35A_A53")
        guard_end = panic_hunk.index("#endif", guard_start)
        fallback = panic_hunk[guard_start:guard_end]
        self.assertIn('!strcmp(platform_name, "vivo,pd1502a")', fallback)
        self.assertIn("bool started = IOPlatformExpert::start(provider);", fallback)
        self.assertIn("return started;", fallback)
        self.assertLess(guard_end, panic_hunk.index('panic("Unable to find driver for this platform'))
        self.assertIn("native_phase_marker_external(20, 0x4559504D30353152ULL); /* R150MPYE */", self.added)
        self.assertIn("native_phase_marker_external(20, 0x4F4E504D30353152ULL); /* R150MPNO */", self.added)
        decision = self.patch[self.patch.index("if (provider && provider->getName() &&"):]
        decision = decision[:decision.index("#else")]
        self.assertIn('!strcmp(provider->getName(), "vivo,pd1502a")', decision)
        self.assertIn("R150MPYE", decision)
        self.assertIn("R150MPNO", decision)

    def test_root_mount_cursor_distinguishes_no_return_success_and_error(self):
        self.assertIn("native_phase_marker_external(22, 0x4E49524D30353152ULL); /* R150MRIN */", self.added)
        self.assertIn("native_phase_marker_external(22, 0x4B4F524D30353152ULL); /* R150MROK */", self.added)
        self.assertIn("native_phase_marker_external(22, 0x5245524D30353152ULL); /* R150MRER */", self.added)
        self.assertLess(self.patch.index("R150MRIN"), self.patch.index("err = vfs_mountroot();"))
        self.assertLess(self.patch.index("err = vfs_mountroot();"), self.patch.index("R150MROK"))
        self.assertLess(self.patch.index("err = vfs_mountroot();"), self.patch.index("R150MRER"))

    def test_root_vnode_marker_is_after_successful_vfs_root_only(self):
        root_check = self.patch.index("if (VFS_ROOT(mountlist.tqh_first, &rootvnode, &context))")
        panic = self.patch.index('panic("bsd_init: cannot find root vnode: %s", PE_boot_args());')
        marker = self.patch.index("R150RVOK")
        flag_write = self.patch.index("rootvnode->v_flag |= VROOT;")
        self.assertLess(root_check, panic)
        self.assertLess(panic, marker)
        self.assertLess(marker, flag_write)

    def test_mapper_witness_is_limited_to_unknown_fallback_and_zero_return(self):
        mapper = self.patch[self.patch.index("IOMapper.cpp"):]
        self.assertIsNotNone(re.search(r"if \(mapper_state == 1\) \{.*?R150UKEN", mapper, re.DOTALL))
        self.assertIsNotNone(re.search(
            r"if \(mapper_state == 1\)\s*\{.*?native_phase_marker_external\(24, 0x4E454B5530353152ULL\); /\* R150UKEN \*/.*?ret = kIOReturnUnsupported;",
            mapper,
            re.DOTALL,
        ))
        mapper_return = mapper.index("R150UKRT")
        self.assertIn("if (mapper_state == 1)", mapper[:mapper_return])
        self.assertIn("return 0;", mapper[mapper_return:])
        self.assertNotIn("IOMapper::gSystem =", self.added)


if __name__ == "__main__":
    unittest.main()
