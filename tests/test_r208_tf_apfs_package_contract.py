import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "verify_r208_tf_apfs_package_contract",
    ROOT / "scripts/y35a/verify_r208_tf_apfs_package_contract.py",
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class R208TfApfsPackageContractTest(unittest.TestCase):
    def contract(self):
        return json.loads(
            (ROOT / "ci/manifests/r208-tf-apfs-package-contract.json").read_text()
        )

    def test_design_contract_is_structurally_valid_but_not_device_ready(self):
        contract = self.contract()
        self.assertEqual(MODULE.validate_contract(contract), [])
        self.assertFalse(contract["qualification"]["device_ready"])

    def test_missing_first_read_failure_is_rejected(self):
        contract = self.contract()
        contract["fallback"]["required_tf_failure_states"].remove("first_read_failed")
        failures = MODULE.validate_contract(contract)
        self.assertTrue(any("first-read failure" in failure for failure in failures))

    def test_unavailable_stock_qcdt_is_explicitly_non_ready(self):
        contract = self.contract()
        self.assertEqual(contract["device_tree"]["stock_qcdt_input"]["status"], "unavailable")
        self.assertEqual(MODULE.validate_contract(contract), [])

    def test_device_permission_cannot_be_enabled_by_contract(self):
        contract = self.contract()
        contract["qualification"]["device_run_allowed"] = True
        failures = MODULE.validate_contract(contract)
        self.assertTrue(any("device_run_allowed" in failure for failure in failures))


if __name__ == "__main__":
    unittest.main()
