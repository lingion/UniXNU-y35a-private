import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MARKER = load("verify_marker_ownership", ROOT / "scripts/y35a/verify_marker_ownership.py")


class MarkerOwnershipTests(unittest.TestCase):
    def contract(self):
        return {
            "carrier": {"base_offset": "0xba0", "bytes": "0x468"},
            "markers": [
                {"name": "MCHENTR0", "value": "0x3052544e4548434d", "offset": "0xba0", "owner": "osfmk/arm64/machine_routines.c", "position": "machine_startup entry", "ascii_le": True},
                {"name": "MCHCONF0", "value": "0x30464e4f4348434d", "offset": "0xba8", "owner": "osfmk/arm64/machine_routines.c", "position": "machine_conf return", "ascii_le": True},
                {"name": "BSDENTR0", "value": "0x3052544e45445342", "offset": "0xe00", "owner": "osfmk/kern/startup.c", "position": "bsd_init callsite", "ascii_le": True},
            ]
        }

    def write_source(self, root, body):
        path = root / "osfmk/arm64/machine_routines.c"
        path.parent.mkdir(parents=True)
        path.write_text(body)
        startup = root / "osfmk/kern/startup.c"
        startup.parent.mkdir(parents=True, exist_ok=True)
        startup.write_text("native_external_phase_marker(NULL, 0xe00, 0x3052544e45445342ULL); /* BSDENTR0 */\n")

    def run_checker(self, root, contract):
        contract_path = root / "contract.json"
        contract_path.write_text(json.dumps(contract))
        script = ROOT / "scripts/y35a/verify_marker_ownership.py"
        return subprocess.run(
            [sys.executable, str(script), "--source-root", str(root), "--contract", str(contract_path)],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_exact_markers_and_owners_pass(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.write_source(root, """
native_external_phase_marker(NULL, 0xba0, 0x3052544e4548434dULL); /* MCHENTR0 */
native_external_phase_marker(NULL, 0xba8, 0x30464e4f4348434dULL); /* MCHCONF0 */
""")
            contract = root / "contract.json"
            contract.write_text(json.dumps(self.contract()))
            hits = MARKER.source_hits(root)
            self.assertEqual(len(hits), 3)
            self.assertEqual({hit["name"] for hit in hits}, {"MCHENTR0", "MCHCONF0", "BSDENTR0"})
            result = self.run_checker(root, self.contract())
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue(json.loads(result.stdout)["ok"])

    def test_missing_expected_marker_is_not_success(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.write_source(root, "native_external_phase_marker(NULL, 0xba0, 0x3052544e4548434dULL); /* MCHENTR0 */\n")
            contract = self.contract()
            expected = {item["name"] for item in contract["markers"]}
            hits = MARKER.source_hits(root)
            self.assertNotEqual({hit["name"] for hit in hits}, expected)

    def test_duplicate_offset_is_detected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.write_source(root, """
native_external_phase_marker(NULL, 0xba0, 0x3052544e4548434dULL); /* MCHENTR0 */
native_external_phase_marker(NULL, 0xba0, 0x30464e4f4348434dULL); /* MCHCONF0 */
""")
            result = self.run_checker(root, self.contract())
            self.assertNotEqual(result.returncode, 0)
            report = json.loads(result.stdout)
            self.assertFalse(report["ok"])
            self.assertTrue(any("duplicate marker offset" in failure for failure in report["failures"]))

    def test_ascii_codeword_must_match_marker_name_when_requested(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.write_source(root, "native_external_phase_marker(NULL, 0xba0, 0x3052544e4548434dULL); /* MCHENTR0 */\n"
                                    "native_external_phase_marker(NULL, 0xba8, 0x30464e4f4348434dULL); /* MCHCONF0 */\n")
            contract = self.contract()
            contract["markers"][0]["value"] = hex(int.from_bytes(b"WRONG000", "little"))
            result = self.run_checker(root, contract)
            self.assertNotEqual(result.returncode, 0)
            report = json.loads(result.stdout)
            self.assertTrue(any("little-endian ASCII name" in item
                                for item in report["failures"]))

    def test_uncommented_writer_is_inventoried_by_codeword(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.write_source(root, """
native_external_phase_marker(NULL, 0xba0, 0x3052544e4548434dULL); /* MCHENTR0 */
native_external_phase_marker(NULL, 0xba8, 0x304f4f4630303030ULL);
""")
            hits = MARKER.source_hits(root)
            inferred = [hit for hit in hits if hit["name_source"] == "codeword"]
            self.assertEqual(len(inferred), 1)
            self.assertEqual(inferred[0]["name"], "0000FOO0")

if __name__ == "__main__":
    unittest.main()
