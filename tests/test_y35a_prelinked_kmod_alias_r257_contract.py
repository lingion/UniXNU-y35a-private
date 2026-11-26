from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = ROOT / "patches/xnu/native-y35a-prelinked-kmod-alias-r257.patch"


class Y35APrelinkedKmodAliasR257Contract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.patch = PATCH.read_text()

    def test_patch_is_y35a_oskext_mapping_only(self):
        files = re.findall(r"^diff --git a/(.*?) b/", self.patch, re.MULTILINE)
        self.assertEqual(files, ["libkern/c++/OSKext.cpp"])

    def test_zero_kernel_slide_moves_kmod_callbacks_with_mapped_header(self):
        self.assertIn("vm_kernel_slide == 0", self.patch)
        self.assertIn("slidKmodAddress - unslidKmodAddress", self.patch)
        self.assertIn("kmod_info->start", self.patch)
        self.assertIn("kmod_info->stop", self.patch)
        # R256 observed a randomized kext-map alias while the callback remained
        # at its static VA. Applying the same alias delta restores segment membership.
        unslid_address = 0xFFFFFFF007CA8C40
        mapped_address = 0xFFFFFFF0226A8C40
        unslid_start = 0xFFFFFFF008196E90
        text_exec_start = 0xFFFFFFF022B5E000
        text_exec_size = 0x39060
        mapped_start = unslid_start + (mapped_address - unslid_address)
        self.assertEqual(mapped_start, 0xFFFFFFF022B96E90)
        self.assertLessEqual(text_exec_start, mapped_start)
        self.assertLess(mapped_start, text_exec_start + text_exec_size)


if __name__ == "__main__":
    unittest.main()
