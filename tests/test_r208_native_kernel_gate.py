from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "verify_r208_native_kernel", ROOT / "scripts/ci/verify_r208_native_kernel.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class R208NativeKernelGateTests(unittest.TestCase):
    def test_passes_only_with_matching_kernel_build_and_driver_symbols(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            kernel = root / "kernel.macho"
            kernel.write_bytes(b"linked kernel fixture")
            staged_source = root / "src"
            staged_source.mkdir()
            (staged_source / "kernel-source.c").write_text("source")
            diff_path = root / "inputs/staged-source-compatibility.diff"
            diff_path.parent.mkdir()
            diff_path.write_bytes(b"compat diff")
            driver_manifest = root / "driver-manifest.json"
            driver_manifest.write_text(json.dumps({
                "archive": {"sha256": "a" * 64},
            }))
            driver_manifest_sha = hashlib.sha256(driver_manifest.read_bytes()).hexdigest()
            provenance = root / "build-provenance.json"
            provenance.write_text(json.dumps({
                "run_root": str(root),
                "status": "prepared",
                "source_identity": {"commit": "494ffe1c29d37ca720c37328feb83069c9641b67"},
                "build_profile": {"y35a_a53": True, "phase_a_amfi": True,
                                   "other_cflags": ["-DXNU_Y35A_A53=1", "-DXNU_Y35A_PHASE_A_AMFI=1"]},
                "staged_inputs": {
                    "source_tree_after_compatibility_sha256": MODULE.tree_sha256(staged_source),
                    "source_compatibility_diff": {
                        "sha256": hashlib.sha256(diff_path.read_bytes()).hexdigest(),
                        "bytes": diff_path.stat().st_size,
                    },
                },
                "steps": [
                    {"name": "installhdrs", "status": "passed", "exit_code": 0},
                    {"name": "build", "status": "passed", "exit_code": 0},
                ],
                "kernel_artifact": {
                    "sha256": hashlib.sha256(kernel.read_bytes()).hexdigest(),
                    "bytes": kernel.stat().st_size,
                },
                "driver_integration": {
                    "status": "passed", "role": "tf-storage", "force_load": True,
                    "required_symbols": ["_native_sdcard_started", "_native_sdcard_ready"],
                    "missing_symbols": [],
                },
                "inputs": {
                    "driver_archives": [{"sha256": "a" * 64}],
                    "driver_manifest": {"sha256": driver_manifest_sha},
                },
            }))
            with mock.patch.object(MODULE, "parse_macho", return_value={
                "base": 0xfffffff007004000, "entry": 0xfffffff007004100,
            }):
                result = MODULE.verify(
                    kernel, provenance, driver_manifest, staged_source,
                    nm_symbols={"_native_sdcard_started", "_native_sdcard_ready"})
            self.assertTrue(result["ok"])
            self.assertEqual(result["missing_driver_symbols"], [])

    def test_rejects_wrong_kernel_bytes_or_missing_force_loaded_symbol(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            kernel = root / "kernel.macho"
            kernel.write_bytes(b"linked kernel fixture")
            staged_source = root / "src"
            staged_source.mkdir()
            (staged_source / "kernel-source.c").write_text("source")
            diff_path = root / "inputs/staged-source-compatibility.diff"
            diff_path.parent.mkdir()
            diff_path.write_bytes(b"compat diff")
            driver_manifest = root / "driver-manifest.json"
            driver_manifest.write_text(json.dumps({"archive": {"sha256": "a" * 64}}))
            provenance = root / "build-provenance.json"
            provenance.write_text(json.dumps({
                "run_root": str(root),
                "status": "prepared",
                "source_identity": {"commit": "494ffe1c29d37ca720c37328feb83069c9641b67"},
                "build_profile": {"y35a_a53": True, "phase_a_amfi": True,
                                   "other_cflags": ["-DXNU_Y35A_A53=1", "-DXNU_Y35A_PHASE_A_AMFI=1"]},
                "staged_inputs": {
                    "source_tree_after_compatibility_sha256": MODULE.tree_sha256(staged_source),
                    "source_compatibility_diff": {
                        "sha256": hashlib.sha256(diff_path.read_bytes()).hexdigest(),
                        "bytes": diff_path.stat().st_size,
                    },
                },
                "steps": [
                    {"name": "installhdrs", "status": "passed", "exit_code": 0},
                    {"name": "build", "status": "passed", "exit_code": 0},
                ],
                "kernel_artifact": {"sha256": "0" * 64, "bytes": kernel.stat().st_size},
                "driver_integration": {
                    "status": "passed", "role": "tf-storage", "force_load": True,
                    "required_symbols": ["_native_sdcard_ready"], "missing_symbols": [],
                },
                "inputs": {
                    "driver_archives": [{"sha256": "a" * 64}],
                    "driver_manifest": {"sha256": hashlib.sha256(driver_manifest.read_bytes()).hexdigest()},
                },
            }))
            with mock.patch.object(MODULE, "parse_macho", return_value={
                "base": 0xfffffff007004000, "entry": 0xfffffff007004100,
            }):
                with self.assertRaisesRegex(ValueError, "kernel bytes do not match"):
                    MODULE.verify(kernel, provenance, driver_manifest, staged_source, nm_symbols=set())
            data = json.loads(provenance.read_text())
            data["kernel_artifact"]["sha256"] = hashlib.sha256(kernel.read_bytes()).hexdigest()
            provenance.write_text(json.dumps(data))
            with mock.patch.object(MODULE, "parse_macho", return_value={
                "base": 0xfffffff007004000, "entry": 0xfffffff007004100,
            }):
                with self.assertRaisesRegex(ValueError, "missing TF-storage symbols"):
                    MODULE.verify(kernel, provenance, driver_manifest, staged_source, nm_symbols=set())


if __name__ == "__main__":
    unittest.main()
