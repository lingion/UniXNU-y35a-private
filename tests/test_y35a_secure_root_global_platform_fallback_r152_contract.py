import re
import unittest
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = ROOT / "patches/xnu/native-y35a-secure-root-global-platform-fallback-r152.patch"
R150_PATCH = ROOT / "patches/xnu/native-y35a-platform-fallback-root-r150.patch"
R151_PATCH = ROOT / "patches/xnu/native-y35a-secure-root-platform-fallback-r151.patch"
MARKERS = {
    "R152REG0": 17,
    "R152GPLO": 18,
    "R152GNUL": 18,
    "R152CMAT": 18,
    "R152SOK0": 19,
    "R152SNPR": 19,
    "R152SOTH": 19,
}


class Y35ASecureRootGlobalPlatformFallbackR152Contract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.patch = PATCH.read_text()
        cls.r150 = R150_PATCH.read_text()
        cls.r151 = R151_PATCH.read_text()
        cls.added = "\n".join(
            line[1:] for line in cls.patch.splitlines()
            if line.startswith("+") and not line.startswith("+++")
        )

    def test_patch_files_and_scope(self):
        self.assertEqual(
            re.findall(r"^diff --git a/(.*?) b/", self.patch, re.MULTILINE),
            ["iokit/Kernel/IOPlatformExpert.cpp", "iokit/bsddev/IOKitBSDInit.cpp"],
        )

    def test_register_service_marker_is_after_successful_target_fallback(self):
        fallback = self.r150[self.r150.index("IOPanicPlatform::start(IOService * provider)"):]
        self.assertIn('!strcmp(platform_name, "vivo,pd1502a")', fallback)
        self.assertIn("bool started = IOPlatformExpert::start(provider);", fallback)
        self.assertIn("registerService();", self.r151)
        self.assertIn("R151REG0", self.r151)
        self.assertIn("R152REG0", self.added)
        self.assertLess(self.patch.index("R151REG0"), self.patch.index("R152REG0"))

    def test_global_platform_used_only_after_class_wait_returns_null(self):
        wait = self.r151.index("IOService::waitForMatchingService(matching, 30ULL * kSecondScale)")
        wait_null = self.r151.index("R151NUL0")
        global_lookup = self.patch.index("pe = IOService::getPlatform();")
        self.assertLess(wait, wait_null)
        self.assertLess(self.patch.index("R151NUL0"), global_lookup)
        self.assertIn("if (pe == NULL)", self.added)
        self.assertIn("pe->retain();", self.added)
        self.assertIn("OSSafeReleaseNULL(pe);", self.patch)
        self.assertIn("R152GPLO", self.added)
        self.assertIn("R152GNUL", self.added)
        self.assertIn("R152CMAT", self.added)

    def test_fallback_is_y35a_only_and_keeps_original_wait(self):
        global_lookup = self.patch.index("pe = IOService::getPlatform();")
        self.assertIn("XNU_Y35A_A53", self.r151)
        self.assertIn("R151SENT", self.r151)
        null_marker = self.patch.index("R151NUL0")
        end = self.patch.index("#endif", null_marker)
        self.assertLess(null_marker, global_lookup)
        self.assertLess(global_lookup, end)
        self.assertIn("pe = (IOPlatformExpert *) IOService::waitForMatchingService(matching, 30ULL * kSecondScale);", self.r151)
        self.assertIn("assert(pe);", self.patch)

    def test_secure_root_result_code_markers_follow_call(self):
        self.assertIn("result = pe->callPlatformFunction", self.patch)
        call = self.patch.index("result = pe->callPlatformFunction")
        for name in ("R152SOK0", "R152SNPR", "R152SOTH"):
            self.assertIn(name, self.added)
            self.assertLess(call, self.patch.index(name))
        self.assertIn("result == kIOReturnNotPrivileged", self.patch)
        self.assertIn("result == kIOReturnSuccess", self.patch)

    def test_marker_names_slots_and_codewords_are_exact(self):
        found = re.findall(
            r"native_phase_marker_external\((\d+),\s*(0x[0-9a-fA-F]+)ULL\);"
            r"\s*/\* (R152\w+) \*/",
            self.added,
        )
        self.assertEqual(Counter(name for _, _, name in found), Counter({name: 1 for name in MARKERS}))
        for slot, value, name in found:
            self.assertEqual(int(slot), MARKERS[name], name)
            self.assertEqual(int(value, 16), int.from_bytes(name.encode("ascii"), "little"), name)
            self.assertEqual(len(name), 8, name)


if __name__ == "__main__":
    unittest.main()
