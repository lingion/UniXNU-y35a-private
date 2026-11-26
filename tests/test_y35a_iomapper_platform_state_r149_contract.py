import re
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATCH = ROOT / "patches/xnu/native-y35a-iomapper-platform-state-r149.patch"
MARKERS = {'R149PEEN': 42, 'R149PESU': 42, 'R149PYES': 42, 'R149PNO0': 42, 'R149MST0': 47, 'R149MSF0': 47, 'R149MSUP': 47, 'R149MHFL': 47, 'R149MHOK': 47, 'R149MPRE': 47, 'R149MPUB': 47, 'R149UNK0': 44, 'R149REQ0': 44, 'R149WHT0': 44, 'R149WRT0': 44, 'R149SLP0': 45, 'R149CPRE': 45, 'R149CKRT': 45, 'R149MAPR': 45, 'R149OKR0': 45, 'R149NOM0': 45, 'R149MRET': 45, 'R149BZOK': 45}


class Y35AIomapperPlatformStateR149Contract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.patch = PATCH.read_text()
        cls.added = "\n".join(
            line[1:] for line in cls.patch.splitlines()
            if line.startswith("+") and not line.startswith("+++")
        )
        cls.iovm = cls.patch[cls.patch.index("R149CPRE"):]

    def test_patch_touches_only_the_three_mapper_boundaries(self):
        files = re.findall(r"^diff --git a/(.*?) b/", self.patch, re.MULTILINE)
        self.assertEqual(files, [
            "iokit/Kernel/IOMapper.cpp",
            "iokit/Kernel/IOPlatformExpert.cpp",
            "bsd/kern/uipc_mbuf.c",
        ])

    def test_marker_names_slots_and_values_are_exact(self):
        found = re.findall(
            r"native_phase_marker_external\((\d+),\s*(0x[0-9a-fA-F]+)ULL\);\s*/\* (R149\w+) \*/",
            self.added,
        )
        names = [name for _, _, name in found]
        decision_markers = {"R149PYES", "R149PNO0"}
        self.assertEqual(set(names), set(MARKERS) - decision_markers)
        expected_counts = Counter({name: 1 for name in MARKERS
                                   if name not in decision_markers})
        expected_counts["R149UNK0"] = 2
        self.assertEqual(Counter(names), expected_counts)
        for slot, value, name in found:
            self.assertEqual(int(slot), MARKERS[name], name)
            self.assertEqual(int(value, 16), int.from_bytes(name.encode("ascii"), "little"), name)
            self.assertEqual(len(name), 8, name)
        for name in decision_markers:
            self.assertEqual(len(name), 8)
            self.assertIn(f"/* {name} */", self.patch)
            self.assertIn(f"0x{int.from_bytes(name.encode('ascii'), 'little'):016X}ULL", self.patch)
        self.assertIn("native_phase_marker_external(42, systemMapperRequired", self.patch)

    def test_unknown_fallback_is_local_and_preserves_other_wait_states(self):
        state_load = self.iovm.index("mapper_state = (uintptr_t) IOMapper::gSystem;")
        unknown_branch = self.iovm.index("if (mapper_state == 1)")
        fallback = self.iovm.index("ret = kIOReturnUnsupported;", unknown_branch)
        wait_call = self.iovm.index("IOMapper::checkForSystemMapper();")
        self.assertLess(state_load, unknown_branch)
        self.assertLess(unknown_branch, fallback)
        self.assertLess(fallback, wait_call)
        self.assertIn("if (IOMapper::gSystem)", self.iovm)
        self.assertNotIn("IOMapper::gSystem =", self.added)
        self.assertNotIn("IOMapper::setMapperRequired(false)", self.patch)
        self.assertIn("R149UNK0", self.iovm)
        self.assertIn("R149NOM0", self.iovm)

    def test_fpx_checkpoint_and_original_mapper_publication_are_preserved(self):
        self.assertNotRegex(self.patch, r"native_phase_marker_external\(41,")
        self.assertIn("IOMapper::gSystem = this;", self.patch)
        self.assertIn("sMapperLock.wakeup(&IOMapper::gSystem);", self.patch)
        self.assertIn("sMapperLock.unlock();", self.patch)
        self.assertIn("R149MPUB", self.patch)
        self.assertIn("R149MRET", self.patch)
        self.assertIn("R149BZOK", self.patch)


if __name__ == "__main__":
    unittest.main()
