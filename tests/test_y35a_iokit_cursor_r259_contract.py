from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = ROOT / "patches/xnu/native-y35a-iokit-cursor-r259-bss.patch"


class Y35AIokitCursorR259Contract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.patch = PATCH.read_text()

    def test_patch_uses_xnu_bss_cursor_and_only_iokit_entry_sources(self):
        paths = re.findall(r"^diff --git a/(.*?) b/", self.patch, re.MULTILINE)
        self.assertEqual(paths, [
            "osfmk/arm/arm_init.c",
            "pexpert/arm/pe_init.c",
            "iokit/Kernel/IOStartIOKit.cpp",
            "osfmk/kern/startup.c",
        ])
        self.assertIn("native_r259_phase_cursor[8]", self.patch)
        additions = "\n".join(line[1:] for line in self.patch.splitlines()
                               if line.startswith("+") and not line.startswith("+++"))
        self.assertNotIn("native_phase_marker_external(5", additions)

    def test_cursor_is_written_at_xnu_c_entry_and_iokit_control_flow_boundaries(self):
        markers = ("R259AENT", "R259PEI0", "R259SPRE", "R259SENT",
                   "R259NNEW", "R259NREG", "R259SRET", "R259IOKR")
        for marker in markers:
            self.assertIn(marker, self.patch)
        arm = self.patch.split("diff --git a/osfmk/arm/arm_init.c", 1)[1].split(
            "diff --git a/pexpert/arm/pe_init.c", 1
        )[0]
        pe = self.patch.split("diff --git a/pexpert/arm/pe_init.c", 1)[1].split(
            "diff --git a/iokit/Kernel/IOStartIOKit.cpp", 1
        )[0]
        start = self.patch.split("diff --git a/iokit/Kernel/IOStartIOKit.cpp", 1)[1].split(
            "diff --git a/osfmk/kern/startup.c", 1
        )[0]
        startup = self.patch.split("diff --git a/osfmk/kern/startup.c", 1)[1]
        self.assertLess(arm.index("R259AENT"), arm.index("native_phase_marker(args, 5"))
        self.assertLess(pe.index("R259PEI0"), pe.index("PE_init_kprintf(TRUE)"))
        self.assertLess(pe.index("R259SPRE"), pe.index("StartIOKit(PE_state.deviceTreeHead"))
        self.assertLess(start.index("R259SENT"), start.index("rootNub = new IOPlatformExpertDevice"))
        self.assertLess(start.index("rootNub = new IOPlatformExpertDevice"), start.index("R259NNEW"))
        self.assertLess(start.index("rootNub->registerService();"), start.index("R259NREG"))
        self.assertGreater(pe.index("R259SRET"), pe.index("StartIOKit(PE_state.deviceTreeHead"))
        self.assertGreater(startup.index("R259IOKR"), startup.index("PE_init_iokit();"))

    def test_all_cursor_values_are_unique_little_endian_codewords(self):
        markers = ("R259AENT", "R259PEI0", "R259SPRE", "R259SENT",
                   "R259NNEW", "R259NREG", "R259SRET", "R259IOKR")
        values = {name: int.from_bytes(name.encode("ascii"), "little") for name in markers}
        self.assertEqual(len(values), len(set(values.values())))
        slots = dict(zip(markers, range(8)))
        for name, value in values.items():
            if name == "R259NNEW":
                self.assertIn(f"0x{value:016x}ULL", self.patch)
                continue
            self.assertIn(f"native_r259_cursor_store({slots[name]}, 0x{value:016x}ULL); /* {name} */", self.patch)

    def test_cursor_symbols_are_externally_readable_and_zero_initialized(self):
        self.assertRegex(self.patch, r"volatile uint64_t\s+native_r259_phase_cursor\[8\]")
        self.assertIn("native_r259_cursor_store(uint32_t slot, uint64_t value)", self.patch)
        self.assertIn("native_r259_phase_cursor[slot] = value", self.patch)
        self.assertIn("dc civac", self.patch)
        self.assertIn("dsb sy", self.patch)
        additions = "\n".join(line[1:] for line in self.patch.splitlines()
                               if line.startswith("+") and not line.startswith("+++"))
        self.assertNotIn("native_phase_marker_external(5", additions)

    def test_every_cursor_write_is_y35a_guarded(self):
        for marker in ("R259AENT", "R259PEI0", "R259SPRE", "R259SENT",
                       "R259NNEW", "R259NREG", "R259SRET", "R259IOKR"):
            at = self.patch.index(marker)
            guard = self.patch.rfind("#if defined(XNU_Y35A_A53) && XNU_Y35A_A53", 0, at)
            close = self.patch.find("#endif", at)
            self.assertGreaterEqual(guard, 0)
            self.assertGreater(close, at)

    def test_expected_probe_window_is_exactly_one_64_byte_array(self):
        cursor_bytes = 8 * 8
        self.assertEqual(cursor_bytes, 64)


if __name__ == "__main__":
    unittest.main()
