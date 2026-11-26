from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/ci"))
sys.path.insert(0, str(ROOT / "scripts/y35a"))
import build_y35a_ci_package as package_ci
import build_y35a_qcdt as qcdt
from extract_ios12_package_inputs import validate_restore_trustcache, validate_trustcache_payload
from verify_y35a_trustcache import combine_v1, parse_v1, verify_coverage
import package_native


def synthetic_fdt(size=128):
    data = bytearray(size)
    data[:4] = b"\xd0\x0d\xfe\xed"
    struct.pack_into(">I", data, 4, size)
    return bytes(data)


def synthetic_kernel(size=8192):
    data = bytearray(size)
    struct.pack_into("<Q", data, 8, 0x80000)
    struct.pack_into("<Q", data, 16, size)
    struct.pack_into("<I", data, 56, 0x644D5241)
    return bytes(data)


class Y35aQcdtTest(unittest.TestCase):
    def test_wrap_fdt_creates_target_qcdt_v3_entry(self):
        table = qcdt.wrap_fdt(synthetic_fdt())
        magic, version, count = struct.unpack_from("<III", table, 0)
        fields = struct.unpack_from("<10I", table, 12)
        self.assertEqual((magic, version, count), (qcdt.QCDT_MAGIC, 3, 1))
        self.assertEqual(fields[:3], (206, 8, 23))
        self.assertEqual(fields[8:], (2048, 128))
        self.assertEqual(table[2048:2176], synthetic_fdt())
        self.assertEqual(len(table) % 2048, 0)

    def test_wrap_fdt_rejects_invalid_fdt(self):
        with self.assertRaises(ValueError):
            qcdt.wrap_fdt(b"not an FDT")


class Y35aContainerValidationTest(unittest.TestCase):
    def test_container_passes_static_geometry_and_qcdt_checks(self):
        table = qcdt.wrap_fdt(synthetic_fdt())
        image = package_native.android_container(
            synthetic_kernel(), table, second=b"R" * 4096, ramdisk=b"\0",
        )
        with tempfile.TemporaryDirectory() as directory:
            image_path = Path(directory) / "boot3.img"
            image_path.write_bytes(image)
            result = package_ci.verify_android_container(
                image_path,
                hashlib.sha256(table).hexdigest(),
                hashlib.sha256(synthetic_kernel()).hexdigest(),
                hashlib.sha256(b"R" * 4096).hexdigest(),
            )
        self.assertEqual(result["board_tuple"], [206, 8, 23])
        self.assertEqual(result["static_container_checks"], "passed")

    def test_hfs_ramdisk_requires_signature_and_alignment(self):
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory) / "ramdisk.raw"
            data = bytearray(8192)
            data[0x400:0x402] = b"H+"
            image.write_bytes(data)
            self.assertEqual(package_ci.verify_hfs_ramdisk(image)["volume_signature"], "H+")
            image.write_bytes(data[:-1])
            with self.assertRaisesRegex(ValueError, "4 KiB aligned"):
                package_ci.verify_hfs_ramdisk(image)

    def test_container_rejects_qcdt_hash_mismatch(self):
        table = qcdt.wrap_fdt(synthetic_fdt())
        image = package_native.android_container(
            synthetic_kernel(), table, second=b"R" * 4096, ramdisk=b"\0",
        )
        with tempfile.TemporaryDirectory() as directory:
            image_path = Path(directory) / "boot3.img"
            image_path.write_bytes(image)
            with self.assertRaisesRegex(ValueError, "QCDT SHA-256"):
                package_ci.verify_android_container(
                    image_path,
                    "0" * 64,
                    hashlib.sha256(synthetic_kernel()).hexdigest(),
                    hashlib.sha256(b"R" * 4096).hexdigest(),
                )

    def test_container_rejects_entry_payload_mismatch(self):
        table = qcdt.wrap_fdt(synthetic_fdt())
        image = bytearray(package_native.android_container(
            synthetic_kernel(), table, second=b"R" * 4096, ramdisk=b"\0",
        ))
        image[package_ci.PAGE_SIZE] ^= 0x01

        with tempfile.TemporaryDirectory() as directory:
            image_path = Path(directory) / "boot3.img"
            image_path.write_bytes(image)
            with self.assertRaisesRegex(ValueError, "kernel domain does not match"):
                package_ci.verify_android_container(
                    image_path,
                    hashlib.sha256(table).hexdigest(),
                    hashlib.sha256(synthetic_kernel()).hexdigest(),
                    hashlib.sha256(b"R" * 4096).hexdigest(),
                )

    def test_container_rejects_second_domain_payload_mismatch(self):
        table = qcdt.wrap_fdt(synthetic_fdt())
        image = bytearray(package_native.android_container(
            synthetic_kernel(), table, second=b"R" * 4096, ramdisk=b"\0",
        ))
        kernel_size = len(synthetic_kernel())
        second_offset = package_ci.PAGE_SIZE + ((kernel_size + package_ci.PAGE_SIZE - 1)
                                                // package_ci.PAGE_SIZE) * package_ci.PAGE_SIZE
        second_offset += package_ci.PAGE_SIZE
        image[second_offset] ^= 0x01

        with tempfile.TemporaryDirectory() as directory:
            image_path = Path(directory) / "boot3.img"
            image_path.write_bytes(image)
            with self.assertRaisesRegex(ValueError, "second domain does not match"):
                package_ci.verify_android_container(
                    image_path,
                    hashlib.sha256(table).hexdigest(),
                    hashlib.sha256(synthetic_kernel()).hexdigest(),
                    hashlib.sha256(b"R" * 4096).hexdigest(),
                )


class NativeArtifactBindingTest(unittest.TestCase):
    def test_native_artifact_requires_successful_matching_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            kernel = root / "kernel/mach.development.t7001.unstripped"
            kernel.parent.mkdir()
            kernel.write_bytes(b"fixture kernel")
            digest = hashlib.sha256(kernel.read_bytes()).hexdigest()
            verification = {"status": "passed"}
            provenance = {
                "status": "complete",
                "kernel_static_verification": verification,
                "kernel_artifact": {"sha256": digest, "bytes": kernel.stat().st_size},
            }
            provenance_path = root / "build-provenance.json"
            provenance_path.write_text(json.dumps(provenance))
            artifact = {
                "schema": 1,
                "status": "success",
                "run_id": 123,
                "head_sha": "a" * 40,
                "artifact_path": "kernel/mach.development.t7001.unstripped",
                "kernel_sha256": digest,
                "kernel_size": kernel.stat().st_size,
                "build_provenance_path": "build-provenance.json",
                "build_provenance_sha256": hashlib.sha256(
                    provenance_path.read_bytes(),
                ).hexdigest(),
                "kernel_static_verification": verification,
            }
            (root / "kernel-artifact.json").write_text(json.dumps(artifact))

            found, binding, _ = package_ci.validate_native_artifact(
                root, "123", "a" * 40,
            )

        self.assertEqual(found.name, "mach.development.t7001.unstripped")
        self.assertEqual(binding["kernel_sha256"], digest)

    def test_native_artifact_rejects_incomplete_build(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            kernel = root / "kernel/mach.development.t7001.unstripped"
            kernel.parent.mkdir()
            kernel.write_bytes(b"fixture kernel")
            digest = hashlib.sha256(kernel.read_bytes()).hexdigest()
            verification = {"status": "passed"}
            provenance = {
                "status": "failed",
                "kernel_static_verification": verification,
                "kernel_artifact": {"sha256": digest, "bytes": kernel.stat().st_size},
            }
            provenance_path = root / "build-provenance.json"
            provenance_path.write_text(json.dumps(provenance))
            artifact = {
                "schema": 1,
                "status": "success",
                "run_id": 123,
                "head_sha": "a" * 40,
                "artifact_path": "kernel/mach.development.t7001.unstripped",
                "kernel_sha256": digest,
                "kernel_size": kernel.stat().st_size,
                "build_provenance_path": "build-provenance.json",
                "build_provenance_sha256": hashlib.sha256(provenance_path.read_bytes()).hexdigest(),
                "kernel_static_verification": verification,
            }
            (root / "kernel-artifact.json").write_text(json.dumps(artifact))
            with self.assertRaisesRegex(ValueError, "not complete"):
                package_ci.validate_native_artifact(root, "123", "a" * 40)

    def test_native_artifact_rejects_path_escape(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifact = {
                "schema": 1,
                "status": "success",
                "run_id": 123,
                "head_sha": "a" * 40,
                "build_provenance_path": "build-provenance.json",
                "artifact_path": "../kernel",
            }
            (root / "kernel-artifact.json").write_text(json.dumps(artifact))
            (root / "build-provenance.json").write_text("{}")
            with self.assertRaisesRegex(ValueError, "stay inside"):
                package_ci.validate_native_artifact(root, "123", "a" * 40)


class RestoreTrustCacheTest(unittest.TestCase):
    def test_validates_v1_entry_count_size_and_hash(self):
        payload = struct.pack("<I", 1) + bytes(16) + struct.pack("<I", 1) + bytes(22)
        expected = {
            "payload_version": 1,
            "payload_entries": 1,
            "payload_size": len(payload),
            "payload_sha256": hashlib.sha256(payload).hexdigest(),
        }
        result = validate_restore_trustcache(payload, expected)
        self.assertEqual(result["entries"], 1)

    def test_rejects_invalid_entry_geometry(self):
        payload = struct.pack("<I", 1) + bytes(16) + struct.pack("<I", 2) + bytes(22)
        expected = {
            "payload_version": 1,
            "payload_entries": 2,
            "payload_size": len(payload),
            "payload_sha256": hashlib.sha256(payload).hexdigest(),
        }
        with self.assertRaisesRegex(ValueError, "length does not match"):
            validate_restore_trustcache(payload, expected)

    def test_static_cache_payload_uses_pinned_count_and_size(self):
        payload = struct.pack("<I", 1) + bytes(16) + struct.pack("<I", 1) + bytes(22)
        expected = {"payload_version": 1, "payload_entries": 1,
                    "payload_size": len(payload)}
        self.assertEqual(
            validate_trustcache_payload(payload, expected, "StaticTrustCache")["entries"], 1,
        )


class TrustCacheUnionTest(unittest.TestCase):
    @staticmethod
    def cache(cache_uuid, hashes):
        entries = sorted(hashes)
        payload = bytearray(struct.pack("<I16sI", 1, cache_uuid, len(entries)))
        for cdhash in entries:
            payload.extend(struct.pack("<20sBB", cdhash, 2, 0))
        return bytes(payload)

    def test_union_is_sorted_deduplicated_and_deterministic(self):
        first = bytes.fromhex("01" * 20)
        second = bytes.fromhex("02" * 20)
        restore = self.cache(bytes.fromhex("11" * 16), [first])
        static = self.cache(bytes.fromhex("22" * 16), [first, second])

        combined, report = combine_v1(restore, static)
        again, _ = combine_v1(restore, static)

        _, entries = parse_v1(combined, "combined")
        self.assertEqual(combined, again)
        self.assertEqual(set(entries), {first, second})
        self.assertEqual(report["duplicate_entries"], 1)

    def test_union_rejects_conflicting_duplicate_metadata(self):
        cdhash = bytes.fromhex("01" * 20)
        restore = self.cache(bytes.fromhex("11" * 16), [cdhash])
        static = bytearray(self.cache(bytes.fromhex("22" * 16), [cdhash]))
        static[-1] = 1

        with self.assertRaisesRegex(ValueError, "conflicting metadata"):
            combine_v1(restore, bytes(static))

    def test_coverage_requires_all_expected_staged_machos(self):
        first = bytes.fromhex("01" * 20)
        second = bytes.fromhex("02" * 20)
        report = verify_coverage({first, second}, {"bin/a": first, "sbin/b": second}, 2)
        self.assertEqual(report["coverage"], "complete")
        with self.assertRaisesRegex(ValueError, "does not cover"):
            verify_coverage({first}, {"bin/a": first, "sbin/b": second}, 2)
        with self.assertRaisesRegex(ValueError, "count mismatch"):
            verify_coverage({first}, {"bin/a": first}, 2)


class PackageSourceClosureTest(unittest.TestCase):
    def test_local_packaging_helpers_are_bound_into_provenance(self):
        self.assertIn("scripts/unixnu/ipsw.py", package_ci.PACKAGE_SOURCE_FILES)
        self.assertIn("scripts/y35a/boot_layout.py", package_ci.PACKAGE_SOURCE_FILES)
        self.assertIn("scripts/ci/verify_y35a_trustcache.py", package_ci.PACKAGE_SOURCE_FILES)
        self.assertIn("scripts/ci/prepare_native_inputs.py", package_ci.PACKAGE_SOURCE_FILES)
        self.assertIn("scripts/build-xnu-4903-native.py", package_ci.PACKAGE_SOURCE_FILES)
        self.assertIn("ci/manifests/r208-tf-sd-driver.json", package_ci.PACKAGE_SOURCE_FILES)
        self.assertIn("scripts/y35a/make_adt.py", package_ci.PACKAGE_SOURCE_FILES)


class PackageComponentClosureTest(unittest.TestCase):
    def test_package_components_require_matching_size_and_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in package_ci.REQUIRED_PACKAGE_COMPONENTS:
                (root / name).write_bytes(name.encode())
            manifest = {
                "package_components": {
                    name: {
                        "path": name,
                        "bytes": (root / name).stat().st_size,
                        "sha256": hashlib.sha256((root / name).read_bytes()).hexdigest(),
                    }
                    for name in package_ci.REQUIRED_PACKAGE_COMPONENTS
                },
            }

            verified = package_ci.verify_package_components(root, manifest)

            self.assertEqual(set(verified), set(package_ci.REQUIRED_PACKAGE_COMPONENTS))

    def test_package_component_rejects_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            name = package_ci.REQUIRED_PACKAGE_COMPONENTS[0]
            (root / name).write_bytes(b"actual")
            manifest = {
                "package_components": {
                    name: {"path": name, "bytes": 6, "sha256": "0" * 64},
                },
            }

            with self.assertRaisesRegex(ValueError, "hash or size mismatch"):
                package_ci.verify_package_components(root, manifest)


if __name__ == "__main__":
    unittest.main()
