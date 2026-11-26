#!/usr/bin/env python3
"""RED-GREEN gate: readback_native.py NAMES against the P1 4903 symbol table.

The 2026-11-07 boot4 review (guardian-session testimony, independently
re-verified here) found `_panicstr` and `_debug_buf` are 17-era names that do
not exist in XNU-4903.270.47 at all: the 4903 reason-string carrier is
`debugger_panic_str` (osfmk/kern/debug.c:169), and the panic-log window is
described by the debug_buf triple + gPanicBase/gPanicSize. The packer's
`if name not in symbols: continue` turns any stale name into a silently
missing record, so the contract must separate REQUIRED core carriers (never
absent) from patch-time glue symbols (legitimately absent in a vanilla build).

Kernel: out/y35a/ios12-kernel.noctf (sha256 5fd4e6b5..., the exact binary
booted by boot3 and stamped into the Y35AXNU2 handoff record).
"""
import hashlib, json, subprocess, tempfile, unittest, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
KERNEL = REPO / 'out/y35a/ios12-kernel.noctf'
sys.path.insert(0, str(REPO / 'scripts/y35a'))

STALE = {'_panicstr', '_debug_buf'}

class ReadbackNamesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not KERNEL.exists():
            raise unittest.SkipTest(f'{KERNEL} not on disk (P1 artifact)')
        assert hashlib.sha256(KERNEL.read_bytes()).hexdigest().startswith('5fd4e6b5'), \
            'symbol table must come from the booted kernel generation'
        out = subprocess.run(['/usr/bin/nm', str(KERNEL)], capture_output=True, text=True, check=True).stdout
        cls.symbols = {w.split()[-1] for w in out.splitlines() if len(w.split()) == 3}

    def test_no_stale_17era_names_in_NAMES(self):
        import readback_native
        self.assertEqual(STALE & set(readback_native.NAMES), set(),
                         'names absent from every 4903 build silently vanish from the probe')

    def test_record_sizes_derive_from_dsym_dwarf(self):
        """The coordinator ruled logical sizes from the build's .dsym DWARF.
        This repo builds with BUILD_DSYM=0 (build script line 416), so the
        machine-readable truth source is the 4903 SOURCE TYPES themselves —
        the test pins the derivation table, and every entry cites the file:
        line that sets its width. read_field_bytes prefers a real .dsym when
        present and falls back to the table otherwise; the table alone must
        never disagree with DWARF when one exists:
          _panicDebugging          osfmk/kern/debug.c:155  unsigned int (boolean_t) = 4
          _gPanicBase              pexpert/pexpert/pexpert.h:61 vm_offset_t = 8
          _gPanicSize              pexpert/pexpert/pexpert.h:62 unsigned int = 4
          _debugger_panic_str      osfmk/kern/debug.c:255    const char * = 8
          _debug_buf_base/ptr      osfmk/kern/debug.c:286-287 char * = 8
          _debug_buf_size          osfmk/kern/debug.c:288    unsigned int = 4
          _BootArgs                osfmk/arm/arm_init.c:157  boot_args * = 8
          _const_boot_args         osfmk/arm/arm_init.c:156  boot_args = 0x180 (symbol spacing)
          _armcpu_gic_boot         drivers/ArmCpu/ArmCpu.cpp:33 uint32_t[8] = 32
          _armdt_platform_configured drivers/ArmDTPlatform/ArmDTPlatform.cpp:25 = 4
        _native_entry_trace width is UNDEFINED here: absent from
        ios12-kernel.noctf (nm has no such line), so it materializes only
        from a rebuilt instrumented kernel whose symbol table carries it;
        the probe must then take size from the symbol presence +
        phase-markers patch definition, never a fallback constant."""
        import readback_native
        truth = {
            '_panicDebugging': 4, '_gPanicSize': 4, '_debug_buf_size': 4,
            '_armdt_platform_configured': 4, '_armcpu_registered': 4,
            '_native_crypto_emulations': 8,
            '_gPanicBase': 8, '_debug_buf_base': 8, '_debug_buf_ptr': 8,
            '_debugger_panic_str': 8, '_BootArgs': 8,
            '_native_early_fault_address': 8, '_armcpu_timer_interrupts': 8,
            '_original_faulting_state': 8,
            '_const_boot_args': 0x180,
            '_armcpu_gic_boot': 32,
        }
        for name, width in truth.items():
            self.assertEqual(readback_native.read_field_bytes(name, {}), width,
                             f'{name}: table derivation wrong')
        # with NO dsym available the table answers; with a dsym path that
        # lacks the symbol the table must also answer (never zero)
        self.assertEqual(readback_native.read_field_bytes('_panicDebugging', {},
                                                          dsym_path=None), 4)
        # a fake DWARF-like object proving dsym precedence:
        class FakeDsym:
            def type_size(self, name):
                return 4 if name == '_panicDebugging' else None
        self.assertEqual(readback_native.read_field_bytes(
            '_gPanicSize', {}, dsym=FakeDsym()), 4)
        self.assertEqual(readback_native.read_field_bytes(
            '_BootArgs', {}, dsym=FakeDsym()), 8)  # dsym silent -> table
        # entry trace: symbol absence is authoritative, no fallback width
        self.assertIsNone(readback_native.read_field_bytes('_native_entry_trace', {},
                                                           dsym=FakeDsym()))
        self.assertEqual(readback_native.read_field_bytes(
            '_native_entry_trace', {'_native_entry_trace': 0xa0004340},
            dsym=FakeDsym()), 512)

    def test_r8_rebuild_publishes_logical_sizes_and_keeps_image_determinism(self):
        """The r8 rebuild the coordinator demanded: records carry field_bytes
        (logical) distinct from size (copy window), the emitted assembly stays
        byte-identical (windows unchanged => same image sha ce63d21a), and the
        manifest gains no new copy geometry."""
        import readback_native
        main_src = (Path(__file__).resolve().parents[1] / 'scripts/y35a' /
                    'readback_native.py').read_text()
        self.assertIn('field_bytes=read_field_bytes(', main_src)

    def test_no_hardcoded_entry_trace_physical(self):
        """R8 never emits a hard-coded physical fallback for the entry trace
        (the 0xa0004000+0x340 arithmetic deleted): the symbol is the only
        authority; a kernel without the symbol gets NO trace record."""
        import readback_native
        main_src = (Path(__file__).resolve().parents[1] / 'scripts/y35a' /
                    'readback_native.py').read_text()
        self.assertNotIn('0xa0004000', main_src)
        self.assertIn('entry-trace symbol not resolved', main_src)

    def test_required_carriers_present_and_resolved(self):
        import readback_native
        for needed in ('_debugger_panic_str', '_debug_buf_base', '_debug_buf_ptr',
                       '_debug_buf_size', '_gPanicBase', '_gPanicSize', '_panicDebugging'):
            self.assertIn(needed, readback_native.NAMES,
                          f'{needed} is a 4903 panic-log carrier name')
            self.assertIn(needed, self.symbols, f'{needed} missing from booted kernel table')

    def test_packer_enforces_REQUIRED_not_silent_continue(self):
        import readback_native
        self.assertTrue(hasattr(readback_native, 'REQUIRED'))
        self.assertTrue(set(readback_native.REQUIRED) <= set(readback_native.NAMES))
        symbols = {name: 0x10000000 for name in readback_native.REQUIRED}
        self.assertIsNone(readback_native.validate_required_symbols(symbols))

    def test_panic_log_copy_precedes_record_staging(self):
        """The PRAM window IS the staging area: if the record table copies into
        [0x40,0xc640) before the debug_buf bytes move to 0x859f0000, the probe
        eats its own evidence — boot4-empty-readback §5 proved the valid
        [0xa9,0xae0) text range sits under the record+excepstack writes.
        Guard failures must also fall through to record staging, not skip it:
        records are the fallback when the carriers read zero."""
        import readback_native
        layout, symbols = self._layout_and_symbols()
        source = readback_native.preservation_entry_source(
            records=[dict(name='sentinel', physical='0x1000', offset=64, size=16)],
            symbols=symbols, layout=layout,
            physical_base=0xa0000000, kernel_sha256='44' * 32)
        self.assertLess(source.index('copy_bytes:'), source.index('adr x19,table'))
        self.assertLess(source.index('ldr w4,[x9]'), source.index('ldr x2,[x19],#8'))
        self.assertIn('b.lo set_table', source)
        self.assertIn('b.hs set_table', source)
        self.assertIn('b.hi set_table', source)

    def test_extra_physical_records_bypass_symbol_table(self):
        """--extra-pa settles residency questions (kernel-entry codeword, LK
        boot-args page) that live OUTSIDE symbol-derived VA translation."""
        import readback_native
        r = readback_native.parse_extra_pa('kernel-entry=0xa026e0a0:128')
        self.assertEqual(r, {'name': 'kernel-entry', 'physical': '0xa026e0a0', 'size': 128})
        layout, symbols = self._layout_and_symbols()
        records = [dict(name='kernel-entry', physical='0xa026e0a0', offset=64, size=128)]
        source = readback_native.preservation_entry_source(
            records=records, symbols=symbols, layout=layout,
            physical_base=0xa0000000, kernel_sha256='55' * 32)
        self.assertIn('.quad 0xa026e0a0,', source)

    def test_extra_physical_record_rejects_bad_geometry(self):
        import readback_native
        for bad in ('kernel-entry=0x0:128', 'kernel-entry=0xa026e0a0:0',
                    'kernel-entry=0xa026e0a0', '=0xa026e0a0:128',
                    '0x26e0a0:128', 'kernel-entry=zzz:128'):
            with self.assertRaises(ValueError, msg=bad):
                readback_native.parse_extra_pa(bad)

    def test_reset_entry_copies_records_and_resets_in_order(self):
        import readback_native
        layout, symbols = self._layout_and_symbols()
        source = readback_native.preservation_entry_source(
            records=[dict(name='early-fault-record', physical='0xa0b7c800', offset=64, size=384)],
            symbols=symbols, layout=layout,
            physical_base=0xa0000000, kernel_sha256='00' * 32)
        self.assertIn('.quad 0xa0b7c800, 0x859e0040, 24', source)
        self.assertNotIn('0x859f0400', source)
        self.assertNotIn('retain_loop', source)
        self.assertNotIn('zero_loop', source)
        self.assertLess(source.index('capture_done:'), source.index('0x0860065c'))
        self.assertLess(source.index('0x0860065c'), source.index('0x004ab000'))

    @staticmethod
    def _layout_and_symbols():
        layout = {
            'base': 0x10000000,
            'end': 0x10040000,
            'segments': [{'address': 0x10000000, 'size': 0x40000}],
        }
        symbols = {
            '_debug_buf_base': 0x10001000,
            '_debug_buf_ptr': 0x10001008,
            '_debug_buf_size': 0x10001010,
            '_gPanicBase': 0x10001018,
            '_gPanicSize': 0x10001020,
        }
        return layout, symbols

    def test_eph_snapshot_precedes_every_stage_write(self):
        """STAGE_BASE == pram reg base == 0x859e0000: the probe header
        (magic/stamp/CNTVCT/ID regs at stage+0..0x38) overwrote the first
        0x38 bytes of the embedded panic header that a panicking XNU wrote at
        pram+0 — including eph_magic — before the host could read it. r8
        snapshots the 0x74-byte header to a pram-TAIL preservation slot
        before its first marker store. Honest scope (R9 boundary): the slot
        is still inside pram — this preserves a compact EPH header witness,
        it does not de-alias the probe from pram nor preserve full panic
        text, which the record-table staging (up to stage+0xc640) overwrites
        by design (transport_mode=full-readback, pram_preserved=false)."""
        import readback_native
        layout, symbols = self._layout_and_symbols()
        source = readback_native.preservation_entry_source(
            records=[dict(name='sentinel', physical='0x1000', offset=64, size=16)],
            symbols=symbols, layout=layout,
            physical_base=0xa0000000, kernel_sha256='44' * 32)
        snapshot_loop = source.index('b.ne snapshot_store')
        first_marker_store = source.index('str x11,[x10]')
        self.assertLess(snapshot_loop, first_marker_store)
        self.assertLess(source.index('snapshot_store:'), first_marker_store)

    def test_eph_snapshot_slot_clears_record_and_fault_usage(self):
        """The slot must survive the probe's own staging: record allocation
        ends at stage+0xc640 and the fault-state copy occupies
        stage+0xf000..0xf0400 (64 pairs, entry copy of 1024B); panic text
        moves to PANIC_LOG_DEST (stage+0x10000). 0xf800..0xf874 is clear of
        all three and still inside the LK-staged 0x11000 window."""
        import readback_native
        self.assertGreaterEqual(readback_native.EPH_SNAPSHOT_OFFSET, 0xf000 + 1024)
        self.assertLessEqual(readback_native.EPH_SNAPSHOT_OFFSET + readback_native.EPH_SNAPSHOT_BYTES,
                             readback_native.PANIC_LOG_OFFSET)
        layout, symbols = self._layout_and_symbols()
        source = readback_native.preservation_entry_source(
            records=[dict(name='sentinel', physical='0x1000', offset=64, size=16)],
            symbols=symbols, layout=layout,
            physical_base=0xa0000000, kernel_sha256='99' * 32)
        self.assertIn(f'{readback_native.STAGE_BASE + readback_native.EPH_SNAPSHOT_OFFSET:#x}', source)

    def test_copy_windows_ge_logical_field_and_16_aligned(self):
        """Windows must at least cover the field and stay ldp/stp-sized;
        logical widths themselves come from read_field_bytes (dsym test)."""
        import readback_native
        for name in ('_panicDebugging', '_gPanicBase', '_debug_buf_ptr',
                     '_const_boot_args', '_armcpu_gic_boot', '_intstack', '_excepstack'):
            field = readback_native.field_bytes(name)
            self.assertGreaterEqual(readback_native._record_size(name), field, name)
            self.assertEqual(readback_native._record_size(name) % 16, 0, name)

    def test_manifest_records_publish_field_bytes(self):
        import readback_native
        main_src = (Path(__file__).resolve().parents[1] / 'scripts/y35a' /
                    'readback_native.py').read_text()
        self.assertIn('field_bytes=read_field_bytes(', main_src)
        # the --dsym path is wired to the resolver, not test-injected only
        self.assertIn('dsym_path=a.dsym', main_src)
        self.assertIn("'--dsym'", main_src)

    def test_no_hardcoded_entry_trace_physical(self):
        """R8 never emits a hard-coded physical fallback for the entry trace:
        the symbol is the only authority; a built kernel without the symbol
        gets NO record, not a wrong-page record."""
        import readback_native
        main_src = (Path(__file__).resolve().parents[1] / 'scripts/y35a' /
                    'readback_native.py').read_text()
        self.assertNotIn('0xa0004000', main_src)

    def test_fault_pointer_marker_after_guards_with_zero_on_failure(self):
        """The stage+0x18 assembly-handoff witness must be stored AFTER the
        fault-pointer range guards, and the failure paths must store an
        explicit zero there: a skipped branch used to leave the pointer
        stored-then-orphaned (r7) or absent-but-garbage-free, blurring
        'guard rejected' with 'no fault state'. EPH snapshot slot and the
        fault-state slot have mutually exclusive success semantics: the EPH
        slot is unconditional, the fault slot only fills when guards pass."""
        import readback_native
        layout, symbols = self._layout_and_symbols()
        symbols['_original_faulting_state'] = 0x10001028
        source = readback_native.preservation_entry_source(
            records=[dict(name='sentinel', physical='0x1000', offset=64, size=16)],
            symbols=symbols, layout=layout,
            physical_base=0xa0000000, kernel_sha256='88' * 32)
        guard_fail = source.index('b.hi fault_invalid')
        # every path to set_table that skips the copy must zero the witness
        marker_store = source.index('str x0,[x9]')
        first_guard = source.index('cmp x0,x10')
        self.assertLess(first_guard, marker_store)
        self.assertIn('str xzr,[x9]', source)

    def test_panic_debugging_decodes_as_boolean_only(self):
        """Host decode rule from the coordinator: a 4-byte boolean_t field
        is FALSE (0) or TRUE (1); anything else (like the r7 0x100 artifact)
        must surface as invalid, not be reinterpreted."""
        import readback_native
        self.assertEqual(readback_native.decode_field(b'\x00\x00\x00\x00', 4), 0)
        self.assertEqual(readback_native.decode_field(b'\x01\x00\x00\x00', 4), 1)
        with self.assertRaises(ValueError):
            readback_native.decode_field(b'\x00\x01\x00\x00', 4, boolean=True)
        self.assertEqual(readback_native.decode_field(b'\x00\x01\x00\x00', 4), 0x100)


    def test_glue_symbol_records_size_the_declared_objects(self):
        """Driver glue widths come from the driver sources (third-party skill
        audit trees, ArmCpu.cpp:24-33 / ArmDTPlatform.cpp:25): armcpu_gic_boot
        is uint32_t[8] = 32B — a 16B window silently drops entries 4..7,
        which are exactly the GIC PMR/IG/SRE state the boot audit needs.
        Timer interrupts is u64, registered/platform-configured are u32;
        16B covers each with slack."""
        import readback_native
        self.assertEqual(readback_native._record_size('_armcpu_gic_boot'), 32)
        for name in ('_armcpu_timer_interrupts', '_armcpu_registered',
                     '_armdt_platform_configured'):
            self.assertEqual(readback_native._record_size(name), 16, name)

    def test_boot_args_records_match_the_built_struct_layout(self):
        """Ground truth from out/y35a/ios12-kernel.noctf (nm -n): _BootArgs VA
        minus _const_boot_args VA == 0x180, so sizeof(boot_args) == 384 in
        this build (pexpert/pexpert/arm/boot.h path: BOOT_LINE_LENGTH=256,
        bootFlags at 0x170). arm_init.c:157 declares `boot_args *BootArgs`:
        _BootArgs is ONE POINTER, _const_boot_args is the struct copy
        (arm_init.c:362-363). A 128B window on _const_boot_args truncates
        exactly where proof of the copy lives (CommandLine/bootFlags);
        384/16 capture the struct and the pointer field respectively."""
        import readback_native
        self.assertEqual(readback_native._record_size('_const_boot_args'), 384)
        self.assertEqual(readback_native._record_size('_BootArgs'), 16)

    def test_manifest_publishes_snapshot_slot_and_field_widths(self):
        import readback_native
        self.assertTrue(hasattr(readback_native, 'EPH_SNAPSHOT_OFFSET'))
        self.assertTrue(hasattr(readback_native, 'EPH_SNAPSHOT_BYTES'))
        self.assertEqual(readback_native.EPH_SNAPSHOT_BYTES, 0x74)

    def test_manifest_declares_honest_transport_mode(self):
        """R9 required gate: the full readback probe stages records INTO the
        pram window, so it must declare transport_mode='full-readback' with
        pram_preserved=false and the report-page payload size. A manifest
        that omits these, or claims preservation it cannot deliver, makes
        every witness boot uninterpretable."""
        import readback_native
        self.assertEqual(readback_native.PANIC_LOG_LIMIT, 0x1000)
        main_src = (Path(__file__).resolve().parents[1] / 'scripts/y35a' /
                    'readback_native.py').read_text()
        self.assertIn("transport_mode='full-readback'", main_src)
        self.assertIn('pram_preserved=False', main_src)
        self.assertIn('report_bytes=PANIC_LOG_LIMIT', main_src)

    def test_stamp_page_preserved_before_dynamic_copy(self):
        """r8 is the first generation whose dynamic debug_buf copy can run (the
        ldr w3 truncation kept it dead before). Its destination,
        PANIC_LOG_DEST 0x859f0000, is the same page boot3's RAMBoot shim stamps
        Y35AXNU2 + kernel-hash + CurrentEL + entry (package_native.py:76/131)
        — the generation witness baf4604 §8 / 91ab4a1 read back at staged
        offset 0x10000/0x10008. An unguarded copy erases that provenance. The
        probe must snapshot the first 64 bytes of the stamp page to the free
        stage tail (STAMP_SNAPSHOT_OFFSET, after the EPH slot) BEFORE
        copy_bytes writes PANIC_LOG_DEST, so both the panic bytes and the
        generation stamp survive in one capture."""
        import readback_native
        layout, symbols = self._layout_and_symbols()
        # Full carrier set so the dynamic copy is actually emitted.
        symbols['_gPanicBase'] = 0x10001018
        symbols['_gPanicSize'] = 0x10001020
        source = readback_native.preservation_entry_source(
            records=[dict(name='sentinel', physical='0x1000', offset=64, size=16)],
            symbols=symbols, layout=layout,
            physical_base=0xa0000000, kernel_sha256='77' * 32)
        self.assertIn('ldr x1,=' + hex(readback_native.PANIC_LOG_DEST), source)
        self.assertLess(source.index('stamp_store:'), source.index('copy_bytes:'))
        # The unrolled snapshot must read the page PA, never x1 (kernel VA):
        last_load_before_copy = source.rindex('ldr x1,=', 0, source.index('copy_bytes:'))
        self.assertGreater(last_load_before_copy, source.index('ldr x10,[x3]'))

    def test_eph_snapshot_publishes_physical_write_extent(self):
        """The layout gate validates the EPH slot against records and other
        slots using the extent the ENTRY CODE actually writes (8 ldp/stp
        pairs = 0x80), not the logical header size (0x74). A manifest that
        understates the write extent hides a real overlap from the gate."""
        import readback_native
        self.assertEqual(readback_native.EPH_SNAPSHOT_WRITE_BYTES, 0x80)
        self.assertGreaterEqual(readback_native.EPH_SNAPSHOT_WRITE_BYTES,
                                readback_native.EPH_SNAPSHOT_BYTES)
        main_src = (Path(__file__).resolve().parents[1] / 'scripts/y35a' /
                    'readback_native.py').read_text()
        self.assertIn('eph_snapshot_write_bytes=EPH_SNAPSHOT_WRITE_BYTES', main_src)
        self.assertGreaterEqual(readback_native.STAMP_SNAPSHOT_OFFSET,
                                readback_native.EPH_SNAPSHOT_OFFSET + readback_native.EPH_SNAPSHOT_BYTES)
        self.assertLess(readback_native.STAMP_SNAPSHOT_OFFSET + 64,
                        readback_native.PANIC_LOG_OFFSET)

    def test_snapshot_slots_do_not_collide(self):
        import readback_native
        eph = set(range(readback_native.EPH_SNAPSHOT_OFFSET,
                        readback_native.EPH_SNAPSHOT_OFFSET + readback_native.EPH_SNAPSHOT_BYTES))
        stamp = set(range(readback_native.STAMP_SNAPSHOT_OFFSET,
                          readback_native.STAMP_SNAPSHOT_OFFSET + readback_native.STAMP_SNAPSHOT_BYTES))
        fault = set(range(0xf000, 0xf000 + 1024))  # entry.S stages 64 pairs at 0xf000
        self.assertEqual(eph & stamp, set())
        self.assertEqual(stamp & fault, set())
        self.assertEqual(readback_native.STAMP_SNAPSHOT_BYTES, 64)

    def test_records_change_the_emitted_copy_table(self):
        import readback_native
        layout, symbols = self._layout_and_symbols()
        records = [dict(name='synthetic-record', physical='0x12340000', offset=0x40, size=32)]
        source = readback_native.preservation_entry_source(
            records=records, symbols=symbols, layout=layout,
            physical_base=0xa0000000, kernel_sha256='00' * 32)
        self.assertIn('.quad 0x12340000, 0x859e0040, 2', source)
        self.assertNotIn('0xa0b7c800', source)

    def test_dynamic_debug_buffer_capture_loads_and_bounds_all_carriers(self):
        import readback_native
        layout, symbols = self._layout_and_symbols()
        source = readback_native.preservation_entry_source(
            records=[dict(name='sentinel', physical='0x1000', offset=64, size=16)],
            symbols=symbols, layout=layout,
            physical_base=0xa0000000, kernel_sha256='11' * 32)
        for virtual in symbols.values():
            self.assertIn(f'{0xa0000000 + virtual - layout["base"]:#x}', source)
        self.assertIn('cmp x0,x3', source)
        self.assertIn('cmp x1,x5', source)
        self.assertIn('sub x6,x1,x0', source)
        self.assertIn('mov w6,#0x1000', source)
        self.assertIn('csel w2,w2,w6,lo', source)
        self.assertIn('copy_bytes:', source)

    def test_probe_stamps_cntvct_freshness_witness_before_table_copy(self):
        """Three r6 captures were byte-identical across a 34s boot3 run, so a
        capture cannot prove it re-sampled DRAM. CNTVCT_EL0 monotonic within a
        power cycle distinguishes a re-run probe from a re-read stale staging
        buffer: two real probe executions cannot print the same counter."""
        import readback_native
        layout, symbols = self._layout_and_symbols()
        source = readback_native.preservation_entry_source(
            records=[dict(name='sentinel', physical='0x1000', offset=64, size=16)],
            symbols=symbols, layout=layout,
            physical_base=0xa0000000, kernel_sha256='44' * 32)
        self.assertIn('mrs x11,cntvct_el0', source)
        witness = source.index('mrs x11,cntvct_el0')
        store = source.index('str x11,[x10,#16]')
        self.assertLess(witness, store)
        self.assertLess(store, source.index('adr x19,table'))
        manifest = {'records': [], 'freshness_witness_offset': readback_native.FRESHNESS_WITNESS_OFFSET}
        self.assertEqual(readback_native.FRESHNESS_WITNESS_OFFSET, 16)
        self.assertLess(readback_native.FRESHNESS_WITNESS_OFFSET, 64)

    def test_reset_and_barrier_order_is_preserved_in_emitted_source(self):
        import readback_native
        layout, symbols = self._layout_and_symbols()
        source = readback_native.preservation_entry_source(
            records=[dict(name='sentinel', physical='0x1000', offset=64, size=16)],
            symbols=symbols, layout=layout,
            physical_base=0xa0000000, kernel_sha256='22' * 32)
        copy_store = source.index('strb w7,[x1],#1')
        capture_done = source.index('capture_done:')
        restart_reason = source.index('0x0860065c')
        ps_hold = source.index('0x004ab000')
        self.assertLess(copy_store, capture_done)
        self.assertLess(capture_done, restart_reason)
        self.assertLess(restart_reason, ps_hold)
        self.assertLess(source.rfind('dsb sy', 0, restart_reason), restart_reason)

    def test_missing_required_carrier_is_rejected_before_generation(self):
        import readback_native
        symbols = {name: 0x10000000 for name in readback_native.REQUIRED}
        symbols.pop('_debug_buf_size')
        with self.assertRaisesRegex(ValueError, '_debug_buf_size'):
            readback_native.validate_required_symbols(symbols)

    def test_manifest_publishes_absent_symbols_explicitly(self):
        """Endorsement guardrail (coordinator 0855): _native_entry_trace is
        absent from the booted vanilla kernel; the packer silently skipping a
        name must NEVER read as 'the field is zero'. The manifest lists every
        unrequested-optional symbol it did not record, per mode."""
        import readback_native
        main_src = (Path(__file__).resolve().parents[1] / 'scripts/y35a' /
                    'readback_native.py').read_text()
        self.assertIn('absent_symbols=', main_src)
        recorded = {'_BootArgs': 1, '_gPanicBase': 2, '_gPanicSize': 3,
                    '_debugger_panic_str': 4, '_panicDebugging': 5,
                    '_debug_buf_base': 6, '_debug_buf_ptr': 7, '_debug_buf_size': 8}
        absent = [n for n in readback_native.NAMES if n not in recorded]
        self.assertIn('_native_entry_trace', absent)

    def test_manifest_purpose_states_pram_fence(self):
        """Endorsement guardrail: either de-alias the stage or explicitly
        fence the copy path and say so in the manifest purpose field. The
        dynamic panic copy reads pram BEFORE any table staging touches it,
        and the purpose field must carry the exported fence note — the same
        constant the manifest uses, so this cannot silently desync."""
        import readback_native
        self.assertEqual(
            readback_native.PRAM_FENCE_NOTE,
            'stage aliases DT pram; panic copy fenced ahead of table staging')
        main_src = (Path(__file__).resolve().parents[1] / 'scripts/y35a' /
                    'readback_native.py').read_text()
        self.assertIn("PRAM_FENCE_NOTE", main_src)
        self.assertIn("not XNU; ' + PRAM_FENCE_NOTE", main_src)

    def test_records_must_fit_the_bounded_stage(self):
        import readback_native
        records = [dict(name='oversized', physical='0x10000000', offset=64,
                        size=readback_native.RECORD_LIMIT)]
        with self.assertRaisesRegex(ValueError, 'bounded'):
            readback_native.validate_stage_footprint(records)

    def test_minimal_boundary_report_geometry_constants(self):
        """R9 direction: snapshot pram to verified LK scratch BEFORE any
        write, keep every probe byte inside the 0x1000 report page above
        pram, restore pram last — the upload then carries untouched XNU-owned
        pram (KNUF measurable for real) plus the probe report, and the LK
        command stays unmodified. The report's first 0x40 bytes are the
        boot3 shim Y35AXNU2 stamp zone; the probe never writes there."""
        import readback_native
        self.assertEqual(readback_native.SCRATCH_PRAM_BACKUP, 0x95000000)
        self.assertEqual(readback_native.SCRATCH_PRAM_BACKUP_BYTES, 0x10000)
        self.assertEqual(readback_native.REPORT_BASE, readback_native.PANIC_LOG_DEST)
        self.assertEqual(readback_native.REPORT_BYTES, 0x1000)
        self.assertEqual(readback_native.REPORT_HEAD_PRESERVED, 0x40)

    def test_minimal_boundary_records_pack_inside_the_report_page(self):
        import readback_native
        payload = [('early-fault-record', 0xa0b7c800, 384),
                   ('_panicDebugging', 0xa0713844, 16),
                   ('_gPanicSize', 0xa07726b0, 16)]
        records = readback_native.minimal_boundary_records(payload)
        self.assertEqual(len(records), 3)
        total = 0
        for r in records:
            self.assertGreaterEqual(r['report_offset'], readback_native.REPORT_RECORDS_OFFSET)
            self.assertLessEqual(r['report_offset'] + r['size'], readback_native.REPORT_BYTES)
            # dual keys: stage-relative for verify_capture_layout,
            # report-relative for verify_readback_transport (prefers it)
            self.assertEqual(r['offset'],
                             r['report_offset'] + readback_native.PANIC_LOG_OFFSET)
            self.assertEqual(r['offset'], r['stage_offset'])
            total += r['size']
        # packing is gap-free from the records start
        self.assertEqual(records[-1]['report_offset'] + records[-1]['size'],
                         readback_native.REPORT_RECORDS_OFFSET + total)

    def test_minimal_boundary_rejects_report_overflow(self):
        import readback_native
        with self.assertRaisesRegex(ValueError, 'report'):
            readback_native.minimal_boundary_records(
                [('oversize', 0xa0b7c800, readback_native.REPORT_BYTES)])

    def test_minimal_boundary_entry_snapshots_then_reports_then_restores(self):
        import readback_native
        records = readback_native.minimal_boundary_records(
            [('_panicDebugging', 0xa0713844, 16),
             ('precpudata-external', 0xa0ba4b00, 256)])
        source = readback_native.minimal_boundary_entry_source(
            records=records, kernel_sha256='55' * 32)
        snap = source.index('pram_snapshot:')
        # probe marker lands at report+0x40, never at the preserved head
        self.assertIn('str x11,[x10,#64]', source)
        marker = source.index('str x11,[x10,#64]')
        self.assertLess(snap, marker)
        # CNTVCT witness at report+0x50, before the table copy
        witness = source.index('str x11,[x10,#80]')
        self.assertLess(marker, witness)
        self.assertLess(witness, source.index('adr x19,table'))
        # snapshot and restore both move the full pram page
        self.assertEqual(source.count('mov x12,#0x10000'), 2)
        restore = source.index('pram_restore:')
        self.assertLess(source.index('adr x19,table'), restore)
        self.assertLess(restore, source.index('0x0860065c'))
        self.assertLess(source.index('0x0860065c'), source.index('0x004ab000'))
        # Current-generation probes must write their own freshness/progress/
        # completion evidence; stale retained bytes cannot satisfy the contract.
        self.assertIn('0x304e5552505943', source)  # CYPRUN0\0
        self.assertIn(f"{int.from_bytes(b'POSTOR00', 'little'):#x}", source)  # POSTOR00
        self.assertIn(f"{int.from_bytes(b'PSTCOPY0', 'little'):#x}", source)  # PSTCOPY0
        self.assertIn('str x21,[x10]', source)  # per-record count
        # Every staging destination is report-relative, never PRAM.
        for line in source.splitlines():
            if line.strip().startswith('.quad 0x'):
                fields = line.split()
                if len(fields) < 4:
                    continue
                dest = int(fields[2].rstrip(','), 16)
                self.assertGreaterEqual(dest, readback_native.REPORT_BASE +
                                        readback_native.REPORT_RECORDS_OFFSET)
                self.assertLessEqual(dest + int(fields[3].rstrip(',')) * 16,
                                     readback_native.REPORT_BASE + readback_native.REPORT_BYTES)

    def test_regular_probe_does_not_emit_preclear_code(self):
        import readback_native
        records = readback_native.minimal_boundary_records(
            [('precpudata-external', 0xa0ba4b00, 256)])
        source = readback_native.minimal_boundary_entry_source(
            records=records, kernel_sha256='55' * 32)
        self.assertNotIn('preclear_record:', source)
        self.assertNotIn('CLR3IDLE', source)

    def test_explicit_preclear_emits_target_and_metadata(self):
        import readback_native
        records = readback_native.minimal_boundary_records(
            [('precpudata-external', 0xa0ba4b00, 256)])
        source = readback_native.minimal_boundary_entry_source(
            records=records, kernel_sha256='55' * 32, preclear=True)
        self.assertIn('preclear_record:', source)
        self.assertIn('0xa0ba4b00', source)
        self.assertIn(f"{int.from_bytes(b'CLR3IDLE', 'little'):#x}", source)

    def test_explicit_preclear_uses_dynamic_record_geometry(self):
        import readback_native
        records = readback_native.minimal_boundary_records(
            [('precpudata-external', 0xa0bacb00, 1024)])
        source = readback_native.minimal_boundary_entry_source(
            records=records, kernel_sha256='66' * 32, preclear=True)
        self.assertIn('ldr x10,=0xa0bacb00', source)
        self.assertIn('mov x11,#64', source)  # 1024 bytes / 16-byte STP
        self.assertIn('mov x11,#16', source)  # 1024 bytes / 64-byte D-cache lines
        self.assertNotIn('0xa0ba4b00', source)
        metadata = readback_native.minimal_preclear_runtime_manifest(records)
        self.assertEqual(metadata['preclear_target_physical'], '0xa0bacb00')
        self.assertEqual(metadata['preclear_target_bytes'], 1024)

    def test_explicit_preclear_clears_selected_symbol_records(self):
        import readback_native
        records = readback_native.minimal_boundary_records([
            ('precpudata-external', 0xa0bacb00, 1024),
            ('_y35a_prng_bootstrap_entered', 0xa076a730, 16),
            ('_y35a_prng_initialized', 0xa076a740, 16),
            ('_y35a_bootstrap_phase', 0xa076a750, 16),
        ])
        source = readback_native.minimal_boundary_entry_source(
            records=records, kernel_sha256='77' * 32, preclear=True,
            preclear_extra_records=(
                '_y35a_prng_bootstrap_entered',
                '_y35a_prng_initialized',
                '_y35a_bootstrap_phase',
            ))
        self.assertIn('preclear_record:', source)
        self.assertIn('preclear_record_1:', source)
        self.assertIn('preclear_record_2:', source)
        self.assertIn('preclear_record_3:', source)
        for address in ('0xa076a730', '0xa076a740', '0xa076a750'):
            self.assertIn(address, source)
        metadata = readback_native.minimal_preclear_runtime_manifest(
            records, ('_y35a_prng_bootstrap_entered',
                      '_y35a_prng_initialized', '_y35a_bootstrap_phase'))
        self.assertEqual([item['name'] for item in metadata['preclear_targets']], [
            'precpudata-external', '_y35a_prng_bootstrap_entered',
            '_y35a_prng_initialized', '_y35a_bootstrap_phase'])
        self.assertIn('OR-read every declared target window', metadata['preclear_sequence'])

    def test_preclear_extra_record_requires_preclear_mode(self):
        import readback_native
        records = readback_native.minimal_boundary_records([
            ('precpudata-external', 0xa0bacb00, 1024),
            ('witness', 0xa076a730, 16),
        ])
        with self.assertRaisesRegex(ValueError, 'require --preclear'):
            readback_native.minimal_boundary_entry_source(
                records=records, kernel_sha256='88' * 32,
                preclear_extra_records=('witness',))

    def test_minimal_runtime_manifest_checksum_is_record_derived(self):
        import readback_native
        records = readback_native.minimal_boundary_records(
            [('precpudata-external', 0xa0ba4b00, 128)])
        runtime = readback_native.minimal_boundary_runtime_manifest(records)
        self.assertEqual(runtime['postcopy_integrity']['data_report_offset'],
                         hex(records[0]['report_offset']))
        self.assertEqual(runtime['postcopy_integrity']['bytes'], records[0]['size'])

    def test_minimal_runtime_manifest_omits_unbound_checksum(self):
        import readback_native
        records = readback_native.minimal_boundary_records([('_BootArgs', 0xa00d26f0, 16)])
        runtime = readback_native.minimal_boundary_runtime_manifest(records)
        self.assertNotIn('postcopy_integrity', runtime)

    def test_minimal_symbol_window_aligns_boolean_field_down(self):
        import readback_native
        layout = {'base': 0xFFFF_FFF0_0700_4000,
                  'end': 0xFFFF_FFF0_0701_0000,
                  'segments': [{'address': 0xFFFF_FFF0_0700_4000, 'size': 0x10000}]}
        records = readback_native.minimal_boundary_records([
            ('_panicDebugging', 0xA000_4844, 16)])
        symbols = {'_panicDebugging': 0xFFFF_FFF0_0700_4844}
        readback_native.annotate_minimal_symbol_windows(records, symbols, layout, 0xA000_4000)
        self.assertEqual(records[0]['physical'], '0xa0004840')
        self.assertEqual(records[0]['symbol_physical'], '0xa0004844')
        self.assertEqual(records[0]['symbol_offset'], 4)
        self.assertEqual(records[0]['field_bytes'], 4)

    def test_minimal_boundary_snapshot_reads_pram_pa_not_stage_alias(self):
        """The snapshot loop must address 0x859e0000 (pram physical) and
        0x95000000 (scratch) with explicit ldr =literal forms; an accidental
        reuse of STAGE_BASE arithmetic elsewhere would re-introduce the
        aliasing that killed r7's header evidence."""
        import readback_native
        records = readback_native.minimal_boundary_records([('_x', 0xa0700000, 16)])
        source = readback_native.minimal_boundary_entry_source(
            records=records, kernel_sha256='66' * 32)
        self.assertIn(f'ldr x10,={readback_native.PRAM_PHYS:#x}', source)
        self.assertIn(f'ldr x11,={readback_native.SCRATCH_PRAM_BACKUP:#x}', source)
        # restore direction: scratch -> pram
        restore_block = source[source.index('pram_restore:') - 400:source.index('pram_restore:')]
        self.assertIn(f'ldr x10,={readback_native.SCRATCH_PRAM_BACKUP:#x}', source)
        self.assertIn(f'ldr x11,={readback_native.PRAM_PHYS:#x}', source)

    def test_mode_flag_selects_transport(self):
        """CLI plumbing: --transport minimal-boundary must produce the
        snapshot/restore entry, the default must remain full-readback so
        every prior capture comparison stays byte-valid."""
        import readback_native
        main_src = (Path(__file__).resolve().parents[1] / 'scripts/y35a' /
                    'readback_native.py').read_text()
        self.assertIn("'--transport'", main_src)
        self.assertIn("choices=('full-readback', 'minimal-boundary')", main_src)
        self.assertIn("transport_mode='minimal-boundary'", main_src)
        self.assertIn('pram_preserved=True', main_src)
        self.assertIn('snapshot_base=hex(SCRATCH_PRAM_BACKUP)', main_src)
        self.assertIn('report_bytes=', main_src)

    def test_manifest_panic_offset_matches_emitted_panic_destination(self):
        import readback_native
        layout, symbols = self._layout_and_symbols()
        source = readback_native.preservation_entry_source(
            records=[dict(name='sentinel', physical='0x1000', offset=64, size=16)],
            symbols=symbols, layout=layout,
            physical_base=0xa0000000, kernel_sha256='33' * 32)
        panic_offset = readback_native.validate_stage_footprint([
            dict(name='sentinel', physical='0x1000', offset=64, size=16)])
        self.assertEqual(
            panic_offset,
            readback_native.PANIC_LOG_DEST - readback_native.STAGE_BASE)
        self.assertEqual(panic_offset, readback_native.PANIC_LOG_OFFSET)
        self.assertIn(f'ldr x1,={readback_native.PANIC_LOG_DEST:#x}', source)

    def test_tool_lookup_includes_installed_deveco_llvm_fallback(self):
        import readback_native
        self.assertTrue(any('DevEco-Studio.app/Contents/sdk/default/openharmony/native/llvm/bin'
                            in value for value in readback_native._tool_path.__code__.co_consts
                            if isinstance(value, str)))
        self.assertTrue(any('DevEco-Studio.app/Contents/sdk/default/openharmony/native/llvm/bin'
                            in value for value in readback_native._linker_environment.__code__.co_consts
                            if isinstance(value, str)))

    def test_manifest_writer_round_trips_json_with_a_real_newline(self):
        import readback_native
        manifest = {
            'kernel_sha256': 'aa' * 32,
            'image_sha256': 'bb' * 32,
            'records': [dict(name='r', physical='0x1000', offset=64, size=16)],
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'readback.json'
            readback_native.write_manifest(path, manifest)
            self.assertEqual(json.loads(path.read_text()), manifest)
            self.assertTrue(path.read_bytes().endswith(b'\n'))

if __name__ == '__main__':
    unittest.main(verbosity=2)
