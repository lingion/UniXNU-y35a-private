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
        boot = contract["device_tree"]["stock_qcdt_input"]["required_source_boot"]
        self.assertEqual(boot["bytes"], 67108864)
        self.assertEqual(boot["sha256"],
                         "92611f876a022fb5af1138f0591f5dafe2b359a226b2f0b28d292211f2fec012")
        self.assertEqual(boot["user_input_path"], "evidence/y35a-20261102/stock-boot.img")
        self.assertTrue(boot["qcdt_must_be_extracted_from_android_header_dt_range"])
        self.assertEqual(MODULE.validate_contract(contract), [])

    def test_unpinned_stock_boot_source_is_rejected(self):
        contract = self.contract()
        contract["device_tree"]["stock_qcdt_input"]["required_source_boot"]["sha256"] = "0" * 64
        failures = MODULE.validate_contract(contract)
        self.assertTrue(any("historical full-partition SHA-256" in failure for failure in failures))

    def test_ios12_root_contract_does_not_assume_ios13_volume_groups(self):
        contract = self.contract()
        root_layout = contract["root_layout"]
        self.assertEqual(root_layout["target_product_version"], "12.4.1")
        self.assertFalse(root_layout["apfs_system_data_volume_group_required"])
        self.assertEqual(root_layout["version_boundary_source"],
                         "https://developer.apple.com/videos/play/wwdc2019/710/")
        self.assertEqual(root_layout["legacy_root_and_private_var_initialization"], "unverified")
        self.assertEqual(MODULE.validate_contract(contract), [])

    def test_device_permission_cannot_be_enabled_by_contract(self):
        contract = self.contract()
        contract["qualification"]["device_run_allowed"] = True
        failures = MODULE.validate_contract(contract)
        self.assertTrue(any("device_run_allowed" in failure for failure in failures))


if __name__ == "__main__":
    unittest.main()
