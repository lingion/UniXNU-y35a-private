import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/y35a"))
SPEC = importlib.util.spec_from_file_location(
    "verify_phase_instrumentation_integrity",
    ROOT / "scripts/y35a/verify_phase_instrumentation.py",
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class ReadbackManifestIntegrityTest(unittest.TestCase):
    def manifest_fixture(self, root):
        kernel = root / "kernel.macho"
        kernel.write_bytes(b"kernel fixture for manifest binding")
        probe = root / "probe.img"
        probe.write_bytes(b"minimal probe fixture")
        manifest = {
            "kernel_sha256": hashlib.sha256(kernel.read_bytes()).hexdigest(),
            "image_sha256": hashlib.sha256(probe.read_bytes()).hexdigest(),
            "transport_mode": "minimal-boundary",
            "report_bytes": 0x2E0,
            "records": [
                {"name": "early-fault-record", "physical": "0xa0b94800",
                 "size": 384, "report_offset": 0x100},
                {"name": "handoff-witness", "physical": "0xa0b949c0",
                 "size": 16, "report_offset": 0x280},
                {"name": "fault-publish-window", "physical": "0xa0b949d0",
                 "size": 48, "report_offset": 0x290},
                {"name": "fault-pointer-window", "physical": "0xa06e60d0",
                 "size": 16, "report_offset": 0x2C0,
                 "symbol_physical": "0xa06e60d8", "symbol_offset": 8},
                {"name": "entry-path-window", "physical": "0xa0b94a00",
                 "size": 16, "report_offset": 0x2D0},
            ],
        }
        manifest_path = root / "readback.json"
        manifest_path.write_text(json.dumps(manifest))
        return kernel, manifest, manifest_path

    def test_manifest_rejects_overlapping_report_record_offsets(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            kernel, manifest, path = self.manifest_fixture(root)
            manifest["records"][3]["report_offset"] = 0x290
            path.write_text(json.dumps(manifest))
            with mock.patch.object(MODULE, "fault_pointer_symbol_physical",
                                   return_value=0xA06E60D8):
                failures = MODULE.verify_manifest(kernel, path)
            self.assertTrue(any("transport ranges overlap" in failure
                                for failure in failures), failures)

    def test_manifest_rejects_minimal_record_inside_reserved_report_head(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            kernel, manifest, path = self.manifest_fixture(root)
            manifest["records"][3]["report_offset"] = 0x50
            path.write_text(json.dumps(manifest))
            with mock.patch.object(MODULE, "fault_pointer_symbol_physical",
                                   return_value=0xA06E60D8):
                failures = MODULE.verify_manifest(kernel, path)
            self.assertTrue(any("reserved report head" in failure
                                for failure in failures), failures)

    def test_minimal_capture_header_must_match_manifest_kernel_prefix(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _kernel, manifest, manifest_path = self.manifest_fixture(root)
            raw = bytearray(0x11000)
            header = MODULE.RAW_STAGE_BASE_OFFSET + 0x40
            raw[header:header + 8] = b"Y35ARD02"
            raw[header + 8:header + 16] = bytes.fromhex(manifest["kernel_sha256"][:16])
            raw_path = root / "final.raw"
            raw_path.write_bytes(raw)
            self.assertEqual(MODULE.verify_capture_kernel_binding(raw_path, manifest_path), [])

            raw[header + 8] ^= 0x01
            raw_path.write_bytes(raw)
            failures = MODULE.verify_capture_kernel_binding(raw_path, manifest_path)
            self.assertTrue(any("kernel SHA-256 prefix" in failure for failure in failures),
                            failures)

    def test_raw_gate_enforces_minimal_capture_kernel_binding(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _kernel, manifest, manifest_path = self.manifest_fixture(root)
            raw = bytearray(0x10400)
            header = MODULE.RAW_STAGE_BASE_OFFSET + 0x40
            raw[header:header + 8] = b"Y35ARD02"
            raw[header + 8:header + 16] = b"wrongtag"
            raw_path = root / "final.raw"
            raw_path.write_bytes(raw)

            failures = MODULE.verify_raw(raw_path, manifest_path,
                                         require_capture_binding=True)
            self.assertTrue(any("kernel SHA-256 prefix" in failure for failure in failures),
                            failures)

    def test_full_capture_header_must_match_manifest_kernel_prefix(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            kernel, manifest, manifest_path = self.manifest_fixture(root)
            manifest["transport_mode"] = "full-readback"
            manifest_path.write_text(json.dumps(manifest))
            raw = bytearray(0x11000)
            raw[:8] = b"Y35ARD01"
            raw[8:16] = bytes.fromhex(hashlib.sha256(kernel.read_bytes()).hexdigest()[:16])
            raw_path = root / "final.raw"
            raw_path.write_bytes(raw)
            self.assertEqual(MODULE.verify_capture_kernel_binding(raw_path, manifest_path), [])

            raw[8] ^= 0x01
            raw_path.write_bytes(raw)
            failures = MODULE.verify_capture_kernel_binding(raw_path, manifest_path)
            self.assertTrue(any("kernel SHA-256 prefix" in failure for failure in failures),
                            failures)

    def test_probe_image_must_match_manifest_and_is_required_for_raw_gate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _kernel, manifest, manifest_path = self.manifest_fixture(root)
            probe = root / "probe.img"
            self.assertEqual(
                MODULE.verify_probe_image_binding(probe, manifest_path, required=True), []
            )
            self.assertTrue(any("requires --probe" in failure for failure in
                                MODULE.verify_probe_image_binding(None, manifest_path, required=True)))

            probe.write_bytes(b"different probe payload")
            failures = MODULE.verify_probe_image_binding(probe, manifest_path, required=True)
            self.assertTrue(any("image_sha256" in failure for failure in failures), failures)


if __name__ == "__main__":
    unittest.main()
