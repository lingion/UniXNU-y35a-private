#!/usr/bin/env python3
"""Contracts for the iOS 12 first-boot kernel builder."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class KernelBuildContractTest(unittest.TestCase):
    def test_4903_builder_applies_early_fault_phase_patch(self):
        src = (ROOT / 'scripts/build-xnu-4903-kernel.py').read_text()
        self.assertIn("patches/xnu/native-early-fault-record.patch", src)
        self.assertIn("native-early-fault-applied", src)
        self.assertIn("patches/xnu/native-entry-witness.patch", src)
        self.assertIn("native-entry-witness-applied", src)
        self.assertIn("patches/xnu/native-phase-markers.patch", src)
        self.assertIn("native-phase-markers-applied", src)
        self.assertIn("patches/xnu/native-phase-console-marker.patch", src)
        self.assertIn("native-phase-console-marker-applied", src)
        self.assertIn("patches/xnu/native-phase-kva-carrier.patch", src)
        self.assertIn("native-phase-kva-carrier-applied", src)
        self.assertIn("patches/xnu/native-handoff-witness.patch", src)
        self.assertIn("native-handoff-witness-applied", src)
        self.assertIn("patches/xnu/native-pre-mmu-witness.patch", src)
        self.assertIn("native-pre-mmu-witness-applied", src)
        self.assertIn("patches/xnu/native-startup-witness.patch", src)
        self.assertIn("native-startup-witness-applied", src)
        self.assertIn("patches/xnu/native-bootargs-witness.patch", src)
        self.assertIn("native-bootargs-witness-applied", src)
        self.assertIn("patches/xnu/native-args-physical-witness.patch", src)
        self.assertIn("native-args-physical-witness-applied", src)
        self.assertIn("patches/xnu/native-stack-link-witness.patch", src)
        self.assertIn("native-stack-link-witness-applied", src)
        self.assertIn("patches/xnu/native-stack-link-physical.patch", src)
        self.assertIn("native-stack-link-physical-applied", src)
        self.assertIn("patches/xnu/native-invalidation-witness.patch", src)
        self.assertIn("native-invalidation-witness-applied", src)
        self.assertIn("patches/xnu/native-invalidation-setup-witness.patch", src)
        self.assertIn("native-invalidation-setup-witness-applied", src)
        self.assertIn("patches/xnu/native-mapping-witness.patch", src)
        self.assertIn("native-mapping-witness-applied", src)
        self.assertIn("patches/xnu/native-invalidation-loop-state.patch", src)
        self.assertIn("native-invalidation-loop-state-applied", src)
        self.assertIn("patches/xnu/native-fault-publish-witness.patch", src)
        self.assertIn("native-fault-publish-witness-applied", src)
        self.assertIn("patches/xnu/native-header-adjust-witness.patch", src)
        self.assertIn("native-header-adjust-witness-applied", src)
        self.assertIn("patches/xnu/native-phase-c-enable.patch", src)
        self.assertIn("native-phase-c-enable-applied", src)
    def test_early_fault_gate_does_not_depend_on_uninitialized_tpidr(self):
        patch = (ROOT / 'patches/xnu/native-early-fault-record.patch').read_text()
        hunk = patch.split('@@ -316', 1)[1].split('--- a/osfmk/arm64/start.s', 1)[0]
        self.assertNotIn('TPIDR_EL1', hunk)
        self.assertIn('native_early_fault_address', hunk)
        self.assertIn('ELR_EL1', hunk)
        self.assertIn('ESR_EL1', hunk)
        self.assertNotIn('Earliest MMU-off entry witness', patch)

    def test_early_fault_carrier_uses_saved_boot_args_after_x0_reuse(self):
        patch = (ROOT / 'patches/xnu/native-early-fault-record.patch').read_text()
        hunk = patch.split('--- a/osfmk/arm64/start.s', 1)[1]
        self.assertIn('add x17, x20, x22', hunk)
        self.assertIn('sub x17, x17, x23', hunk)
        self.assertNotIn('add x16, x16, x22', hunk)
        self.assertNotIn('sub x16, x16, x23', hunk)
        self.assertNotIn('ldr x17, [x0, BA_VIRT_BASE]', hunk)

    def test_earliest_entry_witness_is_a_separate_required_patch(self):
        patch = (ROOT / 'patches/xnu/native-entry-witness.patch').read_text()
        self.assertIn('add x16, x20, #0x820', patch)
        self.assertIn('movk x15, #0x5952, lsl #48', patch)
        self.assertIn('str x15, [x16]', patch)
        src = (ROOT / 'scripts/build-xnu-4903-kernel.py').read_text()
        self.assertIn('required Y35A patch is missing', src)
        self.assertIn('native-entry-witness-applied', src)
        phase = (ROOT / 'patches/xnu/native-phase-c-entry-markers.patch').read_text()
        self.assertIn('native_phase_marker(args, 5, 0x41524d494e495445ULL)', phase)
        self.assertIn('native_phase_marker(args, 6, 0x5045494e4954454eULL)', phase)
        self.assertIn('native_phase_marker(args, 7, 0x5045494e49545254ULL)', phase)
        self.assertNotIn('native_phase_marker(1,', phase)
        self.assertNotIn('native_phase_marker(2,', phase)
        self.assertNotIn('native_phase_marker(3,', phase)
    def test_phase_markers_use_the_published_retained_carrier(self):
        patch = (ROOT / 'patches/xnu/native-phase-markers.patch').read_text()
        self.assertIn('native_early_fault_address == 0', patch)
        self.assertIn('(uintptr_t)native_early_fault_address', patch)
        self.assertNotIn('BootArgs->topOfKernelData + 0x800', patch)
        self.assertIn('if (slot >= 11) return;', patch)
        self.assertIn('native_phase_marker(8, 0x41524d564d494e49ULL)', patch)
        self.assertIn('native_phase_marker(9, 0x50414e4943494e49ULL)', patch)
        console = (ROOT / 'patches/xnu/native-phase-console-marker.patch').read_text()
        self.assertIn('native_phase_marker(args, 10, 0x434f4e534f4c45ULL)', console)

    def test_builder_exports_instrumentation_to_c_and_assembly_rules(self):
        src = (ROOT / 'scripts/build-xnu-4903-kernel.py').read_text()
        self.assertIn("CFLAGS_EXTRA=-DXNU_NATIVE_EARLY_FAULT=1", src)
        self.assertIn("SFLAGS_ARM64+=-DXNU_NATIVE_EARLY_FAULT=1", src)

    def test_native_package_clears_extended_diagnostic_carrier(self):
        src = (ROOT / 'scripts/y35a/package_native.py').read_text()
        self.assertIn('mov x2,#32', src)
        self.assertIn("'diagnostic_carrier_bytes':512", src)

    def test_phase_verifier_accepts_published_carrier_contract(self):
        src = (ROOT / 'scripts/y35a/verify_phase_instrumentation.py').read_text()
        self.assertIn('marker constants and carrier slots', src)
        self.assertIn('ARMINITE', src)
        self.assertIn('PEINITEN', src)
        self.assertIn('PEINITRT', src)
        self.assertIn('MMUON', src)
        self.assertIn('ARMRET', src)
        self.assertIn('COMMON00', src)
        self.assertIn('MAPDONE0', src)
        self.assertIn('TTBRDONE', src)
        self.assertIn('PREMMU00', src)
        self.assertIn('ARGSLOAD', src)
        self.assertIn('STACKS00', src)
        self.assertIn('INVALID0', src)
        self.assertIn('VPMAP000', src)
        self.assertIn('KVAMAP00', src)
        self.assertIn('PREARGS0', src)
        self.assertIn('BAVIRT00', src)
        self.assertIn('BAPHYS00', src)
        self.assertIn('BAMEM000', src)
        self.assertIn('BATOP000', src)
        self.assertIn('BAFLAG00', src)
        self.assertIn('TPIDR000', src)
        self.assertIn('EXCADDR0', src)
        self.assertIn('EXCSPS00', src)
        self.assertIn('EXCSP000', src)
        self.assertIn('INTADDR0', src)
        self.assertIn('INTSPS00', src)
        self.assertIn('INTSP000', src)
        self.assertIn('LINKADDR', src)
        self.assertIn('0x10000', src)

    def test_handoff_patch_uses_little_endian_marker_halves(self):
        patch = (ROOT / 'patches/xnu/native-handoff-witness.patch').read_text()
        self.assertIn('movk\t\tx15, #0x4f55, lsl #16', patch)
        self.assertIn('movk\t\tx15, #0x304e, lsl #32', patch)
        self.assertIn('movk\t\tx15, #0x524d, lsl #16', patch)

    def test_instrumentation_patch_order_respects_context_dependencies(self):
        src = (ROOT / 'scripts/build-xnu-4903-kernel.py').read_text()
        names = (
            'native-phase-markers.patch',
            'native-phase-kva-carrier.patch',
            'native-phase-c-entry-markers.patch',
            'native-phase-console-marker.patch',
            'native-phase-c-enable.patch',
            'native-handoff-witness.patch',
            'native-pre-mmu-witness.patch',
            'native-startup-witness.patch',
            'native-bootargs-witness.patch',
            'native-args-physical-witness.patch',
            'native-stack-link-witness.patch',
            'native-stack-link-physical.patch',
            'native-fault-publish-witness.patch',
            'native-invalidation-witness.patch',
            'native-invalidation-setup-witness.patch',
            'native-invalidation-loop-state.patch',
            'native-mapping-witness.patch',
            'native-header-adjust-witness.patch',
        )
        positions = [src.index(name) for name in names]
        self.assertEqual(positions, sorted(positions))

    def test_stack_witnesses_use_physical_carrier_stores(self):
        source = (
            (ROOT / 'patches/xnu/native-stack-link-witness.patch').read_text()
            + (ROOT / 'patches/xnu/native-stack-link-physical.patch').read_text()
        )
        self.assertIn('str\t\tx15, [x20, #0x890]', source)

if __name__ == '__main__':
    unittest.main(verbosity=2)


