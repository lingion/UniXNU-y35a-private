import importlib.util
import hashlib
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


FALLBACK_V3_SHA256 = "01c105678d3c959a868bafb774cbded77bde3e5b01b31fd4f34db845e7a5cf25"


def uuid_sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class R208TfApfsPackageContractTest(unittest.TestCase):
    def contract(self):
        return json.loads(
            (ROOT / "ci/manifests/r208-tf-apfs-package-contract.json").read_text()
        )

    def test_design_contract_is_structurally_valid_but_not_device_ready(self):
        contract = self.contract()
        self.assertEqual(MODULE.validate_contract(contract), [])
        self.assertFalse(contract["qualification"]["device_ready"])
        self.assertFalse(contract["qualification"]["runtime_qualified"])

    def test_fallback_v3_is_bound_by_path_and_sha(self):
        contract = self.contract()
        patch = contract["fallback"]["patch"]
        self.assertEqual(
            patch["path"], "patches/xnu/native-y35a-tf-emmc-root-fallback-v3.patch")
        self.assertEqual(patch["sha256"], FALLBACK_V3_SHA256)
        self.assertEqual(
            contract["native"]["manifest"],
            "ci/native-build-manifest.r208-fallback-v3.json")
        self.assertEqual(MODULE.validate_contract(contract), [])

    def test_legacy_v1_fallback_is_rejected(self):
        contract = self.contract()
        contract["fallback"]["patch"] = {
            "path": "patches/xnu/native-y35a-tf-emmc-root-fallback.patch",
            "sha256": "f886e829b94999e79af06964ee274992d975382827191912d2ab8c8a8bd291eb",
        }
        failures = MODULE.validate_contract(contract)
        self.assertTrue(any("fallback-v3 candidate patch" in f for f in failures))
        self.assertTrue(any("fallback-v3 patch SHA" in f for f in failures))

    def test_selectors_match_fallback_v3(self):
        contract = self.contract()
        root = contract["root_selection"]
        self.assertEqual(root["tf_selector"], "boot-uuid")
        self.assertEqual(root["emmc_selector"], "emmc-boot-uuid")
        self.assertEqual(MODULE.validate_contract(contract), [])

    def test_wrong_emmc_selector_is_rejected(self):
        contract = self.contract()
        contract["root_selection"]["emmc_selector"] = "boot-uuid"
        failures = MODULE.validate_contract(contract)
        self.assertTrue(any("emmc-boot-uuid" in failure for failure in failures))

    def test_tf_root_uuid_is_pending_build_output(self):
        contract = self.contract()
        slot = contract["root_selection"]["tf_root_uuid"]
        self.assertEqual(slot["status"], "build-output")
        self.assertIsNone(slot["value"])
        self.assertIsNone(slot["sha256"])
        self.assertEqual(MODULE.validate_contract(contract), [])

    def test_tf_build_output_uuid_cannot_be_fabricated_before_package_binding(self):
        contract = self.contract()
        contract["root_selection"]["tf_root_uuid"]["value"] = "943918E9-4137-3834-886B-D09BB564C585"
        failures = MODULE.validate_contract(contract)
        self.assertTrue(any("unbound build-output" in failure for failure in failures))

    def test_root_coordinator_names_real_xnu_entry_point(self):
        contract = self.contract()
        contract["root_selection"]["coordinator_symbol"] = "native_storage_select_root"
        failures = MODULE.validate_contract(contract)
        self.assertTrue(any("IOFindBSDRoot" in failure for failure in failures))

    def test_bound_uuid_slot_accepts_matching_value_and_sha(self):
        contract = self.contract()
        value = "943918E9-4137-3834-886B-D09BB564C585"
        contract["root_selection"]["tf_root_uuid"] = {
            "status": "bound",
            "value": value,
            "sha256": uuid_sha(value),
        }
        self.assertEqual(MODULE.validate_contract(contract), [])

    def test_bound_uuid_slot_requires_value_and_sha(self):
        contract = self.contract()
        contract["root_selection"]["tf_root_uuid"] = {
            "status": "bound",
            "value": None,
            "sha256": None,
        }
        failures = MODULE.validate_contract(contract)
        self.assertTrue(any("must bind both value and SHA-256" in f for f in failures))

    def test_bound_uuid_slot_rejects_sha_mismatch(self):
        contract = self.contract()
        contract["root_selection"]["tf_root_uuid"] = {
            "status": "bound",
            "value": "943918E9-4137-3834-886B-D09BB564C585",
            "sha256": uuid_sha("943918E9-4137-3834-886B-D09BB564C586"),
        }
        failures = MODULE.validate_contract(contract)
        self.assertTrue(any("SHA-256 must match its bound value" in f for f in failures))

    def test_emmc_root_uuid_must_not_be_fabricated(self):
        contract = self.contract()
        slot = contract["root_selection"]["emmc_root_uuid"]
        self.assertEqual(slot["status"], "unavailable")
        self.assertIsNone(slot["value"])
        self.assertIsNone(slot["sha256"])
        self.assertEqual(MODULE.validate_contract(contract), [])

    def test_unavailable_emmc_uuid_with_value_is_rejected(self):
        contract = self.contract()
        contract["root_selection"]["emmc_root_uuid"] = {
            "status": "unavailable",
            "value": "FABRICATED-EEMC-UUID",
            "sha256": uuid_sha("FABRICATED-EEMC-UUID"),
        }
        failures = MODULE.validate_contract(contract)
        self.assertTrue(any("must not carry a fabricated UUID" in f for f in failures))

    def test_missing_first_read_failure_is_rejected(self):
        contract = self.contract()
        contract["fallback"]["required_tf_failure_states"].remove("first_read_failed")
        failures = MODULE.validate_contract(contract)
        self.assertTrue(any("first-read failure" in failure for failure in failures))

    def test_tracked_stock_qcdt_is_explicitly_intermediate_bound(self):
        contract = self.contract()
        stock = contract["device_tree"]["stock_qcdt_input"]
        self.assertEqual(stock["status"], "available")
        self.assertEqual(stock["sha256"], "4e717950b65b1a65a3071d8935f9aa5e47e595ec6df9d80679d306a68342c010")
        boot = contract["device_tree"]["stock_qcdt_input"]["required_source_boot"]
        self.assertEqual(boot["bytes"], 67108864)
        self.assertEqual(boot["sha256"],
                         "92611f876a022fb5af1138f0591f5dafe2b359a226b2f0b28d292211f2fec012")
        self.assertEqual(boot["user_input_path"], "evidence/y35a-20261102/stock-boot.img")
        self.assertTrue(boot["qcdt_must_be_extracted_from_android_header_dt_range"])
        self.assertEqual(MODULE.validate_contract(contract), [])

    def test_tracked_stock_qcdt_rejects_intermediate_sha_mismatch(self):
        contract = self.contract()
        contract["device_tree"]["stock_qcdt_input"]["sha256"] = "0" * 64
        failures = MODULE.validate_contract(contract)
        self.assertTrue(any("available stock QCDT SHA" in failure for failure in failures))

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

    def test_runtime_qualification_cannot_be_enabled_by_contract(self):
        contract = self.contract()
        contract["qualification"]["runtime_qualified"] = True
        failures = MODULE.validate_contract(contract)
        self.assertTrue(any("runtime_qualified" in failure for failure in failures))


if __name__ == "__main__":
    unittest.main()
