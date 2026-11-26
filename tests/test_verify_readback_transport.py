import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/y35a/verify_readback_transport.py"


COMMON = [
    "--pram-base", "0x859e0000",
    "--pram-size", "0x10000",
    "--lk-stage-base", "0x859e0000",
    "--lk-stage-size", "0x11000",
    "--report-base", "0x859f0000",
    "--report-size", "0x1000",
    "--snapshot-base", "0x95000000",
    "--snapshot-size", "0x10000",
    "--scratch-base", "0x90000000",
    "--scratch-size", "0x10000000",
    "--reserved", "0x90aea000:0x2900000",
]


class ReadbackTransportVerifierTest(unittest.TestCase):
    def run_verifier(self, manifest, mode):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            path.write_text(json.dumps(manifest))
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--manifest", str(path), "--mode", mode, *COMMON],
                capture_output=True,
                text=True,
                check=False,
            )
        return result.returncode, json.loads(result.stdout)

    def test_minimal_boundary_report_is_green(self):
        code, report = self.run_verifier(
            {
                "transport_mode": "minimal-boundary",
                "pram_preserved": True,
                "report_bytes": 0x108,
                "staged_bytes": 0x11000,
                "records": [{"name": "phase", "report_offset": 0x100, "size": 8}],
            },
            "minimal-boundary",
        )
        self.assertEqual(code, 0)
        self.assertTrue(report["ok"])

    def test_minimal_boundary_rejects_pram_record(self):
        code, report = self.run_verifier(
            {
                "transport_mode": "minimal-boundary",
                "pram_preserved": True,
                "report_bytes": 0x200,
                "staged_bytes": 0x11000,
                "records": [{"name": "bad", "report_offset": -0x1000, "size": 8}],
            },
            "minimal-boundary",
        )
        self.assertNotEqual(code, 0)
        self.assertTrue(any("overlaps pram" in failure for failure in report["failures"]))

    def test_minimal_boundary_rejects_records_inside_reserved_report_head(self):
        code, report = self.run_verifier(
            {
                "transport_mode": "minimal-boundary",
                "pram_preserved": True,
                "report_bytes": 0x108,
                "staged_bytes": 0x11000,
                "records": [{"name": "phase", "report_offset": 0x80, "size": 8}],
            },
            "minimal-boundary",
        )
        self.assertNotEqual(code, 0)
        self.assertTrue(any("reserved report head" in failure for failure in report["failures"]))

    def test_minimal_boundary_rejects_overlapping_record_destinations(self):
        code, report = self.run_verifier(
            {
                "transport_mode": "minimal-boundary",
                "pram_preserved": True,
                "report_bytes": 0x120,
                "staged_bytes": 0x11000,
                "records": [
                    {"name": "first", "report_offset": 0x100, "size": 16},
                    {"name": "second", "report_offset": 0x108, "size": 16},
                ],
            },
            "minimal-boundary",
        )
        self.assertNotEqual(code, 0)
        self.assertTrue(any("transport ranges overlap" in failure
                            for failure in report["failures"]))

    def test_full_readback_requires_explicit_destructive_contract(self):
        code, report = self.run_verifier(
            {
                "transport_mode": "full-readback",
                "pram_preserved": False,
                "report_bytes": 0x1000,
                "staged_bytes": 0x11000,
                "records": [{"name": "scalar", "offset": 0x40, "size": 8}],
            },
            "full-readback",
        )
        self.assertEqual(code, 0)
        self.assertTrue(report["ok"])

    def test_full_readback_rejects_false_preservation_claim(self):
        code, report = self.run_verifier(
            {
                "transport_mode": "full-readback",
                "pram_preserved": True,
                "report_bytes": 0x1000,
                "staged_bytes": 0x11000,
                "records": [{"name": "scalar", "offset": 0x40, "size": 8}],
            },
            "full-readback",
        )
        self.assertNotEqual(code, 0)
        self.assertTrue(any("pram_preserved=true" in failure for failure in report["failures"]))


if __name__ == "__main__":
    unittest.main()
