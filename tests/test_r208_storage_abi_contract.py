from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "compile_r208_sdcard", ROOT / "scripts/ci/compile_r208_sdcard.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class R208StorageAbiContractTests(unittest.TestCase):
    def test_embedded_abi_probe_requires_matching_padding_and_alignment(self):
        source = MODULE.embedded_kext_abi_probe_source()
        self.assertIn("CONFIG_EMBEDDED != 1", source)
        self.assertIn("APPLE_KEXT_VTABLE_PADDING == 0", source)
        self.assertIn("APPLE_KEXT_ALIGN_CONTAINERS == 1", source)

    def test_embedded_abi_gate_rejects_missing_config_define(self):
        with self.assertRaisesRegex(SystemExit, "requires CONFIG_EMBEDDED=1"):
            MODULE.verify_embedded_kext_abi(["clang++", "-I", "/xnu/libkern"], env={})

    def test_embedded_abi_probe_rejects_mismatched_preprocessor_contract(self):
        with mock.patch.object(MODULE.subprocess, "run") as run_mock:
            run_mock.return_value.returncode = 1
            run_mock.return_value.stdout = ""
            run_mock.return_value.stderr = "static assertion failed"
            with self.assertRaisesRegex(SystemExit, "embedded XNU KEXT ABI"):
                MODULE.verify_embedded_kext_abi(
                    ["clang++", "-DCONFIG_EMBEDDED=1", "-I", "/xnu/libkern"], env={})

    def test_archive_gate_rejects_reserved_virtual_slot_imports(self):
        with mock.patch.object(MODULE, "run", return_value="U __ZN9IOService22_RESERVEDIOService33Ev\n"):
            with self.assertRaisesRegex(SystemExit, "reserved ABI slot"):
                MODULE.reject_reserved_abi_imports(Path("libQcomSdcard.a"), env={})

    def test_archive_gate_accepts_clean_embedded_vtable_imports(self):
        with mock.patch.object(MODULE, "run", return_value="U _kernel_log\n"):
            result = MODULE.reject_reserved_abi_imports(Path("libQcomSdcard.a"), env={})
        self.assertEqual(result, {"status": "passed", "reserved_abi_imports": []})


if __name__ == "__main__":
    unittest.main()
