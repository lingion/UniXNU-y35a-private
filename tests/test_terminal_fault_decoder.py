"""Offline terminal-fault decoding contracts; no device or build operations."""
import copy
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/y35a"))
from decode_terminal_fault import decode_terminal_fault

BASE = 0xFFFFFFF007004000
PHYS = 0xA0004000
PC = BASE + 0x430
EVIDENCE = ROOT / "evidence/y35a-20261102/boot3-20261106"


def kernel_fixture(word=0x4F00E400):
    """A linked ARM64 Mach-O with executable text, symbols, and a data segment."""
    text = struct.pack("<II16sQQQQiiII", 25, 152, b"__TEXT", BASE, 0x1000,
                       0, 0x1000, 5, 5, 1, 0)
    text += struct.pack("<16s16sQQIIIIIIII", b"__text", b"__TEXT",
                        BASE + 0x400, 0x100, 0x400, 2, 0, 0, 0x80000400, 0, 0, 0)
    data = struct.pack("<II16sQQQQiiII", 25, 72, b"__DATA", BASE + 0x1000,
                       0x1000, 0x1000, 0x100, 3, 3, 0, 0)
    names = b"\0_cpu_data_init\0_after\0"
    symbols = struct.pack("<IBBHQ", 1, 0xF, 1, 0, BASE + 0x400)
    symbols += struct.pack("<IBBHQ", 16, 0xF, 1, 0, BASE + 0x480)
    symtab = struct.pack("<6I", 2, 24, 0x800, 2, 0x900, len(names))
    thread = bytearray(288)
    struct.pack_into("<4I", thread, 0, 5, 288, 6, 68)
    struct.pack_into("<Q", thread, 272, BASE + 0x400)
    commands = text + data + symtab + thread
    image = bytearray(0x1100)
    image[:32] = struct.pack("<8I", 0xFEEDFACF, 0x100000C, 0, 2, 4,
                             len(commands), 0, 0)
    image[32:32 + len(commands)] = commands
    struct.pack_into("<I", image, 0x430, word)
    image[0x800:0x800 + len(symbols)] = symbols
    image[0x900:0x900 + len(names)] = names
    return bytes(image)


class DecoderTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.kernel = self.root / "kernel.macho"
        self.kernel.write_bytes(kernel_fixture())
        self.probe = self.root / "probe.img"
        self.probe.write_bytes(b"local offline probe fixture")
        self.manifest = {
            "kernel_sha256": hashlib.sha256(self.kernel.read_bytes()).hexdigest(),
            "image_sha256": hashlib.sha256(self.probe.read_bytes()).hexdigest(),
            "kernel_virtual_base": hex(BASE),
            "kernel_physical_base": hex(PHYS),
            "transport_mode": "minimal-boundary",
            "report_bytes": 0x400,
            "records": [
                {"name": "unrelated", "size": 16, "report_offset": 0x100},
                {"name": "early-fault-record", "physical": "0xa0b94800",
                 "size": 384, "report_offset": 0x180},
            ],
        }
        self.manifest_path = self.root / "readback.json"
        self.raw_path = self.root / "final.raw"
        self.baseline_path = self.root / "baseline.raw"
        self.baseline = self.capture()
        self.raw = self.capture(b"Y35ALV02", PC, 0x1FE00000, 0)

    def offset(self):
        record = self.manifest["records"][1]
        return (0x10000 + record["report_offset"]
                if self.manifest["transport_mode"] == "minimal-boundary"
                else record["offset"])

    def capture(self, magic=b"\0" * 8, elr=0, esr=0, far=0, lr=0):
        data = bytearray(0x11000)
        prefix = bytes.fromhex(self.manifest["kernel_sha256"][:16])
        if self.manifest["transport_mode"] == "minimal-boundary":
            data[0x10000:0x10010] = b"Y35AXNU2" + prefix
            data[0x10040:0x10050] = b"Y35ARD02" + prefix
        else:
            data[:16] = b"Y35ARD01" + prefix
        struct.pack_into("<8sQQQQ", data, self.offset(), magic, elr, esr, far, lr)
        return data

    def run_decode(self, baseline=True, boot=None):
        self.manifest_path.write_text(json.dumps(self.manifest))
        self.raw_path.write_bytes(self.raw)
        self.baseline_path.write_bytes(self.baseline)
        return decode_terminal_fault(
            kernel=self.kernel, manifest=self.manifest_path, probe=self.probe,
            raw=self.raw_path, baseline=self.baseline_path if baseline else None,
            boot_manifest=boot, disassemble=False,
        )

    def test_fresh_v2_uses_named_record_and_exact_instruction(self):
        result = self.run_decode()
        self.assertEqual(result["status"], "fresh", result)
        self.assertTrue(result["verified_fault"])
        self.assertEqual(result["record"]["raw_offset"], "0x10180")
        self.assertEqual(result["fault"]["esr"], {
            "value": "0x1fe00000", "ec": 7, "ec_name": "FP/SIMD access trap",
            "il": 1, "iss": "0x1e00000",
        })
        self.assertFalse(result["fault"]["far"]["valid"])
        insn = result["instruction"]
        self.assertEqual(insn["pc"], hex(PC))
        self.assertEqual(insn["instruction_word"], "0x4f00e400")
        self.assertEqual(insn["file_offset"], "0x430")
        self.assertEqual(insn["nearest_symbol"], "_cpu_data_init")
        self.assertEqual(insn["symbol_offset"], "0x30")

    def test_v1_low_physical_elr_is_translated_using_manifest(self):
        self.raw = self.capture(b"Y35ALV01", PHYS + 0x430, 0x02000000, 0x1234)
        result = self.run_decode()
        self.assertEqual(result["status"], "fresh", result)
        self.assertEqual(result["instruction"]["pc"], hex(PC))
        self.assertEqual(result["instruction"]["address_mode"], "physical-to-virtual")
        self.assertFalse(result["fault"]["far"]["valid"])
        self.assertIsNone(result["fault"]["far"]["address"])

    def test_full_readback_offsets_are_not_minimal_offsets(self):
        self.manifest["transport_mode"] = "full-readback"
        self.manifest["staged_bytes"] = 0x11000
        self.manifest["records"][0] = {"name": "unrelated", "offset": 0x80, "size": 16}
        self.manifest["records"][1]["offset"] = 0x120
        self.baseline = self.capture()
        self.raw = self.capture(b"Y35ALV02", PC, 0x1FE00000, 0)
        result = self.run_decode()
        self.assertEqual(result["record"]["raw_offset"], "0x120")
        self.assertTrue(result["verified_fault"], result)

    def test_bad_artifact_and_capture_bindings_fail_closed(self):
        cases = ("kernel", "probe", "capture-tag", "shim-tag", "baseline-tag", "header")
        for case in cases:
            with self.subTest(case=case):
                kernel = self.kernel.read_bytes()
                probe = self.probe.read_bytes()
                raw, baseline = self.raw[:], self.baseline[:]
                if case == "kernel":
                    self.kernel.write_bytes(kernel + b"corruption")
                elif case == "probe":
                    self.probe.write_bytes(b"wrong probe")
                elif case == "capture-tag":
                    self.raw[0x10048] ^= 1
                elif case == "shim-tag":
                    self.raw[0x10008] ^= 1
                elif case == "baseline-tag":
                    self.baseline[0x10048] ^= 1
                else:
                    self.raw[0x10040] ^= 1
                result = self.run_decode()
                self.assertEqual(result["status"], "invalid", result)
                self.assertFalse(result["verified_fault"])
                self.assertIsNone(result["fault"])
                self.kernel.write_bytes(kernel)
                self.probe.write_bytes(probe)
                self.raw, self.baseline = raw, baseline

    def test_baseline_may_retain_previous_shim_generation(self):
        self.baseline[0x10008:0x10010] = b"previous"
        self.assertTrue(self.run_decode()["verified_fault"])

    def test_missing_baseline_never_claims_freshness(self):
        result = self.run_decode(baseline=False)
        self.assertEqual(result["status"], "unverified")
        self.assertEqual(result["freshness"], "unknown")
        self.assertFalse(result["verified_fault"])

    def test_truncated_baseline_cannot_establish_freshness(self):
        self.baseline = self.baseline[:self.offset() + 24]
        result = self.run_decode()
        self.assertEqual(result["status"], "partial")
        self.assertFalse(result["verified_fault"])

    def test_unknown_ec_is_preserved_without_inventing_far_meaning(self):
        self.raw = self.capture(b"Y35ALV02", PC, (0x3F << 26) | (1 << 25), 7)
        result = self.run_decode()
        self.assertEqual(result["fault"]["esr"]["ec_name"], "Unknown exception class")
        self.assertFalse(result["fault"]["far"]["valid"])

    def test_bad_section_or_symbol_metadata_is_rejected(self):
        original = self.kernel.read_bytes()
        for offset, value in ((32 + 64, 0xFFFFFFFF), (0x800, 0xFFFFFF),
                              (32 + 152 + 72 + 16, 0xFFFFFF)):
            with self.subTest(offset=offset):
                altered = bytearray(original)
                struct.pack_into("<I", altered, offset, value)
                self.kernel.write_bytes(altered)
                self.manifest["kernel_sha256"] = hashlib.sha256(altered).hexdigest()
                self.baseline = self.capture()
                self.raw = self.capture(b"Y35ALV02", PC, 0x1FE00000, 0)
                result = self.run_decode()
                self.assertEqual(result["status"], "invalid", result)
                self.assertFalse(result["verified_fault"])

    def test_identical_tuple_is_unchanged_even_if_other_carrier_slots_change(self):
        self.baseline = self.raw[:]
        struct.pack_into("<Q", self.raw, self.offset() + 5 * 8, 0x41524D494E495445)
        result = self.run_decode()
        self.assertEqual(result["status"], "unchanged")
        self.assertFalse(result["verified_fault"])

    def test_same_commit_with_changed_payload_is_not_uniquely_fresh(self):
        self.baseline = self.capture(b"Y35ALV02", PC + 4, 0x1FE00000, 0)
        result = self.run_decode()
        self.assertEqual(result["status"], "changed")
        self.assertEqual(result["freshness"], "ambiguous")
        self.assertFalse(result["verified_fault"])

    def test_new_version_commit_can_be_fresh_against_old_version(self):
        self.baseline = self.capture(b"Y35ALV01", PHYS + 0x430, 0x02000000, 0)
        self.assertTrue(self.run_decode()["verified_fault"])

    def test_v3_uses_same_four_fields_and_ignores_slot13_chain(self):
        self.baseline = self.capture(b"Y35ALV02", PC, 0x1FE00000, 0)
        self.raw = self.capture(b"Y35ALV03", PC, 0x1FE00000, 0)
        struct.pack_into("<Q", self.raw, self.offset() + 13 * 8,
                         int.from_bytes(b"R73ARM00", "little"))
        result = self.run_decode()
        self.assertEqual(result["status"], "fresh", result)
        self.assertEqual(result["record"]["magic"], "Y35ALV03")
        self.assertEqual(result["fault"]["esr"]["ec"], 7)
        self.assertEqual(result["instruction"]["instruction_word"], "0x4f00e400")
        self.assertNotIn("R73ARM00", result.get("phase_markers", {}))

    def test_zero_terminal_record_is_missing_despite_positive_phase_markers(self):
        self.raw = self.capture()
        struct.pack_into("<Q", self.raw, self.offset() + 9 * 8, 0x50414E4943494E49)
        result = self.run_decode()
        self.assertEqual(result["status"], "missing")
        self.assertIsNone(result["fault"])
        self.assertFalse(result["verified_fault"])
        self.assertEqual(result["phase_markers"]["PANICINI"]["freshness"], "fresh")

    def test_v4_decodes_link_register_and_maps_return_call_site(self):
        lr = BASE + 0x440
        data = bytearray(self.kernel.read_bytes())
        struct.pack_into("<I", data, 0x43c, 0x94000000)
        self.kernel.write_bytes(data)
        self.manifest["kernel_sha256"] = hashlib.sha256(data).hexdigest()
        prefix = bytes.fromhex(self.manifest["kernel_sha256"][:16])
        self.probe.write_bytes(b"local offline probe fixture v4")
        self.manifest["image_sha256"] = hashlib.sha256(self.probe.read_bytes()).hexdigest()
        self.raw = self.capture(b"Y35ALV04", PC, 0x96000005, 0xb, lr)
        self.baseline = self.capture()
        result = self.run_decode()
        self.assertEqual(result["status"], "fresh", result)
        self.assertEqual(result["record"]["decoded_bytes"], 40)
        self.assertEqual(result["record"]["link_register"], hex(lr))
        self.assertEqual(result["record"]["return_call_pc"], hex(lr - 4))
        self.assertTrue(result["instruction"]["return_call_site"]["is_bl"])
        self.assertEqual(result["instruction"]["return_call_site"]["instruction_word"],
                         "0x94000000")

    def test_v5_generation_commit_also_decodes_interrupted_link_register(self):
        lr = BASE + 0x440
        data = bytearray(self.kernel.read_bytes())
        struct.pack_into("<I", data, 0x43c, 0x94000000)
        self.kernel.write_bytes(data)
        self.manifest["kernel_sha256"] = hashlib.sha256(data).hexdigest()
        self.probe.write_bytes(b"local offline probe fixture v5")
        self.manifest["image_sha256"] = hashlib.sha256(self.probe.read_bytes()).hexdigest()
        self.raw = self.capture(b"Y35ALV05", PC, 0x96000005, 0xb, lr)
        self.baseline = self.capture()
        result = self.run_decode()
        self.assertEqual(result["status"], "fresh", result)
        self.assertEqual(result["record"]["magic"], "Y35ALV05")
        self.assertEqual(result["record"]["link_register"], hex(lr))
        self.assertTrue(result["instruction"]["return_call_site"]["is_bl"])
        self.assertEqual(result["phase_markers"]["PANICINI"]["meaning"], "panic initialization checkpoint, not a panic event")

    def test_v7_generation_commit_decodes_link_register_call_site(self):
        lr = BASE + 0x440
        data = bytearray(self.kernel.read_bytes())
        struct.pack_into("<I", data, 0x43c, 0x94000000)
        self.kernel.write_bytes(data)
        self.manifest["kernel_sha256"] = hashlib.sha256(data).hexdigest()
        self.probe.write_bytes(b"local offline probe fixture v7")
        self.manifest["image_sha256"] = hashlib.sha256(self.probe.read_bytes()).hexdigest()
        self.raw = self.capture(b"Y35ALV07", PC, 0x96000005, 0xb, lr)
        self.baseline = self.capture()
        result = self.run_decode()
        self.assertEqual(result["status"], "fresh", result)
        self.assertEqual(result["record"]["magic"], "Y35ALV07")
        self.assertEqual(result["record"]["link_register"], hex(lr))
        self.assertTrue(result["instruction"]["return_call_site"]["is_bl"])

    def test_uncommitted_or_truncated_or_empty_payload_is_partial(self):
        cases = [
            self.capture(b"\0" * 8, PC, 0x1FE00000, 0),
            self.capture(b"Y35ALV02", 0, 0, 0),
            self.raw[:self.offset() + 24],
            self.capture(b"Y35ALV02", PC, 1 << 40, 0),
        ]
        for data in cases:
            with self.subTest(size=len(data)):
                self.raw = data
                result = self.run_decode()
                self.assertEqual(result["status"], "partial", result)
                self.assertFalse(result["verified_fault"])

    def test_unknown_magic_is_never_accepted(self):
        self.raw = self.capture(b"Y35ALV99", PC, 0x1FE00000, 0)
        self.assertEqual(self.run_decode()["status"], "unsupported")

    def test_unknown_unaligned_data_and_zero_fill_elrs_are_not_guessed(self):
        for pc in (0x12345678, PC + 1, BASE + 0x1000, BASE + 0x1800,
                   BASE + 0x3000, 0xFFFFFFFFFFFFFFFF):
            with self.subTest(pc=hex(pc)):
                self.raw = self.capture(b"Y35ALV02", pc, 0x1FE00000, 0)
                result = self.run_decode()
                self.assertEqual(result["instruction"]["status"], "unmapped", result)
                self.assertIsNone(result["instruction"]["instruction_word"])
                self.assertIsNone(result["instruction"]["nearest_symbol"])
                self.assertFalse(result["verified_fault"])

    def test_low_elr_requires_explicit_bases(self):
        self.manifest.pop("kernel_physical_base")
        self.manifest.pop("kernel_virtual_base")
        self.raw = self.capture(b"Y35ALV01", PHYS + 0x430, 0x02000000, 0)
        self.assertEqual(self.run_decode()["instruction"]["status"], "unmapped")

    def test_boot_manifest_can_supply_bases_and_must_agree(self):
        boot = self.root / "boot.json"
        value = {k: self.manifest[k] for k in
                 ("kernel_sha256", "kernel_virtual_base", "kernel_physical_base")}
        boot.write_text(json.dumps(value))
        self.manifest.pop("kernel_virtual_base")
        self.manifest.pop("kernel_physical_base")
        self.raw = self.capture(b"Y35ALV01", PHYS + 0x430, 0x02000000, 0)
        self.assertTrue(self.run_decode(boot=boot)["verified_fault"])
        self.manifest["kernel_virtual_base"] = hex(BASE)
        self.manifest["kernel_physical_base"] = hex(PHYS + 0x200000)
        self.assertEqual(self.run_decode(boot=boot)["status"], "invalid")

    def test_wrong_virtual_base_is_rejected(self):
        self.manifest["kernel_virtual_base"] = hex(BASE + 0x1000)
        self.assertEqual(self.run_decode()["status"], "invalid")

    def test_invalid_boot_hash_returns_a_structured_error(self):
        boot = self.root / "boot.json"
        for value in (None, 123, [], "not-a-sha256"):
            with self.subTest(value=value):
                boot.write_text(json.dumps({"kernel_sha256": value}))
                result = self.run_decode(boot=boot)
                self.assertEqual(result["status"], "invalid")
                self.assertFalse(result["verified_fault"])
                self.assertTrue(result["errors"])

    def test_far_only_for_supported_aborts_with_fnv_clear(self):
        for ec, fsc, fnv, expected in (
            (0, 0, 0, False), (7, 0, 0, False), (0x2F, 0, 0, False),
            (0x20, 4, 0, True), (0x21, 0x10, 0, True),
            (0x24, 4, 0, True), (0x25, 0x10, 0, True),
            (0x20, 0x10, 1, False), (0x25, 0x10, 1, False),
            (0x25, 0x3F, 0, False),
        ):
            with self.subTest(ec=ec, fsc=fsc, fnv=fnv):
                esr = (ec << 26) | (1 << 25) | (fnv << 10) | fsc
                self.raw = self.capture(b"Y35ALV02", PC, esr, 0x12345678)
                far = self.run_decode()["fault"]["far"]
                self.assertEqual(far["valid"], expected)
                self.assertEqual(far["address"], "0x12345678" if expected else None)

    def test_absent_duplicate_overlapping_or_short_manifest_record_is_invalid(self):
        original = copy.deepcopy(self.manifest)
        for case in ("absent", "duplicate", "overlap", "size", "offset"):
            with self.subTest(case=case):
                self.manifest = copy.deepcopy(original)
                if case == "absent":
                    self.manifest["records"].pop()
                elif case == "duplicate":
                    self.manifest["records"].append(copy.deepcopy(self.manifest["records"][1]))
                elif case == "overlap":
                    self.manifest["records"][1]["report_offset"] = 0x100
                elif case == "size":
                    self.manifest["records"][1]["size"] = 24
                else:
                    self.manifest["records"][1]["offset"] = 0xDEAD
                self.assertEqual(self.run_decode()["status"], "invalid")

    def test_malformed_macho_is_invalid_after_hash_binding(self):
        self.kernel.write_bytes(b"not a Mach-O")
        self.manifest["kernel_sha256"] = hashlib.sha256(self.kernel.read_bytes()).hexdigest()
        self.baseline = self.capture()
        self.raw = self.capture(b"Y35ALV02", PC, 0x1FE00000, 0)
        self.assertEqual(self.run_decode()["status"], "invalid")

    def test_nearest_symbol_never_crosses_text_section(self):
        self.raw = self.capture(b"Y35ALV02", BASE + 0x200, 0x1FE00000, 0)
        result = self.run_decode()
        self.assertEqual(result["instruction"]["status"], "unmapped")
        self.assertIsNone(result["instruction"]["nearest_symbol"])

    def test_cli_missing_fault_and_missing_baseline_return_nonzero_json(self):
        self.raw = self.capture()
        self.run_decode()
        args = [sys.executable, "-B", str(ROOT / "scripts/y35a/decode_terminal_fault.py"),
                "--kernel", str(self.kernel), "--manifest", str(self.manifest_path),
                "--probe", str(self.probe), "--raw", str(self.raw_path)]
        result = subprocess.run(args, capture_output=True, text=True, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout)["status"], "missing")


class SealedEvidenceTest(unittest.TestCase):
    def test_real_r69_r70_r71_r72(self):
        expected = [
            ("phase-r69-low-vector-v1-20261111", "fresh", 0, 0xD538F40C),
            ("phase-r70-a53-no-apple-hid-20261111", "missing", None, None),
            ("phase-r71-c-vector-v2-20261111", "fresh", 7, 0x4F00E400),
            (os.environ.get("Y35A_TERMINAL_R72", "phase-r72-a53-fp-enable-20261111"),
             "missing", None, None),
        ]
        for name, status, ec, word in expected:
            with self.subTest(phase=name):
                p = EVIDENCE / name
                if not (p / "final.raw").exists():
                    self.skipTest("Sealed local evidence is unavailable: " + str(p))
                result = decode_terminal_fault(
                    kernel=p / "kernel/kernel.macho",
                    manifest=p / "readback-probe/readback.json",
                    probe=p / "readback-probe/readback-probe-not-xnu.img",
                    raw=p / "final.raw", baseline=p / "baseline.raw", disassemble=False)
                self.assertEqual(result["status"], status, result)
                if status == "fresh":
                    self.assertEqual(result["fault"]["esr"]["ec"], ec)
                    self.assertEqual(result["instruction"]["instruction_word"], hex(word))
                    self.assertTrue(result["verified_fault"])
                else:
                    self.assertFalse(result["verified_fault"])
                if ec == 7:
                    self.assertEqual(result["instruction"]["nearest_symbol"], "_cpu_data_init")
                    self.assertEqual(result["instruction"]["symbol_offset"], "0x30")

    def test_r72_later_checkpoints_do_not_become_a_terminal_fault(self):
        p = EVIDENCE / os.environ.get("Y35A_TERMINAL_R72", "phase-r72-a53-fp-enable-20261111")
        if not (p / "final.raw").exists():
            self.skipTest("R72 sealed evidence is unavailable")
        raw, baseline = (p / "final.raw").read_bytes(), (p / "baseline.raw").read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),
                         "862e5cd171bff210663e41ee92d6b0be27468e6a165cffd10602b911e77f0da9")
        manifest = json.loads((p / "readback-probe/readback.json").read_text())
        record = next(r for r in manifest["records"] if r["name"] == "early-fault-record")
        offset = 0x10000 + record["report_offset"]
        self.assertEqual(raw[offset:offset + 32], bytes(32))
        markers = {6: 0x5045494E4954454E, 7: 0x5045494E49545254,
                   8: 0x41524D564D494E49, 9: 0x50414E4943494E49, 10: 0x434F4E534F4C45}
        for slot, value in markers.items():
            self.assertEqual(struct.unpack_from("<Q", raw, offset + 8 * slot)[0], value)
            self.assertNotEqual(struct.unpack_from("<Q", baseline, offset + 8 * slot)[0], value)


if __name__ == "__main__":
    unittest.main()
