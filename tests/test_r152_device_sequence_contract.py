import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PHASE = (ROOT / "evidence/y35a-20261102/boot3-20261106/"
         "phase-r152-secure-root-global-fallback-20261115")
SCRIPT = PHASE / "device-sequence-r152.py"
SPEC = importlib.util.spec_from_file_location("device_sequence_r152", SCRIPT)
DEVICE_SEQUENCE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = DEVICE_SEQUENCE
SPEC.loader.exec_module(DEVICE_SEQUENCE)


def raw_with_slots(*, stamp_prefix, slot_values, cntvct):
    raw = bytearray(DEVICE_SEQUENCE.RAW_BYTES)
    raw[:8] = DEVICE_SEQUENCE.RAW_MAGIC
    raw[8:16] = bytes.fromhex(DEVICE_SEQUENCE.EXPECTED_KERNEL)[:8]
    raw[16:24] = cntvct.to_bytes(8, "little")

    stamp_offset = 0xF900
    stamp = DEVICE_SEQUENCE.SHIM_MAGIC + stamp_prefix + bytes(64 - 16)
    raw[stamp_offset:stamp_offset + len(stamp)] = stamp
    raw[0x10000:0x10000 + len(stamp)] = stamp

    record_offset = 64
    for slot, codeword in slot_values.items():
        value = int.from_bytes(codeword.encode("ascii"), "little")
        start = record_offset + slot * 8
        raw[start:start + 8] = value.to_bytes(8, "little")
    return bytes(raw)


class R152DeviceSequenceContract(unittest.TestCase):
    def test_pre_run_baseline_from_r151_is_accepted_but_not_bound_to_r152(self):
        previous_kernel_prefix = bytes.fromhex(
            "3205ec91f46c66e5")
        raw = raw_with_slots(
            stamp_prefix=previous_kernel_prefix,
            slot_values={17: "OLDREG00", 18: "OLDSEL00", 19: "OLDRET00"},
            cntvct=1,
        )
        decoded = DEVICE_SEQUENCE.decode_bytes(raw, self.manifest(), False)
        self.assertEqual(decoded["shim_kernel_prefix"], previous_kernel_prefix.hex())
        self.assertFalse(decoded["shim_binds_r152"])

    def test_fresh_r152_fallback_result_is_classified_without_guessing_status(self):
        baseline = {"slot17": "OLDREG00", "slot18": "OLDSEL00", "slot19": "OLDRET00"}
        final = {"slot17": "R152REG0", "slot18": "R152GPLO", "slot19": "R152SOTH"}
        fresh = DEVICE_SEQUENCE.r152_freshness(baseline, final)
        self.assertTrue(fresh["17"]["fresh"])
        self.assertTrue(fresh["18"]["fresh"])
        self.assertTrue(fresh["19"]["fresh"])
        self.assertEqual(
            DEVICE_SEQUENCE.secure_root_outcome(final, fresh),
            "global_platform_secure_root_returned_other_status",
        )
        self.assertNotIn("unsupported", DEVICE_SEQUENCE.secure_root_outcome(final, fresh))

    def test_missing_fresh_register_or_platform_selection_marker_stops_capture(self):
        cases = (
            ({"slot17": "R152REG0", "slot18": "R152GPLO", "slot19": "OLDRET00"},
             {"slot17": "R152REG0", "slot18": "R152GPLO", "slot19": "R152SOTH"}),
            ({"slot17": "OLDREG00", "slot18": "OLDSEL00", "slot19": "OLDRET00"},
             {"slot17": "OLDREG00", "slot18": "R152GPLO", "slot19": "R152SOTH"}),
        )
        for baseline, final in cases:
            with self.subTest(baseline=baseline):
                with self.assertRaises(DEVICE_SEQUENCE.StopExperiment):
                    DEVICE_SEQUENCE.r152_freshness(baseline, final)

    def test_null_platform_and_unretained_return_are_distinct_outcomes(self):
        baseline = {"slot17": "OLDREG00", "slot18": "OLDSEL00", "slot19": "OLDRET00"}
        null_final = {"slot17": "R152REG0", "slot18": "R152GNUL", "slot19": "OLDRET00"}
        null_fresh = DEVICE_SEQUENCE.r152_freshness(baseline, null_final)
        self.assertEqual(
            DEVICE_SEQUENCE.secure_root_outcome(null_final, null_fresh),
            "global_platform_null_before_secure_root_call",
        )

        other_final = {"slot17": "R152REG0", "slot18": "R152GPLO", "slot19": "OLDRET00"}
        other_fresh = DEVICE_SEQUENCE.r152_freshness(baseline, other_final)
        self.assertEqual(
            DEVICE_SEQUENCE.secure_root_outcome(other_final, other_fresh),
            "global_platform_selected_without_retained_result",
        )

    def test_r151_slot19_is_reported_as_superseded_by_r152_not_absent(self):
        baseline = {"slot19": "R151NUL0"}
        final = {"slot19": "R152SOTH"}
        decoded = DEVICE_SEQUENCE.r151_freshness(baseline, final)
        self.assertIsNone(decoded["19"]["fresh"])
        self.assertEqual(decoded["19"]["status"], "superseded_by_r152")

    def test_retained_r151_marker_still_reports_fresh_when_not_overwritten(self):
        baseline = {"slot19": "OLDRET00"}
        final = {"slot19": "R151NUL0"}
        decoded = DEVICE_SEQUENCE.r151_freshness(baseline, final)
        self.assertTrue(decoded["19"]["fresh"])
        self.assertEqual(decoded["19"]["status"], "fresh_r151_marker")

    @staticmethod
    def manifest():
        return {
            "stamp_snapshot_offset": 0xF900,
            "stamp_snapshot_bytes": 64,
            "panic_log_offset": 0x10000,
            "panic_log_limit": 0x1000,
            "records": [
                {"name": "early-fault-record", "offset": 64},
                {"name": "_smsg_bufc", "offset": 992, "size": 0xD000},
            ],
        }


if __name__ == "__main__":
    unittest.main()
