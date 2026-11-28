import importlib.util
import json
import hashlib
import io
import os
from pathlib import Path
import subprocess
import struct
import tarfile
import tempfile
import sys
from types import SimpleNamespace
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/ci"))
SPEC = importlib.util.spec_from_file_location(
    "build_y35a_tf_apfs_image",
    ROOT / "scripts/ci/build_y35a_tf_apfs_image.py",
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)
import extract_y35a_stock_qcdt as stock_qcdt_intake
import extract_y35a_stock_qcdt as stock_qcdt_intake


class TfApfsImageInputTest(unittest.TestCase):
    def test_root_tree_artifact_binding_matches_actual_archive_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "root-tree.tar"
            archive.write_bytes(b"root tree archive")
            binding = {
                "run_id": "123", "head_sha": "a" * 40,
                "head_branch": "codex/test", "artifact_id": 456,
                "artifact_name": "y35a-root-tree-123",
                "artifact_digest": "sha256:" + "b" * 64,
                "archive_path": "root-tree.tar", "archive_bytes": archive.stat().st_size,
                "archive_sha256": MODULE.sha256(archive),
            }
            result = MODULE.validate_root_tree_artifact_binding(binding, archive)
            self.assertEqual(result["run_id"], "123")
            self.assertEqual(result["archive_sha256"], MODULE.sha256(archive))

    def test_root_tree_artifact_binding_rejects_changed_archive(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "root-tree.tar"
            archive.write_bytes(b"changed bytes")
            binding = {
                "run_id": "123", "head_sha": "a" * 40,
                "head_branch": "codex/test", "artifact_id": 456,
                "artifact_name": "y35a-root-tree-123",
                "artifact_digest": "sha256:" + "b" * 64,
                "archive_path": "root-tree.tar", "archive_bytes": len(b"old bytes"),
                "archive_sha256": hashlib.sha256(b"old bytes").hexdigest(),
            }
            with self.assertRaisesRegex(ValueError, "archive bytes do not match"):
                MODULE.validate_root_tree_artifact_binding(binding, archive)

    def test_root_tree_artifact_binding_rejects_changed_archive_same_size(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "root-tree.tar"
            archive.write_bytes(b"new bytes")
            binding = {
                "run_id": "123", "head_sha": "a" * 40,
                "head_branch": "codex/test", "artifact_id": 456,
                "artifact_name": "y35a-root-tree-123",
                "artifact_digest": "sha256:" + "b" * 64,
                "archive_path": "root-tree.tar", "archive_bytes": archive.stat().st_size,
                "archive_sha256": hashlib.sha256(b"old bytes").hexdigest(),
            }
            with self.assertRaisesRegex(ValueError, "archive bytes do not match"):
                MODULE.validate_root_tree_artifact_binding(binding, archive)

    def test_checked_command_preserves_captured_failure_output(self):
        error = subprocess.CalledProcessError(1, ["hdiutil", "create"], output="out", stderr="disk image error")
        with mock.patch.object(MODULE.subprocess, "run", side_effect=error):
            with self.assertRaisesRegex(RuntimeError, "disk image error") as raised:
                MODULE.run_checked(["hdiutil", "create"])
        self.assertIn("hdiutil", str(raised.exception))

    def test_partition_map_read_waits_for_unmount_and_detach(self):
        calls = []

        def fake_run(command, **kwargs):
            calls.append(command)
            return SimpleNamespace(stdout="SCHEME: 1 GPT, \"GPT Partition Scheme\" [16]\n")

        with mock.patch.object(MODULE, "run_checked", side_effect=fake_run):
            output = MODULE.detach_and_read_partition_map(
                Path("/tmp/image.dmg"), "/Volumes/Y35A-TF-ROOT", "/dev/disk6s1",
            )

        self.assertEqual(output, 'SCHEME: 1 GPT, "GPT Partition Scheme" [16]\n')
        self.assertEqual(calls, [
            ["diskutil", "unmount", "force", "/Volumes/Y35A-TF-ROOT"],
            ["hdiutil", "detach", "-quiet", "/dev/disk6s1"],
            ["hdiutil", "pmap", "-simple", "/tmp/image.dmg"],
        ])

    def test_hdiutil_empty_image_uses_udif_type(self):
        # hdiutil's -type selects the empty image type; UDRW is the resulting
        # read/write image and is not itself a valid -type argument.
        text = (ROOT / "scripts/ci/build_y35a_tf_apfs_image.py").read_text()
        self.assertIn('"-type", "UDIF"', text)
        self.assertNotIn('"-format", "UDRW"', text)
        self.assertNotIn('"-type", "UDRW"', text)
        self.assertIn('create_path = output.with_suffix(".dmg")', text)
        self.assertIn('os.rename(create_path, output)', text)

    def test_main_offline_control_binds_arguments_by_name(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "root-tree.tar"
            archive.write_bytes(b"archive")
            metadata = root / "root-tree.metadata.json"
            metadata.write_text("{}")
            qcdt = root / "y35a.qcdt"
            qcdt.write_bytes(b"qcdt")
            qcdt_provenance = root / "y35a.qcdt.json"
            qcdt_provenance.write_text("{}")
            package_root = root / "package"
            package_root.mkdir()
            package_provenance = package_root / "package-provenance.json"
            package_provenance.write_text("{}")
            run_json = root / "run.json"
            run_json.write_text("{}")
            package_artifact_json = root / "package-artifact.json"
            package_artifact_json.write_text("{}")
            tree_artifact_json = root / "tree-artifact.json"
            tree_artifact_json.write_text("{}")
            output = root / "image.apfs.img"
            restored_tree = root / "restored"
            restored_tree.mkdir()
            binding = {"tree_sha256": "a" * 64}

            argv = [
                "build_y35a_tf_apfs_image.py",
                "--root-tree-archive", str(archive),
                "--root-tree-metadata", str(metadata),
                "--qcdt", str(qcdt), "--qcdt-provenance", str(qcdt_provenance),
                "--output", str(output), "--offline-control-derived-qcdt",
                "--control-package-provenance", str(package_provenance),
                "--control-package-root", str(package_root),
                "--control-package-run-json", str(run_json),
                "--control-package-artifact-json", str(package_artifact_json),
                "--control-root-tree-artifact-json", str(tree_artifact_json),
                "--control-package-branch", "codex/test",
                "--control-package-run-id", "12345",
                "--control-package-artifact-name", "y35a-ramboot-12345",
                "--control-package-artifact-id", "77",
                "--control-package-artifact-digest", "sha256:" + "b" * 64,
                "--control-root-tree-artifact-id", "78",
                "--control-root-tree-artifact-digest", "sha256:" + "c" * 64,
            ]
            with mock.patch.object(sys, "argv", argv), \
                    mock.patch.object(MODULE, "extract_root_tree_archive", return_value=restored_tree), \
                    mock.patch.object(MODULE, "verify_root_tree_metadata", return_value=binding), \
                    mock.patch.object(MODULE, "validate_control_package", return_value={"qualification": "offline-control-only"}) as validate, \
                    mock.patch.object(MODULE, "build_image", return_value={"status": "intermediate-built"}) as build:
                self.assertEqual(MODULE.main(), 0)
            validate.assert_called_once()
            self.assertEqual(validate.call_args.args[0:4], (restored_tree, qcdt, qcdt_provenance, archive))
            self.assertEqual(validate.call_args.kwargs["root_tree_transport"], binding)
            build.assert_called_once()
            self.assertEqual(build.call_args.args[0:3], (restored_tree, qcdt, qcdt_provenance))
            self.assertEqual(build.call_args.kwargs["root_tree_transport"], binding)

    @staticmethod
    def derived_qcdt(path: Path, provenance_path: Path) -> None:
        payload = bytearray(b"QCDT" + (3).to_bytes(4, "little") + (1).to_bytes(4, "little") + bytes(40))
        payload[12:24] = (206).to_bytes(4, "little") + (8).to_bytes(4, "little") + (23).to_bytes(4, "little")
        payload[44:48] = (2048).to_bytes(4, "little")
        payload[48:52] = (40).to_bytes(4, "little")
        payload.extend(bytes(2048 - len(payload)))
        payload.extend(b"\xd0\x0d\xfe\xed" + bytes(36))
        path.write_bytes(payload)
        provenance_path.write_text(json.dumps({
            "schema_version": 1,
            "source_type": "derived",
            "dts_path": "board.dts",
            "dts_sha256": "a" * 64,
            "dtc_sha256": "b" * 64,
            "dtc_revision": "pinned-dtc-commit",
            "dtb_sha256": "c" * 64,
            "qcdt_path": path.name,
            "qcdt_sha256": MODULE.sha256(path),
            "qcdt_version": 3,
            "qcdt_entry": {"platform_id": 206, "variant_id": 8, "subtype_id": 23},
        }))

    def parse_stock_fixture(self, qcdt_path: Path, provenance_path: Path):
        qcdt_bytes = qcdt_path.read_bytes()
        boot_path = qcdt_path.with_name("stock-boot.img")
        boot_path.write_bytes(b"fixture placeholder; extraction helper is mocked")
        provenance = json.loads(provenance_path.read_text())
        provenance.update({
            "source_boot_path": boot_path.name,
            "source_boot_sha256": MODULE.KNOWN_PD1502A_STOCK_BOOT_SHA256,
            "source_boot_bytes": MODULE.KNOWN_PD1502A_STOCK_BOOT_BYTES,
            "source_boot_version": "PD1502A_A_1.18.0",
            "source_repository_commit": "a" * 40,
            "source_boot_path": "evidence/y35a-20261102/stock-boot.img",
            "qcdt_offset": 2048,
            "qcdt_bytes": len(qcdt_bytes),
            "sha256": hashlib.sha256(qcdt_bytes).hexdigest(),
        })
        provenance_path.write_text(json.dumps(provenance))
        extracted = {
            "boot_path": boot_path.name,
            "boot_bytes": MODULE.KNOWN_PD1502A_STOCK_BOOT_BYTES,
            "boot_sha256": MODULE.KNOWN_PD1502A_STOCK_BOOT_SHA256,
            "qcdt_offset": 2048,
            "qcdt_bytes": len(qcdt_bytes),
            "qcdt_sha256": hashlib.sha256(qcdt_bytes).hexdigest(),
            "qcdt_bytes_data": qcdt_bytes,
        }
        with mock.patch.object(MODULE, "extract_qcdt_from_pd1502a_boot_image", return_value=extracted):
            return MODULE.parse_stock_qcdt(qcdt_path, provenance_path, boot_path)

    def test_derived_qcdt_is_accepted_only_for_offline_control(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "y35a.qcdt"
            provenance = Path(directory) / "y35a.qcdt.json"
            self.derived_qcdt(path, provenance)
            parsed = MODULE.parse_qcdt(path, provenance, offline_control_derived=True)
            self.assertEqual(parsed["source_type"], "derived")
            self.assertEqual(parsed["entries"][0]["platform_id"], 206)
            with self.assertRaisesRegex(ValueError, "stock-qcdt"):
                MODULE.parse_qcdt(path, provenance)

    def test_stock_qcdt_cannot_be_labeled_as_derived_control(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "stock.qcdt"
            provenance = Path(directory) / "stock.json"
            self.derived_qcdt(path, provenance)
            value = json.loads(provenance.read_text())
            value.update({"source_type": "stock-qcdt", "board": "PD1502A",
                          "origin": "stock-boot-image", "sha256_scope": "qcdt-bytes",
                          "sha256": value["qcdt_sha256"]})
            provenance.write_text(json.dumps(value))
            with self.assertRaisesRegex(ValueError, "refuses stock"):
                MODULE.parse_qcdt(path, provenance, offline_control_derived=True)

    def test_non_qcdt_input_is_rejected_before_hdiutil(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "not-qcdt.bin"
            path.write_bytes(b"derived-dtb")
            provenance = Path(directory) / "provenance.json"
            provenance.write_text(json.dumps({
                "source_type": "stock-qcdt", "board": "PD1502A",
                "origin": "stock-boot-image", "sha256_scope": "qcdt-bytes",
                "sha256": MODULE.hashlib.sha256(path.read_bytes()).hexdigest(),
            }))
            with self.assertRaisesRegex(ValueError, "QCDT magic"):
                self.parse_stock_fixture(path, provenance)

    def test_qcdt_table_range_is_validated(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.qcdt"
            table = bytearray(
                b"QCDT" + (3).to_bytes(4, "little") + (1).to_bytes(4, "little") + bytes(40)
            )
            table[44:48] = (40).to_bytes(4, "little")
            table[48:52] = (64).to_bytes(4, "little")
            path.write_bytes(table)
            with self.assertRaisesRegex(ValueError, "overlaps header/table or exceeds file"):
                provenance = Path(directory) / "provenance.json"
                provenance.write_text(json.dumps({
                    "source_type": "stock-qcdt", "board": "PD1502A",
                    "origin": "stock-boot-image", "sha256_scope": "qcdt-bytes",
                    "sha256": MODULE.hashlib.sha256(path.read_bytes()).hexdigest(),
                }))
                self.parse_stock_fixture(path, provenance)

    def test_non_y35a_tuple_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "wrong.qcdt"
            table = bytearray(b"QCDT" + (3).to_bytes(4, "little") + (1).to_bytes(4, "little") + bytes(40) + bytes(16))
            table[12:24] = (1).to_bytes(4, "little") + (2).to_bytes(4, "little") + (3).to_bytes(4, "little")
            table[44:48] = (52).to_bytes(4, "little")
            table[48:52] = (16).to_bytes(4, "little")
            table[52:56] = b"\xd0\x0d\xfe\xed"
            path.write_bytes(table)
            provenance = Path(directory) / "provenance.json"
            provenance.write_text(json.dumps({
                "source_type": "stock-qcdt", "board": "PD1502A",
                "origin": "stock-boot-image", "sha256_scope": "qcdt-bytes",
                "sha256": MODULE.hashlib.sha256(path.read_bytes()).hexdigest(),
            }))
            with self.assertRaisesRegex(ValueError, "Y35A board tuple"):
                self.parse_stock_fixture(path, provenance)

    def _write_two_entry_qcdt(self, path: Path, *, second_offset: int, second_size: int) -> Path:
        """Create a valid two-row table with either shared or partial DTB ranges."""
        table_end = 12 + 2 * 40
        first_offset = 2048
        first_size = 64 if second_offset != first_offset else 40
        payload = bytearray(max(first_offset + first_size, second_offset + second_size))
        payload[first_offset:first_offset + 4] = b"\xd0\x0d\xfe\xed"
        payload[second_offset:second_offset + 4] = b"\xd0\x0d\xfe\xed"
        data = bytearray(b"QCDT" + (3).to_bytes(4, "little") + (2).to_bytes(4, "little"))
        rows = (
            (206, 8, 23, first_offset, first_size),
            (206, 8, 24, second_offset, second_size),
        )
        for platform, variant, subtype, offset, size in rows:
            data.extend(struct.pack("<10I", platform, variant, subtype, 0, 0, 0, 0, 0, offset, size))
        self.assertEqual(len(data), table_end)
        data.extend(bytes(first_offset - len(data)))
        data.extend(payload[first_offset:])
        path.write_bytes(data)
        provenance = path.with_suffix(".json")
        provenance.write_text(json.dumps({
            "schema_version": 1,
            "source_type": "derived",
            "dts_sha256": "a" * 64,
            "dtc_sha256": "b" * 64,
            "dtc_revision": "pinned-dtc-commit",
            "qcdt_path": path.name,
            "qcdt_sha256": hashlib.sha256(data).hexdigest(),
        }))
        return provenance

    def test_qcdt_exact_payload_alias_is_accepted_and_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "shared.qcdt"
            provenance = self._write_two_entry_qcdt(path, second_offset=2048, second_size=40)
            parsed = MODULE.parse_qcdt(path, provenance, offline_control_derived=True)
            self.assertEqual(len(parsed["entries"]), 2)
            self.assertEqual(parsed["payload_alias_groups"], [{
                "offset": 2048,
                "bytes": 40,
                "entry_indexes": [0, 1],
                "payload_sha256": hashlib.sha256(path.read_bytes()[2048:2088]).hexdigest(),
            }])

    def test_qcdt_partial_payload_overlap_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "partial.qcdt"
            provenance = self._write_two_entry_qcdt(path, second_offset=2060, second_size=40)
            with self.assertRaisesRegex(ValueError, "partially overlap: 0 and 1"):
                MODULE.parse_qcdt(path, provenance, offline_control_derived=True)

    def test_derived_qcdt_provenance_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "derived.qcdt"
            path.write_bytes(b"QCDT" + bytes(64))
            provenance = Path(directory) / "provenance.json"
            provenance.write_text(json.dumps({
                "source_type": "derived", "board": "PD1502A",
                "origin": "derived-dts", "sha256_scope": "qcdt-bytes",
                "sha256": MODULE.hashlib.sha256(path.read_bytes()).hexdigest(),
            }))
            with self.assertRaisesRegex(ValueError, "stock-qcdt"):
                MODULE.parse_stock_qcdt(path, provenance)

    def test_stock_qcdt_is_extracted_from_the_pinned_full_boot_image(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            qcdt_path = root / "stock.qcdt"
            provenance_path = root / "stock.qcdt.json"
            self.derived_qcdt(qcdt_path, provenance_path)
            qcdt_bytes = qcdt_path.read_bytes()
            page_size = 2048
            boot_path = root / "stock-boot.img"
            qcdt_offset = page_size * 2
            with boot_path.open("wb") as stream:
                stream.truncate(MODULE.KNOWN_PD1502A_STOCK_BOOT_BYTES)
                stream.write(b"ANDROID!")
                stream.seek(8)
                stream.write(struct.pack("<10I", 1, 0, 0, 0, 0, 0, 0,
                                         page_size, len(qcdt_bytes), 0))
                stream.seek(qcdt_offset)
                stream.write(qcdt_bytes)
            boot_sha = MODULE.sha256(boot_path)
            provenance = json.loads(provenance_path.read_text())
            provenance.update({
                "source_type": "stock-qcdt",
                "board": "PD1502A",
                "origin": "stock-boot-image",
                "sha256_scope": "qcdt-bytes",
                "sha256": hashlib.sha256(qcdt_bytes).hexdigest(),
                "source_boot_path": boot_path.name,
                "source_boot_sha256": boot_sha,
                "source_boot_bytes": MODULE.KNOWN_PD1502A_STOCK_BOOT_BYTES,
                "source_boot_version": "PD1502A_A_1.18.0",
                "source_repository_commit": "b" * 40,
                "source_boot_path": "evidence/y35a-20261102/stock-boot.img",
                "qcdt_offset": qcdt_offset,
                "qcdt_bytes": len(qcdt_bytes),
            })
            provenance_path.write_text(json.dumps(provenance))
            with mock.patch.object(MODULE, "KNOWN_PD1502A_STOCK_BOOT_SHA256", boot_sha):
                parsed = MODULE.parse_stock_qcdt(qcdt_path, provenance_path, boot_path)
            self.assertEqual(parsed["stock_boot_source"]["sha256"], boot_sha)
            self.assertEqual(parsed["stock_boot_source"]["qcdt_offset"], qcdt_offset)

    def test_stock_provenance_without_original_boot_image_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            qcdt_path = Path(directory) / "stock.qcdt"
            provenance_path = Path(directory) / "stock.json"
            self.derived_qcdt(qcdt_path, provenance_path)
            provenance = json.loads(provenance_path.read_text())
            provenance.update({"source_type": "stock-qcdt", "board": "PD1502A",
                               "origin": "stock-boot-image", "sha256_scope": "qcdt-bytes",
                               "sha256": provenance["qcdt_sha256"]})
            provenance_path.write_text(json.dumps(provenance))
            with self.assertRaisesRegex(ValueError, "original full stock boot image"):
                MODULE.parse_stock_qcdt(qcdt_path, provenance_path)

    def test_stock_qcdt_intake_writes_hash_bound_qcdt_and_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            boot_path = root / "stock-boot.img"
            boot_path.write_bytes(b"user-provided pinned boot source")
            output = root / "intake"
            qcdt_bytes = b"QCDT extracted bytes"
            source = {
                "boot_path": boot_path.name,
                "boot_bytes": MODULE.KNOWN_PD1502A_STOCK_BOOT_BYTES,
                "boot_sha256": MODULE.KNOWN_PD1502A_STOCK_BOOT_SHA256,
                "qcdt_offset": 4096,
                "qcdt_bytes": len(qcdt_bytes),
                "qcdt_sha256": hashlib.sha256(qcdt_bytes).hexdigest(),
                "qcdt_bytes_data": qcdt_bytes,
            }
            with mock.patch.object(stock_qcdt_intake,
                                   "extract_qcdt_from_pd1502a_boot_image", return_value=source):
                result = stock_qcdt_intake.extract(
                    boot_path, output, "c" * 40, "evidence/y35a-20261102/stock-boot.img",
                )
            self.assertEqual(result["qcdt_path"].read_bytes(), qcdt_bytes)
            provenance = json.loads(result["provenance_path"].read_text())
            self.assertEqual(provenance["source_boot_sha256"], source["boot_sha256"])
            self.assertEqual(provenance["source_boot_bytes"], source["boot_bytes"])
            self.assertEqual(provenance["source_boot_version"], "PD1502A_A_1.18.0")
            self.assertEqual(provenance["source_repository_commit"], "c" * 40)
            self.assertEqual(provenance["source_boot_path"], "evidence/y35a-20261102/stock-boot.img")
            self.assertEqual(provenance["qcdt_offset"], source["qcdt_offset"])

    def test_gpt_apfs_relation_is_required(self):
        with self.assertRaisesRegex(ValueError, "GPT partition map"):
            MODULE.validate_gpt_apfs(
                {"PartitionMapType": "GUID_partition_scheme"},
                {"Content": "Apple_APFS", "FilesystemType": "apfs"},
                "SCHEME: 1 FDisk_partition_scheme\n",
                expected_whole_disk="disk6",
            )

    def test_gpt_apfs_relation_accepts_explicit_guid_partition_scheme(self):
        result = MODULE.validate_gpt_apfs(
            {"DeviceIdentifier": "disk6"},
            {"Content": "Apple_APFS", "FilesystemType": "apfs", "DeviceIdentifier": "disk6s1",
             "ParentWholeDisk": "disk6"},
            "SCHEME: 1 GUID_partition_scheme\n",
            expected_whole_disk="disk6",
        )
        self.assertEqual(result["partition_map_source"], "hdiutil-pmap:SCHEME")

    def test_gpt_apfs_relation_accepts_explicit_gpt_scheme(self):
        result = MODULE.validate_gpt_apfs(
            {"DeviceIdentifier": "disk6"},
            {"Content": "Apple_APFS", "FilesystemType": "apfs", "DeviceIdentifier": "disk6s1",
             "ParentWholeDisk": "disk6"},
            'SCHEME: 1 GPT, "GPT Partition Scheme" [16]\n',
            expected_whole_disk="disk6",
        )
        self.assertEqual(result["partition_map_source"], "hdiutil-pmap:SCHEME")

    def test_gpt_apfs_relation_normalizes_dev_device_nodes(self):
        result = MODULE.validate_gpt_apfs(
            {"DeviceNode": "/dev/disk6"},
            {"Content": "Apple_APFS", "FilesystemType": "apfs", "DeviceNode": "/dev/disk6s1",
             "ParentWholeDiskDevice": "/dev/disk6"},
            'SCHEME: 1 GPT, "GPT Partition Scheme" [16]\n',
            expected_whole_disk="disk6",
        )
        self.assertEqual(result["whole_disk"], "disk6")
        self.assertEqual(result["volume_parent_whole_disk"], "disk6")

    def test_apfs_partition_type_guid_is_not_gpt_scheme(self):
        with self.assertRaisesRegex(ValueError, "GPT partition map"):
            MODULE.validate_gpt_apfs(
                {"Content": "EF57347C-0000-11AA-AA11-00306543ECAC"},
                {"Content": "Apple_APFS", "FilesystemType": "apfs"},
                "SECTION: 1 Type:'MAP'\n"
                " 1 EF57347C-0000-11AA-AA11-00306543ECAC 40 8380000 APFS\n",
                expected_whole_disk="disk6",
            )

    def test_gpt_apfs_relation_rejects_missing_or_mismatched_device_binding(self):
        with self.assertRaisesRegex(ValueError, "missing whole-disk"):
            MODULE.validate_gpt_apfs(
                {},
                {"Content": "Apple_APFS", "FilesystemType": "apfs"},
                'SCHEME: 1 GPT, "GPT Partition Scheme" [16]\n',
                expected_whole_disk="disk6",
            )
        with self.assertRaisesRegex(ValueError, "does not match expected"):
            MODULE.validate_gpt_apfs(
                {"DeviceIdentifier": "disk7"},
                {"Content": "Apple_APFS", "FilesystemType": "apfs", "DeviceIdentifier": "disk7s1",
                 "ParentWholeDisk": "disk7"},
                'SCHEME: 1 GPT, "GPT Partition Scheme" [16]\n',
                expected_whole_disk="disk6",
            )
        with self.assertRaisesRegex(ValueError, "parent.*does not match expected"):
            MODULE.validate_gpt_apfs(
                {"DeviceIdentifier": "disk6"},
                {"Content": "Apple_APFS", "FilesystemType": "apfs", "DeviceIdentifier": "disk7s1",
                 "ParentWholeDisk": "disk7"},
                'SCHEME: 1 GPT, "GPT Partition Scheme" [16]\n',
                expected_whole_disk="disk6",
            )

    def test_hdiutil_pmap_scheme_parser_requires_explicit_scheme_record(self):
        self.assertEqual(
            MODULE.parse_hdiutil_partition_scheme("SCHEME: 1 GUID_partition_scheme\n"),
            "GUID_partition_scheme",
        )
        self.assertEqual(
            MODULE.parse_hdiutil_partition_scheme("SECTION: 1 Apple_APFS\n"),
            "",
        )

    def test_tree_digest_changes_with_mode(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "root"
            root.mkdir()
            file = root / "launchd"
            file.write_bytes(b"launchd")
            first = MODULE.tree_sha256(root)
            file.chmod(0o755)
            second = MODULE.tree_sha256(root)
            self.assertNotEqual(first, second)

    def test_root_tree_archive_rejects_parent_traversal(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "unsafe.tar"
            with tarfile.open(archive, "w") as output:
                member = tarfile.TarInfo("root-tree/../../outside")
                member.size = 1
                import io
                output.addfile(member, io.BytesIO(b"x"))
            with self.assertRaisesRegex(ValueError, "unsafe path"):
                MODULE.validate_root_tree_archive(archive)

    def test_root_tree_archive_preserves_absolute_symlink_semantics(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "unsafe-link.tar"
            with tarfile.open(archive, "w") as output:
                root = tarfile.TarInfo("root-tree/")
                root.type = tarfile.DIRTYPE
                output.addfile(root)
                link = tarfile.TarInfo("root-tree/escape")
                link.type = tarfile.SYMTYPE
                link.linkname = "/private/var"
                output.addfile(link)
            result = MODULE.validate_root_tree_archive(archive)
            self.assertEqual(result["symlinks"], 1)
            self.assertEqual(result["root_name"], "root-tree")

    def test_root_tree_metadata_manifest_binds_archive_and_restored_tree(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tree = root / "root-tree"
            tree.mkdir()
            (tree / "launchd").write_bytes(b"launchd")
            archive = root / "root-tree.tar"
            with tarfile.open(archive, "w", format=tarfile.PAX_FORMAT) as output:
                output.add(tree, arcname="root-tree")
            manifest = {
                **MODULE.tree_metadata_manifest(tree),
                "archive_path": archive.name,
                "archive_bytes": archive.stat().st_size,
                "archive_sha256": MODULE.sha256(archive),
                "entries_sha256": hashlib.sha256(
                    json.dumps(MODULE.tree_metadata_manifest(tree)["entries"],
                               sort_keys=True, separators=(",", ":")).encode()
                ).hexdigest(),
            }
            metadata_path = root / "root-tree.metadata.json"
            metadata_path.write_text(json.dumps(manifest, sort_keys=True))
            result = MODULE.verify_root_tree_metadata(archive, metadata_path, tree)
            self.assertEqual(result["round_trip"], "passed")
            (tree / "launchd").write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "restoration differs"):
                MODULE.verify_root_tree_metadata(archive, metadata_path, tree)

    def test_root_tree_archive_rejects_duplicate_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "duplicate.tar"
            with tarfile.open(archive, "w") as output:
                root = tarfile.TarInfo("root-tree/")
                root.type = tarfile.DIRTYPE
                output.addfile(root)
                for content in (b"one", b"two"):
                    member = tarfile.TarInfo("root-tree/file")
                    member.size = len(content)
                    output.addfile(member, io.BytesIO(content))
            with self.assertRaisesRegex(ValueError, "duplicate path"):
                MODULE.validate_root_tree_archive(archive)

    def test_package_artifact_api_binding_requires_exact_run_and_digest(self):
        run = {"databaseId": 12345, "workflowName": "Y35A CI RAM-boot package",
               "conclusion": "success", "headBranch": "codex/test", "headSha": "b" * 40}
        artifact = {"id": 77, "name": "y35a-ramboot-12345", "expired": False,
                    "digest": "sha256:" + "a" * 64,
                    "workflow_run": {"id": 12345, "head_sha": "b" * 40}}
        MODULE.validate_package_artifact_api(
            run, artifact, package_run_id="12345", artifact_id=77,
            artifact_name="y35a-ramboot-12345", artifact_digest="sha256:" + "a" * 64,
            expected_branch="codex/test",
        )
        bad_artifact = dict(artifact, digest="sha256:" + "b" * 64)
        with self.assertRaisesRegex(ValueError, "metadata does not match"):
            MODULE.validate_package_artifact_api(
                run, bad_artifact, package_run_id="12345", artifact_id=77,
                artifact_name="y35a-ramboot-12345", artifact_digest="sha256:" + "a" * 64,
                expected_branch="codex/test",
            )
        with self.assertRaisesRegex(ValueError, "selected package Actions run"):
            MODULE.validate_package_artifact_api(
                dict(run, headBranch="main"), artifact, package_run_id="12345", artifact_id=77,
                artifact_name="y35a-ramboot-12345", artifact_digest="sha256:" + "a" * 64,
                expected_branch="codex/test",
            )
        with self.assertRaisesRegex(ValueError, "metadata does not match"):
            MODULE.validate_package_artifact_api(
                run, dict(artifact, expired=True), package_run_id="12345", artifact_id=77,
                artifact_name="y35a-ramboot-12345", artifact_digest="sha256:" + "a" * 64,
                expected_branch="codex/test",
            )

    def test_package_control_binding_checks_package_tree_qcdt_run_and_artifact(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tree = root / "root-tree"
            (tree / "sbin").mkdir(parents=True)
            (tree / "usr/lib").mkdir(parents=True)
            (tree / "sbin/launchd").write_bytes(b"launchd")
            (tree / "usr/lib/dyld").write_bytes(b"dyld")

            qcdt_path = root / "y35a.qcdt"
            qcdt_provenance = root / "y35a.qcdt.json"
            self.derived_qcdt(qcdt_path, qcdt_provenance)
            archive_path = root / "root-tree.tar"
            with tarfile.open(archive_path, "w", format=tarfile.PAX_FORMAT) as archive:
                archive.add(tree, arcname="root-tree")

            qcdt_bytes = qcdt_path.stat().st_size
            qcdt_provenance_bytes = qcdt_provenance.stat().st_size
            archive_bytes = archive_path.stat().st_size
            tree_digest = MODULE.tree_sha256(tree)
            metadata = {
                **MODULE.tree_metadata_manifest(tree),
                "archive_path": archive_path.name,
                "archive_bytes": archive_bytes,
                "archive_sha256": MODULE.sha256(archive_path),
                "entries_sha256": hashlib.sha256(
                    json.dumps(MODULE.tree_metadata_manifest(tree)["entries"],
                               sort_keys=True, separators=(",", ":")).encode()
                ).hexdigest(),
                "round_trip": "passed",
            }
            metadata["entries_sha256"] = hashlib.sha256(
                json.dumps(metadata["entries"], sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest()
            metadata_path = root / "root-tree.metadata.json"
            metadata_path.write_text(json.dumps(metadata, sort_keys=True))
            restored_tree_binding = MODULE.verify_root_tree_metadata(archive_path, metadata_path, tree)

            files = {
                "y35a.qcdt": {"bytes": qcdt_bytes, "sha256": MODULE.sha256(qcdt_path)},
                "y35a.qcdt.json": {"bytes": qcdt_provenance_bytes,
                                    "sha256": MODULE.sha256(qcdt_provenance)},
                "root-tree.tar": {"bytes": archive_bytes, "sha256": MODULE.sha256(archive_path)},
                "root-tree.metadata.json": {"bytes": metadata_path.stat().st_size,
                                             "sha256": MODULE.sha256(metadata_path),
                                             "entries_sha256": metadata["entries_sha256"]},
            }
            package_provenance = {
                "status": "offline-package-complete",
                "candidate_kind": "launchd-diagnostic-ramboot",
                "package_source": {"workflow_run_id": "12345", "commit": "b" * 40},
                "native_build": {"run_id": "23456", "kernel_sha256": "c" * 64},
                "qualification": {"runtime_qualified": False, "device_run_allowed": False,
                                  "springboard_included": False,
                                  "touch_runtime_validated": False, "device_boot": "not-run"},
                "device_tree": {
                    "source_type": "derived",
                    "qcdt_sha256": MODULE.sha256(qcdt_path),
                    "dts_sha256": json.loads(qcdt_provenance.read_text())["dts_sha256"],
                    "dtc_sha256": json.loads(qcdt_provenance.read_text())["dtc_sha256"],
                    "dtc_revision": json.loads(qcdt_provenance.read_text())["dtc_revision"],
                },
                "files": {
                    **files,
                    "kernel.macho": {"bytes": 1, "sha256": "c" * 64},
                },
                "rootfs": {
                    "tree_sha256": tree_digest,
                    "tree_archive": {"sha256": files["root-tree.tar"]["sha256"],
                                     "bytes": archive_bytes,
                                     "tree_sha256": tree_digest,
                                     "entries_sha256": metadata["entries_sha256"],
                                     "entries": metadata["entries"]},
                },
            }
            provenance_path = root / "package-provenance.json"
            provenance_path.write_text(json.dumps(package_provenance))
            run = {"databaseId": 12345, "workflowName": "Y35A CI RAM-boot package",
                   "conclusion": "success", "headBranch": "codex/test", "headSha": "b" * 40}
            artifact = {"id": 77, "name": "y35a-ramboot-12345", "expired": False,
                        "digest": "sha256:" + "a" * 64,
                        "workflow_run": {"id": 12345, "head_sha": "b" * 40}}
            root_artifact = {"id": 78, "name": "root-tree.tar", "expired": False,
                             "digest": "sha256:" + "e" * 64,
                             "workflow_run": {"id": 12345, "head_sha": "b" * 40}}
            result = MODULE.validate_control_package(
                tree, qcdt_path, qcdt_provenance, archive_path, provenance_path,
                restored_tree_binding,
                run, artifact, root_artifact, "12345", 77, "y35a-ramboot-12345",
                "sha256:" + "a" * 64, 78, "sha256:" + "e" * 64, "codex/test",
            )
            self.assertEqual(result["qualification"], "offline-control-only")
            self.assertEqual(result["package_source_sha"], "b" * 40)

            metadata["entries"][0]["mode"] ^= 0o111
            metadata["entries_sha256"] = hashlib.sha256(
                json.dumps(metadata["entries"], sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest()
            metadata_path.write_text(json.dumps(metadata, sort_keys=True))
            package_provenance["files"]["root-tree.metadata.json"] = {
                "bytes": metadata_path.stat().st_size,
                "sha256": MODULE.sha256(metadata_path),
                "entries_sha256": metadata["entries_sha256"],
            }
            provenance_path.write_text(json.dumps(package_provenance))
            with self.assertRaisesRegex(ValueError, "metadata manifest does not match"):
                MODULE.validate_control_package(
                    tree, qcdt_path, qcdt_provenance, archive_path, provenance_path,
                    restored_tree_binding, run, artifact, root_artifact, "12345", 77,
                    "y35a-ramboot-12345", "sha256:" + "a" * 64, 78,
                    "sha256:" + "e" * 64, "codex/test",
                )

            artifact["digest"] = "sha256:" + "d" * 64
            with self.assertRaisesRegex(ValueError, "metadata does not match"):
                MODULE.validate_control_package(
                    tree, qcdt_path, qcdt_provenance, archive_path, provenance_path,
                    restored_tree_binding,
                    run, artifact, root_artifact, "12345", 77, "y35a-ramboot-12345",
                    "sha256:" + "a" * 64, 78, "sha256:" + "e" * 64, "codex/test",
                )

    def test_tree_digest_changes_with_xattr_when_supported(self):
        if not hasattr(os, "setxattr") or not hasattr(os, "listxattr"):
            self.skipTest("Python xattrs are unsupported in this validation environment")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "root"
            root.mkdir()
            file = root / "launchd"
            file.write_bytes(b"launchd")
            try:
                first = MODULE.tree_sha256(root)
                os.setxattr(file, "user.unixnu-test", b"one", follow_symlinks=False)
                second = MODULE.tree_sha256(root)
            except (OSError, AttributeError):
                self.skipTest("filesystem does not permit xattr fixtures")
            self.assertNotEqual(first, second)

    def test_xattr_cli_fallback_when_python_api_is_missing(self):
        path = Path("/tmp/xattr-fixture")
        expected = hashlib.sha256(b"value").hexdigest()
        calls = []

        def fake_run(command, **kwargs):
            calls.append(command)
            stdout = b"com.example.test\n" if "-px" not in command else b"76 61 6c 75 65\n"
            return SimpleNamespace(stdout=stdout)

        with mock.patch.object(MODULE, "os", SimpleNamespace()), \
                mock.patch.object(MODULE.shutil, "which", return_value="/usr/bin/xattr"), \
                mock.patch.object(MODULE.subprocess, "run", side_effect=fake_run):
            result = MODULE.xattr_manifest(path)

        self.assertEqual(result, [["com.example.test", expected]])
        self.assertEqual(calls[0], ["/usr/bin/xattr", str(path)])
        self.assertEqual(calls[1], ["/usr/bin/xattr", "-px", "com.example.test", str(path)])

    def test_xattr_cli_permission_denied_retries_read_only_with_sudo(self):
        path = Path("/image/.ba")
        calls = []

        def fake_run(command, **kwargs):
            calls.append(command)
            if command[0] == "/usr/bin/xattr":
                raise subprocess.CalledProcessError(
                    1, command, output=b"", stderr=b"xattr: [Errno 13] Permission denied",
                )
            return SimpleNamespace(stdout=b"")

        with mock.patch.object(MODULE, "os", SimpleNamespace()), \
                mock.patch.object(MODULE.shutil, "which", return_value="/usr/bin/xattr"), \
                mock.patch.object(MODULE.subprocess, "run", side_effect=fake_run):
            self.assertEqual(MODULE.xattr_manifest(path), [])
        self.assertEqual(calls, [
            ["/usr/bin/xattr", str(path)],
            ["/usr/bin/sudo", "-n", "/usr/bin/xattr", str(path)],
        ])

    def test_file_content_hash_retries_only_permission_denied_with_sudo(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "protected-file"
            path.write_bytes(b"protected contents")
            expected = hashlib.sha256(b"protected contents").hexdigest()
            original_open = Path.open

            def permission_denied_open(candidate, *args, **kwargs):
                if candidate == path:
                    raise PermissionError(13, "Permission denied", str(path))
                return original_open(candidate, *args, **kwargs)

            with mock.patch.object(Path, "open", new=permission_denied_open), \
                    mock.patch.object(MODULE.sys, "platform", "darwin"), \
                    mock.patch.object(MODULE, "run_checked", return_value=SimpleNamespace(
                        stdout=f"{expected}  {path}\n",
                    )) as checked:
                digest, size = MODULE.file_content_sha256(path)
            self.assertEqual((digest, size), (expected, len(b"protected contents")))
            checked.assert_called_once_with([
                "/usr/bin/sudo", "-n", "/usr/bin/shasum", "-a", "256", str(path),
            ])

    def test_file_content_hash_does_not_retry_other_io_errors(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "io-error-file"
            path.write_bytes(b"contents")
            original_open = Path.open

            def io_error_open(candidate, *args, **kwargs):
                if candidate == path:
                    raise OSError(5, "Input/output error", str(path))
                return original_open(candidate, *args, **kwargs)

            with mock.patch.object(Path, "open", new=io_error_open), \
                    mock.patch.object(MODULE.sys, "platform", "darwin"), \
                    mock.patch.object(MODULE, "run_checked") as checked:
                with self.assertRaisesRegex(OSError, "Input/output error"):
                    MODULE.file_content_sha256(path)
            checked.assert_not_called()

    def test_file_content_hash_propagates_non_permission_io_errors(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "io-error-file"
            path.write_bytes(b"contents")
            original_open = Path.open

            def io_error_open(candidate, *args, **kwargs):
                if candidate == path:
                    raise OSError(5, "Input/output error", str(path))
                return original_open(candidate, *args, **kwargs)

            with mock.patch.object(Path, "open", new=io_error_open), \
                    mock.patch.object(MODULE.sys, "platform", "darwin"), \
                    mock.patch.object(MODULE, "run_checked") as checked:
                with self.assertRaisesRegex(OSError, "Input/output error"):
                    MODULE.file_content_sha256(path)
            checked.assert_not_called()


if __name__ == "__main__":
    unittest.main()
