import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/y35a/verify_capture_layout.py"

COMMON = [
    "--pram-base", "0x859e0000",
    "--pram-size", "0x10000",
    "--stage-base", "0x859e0000",
    "--stage-size", "0x11000",
    "--panic-dest", "0x859f0000",
]


def full_manifest(**updates):
    manifest = {
        "transport_mode": "full-readback",
        "pram_preserved": False,
        "staged_bytes": 0x11000,
        "panic_log_limit": 0x1000,
        "eph_snapshot_offset": 0xF800,
        "eph_snapshot_bytes": 0x74,
        "eph_snapshot_write_bytes": 0x80,
        "stamp_snapshot_offset": 0xF900,
        "stamp_snapshot_bytes": 0x40,
        "fault_state_offset": 0xF000,
        "fault_state_bytes": 0x400,
        "records": [
            {"name": "early-fault-record", "offset": 0x40, "size": 0x180},
            {"name": "intstack", "offset": 0x4640, "size": 0x8000},
        ],
    }
    manifest.update(updates)
    return manifest


class CaptureLayoutTest(unittest.TestCase):
    def run_gate(self, manifest):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            path.write_text(json.dumps(manifest))
            return subprocess.run(
                [sys.executable, str(SCRIPT), "--manifest", str(path), *COMMON],
                capture_output=True,
                text=True,
                check=False,
            )

    def test_declared_destructive_full_readback_can_pass_physical_layout(self):
        result = self.run_gate(full_manifest())
        report = json.loads(result.stdout)
        self.assertEqual(result.returncode, 0, report)
        self.assertTrue(report["ok"])
        self.assertEqual(report["preservation"], "destructive")

    def test_full_readback_must_declare_pram_loss(self):
        result = self.run_gate(full_manifest(pram_preserved=True))
        report = json.loads(result.stdout)
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(any("pram_preserved" in f for f in report["failures"]))

    def test_snapshot_write_must_not_overlap_records(self):
        result = self.run_gate(full_manifest(
            records=[{"name": "bad", "offset": 0xF800, "size": 0x80}],
        ))
        report = json.loads(result.stdout)
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(any("snapshot" in f and "record" in f for f in report["failures"]))

    def test_snapshot_metadata_must_cover_assembly_write_extent(self):
        result = self.run_gate(full_manifest(eph_snapshot_write_bytes=0))
        report = json.loads(result.stdout)
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(any("snapshot write" in f for f in report["failures"]))

    def test_legacy_manifest_still_rejects_stage_pram_alias(self):
        result = self.run_gate({"staged_bytes": 0x11000, "records": []})
        report = json.loads(result.stdout)
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(any("overlaps pram" in f for f in report["failures"]))

    def test_minimal_boundary_uses_report_relative_records(self):
        manifest = {
            "transport_mode": "minimal-boundary",
            "pram_preserved": True,
            "staged_bytes": 0x1000,
            "records": [{"name": "phase", "offset": 0x10000 + 0x100, "report_offset": 0x100, "size": 16}],
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            path.write_text(json.dumps(manifest))
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--manifest", str(path),
                 "--pram-base", "0x859e0000", "--pram-size", "0x10000",
                 "--stage-base", "0x859f0000", "--stage-size", "0x1000",
                 "--panic-dest", "0x859f0000"],
                capture_output=True, text=True, check=False,
            )
        report = json.loads(result.stdout)
        self.assertEqual(result.returncode, 0, report)
        self.assertTrue(report["ok"])


if __name__ == "__main__":
    unittest.main()
