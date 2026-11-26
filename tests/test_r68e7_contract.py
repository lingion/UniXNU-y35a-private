#!/usr/bin/env python3
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/y35a"))
SPEC = importlib.util.spec_from_file_location(
    "verify_phase_instrumentation",
    ROOT / "scripts/y35a/verify_phase_instrumentation.py",
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class R68E7ContractTest(unittest.TestCase):
    def r68e7_capture(self, *, mmu=True, kva=True, corrupt_x9=False):
        report_bytes = 0x320
        manifest = {
            "transport_mode": "minimal-boundary",
            "report_bytes": report_bytes,
            "kernel_virtual_base": "0xfffffff007004000",
            "kernel_physical_base": "0xa0004000",
            "records": [
                {"name": "early-fault-record", "physical": "0x1000",
                 "size": 384, "report_offset": 0x100},
                {"name": MODULE.R68E7_STORE_WINDOW_RECORD, "physical": "0x1240",
                 "size": 64, "report_offset": 0x280},
                {"name": "handoff-witness", "physical": "0x11c0",
                 "size": 16, "report_offset": 0x2c0},
                {"name": "fault-publish-window", "physical": "0x11d0",
                 "size": 48, "report_offset": 0x2d0},
                {"name": "fault-pointer-window", "physical": "0xa06d2100",
                 "size": 16, "report_offset": 0x310,
                 "symbol_physical": "0xa06d2108", "symbol_offset": 8},
            ],
        }
        baseline = bytearray(MODULE.RAW_STAGE_BASE_OFFSET + report_bytes)
        final = bytearray(baseline)
        store = MODULE.RAW_STAGE_BASE_OFFSET + 0x280
        x16 = 0xA06D2108
        x22 = 0xFFFF_FFF0_0700_4000
        x23 = 0xA000_4000
        x17 = (0x1000 + x22 - x23) & 0xFFFF_FFFF_FFFF_FFFF
        x9 = (x16 - x22 + x23) & 0xFFFF_FFFF_FFFF_FFFF
        if corrupt_x9:
            x9 ^= 0x10
        values = (x16, x17, x9, x22, x23, x17,
                  MODULE.R68E7_STORE_MARKERS["PUBLIN00"][1],
                  MODULE.R68E7_STORE_MARKERS["PUBLRD00"][1])
        for index, value in enumerate(values):
            start = store + index * 8
            final[start:start + 8] = value.to_bytes(8, "little")
        handoff = MODULE.RAW_STAGE_BASE_OFFSET + 0x2C0
        final[handoff:handoff + 8] = MODULE.HANDOFF_MARKERS["SCTLRRD0"][1].to_bytes(8, "little")
        final[handoff + 8:handoff + 16] = (5 if mmu else 0).to_bytes(8, "little")
        high = MODULE.RAW_STAGE_BASE_OFFSET + 0x2D0
        if kva:
            final[high + 5 * 8:high + 6 * 8] = MODULE.KVA_ALIAS_MARKER[1].to_bytes(8, "little")
        pointer = MODULE.RAW_STAGE_BASE_OFFSET + 0x310
        final[pointer + 8:pointer + 16] = x17.to_bytes(8, "little")
        return manifest, bytes(baseline), bytes(final)

    def low_carrier_capture(
        self, *, stage="store-readback-complete", baseline_stage=0,
        overwrite_names=(), kva=True, pointer_value=0,
    ):
        early_physical = 0xA0B80800
        manifest = {
            "transport_mode": "minimal-boundary",
            "report_bytes": 0x350,
            "kernel_virtual_base": "0xfffffff007004000",
            "kernel_physical_base": "0xa0004000",
            "records": [
                {"name": "early-fault-record", "physical": hex(early_physical),
                 "size": MODULE.EARLY_RECORD_BYTES, "report_offset": 0x100},
                {"name": MODULE.HANDOFF_WITNESS_RECORD,
                 "physical": hex(early_physical + 56 * 8),
                 "size": 16, "report_offset": 0x280},
                {"name": MODULE.FAULT_PUBLISH_WINDOW_RECORD,
                 "physical": hex(early_physical + 58 * 8),
                 "size": MODULE.FAULT_PUBLISH_WINDOW_BYTES, "report_offset": 0x290},
                {"name": MODULE.FAULT_POINTER_WINDOW_RECORD,
                 "physical": "0xa06d2100", "size": 16, "report_offset": 0x2d0,
                 "symbol_physical": "0xa06d2108", "symbol_offset": 8},
                {"name": MODULE.R68E7_STORE_WINDOW_RECORD,
                 "physical": hex(early_physical + MODULE.R68E7_STORE_WINDOW_BASE_OFFSET),
                 "size": MODULE.R68E7_STORE_WINDOW_BYTES, "report_offset": 0x300},
            ],
        }
        baseline = bytearray(MODULE.RAW_STAGE_BASE_OFFSET + manifest["report_bytes"])
        final = bytearray(baseline)
        x16 = 0xA06D2108
        x22 = 0xFFFF_FFF0_0700_4000
        x23 = 0xA000_4000
        x17 = (early_physical + x22 - x23) & 0xFFFF_FFFF_FFFF_FFFF
        x9 = (x16 - x22 + x23) & 0xFFFF_FFFF_FFFF_FFFF
        low_slots = [0] * 12
        low_slots[5:11] = [x16, x17, x9, x22, x23, x17]
        stage_values = {name: value for value, name in MODULE.R68E7_LOW_STAGE_MARKERS.items()}
        final_stage = (stage_values[stage]
                       if isinstance(stage, str) else stage)
        baseline_stage_value = (stage_values[baseline_stage]
                                if isinstance(baseline_stage, str) else baseline_stage)
        low_slots[MODULE.R68E7_LOW_STAGE_SLOT] = final_stage
        early_offset = MODULE.RAW_STAGE_BASE_OFFSET + 0x100
        for index, value in enumerate(low_slots):
            start = early_offset + index * 8
            final[start:start + 8] = value.to_bytes(8, "little")
        final[early_offset + 4 * 8:early_offset + 5 * 8] = \
            MODULE.ENTRY_MARKER.to_bytes(8, "little")
        final[early_offset + MODULE.HANDOFF_MARKERS["PREMMU00"][0] * 8:
              early_offset + (MODULE.HANDOFF_MARKERS["PREMMU00"][0] + 1) * 8] = \
            MODULE.HANDOFF_MARKERS["PREMMU00"][1].to_bytes(8, "little")
        baseline_slot = early_offset + MODULE.R68E7_LOW_STAGE_SLOT * 8
        baseline[baseline_slot:baseline_slot + 8] = baseline_stage_value.to_bytes(8, "little")

        for name in overwrite_names:
            slot, marker = MODULE.PHASE_MARKERS[name]
            start = early_offset + slot * 8
            final[start:start + 8] = marker.to_bytes(8, "little")

        handoff = MODULE.RAW_STAGE_BASE_OFFSET + 0x280
        final[handoff:handoff + 8] = MODULE.HANDOFF_MARKERS["SCTLRRD0"][1].to_bytes(8, "little")
        final[handoff + 8:handoff + 16] = (5).to_bytes(8, "little")
        publish = MODULE.RAW_STAGE_BASE_OFFSET + 0x290
        if kva:
            final[publish + 5 * 8:publish + 6 * 8] = MODULE.KVA_ALIAS_MARKER[1].to_bytes(8, "little")
        pointer = MODULE.RAW_STAGE_BASE_OFFSET + 0x2D0
        final[pointer + 8:pointer + 16] = pointer_value.to_bytes(8, "little")
        # The independent +0xa40 witness is deliberately left zero in both captures.
        return manifest, bytes(baseline), bytes(final)

    def test_new_patch_runs_after_r68e6_on_a_fresh_xnu_source(self):
        source = (ROOT / "scripts/build-xnu-4903-kernel.py").read_text()
        self.assertIn("native-r68e7-boundary-witness-v5.patch", source)
        self.assertLess(source.index("native-r68e-entry-path-witness.patch"),
                        source.index("native-r68e7-boundary-witness-v5.patch"))

    def test_new_generation_has_unique_durable_and_kva_markers(self):
        self.assertEqual(MODULE.R68E7_STORE_MARKERS["PUBLIN00"],
                         (6, int.from_bytes(b"R68E7IN0", "little")))
        self.assertEqual(MODULE.KVA_ALIAS_MARKER,
                         (63, int.from_bytes(b"R68E7KV0", "little")))
        self.assertEqual(MODULE.R68E7_STORE_MARKERS["PUBLRD00"],
                         (7, int.from_bytes(b"R68E7RB0", "little")))
        self.assertEqual(MODULE.ENTRY_MARKER, int.from_bytes(b"R68E7AR0", "little"))
        self.assertEqual(MODULE.HANDOFF_MARKERS["PREMMU00"][1],
                         int.from_bytes(b"R68E7PM0", "little"))
        self.assertEqual(MODULE.HANDOFF_MARKERS["SCTLRRD0"][1],
                         int.from_bytes(b"R68E7RD0", "little"))

    def test_v4_legacy_patch_persists_pre_store_operands_and_separates_post_isb_aliases(self):
        patch_path = ROOT / "patches/xnu/native-r68e7-boundary-witness-v4.patch"
        if not patch_path.exists():
            self.skipTest("optional v4 legacy patch is not present")
        patch = " ".join(patch_path.read_text().split())
        for instruction in (
            "str x16, [x20, #0xa40]",
            "str x17, [x20, #0xa48]",
            "str x9, [x20, #0xa50]",
            "str x22, [x20, #0xa58]",
            "str x23, [x20, #0xa60]",
            "str x17, [x16]",
            "ldr x14, [x16]",
            "str x14, [x20, #0xa68]",
            "dc civac, x16",
            "str x15, [x20, #0xa70]",
            "str x15, [x20, #0xa78]",
            "str x11, [x20, #0x9c8]",
            "str x13, [x20, #0x9c0]",
            "str x13, [x12, #0x9f8]",
            "dsb sy dc civac, x14 dsb sy",
        ):
            with self.subTest(instruction=instruction):
                self.assertIn(instruction, patch)
        self.assertLess(patch.index("str x16, [x20, #0xa40]"),
                        patch.index("str x17, [x16]"))
        self.assertLess(patch.index("str x17, [x16]"),
                        patch.index("ldr x14, [x16]"))
        self.assertLess(patch.index("mrs x11, SCTLR_EL1"),
                        patch.index("str x11, [x20, #0x9c8]"))
        self.assertLess(patch.index("str x11, [x20, #0x9c8]"),
                        patch.index("str x13, [x12, #0x9f8]"))
        self.assertIn("add x14, x20, #0xa08 + dsb sy dc civac, x14 dsb sy", patch)

    def test_low_carrier_decodes_slots5_to10_and_baseline_fresh_slot11_stages(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, baseline, final = self.low_carrier_capture(
                stage="snapshot-complete", baseline_stage=0,
            )
            manifest_path = root / "readback.json"
            baseline_path = root / "baseline.raw"
            final_path = root / "final.raw"
            manifest_path.write_text(json.dumps(manifest))
            baseline_path.write_bytes(baseline)
            final_path.write_bytes(final)

            decoded = MODULE.decode_r68e7_low_carrier(final_path, manifest_path, baseline_path)
            self.assertEqual(decoded["stage"], "snapshot-complete")
            self.assertTrue(decoded["stage_fresh"])
            self.assertTrue(decoded["low_payload_available"])
            self.assertEqual(decoded["c_phase_overwrites"], [])
            self.assertTrue(decoded["x16_matches_global_symbol"])
            self.assertTrue(decoded["x22_matches_expected_base"])
            self.assertTrue(decoded["x23_matches_expected_base"])
            self.assertTrue(decoded["x17_matches_early_carrier_payload"])
            self.assertTrue(decoded["x9_matches_live_base_arithmetic"])
            self.assertTrue(decoded["readback_matches_x17"])
            self.assertFalse(decoded["pointer_matches_x17"])
            self.assertTrue(decoded["readback_matches_x17"])

            manifest, baseline, final = self.low_carrier_capture(
                stage="store-readback-complete", baseline_stage="snapshot-complete",
            )
            manifest_path.write_text(json.dumps(manifest))
            baseline_path.write_bytes(baseline)
            final_path.write_bytes(final)
            decoded = MODULE.decode_r68e7_low_carrier(final_path, manifest_path, baseline_path)
            self.assertEqual(decoded["stage"], "store-readback-complete")
            self.assertTrue(decoded["stage_fresh"])

            manifest, baseline, final = self.low_carrier_capture(
                stage="store-readback-complete", baseline_stage="store-readback-complete",
            )
            manifest_path.write_text(json.dumps(manifest))
            baseline_path.write_bytes(baseline)
            final_path.write_bytes(final)
            decoded = MODULE.decode_r68e7_low_carrier(final_path, manifest_path, baseline_path)
            self.assertFalse(decoded["stage_fresh"])

    def test_low_carrier_rejects_wrong_x22_x23_even_when_their_delta_is_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, baseline, final = self.low_carrier_capture(
                stage="store-readback-complete", baseline_stage="snapshot-complete",
            )
            early_offset = MODULE.RAW_STAGE_BASE_OFFSET + 0x100
            final = bytearray(final)
            for slot in (8, 9):
                start = early_offset + slot * 8
                value = int.from_bytes(final[start:start + 8], "little") + 0x100
                final[start:start + 8] = value.to_bytes(8, "little")
            manifest_path = root / "readback.json"
            baseline_path = root / "baseline.raw"
            final_path = root / "final.raw"
            manifest_path.write_text(json.dumps(manifest))
            baseline_path.write_bytes(baseline)
            final_path.write_bytes(final)

            decoded = MODULE.decode_r68e7_low_carrier(final_path, manifest_path, baseline_path)
            self.assertTrue(decoded["x9_matches_live_base_arithmetic"])
            self.assertTrue(decoded["x17_matches_early_carrier_payload"])
            self.assertFalse(decoded["x22_matches_expected_base"])
            self.assertFalse(decoded["x23_matches_expected_base"])
            self.assertFalse(decoded["registers_match_contract"])

    def test_c_phase_markers_overwrite_payload_slots_without_becoming_registers(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = root / "readback.json"
            baseline_path = root / "baseline.raw"
            final_path = root / "final.raw"
            overwrite_names = tuple(MODULE.PHASE_MARKERS)

            manifest, baseline, final = self.low_carrier_capture(
                stage="store-readback-complete", baseline_stage="snapshot-complete",
                overwrite_names=overwrite_names,
            )
            manifest_path.write_text(json.dumps(manifest))
            baseline_path.write_bytes(baseline)
            final_path.write_bytes(final)
            decoded = MODULE.decode_r68e7_low_carrier(final_path, manifest_path, baseline_path)

            classified = decoded["c_phase_overwrites"]
            self.assertEqual({item["marker"] for item in classified}, set(overwrite_names))
            self.assertEqual({item["slot"] for item in classified},
                             {MODULE.PHASE_MARKERS[name][0] for name in overwrite_names})
            self.assertEqual(
                {(item["slot"], item["marker"]) for item in classified},
                {(MODULE.PHASE_MARKERS[name][0], name) for name in overwrite_names},
            )
            self.assertTrue(all(item["fresh"] for item in classified))
            self.assertFalse(decoded["low_payload_available"])
            self.assertFalse(decoded["registers_match_contract"])
            self.assertEqual(decoded["stage"], "store-readback-complete")
            self.assertTrue(decoded["stage_fresh"], "C-phase writes to slots5..10 must not erase slot11 stage")

    def test_raw_gate_does_not_treat_live_carrier_words_as_missing_c_markers(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = root / "readback.json"
            baseline_path = root / "baseline.raw"
            final_path = root / "final.raw"
            names = tuple(MODULE.PHASE_MARKERS)

            for overwrite_names in ((), ("ARMINITE",), names):
                manifest, baseline, final = self.low_carrier_capture(
                    stage="store-readback-complete", baseline_stage="snapshot-complete",
                    overwrite_names=overwrite_names,
                )
                manifest_path.write_text(json.dumps(manifest))
                baseline_path.write_bytes(baseline)
                final_path.write_bytes(final)
                failures = MODULE.verify_raw(
                    final_path, manifest_path, baseline_path,
                    require_r68e7_low_carrier=True,
                )
                c_marker_false_positives = [
                    failure for failure in failures
                    if any(failure.startswith(f"raw {name} marker is ")
                           and "expected" in failure for name in names)
                ]
                self.assertEqual(c_marker_false_positives, [])

    def test_raw_gate_rejects_a_bad_same_boot_loadback_even_if_probe_pointer_is_zero(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, baseline, final = self.low_carrier_capture(
                stage="store-readback-complete", baseline_stage="snapshot-complete",
                pointer_value=0,
            )
            manifest_path = root / "readback.json"
            baseline_path = root / "baseline.raw"
            final_path = root / "final.raw"
            manifest_path.write_text(json.dumps(manifest))
            baseline_path.write_bytes(baseline)

            early_offset = MODULE.RAW_STAGE_BASE_OFFSET + 0x100
            final = bytearray(final)
            final[early_offset + 10 * 8:early_offset + 11 * 8] = (0xDEADBEEF).to_bytes(8, "little")
            final_path.write_bytes(final)

            failures = MODULE.verify_raw(
                final_path, manifest_path, baseline_path,
                require_r68e7_low_carrier=True,
            )
            self.assertTrue(any("same-boot immediate load-back" in failure.lower()
                                for failure in failures))

    def test_partial_c_phase_overwrite_does_not_hide_corrupt_live_loadback(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, baseline, final = self.low_carrier_capture(
                stage="store-readback-complete", baseline_stage="snapshot-complete",
                overwrite_names=("ARMINITE",), pointer_value=0,
            )
            manifest_path = root / "readback.json"
            baseline_path = root / "baseline.raw"
            final_path = root / "final.raw"
            manifest_path.write_text(json.dumps(manifest))
            baseline_path.write_bytes(baseline)

            early_offset = MODULE.RAW_STAGE_BASE_OFFSET + 0x100
            final = bytearray(final)
            final[early_offset + 10 * 8:early_offset + 11 * 8] = (0xDEADBEEF).to_bytes(8, "little")
            final_path.write_bytes(final)

            raw_failures = MODULE.verify_raw(
                final_path, manifest_path, baseline_path,
                require_r68e7_low_carrier=True,
            )
            fresh = MODULE.verify_fresh_generation_markers(
                final_path, baseline_path, manifest_path,
            )
            self.assertTrue(any("immediate load-back" in failure.lower()
                                for failure in raw_failures))
            self.assertTrue(any("immediate load-back" in failure.lower()
                                for failure in fresh["failures"]))

    def test_fresh_low_carrier_is_primary_when_independent_a40_window_is_empty(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, baseline, final = self.low_carrier_capture(
                stage="store-readback-complete", baseline_stage="snapshot-complete",
            )
            manifest_path = root / "readback.json"
            baseline_path = root / "baseline.raw"
            final_path = root / "final.raw"
            manifest_path.write_text(json.dumps(manifest))
            baseline_path.write_bytes(baseline)
            final_path.write_bytes(final)

            result = MODULE.verify_fresh_generation_markers(
                final_path, baseline_path, manifest_path,
            )
            primary = result["markers"]["R68E7_LOW_CARRIER"]
            self.assertEqual(primary["stage"], "store-readback-complete")
            self.assertTrue(primary["stage_fresh"])
            self.assertTrue(primary["low_payload_available"])
            self.assertTrue(primary["readback_matches_x17"])
            self.assertFalse(primary["pointer_matches_x17"])
            self.assertEqual(result["failures"], [])

            manifest, baseline, final = self.low_carrier_capture(
                stage="store-readback-complete", baseline_stage="store-readback-complete",
            )
            manifest_path.write_text(json.dumps(manifest))
            baseline_path.write_bytes(baseline)
            final_path.write_bytes(final)
            stale = MODULE.verify_fresh_generation_markers(final_path, baseline_path, manifest_path)
            self.assertFalse(stale["markers"]["R68E7_LOW_CARRIER"]["stage_fresh"])
            self.assertTrue(any("low-carrier stage" in failure.lower()
                                for failure in stale["failures"]))

    def test_probe_captures_the_separate_store_window_derived_from_early_record(self):
        readback = (ROOT / "scripts/y35a/readback_native.py").read_text()
        self.assertIn("p.add_argument('--extra-pa'", readback)
        self.assertIn("append_r68e7_diagnostic_payload(payload, record_pa, fault_pointer_physical)", readback)
        self.assertIn("R68E7_STORE_WINDOW_RECORD = 'r68e7-store-witness'", readback)
        self.assertIn("R68E7_STORE_WINDOW_BYTES", readback)
        self.assertIn("kernel_virtual_base=hex(layout['base'])", readback)
        self.assertIn("kernel_physical_base=hex(base)", readback)

    def test_r68e7_manifest_binds_bootargs_bases_to_the_kernel_layout(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            kernel = root / "kernel.macho"
            kernel.write_bytes(b"kernel-layout-fixture")
            manifest = {
                "kernel_sha256": __import__("hashlib").sha256(kernel.read_bytes()).hexdigest(),
                "kernel_virtual_base": "0xfffffff007004000",
                "kernel_physical_base": "0xa0004000",
                "transport_mode": "minimal-boundary",
                "records": [],
            }
            manifest_path = root / "readback.json"
            manifest_path.write_text(json.dumps(manifest))
            with mock.patch.object(MODULE, "parse_macho", return_value={"base": 0xFFFF_FFF0_0700_4000}):
                self.assertFalse(any("kernel_virtual_base" in error or "kernel_physical_base" in error
                                     for error in MODULE.verify_manifest(
                                         kernel, manifest_path, require_r68e7=True)))

                manifest["kernel_virtual_base"] = "0xfffffff007004100"
                manifest["kernel_physical_base"] = "0xa0004100"
                manifest_path.write_text(json.dumps(manifest))
                errors = MODULE.verify_manifest(kernel, manifest_path, require_r68e7=True)
                self.assertTrue(any("kernel_virtual_base" in error for error in errors))
                self.assertTrue(any("kernel_physical_base" in error for error in errors))

    def test_static_gate_requires_durable_snapshot_and_global_target_cleans(self):
        def marker(register, value):
            return [f"mov {register}, #{(value >> shift) & 0xffff:#x}" if shift == 0
                    else f"movk {register}, #{(value >> shift) & 0xffff:#x}, lsl #{shift}"
                    for shift in (0, 16, 32, 48)]

        body = [
            "str x16, [x20, #0xa40]", "str x17, [x20, #0xa48]",
            "str x9, [x20, #0xa50]", "str x22, [x20, #0xa58]",
            "str x23, [x20, #0xa60]", "add x14, x20, #0xa40",
            "dsb sy", "dc civac, x14", "dsb sy",
            *marker("x15", MODULE.R68E7_STORE_MARKERS["PUBLIN00"][1]),
            "str x15, [x20, #0xa70]", "dsb sy",
            "add x14, x20, #0xa40", "dc civac, x14", "dsb sy",
            "str x17, [x16]", "ldr x14, [x16]",
            "str x14, [x20, #0x850]", "str x14, [x20, #0xa68]",
            "dsb sy", "dc civac, x16", "dsb sy",
            *marker("x15", MODULE.R68E7_STORE_MARKERS["PUBLRD00"][1]),
            "str x15, [x20, #0xa78]", "dsb sy",
            "add x14, x20, #0xa40", "dc civac, x14", "dsb sy",
        ]
        self.assertEqual(MODULE.verify_r68e7_store_window_disassembly("\n".join(body)), [])
        wrong_order = body.copy()
        low_readback = wrong_order.index("str x14, [x20, #0x850]")
        wrong_order[low_readback], wrong_order[low_readback + 1] = \
            wrong_order[low_readback + 1], wrong_order[low_readback]
        self.assertTrue(MODULE.verify_r68e7_store_window_disassembly("\n".join(wrong_order)))
        missing_primary = body.copy()
        missing_primary.remove("str x14, [x20, #0x850]")
        self.assertTrue(MODULE.verify_r68e7_store_window_disassembly("\n".join(missing_primary)))
        without_cleans = [line for line in body if not line.startswith("dc civac")]
        failures = MODULE.verify_r68e7_store_window_disassembly("\n".join(without_cleans))
        self.assertTrue(any("must clean" in failure for failure in failures))

    def low_carrier_disassembly_body(self):
        def marker(register, value):
            return [f"mov {register}, #{(value >> shift) & 0xffff:#x}" if shift == 0
                    else f"movk {register}, #{(value >> shift) & 0xffff:#x}, lsl #{shift}"
                    for shift in (0, 16, 32, 48)]

        lines = [
            "str x16, [x20, #0x828]", "str x17, [x20, #0x830]",
            "str x9, [x20, #0x838]", "str x22, [x20, #0x840]",
            "str x23, [x20, #0x848]",
            "add x14, x20, #0x800", "dsb sy", "dc civac, x14", "dsb sy",
            "add x14, x20, #0x840", "dsb sy", "dc civac, x14", "dsb sy",
            *marker("x15", next(value for value, label in MODULE.R68E7_LOW_STAGE_MARKERS.items()
                                 if label == "snapshot-complete")),
            "str x15, [x20, #0x858]",
            "add x14, x20, #0x840", "dsb sy", "dc civac, x14", "dsb sy",
            "str x17, [x16]", "ldr x14, [x16]", "str x14, [x20, #0x850]",
            "dsb sy", "dc civac, x16", "dsb sy",
            "add x14, x20, #0x800", "dsb sy", "dc civac, x14", "dsb sy",
            "add x14, x20, #0x840", "dsb sy", "dc civac, x14", "dsb sy",
            *marker("x15", next(value for value, label in MODULE.R68E7_LOW_STAGE_MARKERS.items()
                                 if label == "store-readback-complete")),
            "str x15, [x20, #0x858]",
            "add x14, x20, #0x840", "dsb sy", "dc civac, x14", "dsb sy",
        ]
        return lines

    def test_low_carrier_static_gate_binds_cache_clean_ranges_and_barriers(self):
        valid = self.low_carrier_disassembly_body()
        self.assertEqual(MODULE.verify_r68e7_low_carrier_disassembly("\n".join(valid)), [])

        cases = []
        missing_preclean = valid.copy()
        del missing_preclean[5:9]
        cases.append(missing_preclean)

        wrong_range = valid.copy()
        wrong_range[5] = "add x14, x20, #0x808"
        cases.append(wrong_range)

        missing_barrier = valid.copy()
        del missing_barrier[6]
        cases.append(missing_barrier)

        missing_postreadback_line = valid[:-4]
        cases.append(missing_postreadback_line)

        for body in cases:
            with self.subTest(body=body):
                self.assertTrue(MODULE.verify_r68e7_low_carrier_disassembly("\n".join(body)))

    def test_decoder_checks_live_arithmetic_payload_pointer_and_marker_freshness(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, baseline, final = self.r68e7_capture()
            manifest_path = root / "readback.json"
            baseline_path = root / "baseline.raw"
            final_path = root / "final.raw"
            manifest_path.write_text(json.dumps(manifest))
            baseline_path.write_bytes(baseline)
            final_path.write_bytes(final)
            without_baseline = MODULE.decode_r68e7_store_window(final_path, manifest_path)
            self.assertTrue(without_baseline["snapshot_present"])
            self.assertFalse(without_baseline["snapshot_fresh"])
            decoded = MODULE.decode_r68e7_store_window(final_path, manifest_path, baseline_path)
            self.assertTrue(decoded["snapshot_fresh"])
            self.assertTrue(decoded["readback_fresh"])
            self.assertTrue(decoded["registers_match_contract"])
            self.assertTrue(decoded["loadback_matches_payload"])
            self.assertTrue(decoded["pointer_matches_payload"])

            manifest, baseline, final = self.r68e7_capture(corrupt_x9=True)
            manifest_path.write_text(json.dumps(manifest))
            baseline_path.write_bytes(baseline)
            final_path.write_bytes(final)
            decoded = MODULE.decode_r68e7_store_window(final_path, manifest_path, baseline_path)
            self.assertFalse(decoded["x9_matches_arithmetic"])
            self.assertFalse(decoded["registers_match_contract"])

    def test_alias_decoder_distinguishes_mmu_state_from_kva_store_return(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, baseline, final = self.r68e7_capture(mmu=True, kva=True)
            manifest_path = root / "readback.json"
            baseline_path = root / "baseline.raw"
            final_path = root / "final.raw"
            manifest_path.write_text(json.dumps(manifest))
            baseline_path.write_bytes(baseline)
            final_path.write_bytes(final)
            decoded = MODULE.decode_r68e7_alias_witnesses(final_path, manifest_path, baseline_path)
            self.assertEqual(decoded["status"], "mmu-and-both-alias-witnesses-fresh")
            without_baseline = MODULE.decode_r68e7_alias_witnesses(final_path, manifest_path)
            self.assertTrue(without_baseline["kva_alias_present"])
            self.assertFalse(without_baseline["kva_alias_fresh"])

            manifest, baseline, final = self.r68e7_capture(mmu=True, kva=False)
            manifest_path.write_text(json.dumps(manifest))
            baseline_path.write_bytes(baseline)
            final_path.write_bytes(final)
            decoded = MODULE.decode_r68e7_alias_witnesses(final_path, manifest_path, baseline_path)
            self.assertEqual(decoded["status"], "mmu-and-vp-witness-fresh-kva-witness-absent")

            manifest, baseline, final = self.r68e7_capture(mmu=False, kva=False)
            manifest_path.write_text(json.dumps(manifest))
            baseline_path.write_bytes(baseline)
            final_path.write_bytes(final)
            decoded = MODULE.decode_r68e7_alias_witnesses(final_path, manifest_path, baseline_path)
            self.assertEqual(decoded["status"], "vp-witness-fresh-mmu-not-proven-on")


if __name__ == "__main__":
    unittest.main()
