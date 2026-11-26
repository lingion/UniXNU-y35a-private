import hashlib
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
PATCH = ROOT / "patches/xnu/native-y35a-tf-emmc-root-fallback.patch"


class TfEmmcRootFallbackPatchTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = PATCH.read_text()

    def test_patch_hash_and_scope(self):
        self.assertEqual(
            hashlib.sha256(PATCH.read_bytes()).hexdigest(),
            "f886e829b94999e79af06964ee274992d975382827191912d2ab8c8a8bd291eb",
        )
        self.assertEqual(
            re.findall(r"^--- a/(.*)$", self.text, re.MULTILINE),
            ["iokit/bsddev/IOKitBSDInit.cpp"],
        )

    def test_fallback_is_opt_in_and_requires_explicit_emmc_uuid(self):
        self.assertIn("XNU_Y35A_STORAGE_FALLBACK", self.text)
        self.assertIn('PE_parse_boot_argn("emmc-boot-uuid"', self.text)
        self.assertIn('!strcmp(mediaProperty, "boot-uuid-media")', self.text)
        self.assertIn("storageFallbackAttempted = false", self.text)
        self.assertEqual(self.text.count("storageFallbackAttempted = true"), 1)

    def test_fallback_replaces_uuid_matcher_only_after_tf_wait_failure(self):
        self.assertLess(self.text.index("if (!service && !storageFallbackAttempted"),
                        self.text.index("matching = fallbackMatching"))
        self.assertIn('removeProperty("boot-uuid")', self.text)
        self.assertIn('publishResource("boot-uuid", fallbackUUID)', self.text)


if __name__ == "__main__":
    unittest.main()
