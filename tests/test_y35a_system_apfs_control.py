import importlib.util
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


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
        self.assertEqual(control["minimum_free_fraction"], 0.10)
        self.assertEqual(control["capacity_rounding_bytes"], 1 << 30)

    def test_control_capacity_derives_rounded_size_from_source_bytes(self):
        manifest = json.loads((ROOT / "ci/y35a-ci-package-manifest.json").read_text())
        control = manifest["system_root_apfs_control"]
        gib = 1 << 30
        plan = MODULE.select_control_capacity(control, 4 * gib)
        self.assertEqual(plan["size"], "5g")
        required = plan["source_file_bytes"] + plan["apfs_metadata_reserve_bytes"]
        self.assertLessEqual(required * 100, plan["capacity_bytes"] * 90)
        self.assertEqual(plan["capacity_bytes"] % plan["rounding_bytes"], 0)

    def test_control_capacity_rounding_boundary_at_minimum_free_fraction(self):
        manifest = json.loads((ROOT / "ci/y35a-ci-package-manifest.json").read_text())
        control = manifest["system_root_apfs_control"]
        gib = 1 << 30
        exact = MODULE.select_control_capacity(control, 4 * gib)
        self.assertEqual(exact["size"], "5g")
        self.assertEqual(
            (exact["source_file_bytes"] + exact["apfs_metadata_reserve_bytes"]) * 100,
            exact["capacity_bytes"] * 90,
        )
        over = MODULE.select_control_capacity(control, 4 * gib + 1)
        self.assertEqual(over["size"], "6g")
        self.assertLessEqual(
            (over["source_file_bytes"] + over["apfs_metadata_reserve_bytes"]) * 100,
            over["capacity_bytes"] * 90,
        )

    def test_control_capacity_keeps_manifest_floor_for_small_source(self):
        manifest = json.loads((ROOT / "ci/y35a-ci-package-manifest.json").read_text())
        control = manifest["system_root_apfs_control"]
        plan = MODULE.select_control_capacity(control, 1 << 20)
        self.assertEqual(plan["size"], "4g")
        self.assertEqual(plan["capacity_bytes"], 4 << 30)

    def test_control_capacity_rejects_non_integer_free_space_margin(self):
        manifest = json.loads((ROOT / "ci/y35a-ci-package-manifest.json").read_text())
        control = dict(manifest["system_root_apfs_control"])
        control["minimum_free_fraction"] = 0.105
        with self.assertRaisesRegex(ValueError, "integer percentage"):
            MODULE.select_control_capacity(control, 4 << 30)

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

    def test_tree_manifest_diff_reports_exact_paths_and_changed_fields(self):
        source = {"tree_sha256": "a" * 64, "entries": [
            {"path": ".", "type": "directory", "mode": 0o755},
            {"path": "file", "type": "file", "content_sha256": "b" * 64, "mode": 0o644},
        ]}
        target = {"tree_sha256": "c" * 64, "entries": [
            {"path": ".", "type": "directory", "mode": 0o755},
            {"path": "file", "type": "file", "content_sha256": "b" * 64, "mode": 0o600},
            {"path": "extra", "type": "file", "content_sha256": "d" * 64},
        ]}
        report = MODULE.diff_tree_manifests(source, target)
        self.assertEqual(report["changed_entry_count"], 2)
        self.assertEqual(report["changed_field_counts"], {"mode": 1})
        self.assertEqual(report["missing_source_entry_count"], 1)
        self.assertEqual(report["missing_source_paths"], ["extra"])
        self.assertEqual(report["examples"][0]["path"], "extra")
        self.assertIn("mode", report["examples"][1]["fields"])
        self.assertEqual(report["changed_field_examples"]["mode"][0], {
            "path": "file", "source": 0o644, "target": 0o600,
        })

    def test_tree_manifest_diff_limits_example_payload(self):
        source = {"entries": []}
        target = {"entries": [
            {"path": f"p{i}", "type": "file", "content_sha256": str(i)} for i in range(70)
        ]}
        report = MODULE.diff_tree_manifests(source, target, limit=10)
        self.assertEqual(report["changed_entry_count"], 70)
        self.assertEqual(len(report["examples"]), 10)
        self.assertEqual(report["examples_truncated"], 60)
        self.assertEqual(len(report["missing_source_paths"]), 10)
        self.assertEqual(report["missing_source_paths_truncated"], 60)

    def test_control_image_attach_explicitly_enables_posix_ownership(self):
        command = MODULE.control_image_attach_command(Path("/tmp/control.dmg"))
        self.assertEqual(command, [
            "hdiutil", "attach", "-nobrowse", "-owners", "on", "-plist",
            "/tmp/control.dmg",
        ])

    def test_target_root_owner_is_restored_from_the_source_manifest(self):
        command = MODULE.target_root_chown_command(
            Path("/tmp/control-volume"),
            {"entries": [{"path": ".", "type": "directory", "uid": 0, "gid": 0}]},
        )
        self.assertEqual(command, [
            "/usr/bin/sudo", "-n", "/usr/sbin/chown", "0:0", "/tmp/control-volume",
        ])

    def test_mtime_restore_records_set_files_before_deep_directories_and_root(self):
        manifest = {"entries": [
            {"path": ".", "type": "directory", "mtime_ns": 10},
            {"path": "dir", "type": "directory", "mtime_ns": 20},
            {"path": "dir/nested", "type": "directory", "mtime_ns": 30},
            {"path": "dir/nested/file", "type": "file", "mtime_ns": 40},
        ]}
        records = MODULE.metadata_restore_records(manifest)
        self.assertEqual([row["path"] for row in records], [
            "dir/nested/file", "dir/nested", "dir", ".",
        ])
        self.assertEqual(records[-1]["mtime_ns"], 10)

    def test_mtime_restore_rejects_parent_traversal_paths(self):
        manifest = {"entries": [
            {"path": ".", "type": "directory", "mtime_ns": 10},
            {"path": "../outside", "type": "file", "mtime_ns": 20},
        ]}
        with self.assertRaisesRegex(ValueError, "unsafe relative path"):
            MODULE.metadata_restore_records(manifest)

    def test_mtime_restore_runs_privileged_script_with_source_manifest_records(self):
        manifest = {"entries": [
            {"path": ".", "type": "directory", "mtime_ns": 10},
            {"path": "file", "type": "file", "mtime_ns": 20},
        ]}
        with mock.patch.object(MODULE.subprocess, "run", return_value=mock.Mock(stdout="")) as run:
            MODULE.restore_target_directory_and_entry_mtimes(Path("/tmp/control-volume"), manifest)
        command = run.call_args.args[0]
        self.assertEqual(command[:3], ["/usr/bin/sudo", "-n", MODULE.sys.executable])
        self.assertEqual(command[3], "-c")
        self.assertIn("os.utime", command[4])
        self.assertEqual(command[-1], "/tmp/control-volume")
        self.assertTrue(run.call_args.kwargs["check"])
        records = json.loads(run.call_args.kwargs["input"])
        self.assertEqual([record["path"] for record in records], ["file", "."])

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
        self.assertIn(".target_image.configured_capacity == .image_capacity_plan.size", workflow)
        self.assertIn("Selected APFS capacity:", workflow)
        self.assertIn("Upload System-root metadata diff diagnostics", workflow)
        self.assertIn("if: failure()", workflow)


if __name__ == "__main__":
    unittest.main()
