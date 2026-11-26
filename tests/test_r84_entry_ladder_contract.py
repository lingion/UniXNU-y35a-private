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


class R84EntryLadderContractTest(unittest.TestCase):
    def _raw_pair(self, *, setter_return=True, late=True):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(root, ignore_errors=True))
        manifest = root / "readback.json"
        baseline = root / "baseline.raw"
        final = root / "final.raw"
        early_pa = 0xA000
        early_report = 0x100
        path_pa = early_pa + 64 * 8
        path_report = 0x280
        phase_pa = 0xB000
        phase_report = 0x300
        records = [
            {"name": "early-fault-record", "physical": hex(early_pa),
             "report_offset": early_report,
             "stage_offset": MODULE.RAW_STAGE_BASE_OFFSET + early_report,
             "offset": MODULE.RAW_STAGE_BASE_OFFSET + early_report,
             "size": MODULE.EARLY_RECORD_BYTES},
            {"name": "entry-path-window", "physical": hex(path_pa),
             "report_offset": path_report,
             "stage_offset": MODULE.RAW_STAGE_BASE_OFFSET + path_report,
             "offset": MODULE.RAW_STAGE_BASE_OFFSET + path_report,
             "size": MODULE.ENTRY_PATH_WINDOW_BYTES},
            {"name": "_y35a_bootstrap_phase", "physical": hex(phase_pa),
             "report_offset": phase_report,
             "stage_offset": MODULE.RAW_STAGE_BASE_OFFSET + phase_report,
             "offset": MODULE.RAW_STAGE_BASE_OFFSET + phase_report,
             "size": 16, "field_bytes": 8},
        ]
        manifest.write_text(json.dumps({
            "transport_mode": "minimal-boundary",
            "report_bytes": 0x1000,
            "records": records,
        }))
        size = MODULE.RAW_STAGE_BASE_OFFSET + 0x1000
        before = bytearray(size)
        after = bytearray(size)
        counter = MODULE.MINIMAL_FRESHNESS_WITNESS_RAW_OFFSET
        before[counter:counter + 8] = (0x10101010).to_bytes(8, "little")
        after[counter:counter + 8] = (0x20202020).to_bytes(8, "little")

        def set_word(data, offset, value):
            data[offset:offset + 8] = value.to_bytes(8, "little")

        eo = MODULE.RAW_STAGE_BASE_OFFSET + early_report
        po = MODULE.RAW_STAGE_BASE_OFFSET + path_report
        go = MODULE.RAW_STAGE_BASE_OFFSET + phase_report
        set_word(before, eo + 4 * 8, MODULE.R83_ENTRY_MARKER)
        set_word(before, eo + 5 * 8, MODULE.R83_C_ENTRY_MARKER)
        set_word(before, po, MODULE.R83_FIRST_CPU_MARKER)
        set_word(before, po + 8, MODULE.R83_FIRST_CPU_MARKER)

        set_word(after, eo + 4 * 8, MODULE.R84_ENTRY_MARKER)
        set_word(after, eo + 5 * 8, MODULE.R84_C_ENTRY_MARKER)
        set_word(after, eo + 11 * 8, MODULE.R84_SETTER_RETURN_MARKER if setter_return else 0)
        set_word(after, eo + 29 * 8, MODULE.R84_FIRST_CPU_MARKER)
        set_word(after, eo + 30 * 8, MODULE.R84_FIRST_CPU_MARKER)
        set_word(after, po, 0)
        set_word(after, po + 8, 0)
        if late:
            for name, (slot, value) in MODULE.R84_PHASE_MARKERS.items():
                if name in ("ARMINITE", "R84SET00", "R84MST00"):
                    continue
                set_word(after, eo + slot * 8, value)
        if late:
            set_word(after, eo + 13 * 8, MODULE.R84_PHASE_MARKERS["R84MST00"][1])
            set_word(after, go, MODULE.R84_LATE_PHASE)
        else:
            set_word(after, go, MODULE.R84_ARM_ENTRY_PHASE)
        baseline.write_bytes(before)
        final.write_bytes(after)
        return manifest, baseline, final

    def test_r84_markers_are_unique_from_r83(self):
        self.assertEqual(MODULE.R84_ENTRY_MARKER, int.from_bytes(b"R84ENT00", "little"))
        self.assertEqual(MODULE.R84_C_ENTRY_MARKER, int.from_bytes(b"R84CIN00", "little"))
        self.assertEqual(MODULE.R84_FIRST_CPU_MARKER, int.from_bytes(b"R84FS00\0", "little"))
        self.assertEqual(MODULE.R84_SETTER_RETURN_MARKER, int.from_bytes(b"R84SET00", "little"))
        self.assertNotEqual(MODULE.R84_ENTRY_MARKER, MODULE.R83_ENTRY_MARKER)
        self.assertNotEqual(MODULE.R84_C_ENTRY_MARKER, MODULE.R83_C_ENTRY_MARKER)

    def test_r84_arm_init_contract_orders_snapshot_setter_return_and_c_stages(self):
        def marker(name, word, slot):
            pieces = [
                f"mov x11, #{word & 0xffff:#x}",
                f"movk x11, #{(word >> 16) & 0xffff:#x}, lsl #16",
                f"movk x11, #{(word >> 32) & 0xffff:#x}, lsl #32",
                f"movk x11, #{(word >> 48) & 0xffff:#x}, lsl #48",
                f"str x11, [x8, #{0x800 + slot * 8}]",
                "dc civac, x10",
                "dsb sy",
            ]
            return pieces

        entry = ["mov x19, x0", "mov x8, x19", "add x10, x8, #2088"]
        entry += marker("ARMINITE", MODULE.R84_C_ENTRY_MARKER, 5)
        entry += [
            "ldr x12, [x19, #2560]", "ldr x13, [x19, #2568]",
            "mov x20, x19", "add x20, x20, #2048",
            "str x12, [x20, #232]!", "dc civac, x20", "dsb sy",
            "str x13, [x20, #240]!", "dc civac, x20", "dsb sy",
            "mov x0, #0x3852", "movk x0, #0x4134, lsl #16",
            "movk x0, #0x4d52, lsl #32", "movk x0, #0x3030, lsl #48",
            "bl _y35a_bootstrap_phase_set",
            "mov x11, #0x3852", "movk x11, #0x5334, lsl #16",
            "movk x11, #0x5445, lsl #32", "movk x11, #0x3030, lsl #48",
            "str x11, [x20, #88]", "dc civac, x20", "dsb sy",
        ]
        call_markers = (
            ("PEINITEN", "PE_init_platform", 6),
            ("PEINITRT", "PE_init_platform", 7),
            ("ARMVMINI", "arm_vm_init", 8),
            ("PANICINI", "panic_init", 9),
            ("CONSOLE", "PE_create_console", 10),
            ("R84MST00", None, 13),
        )
        for name, symbol, slot in call_markers:
            if name == "PEINITRT":
                entry.append(f"bl _{symbol}")
            entry += marker(name, MODULE.R84_PHASE_MARKERS[name][1], slot)
            if symbol and name != "PEINITRT":
                entry.append(f"bl _{symbol}")
        entry += [
            "mov x0, #0x3852", "movk x0, #0x4c34, lsl #16",
            "movk x0, #0x5441, lsl #32", "movk x0, #0x3045, lsl #48",
            "bl _y35a_bootstrap_phase_set",
        ]
        self.assertEqual(
            MODULE.verify_r84_arm_init_progress("\n".join(entry), required=True), []
        )

    def test_r84_raw_decode_reports_c_entry_snapshots_and_late_progress(self):
        manifest, baseline, final = self._raw_pair()
        result = MODULE.decode_r84_entry_ladder(final, manifest, baseline)
        self.assertEqual(result["progress"], "arm-init-late-phase")
        self.assertTrue(result["markers"]["entry"]["fresh"])
        self.assertTrue(result["markers"]["c_entry"]["fresh"])
        self.assertTrue(result["markers"]["setter_return"]["fresh"])
        self.assertTrue(result["snapshot_at_c_entry"]["pair_matches_first_cpu"])
        self.assertEqual(result["markers"]["first_cpu_roundtrip"]["status"], "incomplete")
        self.assertTrue(result["markers"]["CONSOLE"]["fresh"])
        self.assertTrue(result["markers"]["phase_cursor"]["fresh"])

    def test_r84_raw_decode_locates_setter_return_before_later_c_stages(self):
        manifest, baseline, final = self._raw_pair(setter_return=True, late=False)
        result = MODULE.decode_r84_entry_ladder(final, manifest, baseline)
        self.assertEqual(result["progress"], "arm-init-phase-setter-return")
        self.assertTrue(result["markers"]["setter_return"]["fresh"])
        self.assertFalse(result["markers"]["CONSOLE"]["fresh"])
        self.assertEqual(result["markers"]["phase_cursor"]["stage"], "R84ARM00")

    def test_r84_raw_decode_does_not_claim_setter_return_from_c_entry_alone(self):
        manifest, baseline, final = self._raw_pair(setter_return=False, late=False)
        result = MODULE.decode_r84_entry_ladder(final, manifest, baseline)
        self.assertEqual(result["progress"], "arm-init-phase-setter-published")
        self.assertFalse(result["markers"]["setter_return"]["fresh"])


if __name__ == "__main__":
    unittest.main()
