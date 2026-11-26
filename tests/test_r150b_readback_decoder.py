import importlib.util
import unittest
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "evidence/y35a-20261102/boot3-20261106/phase-r150b-platform-fallback-root-20261115/device-sequence-r150b.py"
)
SPEC = importlib.util.spec_from_file_location("device_sequence_r150b", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class R150bReadbackDecoderTest(unittest.TestCase):
    def test_uses_manifest_stamp_snapshot_and_reports_current_smsg_panic(self):
        raw = bytearray(MODULE.RAW_BYTES)
        raw[:8] = MODULE.RAW_MAGIC
        raw[8:16] = bytes.fromhex(MODULE.EXPECTED_KERNEL)[:8]
        stamp_offset = 0xF900
        stamp = MODULE.SHIM_MAGIC + bytes.fromhex(MODULE.EXPECTED_KERNEL)[:8] + bytes(48)
        raw[stamp_offset:stamp_offset + 64] = stamp
        raw[0x10000:0x10040] = stamp
        panic = (
            b"Darwin Kernel Version 18.7.0: R150B\n"
            b"panic(cpu 0 caller 0xfffffff007131dac): IOKitBSDInit.cpp:745 Assertion failed: pe\n"
        )
        smsg_offset = 0x3E0
        raw[smsg_offset:smsg_offset + len(panic)] = panic
        manifest = {
            "stamp_snapshot_offset": stamp_offset,
            "stamp_snapshot_bytes": 64,
            "panic_log_offset": 0x10000,
            "panic_log_limit": 0x1000,
            "records": [
                {"name": "early-fault-record", "offset": 0x40, "size": 384},
                {"name": "_smsg_bufc", "offset": smsg_offset, "size": 0xD000},
            ],
        }
        result = MODULE.decode_bytes(bytes(raw), manifest, final=False)

        self.assertEqual(result["shim_stamp_snapshot_offset"], "0xf900")
        self.assertTrue(result["panic_log_header_matches_stamp_snapshot"])
        self.assertEqual(result["smsg_bufc_panic_callers"], ["0xfffffff007131dac"])
        self.assertIn("Assertion failed: pe", result["smsg_bufc_last_panic_excerpt"])


if __name__ == "__main__":
    unittest.main()
