import importlib.util
import json
import os
import plistlib
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("arm_driver_4903", ROOT / "scripts/y35a/build_arm_driver_4903.py")
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


def object_bytes(cpu=0x0100000C, kind=1, platform=2, minimum=0x0C0400):
    command = struct.pack("<6I", 0x32, 24, platform, minimum, 0, 0)
    return struct.pack("<8I", 0xFEEDFACF, cpu, 0, kind, 1, len(command), 0, 0) + command


class Driver4903Tests(unittest.TestCase):
    def test_iostorage_family_source_requires_pinned_header_abi_and_bundle_version(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp)
            header_hashes = {}
            for name in M.IOSTORAGE_HEADER_FILES:
                (source / name).write_text(name)
                header_hashes[name] = M.sha256(source / name)
            for name in M.IOSTORAGE_FAMILY_SOURCE_FILES:
                (source / name).write_text("// pinned IOStorageFamily source")
                header_hashes[name] = M.sha256(source / name)
            (source / "Info.plist").write_bytes(plistlib.dumps({"CFBundleVersion": "2.1"}))
            source_record = {
                "repository": "https://github.com/apple-oss-distributions/IOStorageFamily",
                "tag": M.IOSTORAGE_FAMILY_TAG,
                "commit": M.IOSTORAGE_FAMILY_COMMIT,
                "git_archive_sha256": M.IOSTORAGE_FAMILY_ARCHIVE_SHA256,
                "bundle_version_in_tag": "2.1",
                "header_sha256": header_hashes,
            }
            (source / "SOURCE.json").write_text(json.dumps(source_record))
            with mock.patch.object(M, "IOSTORAGE_DEVICE_HEADER_SHA256", header_hashes["IOBlockStorageDevice.h"]):
                record = M.validate_iostorage_family_source(source)
            self.assertEqual(record["commit"], M.IOSTORAGE_FAMILY_COMMIT)
            self.assertEqual(record["bundle_version"], "2.1")
            source_record["commit"] = "wrong"
            (source / "SOURCE.json").write_text(json.dumps(source_record))
            with self.assertRaises(ValueError):
                M.validate_iostorage_family_source(source)

    def test_qcom_sdcc_component_support_sources_are_io_storage_family_sources(self):
        support = M.component_support_sources(
            "QcomSdcc", ROOT / "upstream-refresh/2026-11-15/sources/IOStorageFamily-191")
        self.assertEqual([path.name for path in support], list(M.IOSTORAGE_FAMILY_SOURCE_FILES))

    def test_qcom_sdcc_archive_member_is_combined_storage_object(self):
        run = Path('/tmp/arm-driver-4903-fixture')
        destination = run / 'QcomSdcc.o'
        self.assertEqual(
            M.archive_members('QcomSdcc', run, destination),
            [run / 'IOStorageFamily-QcomSdcc.o'])
        self.assertEqual(M.archive_members('ArmDTPlatform', run, destination), [destination])

    def test_qcom_sdcc_declares_userdata_window_force_load_contract(self):
        self.assertEqual(M.component_integration('QcomSdcc'), {
            'role': 'userdata-window',
            'force_load': True,
            'consumer': 'scripts/build-xnu-4903-native.py',
        })

    def test_input_binding_detects_header_config_change_and_missing_file(self):
        with tempfile.TemporaryDirectory() as temp:
            header = Path(temp) / "T7000.h"
            header.write_text("#define WITH_CLASSIC_S2R 1\n")
            records = [{"input": str(header), "sha256": M.sha256(header)}]
            self.assertEqual(M.changed_inputs(records), [])
            header.write_text("#define WITH_CLASSIC_S2R 0\n")
            self.assertEqual(M.changed_inputs(records), [str(header)])
            header.unlink()
            self.assertEqual(M.changed_inputs(records), [str(header)])

    def test_config_capture_requires_effective_classic_s2r(self):
        macros = "#define WITH_CLASSIC_S2R 1\n#define ARM64_BOARD_CONFIG_T7001 1\n"
        self.assertEqual(M.effective_configuration(macros)["WITH_CLASSIC_S2R"], "1")
        with self.assertRaises(ValueError):
            M.effective_configuration("#define ARM64_BOARD_CONFIG_T7001 1\n")

    def test_armcpu_sgi_probe_uses_input_register_for_write_and_output_for_counter(self):
        with tempfile.TemporaryDirectory(prefix="armcpu-4903-sgi-patch-") as temp:
            root = Path(temp)
            staged = root / "ArmCpu"
            staged.mkdir()
            shutil.copy2(ROOT / "drivers/ArmCpu/ArmCpu.cpp", staged / "ArmCpu.cpp")
            original = (staged / "ArmCpu.cpp").read_text()
            self.assertIn('"msr icc_sgi1r_el1, %0; isb; mrs %1, cntvct_el0"', original)
            patch = ROOT / "patches/arm-driver-4903/0002-armcpu-boot-only.patch"
            result = subprocess.run(["git", "-C", temp, "apply", str(patch)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            operand_patch = ROOT / "patches/arm-driver-4903/0004-armcpu-sgi-probe-constraints.patch"
            result = subprocess.run(["git", "-C", temp, "apply", str(operand_patch)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            source = (staged / "ArmCpu.cpp").read_text()
        self.assertIn(
            '"msr icc_sgi1r_el1, %1; isb; mrs %0, cntvct_el0" : "=r" (tb) : "r" (sgi)',
            source)

    def test_boot_policy_and_mapping_ownership_on_host(self):
        run = Path(tempfile.mkdtemp(prefix="armcpu-4903-ownership-", dir="/tmp"))
        source = ROOT / "patches/arm-driver-4903/test-support.cpp"
        command = ["xcrun", "clang++", "-std=c++17", "-Wall", "-Wextra", "-Werror",
                   "-fsanitize=address,undefined", "-fno-omit-frame-pointer",
                   str(source), "-o", str(run / "ownership-test")]
        result = subprocess.run(command, capture_output=True, text=True)
        (run / "compile-command.json").write_text(json.dumps(command, indent=2))
        (run / "compile.log").write_text(result.stdout + result.stderr)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        result = subprocess.run([str(run / "ownership-test")], capture_output=True, text=True)
        (run / "test.log").write_text(result.stdout + result.stderr)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        print(f"Ownership and boot policy artifacts: {run}")

    def test_armcpu_mode_must_be_explicit_and_cannot_mask_baseline(self):
        parent = Path(tempfile.mkdtemp(prefix="armcpu-4903-mode-test-", dir="/tmp"))
        for index, args in enumerate((["--component", "ArmCpu"], ["--boot-cpu-only"],
                                      ["--component", "ArmCpu", "--baseline", "--boot-cpu-only"])):
            output = parent / str(index)
            result = subprocess.run([sys.executable, str(ROOT / "scripts/y35a/build_arm_driver_4903.py"),
                                     "--run-root", str(output)] + args, capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertFalse(output.exists())

    def test_accepts_arm64_ios124_object(self):
        self.assertEqual(M.audit_object(object_bytes())["minimum_os"], "12.4.0")

    def test_rejects_other_abi_and_linked_kernel(self):
        for data in (object_bytes(cpu=0x01000007), object_bytes(kind=2),
                     object_bytes(platform=1), object_bytes(minimum=0x110000)):
            with self.subTest(data=data), self.assertRaises(ValueError):
                M.audit_object(data)

    def test_rejects_truncated_or_invalid_load_commands(self):
        for data in (b"", object_bytes()[:-1], object_bytes()[:36] + struct.pack("<I", 0) + object_bytes()[40:]):
            with self.subTest(data=data), self.assertRaises(ValueError):
                M.audit_object(data)

    def test_existing_output_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            marker = root / "keep"
            marker.write_text("user data")
            with self.assertRaises(FileExistsError):
                M.allocate_run(root, [ROOT])
            self.assertEqual(marker.read_text(), "user data")

    def test_output_under_inputs_is_rejected_even_through_symlink(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            protected = root / "input"
            protected.mkdir()
            alias = root / "alias"
            alias.symlink_to(protected, target_is_directory=True)
            for candidate in (protected / "new", alias / "new"):
                with self.subTest(candidate=candidate), self.assertRaises(ValueError):
                    M.allocate_run(candidate, [protected])
            self.assertEqual(list(protected.iterdir()), [])

    def test_config_keeps_space_containing_define_as_one_argument(self):
        config = 'export CONFIG_DEFINES = -DIOKIT -DCONFIG_NMBCLUSTERS="((1024 * 256) / MCLBYTES)"\n'
        self.assertEqual(M.config_defines(config), ["-DIOKIT", "-DCONFIG_NMBCLUSTERS=((1024 * 256) / MCLBYTES)"])

    def test_config_refuses_command_or_include_injection(self):
        for bad in ("-DIOKIT -include /tmp/other.h", "-DIOKIT $(shell bad)", "-DIOKIT -o /tmp/file"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                M.config_defines("export CONFIG_DEFINES = " + bad)

    def test_dependency_audit_rejects_host_headers(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            local = root / "headers"
            local.mkdir()
            (local / "a.h").write_text("snapshot")
            (root / "host.h").write_text("host")
            good = M.audit_dependencies(f"out: {local / 'a.h'}", local)
            self.assertEqual(len(good), 1)
            with self.assertRaises(ValueError):
                M.audit_dependencies(f"out: {root / 'host.h'}", local)

    def test_dependency_audit_handles_escaped_spaces(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            header = root / "space name.h"
            header.write_text("real bytes")
            escaped = str(header).replace(" ", "\\ ")
            self.assertEqual(M.audit_dependencies(f"out: {escaped}", root)[0]["sha256"], M.sha256(header))

    def test_qcom_sdcc_component_selects_only_its_own_source_patch_and_personality(self):
        self.assertEqual(M.component_patches("QcomSdcc"), [])
        self.assertEqual(M.component_defines("QcomSdcc"), [
            "-DXNU_NATIVE_SDCC=1",
        ])
        self.assertEqual(M.component_defines("ArmDTPlatform"), [])
        self.assertEqual(M.component_personality_patch("QcomSdcc"),
                         ROOT / "patches/arm-driver-4903/0005-qcom-sdcc-personality.patch")
        sources = M.component_source_files("QcomSdcc")
        self.assertIn(ROOT / "drivers/QcomSdcc/NativeSdcc.cpp", sources)
        self.assertIn(ROOT / "drivers/QcomSdcc/SdciCore.h", sources)
        self.assertIn(ROOT / "drivers/QcomSdcc/PersistStore.h", sources)
        self.assertEqual(M.component_entry_source("QcomSdcc"), "NativeSdcc.cpp")
        self.assertEqual(M.component_support_sources(
            "QcomSdcc", ROOT / "upstream-refresh/2026-11-15/sources/IOStorageFamily-191"),
            [ROOT / "upstream-refresh/2026-11-15/sources/IOStorageFamily-191" / name
             for name in M.IOSTORAGE_FAMILY_SOURCE_FILES])
        self.assertEqual(M.component_support_sources("ArmDTPlatform"), [])

    def test_arm_components_stage_exact_existing_translation_unit_inputs(self):
        expected = {
            "ArmDTPlatform": ("ArmDTPlatform.cpp",),
            "ArmCpu": ("ArmCpu.cpp", "GicV2.h"),
        }
        for component, names in expected.items():
            with self.subTest(component=component):
                sources = M.component_source_files(component)
                self.assertEqual(tuple(path.name for path in sources), names)
                self.assertTrue(all(path.is_file() for path in sources))

                with tempfile.TemporaryDirectory() as temp:
                    staged = Path(temp) / component
                    records = []
                    for source in sources:
                        M.snapshot(source, staged / source.name, records)
                    self.assertEqual(
                        tuple(path.name for path in sorted(staged.iterdir())), names)
                    self.assertEqual(
                        [Path(record["input"]).name for record in records], list(names))
                    for source in sources:
                        self.assertEqual(
                            (staged / source.name).read_bytes(), source.read_bytes())

    def test_component_patch_map_keeps_4903_platform_patches_disjoint(self):
        self.assertEqual(M.component_patches("ArmDTPlatform"), [M.PATCH])
        self.assertEqual(M.component_patches("ArmCpu"), [M.CPU_PATCH, M.CPU_SGI_PATCH])
        with self.assertRaises(ValueError):
            M.component_patches("NotADriver")

    @unittest.skipUnless(os.environ.get("ARM_DRIVER_4903_NATIVE_BUILD"), "opt-in real XNU header compile")
    def test_real_headers_fail_before_patch_and_compile_after_patch(self):
        native = os.environ["ARM_DRIVER_4903_NATIVE_BUILD"]
        original = ROOT / "drivers/ArmDTPlatform/ArmDTPlatform.cpp"
        before = M.sha256(original)
        # Preserve both compiler runs for review, including a failed baseline.
        parent = Path(tempfile.mkdtemp(prefix="arm-driver-4903-test-", dir="/tmp"))
        for name, extra, expected in (("baseline", ["--baseline"], 1), ("patched", [], 0)):
            run = parent / name
            result = subprocess.run([sys.executable, str(ROOT / "scripts/y35a/build_arm_driver_4903.py"),
                                     "--native-build", native, "--board-profile", "y35a-a53",
                                     "--run-root", str(run)] + extra,
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
            manifest = json.loads((run / "manifest.json").read_text())
            if name == "baseline":
                self.assertIn("no template named 'OSSharedPtr'", (run / "compile.log").read_text())
                self.assertFalse((run / "ArmDTPlatform.o").exists())
            else:
                self.assertEqual(manifest["status"], "object-compiled")
                self.assertEqual(M.audit_object((run / "ArmDTPlatform.o").read_bytes())["minimum_os"], "12.4.0")
                self.assertGreater(manifest["consumed_input_count"], 10)
                self.assertEqual(manifest["configuration"]["effective_macros"]["WITH_CLASSIC_S2R"], "0")
            self.assertEqual(M.sha256(original), before)
        print(f"Real header regression artifacts: {parent}")

    @unittest.skipUnless(os.environ.get("ARM_DRIVER_4903_NATIVE_BUILD"), "opt-in real XNU header compile")
    def test_armcpu_original_fails_and_explicit_boot_only_compiles(self):
        native = os.environ["ARM_DRIVER_4903_NATIVE_BUILD"]
        original = ROOT / "drivers/ArmCpu/ArmCpu.cpp"
        before = M.sha256(original)
        parent = Path(tempfile.mkdtemp(prefix="armcpu-4903-test-", dir="/tmp"))
        for name, extra, expected in (("baseline", ["--baseline"], 1),
                                     ("boot-only", ["--boot-cpu-only"], 0)):
            run = parent / name
            result = subprocess.run([sys.executable, str(ROOT / "scripts/y35a/build_arm_driver_4903.py"),
                                     "--native-build", native, "--component", "ArmCpu",
                                     "--board-profile", "y35a-a53",
                                     "--run-root", str(run)] + extra, capture_output=True, text=True)
            self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
            manifest = json.loads((run / "manifest.json").read_text())
            if name == "baseline":
                log = (run / "compile.log").read_text()
                for symbol in ("OSSharedPtr", "ml_get_cluster_number", "ml_get_boot_cluster_type"):
                    self.assertIn(symbol, log)
                self.assertFalse((run / "ArmCpu.o").exists())
            else:
                self.assertEqual(manifest["cpu_mode"], "boot-cpu-only")
                self.assertEqual(manifest["maximum_supported_cpus"], 1)
                self.assertFalse(manifest["smp_supported"])
                self.assertEqual(manifest["required_boot_args"], ["cpus=1"])
                self.assertEqual(manifest["status"], "object-compiled")
                self.assertEqual(manifest["configuration"]["effective_macros"]["WITH_CLASSIC_S2R"], "0")
                self.assertEqual(manifest["configuration"]["explicit_other_cflags"], ["-DXNU_Y35A_A53=1"])
                self.assertEqual(M.verify_inputs(run), 0)
                # A later installhdrs/profile change must invalidate the bound run.
                inventory = json.loads((run / "inputs.json").read_text())
                self.assertTrue(any("cpu_data_internal.h" in item["input"] for item in inventory))
                self.assertEqual((run / "compile.log").read_text(), "")
                undefined = set(manifest["undefined_symbols"])
                self.assertIn("_ml_get_boot_cluster", undefined)
                for symbol in ("_ml_get_cluster_number", "_ml_get_boot_cluster_type",
                               "_processor_start", "_kernel_thread_start", "_LowResetVectorBase"):
                    self.assertNotIn(symbol, undefined)
                obj = (run / "ArmCpu.o").read_bytes()
                self.assertEqual(M.audit_object(obj)["minimum_os"], "12.4.0")
                # Even direct compiler reuse cannot accidentally enable a generic/SMP build.
                compile_args = json.loads((run / "compile-command.json").read_text())["argv"]
                base = compile_args[:compile_args.index("-MD")]
                base.remove("-DARMCPU_4903_BOOT_CPU_ONLY=1")
                negative = base + ["-DARMCPU_4903_BOOT_CPU_ONLY=0", "-c",
                                   str(run / "driver/ArmCpu/ArmCpu.cpp"), "-o", str(run / "forbidden.o")]
                result = subprocess.run(negative, capture_output=True, text=True)
                (run / "mode-guard-command.json").write_text(json.dumps(negative, indent=2))
                (run / "mode-guard.log").write_text(result.stdout + result.stderr)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("requires explicit ARMCPU_4903_BOOT_CPU_ONLY=1", result.stderr)
                self.assertFalse((run / "forbidden.o").exists())
                disassembly = subprocess.check_output(["xcrun", "otool", "-tvV", str(run / "ArmCpu.o")], text=True)
                (run / "disassembly.log").write_text(disassembly)
                self.assertNotRegex(disassembly, r"\t(?:smc|hvc)\s")
                probe = disassembly.split("_armcpu_sgi_selfprobe:\n", 1)[1].split(
                    "_armcpu_ipi_selftest:\n", 1)[0]
                self.assertRegex(probe, re.compile(
                    r"orr\s+(x\d+), x\d+, x\d+, lsl #24\n"
                    r"[^\n]*dsb\s+ishst\n[^\n]*msr\s+ICC_SGI1R_EL1, \1"))
            self.assertEqual(M.sha256(original), before)
        print(f"ArmCpu real header regression artifacts: {parent}")


if __name__ == "__main__":
    unittest.main()
