from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
PATCH = ROOT / "patches/xnu/native-y35a-entry-retained-carrier-r261.patch"


class Y35AEntryRetainedCarrierR261Contract(unittest.TestCase):
    def test_entry_witness_uses_preserved_report_gap_before_first_bootargs_load(self):
        source = PATCH.read_text()
        self.assertIn("R261ENT0", source)
        self.assertIn("mov\t\tx14, #0x00a0", source)
        self.assertIn("movk\tx14, #0x859f, lsl #16", source)
        self.assertIn("dc\t\tcivac, x14", source)
        self.assertIn("movk\tx15, #0x3136, lsl #16", source)
        self.assertIn("movk\tx15, #0x4e45, lsl #32", source)
        self.assertGreater(source.index("R261ENT0"), source.index("mov\t\tx21, #0"))


if __name__ == "__main__":
    unittest.main()
