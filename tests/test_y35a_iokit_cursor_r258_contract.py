from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = ROOT / "patches/xnu/native-y35a-iokit-cursor-r258.patch"


class Y35AIokitCursorR258Contract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.patch = PATCH.read_text()

    def test_patch_changes_only_the_two_iokit_entry_sources(self):
        paths = re.findall(r"^diff --git a/(.*?) b/", self.patch, re.MULTILINE)
        self.assertEqual(paths, ["pexpert/arm/pe_init.c", "iokit/Kernel/IOStartIOKit.cpp"])

    def test_cursor_brackets_iokit_entry_service_registration_and_return(self):
        for marker in ("R258PENT", "R258SPRE", "R258SENT", "R258NREG", "R258SRET"):
            self.assertIn(marker, self.patch)
        peinit = self.patch.split("diff --git a/pexpert/arm/pe_init.c", 1)[1].split(
            "diff --git a/iokit/Kernel/IOStartIOKit.cpp", 1
        )[0]
        start = self.patch.split("diff --git a/iokit/Kernel/IOStartIOKit.cpp", 1)[1]
        peinit_sequence = [
            peinit.index("R258PENT"),
            peinit.index("R258SPRE"),
            peinit.index("StartIOKit(PE_state.deviceTreeHead"),
            peinit.index("R258SRET"),
        ]
        start_sequence = [
            start.index("R258SENT"),
            start.index("rootNub->registerService();"),
            start.index("R258NREG"),
        ]
        self.assertEqual(peinit_sequence, sorted(peinit_sequence))
        self.assertEqual(start_sequence, sorted(start_sequence))
        self.assertIn("R258SENT", start)
        self.assertIn("StartIOKit(PE_state.deviceTreeHead", peinit)
        self.assertEqual(self.patch.count("native_phase_marker_external(57,"), 2)

    def test_each_cursor_write_is_y35a_guarded(self):
        for marker in ("R258PENT", "R258SPRE", "R258SENT", "R258NREG", "R258SRET"):
            at = self.patch.index(marker)
            guard = self.patch.rfind("#if defined(XNU_Y35A_A53) && XNU_Y35A_A53", 0, at)
            close = self.patch.find("#endif", at)
            self.assertGreaterEqual(guard, 0)
            self.assertGreater(close, at)

    def test_codewords_match_their_documented_little_endian_names(self):
        expected = {
            "R258PENT": 0x544E455038353252,
            "R258SPRE": 0x4552505338353252,
            "R258SENT": 0x544E455338353252,
            "R258NREG": 0x4745524E38353252,
            "R258SRET": 0x5445525338353252,
        }
        for name, value in expected.items():
            self.assertIn(f"0x{value:016x}ULL); /* {name} */", self.patch)

    def test_slots_56_to_59_fit_the_64_byte_extension_window(self):
        args_physical = 0xA27E4000
        early_record_physical = args_physical + 0x800
        slot56_physical = early_record_physical + 56 * 8
        slot59_end = early_record_physical + 60 * 8
        extension_end = early_record_physical + 64 * 8
        self.assertEqual(slot56_physical, 0xA27E49C0)
        self.assertEqual(slot59_end, 0xA27E49E0)
        self.assertLessEqual(slot59_end, extension_end)
        self.assertEqual(extension_end, 0xA27E4A00)

    def test_cursor_does_not_reuse_previous_carrier_owners(self):
        new_slots = {56, 57, 58, 59}
        previous_patch_owners = set()
        for path in (ROOT / "patches/xnu").glob("*.patch"):
            if path == PATCH:
                continue
            previous_patch_owners.update(
                int(slot) for slot in re.findall(
                    r"native_phase_marker_external\(\s*(\d+)\s*,", path.read_text()
                )
            )
        self.assertTrue(new_slots.isdisjoint(previous_patch_owners))


if __name__ == "__main__":
    unittest.main()
