#!/usr/bin/env python3
"""Build a RAM-only RMI4/S3202 identity probe for the Y35A LK2nd handoff.

Runs inside the Linux build container only (clang++ /usr/bin paths are
the container's, same convention as build-xnu-4903-kernel.py):
  docker exec unixnu-y35a-native-20261103 python3 \
    /work/UniXNU-y35a/scripts/y35a/probe_rmi.py --directory DIR \
    --stock-boot /work/evidence-stock-boot.img
(First docker-cp rmi_probe.cpp + probe_rmi.py in, and the host
evidence/y35a-20261102/stock-boot.img to /work/evidence-stock-boot.img;
the container checkout has no evidence blob.)

Plan docs/superpowers/plans/2026-11-05-y35a-touch-driver.md T0.2. The
probe reads the QUP5 SE window, dumps TLMM/GCC register windows raw and
issues one read-only identity transaction against slave 0x20.

Geometry discipline (defect-1 + CAPTURE-TRANSPORT-AUDIT-20261109.md
candidate, adopted 10:0x): every address is DERIVED, none hardcoded
here —
  pram window         from make_adt.py's node('pram',...) reg literals
  report base         from readback_native.py PANIC_LOG_DEST (above pram
                      by construction; the touch probe writes NOTHING
                      into pram, preserving remnants for the readback
                      line; the standalone probe needs no snapshot
                      dance — no XNU runs and the probe never resets)
  LK stage extent     from readback_native.py STAGE_BASE + the measured
                      LK contract fastboot_stage(0x859e0000, 0x11000)
                      cited in the audit doc
  entry stack         pram_base - 0x1000 (below pram, grows downward)
When the fixer migrates the literals, the next build re-stamps itself
with zero edits. Both gates run on every build into the manifest:
verify_capture_layout.py checks the probe's own write interval against
pram (green by construction here), verify_capture_transport.py
cross-checks the full shared map including the readback line's
snapshot interval parsed from the audit doc. The device-run refusal
lives in CURRENT.md Next-Work #0, not in this build script — an
offline build must stay reproducible.
"""
from pathlib import Path
import argparse, hashlib, json, os, re, struct, subprocess, sys
from package_native import android_container, select_device_dt, align

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]

# sizeof(Report) in rmi_probe.cpp; the C++ side static_asserts the fit
# (report must live between pram end and the LK stage extent), this
# side mirrors the field offsets into the manifest. The compile is the
# authority — if either drifts, re-derive from clang, not from here.
# Report layout is derived from rmi_probe.cpp. The corrected collector keeps
# only the exact TLMM/QUP5 windows needed for the handoff decision.
REPORT_BYTES = 0x124

def _literal(path, name):
    m = re.search(rf'^{name} = (0x[0-9a-fA-F]+)', path.read_text(), re.M)
    if not m:
        raise SystemExit(f'{name} literal not found in {path.name}')
    return int(m.group(1), 0)

def stage_base():
    return _literal(HERE / 'readback_native.py', 'STAGE_BASE')

def report_base():
    return _literal(HERE / 'readback_native.py', 'PANIC_LOG_DEST')

def pram_window():
    m = re.search(r"node\('pram',\[\('reg',struct\.pack\('<QQ',(0x[0-9a-f]+),(0x[0-9a-f]+)\)\)\]\)",
                  (HERE / 'make_adt.py').read_text())
    if not m:
        raise SystemExit('pram reg literal not found in make_adt.py')
    return int(m.group(1), 0), int(m.group(2), 0)

def lk_stage_size():
    """Measured LK contract, cited in the audit doc:
    cmd_oem_y35a_panic calls fastboot_stage(0x859e0000, 0x11000)."""
    m = re.search(r'fastboot_stage\(\(void \*\)0x(859e0000), (0x[0-9a-f]+)\)',
                  (REPO / 'docs/coordination/claude-codex-sync/CAPTURE-TRANSPORT-AUDIT-20261109.md').read_text())
    if not m:
        raise SystemExit('LK stage extent not found in CAPTURE-TRANSPORT-AUDIT doc')
    return int(m.group(2), 0)

def snapshot_interval():
    """Readback line's candidate scratch snapshot interval, parsed from
    the audit doc's candidate block ('copy 0x859e0000..0x859f0000 ->
    0x95000000..0x95010000'). The touch probe never writes it; the
    transport gate validates the whole shared map including this."""
    doc = (REPO / 'docs/coordination/claude-codex-sync/CAPTURE-TRANSPORT-AUDIT-20261109.md').read_text()
    m = re.search(r'-> (0x[0-9a-f]+)\.\.(0x[0-9a-f]+)', doc)
    if not m:
        raise SystemExit('snapshot interval not found in CAPTURE-TRANSPORT-AUDIT doc')
    lo, hi = int(m.group(1), 0), int(m.group(2), 0)
    return lo, hi - lo

def run_json(cmd):
    r = subprocess.run([sys.executable] + cmd, capture_output=True, text=True)
    try:
        return json.loads(r.stdout)
    except Exception:
        return {'ok': False, 'rc': r.returncode, 'stdout': r.stdout, 'stderr': r.stderr}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--directory', required=True, type=Path)
    p.add_argument('--stock-boot', required=True, type=Path)
    a = p.parse_args(); a.directory.mkdir(parents=True, exist_ok=False)
    sb, rb = stage_base(), report_base()
    pb, ps = pram_window()
    lk_sz = lk_stage_size()
    snap_b, snap_s = snapshot_interval()

    entry = '''.section .text.entry
.global _start
_start:
 b enter
 .word 0
 .quad 0x80000
 .quad image_end-_start
 .quad 0,0,0,0
 .word 0x644d5241,0
enter:
 msr daifset,#15
 mrs x9,sctlr_el1
 tbnz x9,#0,halt
 ldr x9,={stack:#x}
 mov sp,x9
 bl probe_main
halt:
 wfe
 b halt
 .ltorg
'''.format(stack=pb - 0x1000)  # below pram; derived, moves with migration
    (a.directory / 'entry.S').write_text(entry)
    (a.directory / 'layout.ld').write_text(
        'ENTRY(_start)\nSECTIONS { . = 0x80080000; '
        '.text : { *(.text.entry) *(.text*) } .rodata : { *(.rodata*) } '
        '.data : { *(.data*) } .bss : { *(.bss*) *(COMMON) } '
        'image_end = .; /DISCARD/ : { *(.comment) *(.eh_frame*) } }\n')
    # The XNU build exports CCC_OVERRIDE_OPTIONS globally to inject Apple-clang
    # warning suppressions. Ubuntu clang rejects those options under -Werror;
    # keep this standalone probe build independent of the parent kernel build.
    build_env = dict(os.environ)
    build_env.pop('CCC_OVERRIDE_OPTIONS', None)
    subprocess.run([
        '/usr/bin/clang++', '--target=aarch64-none-elf', '-O2', '-nostdlib',
        '-ffreestanding', '-fno-exceptions', '-fno-rtti', '-fno-builtin',
        '-mgeneral-regs-only', '-std=c++17', '-Wall', '-Werror',
        f'-DY35A_REPORT_BASE={rb}UL', f'-DY35A_PRAM_BASE={pb}UL',
        f'-I{HERE}', f'-I{REPO / "drivers/QcomQupI2c"}',
        '-fuse-ld=lld', '-Wl,-T,layout.ld', 'entry.S', str(HERE / 'rmi_probe.cpp'),
        '-o', 'probe.elf'], cwd=a.directory, check=True, env=build_env)
    subprocess.run(['/usr/bin/llvm-objcopy', '-O', 'binary', 'probe.elf', 'probe.bin'],
                   cwd=a.directory, check=True)
    stock = a.stock_boot.read_bytes()
    v = struct.unpack_from('<10I', stock, 8); page = v[7]
    off = page + align(v[0], page) + align(v[2], page) + align(v[4], page)
    image = android_container((a.directory / 'probe.bin').read_bytes(),
                              select_device_dt(stock[off:off + v[8]]))
    (a.directory / 'rmi-probe-not-xnu.img').write_bytes(image)

    geometry = dict(
        pram_base=hex(pb), pram_size=hex(ps),
        report_pa=hex(rb), report_size=hex(REPORT_BYTES),
        stage_source_pa=hex(sb), stage_source_size=hex(lk_sz),
        pram_snapshot_pa='not_written_by_this_probe',
        snapshot_candidate=hex(snap_b), snapshot_candidate_size=hex(snap_s),
        entry_stack=hex(pb - 0x1000))
    record = dict(
        purpose='RAM-only RMI4 identity characterization; not XNU',
        image_sha256=hashlib.sha256(image).hexdigest(),
        magic='Y35ARD01',
        # R9-READBACK-TRANSPORT-RECONCILIATION-20261109.md Required
        # gates, item 1: every image manifest declares its transport
        # mode. The touch probe is minimal-boundary IN GEOMETRY (report
        # page only, <= 0x1000, zero pram writes). It is NOT the
        # readback line's snapshot/restore mode — as a standalone image
        # there is no XNU/EPH writer to preserve against, so
        # pram_preserved holds by zero-write. Declared explicitly so
        # its green gates can never be mistaken for readback-line
        # transport evidence (R9's Communication-to-the-fixer rule).
        transport_mode='minimal-boundary',
        mode_note='standalone T0.2 probe: pram_preserved=true by zero '
                  'writes, not by snapshot/restore; snapshot interval '
                  'is candidate geometry validated for the shared map '
                  'only',
        pram_preserved=True,
        report_bytes=REPORT_BYTES,
        staged_bytes=lk_sz,  # LK uploads the whole stage range
        geometry=geometry,
        report=struct_layout(),
        records=[],  # this probe stages no kernel-symbol records
        readback='body offset 0x10000 of `oem y35a panic` upload '
                 '(report_pa - stage_source_pa); t_boot at +0x08 is the '
                 'freshness witness (baf4604)')
    manifest = a.directory / 'manifest.json'

    def gates():
        g = {}
        gl = HERE / 'verify_capture_layout.py'
        if gl.is_file():
            # probe's own write interval vs pram: stage args = report
            # interval (the probe writes nothing else to memory).
            tmp = a.directory / 'manifest-layout.json'
            tmp.write_text(json.dumps({'staged_bytes': REPORT_BYTES, 'records': []}))
            g['layout'] = run_json([str(gl), '--manifest', str(tmp),
                                    '--pram-base', hex(pb), '--pram-size', hex(ps),
                                    '--stage-base', hex(rb), '--stage-size', hex(REPORT_BYTES)])
        gt = HERE / 'verify_capture_transport.py'
        if gt.is_file():
            g['transport'] = run_json([str(gt),
                                       '--pram-base', hex(pb), '--pram-size', hex(ps),
                                       '--lk-stage-base', hex(sb), '--lk-stage-size', hex(lk_sz),
                                       '--snapshot-base', hex(snap_b), '--snapshot-size', hex(snap_s),
                                       '--report-base', hex(rb), '--report-size', hex(REPORT_BYTES),
                                       '--scratch-base', hex(0x90000000), '--scratch-size', hex(0x10000000),
                                       '--reserved', '0x90aea000:0x2900000'])
        gm = HERE / 'verify_readback_transport.py'
        if gm.is_file():
            # R9 mode gate reads the declared fields straight from the
            # real manifest (written before gates() runs).
            g['mode'] = run_json([str(gm), '--manifest', str(manifest),
                                  '--mode', 'minimal-boundary',
                                  '--pram-base', hex(pb), '--pram-size', hex(ps),
                                  '--lk-stage-base', hex(sb), '--lk-stage-size', hex(lk_sz),
                                  '--report-base', hex(rb), '--report-size', hex(REPORT_BYTES),
                                  '--snapshot-base', hex(snap_b), '--snapshot-size', hex(snap_s),
                                  '--scratch-base', hex(0x90000000), '--scratch-size', hex(0x10000000),
                                  '--reserved', '0x90aea000:0x2900000'])
        return g

    manifest.write_text(json.dumps(record, indent=2) + '\n')
    record['gates'] = gates()
    manifest.write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps(record, indent=2))

def struct_layout():
    """Byte offsets of the Report fields (mirror of rmi_probe.cpp; the
    compile is the authority — if either side drifts, re-derive from
    clang -Xclang -ast-dump rather than editing numbers here)."""
    return {
        'magic': 0x00, 't_boot': 0x08, 'cntfrq': 0x10,
        'status': 0x18, 'err': 0x1c, 'se_dump': 0x20,
        't_xfer0': 0x50, 't_xfer1': 0x58, 't_end': 0x60,
        'clkctl_after': 0x68, 'err2': 0x6c, 'page0': 0x70, 'f01': 0x78,
        'attn_input': 0x90, 'attn_status': 0xa0,
        'tlmm_target': 0xb0, 'gcc_q5': 0xf0,
    }

if __name__ == '__main__':
    main()
