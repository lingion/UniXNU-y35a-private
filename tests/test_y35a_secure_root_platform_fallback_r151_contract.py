import re
import unittest
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = ROOT / "patches/xnu/native-y35a-secure-root-platform-fallback-r151.patch"
R150_PATCH = ROOT / "patches/xnu/native-y35a-platform-fallback-root-r150.patch"
MARKERS = {
    "R151REG0": 19,
    "R151SENT": 19,
    "R151MAT0": 19,
    "R151NUL0": 19,
    "R151SFRT": 19,
}


class Y35ASecureRootPlatformFallbackR151Contract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.patch = PATCH.read_text()
        cls.r150 = R150_PATCH.read_text()
        cls.added = "\n".join(
            line[1:] for line in cls.patch.splitlines()
            if line.startswith("+") and not line.startswith("+++")
        )

    def test_patch_touches_only_platform_start_and_secure_root(self):
        files = re.findall(r"^diff --git a/(.*?) b/", self.patch, re.MULTILINE)
        self.assertEqual(files, [
            "iokit/Kernel/IOPlatformExpert.cpp",
            "iokit/bsddev/IOKitBSDInit.cpp",
        ])

    def test_registration_happens_only_after_target_base_start_succeeds(self):
        fallback = self.r150[self.r150.index("IOPanicPlatform::start(IOService * provider)"):]
        self.assertIn('!strcmp(platform_name, "vivo,pd1502a")', fallback)
        self.assertIn("bool started = IOPlatformExpert::start(provider);", fallback)
        self.assertIn("return started;", fallback)
        self.assertIn("registerService();", self.added)
        self.assertIn("R151REG0", self.added)
        r151_fallback = self.patch[self.patch.index("bool started = IOPlatformExpert::start(provider);"):]
        register = r151_fallback.index("registerService();")
        self.assertIn("if (started)", fallback)
        self.assertLess(r151_fallback.index("R150PSOK"), register)
        self.assertLess(register, r151_fallback.index("} else {"))
        self.assertNotIn("registerService();", fallback)

    def test_secure_root_records_service_match_result_only_for_y35a(self):
        self.assertIn("native_phase_marker_external(19,", self.added)
        self.assertNotIn("IOService::getPlatform()", self.added)
        self.assertNotIn("pe->retain();", self.added)
        bsd = self.patch[self.patch.index("diff --git a/iokit/bsddev/IOKitBSDInit.cpp"):]
        secure = bsd[bsd.index("R151SENT"):]
        self.assertIn("#if defined(XNU_Y35A_A53) && XNU_Y35A_A53", bsd)
        self.assertIn("assert(pe);", self.patch)
        self.assertIn("OSSafeReleaseNULL(pe);", self.patch)
        self.assertIn("R151MAT0", secure)
        self.assertIn("R151NUL0", secure)

    def test_wait_result_and_platform_function_return_are_distinct_cursor_values(self):
        self.assertIn("pe = (IOPlatformExpert *) IOService::waitForMatchingService(matching, 30ULL * kSecondScale);", self.patch)
        self.assertIn("R151SENT", self.added)
        self.assertIn("R151MAT0", self.added)
        self.assertIn("R151NUL0", self.added)
        self.assertIn("R151SFRT", self.added)
        self.assertLess(self.patch.index("pe = (IOPlatformExpert *) IOService::waitForMatchingService"), self.patch.index("R151MAT0"))
        self.assertLess(self.patch.index("R151MAT0"), self.patch.index("assert(pe);"))
        self.assertLess(self.patch.index("result = pe->callPlatformFunction"), self.patch.index("R151SFRT"))

    def test_marker_names_slots_and_codewords_are_exact(self):
        found = re.findall(
            r"native_phase_marker_external\((\d+),\s*(0x[0-9a-fA-F]+)ULL\);"
            r"\s*/\* (R151\w+) \*/",
            self.added,
        )
        self.assertEqual(Counter(name for _, _, name in found), Counter({name: 1 for name in MARKERS}))
        for slot, value, name in found:
            self.assertEqual(int(slot), MARKERS[name], name)
            self.assertEqual(int(value, 16), int.from_bytes(name.encode("ascii"), "little"), name)
            self.assertEqual(len(name), 8, name)


if __name__ == "__main__":
    unittest.main()
