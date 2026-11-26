#!/usr/bin/env python3
"""Guard the shim's pointer to its embedded Mach-O payload.

The flattened boot image can be linked from an ELF or extracted from a Mach-O
text section. PC-relative addressing keeps the source pointer correct when
the section's linked VMA differs from the Android image load address.
"""
import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "y35a"))
spec = importlib.util.spec_from_file_location(
    "native_pkg_kernel_data_test", ROOT / "scripts/y35a/package_native.py")
pkg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pkg)


class EmbeddedKernelPointerContractTest(unittest.TestCase):
    def test_embedded_kernel_source_is_pc_relative(self):
        source = pkg.generate_entry_source(
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

        self.assertIn("adr x19,_start", source)
        self.assertIn("ldr x9,=kernel_data-_start", source)
        self.assertIn("add x19,x19,x9", source)
        self.assertNotIn("adrp x19,kernel_data", source)
        self.assertNotIn("ldr x19,=kernel_data", source)


if __name__ == "__main__":
    unittest.main()
