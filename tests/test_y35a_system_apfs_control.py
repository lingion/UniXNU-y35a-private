import importlib.util
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/ci"))
SPEC = importlib.util.spec_from_file_location(
    "build_y35a_system_apfs_control",
    ROOT / "scripts/ci/build_y35a_system_apfs_control.py",
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class SystemApfsControlBindingTest(unittest.TestCase):
    def inputs(self, root):
        image = root / "system-root.dmg"
        image.write_bytes(b"pinned system image")
        source_report = root / "system-root-source.json"
        report = {
            "schema_version": 2,
            "status": "full-system-volume-source-verified",
            "candidate_kind": "pinned-ios12-system-volume-source",
            "package_source": {"workflow_run_id": "46100598017", "commit": "a" * 40},
            "artifact_name": "y35a-ios12-system-root-46100598017",
            "firmware_identity": {
                "product_version": "12.4.1", "build": "16G102",
                "device_class": "j96ap", "product": "iPad5,1",
            },
            "system_root_image": {
                "path": image.name, "bytes": image.stat().st_size,
                "sha256": hashlib.sha256(image.read_bytes()).hexdigest(),
            },
            "system_version": {"product_version": "12.4.1", "build": "16G102"},
            "critical_system_files": {},
            "apfs_volume": {"name": "System", "uuid": "SOURCE-UUID"},
            "scope": {
                "system_volume_complete": True, "paired_data_volume_present": False,
                "device_ready": False, "device_run_allowed": False,
            },
        }
        source_report.write_text(json.dumps(report))
        sums = root / "SHA256SUMS"
        sums.write_text(
            f"{hashlib.sha256(image.read_bytes()).hexdigest()}  {image.name}\n"
            f"{hashlib.sha256(source_report.read_bytes()).hexdigest()}  {source_report.name}\n"
        )
        run = {
            "databaseId": 46100598017, "workflowName": "Y35A CI RAM-boot package",
            "conclusion": "success", "headBranch": "codex/unixnu-ci-package-v2",
            "headSha": "a" * 40,
        }
        artifact = {
            "id": 15245028918, "name": "y35a-ios12-system-root-46100598017",
            "digest": "sha256:" + "b" * 64, "expired": False,
            "workflow_run": {"id": 46100598017, "head_sha": "a" * 40},
        }
        return image, source_report, run, artifact

    def test_source_binding_requires_exact_run_artifact_and_component_hashes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            image, report, run, artifact = self.inputs(root)
            source, binding = MODULE.validate_source_binding(
                image, report, run, artifact,
                source_run_id="46100598017", artifact_id=15245028918,
                artifact_digest="sha256:" + "b" * 64,
                expected_branch="codex/unixnu-ci-package-v2",
            )
            self.assertEqual(binding["artifact_id"], 15245028918)
            self.assertEqual(source["system_root_image"]["sha256"],
                             hashlib.sha256(image.read_bytes()).hexdigest())

    def test_source_binding_rejects_wrong_artifact_identity(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            image, report, run, artifact = self.inputs(root)
            artifact["id"] += 1
            with self.assertRaisesRegex(ValueError, "artifact API record"):
                MODULE.validate_source_binding(
                    image, report, run, artifact,
                    source_run_id="46100598017", artifact_id=15245028918,
                    artifact_digest="sha256:" + "b" * 64,
                    expected_branch="codex/unixnu-ci-package-v2",
                )

    def test_source_binding_rejects_changed_source_sidecar_or_image(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            image, report, run, artifact = self.inputs(root)
            image.write_bytes(b"changed system image")
            with self.assertRaisesRegex(ValueError, "source image bytes"):
                MODULE.validate_source_binding(
                    image, report, run, artifact,
                    source_run_id="46100598017", artifact_id=15245028918,
                    artifact_digest="sha256:" + "b" * 64,
                    expected_branch="codex/unixnu-ci-package-v2",
                )

    def test_source_binding_rejects_checksum_manifest_mismatch(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            image, report, run, artifact = self.inputs(root)
            (root / "SHA256SUMS").write_text("0" * 64 + "  system-root.dmg\n")
            with self.assertRaisesRegex(ValueError, "must bind exactly"):
                MODULE.validate_source_binding(
                    image, report, run, artifact,
                    source_run_id="46100598017", artifact_id=15245028918,
                    artifact_digest="sha256:" + "b" * 64,
                    expected_branch="codex/unixnu-ci-package-v2",
                )

    def test_repository_manifest_pins_nonbootable_control_contract(self):
        manifest = json.loads((ROOT / "ci/y35a-ci-package-manifest.json").read_text())
        control = manifest["system_root_apfs_control"]
        self.assertEqual(MODULE.validate_control_contract(control), ("4g", "IOS12-SYSTEM-CONTROL"))

    def test_control_contract_rejects_bootable_or_target_qualified_claims(self):
        manifest = json.loads((ROOT / "ci/y35a-ci-package-manifest.json").read_text())
        control = manifest["system_root_apfs_control"]
        control["bootable"] = True
        with self.assertRaisesRegex(ValueError, "invalid System-root APFS control contract"):
            MODULE.validate_control_contract(control)

    def test_control_sidecar_paths_match_workflow_artifact_contract(self):
        output = Path("/runner/temp/system-root-control.dmg")
        paths = MODULE.control_output_paths(output)
        self.assertEqual(paths["report"].name, "system-root-control.dmg.json")
        self.assertEqual(paths["binding"].name, "system-root-control.dmg.json.binding.json")
        self.assertEqual(paths["tree_metadata"].name, "system-root-control.dmg.tree-metadata.json")
        self.assertEqual(paths["checksums"].name, "y35a-system-root-apfs-control.SHA256SUMS")

    def test_apfs_container_store_must_belong_to_attached_image(self):
        volume = {
            "VolumeName": "System", "DeviceIdentifier": "disk6s1",
            "ParentWholeDisk": "disk6", "VolumeUUID": "uuid-1",
        }
        listing = {"Containers": [{
            "ContainerReference": "disk6",
            "PhysicalStores": [{"DeviceIdentifier": "disk5s1"}],
            "Volumes": [{"Name": "System", "DeviceIdentifier": "disk6s1",
                         "APFSVolumeUUID": "uuid-1"}],
        }]}
        relation = MODULE.validate_apfs_store_binding("disk5", volume, listing)
        self.assertEqual(relation["attached_physical_stores"], ["disk5s1"])
        with self.assertRaisesRegex(ValueError, "not partitions of attached image"):
            MODULE.validate_apfs_store_binding(
                "disk4", volume, listing,
            )

    def test_apfs_volume_container_must_match_the_reported_parent(self):
        volume = {
            "VolumeName": "System", "DeviceIdentifier": "disk6s1",
            "ParentWholeDisk": "disk9", "VolumeUUID": "uuid-1",
        }
        listing = {"Containers": [{
            "ContainerReference": "disk6",
            "PhysicalStores": [{"DeviceIdentifier": "disk5s1"}],
            "Volumes": [{"Name": "System", "DeviceIdentifier": "disk6s1",
                         "APFSVolumeUUID": "uuid-1"}],
        }]}
        with self.assertRaisesRegex(ValueError, "parent does not match"):
            MODULE.validate_apfs_store_binding("disk5", volume, listing)

    def test_dispatch_workflow_binds_system_artifact_and_preserves_offline_scope(self):
        workflow = (ROOT / ".github/workflows/y35a-ci-package.yml").read_text()
        self.assertIn("system_root_run_id:", workflow)
        self.assertIn("system_root_artifact_id:", workflow)
        self.assertIn("system_root_artifact_digest:", workflow)
        self.assertIn("system-root-apfs-control:", workflow)
        self.assertIn("actions/download-artifact@v4", workflow)
        self.assertIn("--system-artifact-digest \"$SOURCE_ARTIFACT_DIGEST\"", workflow)
        self.assertIn("name: y35a-system-root-apfs-control-${{ github.run_id }}", workflow)
        self.assertIn('SOURCE="$RUNNER_TEMP/system-source/y35a-ios12-system-root-$SOURCE_RUN_ID"', workflow)
        self.assertIn(".qualification.bootable == false", workflow)
        self.assertIn(".qualification.device_run_allowed == false", workflow)
        self.assertIn(".qualification.stock_pd1502a_qcdt_bound == false", workflow)
        self.assertIn("y35a-system-root-apfs-control.SHA256SUMS", workflow)
        self.assertIn('(cd "$RUNNER_TEMP" && shasum -a 256 -c y35a-system-root-apfs-control.SHA256SUMS)',
                      workflow)
        self.assertIn(".entries_sha256 == .target_entries_sha256", workflow)


if __name__ == "__main__":
    unittest.main()
