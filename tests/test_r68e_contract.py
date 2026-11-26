#!/usr/bin/env python3
import importlib.util
from pathlib import Path
import sys
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


class R68EContractTest(unittest.TestCase):
    def test_pointer_window_manifest_binds_the_global_symbol(self):
        import readback_native
        records = [{"name": "fault-pointer-window", "physical": "0xa06d2100", "size": 16}]
        readback_native.annotate_fault_pointer_window(
            records,
            {"_native_early_fault_address": 0xFFFF_FFF0_076D_2108},
            {"base": 0xFFFF_FFF0_0700_4000},
            0xA000_4000,
        )
        self.assertEqual(records[0]["symbol_physical"], "0xa06d2108")
        self.assertEqual(records[0]["symbol_offset"], 8)

        records[0]["physical"] = "0xa06d2110"
        with self.assertRaisesRegex(ValueError, "does not contain"):
            readback_native.annotate_fault_pointer_window(
                records,
                {"_native_early_fault_address": 0xFFFF_FFF0_076D_2108},
                {"base": 0xFFFF_FFF0_0700_4000},
                0xA000_4000,
            )

    def test_minimal_probe_binds_fault_pointer_and_kernel_bases(self):
        import readback_native
        layout = {'base': 0xFFFF_FFF0_0700_4000,
                  'end': 0xFFFF_FFF0_0701_0000,
                  'segments': [{'address': 0xFFFF_FFF0_0700_4000,
                                'size': 0x10000}]}
        symbols = {'_native_early_fault_address': 0xFFFF_FFF0_0700_5008}
        records = readback_native.minimal_boundary_records([
            ('fault-pointer-window', 0xA000_5000, 16)])
        readback_native.annotate_fault_pointer_window(records, symbols, layout, 0xA000_4000)
        self.assertEqual(records[0]['symbol_physical'], '0xa0005008')
        self.assertEqual(records[0]['symbol_offset'], 8)

    def test_entry_path_window_starts_after_the_original_64_slot_carrier(self):
        import readback_native
        self.assertEqual(readback_native.entry_path_window_physical(0xA0B7C800), 0xA0B7CA00)
        self.assertEqual(readback_native.ENTRY_PATH_WINDOW_BYTES, 16)

    def test_r68e7_store_window_is_adjacent_to_the_early_fault_record(self):
        import readback_native
        self.assertEqual(readback_native.r68e7_store_window_physical(0xA0B7C800), 0xA0B7CA40)
        self.assertEqual(readback_native.R68E7_STORE_WINDOW_BYTES, 64)
        self.assertEqual(readback_native.r68e7_diagnostic_payload(0xA0B7C800), [
            ("handoff-witness", 0xA0B7C9C0, 16),
            ("fault-publish-window", 0xA0B7C9D0, 48),
            ("r68e7-store-witness", 0xA0B7CA40, 64),
        ])
        self.assertEqual(readback_native.r68e7_diagnostic_payload(
            0xA0B7C800, 0xA06D2100
        )[-1], ("fault-pointer-window", 0xA06D2100, 16))
        with self.assertRaisesRegex(ValueError, "conflicts"):
            readback_native.append_r68e7_diagnostic_payload(
                [("handoff-witness", 0xA0B7C9B0, 16)], 0xA0B7C800
            )

    def test_path_marker_is_after_vbar_and_readback_echo_uses_slot65(self):
        patch = (ROOT / "patches/xnu/native-r68e-entry-path-witness.patch").read_text()
        self.assertLess(patch.index("MSR_VBAR_EL1_X0"),
                        patch.index("str\t\tx15, [x20, #0xa00]"))
        self.assertIn("ldr\t\tx16, [x20, #0xa00]", patch)
        self.assertIn("str\t\tx16, [x20, #0xa08]", patch)
        self.assertIn("dc\t\tcivac, x14", patch)
        self.assertNotIn("R68ESND0", patch)
        self.assertNotIn("str x15, [x20, #0xa08]", patch)

    def test_pre_mmu_marker_identifies_the_r68e_generation(self):
        value = MODULE.HANDOFF_MARKERS["PREMMU00"][1]
        self.assertEqual(value, int.from_bytes(b"R68E7PM0", "little"))
        self.assertNotEqual(value, int.from_bytes(b"PREMMU00", "little"))
        self.assertEqual(MODULE.PREVIOUS_GENERATION_MARKERS["PREMMU00"],
                         int.from_bytes(b"R68E6PM0", "little"))
        self.assertEqual(MODULE.HANDOFF_MARKERS["FPBEFOR0"][1],
                         int.from_bytes(b"R68E7BF0", "little"))
        self.assertEqual(MODULE.HANDOFF_MARKERS["FPSTOR00"][1],
                         int.from_bytes(b"R68E7ST0", "little"))
        self.assertEqual(MODULE.HANDOFF_MARKERS["PUBLPR00"][1],
                         int.from_bytes(b"R68E7PR0", "little"))
        self.assertEqual(MODULE.HANDOFF_MARKERS["PUBLPS00"][1],
                         int.from_bytes(b"R68E7PS0", "little"))
        self.assertEqual(MODULE.HANDOFF_ORDER.count("PUBLPR00"), 1)
        self.assertEqual(MODULE.HANDOFF_ORDER.count("PUBLPS00"), 1)

    def test_entry_path_markers_are_diagnostic_and_do_not_claim_secondary_path(self):
        markers = MODULE.ENTRY_PATH_MARKERS
        self.assertEqual(markers["FIRST_CPU"][0], 64)
        self.assertEqual(markers["FIRST_CPU"][1], int.from_bytes(b"R68E7FS0", "little"))
        self.assertEqual(MODULE.PREVIOUS_GENERATION_MARKERS["FIRST_CPU"],
                         int.from_bytes(b"R68E6FS0", "little"))
        self.assertNotIn("SECONDARY_CPU", markers)

        patch = (ROOT / "patches/xnu/native-r68e-entry-path-witness.patch").read_text()
        self.assertIn("str\t\tx15, [x20, #0xa00]", patch)
        self.assertIn("str\t\tx16, [x20, #0xa08]", patch)
        self.assertIn("R68E6FS0", patch)
        handoff_patch = (ROOT / "patches/xnu/native-handoff-witness.patch").read_text()
        self.assertIn("movk\tx14, #0x5036, lsl #32", handoff_patch)
        self.assertIn("movk\tx14, #0x304d, lsl #48", handoff_patch)

    def test_builder_applies_entry_path_witness_after_r68e_boundary_patch(self):
        source = (ROOT / "scripts/build-xnu-4903-kernel.py").read_text()
        boundary = source.index("native-r68e-boundary-witness.patch")
        path_witness = source.index("native-r68e-entry-path-witness.patch")
        self.assertLess(boundary, path_witness)

    def test_post_sctlr_witness_reads_control_register_and_cleans_kva_lines(self):
        patch = (ROOT / "patches/xnu/native-handoff-witness.patch").read_text()
        required = (
            "isb\t\tsy",
            "mrs\t\tx11, SCTLR_EL1",
            "str\t\tx11, [x12, #0x9c8]",
            "dc\t\tcivac, x14",
            "dsb\t\tsy",
        )
        for instruction in required:
            with self.subTest(instruction=instruction):
                self.assertIn(instruction, patch)
        self.assertNotIn("str\t\tx15, [x20, #0x9c0]", patch)
        self.assertIn("add\t\tx12, x20, x22", patch)
        self.assertIn("sub\t\tx12, x12, x23", patch)

    def test_mapping_diagnostic_patches_preserve_x14_x15_cursor_registers(self):
        sources = {
            "VPMAP000": ROOT / "patches/xnu/native-startup-witness.patch",
            "KVAMAP00": ROOT / "patches/xnu/native-startup-witness.patch",
            "VPPRE000": ROOT / "patches/xnu/native-mapping-witness.patch",
            "VPCALL00": ROOT / "patches/xnu/native-mapping-witness.patch",
            "KVPRE000": ROOT / "patches/xnu/native-mapping-witness.patch",
            "KVCALL00": ROOT / "patches/xnu/native-mapping-witness.patch",
            "L1ALLOC0": ROOT / "patches/xnu/native-header-adjust-witness.patch",
            "MAPDONE0": ROOT / "patches/xnu/native-pre-mmu-witness.patch",
            "COMMON00": ROOT / "patches/xnu/native-pre-mmu-witness.patch",
            "TTBRDONE": ROOT / "patches/xnu/native-pre-mmu-witness.patch",
        }
        for marker, path in sources.items():
            patch = path.read_text()
            start = patch.index(marker)
            end = patch.find("#endif", start)
            block = patch[start:end if end >= 0 else None]
            with self.subTest(marker=marker):
                self.assertRegex(block, r"mov\s+x16,")
                self.assertNotRegex(block, r"(?:mov|movk|add|sub)\s+x(?:14|15),")
                self.assertNotRegex(block, r"add\s+x14,\s*x20,\s*x22")

    def test_cold_entry_readback_marker_is_after_vbar_and_has_an_echo(self):
        patch = (ROOT / "patches/xnu/native-r68e-entry-path-witness.patch").read_text()
        self.assertLess(patch.index("MSR_VBAR_EL1_X0"),
                        patch.index("str\t\tx15, [x20, #0xa00]"))
        self.assertIn("ldr\t\tx16, [x20, #0xa00]", patch)
        self.assertIn("str\t\tx16, [x20, #0xa08]", patch)
        self.assertIn("dc\t\tcivac", patch)
        self.assertNotIn("str x15, [x20, #0xa08]", patch)

    def test_fault_publish_gate_reads_arithmetic_bases_and_actual_global_value(self):
        self.assertEqual(MODULE.FAULT_PUBLISH_WINDOW_RECORD, "fault-publish-window")
        self.assertEqual(MODULE.FAULT_POINTER_WINDOW_RECORD, "fault-pointer-window")
        self.assertEqual(MODULE.FAULT_POINTER_VALUE_OFFSET, 8)
        source = (ROOT / "scripts/y35a/verify_phase_instrumentation.py").read_text()
        self.assertIn("translated_candidate_matches_formula", source)
        self.assertIn("published_global_value", source)

    def test_fault_publish_witness_is_checked_on_the_isolated_cold_entry_body(self):
        source = (ROOT / "scripts/y35a/verify_phase_instrumentation.py").read_text()
        start = source.index("def main()")
        self.assertIn("verify_fault_publish_disassembly(first_cpu_body)", source[start:])
        handoff = source[source.index("def verify_handoff_disassembly("):start]
        self.assertNotIn("verify_fault_publish_disassembly(body)", handoff)

    def test_objdump_instruction_normalizer_removes_address_and_bytes(self):
        raw = "\n".join((
            "fffffff0072707b8:\t00 20 18 d5\tmsr\tSCTLR_EL1, x0",
            "fffffff0072707bc:\tdf 3f 03 d5\tisb\tsy",
        ))
        self.assertEqual(
            MODULE.normalize_disassembly_body(raw),
            "msr\tSCTLR_EL1, x0\nisb\tsy",
        )

    def test_r68e6_captures_x9_before_direct_store_and_operands_after_return(self):
        producer = (ROOT / "patches/xnu/native-fault-publish-witness.patch").read_text()
        boundary = (ROOT / "patches/xnu/native-r68e-boundary-witness.patch").read_text()
        for required in (
            "sub x9, x16, x22",
            "add x9, x9, x23",
            "str x9, [x20, #0x968]",
            "str x17, [x16]",
            "str x15, [x20, #0x958]",
            "str x15, [x20, #0x960]",
            "movk x15, #0x4236, lsl #32",
            "movk x15, #0x5336, lsl #32",
        ):
            with self.subTest(required=required):
                self.assertIn(required, producer)
        self.assertNotIn("str x17, [x9]", producer)
        producer_lines = producer.splitlines()
        formula = next(i for i,line in enumerate(producer_lines) if "sub x9, x16, x22" in line)
        formula_add = next(i for i,line in enumerate(producer_lines) if "add x9, x9, x23" in line)
        input_capture = next(i for i,line in enumerate(producer_lines) if "str x9, [x20, #0x968]" in line)
        before = next(i for i,line in enumerate(producer_lines) if "FPBEFOR0" in line)
        store = next(i for i,line in enumerate(producer_lines) if "str x17, [x16]" in line)
        store_return = next(i for i,line in enumerate(producer_lines) if "FPSTOR00" in line)
        self.assertEqual(formula_add, formula + 1)
        self.assertLess(formula, formula_add)
        self.assertLess(formula_add, input_capture)
        self.assertLess(input_capture, before)
        self.assertLess(before, store)
        self.assertLess(store, store_return)

        for required in (
            "str x16, [x20, #0x9d0]",
            "str x17, [x20, #0x9d8]",
            "str x9, [x20, #0x9e0]",
            "str x15, [x20, #0x9f0]",
            "movk x15, #0x5036, lsl #32",
            "movk x15, #0x3052, lsl #48",
            "movk x15, #0x3053, lsl #48",
        ):
            with self.subTest(required=required):
                self.assertIn(required, boundary)
        self.assertNotIn("sub x9, x16, x22", boundary)
        self.assertLess(boundary.index("FPSTOR00"), boundary.index("PUBLPR00"))
        self.assertLess(boundary.index("PUBLPR00"), boundary.index("str x16, [x20, #0x9d0]"))
        self.assertLess(boundary.index("str x9, [x20, #0x9e0]"), boundary.index("PUBLPS00"))

    def test_builder_applies_the_r68e_patch_after_existing_instrumentation(self):
        source = (ROOT / "scripts/build-xnu-4903-kernel.py").read_text()
        self.assertIn("native-r68e-boundary-witness.patch", source)


if __name__ == "__main__":
    unittest.main()
