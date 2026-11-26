from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "y35a"))
SPEC = importlib.util.spec_from_file_location(
    "native_pkg_r260", ROOT / "scripts/y35a/package_native.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class PackageNativeEntryCopyWitnessR260Contract(unittest.TestCase):
    def test_shim_publishes_copied_entry_bytes_after_segment_copy(self):
        source = MODULE.generate_entry_source(
            segments=[(0, 0xA0004000, 0x1000)],
            kernel_data_name="kernel-packed.macho",
            physical_base=0xA0004000,
            memory_end=0x1000,
            args_pa=0xA0008000,
            args_len=384,
            tree_pa=0xA0009000,
            tree_len=64,
            tree_name="board.adt",
            rootfs=None,
            trustcache=None,
            entry=0xA0004000,
            kernel_sha256_8=bytes(8),
        )
        copy_marker = hex(int.from_bytes(b"R260CPY0", "little"))
        self.assertIn(copy_marker, source)
        self.assertIn("0xa0008a00", source)
        self.assertIn("ldr x12,[x11]", source)
        self.assertIn("ldr x13,[x11,#8]", source)
        self.assertIn("str x12,[x10,#16]", source)
        self.assertIn("str x13,[x10,#24]", source)
        self.assertIn("0x859f0080", source)
        self.assertGreater(source.rfind(copy_marker), source.index("0x859f0080"))
        self.assertLess(source.index(copy_marker), source.index("br x1"))


if __name__ == "__main__":
    unittest.main()
