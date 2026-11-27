import importlib.util
import json
import os
from pathlib import Path
import shlex
import struct
import subprocess
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/build-xnu-4903-native.py"
SPEC = importlib.util.spec_from_file_location("build_xnu_4903_native", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class NativeXnuBuildContractTest(unittest.TestCase):
    def test_driver_archive_is_force_loaded_into_build_command(self):
        archive = Path('/tmp/libQcomSdcc.a')
        command = MODULE.make_step_command(
            'build', run_root=Path('/tmp/run'), source=Path('/tmp/src'),
            fakeroot=Path('/tmp/fakeroot'), overlay=Path('/tmp/overlay'),
            make=Path('/usr/bin/make'), host_sdkroot=Path('/tmp/sdk'),
            toolchain=Path('/tmp/toolchain'), memory_bytes=1024,
            physical_cpu_count=1, logical_cpu_count=1, jobs=1,
            host_os_version='fixture', driver_archives=[archive])
        libs = next(value for value in command if value.startswith('LD_KERNEL_LIBS='))
        self.assertIn('-Wl,-force_load,/tmp/libQcomSdcc.a', libs)
        self.assertLess(libs.index('libcc_kext.a'), libs.index('libQcomSdcc.a'))

    def test_native_build_enables_firehose_spi_contract(self):
        command = self.make_command("build")
        self.assertIn(
            "OTHER_CFLAGS=-DXNU_NATIVE_EARLY_FAULT=1 -DOS_FIREHOSE_SPI=1",
            command,
        )

    def test_monotonic_header_guard_is_applied_to_staged_source(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)
            header = source / "osfmk/machine/monotonic.h"
            header.parent.mkdir(parents=True)
            header.write_text(
                "#error unsupported architecture\n#endif\n\n"
                "#include <stdatomic.h>\n#include <stdbool.h>\n#include <stdint.h>\n"
                "int mt_microstackshot_start_arch(uint64_t period);\n"
            )
            result = MODULE.patch_monotonic_header(source)
            self.assertEqual(result["status"], "patched")
            text = header.read_text()
            self.assertEqual(text.count("#if defined(MT_CORE_NFIXED)"), 1)
            self.assertIn("#endif /* defined(MT_CORE_NFIXED) */", text)

    def test_userdata_window_manifest_binds_archive_hash_and_role(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / 'libQcomSdcc.a'
            archive.write_bytes(b'archive')
            manifest = root / 'manifest.json'
            manifest.write_text(json.dumps({
                'integration': {'role': 'userdata-window', 'force_load': True},
                'archive': {'sha256': MODULE.sha256_file(archive)},
            }))
            data = MODULE.validate_driver_manifest(manifest, [archive])
            self.assertEqual(data['integration']['role'], 'userdata-window')
            archive.write_bytes(b'changed')
            with self.assertRaisesRegex(SystemExit, 'does not match manifest'):
                MODULE.validate_driver_manifest(manifest, [archive])

    def test_driver_manifest_binds_exact_ci_producer_and_embedded_abi(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "libQcomSdcard.a"
            archive.write_bytes(b"archive")
            manifest_path = root / "driver-manifest.json"
            data = {
                "integration": {"role": "tf-storage", "force_load": True},
                "archive": {"path": "libQcomSdcard.a", "sha256": MODULE.sha256_file(archive)},
                "source": {"sha256": "a" * 64},
                "xnu": {"commit": "xnu-pin"},
                "iostorage": {"commit": "iostorage-pin"},
                "ci_provenance": {
                    "run_id": 123, "artifact_name": "r208-native-sdcard-123",
                    "head_sha": "b" * 40, "head_branch": "topic",
                    "workflow_name": "R208 TF validation",
                },
                "kext_abi": {
                    "status": "passed", "config_embedded": 1,
                    "apple_kext_vtable_padding": 0, "apple_kext_align_containers": 1,
                },
                "archive_kext_abi": {"status": "passed", "reserved_abi_imports": []},
            }
            manifest_path.write_text(json.dumps(data))
            expected = {
                "run_id": 123, "name": "r208-native-sdcard-123", "head_sha": "b" * 40,
                "head_branch": "topic",
                "sha256": MODULE.sha256_file(archive), "archive": "libQcomSdcard.a",
                "source_sha256": "a" * 64, "xnu_commit": "xnu-pin",
                "iostorage_commit": "iostorage-pin",
                "driver_manifest_sha256": MODULE.sha256_file(manifest_path),
            }
            MODULE.validate_driver_manifest(manifest_path, [archive], expected=expected)
            data["ci_provenance"]["run_id"] = 124
            manifest_path.write_text(json.dumps(data))
            with self.assertRaisesRegex(SystemExit, "producer run_id"):
                MODULE.validate_driver_manifest(manifest_path, [archive], expected=expected)

    def test_driver_archive_requires_manifest(self):
        with self.assertRaisesRegex(SystemExit, 'requires --driver-manifest'):
            MODULE.load_driver_integration([Path('/tmp/libQcomSdcc.a')], None)

    def test_driver_manifest_requires_archive(self):
        with self.assertRaisesRegex(SystemExit, 'requires --driver-archive'):
            MODULE.load_driver_integration([], Path('/tmp/manifest.json'))

    def execute_fixture(self, root, *, expected=None, manifest=None, gate_error=None,
                        malformed=False, profile=(), commands=None):
        """Exercise the runner orchestration with only expensive build work stubbed."""
        source = root / "source"
        source.mkdir()
        fakeroot = root / "fakeroot-input"
        fakeroot.mkdir()
        overlay = root / "overlay-input"
        overlay.mkdir()
        wrapper = root / "xcrun-input"
        wrapper.write_text("fixture")
        source_provenance = root / "source-provenance.json"
        source_provenance.write_text("{}")
        run_root = root / "run"
        run_root.mkdir()
        staged_source = run_root / "src"
        genassym = staged_source / "osfmk/arm64/genassym.c"
        genassym.parent.mkdir(parents=True)
        genassym.write_text(r'.ascii \"#%0\"" : : "i"' + "\n")
        monotonic = staged_source / "osfmk/machine/monotonic.h"
        monotonic.parent.mkdir(parents=True)
        monotonic.write_text("#if defined(MT_CORE_NFIXED)\n#endif /* defined(MT_CORE_NFIXED) */\n")
        subprocess.run(["git", "init", "-q", str(staged_source)], check=True)
        subprocess.run(["git", "-C", str(staged_source), "config", "user.name", "Fixture"], check=True)
        subprocess.run(["git", "-C", str(staged_source), "config", "user.email", "fixture@example.invalid"], check=True)
        subprocess.run(["git", "-C", str(staged_source), "add", "."], check=True)
        subprocess.run(["git", "-C", str(staged_source), "commit", "-qm", "fixture"], check=True)
        provenance_path = run_root / "build-provenance.json"
        args = MODULE.parse_args(list(profile))
        provenance = {
            "run_root": str(run_root), "status": "preparing", "steps": [],
            "build_profile": {
                "y35a_a53": args.y35a_a53,
                "y35a_low_vector": args.y35a_low_vector,
                "phase_a_amfi": args.phase_a_amfi,
                "y35a_storage_fallback": args.y35a_storage_fallback,
                "other_cflags": ["-DXNU_NATIVE_EARLY_FAULT=1", "-DOS_FIREHOSE_SPI=1"]
                + (["-DXNU_Y35A_A53=1"] if args.y35a_a53 else [])
                + (["-DXNU_Y35A_LOW_VECTOR=1"] if args.y35a_low_vector else [])
                + (["-DXNU_Y35A_PHASE_A_AMFI=1"] if args.phase_a_amfi else [])
                + (["-DXNU_Y35A_STORAGE_FALLBACK=1"] if args.y35a_storage_fallback else []),
            },
        }
        args.expected_sha256 = expected
        args.manifest = manifest
        xcode = {"developer_dir": "/xcode", "toolchain": "/xcode/toolchain",
                 "macosx_sdk": "/xcode/sdk", "memory_bytes": 1024,
                 "physical_cpu_count": 1, "logical_cpu_count": 1,
                 "host_os_version": "fixture"}
        gates = []

        def fake_step(name, command, **kwargs):
            if commands is not None:
                commands.append((name, command))
            if name == "build":
                kernel = run_root / "obj/DEVELOPMENT_ARM64_T7001/mach.development.t7001.unstripped"
                kernel.parent.mkdir(parents=True)
                header = struct.pack("<IiiIIIII", MODULE.MACHO_MAGIC_64,
                                     MODULE.CPU_TYPE_ARM64, 0, MODULE.MH_EXECUTE,
                                     1, 72, 0, 0)
                segment = struct.pack("<II16sQQQQiiII", MODULE.LC_SEGMENT_64,
                                      72, b"__TEXT", MODULE.KERNEL_TEXT_BASE,
                                      4096, 0, 104, 7, 5, 0, 0)
                kernel.write_bytes(b"bad linked output" if malformed else header + segment)
            elif name not in ("installhdrs", "build"):
                gates.append(command)
                # The artifact must be durable before a verifier can fail or interrupt.
                saved = json.loads(provenance_path.read_text())
                self.assertEqual(saved["kernel_artifact"]["sha256"],
                                 MODULE.sha256_file(Path(saved["kernel_artifact"]["path"])))
                self.assertTrue((run_root / "kernel-artifact.json").is_file())
                if gate_error:
                    raise gate_error

        with mock.patch.object(MODULE, "stage_source_tree", return_value="staged"), \
                mock.patch.object(MODULE, "_run_logged", side_effect=fake_step):
            MODULE.run_recorded(provenance_path, provenance, lambda: MODULE._execute_run(
                args, run_root=run_root, provenance=provenance,
                provenance_path=provenance_path, source=source,
                source_provenance=source_provenance, fakeroot_input=fakeroot,
                overlay_input=overlay, wrapper_input=wrapper, patch_paths=[],
                xcode_info=xcode, assets={"source": {"tree_sha256": MODULE.tree_sha256(source)}},
            ))
        return provenance, gates

    def make_command(self, target="build", **profile):
        root = Path("/unused/native-profile-contract")
        return MODULE.make_step_command(
            target, run_root=root, source=root / "src", fakeroot=root / "fakeroot",
            overlay=root / "overlay", make=Path("/usr/bin/make"),
            host_sdkroot=Path("/xcode/sdk"), toolchain=Path("/xcode/toolchain"),
            memory_bytes=1024, physical_cpu_count=1, logical_cpu_count=1,
            jobs=1, host_os_version="fixture", **profile,
        )

    def test_profile_defaults_preserve_source_and_explicit_patch_selection(self):
        defaults = MODULE.parse_args([])
        self.assertFalse(defaults.y35a_a53)
        self.assertFalse(defaults.y35a_low_vector)
        self.assertFalse(defaults.phase_a_amfi)
        self.assertFalse(defaults.y35a_storage_fallback)
        self.assertIsNone(defaults.developer_dir)
        self.assertEqual(defaults.patch, [])
        self.assertEqual(defaults.source, MODULE.DEFAULT_SOURCE)
        self.assertEqual(defaults.source_diff, MODULE.DEFAULT_SOURCE_DIFF)
        explicit = MODULE.parse_args([
            "--y35a-a53", "--y35a-low-vector", "--phase-a-amfi",
            "--y35a-storage-fallback",
            "--developer-dir", "/xcode/Developer",
            "--patch", "first.patch",
            "--patch", "second.patch",
        ])
        self.assertTrue(explicit.y35a_a53)
        self.assertTrue(explicit.y35a_low_vector)
        self.assertTrue(explicit.phase_a_amfi)
        self.assertTrue(explicit.y35a_storage_fallback)
        self.assertEqual(explicit.developer_dir, Path("/xcode/Developer"))
        self.assertEqual(explicit.patch, [Path("first.patch"), Path("second.patch")])
        self.assertEqual(explicit.source_diff, defaults.source_diff)

    def test_no_source_diff_is_explicit_and_does_not_use_historical_default(self):
        args = MODULE.parse_args(["--no-source-diff"])
        self.assertIsNone(args.source_diff)

    def test_default_make_flags_use_consumed_variable_without_sflags_override(self):
        installhdrs = self.make_command("installhdrs")
        build = self.make_command("build")
        self.assertFalse(any(value.startswith(("CFLAGS_EXTRA=", "OTHER_CFLAGS=", "SFLAGS"))
                             for value in installhdrs))
        other_cflags = next(value for value in build if value.startswith("OTHER_CFLAGS="))
        self.assertIn("-DXNU_NATIVE_EARLY_FAULT=1", other_cflags)
        self.assertIn("-DOS_FIREHOSE_SPI=1", other_cflags)
        self.assertFalse(any(value.startswith(("CFLAGS_EXTRA=", "SFLAGS")) for value in build))
        self.assertFalse(any("XNU_Y35A_" in value for value in build))

    def test_profile_reaches_recorded_build_step(self):
        with tempfile.TemporaryDirectory() as directory:
            commands = []
            self.execute_fixture(Path(directory),
                                 profile=("--y35a-a53", "--y35a-low-vector"),
                                 commands=commands)
            self.assertEqual(commands[0][0], "installhdrs")
            self.assertFalse(any(part.startswith("OTHER_CFLAGS=") for part in commands[0][1]))
            self.assertEqual(commands[1][0], "build")
            self.assertIn(
                "OTHER_CFLAGS=-DXNU_NATIVE_EARLY_FAULT=1 -DOS_FIREHOSE_SPI=1 "
                "-DXNU_Y35A_A53=1 -DXNU_Y35A_LOW_VECTOR=1", commands[1][1])
            recorded = json.loads((Path(directory) / "run/build-provenance.json").read_text())
            self.assertEqual(recorded["build_profile"], {
                "y35a_a53": True, "y35a_low_vector": True,
                "phase_a_amfi": False,
                "y35a_storage_fallback": False,
                "other_cflags": ["-DXNU_NATIVE_EARLY_FAULT=1", "-DOS_FIREHOSE_SPI=1",
                                 "-DXNU_Y35A_A53=1", "-DXNU_Y35A_LOW_VECTOR=1"],
            })

    def test_phase_a_amfi_flag_reaches_make_and_provenance(self):
        command = self.make_command(
            y35a_a53=True, y35a_low_vector=True, phase_a_amfi=True)
        self.assertIn(
            "OTHER_CFLAGS=-DXNU_NATIVE_EARLY_FAULT=1 -DOS_FIREHOSE_SPI=1 "
            "-DXNU_Y35A_A53=1 -DXNU_Y35A_LOW_VECTOR=1 "
            "-DXNU_Y35A_PHASE_A_AMFI=1", command)
        with tempfile.TemporaryDirectory() as directory:
            commands = []
            self.execute_fixture(
                Path(directory),
                profile=("--y35a-a53", "--y35a-low-vector", "--phase-a-amfi"),
                commands=commands,
            )
            self.assertIn(
                "-DXNU_Y35A_PHASE_A_AMFI=1",
                " ".join(commands[1][1]),
            )
            recorded = json.loads(
                (Path(directory) / "run/build-provenance.json").read_text())
            self.assertTrue(recorded["build_profile"]["phase_a_amfi"])
            self.assertIn(
                "-DXNU_Y35A_PHASE_A_AMFI=1",
                recorded["build_profile"]["other_cflags"],
            )

    def test_y35a_storage_fallback_flag_reaches_make_and_provenance(self):
        command = self.make_command(y35a_a53=True, y35a_storage_fallback=True)
        self.assertIn(
            "OTHER_CFLAGS=-DXNU_NATIVE_EARLY_FAULT=1 -DOS_FIREHOSE_SPI=1 "
            "-DXNU_Y35A_A53=1 -DXNU_Y35A_STORAGE_FALLBACK=1",
            command,
        )
        with tempfile.TemporaryDirectory() as directory:
            commands = []
            self.execute_fixture(
                Path(directory),
                profile=("--y35a-a53", "--y35a-storage-fallback"),
                commands=commands,
            )
            self.assertIn(
                "-DXNU_Y35A_STORAGE_FALLBACK=1",
                " ".join(commands[1][1]),
            )
            recorded = json.loads(
                (Path(directory) / "run/build-provenance.json").read_text())
            self.assertTrue(recorded["build_profile"]["y35a_storage_fallback"])
            self.assertIn(
                "-DXNU_Y35A_STORAGE_FALLBACK=1",
                recorded["build_profile"]["other_cflags"],
            )

    def test_xcode_input_probe_uses_selected_developer_dir_for_xcrun(self):
        with tempfile.TemporaryDirectory() as directory:
            developer = Path(directory) / "Developer"
            (developer / "usr/bin").mkdir(parents=True)
            (developer / "Toolchains/XcodeDefault.xctoolchain/usr/bin").mkdir(parents=True)
            (developer / "Toolchains/XcodeDefault.xctoolchain/usr/libexec").mkdir(parents=True)
            for relative in (
                "usr/bin/xcodebuild", "usr/bin/xcrun", "usr/bin/make",
                "Toolchains/XcodeDefault.xctoolchain/usr/bin/make",
                "Toolchains/XcodeDefault.xctoolchain/usr/bin/clang",
                "Toolchains/XcodeDefault.xctoolchain/usr/bin/clang++",
                "Toolchains/XcodeDefault.xctoolchain/usr/bin/mig",
                "Toolchains/XcodeDefault.xctoolchain/usr/bin/codesign_allocate",
                "Toolchains/XcodeDefault.xctoolchain/usr/libexec/migcom",
            ):
                path = developer / relative
                path.write_text("fixture")
            calls = []

            def fake_capture(command, *, env=None):
                calls.append((command, env))
                if command[-1] == "-version":
                    return "Xcode 16.4\nBuild version 16F6\n"
                if command[-1] == "--show-sdk-path" and command[-2] == "iphoneos":
                    return "/sdk/iphoneos"
                if command[-1] == "--show-sdk-version":
                    return "18.5"
                if command[-1] == "--show-sdk-path" and command[-2] == "macosx":
                    return "/sdk/macosx"
                if command[:3] == ["/usr/sbin/sysctl", "-n", "hw.memsize"]:
                    return "1024"
                if command[:3] == ["/usr/sbin/sysctl", "-n", "hw.physicalcpu"]:
                    return "1"
                if command[:3] == ["/usr/sbin/sysctl", "-n", "hw.logicalcpu"]:
                    return "1"
                if command == ["/usr/bin/sw_vers", "-productVersion"]:
                    return "13.7.8"
                raise AssertionError(command)

            with mock.patch.object(MODULE, "_capture", side_effect=fake_capture):
                info = MODULE._xcode_inputs(developer)
            self.assertEqual(info["iphoneos_sdk_version"], "18.5")
            xcrun_calls = [call for call in calls if call[0][0].endswith("/usr/bin/xcrun")]
            self.assertEqual(len(xcrun_calls), 3)
            for command, env in xcrun_calls:
                self.assertEqual(command[0], "/usr/bin/xcrun")
                self.assertEqual(env["DEVELOPER_DIR"], str(developer.resolve()))

    @unittest.skipUnless(os.environ.get("UNIXNU_XNU_SOURCE"), "exact pinned XNU source is not provided")
    def test_real_4903_make_expands_profile_for_c_s_cpp_and_genassym(self):
        # This integration check needs the same local, pinned source as the runner.
        # It expands real rules in a private makefile; no kernel recipe is executed.
        source = Path(os.environ.get("UNIXNU_XNU_SOURCE", MODULE.DEFAULT_SOURCE))
        definitions = source / "makedefs/MakeInc.def"
        self.assertTrue(definitions.is_file(), "prepare the runner's local XNU 4903 source")
        template = (source / "osfmk/conf/Makefile.template").read_text().splitlines()
        rules = (source / "makedefs/MakeInc.rule").read_text().splitlines()
        additions = [line for line in template if line.startswith(("CFLAGS+=", "SFLAGS+="))]
        recipes = [line for line in rules
                   if line.startswith(("C_RULE_1A=", "S_RULE_1A=", "P_RULE_1A="))]
        genassym = next(line.strip().removeprefix("$(_v)") for line in template
                       if line.startswith("\t$(_v)${GENASSYM_KCC} "))
        with tempfile.TemporaryDirectory() as directory:
            makefile = Path(directory) / "profile.mk"
            makefile.write_text("\n".join([
                "CURRENT_ARCH_CONFIG=ARM64", "CURRENT_KERNEL_CONFIG=DEVELOPMENT",
                "CURRENT_MACHINE_CONFIG=T7001", "TR=/usr/bin/tr",
                f"include {definitions}", *additions, *recipes,
                ".PHONY: probe observe", "probe:",
                '\t@$(MAKE) --no-print-directory -f "$(firstword $(MAKEFILE_LIST))" observe',
                "observe:",
                "\t@printf '%s\\n' 'C=$(C_RULE_1A)' 'S=$(S_RULE_1A)' "
                f"'CPP=$(P_RULE_1A)' 'GENASSYM={genassym}'",
            ]) + "\n")
            for a53, vector in ((False, False), (True, False), (False, True), (True, True)):
                for target in ("build",):
                    with self.subTest(a53=a53, vector=vector, target=target):
                        command = self.make_command(target, y35a_a53=a53, y35a_low_vector=vector)
                        # Retain every runner make assignment, including overrides.
                        assignments = [part for part in command[5:] if "=" in part]
                        result = subprocess.run(
                            ["/usr/bin/make", "--no-print-directory", "-f", str(makefile),
                             "probe", *assignments], cwd=directory, check=True,
                            capture_output=True, text=True,
                            env={"PATH": "/usr/bin:/bin", "LC_ALL": "C"},
                        )
                        expanded = dict(line.split("=", 1) for line in result.stdout.splitlines())
                        self.assertEqual(set(expanded), {"C", "S", "CPP", "GENASSYM"})
                        for kind, value in expanded.items():
                            flags = shlex.split(value)
                            for required in ("-DXNU_NATIVE_EARLY_FAULT=1", "-Darm64",
                                             "-DARM64", "-DLP64", "-DPAGE_SIZE_FIXED",
                                             "-DARM64_BOARD_CONFIG_T7001", "-mkernel",
                                             "-include", "meta_features.h"):
                                self.assertIn(required, flags, (kind, value))
                            self.assertEqual(flags.count("-DXNU_Y35A_A53=1"), int(a53))
                            self.assertEqual(flags.count("-DXNU_Y35A_LOW_VECTOR=1"), int(vector))
                            if kind == "S":
                                self.assertIn("-D__ASSEMBLER__", flags)
                            if kind == "GENASSYM":
                                self.assertIn("-S", flags)

    def test_kernel_static_gate_runs_without_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            provenance, gates = self.execute_fixture(root)
            self.assertEqual(len(gates), 1)
            self.assertNotIn("--manifest", gates[0])
            self.assertEqual(provenance["manifest_verification"]["status"], "not-requested")
            self.assertEqual(provenance["kernel_static_verification"]["status"], "passed")

    def test_expected_hash_failure_keeps_linked_artifact(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaisesRegex(SystemExit, "does not match expected"):
                self.execute_fixture(root, expected="0" * 64)
            saved = json.loads((root / "run/build-provenance.json").read_text())
            self.assertEqual(saved["status"], "failed")
            artifact = json.loads((root / "run/kernel-artifact.json").read_text())
            self.assertEqual(saved["kernel_artifact"], artifact)
            self.assertEqual(artifact["sha256"], MODULE.sha256_file(Path(artifact["path"])))

    def test_static_gate_failure_and_interrupt_keep_linked_artifact(self):
        for error in (SystemExit("static gate failed"), KeyboardInterrupt()):
            with self.subTest(error=type(error).__name__), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                with self.assertRaises(type(error)):
                    self.execute_fixture(root, gate_error=error)
                saved = json.loads((root / "run/build-provenance.json").read_text())
                self.assertIn("kernel_artifact", saved)
                self.assertEqual(saved["kernel_static_verification"]["status"],
                                 "interrupted" if isinstance(error, KeyboardInterrupt) else "failed")

    def test_invalid_macho_still_records_linked_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaisesRegex(SystemExit, "not a little-endian"):
                self.execute_fixture(root, malformed=True)
            saved = json.loads((root / "run/build-provenance.json").read_text())
            artifact = saved["kernel_artifact"]
            self.assertEqual(artifact["sha256"], MODULE.sha256_file(Path(artifact["path"])))
            self.assertNotIn("__TEXT_vmaddr", artifact)

    def test_stale_manifest_is_refused_without_rebinding_or_modifying_input(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = root / "old-readback.json"
            manifest.write_text(json.dumps({"kernel_sha256": "0" * 64, "records": []}))
            original = manifest.read_bytes()
            with self.assertRaisesRegex(SystemExit, "manifest kernel_sha256"):
                self.execute_fixture(root, manifest=manifest)
            saved = json.loads((root / "run/build-provenance.json").read_text())
            self.assertEqual(saved["manifest_verification"]["status"], "failed")
            self.assertEqual(saved["manifest_verification"]["kernel_sha256"],
                             saved["kernel_artifact"]["sha256"])
            self.assertEqual(manifest.read_bytes(), original)
            self.assertEqual((root / "run/inputs/readback-manifest.json").read_bytes(), original)

    def test_matching_manifest_verification_uses_unchanged_private_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            # Obtain the deterministic fixture digest from an independent successful run.
            reference = root / "reference"
            reference.mkdir()
            provenance, _ = self.execute_fixture(reference)
            manifest = root / "readback.json"
            manifest.write_text(json.dumps({"kernel_sha256": provenance["kernel_artifact"]["sha256"]}))
            original = manifest.read_bytes()
            actual = root / "actual"
            actual.mkdir()
            provenance, gates = self.execute_fixture(actual, manifest=manifest)
            self.assertEqual(len(gates), 2)
            command = gates[-1]
            snapshot = Path(command[command.index("--manifest") + 1])
            self.assertEqual(snapshot, actual / "run/inputs/readback-manifest.json")
            self.assertEqual(snapshot.read_bytes(), original)
            self.assertEqual(manifest.read_bytes(), original)
            binding = provenance["manifest_verification"]
            self.assertEqual(binding["manifest_sha256"], MODULE.sha256_file(manifest))
            self.assertEqual(binding["kernel_sha256"], provenance["kernel_artifact"]["sha256"])
            self.assertEqual(binding["status"], "passed")

    def test_existing_run_root_is_refused_without_touching_contents(self):
        with tempfile.TemporaryDirectory() as directory:
            existing = Path(directory) / "run"
            existing.mkdir()
            marker = existing / "keep.txt"
            marker.write_text("user data")

            with self.assertRaisesRegex(SystemExit, "already exists"):
                MODULE.allocate_run_root(explicit=existing)

            self.assertEqual(marker.read_text(), "user data")

    def test_automatic_run_roots_are_unique_and_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            first = MODULE.allocate_run_root(parent=Path(directory))
            second = MODULE.allocate_run_root(parent=Path(directory))
            self.assertNotEqual(first, second)
            self.assertTrue(first.is_dir())
            self.assertTrue(second.is_dir())

    def test_explicit_run_root_cannot_be_created_inside_an_input_tree(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source"
            source.mkdir()
            destination = source / "native-run"

            with self.assertRaisesRegex(SystemExit, "overlaps build input"):
                MODULE.allocate_isolated_run_root(
                    explicit=destination, parent=None, input_paths=[source],
                )

            self.assertFalse(destination.exists())

    def test_run_parent_inside_an_input_tree_is_rejected_before_creation(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source"
            parent = source / "runs"
            parent.mkdir(parents=True)

            with self.assertRaisesRegex(SystemExit, "run parent is inside build input"):
                MODULE.allocate_isolated_run_root(
                    explicit=None, parent=parent, input_paths=[source],
                )

            self.assertEqual(list(parent.iterdir()), [])

    def test_run_parent_may_contain_an_input_when_output_is_a_sibling(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            source = parent / "source"
            source.mkdir()

            run_root = MODULE.allocate_isolated_run_root(
                explicit=None, parent=parent, input_paths=[source],
            )

            self.assertTrue(run_root.is_dir())
            self.assertFalse(run_root.is_relative_to(source))

    def test_run_root_must_not_overlap_effective_xcode_sdk_input(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sdk = root / "Xcode/SDKs/iPhoneOS.sdk"
            sdk.mkdir(parents=True)
            destination = sdk / "native-run"

            with self.assertRaisesRegex(SystemExit, "overlaps build input"):
                MODULE.allocate_isolated_run_root(
                    explicit=destination, parent=None, input_paths=[sdk],
                )

            self.assertFalse(destination.exists())

    def test_overlay_symlink_targets_are_included_as_effective_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            overlay = root / "overlay"
            sdk = root / "real-sdk"
            overlay.mkdir()
            sdk.mkdir()
            (overlay / "usr").symlink_to(sdk, target_is_directory=True)

            targets = MODULE.referenced_tree_paths([overlay])
            self.assertIn(sdk.resolve(), targets)

            with self.assertRaisesRegex(SystemExit, "overlaps build input"):
                MODULE.allocate_isolated_run_root(
                    explicit=sdk / "native-run", parent=None,
                    input_paths=[overlay, *targets],
                )

    def test_run_failure_is_persisted_as_failed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            provenance_path = root / "build-provenance.json"
            provenance = {"run_root": str(root), "status": "prepared", "steps": []}

            def fail():
                raise RuntimeError("staging failed")

            with self.assertRaisesRegex(RuntimeError, "staging failed"):
                MODULE.run_recorded(provenance_path, provenance, fail)

            import json
            recorded = json.loads(provenance_path.read_text())
            self.assertEqual(recorded["status"], "failed")
            self.assertEqual(recorded["failure"]["type"], "RuntimeError")
            self.assertEqual(recorded["failure"]["message"], "staging failed")

    def test_interrupted_run_is_persisted_as_interrupted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            provenance_path = root / "build-provenance.json"
            provenance = {"run_root": str(root), "status": "prepared", "steps": []}

            with self.assertRaises(KeyboardInterrupt):
                MODULE.run_recorded(
                    provenance_path, provenance,
                    lambda: (_ for _ in ()).throw(KeyboardInterrupt()),
                )

            import json
            recorded = json.loads(provenance_path.read_text())
            self.assertEqual(recorded["status"], "interrupted")
            self.assertEqual(recorded["failure"]["type"], "KeyboardInterrupt")

    def test_failed_to_spawn_build_step_does_not_remain_running(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            provenance = {"run_root": str(root), "steps": []}
            with mock.patch.object(MODULE.subprocess, "run", side_effect=OSError("spawn failed")):
                with self.assertRaisesRegex(OSError, "spawn failed"):
                    MODULE._run_logged(
                        "build", ["missing-tool"], cwd=root, env={},
                        log_path=root / "build.log", provenance=provenance,
                    )

            self.assertEqual(provenance["steps"][0]["status"], "failed")
            self.assertEqual(provenance["steps"][0]["error_type"], "OSError")

    def test_staging_patch_failure_records_completed_patch_and_partial_tree(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            source.mkdir()
            target = source / "file.txt"
            target.write_text("base\n")
            subprocess.run(["git", "init", "-q", str(source)], check=True)
            subprocess.run(["git", "-C", str(source), "config", "user.name", "Test"], check=True)
            subprocess.run(["git", "-C", str(source), "config", "user.email", "test@example.invalid"], check=True)
            subprocess.run(["git", "-C", str(source), "add", "file.txt"], check=True)
            subprocess.run(["git", "-C", str(source), "commit", "-qm", "fixture"], check=True)
            target.write_text("first\n")
            first_patch = root / "first.patch"
            with first_patch.open("w") as stream:
                subprocess.run(["git", "-C", str(source), "diff", "--", "file.txt"],
                               check=True, stdout=stream)
            target.write_text("base\n")
            target.write_text("second\n")
            second_patch = root / "second.patch"
            with second_patch.open("w") as stream:
                subprocess.run(["git", "-C", str(source), "diff", "--", "file.txt"],
                               check=True, stdout=stream)
            target.write_text("base\n")
            staged = root / "staged"
            progress = []

            with self.assertRaisesRegex(SystemExit, "second.patch"):
                MODULE.stage_source_tree(
                    source, staged, [first_patch, second_patch],
                    on_progress=progress.append,
                )

            self.assertEqual(progress[0]["status"], "running")
            self.assertEqual(progress[1]["status"], "copied")
            self.assertEqual(progress[2]["status"], "patch-applied")
            self.assertEqual(progress[2]["patch"]["sha256"], MODULE.sha256_file(first_patch))
            self.assertEqual(progress[3]["status"], "failed")
            self.assertEqual(progress[3]["applied_patches"][0]["sha256"],
                             MODULE.sha256_file(first_patch))
            self.assertEqual(progress[3]["partial_tree_sha256"], MODULE.tree_sha256(staged))
            self.assertEqual((staged / "file.txt").read_text(), "first\n")

    def test_tree_digest_changes_when_source_content_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            tree = Path(directory) / "source"
            tree.mkdir()
            (tree / "Makefile").write_text("first")
            first = MODULE.tree_sha256(tree)
            (tree / "Makefile").write_text("second")
            self.assertNotEqual(first, MODULE.tree_sha256(tree))

    def test_make_step_keeps_all_mutable_make_roots_inside_run_root(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "run"
            source = root / "src"
            fakeroot = root / "fakeroot"
            overlay = root / "overlay"
            command = MODULE.make_step_command(
                "build", run_root=root, source=source, fakeroot=fakeroot,
                overlay=overlay, make=Path("/xcode/make"),
                host_sdkroot=Path("/xcode/MacOSX.sdk"),
                toolchain=Path("/xcode/Toolchains/XcodeDefault.xctoolchain/usr"),
                memory_bytes=64 * 1024**3, physical_cpu_count=4,
                logical_cpu_count=8, jobs=4, host_os_version="13.7.8",
            )
            rendered = " ".join(command)
            for key in ("OBJROOT", "SYMROOT", "DSTROOT"):
                value = next(part.split("=", 1)[1] for part in command
                             if part.startswith(key + "="))
                self.assertTrue(Path(value).is_relative_to(root), (key, value, rendered))
            self.assertIn("SDKVERSION=12.4", command)
            self.assertIn("MACHINE_CONFIGS=T7001", command)
            self.assertIn("ARCH_CONFIGS=ARM64", command)
            self.assertIn("BUILD_LTO=0", command)

    def test_source_validator_requires_exact_clean_tag_and_commit(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "xnu"
            source.mkdir()
            subprocess.run(["git", "init", "-q", str(source)], check=True)
            subprocess.run(["git", "-C", str(source), "config", "user.name", "Test"], check=True)
            subprocess.run(["git", "-C", str(source), "config", "user.email", "test@example.invalid"], check=True)
            (source / "makedefs").mkdir()
            (source / "makedefs/MakeInc.def").write_text("fixture")
            subprocess.run(["git", "-C", str(source), "add", "makedefs/MakeInc.def"], check=True)
            subprocess.run(["git", "-C", str(source), "commit", "-qm", "fixture"], check=True)
            subprocess.run(["git", "-C", str(source), "tag", "xnu-4903.270.47"], check=True)
            head = subprocess.run(["git", "-C", str(source), "rev-parse", "HEAD"],
                                  check=True, capture_output=True, text=True).stdout.strip()
            identity = MODULE.validate_source_tree(
                source, expected_tag="xnu-4903.270.47", expected_commit=head,
            )
            self.assertEqual(identity["commit"], head)

            (source / "makedefs/MakeInc.def").write_text("dirty")
            with self.assertRaisesRegex(SystemExit, "not clean"):
                MODULE.validate_source_tree(
                    source, expected_tag="xnu-4903.270.47", expected_commit=head,
                )

    def test_source_patch_is_applied_to_private_copy_only(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            source.mkdir()
            subprocess.run(["git", "init", "-q", str(source)], check=True)
            subprocess.run(["git", "-C", str(source), "config", "user.name", "Test"], check=True)
            subprocess.run(["git", "-C", str(source), "config", "user.email", "test@example.invalid"], check=True)
            target = source / "osfmk/arm64/start.s"
            target.parent.mkdir(parents=True)
            target.write_text("old\n")
            subprocess.run(["git", "-C", str(source), "add", "osfmk/arm64/start.s"], check=True)
            subprocess.run(["git", "-C", str(source), "commit", "-qm", "fixture"], check=True)
            target.write_text("new\n")
            patch = root / "change.patch"
            with patch.open("w") as stream:
                subprocess.run(["git", "-C", str(source), "diff", "--", "osfmk/arm64/start.s"],
                               check=True, stdout=stream)
            target.write_text("old\n")

            staged = root / "staged"
            MODULE.stage_source_tree(source, staged, [patch])

            self.assertEqual(target.read_text(), "old\n")
            self.assertEqual((staged / "osfmk/arm64/start.s").read_text(), "new\n")


if __name__ == "__main__":
    unittest.main()
