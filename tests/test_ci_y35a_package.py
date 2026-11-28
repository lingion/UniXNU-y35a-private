from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import plistlib
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


WRITABLE_STATE_CONTRACT = {
    "paths": ["private/var", "private/var/db", "private/var/mobile"],
    "allowed_entry_types": ["missing", "directory", "symlink", "file", "other"],
    "allowed_resolution_status": [
        "missing", "resolved", "link", "not-a-directory", "symlink-loop", "escapes-volume",
    ],
}


class PackageToolchainContractTest(unittest.TestCase):
    def test_package_workflow_only_downgrades_gcc_specific_dtc_warning(self):
        workflow = (ROOT / ".github/workflows/y35a-ci-package.yml").read_text()
        self.assertIn("-Wno-error=unknown-warning-option -Wno-error=sign-compare", workflow)
        self.assertNotIn("-Wno-error ", workflow)
        self.assertIn("-Werror for all other diagnostics", workflow)
        self.assertIn("DTC_REVISION: 2d10aa2afe35527728db30b35ec491ecb6959e5c", workflow)

    def test_offline_tf_control_uses_metadata_archive_and_stays_non_device_ready(self):
        workflow = (ROOT / ".github/workflows/y35a-ci-package.yml").read_text()
        self.assertIn("root-tree.tar", workflow)
        self.assertIn("artifact-ids: ${{ inputs.control_package_artifact_id }}", workflow)
        self.assertIn("tf-apfs-offline-control:", workflow)
        self.assertIn("--offline-control-derived-qcdt", workflow)
        self.assertIn("uses: actions/upload-artifact@v7", workflow)
        self.assertIn("archive: false", workflow)
        self.assertIn("uses: actions/download-artifact@v8", workflow)
        self.assertIn("name: root-tree.tar", workflow)
        self.assertIn("control_root_tree_artifact_id", workflow)
        self.assertIn(".device_run_allowed == false", workflow)
        self.assertIn(".bootable == false", workflow)
        upload_step = workflow.split("- name: Upload metadata-preserving root-tree tar without outer ZIP", 1)[1].split("  tf-apfs-intermediate:", 1)[0]
        self.assertEqual(upload_step.count("name: root-tree.tar"), 1)

    def test_tf_production_input_requires_tracked_original_stock_boot_bytes(self):
        workflow = (ROOT / ".github/workflows/y35a-ci-package.yml").read_text()
        self.assertIn("stock_boot_path:", workflow)
        self.assertIn("evidence/y35a-20261102/stock-boot.img", workflow)
        self.assertIn("inputs.root_tree_run_id != '' && inputs.stock_boot_path != ''", workflow)
        self.assertIn("scripts/ci/extract_y35a_stock_qcdt.py", workflow)
        self.assertIn("--stock-boot-image \"$STOCK_BOOT\"", workflow)
        self.assertIn("--source-commit \"$SOURCE_COMMIT\"", workflow)
        self.assertIn("--source-boot-repo-path \"$STOCK_BOOT_PATH\"", workflow)
        self.assertIn("--stock-boot-image \"$STOCK_BOOT\" \\", workflow)
        self.assertIn('git ls-files --error-unmatch "$STOCK_BOOT_PATH"', workflow)
        self.assertIn("KNOWN_PD1502A_STOCK_BOOT_SHA256", (ROOT / "scripts/ci/build_y35a_tf_apfs_image.py").read_text())
        contract = json.loads((ROOT / "ci/manifests/r208-tf-apfs-package-contract.json").read_text())
        source_boot = contract["device_tree"]["stock_qcdt_input"]["required_source_boot"]
        self.assertEqual(source_boot["status"], "tracked-and-pinned")
        self.assertEqual(source_boot["user_input_path"], "evidence/y35a-20261102/stock-boot.img")
        self.assertEqual(source_boot["sha256"], "92611f876a022fb5af1138f0591f5dafe2b359a226b2f0b28d292211f2fec012")

    def test_full_system_volume_source_is_uploaded_as_a_separate_unqualified_artifact(self):
        workflow = (ROOT / ".github/workflows/y35a-ci-package.yml").read_text()
        package_command = workflow.split("- name: Build and verify RAM-boot package", 1)[1].split(
            "- name: Upload verified package", 1,
        )[0]
        self.assertIn('--system-root-output-dir "$RUNNER_TEMP/y35a-ios12-system-root"', package_command)
        step = workflow.split("- name: Upload pinned iOS System-volume source", 1)[1].split(
            "- name: Upload root-tree producer artifact", 1,
        )[0]
        self.assertIn("name: y35a-ios12-system-root-${{ github.run_id }}", step)
        self.assertIn("retention-days: 7", step)
        self.assertIn("compression-level: 0", step)
        self.assertIn("scope.paired_data_volume_present == false", workflow)


    def test_toolchain_manifest_binds_pinned_ndk_paths_versions_and_hashes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            ndk = root / "android-sdk/ndk/27.0.12077973"
            prebuilt = ndk / "toolchains/llvm/prebuilt/darwin-x86_64/bin"
            prebuilt.mkdir(parents=True)
            compiler = root / "xcode/clang"
            compiler.parent.mkdir()
            tools = {
                "clang": (compiler, "Apple clang test"),
                "ld.lld": (prebuilt / "ld.lld", "LLD test"),
                "llvm-objcopy": (prebuilt / "llvm-objcopy", "llvm-objcopy test"),
            }
            records = {}
            for name, (path, version) in tools.items():
                path.write_text(f"#!/bin/sh\necho '{version}'\n")
                path.chmod(0o755)
                records[name] = {
                    "path": str(path),
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    "version": version,
                }
            manifest_path = root / "toolchain.json"
            manifest_path.write_text(json.dumps({
                "android_ndk": {"revision": "27.0.12077973", "root": str(ndk),
                                "host_tag": "darwin-x86_64"},
                "tools": records,
            }))
            config = {"toolchain": {"android_ndk_revision": "27.0.12077973"}}
            result = package_ci.validate_package_toolchain(
                manifest_path, config, compiler=compiler,
                linker=tools["ld.lld"][0], objcopy=tools["llvm-objcopy"][0])
            self.assertEqual(result["android_ndk_revision"], "27.0.12077973")
            self.assertEqual(result["android_ndk_host_tag"], "darwin-x86_64")
            self.assertEqual(set(result["tools"]), {"clang", "ld.lld", "llvm-objcopy"})

    def test_ld_lld_symlink_name_is_preserved_for_version_probe(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            ndk = root / "android-sdk/ndk/27.0.12077973"
            bindir = ndk / "toolchains/llvm/prebuilt/darwin-x86_64/bin"
            bindir.mkdir(parents=True)
            compiler = root / "xcode/clang"
            compiler.parent.mkdir()
            objcopy = bindir / "llvm-objcopy"
            lld_impl = bindir / "lld"
            lld_entry = bindir / "ld.lld"
            for path, version in ((compiler, "clang-test"), (objcopy, "objcopy-test")):
                path.write_text(f"#!/bin/sh\necho '{version}'\n")
                path.chmod(0o755)
            lld_impl.write_text("#!/bin/sh\n[ \"$(basename \"$0\")\" = ld.lld ] || exit 9\necho 'LLD test'\n")
            lld_impl.chmod(0o755)
            lld_entry.symlink_to(lld_impl.name)
            tool_records = {}
            for name, path, version in (("clang", compiler, "clang-test"),
                                        ("ld.lld", lld_entry, "LLD test"),
                                        ("llvm-objcopy", objcopy, "objcopy-test")):
                tool_records[name] = {
                    "path": str(path.absolute()),
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    "version": version,
                }
            manifest = root / "toolchain.json"
            manifest.write_text(json.dumps({
                "android_ndk": {"revision": "27.0.12077973", "root": str(ndk),
                                "host_tag": "darwin-x86_64"},
                "tools": tool_records,
            }))
            result = package_ci.validate_package_toolchain(
                manifest, {"toolchain": {"android_ndk_revision": "27.0.12077973"}},
                compiler=compiler, linker=lld_entry, objcopy=objcopy)
            self.assertEqual(result["tools"]["ld.lld"]["path"], str(lld_entry.absolute()))

    def test_toolchain_manifest_rejects_pinned_ndk_revision_mismatch(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest_path = root / "toolchain.json"
            manifest_path.write_text(json.dumps({
                "android_ndk": {"revision": "wrong", "root": str(root),
                                "host_tag": "darwin-x86_64"},
                "tools": {},
            }))
            with self.assertRaisesRegex(ValueError, "revision does not match"):
                package_ci.validate_package_toolchain(
                    manifest_path, {"toolchain": {"android_ndk_revision": "27.0.12077973"}},
                    compiler=root / "clang", linker=root / "ld.lld", objcopy=root / "llvm-objcopy")



class FullSystemRootSourceTest(unittest.TestCase):
    def make_inputs(self, root):
        image = root / "system.dmg"
        image.write_bytes(b"pinned system volume bytes")
        source_root = root / "mounted-system"
        (source_root / "sbin").mkdir(parents=True)
        (source_root / "usr/lib").mkdir(parents=True)
        springboard = source_root / "System/Library/CoreServices/SpringBoard.app/SpringBoard"
        springboard.parent.mkdir(parents=True)
        (source_root / "sbin/launchd").write_bytes(b"launchd")
        (source_root / "usr/lib/dyld").write_bytes(b"dyld")
        springboard.write_bytes(b"SpringBoard")
        version_path = source_root / "System/Library/CoreServices/SystemVersion.plist"
        version_path.parent.mkdir(parents=True, exist_ok=True)
        version_path.write_bytes(plistlib.dumps({
            "ProductVersion": "12.4.1", "ProductBuildVersion": "16G102",
        }))
        firmware = {
            "ipsw": {"size": 3053369741, "sha256": "a" * 64},
            "identity": {
                "device_class": "j96ap", "product_version": "12.4.1",
                "build": "16G102", "product": "iPad5,1",
            },
            "components": {"OS": {
                "member": "048-78033-095.dmg", "size": image.stat().st_size,
                "sha256": hashlib.sha256(image.read_bytes()).hexdigest(),
            }},
        }
        volume = {
            "DeviceIdentifier": "disk5s1", "ParentWholeDisk": "disk5",
            "Content": "Apple_APFS", "FilesystemType": "apfs",
            "VolumeUUID": "A1B2C3D4-E5F6-4711-8111-123456789ABC",
            "VolumeName": package_ci.FIRMWARE_VOLUME,
        }
        whole = {"DeviceIdentifier": "disk5", "Content": "GUID_partition_scheme"}
        return image, source_root, firmware, whole, volume

    def test_full_system_source_artifact_preserves_exact_image_and_stays_unqualified(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            image, system_root, firmware, whole, volume = self.make_inputs(root)
            output = root / "full-system-artifact"
            version, critical, writable_state_paths = package_ci.inspect_full_system_volume(
                system_root, firmware["identity"],
            )
            report = package_ci.build_full_system_root_source(
                image, firmware, version, critical, writable_state_paths, whole, volume,
                'SCHEME: 1 GPT, "GPT Partition Scheme" [16]\n', output,
                WRITABLE_STATE_CONTRACT,
                native_binding={"run_id": "native-1", "head_sha": "b" * 40,
                                "kernel_sha256": "c" * 64},
                package_source_sha="d" * 40, package_run_id="package-1",
            )
            copied = output / "system-root.dmg"
            self.assertEqual(copied.read_bytes(), image.read_bytes())
            self.assertEqual(report["system_root_image"]["sha256"],
                             hashlib.sha256(image.read_bytes()).hexdigest())
            self.assertEqual(report["schema_version"], 2)
            self.assertEqual(report["source_component"]["member"], "048-78033-095.dmg")
            self.assertIn("System/Library/CoreServices/SpringBoard.app/SpringBoard",
                          report["critical_system_files"])
            self.assertEqual(
                report["writable_state_path_observation"],
                "path metadata only; does not establish writability or a mounted Data volume",
            )
            self.assertEqual(
                set(report["writable_state_paths"]),
                {"private/var", "private/var/db", "private/var/mobile"},
            )
            self.assertTrue(all(
                item == {
                    "present": False,
                    "entry_type": "missing",
                    "symlink_target": None,
                    "symlink_chain": [],
                    "resolved_target_exists": False,
                    "resolved_target_is_directory": False,
                    "resolution_status": "missing",
                }
                for item in report["writable_state_paths"].values()
            ))
            self.assertFalse(report["scope"]["paired_data_volume_present"])
            self.assertFalse(report["qualification"]["device_ready"])
            self.assertFalse(report["qualification"]["runtime_qualified"])
            self.assertFalse(report["qualification"]["device_run_allowed"])
            self.assertTrue((output / "SHA256SUMS").is_file())

    def test_full_system_source_reports_writable_state_path_presence(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            image, system_root, firmware, whole, volume = self.make_inputs(root)
            (system_root / "private/var/db").mkdir(parents=True)
            (system_root / "private/var/mobile").mkdir(parents=True)
            version, critical, writable_state_paths = package_ci.inspect_full_system_volume(
                system_root, firmware["identity"],
            )
            self.assertEqual(writable_state_paths, {
                "private/var": {
                    "present": True, "entry_type": "directory", "symlink_target": None,
                    "symlink_chain": [],
                    "resolved_target_exists": True, "resolved_target_is_directory": True,
                    "resolution_status": "resolved",
                },
                "private/var/db": {
                    "present": True, "entry_type": "directory", "symlink_target": None,
                    "symlink_chain": [],
                    "resolved_target_exists": True, "resolved_target_is_directory": True,
                    "resolution_status": "resolved",
                },
                "private/var/mobile": {
                    "present": True, "entry_type": "directory", "symlink_target": None,
                    "symlink_chain": [],
                    "resolved_target_exists": True, "resolved_target_is_directory": True,
                    "resolution_status": "resolved",
                },
            })

    def test_full_system_source_reports_symlinked_var_target(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, system_root, firmware, _, _ = self.make_inputs(root)
            (system_root / "var/db").mkdir(parents=True)
            (system_root / "var/mobile").mkdir(parents=True)
            (system_root / "private").mkdir()
            (system_root / "private/var").symlink_to("../var")
            _, _, writable_state_paths = package_ci.inspect_full_system_volume(
                system_root, firmware["identity"],
            )
            self.assertEqual(writable_state_paths["private/var"]["entry_type"], "symlink")
            self.assertEqual(writable_state_paths["private/var"]["symlink_target"], "../var")
            self.assertTrue(writable_state_paths["private/var"]["resolved_target_is_directory"])
            self.assertTrue(writable_state_paths["private/var/db"]["resolved_target_is_directory"])

    def test_full_system_source_resolves_absolute_symlink_inside_image_root(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, system_root, firmware, _, _ = self.make_inputs(root)
            (system_root / "private").mkdir()
            (system_root / "private/var").symlink_to("/var")
            _, _, writable_state_paths = package_ci.inspect_full_system_volume(
                system_root, firmware["identity"],
            )
            var = writable_state_paths["private/var"]
            self.assertEqual(var["entry_type"], "symlink")
            self.assertEqual(var["symlink_target"], "/var")
            self.assertEqual(var["resolution_status"], "missing")
            self.assertEqual(var["symlink_chain"], [{"path": "private/var", "target": "/var"}])
            self.assertFalse(var["resolved_target_exists"])
            self.assertEqual(writable_state_paths["private/var/db"]["resolution_status"], "missing")

            (system_root / "var/db").mkdir(parents=True)
            (system_root / "var/mobile").mkdir(parents=True)
            _, _, writable_state_paths = package_ci.inspect_full_system_volume(
                system_root, firmware["identity"],
            )
            var = writable_state_paths["private/var"]
            self.assertEqual(var["resolution_status"], "resolved")
            self.assertTrue(var["resolved_target_is_directory"])
            self.assertEqual(writable_state_paths["private/var/db"]["symlink_chain"],
                             [{"path": "private/var", "target": "/var"}])

    def test_full_system_source_marks_dangling_image_symlink(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, system_root, firmware, _, _ = self.make_inputs(root)
            (system_root / "private").mkdir()
            (system_root / "private/var").symlink_to("/missing-data-volume")
            _, _, writable_state_paths = package_ci.inspect_full_system_volume(
                system_root, firmware["identity"],
            )
            var = writable_state_paths["private/var"]
            self.assertTrue(var["present"])
            self.assertEqual(var["entry_type"], "symlink")
            self.assertFalse(var["resolved_target_exists"])
            self.assertEqual(var["resolution_status"], "missing")

    def test_workflow_rejects_missing_writable_state_path_inventory(self):
        workflow = (ROOT / ".github/workflows/y35a-ci-package.yml").read_text()
        verification = workflow.split(
            "- name: Verify complete iOS System-volume source handoff", 1,
        )[1].split("- name: Upload pinned iOS System-volume source", 1)[0]
        self.assertIn('(.writable_state_paths | keys == ["private/var", "private/var/db", "private/var/mobile"])',
                      verification)
        self.assertIn('.entry_type == "missing" or .entry_type == "directory" or .entry_type == "symlink" or .entry_type == "file" or .entry_type == "other"',
                      verification)
        self.assertIn('(.resolved_target_exists | type) == "boolean"', verification)
        self.assertIn('.resolution_status == "symlink-loop" or .resolution_status == "escapes-volume"',
                      verification)
        self.assertIn('((.entry_type == "symlink") == ((.symlink_target | type) == "string"))', verification)
        self.assertIn('.present == (.entry_type != "missing")', verification)
        self.assertIn('.resolved_target_is_directory == false or .resolved_target_exists == true', verification)
        self.assertIn('.schema_version == 2', verification)
        self.assertIn("does not establish writability or a mounted Data volume", verification)

    def test_package_manifest_declares_writable_state_observation_contract(self):
        manifest = json.loads((ROOT / "ci/y35a-ci-package-manifest.json").read_text())
        system = manifest["system_root_source"]
        self.assertEqual(system["writable_state_path_observation"],
                         "path metadata only; does not establish writability or a mounted Data volume")
        self.assertEqual(system["writable_state_paths"], WRITABLE_STATE_CONTRACT)

    def test_full_system_source_rejects_component_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            image, system_root, firmware, whole, volume = self.make_inputs(root)
            firmware["components"]["OS"]["sha256"] = "0" * 64
            with self.assertRaisesRegex(ValueError, "does not match the pinned IPSW component size/hash"):
                version, critical, writable_state_paths = package_ci.inspect_full_system_volume(
                    system_root, firmware["identity"],
                )
                package_ci.build_full_system_root_source(
                    image, firmware, version, critical, writable_state_paths, whole, volume,
                    'SCHEME: 1 GPT, "GPT Partition Scheme" [16]\n', root / "artifact",
                    WRITABLE_STATE_CONTRACT,
                    native_binding={"run_id": "native-1", "head_sha": "b" * 40,
                                    "kernel_sha256": "c" * 64},
                    package_source_sha="d" * 40, package_run_id="package-1",
                )

    def test_writable_state_inventory_rejects_unknown_and_inconsistent_entries(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, system_root, firmware, _, _ = self.make_inputs(root)
            _, _, inventory = package_ci.inspect_full_system_volume(system_root, firmware["identity"])
            invalid_type = json.loads(json.dumps(inventory))
            invalid_type["private/var"]["entry_type"] = "bogus"
            with self.assertRaisesRegex(ValueError, "invalid writable-state observation"):
                package_ci.validate_writable_state_inventory(invalid_type, WRITABLE_STATE_CONTRACT)

            inconsistent = json.loads(json.dumps(inventory))
            inconsistent["private/var"]["present"] = True
            with self.assertRaisesRegex(ValueError, "presence disagrees"):
                package_ci.validate_writable_state_inventory(inconsistent, WRITABLE_STATE_CONTRACT)

            unexpected_link = json.loads(json.dumps(inventory))
            unexpected_link["private/var"]["symlink_target"] = "/var"
            with self.assertRaisesRegex(ValueError, "non-symlink writable-state path has a link target"):
                package_ci.validate_writable_state_inventory(unexpected_link, WRITABLE_STATE_CONTRACT)

            missing_parent = json.loads(json.dumps(inventory))
            missing_parent["private/var"]["present"] = True
            with self.assertRaisesRegex(ValueError, "presence disagrees"):
                package_ci.validate_writable_state_inventory(missing_parent, WRITABLE_STATE_CONTRACT)

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
    @staticmethod
    def write_native_evidence(root, kernel, *, provenance_status="complete"):
        manifest_path = root / "native-build-manifest.json"
        source_provenance_path = root / "source-provenance.json"
        source_provenance_path.write_text("pinned source contract\n")
        patch_hash = hashlib.sha256(b"pinned patch").hexdigest()
        driver_hash = hashlib.sha256(b"pinned driver archive").hexdigest()
        native_manifest = {
            "source_ref": "xnu-commit",
            "source_provenance": str(source_provenance_path),
            "driver_artifact": {"archive": "libQcomSdcard.a", "sha256": driver_hash},
            "patches": [{"order": 0, "path": "patches/native.patch", "sha256": patch_hash}],
        }
        manifest_path.write_text(json.dumps(native_manifest))
        plan_path = root / "native-build-plan.json"
        plan_path.write_text(json.dumps({
            "ok": True,
            "manifest": "native-build-manifest.json",
            "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
            "plan_only": True,
        }))
        digest = hashlib.sha256(kernel.read_bytes()).hexdigest()
        verification = {"status": "passed"}
        provenance = {
            "status": provenance_status,
            "source_identity": {"commit": "xnu-commit"},
            "inputs": {
                "source_diff": [{"path": "/runner/patches/native.patch", "sha256": patch_hash}],
                "source_provenance": {"sha256": hashlib.sha256(
                    source_provenance_path.read_bytes(),
                ).hexdigest()},
                "driver_archives": [{"path": "/runner/libQcomSdcard.a", "sha256": driver_hash}],
            },
            "driver_integration": {"status": "passed"},
            "kernel_static_verification": verification,
            "kernel_artifact": {"sha256": digest, "bytes": kernel.stat().st_size},
        }
        provenance_path = root / "build-provenance.json"
        provenance_path.write_text(json.dumps(provenance))
        artifact = {
            "schema": 2,
            "status": "success",
            "run_id": 123,
            "head_sha": "a" * 40,
            "artifact_path": "kernel/mach.development.t7001.unstripped",
            "kernel_sha256": digest,
            "kernel_size": kernel.stat().st_size,
            "build_provenance_path": provenance_path.name,
            "build_provenance_sha256": hashlib.sha256(provenance_path.read_bytes()).hexdigest(),
            "native_build_plan_path": plan_path.name,
            "native_build_plan_sha256": hashlib.sha256(plan_path.read_bytes()).hexdigest(),
            "kernel_static_verification": verification,
        }
        (root / "kernel-artifact.json").write_text(json.dumps(artifact))
        return manifest_path

    def test_native_artifact_requires_successful_matching_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            kernel = root / "kernel/mach.development.t7001.unstripped"
            kernel.parent.mkdir()
            kernel.write_bytes(b"fixture kernel")
            manifest_path = self.write_native_evidence(root, kernel)
            digest = hashlib.sha256(kernel.read_bytes()).hexdigest()

            found, binding, _ = package_ci.validate_native_artifact(
                root, "123", "a" * 40, manifest_path,
            )

        self.assertEqual(found.name, "mach.development.t7001.unstripped")
        self.assertEqual(binding["kernel_sha256"], digest)
        self.assertIn("native_build_manifest_sha256", binding)

    def test_native_artifact_rejects_incomplete_build(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            kernel = root / "kernel/mach.development.t7001.unstripped"
            kernel.parent.mkdir()
            kernel.write_bytes(b"fixture kernel")
            manifest_path = self.write_native_evidence(
                root, kernel, provenance_status="failed",
            )
            with self.assertRaisesRegex(ValueError, "not complete"):
                package_ci.validate_native_artifact(root, "123", "a" * 40, manifest_path)

    def test_native_artifact_rejects_path_escape(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            kernel = root / "kernel/mach.development.t7001.unstripped"
            kernel.parent.mkdir()
            kernel.write_bytes(b"fixture kernel")
            manifest_path = self.write_native_evidence(root, kernel)
            artifact_path = root / "kernel-artifact.json"
            artifact = json.loads(artifact_path.read_text())
            artifact["artifact_path"] = "../kernel"
            artifact_path.write_text(json.dumps(artifact))
            with self.assertRaisesRegex(ValueError, "stay inside"):
                package_ci.validate_native_artifact(root, "123", "a" * 40, manifest_path)

    def test_native_artifact_rejects_a_different_build_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            kernel = root / "kernel/mach.development.t7001.unstripped"
            kernel.parent.mkdir()
            kernel.write_bytes(b"fixture kernel")
            manifest_path = self.write_native_evidence(root, kernel)
            plan_path = root / "native-build-plan.json"
            plan = json.loads(plan_path.read_text())
            plan["manifest_sha256"] = "0" * 64
            plan_path.write_text(json.dumps(plan))
            artifact_path = root / "kernel-artifact.json"
            artifact = json.loads(artifact_path.read_text())
            artifact["native_build_plan_sha256"] = hashlib.sha256(
                plan_path.read_bytes(),
            ).hexdigest()
            artifact_path.write_text(json.dumps(artifact))
            with self.assertRaisesRegex(ValueError, "R208 build manifest"):
                package_ci.validate_native_artifact(root, "123", "a" * 40, manifest_path)

    def test_native_artifact_rejects_patch_inputs_outside_the_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            kernel = root / "kernel/mach.development.t7001.unstripped"
            kernel.parent.mkdir()
            kernel.write_bytes(b"fixture kernel")
            manifest_path = self.write_native_evidence(root, kernel)
            provenance_path = root / "build-provenance.json"
            provenance = json.loads(provenance_path.read_text())
            provenance["inputs"]["source_diff"][0]["sha256"] = "0" * 64
            provenance_path.write_text(json.dumps(provenance))
            artifact_path = root / "kernel-artifact.json"
            artifact = json.loads(artifact_path.read_text())
            artifact["build_provenance_sha256"] = hashlib.sha256(
                provenance_path.read_bytes(),
            ).hexdigest()
            artifact_path.write_text(json.dumps(artifact))
            with self.assertRaisesRegex(ValueError, "ordered R208 build manifest"):
                package_ci.validate_native_artifact(root, "123", "a" * 40, manifest_path)


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
        self.assertIn("scripts/unixnu/devicetree.py", package_ci.PACKAGE_SOURCE_FILES)
        self.assertIn("scripts/unixnu/udif.py", package_ci.PACKAGE_SOURCE_FILES)
        self.assertIn("scripts/unixnu/util.py", package_ci.PACKAGE_SOURCE_FILES)
        self.assertIn("ci/native-build-manifest.r208-fallback-v2.json", package_ci.PACKAGE_SOURCE_FILES)
        self.assertIn("ci/native-source-provenance.r208-fallback-v2.json", package_ci.PACKAGE_SOURCE_FILES)
        self.assertIn("ci/native-build-manifest.r208-fallback-v3.json", package_ci.PACKAGE_SOURCE_FILES)
        self.assertIn("ci/native-source-provenance.r208-fallback-v3.json", package_ci.PACKAGE_SOURCE_FILES)
        self.assertIn("ci/manifests/r208-tf-emmc-root-fallback-v3-candidate.json", package_ci.PACKAGE_SOURCE_FILES)
        self.assertIn("patches/xnu/native-y35a-tf-emmc-root-fallback-v3.patch", package_ci.PACKAGE_SOURCE_FILES)
        self.assertIn("scripts/ci/verify_r208_fallback_v3_source.py", package_ci.PACKAGE_SOURCE_FILES)

    def test_candidate_native_manifest_is_selectable_but_external_paths_are_not(self):
        candidate = package_ci.resolve_native_manifest(
            ROOT / "ci/native-build-manifest.r208-fallback-v2.json",
        )
        self.assertEqual(candidate.name, "native-build-manifest.r208-fallback-v2.json")
        candidate_v3 = package_ci.resolve_native_manifest(
            ROOT / "ci/native-build-manifest.r208-fallback-v3.json",
        )
        self.assertEqual(candidate_v3.name, "native-build-manifest.r208-fallback-v3.json")
        with tempfile.TemporaryDirectory() as directory:
            external = Path(directory) / "manifest.json"
            external.write_text("{}")
            with self.assertRaisesRegex(ValueError, "inside the checked-out repository"):
                package_ci.resolve_native_manifest(external)

    def test_native_artifact_api_binding_requires_exact_id_and_digest(self):
        digest = "sha256:" + "a" * 64
        self.assertEqual(
            package_ci.validate_native_artifact_api_binding("15228783166", digest),
            {"id": 15228783166, "digest": digest},
        )
        with self.assertRaisesRegex(ValueError, "decimal Actions artifact ID"):
            package_ci.validate_native_artifact_api_binding("artifact-1", digest)
        with self.assertRaisesRegex(ValueError, "exact sha256"):
            package_ci.validate_native_artifact_api_binding("15228783166", "sha256:bad")

    def test_package_workflow_passes_selected_native_manifest(self):
        workflow = (ROOT / ".github/workflows/y35a-ci-package.yml").read_text()
        self.assertIn("native_manifest_path:", workflow)
        self.assertIn("ci/native-build-manifest.r208-fallback-v2.json", workflow)
        self.assertIn("ci/native-build-manifest.r208-fallback-v3.json", workflow)
        self.assertIn('--native-manifest "$NATIVE_BUILD_MANIFEST_PATH"', workflow)


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
            for component in package_ci.REQUIRED_PACKAGE_COMPONENTS:
                (root / component).write_bytes(b"actual" if component == name else component.encode())
            manifest = {
                "package_components": {
                    component: {
                        "path": component,
                        "bytes": 6 if component == name else (root / component).stat().st_size,
                        "sha256": "0" * 64 if component == name else hashlib.sha256(
                            (root / component).read_bytes(),
                        ).hexdigest(),
                    }
                    for component in package_ci.REQUIRED_PACKAGE_COMPONENTS
                },
            }

            with self.assertRaisesRegex(ValueError, "hash or size mismatch"):
                package_ci.verify_package_components(root, manifest)


if __name__ == "__main__":
    unittest.main()
