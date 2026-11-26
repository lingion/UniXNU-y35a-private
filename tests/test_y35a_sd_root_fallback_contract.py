import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "verify_sd_root_fallback_contract",
    ROOT / "scripts/y35a/verify_sd_root_fallback_contract.py",
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class SdRootFallbackContractTest(unittest.TestCase):
    def test_state_matrix_selects_tf_when_ready(self):
        self.assertEqual(MODULE.select_root("ready", "ready"), "tf")

    def test_tf_initialization_or_read_failure_falls_back_to_emmc(self):
        for state in ("card_absent", "init_failed", "first_read_failed"):
            with self.subTest(state=state):
                self.assertEqual(MODULE.select_root(state, "ready"), "emmc")

    def test_both_media_fail_closed(self):
        for tf_state in ("card_absent", "init_failed", "first_read_failed"):
            with self.subTest(tf_state=tf_state):
                self.assertEqual(MODULE.select_root(tf_state, "failed"), "fail")
                self.assertEqual(MODULE.select_root(tf_state, "unavailable"), "fail")

    def test_unknown_state_is_unverified(self):
        self.assertEqual(MODULE.select_root("unknown", "ready"), "unverified")

    def test_contract_requires_ordered_fallback_scenarios(self):
        contract = json.loads((ROOT / "ci/manifests/r208-root-fallback-contract.json").read_text())
        self.assertEqual(MODULE.validate_contract(contract), [])

    def test_contract_rejects_tf_priority_after_emmc(self):
        contract = json.loads((ROOT / "ci/manifests/r208-root-fallback-contract.json").read_text())
        contract["priority"] = ["emmc", "tf"]
        failures = MODULE.validate_contract(contract)
        self.assertTrue(any("priority" in failure for failure in failures))


if __name__ == "__main__":
    unittest.main()
