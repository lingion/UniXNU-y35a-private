import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/y35a"))
SPEC = importlib.util.spec_from_file_location(
    "verify_phase_instrumentation",
    ROOT / "scripts/y35a/verify_phase_instrumentation.py",
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class R83EntryLadderContractTest(unittest.TestCase):
    def _manifest_and_raw_pair(self, *, terminal=False, stale=False):
        root = Path(tempfile.mkdtemp())
        manifest_path = root / "readback.json"
        baseline_path = root / "baseline.raw"
        final_path = root / "final.raw"
        early_physical = 0xA000
        early_report_offset = 0x100
        entry_physical = early_physical + 64 * 8
        entry_report_offset = 0x280
        phase_physical = 0xB000
        phase_report_offset = 0x300
        records = [
            {"name": "early-fault-record", "physical": hex(early_physical),
             "report_offset": early_report_offset,
             "stage_offset": MODULE.RAW_STAGE_BASE_OFFSET + early_report_offset,
             "offset": MODULE.RAW_STAGE_BASE_OFFSET + early_report_offset,
             "size": MODULE.EARLY_RECORD_BYTES},
            {"name": "entry-path-window", "physical": hex(entry_physical),
             "report_offset": entry_report_offset,
             "stage_offset": MODULE.RAW_STAGE_BASE_OFFSET + entry_report_offset,
             "offset": MODULE.RAW_STAGE_BASE_OFFSET + entry_report_offset,
             "size": MODULE.ENTRY_PATH_WINDOW_BYTES},
            {"name": "_y35a_bootstrap_phase", "physical": hex(phase_physical),
             "report_offset": phase_report_offset,
             "stage_offset": MODULE.RAW_STAGE_BASE_OFFSET + phase_report_offset,
             "offset": MODULE.RAW_STAGE_BASE_OFFSET + phase_report_offset,
             "size": 16, "field_bytes": 8},
        ]
        manifest_path.write_text(json.dumps({
            "transport_mode": "minimal-boundary",
            "report_bytes": 0x1000,
            "records": records,
        }))
        baseline = bytearray(MODULE.RAW_STAGE_BASE_OFFSET + 0x1000)
        final = bytearray(len(baseline))
        counter = MODULE.MINIMAL_FRESHNESS_WITNESS_RAW_OFFSET
        baseline[counter:counter + 8] = (
                     0x11111111).to_bytes(8, "little")
        final[counter:counter + 8] = (
                  0x22222222).to_bytes(8, "little")

        def write_word(data, offset, value):
            data[offset:offset + 8] = value.to_bytes(8, "little")

        early_offset = MODULE.RAW_STAGE_BASE_OFFSET + early_report_offset
        entry_offset = MODULE.RAW_STAGE_BASE_OFFSET + entry_report_offset
        phase_offset = MODULE.RAW_STAGE_BASE_OFFSET + phase_report_offset
        if stale:
            for data in (baseline, final):
                write_word(data, early_offset + 4 * 8, MODULE.R83_ENTRY_MARKER)
                write_word(data, early_offset + 5 * 8, MODULE.R83_C_ENTRY_MARKER)
                write_word(data, entry_offset, MODULE.R83_FIRST_CPU_MARKER)
                write_word(data, entry_offset + 8, MODULE.R83_FIRST_CPU_MARKER)
                write_word(data, phase_offset, MODULE.R82_ARM_ENTRY_PHASE)
        else:
            write_word(final, early_offset + 4 * 8, MODULE.R83_ENTRY_MARKER)
            write_word(final, early_offset + 5 * 8, MODULE.R83_C_ENTRY_MARKER)
            write_word(final, entry_offset, MODULE.R83_FIRST_CPU_MARKER)
            write_word(final, entry_offset + 8, MODULE.R83_FIRST_CPU_MARKER)
            write_word(final, phase_offset, MODULE.R82_ARM_ENTRY_PHASE)
        if terminal:
            write_word(final, early_offset, int.from_bytes(b"Y35ALV07", "little"))
            write_word(final, early_offset + 4 * 8, 0x123456789ABCDEF0)
        baseline_path.write_bytes(baseline)
        final_path.write_bytes(final)
        return manifest_path, baseline_path, final_path, early_offset

    def test_r83_marker_words_have_exact_little_endian_encoding(self):
        self.assertEqual(MODULE.R83_ENTRY_MARKER, int.from_bytes(b"R83ENT00", "little"))
        self.assertEqual(MODULE.R83_C_ENTRY_MARKER, int.from_bytes(b"R83CIN00", "little"))
        self.assertEqual(MODULE.R83_FIRST_CPU_MARKER, int.from_bytes(b"R83FS00\0", "little"))
        self.assertNotEqual(MODULE.R83_FIRST_CPU_MARKER, int.from_bytes(b"R83FS000", "little"))

    def test_r83_arm_init_marker_store_and_clean_precede_phase_setter(self):
        entry = [
            "mov x19, x0",
            "mov x8, x19",
            "add x10, x8, #2088",
            "mov x11, #0x3852",
            "movk x11, #0x4333, lsl #16",
            "movk x11, #0x4e49, lsl #32",
            "movk x11, #0x3030, lsl #48",
            "str x11, [x8, #2088]",
            "dc civac, x10",
            "dsb sy",
            "mov x0, #0x3852",
            "movk x0, #0x4132, lsl #16",
            "movk x0, #0x4d52, lsl #32",
            "movk x0, #0x3030, lsl #48",
            "bl _y35a_bootstrap_phase_set",
        ]
        self.assertEqual(
            MODULE.verify_r83_arm_init_cursor("\n".join(entry), required=True), []
        )
        marker_first = "\n".join([*entry[9:], *entry[:9]])
        self.assertTrue(MODULE.verify_r83_arm_init_cursor(marker_first, required=True))
        missing_clean = "\n".join([*entry[:8], *entry[9:]])
        self.assertTrue(MODULE.verify_r83_arm_init_cursor(missing_clean, required=True))

    def test_cbz_cbnz_target_decoder_uses_pc_relative_signed_immediate(self):
        self.assertEqual(MODULE._decode_cbz_target(0xB5000068, 0x1000), 0x100C)
        self.assertIsNone(MODULE._decode_cbz_target(0xD503201F, 0x1000))

    def test_r83_raw_decode_uses_named_discontiguous_records_and_freshness(self):
        manifest, baseline, final, _ = self._manifest_and_raw_pair()
        result = MODULE.decode_r83_entry_ladder(final, manifest, baseline)
        self.assertTrue(result["markers"]["entry"]["fresh"])
        self.assertTrue(result["markers"]["c_entry"]["fresh"])
        self.assertTrue(result["markers"]["first_cpu_store"]["fresh"])
        self.assertTrue(result["markers"]["first_cpu_loadback"]["fresh"])
        self.assertTrue(result["markers"]["first_cpu_roundtrip"]["fresh"])
        self.assertTrue(result["markers"]["phase_cursor"]["fresh"])
        self.assertEqual(result["progress"], "arm-init-phase-setter")

    def test_r83_raw_decode_does_not_call_unchanged_words_fresh(self):
        manifest, baseline, final, _ = self._manifest_and_raw_pair(stale=True)
        result = MODULE.decode_r83_entry_ladder(final, manifest, baseline)
        for marker in ("entry", "c_entry", "first_cpu_store", "first_cpu_loadback", "phase_cursor"):
            with self.subTest(marker=marker):
                self.assertFalse(result["markers"][marker]["fresh"])

    def test_fresh_terminal_v7_takes_slot4_ownership_without_entry_success_claim(self):
        manifest, baseline, final, _ = self._manifest_and_raw_pair(terminal=True)
        result = MODULE.decode_r83_entry_ladder(final, manifest, baseline)
        self.assertEqual(result["markers"]["entry"]["status"], "overwritten-by-terminal-v7")
        self.assertTrue(result["terminal"]["fresh"])
        self.assertNotEqual(result["progress"], "start-first-cpu-entry")

    def test_slot4_only_change_cannot_make_repeated_terminal_flag_fresh(self):
        manifest, baseline, final, early_offset = self._manifest_and_raw_pair(
            terminal=True, stale=True
        )
        terminal_word = int.from_bytes(b"Y35ALV07", "little").to_bytes(8, "little")
        before = bytearray(baseline.read_bytes())
        after = bytearray(final.read_bytes())
        before[early_offset:early_offset + 8] = terminal_word
        after[early_offset:early_offset + 8] = terminal_word
        before[early_offset + 8:early_offset + 32] = bytes(24)
        after[early_offset + 8:early_offset + 32] = bytes(24)
        baseline.write_bytes(before)
        final.write_bytes(after)
        result = MODULE.decode_r83_entry_ladder(final, manifest, baseline)
        self.assertFalse(result["terminal"]["fresh"])
        self.assertEqual(result["progress"], "terminal-v7-freshness-unproven")

    def test_r83_capture_integrity_accepts_a_valid_early_stop_and_rejects_replayed_probe(self):
        manifest, baseline, final, _ = self._manifest_and_raw_pair()
        self.assertEqual(MODULE.verify_r83_capture(final, manifest, baseline), [])
        data = bytearray(final.read_bytes())
        counter = MODULE.MINIMAL_FRESHNESS_WITNESS_RAW_OFFSET
        before = baseline.read_bytes()[counter:counter + 8]
        data[counter:counter + 8] = before
        final.write_bytes(data)
        self.assertTrue(any(
            "CNTVCT witnesses are not distinct" in failure
            for failure in MODULE.verify_r83_capture(final, manifest, baseline)
        ))

    def test_r83_capture_integrity_does_not_require_progress_markers(self):
        manifest, baseline, final, _ = self._manifest_and_raw_pair()
        raw = bytearray(final.read_bytes())
        raw[0x10100:0x10100 + MODULE.EARLY_RECORD_BYTES] = bytes(MODULE.EARLY_RECORD_BYTES)
        raw[0x10280:0x10290] = bytes(MODULE.ENTRY_PATH_WINDOW_BYTES)
        raw[0x10300:0x10310] = bytes(16)
        final.write_bytes(raw)
        self.assertEqual(MODULE.verify_r83_capture(final, manifest, baseline), [])
        self.assertEqual(
            MODULE.decode_r83_entry_ladder(final, manifest, baseline)["progress"],
            "no-fresh-r83-marker-observed",
        )

    def test_terminal_slot4_freshness_is_reported_as_terminal_ownership(self):
        manifest, baseline, final, _ = self._manifest_and_raw_pair(terminal=True)
        result = MODULE.verify_fresh_generation_markers(final, baseline, manifest)
        marker = result["markers"]["ARMENTRY"]
        self.assertFalse(marker["fresh"])
        self.assertEqual(
            marker["entry_freshness"],
            "unobservable-slot4-owned-by-terminal-link-register",
        )
        self.assertTrue(marker["terminal_record_freshness"]["fresh"])
        self.assertFalse(any("final ARMENTRY is not fresh" in failure
                             for failure in result["failures"]))

    def test_explicit_r82_contract_rejects_r83_instead_of_auto_switching(self):
        entry = "\n".join([
            "mov x19, x0", "mov x8, x19", "add x10, x8, #2088",
            "mov x11, #0x3852", "movk x11, #0x4333, lsl #16",
            "movk x11, #0x4e49, lsl #32", "movk x11, #0x3030, lsl #48",
            "str x11, [x8, #2088]", "dc civac, x10", "dsb sy",
            "mov x0, #0x3852", "movk x0, #0x4132, lsl #16",
            "movk x0, #0x4d52, lsl #32", "movk x0, #0x3030, lsl #48",
            "bl _y35a_bootstrap_phase_set",
        ])
        failures = MODULE.verify_disassembly(entry, require_r82_cursor=True)
        self.assertIn(
            "R82 arm-init contract cannot use the R83CIN00 slot-5 marker",
            failures,
        )


if __name__ == "__main__":
    unittest.main()
