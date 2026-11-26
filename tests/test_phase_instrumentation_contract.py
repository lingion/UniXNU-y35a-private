#!/usr/bin/env python3
import importlib.util
import json
import sys
import tempfile
from pathlib import Path
from unittest import mock
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


class PhaseInstrumentationContractTest(unittest.TestCase):
    def test_r82_arm_init_entry_cursor_is_a_fresh_decodable_stage(self):
        marker = int.from_bytes(b"R82ARM00", "little")

        self.assertEqual(MODULE.Y35A_BOOTSTRAP_PHASES.get(marker), "R82ARM00")
        self.assertEqual(MODULE.classify_y35a_bootstrap_phase(marker, 0), "fresh")

    def test_r82_arm_cursor_is_bound_before_the_arminite_carrier_store(self):
        entry = [
            "mov x19, x0",
            "mov x8, #0x3852",
            "movk x8, #0x4131, lsl #16",
            "movk x8, #0x4d52, lsl #32",
            "movk x8, #0x3030, lsl #48",
            "str xzr, [sp, #24]",
            "add x0, x8, #16, lsl #12",
            "bl _y35a_bootstrap_phase_set",
        ]
        arminite = [
            "mov x8, x19",
            "add x9, x8, #2088",
            "mov x10, #0x5445",
            "movk x10, #0x4e49, lsl #16",
            "movk x10, #0x4d49, lsl #32",
            "movk x10, #0x4152, lsl #48",
            "str x10, [x8, #2088]",
            "dc civac, x9",
            "dsb sy",
        ]
        valid = "\n".join([*entry, *arminite])

        self.assertEqual(MODULE.verify_r82_arm_init_cursor(valid, required=True), [])

        marker_first = "\n".join([*arminite, *entry])
        self.assertIn(
            "R82ARM00 cursor must precede the ARMINITE carrier store",
            MODULE.verify_r82_arm_init_cursor(marker_first, required=True),
        )

        wrong_stage = "\n".join([
            "mov x0, #0x3852",
            "movk x0, #0x4145, lsl #16",
            "movk x0, #0x5238, lsl #32",
            "movk x0, #0x3030, lsl #48",
            "bl _y35a_bootstrap_phase_set",
            *arminite,
        ])
        self.assertIn(
            "missing or duplicate R82ARM00 phase-set call",
            MODULE.verify_r82_arm_init_cursor(wrong_stage, required=True),
        )

        for clobber in (
            "eor x0, x0, x0",
            "mov w0, #0",
            "ldr x0, [x19]",
        ):
            with self.subTest(clobber=clobber):
                clobbered = "\n".join([*entry[:-1], clobber, entry[-1], *arminite])
                self.assertIn(
                    "missing or duplicate R82ARM00 phase-set call",
                    MODULE.verify_r82_arm_init_cursor(clobbered, required=True),
                )

        bypass = "\n".join([*entry[:1], "b skip_cursor", *entry[1:], *arminite])
        self.assertIn(
            "branch can bypass R82ARM00 phase-set call",
            MODULE.verify_r82_arm_init_cursor(bypass, required=True),
        )

        indirect_call = "\n".join([*entry[:1], "blr x20", *entry[1:], *arminite])
        self.assertIn(
            "R82ARM00 setter is not the first arm_init call",
            MODULE.verify_r82_arm_init_cursor(indirect_call, required=True),
        )

        wrong_carrier = "\n".join([*entry, *arminite[:-3],
                                    "str x10, [x0, #2088]", *arminite[-2:]])
        self.assertIn(
            "ARMINITE slot-5 store is not based on the incoming boot_args pointer",
            MODULE.verify_r82_arm_init_cursor(wrong_carrier, required=True),
        )

        copied_arg = "\n".join([
            "mov x19, x0",
            "mov x8, #0x3852",
            "movk x8, #0x4131, lsl #16",
            "movk x8, #0x4d52, lsl #32",
            "movk x8, #0x3030, lsl #48",
            "add x8, x8, #16, lsl #12",
            "mov x0, x8",
            "bl _y35a_bootstrap_phase_set",
            *arminite,
        ])
        self.assertEqual(MODULE.verify_r82_arm_init_cursor(copied_arg, required=True), [])

    def test_r82_phase_setter_must_store_the_named_global_and_clean_it(self):
        body = "\n".join([
            "_y35a_bootstrap_phase_set:",
            "adrp x8, 1320 ; 0xfffffff00776a000",
            "add x8, x8, #1864",
            "str x0, [x8]",
            "dc cvac, x8",
            "dsb sy",
            "ret",
        ])
        self.assertEqual(
            MODULE.verify_r82_phase_setter(body, 0xfffffff00776a748), []
        )
        self.assertTrue(
            MODULE.verify_r82_phase_setter("ret", 0xfffffff00776a748)
        )

    def test_first_cpu_witness_rejects_wrong_half_even_when_later_spoof_completes_marker(self):
        marker = MODULE.ENTRY_PATH_MARKERS["FIRST_CPU"][1]
        expected = [
            f"mov x15, #{marker & 0xffff:#x}",
            f"movk x15, #{(marker >> 16) & 0xffff:#x}, lsl #16",
            f"movk x15, #{(marker >> 32) & 0xffff:#x}, lsl #32",
            f"movk x15, #{(marker >> 48) & 0xffff:#x}, lsl #48",
        ]
        store = "str x15, [x20, #0xa00]"
        after_store = [
            "add x14, x20, #0xa00",
            "dsb sy",
            "dc civac, x14",
            "dsb sy",
            "ldr x16, [x20, #0xa00]",
            "str x16, [x20, #0xa08]",
            "add x14, x20, #0xa08",
            "dsb sy",
            "dc civac, x14",
            "dsb sy",
        ]
        body = "\n".join([
            "msr VBAR_EL1, x0",
            *expected[:3],
            "movk x15, #0x0030, lsl #48",  # stale/wrong high half at the real store
            store,
            expected[3],  # a later correct half must not retroactively validate the store
            *after_store,
        ])

        # A function-wide scatter search sees every expected instruction and
        # would accept this body; the witness must bind all four halves to the
        # immediately following slot64 store.
        self.assertTrue(all(instruction in body for instruction in expected))
        self.assertLess(body.index("movk x15, #0x0030, lsl #48"), body.index(store))
        self.assertGreater(body.index(expected[3]), body.index(store))
        failures = MODULE.verify_first_cpu_path_witness(body)
        self.assertIn(
            "R68E7FS0 must be fully materialized immediately before slot64 store",
            failures,
        )

        valid_body = "\n".join([
            "msr VBAR_EL1, x0",
            *expected,
            store,
            *after_store,
        ])
        self.assertEqual(MODULE.verify_first_cpu_path_witness(valid_body), [])

    def test_first_cpu_witness_rejects_intervening_instruction_before_slot64_store(self):
        body = "\n".join([
            "msr VBAR_EL1, x0",
            "mov x15, #0x3652",
            "movk x15, #0x4538, lsl #16",
            "movk x15, #0x4637, lsl #32",
            "nop",
            "movk x15, #0x3053, lsl #48",
            "str x15, [x20, #0xa00]",
            "add x14, x20, #0xa00",
            "dsb sy",
            "dc civac, x14",
            "dsb sy",
            "ldr x16, [x20, #0xa00]",
            "str x16, [x20, #0xa08]",
            "add x14, x20, #0xa08",
            "dsb sy",
            "dc civac, x14",
            "dsb sy",
        ])

        # All expected halves exist in the function slice, but they are not an
        # adjacent codeword immediately before the store.
        self.assertTrue(all(instruction in body for instruction in (
            "mov x15, #0x3652",
            "movk x15, #0x4538, lsl #16",
            "movk x15, #0x4637, lsl #32",
            "movk x15, #0x3053, lsl #48",
        )))
        self.assertLess(body.index("nop"), body.index("movk x15, #0x3053, lsl #48"))
        self.assertLess(body.index("movk x15, #0x3053, lsl #48"),
                        body.index("str x15, [x20, #0xa00]"))
        self.assertIn(
            "R68E7FS0 must be fully materialized immediately before slot64 store",
            MODULE.verify_first_cpu_path_witness(body),
        )

    def test_entry_witness_rejects_late_halfword_spoof_and_branch_bypass(self):
        value = MODULE.ENTRY_MARKER
        halves = [(value >> shift) & 0xffff for shift in (0, 16, 32, 48)]
        valid = "\n".join([
            "add x16, x20, #0x820",
            f"mov x15, #{halves[0]}",
            f"movk x15, #{halves[1]}, lsl #16",
            f"movk x15, #{halves[2]}, lsl #32",
            f"movk x15, #{halves[3]}, lsl #48",
            "str x15, [x16]",
        ])
        self.assertEqual(MODULE.verify_entry_witness(valid), [])
        spoof = valid.replace(f"movk x15, #{halves[3]}, lsl #48",
                              "movk x15, #48, lsl #48", 1)
        spoof += f"\nmovk x15, #{halves[3]}, lsl #48"
        self.assertTrue(MODULE.verify_entry_witness(spoof))
        bypass = valid.replace("str x15, [x16]", "b .Lskip\nstr x15, [x16]", 1)
        self.assertTrue(MODULE.verify_entry_witness(bypass))
        prefix_bypass = "b .Lafter_entry\n" + valid + "\n.Lafter_entry:"
        self.assertTrue(MODULE.verify_entry_witness(prefix_bypass))

    def test_slot64_witness_rejects_branch_before_current_generation_store(self):
        body = "\n".join([
            "msr VBAR_EL1, x0",
            "b .Lskip",
            "mov x15, #0x3652",
            "movk x15, #0x4538, lsl #16",
            "movk x15, #0x4636, lsl #32",
            "movk x15, #0x3053, lsl #48",
            "str x15, [x20, #0xa00]",
            "add x14, x20, #0xa00",
            "dc civac, x14",
            "dsb sy",
            "ldr x16, [x20, #0xa00]",
            "str x16, [x20, #0xa08]",
            "add x14, x20, #0xa08",
            "dc civac, x14",
            "dsb sy",
        ])
        self.assertTrue(any("immediately follow early VBAR_EL1" in failure
                            for failure in MODULE.verify_first_cpu_path_witness(body)))

    def test_generation_freshness_compares_final_markers_to_baseline(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = {
                "transport_mode": "minimal-boundary",
                "records": [{
                    "name": "early-fault-record", "physical": "0x1000",
                    "size": 384, "report_offset": 0x100,
                }, {
                    "name": "handoff-witness", "physical": "0x11c0",
                    "size": 16, "report_offset": 0x280,
                }, {
                    "name": "fault-publish-window", "physical": "0x11d0",
                    "size": 48, "report_offset": 0x280,
                }, {
                    "name": "entry-path-window", "physical": "0x1200",
                    "size": 16, "report_offset": 0x2B0,
                }],
            }
            baseline = bytearray(0x11000)
            final = bytearray(0x11000)
            carrier = MODULE.RAW_STAGE_BASE_OFFSET + 0x100
            final[carrier + 4 * 8:carrier + 5 * 8] = MODULE.ENTRY_MARKER.to_bytes(8, "little")
            final[carrier + 16 * 8:carrier + 17 * 8] = \
                MODULE.HANDOFF_MARKERS["PREMMU00"][1].to_bytes(8, "little")
            final[carrier + 43 * 8:carrier + 44 * 8] = \
                MODULE.HANDOFF_MARKERS["FPBEFOR0"][1].to_bytes(8, "little")
            final[carrier + 44 * 8:carrier + 45 * 8] = \
                MODULE.HANDOFF_MARKERS["FPSTOR00"][1].to_bytes(8, "little")
            handoff = MODULE.RAW_STAGE_BASE_OFFSET + 0x280
            final[handoff:handoff + 8] = MODULE.HANDOFF_MARKERS["SCTLRRD0"][1].to_bytes(8, "little")
            final[handoff + 8:handoff + 16] = (1).to_bytes(8, "little")
            publish = MODULE.RAW_STAGE_BASE_OFFSET + 0x280
            final[publish + 24:publish + 32] = \
                MODULE.HANDOFF_MARKERS["PUBLPR00"][1].to_bytes(8, "little")
            final[publish + 32:publish + 40] = \
                MODULE.HANDOFF_MARKERS["PUBLPS00"][1].to_bytes(8, "little")
            baseline_path = root / "baseline.raw"
            final_path = root / "final.raw"
            manifest_path = root / "readback.json"
            baseline_path.write_bytes(baseline)
            final_path.write_bytes(final)
            manifest_path.write_text(json.dumps(manifest))

            result = MODULE.verify_fresh_generation_markers(final_path, baseline_path, manifest_path)
            self.assertEqual(result["failures"], [])
            self.assertTrue(result["markers"]["ARMENTRY"]["fresh"])
            self.assertTrue(result["markers"]["PREMMU00"]["fresh"])
            self.assertTrue(result["markers"]["SCTLRRD0"]["fresh"])
            self.assertTrue(result["markers"]["FPBEFOR0"]["fresh"])
            self.assertTrue(result["markers"]["FPSTOR00"]["fresh"])
            self.assertTrue(result["markers"]["PUBLPR00"]["fresh"])
            self.assertTrue(result["markers"]["PUBLPS00"]["fresh"])
            self.assertEqual(result["markers"]["FIRST_CPU"]["final_status"], "zero")

            baseline[carrier + 16 * 8:carrier + 17 * 8] = \
                MODULE.HANDOFF_MARKERS["PREMMU00"][1].to_bytes(8, "little")
            baseline_path.write_bytes(baseline)
            result = MODULE.verify_fresh_generation_markers(final_path, baseline_path, manifest_path)
            self.assertTrue(any("PREMMU00" in failure for failure in result["failures"]))

    def test_armentry_identifies_cold_path_when_slot64_and_fault_window_are_zero(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, raw = self.r68e4_capture(sctlr=1)
            manifest_path = root / "readback.json"
            raw_path = root / "capture.raw"
            manifest_path.write_text(json.dumps(manifest))
            raw_path.write_bytes(raw)

            observed = MODULE.decode_boundary_markers(raw_path, manifest_path)
            self.assertEqual(observed["ARMENTRY"]["status"], "present")
            self.assertEqual(observed["FIRST_CPU"]["status"], "zero")
            self.assertEqual(MODULE.decode_fault_publish_operands(raw_path, manifest_path)["status"],
                             "not-applicable")
            self.assertEqual(MODULE.verify_raw(raw_path, manifest_path), [])

    def test_terminal_v4_transfers_armentry_slot_to_interrupted_link_register(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, raw = self.r68e4_capture(sctlr=1)
            carrier = MODULE.RAW_STAGE_BASE_OFFSET + 0x100
            lr = 0xFFFF_FFF0_0726_4300
            raw[carrier:carrier + 8] = b"Y35ALV04"
            raw[carrier + 4 * 8:carrier + 5 * 8] = lr.to_bytes(8, "little")
            manifest_path = root / "readback.json"
            raw_path = root / "capture.raw"
            manifest_path.write_text(json.dumps(manifest))
            raw_path.write_bytes(raw)

            observed = MODULE.decode_boundary_markers(raw_path, manifest_path)
            self.assertEqual(observed["ARMENTRY"]["status"],
                             "overwritten-by-terminal-link-register")
            self.assertEqual(observed["ARMENTRY"]["link_register"], hex(lr))
            failures = MODULE.verify_raw(raw_path, manifest_path)
            self.assertFalse(any("ARMENTRY" in failure for failure in failures), failures)

    def test_unknown_terminal_magic_does_not_transfer_armentry_ownership(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, raw = self.r68e4_capture(sctlr=1)
            carrier = MODULE.RAW_STAGE_BASE_OFFSET + 0x100
            raw[carrier:carrier + 8] = b"Y35ALV99"
            manifest_path = root / "readback.json"
            raw_path = root / "capture.raw"
            manifest_path.write_text(json.dumps(manifest))
            raw_path.write_bytes(raw)

            observed = MODULE.decode_boundary_markers(raw_path, manifest_path)
            self.assertEqual(observed["ARMENTRY"]["status"], "present")

    def test_post_sctlr_gate_requires_exact_mrs_kva_store_and_cache_persist_order(self):
        marker = MODULE.HANDOFF_MARKERS["SCTLRRD0"][1]
        premmu = MODULE.HANDOFF_MARKERS["PREMMU00"][1]
        kva = MODULE.KVA_ALIAS_MARKER[1]

        def mov64(register, value):
            return [f"mov {register}, #{(value >> shift) & 0xffff:#x}" if shift == 0
                    else f"movk {register}, #{(value >> shift) & 0xffff:#x}, lsl #{shift}"
                    for shift in (0, 16, 32, 48)]

        body = "\n".join([
            *mov64("x14", premmu),
            "str x14, [x20, #0x880]",
            "msr SCTLR_EL1, x0",
            "isb sy",
            "mrs x11, SCTLR_EL1",
            "str x11, [x20, #0x9c8]",
            *mov64("x13", marker),
            "str x13, [x20, #0x9c0]",
            "dsb sy",
            "add x14, x20, #0x9c0",
            "dc civac, x14",
            "add x14, x20, #0x9c8",
            "dc civac, x14",
            "dsb sy",
            "add x12, x20, x22",
            "sub x12, x12, x23",
            *mov64("x13", kva),
            "str x13, [x12, #0x9f8]",
            "add x14, x12, #0x9f8",
            "dsb sy",
            "dc civac, x14",
            "dsb sy",
        ])
        self.assertEqual(MODULE.verify_sctlr_isb_boundaries(body), [])
        self.assertTrue(MODULE.verify_sctlr_isb_boundaries(
            body.replace("sub x12, x12, x23", "sub x12, x12, x22")))
        self.assertTrue(MODULE.verify_sctlr_isb_boundaries(
            body.replace("dc civac, x14\n", "", 1)))
        self.assertTrue(MODULE.verify_sctlr_isb_boundaries(
            body.replace("isb sy\nmrs x11, SCTLR_EL1", "mrs x11, SCTLR_EL1\nisb sy")))

    def test_entry_path_echo_separates_slot64_store_from_slot65_loadback(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, raw = self.r68e4_capture(sctlr=1)
            path = MODULE.RAW_STAGE_BASE_OFFSET + 0x2D0
            expected = MODULE.ENTRY_PATH_MARKERS["FIRST_CPU"][1].to_bytes(8, "little")
            raw[path:path + 8] = expected
            raw[path + 8:path + 16] = expected
            manifest_path = root / "readback.json"
            raw_path = root / "capture.raw"
            manifest_path.write_text(json.dumps(manifest))
            raw_path.write_bytes(raw)
            self.assertTrue(MODULE.decode_entry_path_echo(raw_path, manifest_path)["roundtrip_matches"])

            raw[path:path + 8] = bytes(8)
            raw_path.write_bytes(raw)
            decoded = MODULE.decode_entry_path_echo(raw_path, manifest_path)
            self.assertFalse(decoded["marker_matches"])
            self.assertTrue(decoded["readback_matches"])
            self.assertFalse(decoded["roundtrip_matches"])

    def test_raw_gate_rejects_a_post_isb_witness_with_sctlr_m_clear(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, raw = self.r68e4_capture(sctlr=0)
            manifest_path = root / "readback.json"
            raw_path = root / "capture.raw"
            manifest_path.write_text(json.dumps(manifest))
            raw_path.write_bytes(raw)
            self.assertTrue(any("SCTLR.M" in failure
                                for failure in MODULE.verify_raw(raw_path, manifest_path)))

    @staticmethod
    def r68e4_capture(sctlr: int):
        manifest = {
            "kernel_sha256": "00" * 32,
            "transport_mode": "minimal-boundary",
            "report_bytes": 0x2E0,
            "records": [
                {"name": "early-fault-record", "physical": "0x1000",
                 "size": 384, "report_offset": 0x100},
                {"name": "handoff-witness", "physical": "0x11c0",
                 "size": 16, "report_offset": 0x280},
                {"name": "fault-publish-window", "physical": "0x11d0",
                 "size": 48, "report_offset": 0x290},
                {"name": "fault-pointer-window", "physical": "0xa06d2100",
                 "size": 16, "report_offset": 0x2C0,
                 "symbol_physical": "0xa06d2108", "symbol_offset": 8},
                {"name": "entry-path-window", "physical": "0x1200",
                 "size": 16, "report_offset": 0x2D0},
            ],
        }
        raw = bytearray(0x10000 + 0x2E0)
        carrier = MODULE.RAW_STAGE_BASE_OFFSET + 0x100
        raw[carrier + 4 * 8:carrier + 5 * 8] = MODULE.ENTRY_MARKER.to_bytes(8, "little")
        raw[carrier + 16 * 8:carrier + 17 * 8] = \
            MODULE.HANDOFF_MARKERS["PREMMU00"][1].to_bytes(8, "little")
        handoff = MODULE.RAW_STAGE_BASE_OFFSET + 0x280
        raw[handoff:handoff + 8] = MODULE.HANDOFF_MARKERS["SCTLRRD0"][1].to_bytes(8, "little")
        raw[handoff + 8:handoff + 16] = sctlr.to_bytes(8, "little")
        raw[carrier + 29 * 8:carrier + 30 * 8] = \
            (0xFFFF_FFF0_0700_4000).to_bytes(8, "little")
        raw[carrier + 30 * 8:carrier + 31 * 8] = (0xA000_4000).to_bytes(8, "little")
        return manifest, raw

    def test_marker_parser_invalidates_loaded_register_before_later_store(self):
        lines = []
        values = [
            ("FPGVA00", MODULE.HANDOFF_MARKERS["FPGVA00"][0],
             MODULE.HANDOFF_MARKERS["FPGVA00"][1], 0x948),
            ("FPSTOR00", MODULE.HANDOFF_MARKERS["FPSTOR00"][0],
             MODULE.HANDOFF_MARKERS["FPSTOR00"][1], 0x960),
        ]
        for name, slot, value, offset in values[:1]:
            for shift in (0, 16, 32, 48):
                half = (value >> shift) & 0xffff
                lines.append(f"mov x15, #{half}" if shift == 0
                             else f"movk x15, #{half}, lsl #{shift}")
            lines.append(f"str x15, [x20, #{offset}]")
        lines.extend(["ldr x15, [x20, #2520]", "str x15, [x20, #2384]"])
        name, slot, value, offset = values[1]
        for shift in (0, 16, 32, 48):
            half = (value >> shift) & 0xffff
            lines.append(f"mov x15, #{half}" if shift == 0
                         else f"movk x15, #{half}, lsl #{shift}")
        lines.append(f"str x15, [x20, #{offset}]")
        events = MODULE._marker_events("\n".join(lines), MODULE.HANDOFF_MARKERS)
        self.assertEqual([event[0] for event in events], ["FPGVA00", "FPSTOR00"])

    def test_mapping_and_loop_carriers_are_disjoint(self):
        self.assertEqual(MODULE.HANDOFF_MARKERS["VPPRE000"][0], 52)
        self.assertEqual(MODULE.HANDOFF_MARKERS["VPCALL00"][0], 53)
        self.assertEqual(MODULE.HANDOFF_MARKERS["KVPRE000"][0], 54)
        self.assertEqual(MODULE.HANDOFF_MARKERS["KVCALL00"][0], 55)
        self.assertEqual(MODULE.HANDOFF_MARKERS["VPCALL00"][1],
                         0x30304C4C41435056)
        self.assertEqual(MODULE.HANDOFF_MARKERS["KVCALL00"][1],
                         0x30304C4C4143564B)
        self.assertNotIn(MODULE.HANDOFF_MARKERS["VPPRE000"][0], (46, 47))
        self.assertNotIn(MODULE.HANDOFF_MARKERS["VPCALL00"][0], (46, 47))
        self.assertEqual(MODULE.HANDOFF_MARKERS["LRPRE000"][0], 38)
        self.assertEqual(MODULE.HANDOFF_MARKERS["LRPAGE00"][0], 39)
        self.assertEqual(MODULE.HANDOFF_MARKERS["LROFF000"][0], 40)
        self.assertEqual(MODULE.HANDOFF_MARKERS["FPGVA00"][0], 41)
        self.assertEqual(MODULE.HANDOFF_MARKERS["FPBEFOR0"][0], 43)
        self.assertEqual(MODULE.HANDOFF_MARKERS["FPSTOR00"][0], 44)
        self.assertEqual(MODULE.HANDOFF_MARKERS["LRADD000"][0], 45)
        self.assertEqual(MODULE.HANDOFF_MARKERS["SCTLRRD0"][0], 56)
        self.assertEqual(MODULE.SCTLR_VALUE_SLOT, 57)
        all_markers = list(MODULE.PHASE_MARKERS.items()) + list(MODULE.HANDOFF_MARKERS.items())
        self.assertEqual(sum(slot == 56 for _name, (slot, _value) in all_markers), 1)
        self.assertEqual(sum(slot == 57 for _name, (slot, _value) in all_markers), 0)

    def test_manifest_requires_a_separate_readback_record_for_handoff_slots(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            kernel = root / "kernel.macho"
            kernel.write_bytes(b"instrumented-kernel")
            import hashlib
            manifest = {
                "kernel_sha256": hashlib.sha256(kernel.read_bytes()).hexdigest(),
                "transport_mode": "minimal-boundary",
                "report_bytes": 0x2E0,
                "records": [
                    {
                        "name": "early-fault-record",
                        "physical": "0x1000",
                        "size": 384,
                        "report_offset": 0x100,
                    },
                    {
                        "name": "handoff-witness",
                        "physical": "0x11c0",
                        "size": 16,
                        "report_offset": 0x280,
                    },
                    {
                        "name": "fault-publish-window",
                        "physical": "0x11d0",
                        "size": 48,
                        "report_offset": 0x290,
                    },
                    {
                        "name": "fault-pointer-window",
                        "physical": "0xa06d2100",
                        "size": 16,
                        "report_offset": 0x2C0,
                        "symbol_physical": "0xa06d2108",
                        "symbol_offset": 8,
                    },
                    {
                        "name": "entry-path-window",
                        "physical": "0x1200",
                        "size": 16,
                        "report_offset": 0x2D0,
                    },
                ],
            }
            manifest_path = root / "readback.json"
            manifest_path.write_text(json.dumps(manifest))
            with mock.patch.object(MODULE, "fault_pointer_symbol_physical", return_value=0xA06D2108):
                self.assertEqual(MODULE.verify_manifest(kernel, manifest_path), [])

            manifest["records"][4]["physical"] = "0x1208"
            manifest_path.write_text(json.dumps(manifest))
            with mock.patch.object(MODULE, "fault_pointer_symbol_physical", return_value=0xA06D2108):
                self.assertTrue(any("entry-path-window physical" in error
                                    for error in MODULE.verify_manifest(kernel, manifest_path)))
            manifest["records"][4]["physical"] = "0x1200"

            manifest["records"][1]["physical"] = "0x11b0"
            manifest_path.write_text(json.dumps(manifest))
            with mock.patch.object(MODULE, "fault_pointer_symbol_physical", return_value=0xA06D2108):
                self.assertTrue(any("handoff-witness" in error
                                    for error in MODULE.verify_manifest(kernel, manifest_path)))

            manifest["records"][1]["physical"] = "0x11c0"
            manifest["records"][2]["physical"] = "0x11d0"
            manifest["records"][3]["physical"] = "0x11d0"
            manifest["records"][3]["symbol_physical"] = "0x11d8"
            manifest["records"][3]["symbol_offset"] = 8
            manifest_path.write_text(json.dumps(manifest))
            with mock.patch.object(MODULE, "fault_pointer_symbol_physical", return_value=0x11D8):
                self.assertTrue(any("physical ranges alias" in error
                                    for error in MODULE.verify_manifest(kernel, manifest_path)))

            manifest["records"][2]["physical"] = "0x11d0"
            manifest["records"][3]["physical"] = "0xa06d20f0"
            manifest["records"][3]["symbol_physical"] = "0xa06d20f8"
            manifest_path.write_text(json.dumps(manifest))
            with mock.patch.object(MODULE, "fault_pointer_symbol_physical", return_value=0xA06D2108):
                self.assertTrue(any("does not contain the Mach-O" in error
                                    for error in MODULE.verify_manifest(kernel, manifest_path)))

    def test_raw_reports_observed_handoff_markers_from_the_declared_record(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = {
                "kernel_sha256": "00" * 32,
                "transport_mode": "minimal-boundary",
                "report_bytes": 0x2E0,
                "records": [
                    {
                        "name": "early-fault-record",
                        "physical": "0x1000",
                        "size": 384,
                        "report_offset": 0x100,
                    },
                    {
                        "name": "handoff-witness",
                        "physical": "0x11c0",
                        "size": 16,
                        "report_offset": 0x280,
                    },
                    {
                        "name": "fault-publish-window",
                        "physical": "0x11d0",
                        "size": 48,
                        "report_offset": 0x290,
                    },
                    {
                        "name": "fault-pointer-window",
                        "physical": "0xa06d2100",
                        "size": 16,
                        "report_offset": 0x2C0,
                        "symbol_physical": "0xa06d2108",
                        "symbol_offset": 8,
                    },
                    {
                        "name": "entry-path-window",
                        "physical": "0x1200",
                        "size": 16,
                        "report_offset": 0x2D0,
                    },
                ],
            }
            raw = bytearray(0x11000)
            carrier = MODULE.RAW_STAGE_BASE_OFFSET + 0x100
            raw[carrier:carrier + 8] = (1).to_bytes(8, "little")
            raw[carrier + 4 * 8:carrier + 5 * 8] = MODULE.ENTRY_MARKER.to_bytes(8, "little")
            raw[MODULE.RAW_STAGE_BASE_OFFSET + 0x2D0:
                MODULE.RAW_STAGE_BASE_OFFSET + 0x2D8] = \
                MODULE.ENTRY_PATH_MARKERS["FIRST_CPU"][1].to_bytes(8, "little")
            raw[carrier + 16 * 8:carrier + 17 * 8] = \
                MODULE.HANDOFF_MARKERS["PREMMU00"][1].to_bytes(8, "little")
            raw[carrier + 29 * 8:carrier + 30 * 8] = \
                (0xFFFF_FFF0_0700_4000).to_bytes(8, "little")
            raw[carrier + 30 * 8:carrier + 31 * 8] = \
                (0xA000_4000).to_bytes(8, "little")
            raw[MODULE.RAW_STAGE_BASE_OFFSET + 0x280:
                MODULE.RAW_STAGE_BASE_OFFSET + 0x288] = \
                MODULE.HANDOFF_MARKERS["SCTLRRD0"][1].to_bytes(8, "little")
            raw[MODULE.RAW_STAGE_BASE_OFFSET + 0x288:
                MODULE.RAW_STAGE_BASE_OFFSET + 0x290] = (1).to_bytes(8, "little")
            publish = MODULE.RAW_STAGE_BASE_OFFSET + 0x290
            for index, value in enumerate((
                0xFFFF_FFF0_076D_2108,
                0xFFFF_FFF0_07B7_C800,
                0xA06D_2108,
                MODULE.HANDOFF_MARKERS["PUBLPR00"][1],
                MODULE.HANDOFF_MARKERS["PUBLPS00"][1],
                0,
            )):
                raw[publish + index * 8:publish + (index + 1) * 8] = value.to_bytes(8, "little")
            pointer_window = MODULE.RAW_STAGE_BASE_OFFSET + 0x2C0
            raw[pointer_window + 8:pointer_window + 16] = \
                (0xFFFF_FFF0_07B7_C800).to_bytes(8, "little")
            manifest_path = root / "readback.json"
            raw_path = root / "capture.raw"
            manifest_path.write_text(json.dumps(manifest))
            raw_path.write_bytes(raw)

            observed = MODULE.decode_boundary_markers(raw_path, manifest_path)
            self.assertEqual(observed["PREMMU00"]["status"], "present")
            self.assertEqual(observed["SCTLRRD0"]["status"], "present")
            initial_failures = MODULE.verify_raw(raw_path, manifest_path)
            self.assertTrue(any("direct MMU-off global address" in error
                                for error in initial_failures))
            self.assertEqual(MODULE.decode_fault_publish_operands(raw_path, manifest_path)["diagnostic_complete_marker"],
                             "present")
            self.assertEqual(MODULE.decode_fault_publish_operands(raw_path, manifest_path)["global_address_form"],
                             "virtual")

            manifest["records"][3]["physical"] = "0x2000"
            manifest["records"][3]["symbol_physical"] = "0x2008"
            manifest_path.write_text(json.dumps(manifest))
            mismatched_symbol = MODULE.verify_raw(raw_path, manifest_path)
            self.assertTrue(any("direct MMU-off global address" in error
                                for error in mismatched_symbol))
            self.assertEqual(MODULE.decode_fault_publish_operands(raw_path, manifest_path)["global_address_form"],
                             "other")
            manifest["records"][3]["physical"] = "0xa06d2100"
            manifest["records"][3]["symbol_physical"] = "0xa06d2108"
            manifest_path.write_text(json.dumps(manifest))

            raw[publish + 16:publish + 24] = (0xA06D_2109).to_bytes(8, "little")
            raw_path.write_bytes(raw)
            self.assertFalse(MODULE.decode_fault_publish_operands(
                raw_path, manifest_path)["translated_candidate_matches_formula"])
            raw[publish + 16:publish + 24] = (0xA06D_2108).to_bytes(8, "little")
            raw[pointer_window + 8:pointer_window + 16] = (0x1234).to_bytes(8, "little")
            raw_path.write_bytes(raw)
            self.assertTrue(any("publish payload" in error
                                for error in MODULE.verify_raw(raw_path, manifest_path)))
            raw[pointer_window + 8:pointer_window + 16] = \
                (0xFFFF_FFF0_07B7_C800).to_bytes(8, "little")

            raw[MODULE.RAW_STAGE_BASE_OFFSET + 0x280:
                MODULE.RAW_STAGE_BASE_OFFSET + 0x288] = (0xdead).to_bytes(8, "little")
            raw_path.write_bytes(raw)
            self.assertTrue(any("SCTLRRD0" in error
                                for error in MODULE.verify_raw(raw_path, manifest_path)))

            raw[MODULE.RAW_STAGE_BASE_OFFSET + 0x280:
                MODULE.RAW_STAGE_BASE_OFFSET + 0x290] = bytes(16)
            raw_path.write_bytes(raw)
            observed = MODULE.decode_boundary_markers(raw_path, manifest_path)
            self.assertEqual(observed["SCTLRRD0"]["status"], "zero")
            self.assertTrue(any("SCTLRRD0" in error
                                for error in MODULE.verify_raw(raw_path, manifest_path)))

            manifest["records"] = manifest["records"][:-1]
            manifest["records"] = [record for record in manifest["records"]
                                    if record["name"] not in ("handoff-witness", "fault-pointer-window")]
            manifest_path.write_text(json.dumps(manifest))
            observed = MODULE.decode_boundary_markers(raw_path, manifest_path)
            self.assertEqual(observed["SCTLRRD0"]["status"], "unavailable")
            self.assertTrue(any("SCTLRRD0" in error
                                for error in MODULE.verify_raw(raw_path, manifest_path)))

    def test_marker_parser_propagates_add_immediate(self):
        body = "\n".join([
            "mov x20, #17742",
            "movk x20, #18772, lsl #16",
            "movk x20, #18766, lsl #32",
            "movk x20, #20549, lsl #48",
            "add x9, x20, #3334",
            "str x9, [x8, #56]",
        ])
        self.assertEqual(MODULE._marker_events(body), [("PEINITRT", 5, 7)])

    def test_marker_parser_normalizes_kva_carrier_offset(self):
        body = "\n".join([
            "mov x9, #21573",
            "movk x9, #20041, lsl #16",
            "movk x9, #19785, lsl #32",
            "movk x9, #16722, lsl #48",
            "str x9, [x8, #2088]",
        ])
        self.assertEqual(MODULE._marker_events(body), [("ARMINITE", 4, 5)])

    def test_full_readback_raw_uses_stage_relative_carrier_offset(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = {
                "kernel_sha256": "00" * 32,
                "transport_mode": "full-readback",
                "report_bytes": 544,
                "records": [{
                    "name": "early-fault-record",
                    "physical": "0x1000",
                    "offset": 64,
                    "size": 384,
                }, {
                    "name": "handoff-witness",
                    "physical": "0x11c0",
                    "offset": 448,
                    "size": 16,
                }, {
                    "name": "fault-publish-window",
                    "physical": "0x11d0",
                    "offset": 464,
                    "size": 48,
                }, {
                    "name": "fault-pointer-window",
                    "physical": "0xa06d2100",
                    "offset": 512,
                    "size": 16,
                    "symbol_physical": "0xa06d2108",
                    "symbol_offset": 8,
                }, {
                    "name": "entry-path-window",
                    "physical": "0x1200",
                    "offset": 528,
                    "size": 16,
                }],
            }
            raw = bytearray(0x10000 + 544)
            raw[0x40 + 4 * 8:0x40 + 5 * 8] = MODULE.ENTRY_MARKER.to_bytes(8, "little")
            raw[528:536] = MODULE.ENTRY_PATH_MARKERS["FIRST_CPU"][1].to_bytes(8, "little")
            raw[0x40:0x40 + 8] = (0).to_bytes(8, "little")
            raw[64 + 16 * 8:64 + 17 * 8] = MODULE.HANDOFF_MARKERS["PREMMU00"][1].to_bytes(8, "little")
            raw[448:456] = MODULE.HANDOFF_MARKERS["SCTLRRD0"][1].to_bytes(8, "little")
            raw[456:464] = (1).to_bytes(8, "little")
            raw[64 + 29 * 8:64 + 30 * 8] = (0xFFFF_FFF0_0700_4000).to_bytes(8, "little")
            raw[64 + 30 * 8:64 + 31 * 8] = (0xA000_4000).to_bytes(8, "little")
            publish = 464
            for index, value in enumerate((
                0xFFFF_FFF0_076D_2108,
                0xFFFF_FFF0_07B7_C800,
                0xA06D_2108,
                MODULE.HANDOFF_MARKERS["PUBLPR00"][1],
                0,
                0,
            )):
                raw[publish + index * 8:publish + (index + 1) * 8] = value.to_bytes(8, "little")
            raw[512 + 8:512 + 16] = (0xFFFF_FFF0_07B7_C800).to_bytes(8, "little")
            manifest_path = root / "readback.json"
            raw_path = root / "capture.raw"
            manifest_path.write_text(json.dumps(manifest))
            raw_path.write_bytes(raw)
            self.assertEqual(MODULE.decode_fault_publish_operands(raw_path, manifest_path)["status"],
                             "captured")
            self.assertTrue(any("direct MMU-off global address" in error
                                for error in MODULE.verify_raw(raw_path, manifest_path)))

    def test_pre_store_decode_does_not_promote_unchanged_base_slots_to_runtime_reads(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = {
                "transport_mode": "minimal-boundary",
                "records": [
                    {"name": "early-fault-record", "physical": "0xa0b80800",
                     "size": 384, "report_offset": 0x100},
                    {"name": "fault-pointer-window", "physical": "0xa06d2100",
                     "size": 16, "report_offset": 0x300,
                     "symbol_physical": "0xa06d2108", "symbol_offset": 8},
                ],
            }
            baseline = bytearray(0x11000)
            final = bytearray(0x11000)
            carrier = MODULE.RAW_STAGE_BASE_OFFSET + 0x100
            for raw in (baseline, final):
                raw[carrier + 29 * 8:carrier + 30 * 8] = \
                    (0xFFFF_FFF0_0700_4000).to_bytes(8, "little")
                raw[carrier + 30 * 8:carrier + 31 * 8] = \
                    (0xA000_4000).to_bytes(8, "little")
            final[carrier + 43 * 8:carrier + 44 * 8] = \
                MODULE.HANDOFF_MARKERS["FPBEFOR0"][1].to_bytes(8, "little")
            final[carrier + MODULE.FAULT_PUBLISH_PRE_STORE_CANDIDATE_SLOT * 8:
                  carrier + (MODULE.FAULT_PUBLISH_PRE_STORE_CANDIDATE_SLOT + 1) * 8] = \
                (0x11396D2108).to_bytes(8, "little")
            manifest_path = root / "readback.json"
            raw_path = root / "final.raw"
            baseline_path = root / "baseline.raw"
            manifest_path.write_text(json.dumps(manifest))
            raw_path.write_bytes(final)
            baseline_path.write_bytes(baseline)

            decoded = MODULE.decode_fault_publish_pre_store(
                raw_path, manifest_path, baseline_path)
            self.assertEqual(decoded["status"], "captured")
            self.assertEqual(decoded["base_slots_vs_baseline"], "unchanged")
            self.assertFalse(decoded["reconstruction_is_runtime_proof"])
            self.assertEqual(decoded["x9_candidate"], "0x11396d2108")

    def test_fault_flag_keeps_low_slot45_evidence_when_poststore_window_is_empty(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, raw = self.r68e4_capture(sctlr=0)
            carrier = MODULE.RAW_STAGE_BASE_OFFSET + 0x100
            raw[carrier:carrier + 8] = (1).to_bytes(8, "little")
            raw[carrier + 43 * 8:carrier + 44 * 8] = \
                MODULE.HANDOFF_MARKERS["FPBEFOR0"][1].to_bytes(8, "little")
            raw[carrier + MODULE.FAULT_PUBLISH_PRE_STORE_CANDIDATE_SLOT * 8:
                carrier + (MODULE.FAULT_PUBLISH_PRE_STORE_CANDIDATE_SLOT + 1) * 8] = \
                (0x11396D2108).to_bytes(8, "little")
            raw_path = root / "capture.raw"
            manifest_path = root / "readback.json"
            raw_path.write_bytes(raw)
            manifest_path.write_text(json.dumps(manifest))

            pre_store = MODULE.decode_fault_publish_pre_store(raw_path, manifest_path)
            self.assertEqual(pre_store["status"], "captured")
            self.assertEqual(pre_store["x9_candidate"], "0x11396d2108")
            failures = MODULE.verify_raw(raw_path, manifest_path)
            self.assertTrue(any("fault-publish-window" in failure for failure in failures))

    def test_slot45_overwrite_is_not_attributed_to_slot43_ptbase_marker(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = {
                "transport_mode": "minimal-boundary",
                "records": [
                    {"name": "early-fault-record", "physical": "0xa0b80800",
                     "size": 384, "report_offset": 0x100},
                    {"name": "fault-pointer-window", "physical": "0xa06d2100",
                     "size": 16, "report_offset": 0x300,
                     "symbol_physical": "0xa06d2108", "symbol_offset": 8},
                ],
            }
            raw = bytearray(0x11000)
            carrier = MODULE.RAW_STAGE_BASE_OFFSET + 0x100
            raw[carrier + 43 * 8:carrier + 44 * 8] = \
                MODULE.HANDOFF_MARKERS["PTBASE00"][1].to_bytes(8, "little")
            raw[carrier + 44 * 8:carrier + 45 * 8] = \
                MODULE.HANDOFF_MARKERS["PTCOUNT0"][1].to_bytes(8, "little")
            slot45 = carrier + MODULE.FAULT_PUBLISH_PRE_STORE_CANDIDATE_SLOT * 8
            raw[slot45:slot45 + 8] = MODULE.HANDOFF_MARKERS["LRADD000"][1].to_bytes(8, "little")
            manifest_path = root / "readback.json"
            raw_path = root / "capture.raw"
            manifest_path.write_text(json.dumps(manifest))
            raw_path.write_bytes(raw)

            decoded = MODULE.decode_fault_publish_pre_store(raw_path, manifest_path)
            self.assertEqual(decoded["status"], "overwritten")
            self.assertEqual(decoded["candidate_overwritten_by"], "LRADD000")
            self.assertEqual(decoded["pre_store_marker_status"], "overwritten-by-PTBASE00")
            boundary = MODULE.decode_boundary_markers(raw_path, manifest_path)
            self.assertEqual(boundary["FPBEFOR0"]["status"], "overwritten")
            self.assertEqual(boundary["FPSTOR00"]["status"], "overwritten")
            self.assertEqual(boundary["PTBASE00"]["status"], "present")
            self.assertEqual(boundary["PTCOUNT0"]["status"], "present")

    def test_handoff_markers_use_reserved_slots(self):
        all_markers = list(MODULE.PHASE_MARKERS.items()) + list(MODULE.HANDOFF_MARKERS.items())
        self.assertEqual(MODULE.HANDOFF_MARKERS["SCTLRRD0"][0], 56)
        self.assertEqual(MODULE.SCTLR_VALUE_SLOT, 57)
        self.assertEqual(sum(slot == 56 for _name, (slot, _value) in all_markers), 1)
        self.assertEqual(sum(slot == 57 for _name, (slot, _value) in all_markers), 0)
        self.assertEqual(MODULE.RAW_LOOP_STATE_SLOTS, (46, 47))

        def load_marker(name, register):
            _slot, value = MODULE.HANDOFF_MARKERS[name]
            lines = []
            for shift in (0, 16, 32, 48):
                half = (value >> shift) & 0xFFFF
                lines.append(f"mov {register}, #{half}" if shift == 0
                             else f"movk {register}, #{half}, lsl #{shift}")
            return lines

        def store_marker(name, register):
            slot, _value = MODULE.HANDOFF_MARKERS[name]
            return f"str {register}, [x20, #{0x800 + slot * 8}]"

        body_lines = ["mov x14, x22", "mov x15, x23"]
        split_names = {"SCTLRRD0"}
        for name in MODULE.HANDOFF_ORDER:
            if name in split_names or name in {"FPSTOR00", "PUBLPR00", "PUBLPS00"}:
                continue
            if name == "PREMMU00":
                body_lines.extend(load_marker("PREMMU00", "x14"))
                body_lines.append(store_marker("PREMMU00", "x14"))
                body_lines.append("msr SCTLR_EL1, x0")
                body_lines.extend([
                    "isb sy",
                    "mrs x11, SCTLR_EL1",
                    "str x11, [x20, #0x9c8]",
                ])
                body_lines.extend(load_marker("SCTLRRD0", "x13"))
                body_lines.extend([
                    "str x13, [x20, #0x9c0]",
                    "dsb sy",
                    "add x14, x20, #0x9c0",
                    "dc civac, x14",
                    "add x14, x20, #0x9c8",
                    "dc civac, x14",
                    "dsb sy",
                    "add x12, x20, x22",
                    "sub x12, x12, x23",
                ])
                value = MODULE.KVA_ALIAS_MARKER[1]
                for shift in (0, 16, 32, 48):
                    half = (value >> shift) & 0xFFFF
                    body_lines.append(f"mov x13, #{half}" if shift == 0
                                      else f"movk x13, #{half}, lsl #{shift}")
                body_lines.extend([
                    "str x13, [x12, #0x9f8]",
                    "add x14, x12, #0x9f8",
                    "dsb sy",
                    "dc civac, x14",
                    "dsb sy",
                ])
                continue
            if name == "FPGVA00":
                body_lines.extend([
                    "adrp x16, _native_early_fault_address@PAGE",
                    "add x16, x16, #0x108",
                ])
                body_lines.extend(load_marker(name, "x15"))
                body_lines.append(store_marker(name, "x15"))
                continue
            if name == "FPBEFOR0":
                body_lines.extend([
                    "mov x9, x16",
                    "str x9, [x20, #0x968]",
                ])
                body_lines.extend(load_marker(name, "x15"))
                body_lines.append(store_marker(name, "x15"))
                body_lines.append("str x17, [x16]")
                body_lines.append("ldr x14, [x16]")
                body_lines.append("str x14, [x20, #0x850]")
                body_lines.append("str x14, [x20, #0xa68]")
                body_lines.extend(load_marker("FPSTOR00", "x15"))
                body_lines.append(store_marker("FPSTOR00", "x15"))
                body_lines.extend(load_marker("PUBLPR00", "x15"))
                body_lines.append(store_marker("PUBLPR00", "x15"))
                body_lines.extend([
                    "str x16, [x20, #0x9d0]",
                    "str x17, [x20, #0x9d8]",
                    "str x9, [x20, #0x9e0]",
                ])
                body_lines.extend(load_marker("PUBLPS00", "x15"))
                body_lines.append(store_marker("PUBLPS00", "x15"))
                continue
            register = "x16" if name in MODULE.MAPPING_CURSOR_MARKERS else "x15"
            body_lines.extend(load_marker(name, register))
            body_lines.append(store_marker(name, register))

        body = "\n".join(body_lines)
        self.assertEqual(MODULE.verify_handoff_disassembly(body), [])
        fault_start = body.index("adrp x16, _native_early_fault_address@PAGE")
        fault_end_marker = body.index(store_marker("PUBLPS00", "x15"), fault_start)
        fault_end = body.index("\n", fault_end_marker)
        fault_body = body[fault_start:fault_end]
        self.assertEqual(MODULE.verify_fault_publish_disassembly(fault_body), [])
        fpgva_high = (MODULE.HANDOFF_MARKERS["FPGVA00"][1] >> 48) & 0xffff
        wrong_half = fault_body.replace(
            f"movk x15, #{fpgva_high}, lsl #48",
            "movk x15, #48, lsl #48",
            1,
        ) + f"\nmovk x15, #{fpgva_high}, lsl #48"
        self.assertTrue(any("FPGVA00 codeword" in failure
                            for failure in MODULE.verify_fault_publish_disassembly(wrong_half)))
        bypassed_store = fault_body.replace(
            "str x17, [x16]",
            "b .Lafter_global_store\nstr x17, [x16]",
            1,
        )
        self.assertTrue(any("control transfer can bypass" in failure
                            for failure in MODULE.verify_fault_publish_disassembly(bypassed_store)))
        prefix_bypass = "b .Lafter_publish\n" + fault_body
        self.assertTrue(any("control-flow branch can skip" in failure
                            for failure in MODULE.verify_fault_publish_disassembly(prefix_bypass)))
        wrong_fault_pointer_base = fault_body.replace("str x17, [x16]", "str x17, [x9]", 1)
        wrong_base_failures = MODULE.verify_fault_publish_disassembly(wrong_fault_pointer_base)
        self.assertTrue(any("direct MMU-off global store through x16" in failure
                            for failure in wrong_base_failures))
        self.assertTrue(any("x9 double-translates" in failure for failure in wrong_base_failures))
        offset = 0x800 + MODULE.HANDOFF_MARKERS["VPPRE000"][0] * 8
        corrupted = body.replace(f"str x16, [x20, #{offset}]",
                                 f"str x15, [x20, #{offset}]", 1)
        self.assertTrue(any("VPPRE000" in failure
                            for failure in MODULE.verify_mapping_cursor_registers(corrupted)))

    def test_sctlr_boundary_accepts_r167_physical_pre_and_post_witnesses(self):
        def load(value, register):
            return [
                f"mov {register}, #{(value >> shift) & 0xffff}" if shift == 0
                else f"movk {register}, #{(value >> shift) & 0xffff}, lsl #{shift}"
                for shift in (0, 16, 32, 48)
            ]

        lines = [
            *load(MODULE.HANDOFF_MARKERS["PREMMU00"][1], "x14"),
            "str x14, [x20, #0x880]",
            *load(int.from_bytes(b"SCTPRE00", "little"), "x14"),
            "str x14, [x20, #0xa10]",
            "add x14, x20, #0xa10",
            "dc civac, x14",
            "dsb sy",
            "msr SCTLR_EL1, x0",
            "isb sy",
            "mrs x11, SCTLR_EL1",
            *load(int.from_bytes(b"SCTPOST0", "little"), "x14"),
            "str x14, [x20, #0xa20]",
            "add x14, x20, #0xa20",
            "dc civac, x14",
            "dsb sy",
            "str x11, [x20, #0x9c8]",
            *load(MODULE.HANDOFF_MARKERS["SCTLRRD0"][1], "x13"),
            "str x13, [x20, #0x9c0]",
            "dsb sy",
            "add x14, x20, #0x9c0",
            "dc civac, x14",
            "add x14, x20, #0x9c8",
            "dc civac, x14",
            "dsb sy",
            "add x12, x20, x22",
            "sub x12, x12, x23",
            *load(MODULE.KVA_ALIAS_MARKER[1], "x13"),
            "str x13, [x12, #0x9f8]",
            "add x14, x12, #0x9f8",
            "dsb sy",
            "dc civac, x14",
            "dsb sy",
        ]
        self.assertEqual(MODULE.verify_sctlr_isb_boundaries("\n".join(lines)), [])


if __name__ == "__main__":
    unittest.main()
