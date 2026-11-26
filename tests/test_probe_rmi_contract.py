from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ProbeRmiBuildContractTest(unittest.TestCase):
    def test_probe_build_isolated_from_xnu_clang_overrides(self):
        source = (ROOT / "scripts/y35a/probe_rmi.py").read_text()
        self.assertIn("build_env = dict(os.environ)", source)
        self.assertIn("build_env.pop('CCC_OVERRIDE_OPTIONS', None)", source)
        self.assertIn("env=build_env", source)

    def test_raw_dump_targets_source_pinned_tlmm_and_qup5_windows(self):
        source = (ROOT / "scripts/y35a/rmi_probe.cpp").read_text()
        self.assertIn("pins[p] * 0x1000", source)
        self.assertIn("0x01000000 + 13 * 0x1000 + 0x4", source)
        self.assertIn("0x01000000 + 13 * 0x1000 + 0xc", source)
        self.assertIn("0x06000", source)
        self.assertIn("0x06020", source)
        self.assertIn("0x45004", source)
        self.assertNotIn("0x01000000 + i * 4", source)
        self.assertNotIn("0x01800000 + i * 4", source)

    def test_manifest_mirrors_corrected_report_layout(self):
        source = (ROOT / "scripts/y35a/probe_rmi.py").read_text()
        self.assertIn("REPORT_BYTES = 0x124", source)
        self.assertIn("'tlmm_target': 0xb0", source)
        self.assertIn("'gcc_q5': 0xf0", source)


if __name__ == "__main__":
    unittest.main()
