import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "build_y35a_tf_apfs_image",
    ROOT / "scripts/ci/build_y35a_tf_apfs_image.py",
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class TfApfsImageInputTest(unittest.TestCase):
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
                MODULE.parse_stock_qcdt(path, provenance)

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
                MODULE.parse_stock_qcdt(path, provenance)

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
                MODULE.parse_stock_qcdt(path, provenance)

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

    def test_gpt_apfs_relation_is_required(self):
        with self.assertRaisesRegex(ValueError, "GPT partition map"):
            MODULE.validate_gpt_apfs(
                {"PartitionMapType": "FDisk_partition_scheme"},
                {"Content": "Apple_APFS", "FilesystemType": "apfs"},
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


if __name__ == "__main__":
    unittest.main()
