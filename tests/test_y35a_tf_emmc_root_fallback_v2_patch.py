import hashlib
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
PATCH = ROOT / "patches/xnu/native-y35a-tf-emmc-root-fallback-v2.patch"
MANIFEST = ROOT / "ci/manifests/r208-tf-emmc-root-fallback-v2-candidate.json"


class TfEmmcRootFallbackV2PatchTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = PATCH.read_text()

    def test_patch_hash_scope_and_source_contract(self):
        self.assertEqual(
            hashlib.sha256(PATCH.read_bytes()).hexdigest(),
            "1863a52b087dfc25e2fbf132c36f2ceae03777f82efbf1843b178cfc193c8670",
        )
        self.assertEqual(
            re.findall(r"^--- a/(.*)$", self.text, re.MULTILINE),
            ["bsd/kern/bsd_init.c", "iokit/bsddev/IOKitBSDInit.cpp"],
        )
        manifest = MANIFEST.read_text()
        self.assertIn('"source_ref": "xnu-4903.270.47"', manifest)
        self.assertIn('"device_run_allowed": false', manifest)

    def test_fallback_is_triggered_after_mountroot_failure_once(self):
        self.assertIn("IOY35ARequestEmmcRootFallback", self.text)
        self.assertIn("if (!storageFallbackAttempted && IOY35ARequestEmmcRootFallback())", self.text)
        self.assertIn("storageFallbackAttempted = TRUE", self.text)
        self.assertIn("setconf();", self.text)
        self.assertIn("continue;", self.text)
        mount_failure = self.text.index("if (0 == (err = vfs_mountroot()))")
        fallback = self.text.index("IOY35ARequestEmmcRootFallback()")
        self.assertGreater(fallback, mount_failure)

    def test_fallback_reselects_emmc_uuid_and_skips_original_chosen_uuid(self):
        self.assertIn("native_y35a_emmc_fallback_active", self.text)
        self.assertIn('PE_parse_boot_argn("emmc-boot-uuid"', self.text)
        self.assertIn('IOService::publishResource("boot-uuid", fallbackUUID)', self.text)
        self.assertIn("matching = IOUUIDMatching()", self.text)
        self.assertIn('mediaProperty = "boot-uuid-media"', self.text)
        self.assertIn("if (native_y35a_emmc_fallback_active)", self.text)

    def test_candidate_is_not_the_production_manifest(self):
        native_manifest = (ROOT / "ci/native-build-manifest.r208.json").read_text()
        self.assertNotIn("native-y35a-tf-emmc-root-fallback-v2.patch", native_manifest)


if __name__ == "__main__":
    unittest.main()
