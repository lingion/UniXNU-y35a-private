from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "run_native_build", ROOT / "scripts/ci/run_native_build.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class NativeBuildGateTests(unittest.TestCase):
    def test_source_provenance_must_match_ordered_manifest_and_dependencies(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source_path = root / "source.json"
            patches = [{"order": 0, "target_tree": "xnu-source", "path": "p.patch", "sha256": "a" * 64}]
            source = {
                "source": {"commit": "xnu-pin"},
                "patches": patches,
                "external_driver_patches": [],
                "source_diff": None,
                "kernel_dependency_versions": {
                    "libdispatch": "dispatch-pin", "libplatform": "platform-pin"},
                "native_input_commits": {
                    "availability": "availability-commit", "libdispatch": "dispatch-commit",
                    "libplatform": "platform-commit", "llvm": "llvm-commit", "libc": "libc-commit"},
            }
            source_path.write_text(json.dumps(source))
            manifest = {
                "source_ref": "xnu-pin", "source_provenance": "source.json",
                "source_provenance_sha256": MODULE.sha256(source_path),
                "patches": patches,
                "external_driver_patches": [],
                "native_inputs": {
                    "availability_commit": "availability-commit",
                    "libdispatch_tag": "dispatch-pin", "libdispatch_commit": "dispatch-commit",
                    "libplatform_tag": "platform-pin", "libplatform_commit": "platform-commit",
                    "llvm_commit": "llvm-commit", "libc_commit": "libc-commit"},
            }
            self.assertEqual(MODULE.validate_native_provenance(manifest, root), source)
            manifest["patches"][0]["sha256"] = "b" * 64
            with self.assertRaisesRegex(SystemExit, "ordered XNU patch list"):
                MODULE.validate_native_provenance(manifest, root)

    def test_prepared_input_manifest_must_match_every_pinned_dependency(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "native-inputs.json"
            expected = {
                "availability_tag": "availability-pin", "availability_commit": "availability-commit",
                "libdispatch_tag": "dispatch-pin", "libdispatch_commit": "dispatch-commit",
                "libplatform_tag": "platform-pin", "libplatform_commit": "platform-commit",
                "llvm_commit": "llvm-commit",
                "libc_commit": "libc-commit",
            }
            data = {
                "source": {"xnu_commit": "xnu-pin", **expected},
                "trees": {"fakeroot_sha256": "a" * 64, "sdk_overlay_sha256": "b" * 64,
                          "xcrun_wrapper_sha256": "c" * 64},
            }
            path.write_text(json.dumps(data))
            roots = [Path(temp) / name for name in ("fakeroot", "sdk", "wrapper")]
            for root in roots[:2]:
                root.mkdir()
            roots[2].write_text("wrapper")
            roots[2].chmod(0o755)
            data["paths"] = dict(zip(("fakeroot", "sdk_overlay", "xcrun_wrapper"),
                                     map(str, roots)))
            data["trees"] = {
                "fakeroot_sha256": MODULE.tree_sha256(roots[0]),
                "sdk_overlay_sha256": MODULE.tree_sha256(roots[1]),
                "xcrun_wrapper_sha256": MODULE.sha256(roots[2]),
            }
            path.write_text(json.dumps(data))
            MODULE.validate_native_inputs_manifest(
                path, expected, source_ref="xnu-pin", fakeroot=roots[0],
                sdk_overlay=roots[1], xcrun_wrapper=roots[2])
            data["source"]["libplatform_tag"] = "wrong-pin"
            path.write_text(json.dumps(data))
            with self.assertRaisesRegex(SystemExit, "prepared native input versions"):
                MODULE.validate_native_inputs_manifest(
                    path, expected, source_ref="xnu-pin", fakeroot=roots[0],
                    sdk_overlay=roots[1], xcrun_wrapper=roots[2])


if __name__ == "__main__":
    unittest.main()
