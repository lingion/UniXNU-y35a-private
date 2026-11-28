"""CI contracts for the optional external TF/APFS boot bundle."""

import hashlib
import importlib.util
import inspect
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/ci"))
sys.path.insert(0, str(ROOT / "scripts/y35a"))
SPEC = importlib.util.spec_from_file_location(
    "build_y35a_tf_root_boot_package",
    ROOT / "scripts/ci/build_y35a_tf_root_boot_package.py",
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)
import package_native
import build_y35a_ci_package as package_ci


class TfRootBootPackageContractTest(unittest.TestCase):
    def api_facts(self):
        run = {
            "databaseId": 123, "workflowName": "Y35A CI RAM-boot package",
            "conclusion": "success", "headBranch": "codex/test",
            "headSha": "a" * 40,
            "jobs": [{"name": "tf-apfs-intermediate", "conclusion": "success"}],
        }
        artifact = {
            "id": 456, "name": "y35a-tf-apfs-intermediate-123",
            "digest": "sha256:" + "b" * 64, "expired": False,
            "workflow_run": {"id": 123, "head_sha": "a" * 40,
                              "head_branch": "codex/test"},
        }
        return run, artifact

    def test_tf_artifact_api_binding_requires_successful_intermediate_job(self):
        run, artifact = self.api_facts()
        result = MODULE.validate_tf_artifact_binding(
            run, artifact, run_id="123", artifact_id=456,
            artifact_digest="sha256:" + "b" * 64,
            expected_branch="codex/test", expected_sha="a" * 40,
        )
        self.assertEqual(result["artifact_id"], 456)
        self.assertEqual(result["run_id"], "123")

    def test_package_caller_does_not_forward_an_unavailable_emmc_uuid(self):
        self.assertNotIn("emmc_root_uuid", inspect.signature(MODULE.build_bundle).parameters)
        package_source = (ROOT / "scripts/ci/build_y35a_ci_package.py").read_text()
        self.assertNotIn("emmc_root_uuid=args.emmc_root_uuid", package_source)
        self.assertNotIn('parser.add_argument("--emmc-root-uuid")', package_source)

    def test_source_ram_package_binding_requires_exact_successful_artifact(self):
        run = {
            "databaseId": 900,
            "workflowName": "Y35A CI RAM-boot package",
            "conclusion": "success",
            "headBranch": "codex/test",
            "headSha": "a" * 40,
            "jobs": [{"name": "package", "conclusion": "success"}],
        }
        artifact = {
            "id": 901,
            "name": "y35a-ramboot-900",
            "digest": "sha256:" + "c" * 64,
            "expired": False,
            "workflow_run": {"id": 900, "head_sha": "a" * 40,
                              "head_branch": "codex/test"},
        }
        binding = MODULE.validate_source_ram_package_binding(
            run, artifact, run_id="900", artifact_id=901,
            artifact_digest="sha256:" + "c" * 64,
            expected_branch="codex/test", expected_sha="a" * 40,
        )
        self.assertEqual(binding["artifact_id"], 901)
        self.assertEqual(binding["run_id"], "900")
        run["jobs"][0]["conclusion"] = "skipped"
        with self.assertRaisesRegex(ValueError, "no successful package job"):
            MODULE.validate_source_ram_package_binding(
                run, artifact, run_id="900", artifact_id=901,
                artifact_digest="sha256:" + "c" * 64,
                expected_branch="codex/test", expected_sha="a" * 40,
            )

    def test_tf_artifact_api_binding_rejects_skipped_intermediate_job(self):
        run, artifact = self.api_facts()
        run["jobs"][0]["conclusion"] = "skipped"
        with self.assertRaisesRegex(ValueError, "no successful tf-apfs-intermediate"):
            MODULE.validate_tf_artifact_binding(
                run, artifact, run_id="123", artifact_id=456,
                artifact_digest="sha256:" + "b" * 64,
                expected_branch="codex/test", expected_sha="a" * 40,
            )

    def test_tf_artifact_api_binding_rejects_artifact_digest_mismatch(self):
        run, artifact = self.api_facts()
        with self.assertRaisesRegex(ValueError, "artifact API record"):
            MODULE.validate_tf_artifact_binding(
                run, artifact, run_id="123", artifact_id=456,
                artifact_digest="sha256:" + "c" * 64,
                expected_branch="codex/test", expected_sha="a" * 40,
            )

    def test_tf_artifact_api_binding_rejects_a_different_commit(self):
        run, artifact = self.api_facts()
        with self.assertRaisesRegex(ValueError, "expected successful branch/SHA"):
            MODULE.validate_tf_artifact_binding(
                run, artifact, run_id="123", artifact_id=456,
                artifact_digest="sha256:" + "b" * 64,
                expected_branch="codex/test", expected_sha="c" * 40,
            )

    def test_root_tree_artifact_binding_records_exact_archive_identity(self):
        with tempfile.TemporaryDirectory() as temporary:
            archive = Path(temporary) / "root-tree.tar"
            archive.write_bytes(b"root tree archive")
            binding = {
                "run_id": "123", "head_sha": "a" * 40,
                "artifact_id": 456, "artifact_name": "y35a-root-tree-123",
                "artifact_digest": "sha256:" + "b" * 64,
                "head_branch": "codex/test",
                "archive_path": "root-tree.tar",
                "archive_bytes": archive.stat().st_size,
                "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
            }
            result = MODULE.validate_root_tree_artifact_binding(binding, archive)
            self.assertEqual(result["archive_sha256"], hashlib.sha256(b"root tree archive").hexdigest())
            self.assertEqual(result["artifact_id"], 456)
            self.assertEqual(result["run_id"], "123")

    def test_root_tree_artifact_binding_rejects_malformed_identity(self):
        with tempfile.TemporaryDirectory() as temporary:
            archive = Path(temporary) / "root-tree.tar"
            archive.write_bytes(b"root tree archive")
            with self.assertRaisesRegex(ValueError, "incomplete or malformed"):
                MODULE.validate_root_tree_artifact_binding(
                    {"run_id": "123", "head_sha": "short"}, archive,
                )

    def test_tf_root_report_and_binding_are_hash_checked(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            image = root / "y35a-tf-root.apfs.img"
            image.write_bytes(b"GPT APFS fixture")
            root_archive = root / "root-tree.tar"
            root_archive.write_bytes(b"root tree archive")
            root_artifact_binding = {
                # An earlier package run may supply the same tree; the tree
                # hash is checked against this commit's RAM package later.
                "run_id": "123", "head_sha": "c" * 40,
                "head_branch": "codex/test", "artifact_id": 456,
                "artifact_name": "y35a-root-tree-123",
                "artifact_digest": "sha256:" + "b" * 64,
                "archive_path": "root-tree.tar",
                "archive_bytes": root_archive.stat().st_size,
                "archive_sha256": hashlib.sha256(root_archive.read_bytes()).hexdigest(),
            }
            stock_boot = root / "stock-boot.img"
            stock_boot.write_bytes(b"pinned stock boot fixture")
            report = {
                "status": "intermediate-built", "candidate_kind": "stock-qcdt-intermediate",
                "bootable": False, "device_ready": False, "device_run_allowed": False,
                "image": {"path": image.name, "bytes": image.stat().st_size,
                          "sha256": hashlib.sha256(image.read_bytes()).hexdigest()},
                "apfs": {"volume_uuid": "943918E9-4137-3834-886B-D09BB564C585",
                         "volume_name": "Y35A-TF-ROOT"},
                "device_tree_input": {
                    "source_type": "stock-qcdt",
                    "sha256": "d" * 64,
                    "bytes": 64,
                    "stock_boot_source": {
                        "sha256": "c" * 64,
                        "bytes": stock_boot.stat().st_size,
                        "qcdt_offset": 2048,
                        "qcdt_bytes": 64,
                        "source_repository_commit": "a" * 40,
                        "source_repository_path": "evidence/y35a-20261102/stock-boot.img",
                    },
                },
                "gpt_apfs": {"partition_map_type": "GPT", "filesystem_type": "apfs"},
                "card_binding": {"status": "pending", "device": None},
                "qualification": "stock-qcdt-intermediate-unqualified",
                "ios_system_image": False,
                "springboard_included": False,
                "touch_runtime_validated": False,
                "root_selection": {"status": "unverified"},
                "fallback": {"status": "unverified"},
                "root_tree_artifact": root_artifact_binding,
                "root_tree_transport": {
                    "archive_sha256": root_artifact_binding["archive_sha256"],
                    "tree_sha256": "d" * 64,
                },
                "root_tree": {"sha256": "d" * 64,
                               "scope": "diagnostic-root-until-production-root-is-bound"},
            }
            report_path = root / "y35a-tf-root.apfs.img.json"
            report_path.write_text(json.dumps(report))
            report_sha = hashlib.sha256(report_path.read_bytes()).hexdigest()
            binding_path = root / "y35a-tf-root.apfs.img.json.binding.json"
            binding_path.write_text(json.dumps({
                "schema_version": 1, "report_path": report_path.name,
                "report_sha256": report_sha,
            }))
            qcdt = {
                "boot_sha256": "c" * 64,
                "boot_bytes": stock_boot.stat().st_size,
                "qcdt_offset": 2048,
                "qcdt_bytes": 64,
                "qcdt_sha256": "d" * 64,
            }
            with mock.patch.object(MODULE, "extract_qcdt_from_pd1502a_boot_image",
                                  return_value=qcdt):
                result = MODULE.verify_tf_root_inputs(
                    image, report_path, binding_path, report,
                    json.loads(binding_path.read_text()), stock_boot,
                    root_artifact_binding, "a" * 40, "codex/test",
                )
            self.assertEqual(result["image_sha256"], report["image"]["sha256"])
            self.assertEqual(result["apfs_volume_uuid"], report["apfs"]["volume_uuid"])
            self.assertEqual(result["root_tree_scope"], "diagnostic-root-until-production-root-is-bound")
            self.assertEqual(result["root_tree_artifact"]["artifact_id"], 456)

    def test_system_control_root_image_is_not_claimed_as_tf_intermediate(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            image = root / "system-control.dmg"
            image.write_bytes(b"control")
            report_path = root / "report.json"
            report = {"status": "offline-system-root-apfs-control-built"}
            report_path.write_text(json.dumps(report))
            binding_path = root / "binding.json"
            binding_path.write_text("{}")
            stock_boot = root / "stock-boot.img"
            stock_boot.write_bytes(b"fixture")
            with self.assertRaisesRegex(ValueError, "unqualified intermediate"):
                MODULE.verify_tf_root_inputs(
                    image, report_path, binding_path, report, {}, stock_boot, {},
                    "a" * 40, "codex/test",
                )

    def test_tf_root_report_rejects_bootable_claim(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            image = root / "y35a-tf-root.apfs.img"
            image.write_bytes(b"image")
            report = {"bootable": True}
            report_path = root / "report.json"
            report_path.write_text(json.dumps(report))
            binding_path = root / "binding.json"
            binding_path.write_text("{}")
            stock_boot = root / "stock-boot.img"
            stock_boot.write_bytes(b"fixture")
            with self.assertRaisesRegex(ValueError, "unqualified intermediate"):
                MODULE.verify_tf_root_inputs(
                    image, report_path, binding_path, report, {}, stock_boot, {},
                    "a" * 40, "codex/test",
                )

    def test_tf_root_tree_must_match_the_package_trustcache_source_tree(self):
        root_binding = {
            "root_tree_sha256": "a" * 64,
            "root_tree_scope": "diagnostic-root-until-production-root-is-bound",
        }
        package = {
            "rootfs": {"tree_sha256": "b" * 64},
            "trust_cache": {"combined": {"coverage": {
                "coverage": "complete", "staged_macho_count": 58,
            }}},
        }
        with self.assertRaisesRegex(ValueError, "differs from the tree"):
            MODULE.validate_package_root_tree(root_binding, package)

    def test_empty_second_domain_container_is_only_accepted_explicitly(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            image = root / "boot3.img"
            kernel = self._synthetic_arm64_image(8192)
            qcdt = self._synthetic_qcdt()
            image.write_bytes(package_native.android_container(kernel, qcdt, second=b"", ramdisk=b"\0"))
            with self.assertRaisesRegex(ValueError, "second-domain rootfs"):
                package_ci.verify_android_container(
                    image, hashlib.sha256(qcdt).hexdigest(),
                    hashlib.sha256(kernel).hexdigest(), hashlib.sha256(b"").hexdigest(),
                )
            verified = package_ci.verify_android_container(
                image, hashlib.sha256(qcdt).hexdigest(),
                hashlib.sha256(kernel).hexdigest(), hashlib.sha256(b"").hexdigest(),
                allow_empty_second=True,
            )
            self.assertEqual(verified["second_domain_bytes"], 0)

    @staticmethod
    def _synthetic_arm64_image(size):
        data = bytearray(size)
        import struct
        struct.pack_into("<Q", data, 8, 0x80000)
        struct.pack_into("<Q", data, 16, size)
        struct.pack_into("<I", data, 56, 0x644D5241)
        return bytes(data)

    @staticmethod
    def _synthetic_qcdt():
        import struct
        page = 2048
        header = bytearray(b"QCDT" + struct.pack("<II", 3, 1) + bytes(40))
        header[12:24] = struct.pack("<III", 206, 8, 23)
        struct.pack_into("<II", header, 44, page, 40)
        header.extend(bytes(page - len(header)))
        header.extend(b"\xd0\x0d\xfe\xed" + bytes(36))
        header[44:52] = struct.pack("<II", page, 40)
        return bytes(header)

    def test_package_workflow_consumes_exact_tf_artifact_and_uploads_unqualified_bundle(self):
        workflow = (ROOT / ".github/workflows/y35a-ci-package.yml").read_text()
        inputs_block = workflow.split("  workflow_dispatch:\n    inputs:\n", 1)[1].split(
            "\n  workflow_run:", 1)[0]
        input_names = re.findall(r"^      [a-zA-Z0-9_-]+:\s*$", inputs_block, re.MULTILINE)
        self.assertLessEqual(len(input_names), 25)
        self.assertIn("Resolve exact TF/APFS intermediate artifact", workflow)
        self.assertIn('name: y35a-tf-apfs-intermediate-${{ needs.validate.outputs.tf_apfs_run_id }}', workflow)
        self.assertIn("--tf-apfs-artifact-digest", workflow)
        self.assertIn("--tf-apfs-head-sha", workflow)
        self.assertIn("--tf-bundle-output", workflow)
        self.assertNotIn("--root-kind", workflow)
        self.assertIn("Resolve exact root-tree package artifact", workflow)
        self.assertIn("EXPECTED_ROOT_TREE_ARTIFACT_DIGEST", workflow)
        self.assertIn('ROOT_TREE_DIR="$RUNNER_TEMP/root-tree/$ROOT_TREE_ARTIFACT"', workflow)
        self.assertIn(".workflow_run.head_branch == $branch", workflow)
        self.assertIn(".package_source.commit == $sha", workflow)
        self.assertIn("--root-tree-artifact-binding", workflow)
        self.assertIn("Resolve source RAM package bound to the TF root tree", workflow)
        self.assertIn("Download exact source RAM package", workflow)
        self.assertIn("--source-package-artifact-digest", workflow)
        self.assertIn("--native-artifact-digest", workflow)
        self.assertIn('"root_tree_artifact": root_tree_artifact_binding',
                      (ROOT / "scripts/ci/build_y35a_tf_apfs_image.py").read_text())
        self.assertIn('test "$STOCK_BOOT_PATH" = "evidence/y35a-20261102/stock-boot.img"', workflow)
        self.assertIn("name: y35a-tf-root-diagnostic-${{ github.run_id }}", workflow)
        self.assertIn(".qualification.bootable == false", workflow)
        self.assertIn(".fallback.status == \"unavailable-no-eMMC-APFS-root-UUID\"", workflow)


if __name__ == "__main__":
    unittest.main()
