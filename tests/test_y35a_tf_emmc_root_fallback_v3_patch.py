import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
PATCH = ROOT / "patches/xnu/native-y35a-tf-emmc-root-fallback-v3.patch"
CANDIDATE = ROOT / "ci/manifests/r208-tf-emmc-root-fallback-v3-candidate.json"
MANIFEST = ROOT / "ci/native-build-manifest.r208-fallback-v3.json"
PROVENANCE = ROOT / "ci/native-source-provenance.r208-fallback-v3.json"


class TfEmmcRootFallbackV3PatchTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.patch_text = PATCH.read_text()
        cls.candidate = json.loads(CANDIDATE.read_text())
        cls.manifest = json.loads(MANIFEST.read_text())
        cls.provenance = json.loads(PROVENANCE.read_text())

    def test_candidate_hash_and_ordered_patch_chain_are_bound(self):
        digest = hashlib.sha256(PATCH.read_bytes()).hexdigest()
        self.assertEqual(self.candidate["patch"]["sha256"], digest)
        self.assertEqual(self.manifest["fallback_candidate"]["path"],
                         "patches/xnu/native-y35a-tf-emmc-root-fallback-v3.patch")
        self.assertEqual(self.manifest["fallback_candidate"]["sha256"], digest)
        patches = self.manifest["patches"]
        self.assertEqual(sum(item["path"] == self.manifest["fallback_candidate"]["path"]
                             for item in patches), 1)
        self.assertFalse(any(item["path"].endswith("fallback-v2.patch") for item in patches))
        self.assertIn("--y35a-storage-fallback", self.manifest["build"]["flags"])
        self.assertEqual(self.provenance["patches"], patches)

    def test_uuid_service_wait_is_bounded_and_returns_to_setconf(self):
        bsd_patch, iokit_patch = self.patch_text.split(
            "--- a/iokit/bsddev/IOKitBSDInit.cpp", 1)
        declaration_hunk = iokit_patch.index("@@ -399,")
        root_selector_hunk = iokit_patch.index("@@ -453,")
        self.assertLess(declaration_hunk, root_selector_hunk)
        self.assertIn("y35aBoundedRootWait = native_y35a_tf_root_selected && matching", iokit_patch)
        self.assertIn("native_y35a_tf_root_selected && matching", iokit_patch)
        self.assertIn("++y35aRootWaitAttempts >= 3", iokit_patch)
        self.assertIn("return kIOReturnNotFound", iokit_patch)
        initial_read = bsd_patch.index("err = IOFindBSDRoot")
        fallback = bsd_patch.index("IOY35ARequestEmmcRootFallback()", initial_read)
        default_root = bsd_patch.index("setting rootdevice to 'sd0a'")
        self.assertLess(initial_read, fallback)
        self.assertLess(fallback, default_root)

    def test_mountroot_failure_reselects_emmc_once_and_repeated_failure_fails_closed(self):
        mountroot = self.patch_text.index("vfs_mountroot()")
        switch = self.patch_text.index("IOY35ARequestEmmcRootFallback()", mountroot)
        self.assertGreater(switch, mountroot)
        self.assertIn("native_y35a_emmc_fallback_active", self.patch_text)
        self.assertIn("single fallback attempt", self.patch_text)
        self.assertIn("without emmc-boot-uuid", self.patch_text)

    def test_candidate_requires_the_tf_and_emmc_selectors(self):
        self.assertEqual(self.candidate["tf_selector"], "boot-uuid")
        self.assertEqual(self.candidate["emmc_selector"], "emmc-boot-uuid")
        self.assertEqual(self.candidate["bounded_wait_attempts"], 3)
        self.assertEqual(self.candidate["device_run_allowed"], False)
        driver = self.manifest["driver_artifact"]
        self.assertEqual(driver["run_id"], 46064499637)
        self.assertEqual(driver["artifact_id"], 15230012212)
        self.assertEqual(driver["artifact_zip_digest"],
                         "sha256:c595d163be57d921d31270c680307f4277b9889f693c72b1d54241c06fa15e0e")
        self.assertEqual(driver["head_sha"], "f2444c978e6750cbd6422a7c4b8790c300958333")

    def test_candidate_is_not_the_production_manifest(self):
        production = (ROOT / "ci/native-build-manifest.r208.json").read_text()
        self.assertNotIn("native-y35a-tf-emmc-root-fallback-v3.patch", production)


if __name__ == "__main__":
    unittest.main()
