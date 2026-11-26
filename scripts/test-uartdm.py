#!/usr/bin/env python3
"""Host-only UARTDM contracts. No kernel build, devices, downloads or installs.

Run with -I; --xnu-source may be pristine or the current prepared recipe tree.
Only the three affected source files are copied into this worktree's .cache.
"""
import argparse
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--xnu-source', type=Path, required=True)
parser.add_argument('--clang', default='/usr/bin/clang')
parser.add_argument('--baseline', action='store_true', help='Run tests before applying the new patch (RED)')
args = parser.parse_args()
work = ROOT / '.cache/uartdm-tests'
work.mkdir(parents=True, exist_ok=True)
for rel in ('pexpert/arm/pe_serial.c', 'pexpert/pexpert/arm/protos.h'):
    dst = work / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(args.xnu_source / rel, dst)
header = work / 'pexpert/pexpert/arm/uartdm.h'
if header.exists():
    header.unlink()  # Only this script's generated copy, never source inputs.
if not args.baseline:
    subprocess.run(['patch', '--batch', '--fuzz=0', '-p1', '-d', str(work), '-i',
                    str(ROOT / 'patches/xnu/native-uartdm-console.patch')], check=True)
# All driver statements and real serial enum are retained. Only kernel include
# dependencies are replaced by the host service shims in test_dispatch.c.
source = (work / 'pexpert/arm/pe_serial.c').read_text()
host = '\n'.join(line for line in source.splitlines()
                 if not line.startswith('#include ') or '<pexpert/arm/uartdm.h>' in line)
(work / 'pe_serial_host.c').write_text(host + '\n')
flags = ['-std=c11', '-Wall', '-Wextra', '-Werror', '-g', '-O1',
         '-fsanitize=address,undefined', '-fno-sanitize-recover=all',
         '-I', str(work / 'pexpert'), '-I', str(work)]
for name, extra in [('test_uartdm', []), ('test_dispatch', ['-DXNU_NATIVE_UARTDM=1']),
                    ('test_dispatch', ['-DXNU_NATIVE_UARTDM=0'])]:
    output = work / (name + ('-off' if extra == ['-DXNU_NATIVE_UARTDM=0'] else ''))
    subprocess.run([args.clang, *flags, *extra, str(ROOT / 'tests/uartdm' / (name + '.c')),
                    '-o', str(output)], check=True)
    subprocess.run([str(output)], check=True, timeout=10)
# Exercise only the recipe's opt-in block, not the network/build-capable recipe.
recipe = (ROOT / 'scripts/build-xnu-4k-baseline.sh').read_text()
block = recipe.split('NATIVE_UARTDM=${XNU_NATIVE_UARTDM:-0}', 1)[1].split('ZONE_PGZ_PROBE=', 1)[0]
block = 'NATIVE_UARTDM=${XNU_NATIVE_UARTDM:-0}' + block
recipe_root = work / 'recipe'
objdir = recipe_root / 'build/xnu/ios-obj/DEVELOPMENT_ARM64_BCM2837'
(objdir / 'pexpert/DEVELOPMENT').mkdir(parents=True, exist_ok=True)
stamp = objdir / '.native-uartdm-mode'
obj = objdir / 'pexpert/DEVELOPMENT/pe_serial.o'
if stamp.exists():
    stamp.unlink()
for mode in ('0', '1', '0', 'invalid'):
    obj.write_text('test-owned stale object')
    script = ('set -eu\nROOT="$1"\nXNU_NATIVE_UARTDM="$2"\nEXTRA_MAKE_ARGS=()\n' + block +
              '\nprintf "%s\\n" "${EXTRA_MAKE_ARGS[@]}"\n')
    result = subprocess.run(['bash', '-c', script, 'uartdm-recipe', str(recipe_root), mode],
                            capture_output=True, text=True)
    if mode == 'invalid':
        assert result.returncode != 0 and 'must be 0 or 1' in result.stderr
        assert obj.exists()
    else:
        assert result.returncode == 0, result.stderr
        assert result.stdout.strip() == 'pe_serial.o_CFLAGS_ADD=-DXNU_NATIVE_UARTDM=' + mode
        if stamp.exists():
            assert stamp.read_text().strip() == mode and not obj.exists()
print('PASS: recipe opt-in flags, invalid value rejection, object invalidation on toggles')
print('PASS: host -Werror and ASan/UBSan; no kernel or physical serial validation claimed')
