"""KASLR-site geometry for the iOS 12 legacy graft emitter."""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "kits" / "XnuPrelink"))

from legacy_graft_emit import kaslr_offset_values, kaslr_offsets_for_plan


class LegacyGraftKASLROffsetTests(unittest.TestCase):
    def test_candidate_sites_are_relative_to_rebased_prelink_text(self):
        original_prelink_text = 0xfffffff005ca0000
        slide = 0x02000000
        prelink_text = original_prelink_text + slide
        binding_site = 0xfffffff008e217d8
        kmod_start_site = 0xfffffff0096f526c
        kmod_stop_site = 0xfffffff0096f5274

        offsets = kaslr_offsets_for_plan(
            bindings=({"site": binding_site},),
            prelink_text_base=prelink_text,
            kmod_pointer_sites=(kmod_start_site, kmod_stop_site),
        )

        self.assertEqual(
            offsets,
            (0x11817d8, 0x1a5526c, 0x1a55274),
        )
        self.assertNotIn(0x31817d8, offsets)

    def test_duplicate_sites_are_emitted_once(self):
        base = 0xfffffff007ca0000
        site = base + 0x1234
        self.assertEqual(
            kaslr_offset_values((site, site), (site,), base),
            (0x1234,),
        )

    def test_rejects_sites_below_prelink_text_base(self):
        with self.assertRaises(ValueError):
            kaslr_offset_values((0xfffffff007c9ffff,), (), 0xfffffff007ca0000)


if __name__ == "__main__":
    unittest.main()
