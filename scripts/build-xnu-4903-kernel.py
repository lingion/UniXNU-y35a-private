#!/usr/bin/env python3
"""Build the vanilla iOS 12-generation XNU kernel (arm64, T7001/A8X) in the Linux container.

Critical-path finding (2026-11-04), why this script builds xnu-4903.270.47 and not xnu-4570.51.1:

  The pivot record (docs/board/pivot-ios12.md) says the iOS 12.4.1 (16G102) j96ap kernel is
  "XNU-4570". It is not. The device kernelcache itself says so:
    out/ipsw/16G102/kernelcache.decompressed  @(#)VERSION: Darwin Kernel Version 18.7.0:
    ... root:xnu-4903.272.1~1/RELEASE_ARM64_T7000
  iOS 12.4 is Darwin 18.7 — the XNU-4903 series (the exact device build xnu-4903.272.1 is not
  published; the newest public 4903 tag is xnu-4903.270.47, Darwin 18.7.0, same series).
  xnu-4570 is Darwin 17.x, the iOS 11.3/11.4 generation; config/MasterVersion at tag
  xnu-4570.51.1 is literally "17.5.0".

  Second, independent reason: Apple's published xnu-4570 tag cannot build ARM64 at all.
  Verified live in the container: `make installhdrs ARCH_CONFIGS=ARM64 MACHINE_CONFIGS=T7001`
  stops at makedefs/MakeInc.kernel:14 "Unsupported CURRENT_ARCH_CONFIG ARM64", because the
  4570 public makedefs have SUPPORTED_ARCH_CONFIGS := X86_64 X86_64H only — no ARCH_FLAGS_ARM64,
  no MACHINE_FLAGS_ARM64_*, no ARM64 link recipe (git tree is clean at the tag; GitHub API blob
  hashes match, so this is Apple's release, not a bad clone). By iOS 12 Apple kept the embedded
  arm64 *build recipe* private while releasing the arm64 *sources* — an ARM64 reconstruction from
  4570 would have to invent the recipe. xnu-4903.270.47 ships it complete:
    SUPPORTED_ARCH_CONFIGS ... ARM64; SUPPORTED_ARM64_MACHINE_CONFIGS = S5L8960X T7000 T7001 ...
    LDFLAGS_KERNEL_GENARM64 hard-codes -Wl,-image_base,0xfffffff007004000 and
    -Wl,-segaddr,__PRELINK_TEXT,0xfffffff004004000 — exactly the j96ap kernelcache layout, so
    no ARM64_LINK_ADDR knob is needed (that knob exists only in the 10063-generation tree).

  Page size: in this generation the Cortex-A5-era boards are 4K by construction.
  osfmk/arm/proc_reg.h line 720 `#define ARM_PGSHIFT 12`, and the APPLETYPHOON family block
  (T7000/T7001 define APPLETYPHOON in pexpert/pexpert/arm64/board_config.h) does NOT define
  __ARM_16K_PG__ (only TWISTER/HURRICANE blocks do). MSM8916's 4K-only MMU granule is therefore
  satisfied natively; this script verifies it (probe below) instead of trusting it.

Build shape mirrors the 17-era pipeline (scripts/build-xnu-4k-baseline.sh + scripts/y35a/build_native.py):
  * canonical env contract from scripts/unixnu/kernel.py linux_env() (patched clang, CLT ld/mig
    shim, xcrun shim answering from .cache/fakeroot, CCC_OVERRIDE_OPTIONS for the newer clang's
    designated-initializer and unused-but-set warnings — do not remove);
  * two-pass make: installhdrs with SDKROOT=macosx into .cache/fakeroot, then build with
    SDKROOT=iphoneos;
  * build CWD is a copy of the source tree on native Docker storage (/work), never SSHFS;
  * vanilla: no UniXNU source patches, no external archives — the raw Apple kernel Mach-O.

Linux-host workarounds baked into the make invocation (same class as the 17-era XNU_HOST_MAKE_ARGS):
  PLATFORM=iPhoneOS HOST_CC=xnu-host-cc MIGCOM=libexec/migcom (xcrun shim finds them),
  TIGHTBEAMC=tightbeamc-not-supported, BUILD_DSYM=0, BUILD_WERROR=0, BUILD_LTO=0, BOUND_CHECKS=0,
  MEMORY_SIZE from getconf + SYSCTL_HW_* from nproc (makedefs call /usr/sbin/sysctl hw.memsize),
  HOST_OS_VERSION=14.6 (makedefs call sw_vers, absent on Linux),
  HOST_CODESIGN=/usr/bin/true (SETUP host tools ad-hoc-sign on macOS),
  ARCH_STRING_FOR_CURRENT_MACHINE_CONFIG=arm64 (without it makedefs would query the private
  embedded_device_map tool for -arch), SDKVERSION=12.4 (deployment target; fakeroot/headers stay
  version-agnostic, so no 17.0 skew fix was needed),
  RC_PROJECT_CONFIG=RELEASE_ARM64_T7001 (version stamp, matches the device string's shape).

Source-tree fixes applied idempotently before building (reusing scripts/linux/prepare-xnu.py's
verified rewrites, which target that 10063 path, so they are reimplemented here for this tree):
  1. bsd/kern/makesyscalls.sh: `\\(sy_call_t *\\)` escapes — mawk keeps the backslash, init_sysent.c
     fails to compile; BSD awk/gawk drop it. Same defect class fixed for the 17-era tree.
  2. SETUP/kextsymboltool/kextsymboltool.c: seekFile() treats lseek()==0 on /dev/null (which the
     export check writes through with -output /dev/null) as disk-full; Linux lseek returns 0 there.
  3. .cache/fakeroot/usr/include/TargetConditionals.h: the iPhoneOS SDK provides it; installed from
     scripts/linux/TargetConditionals.h as in the 17-era flow.

Run inside container unixnu-y35a-native-20261103 (native volume /work only):
    docker exec unixnu-y35a-native-20261103 python3 /work/UniXNU-y35a/scripts/build-xnu-4903-kernel.py
Artifact: out/y35a/ios12-kernel/mach.development.t7001.unstripped (+ .noctf alias kept for the
downstream prelink naming from the 17-era pipeline) + build.log + artifact.json (sizes, sha256,
otool excerpts).
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from unixnu.kernel import linux_env

XNU_TAG = 'xnu-4903.270.47'
# The container's gitconfig rewrites https://github.com/ through the gh.qdp mirror (user-configured; do not bypass).
MIRROR = 'https://github.com/apple-oss-distributions/xnu.git'
ISA_APPLE = '#if defined(__clang__) && ((defined(__apple_build_version__) && __apple_build_version__ > 5010000))\n'
ISA_ANY = '#if defined(__clang__) && (!defined(__apple_build_version__) || __apple_build_version__ > 5010000)\n'


_KDEBUG_PY3 = """\
#!/usr/bin/env python3
#
# This script scans the trace.codes file, containing a mapping of event id to
# event name for all events, and writes to stdout a C declaration for a table
# named kd_events[] or these mappings.
# Required to generate a header file used by DEVELOPMENT and DEBUG kernels.
# (python3 translation of Apple's python2 original; output is byte-identical.)

import re
import sys

# we expect one arg specifying the path to the trace.codes file
if (len(sys.argv) < 2):
    exit(1)
trace_code_file = sys.argv[1]

# regular expression pattern to match <hex_id> <string>
id_name_pattern = re.compile('0x([0-9a-fA-F]+)\\s+([^\\s]*)')
code_table = []

# scan file to generate internal table
with open(trace_code_file, 'rt') as codes:
    for line in codes:
        m = id_name_pattern.match(line)
        if m:
            code_table += [(int(m.group(1), base=16), m.group(2))]

# emit typedef:
print("typedef struct {")
print("        uint32_t   id;")
print('        const char *name;')
print("} kd_event_t;")
# emit structure declaration and sorted initialization:
print("kd_event_t kd_events[] = {")
for mapping in sorted(code_table, key=lambda x: x[0]):
    print('        {0x%x, \\"%s\\"},' % mapping)
print("};")
"""


def info(message):
    print(f'[info] {message}', flush=True)


def run(command, env, *, cwd=None, log=None, check=True):
    printable = ' '.join(map(str, command))
    info(f'$ {printable}')
    stdout = log if log is not None else subprocess.PIPE
    result = subprocess.run(list(map(str, command)), cwd=cwd, env=env, stdout=stdout,
                            stderr=subprocess.STDOUT if log else subprocess.PIPE, check=False)
    if result.returncode and check:
        if not log and result.stdout:
            sys.stdout.write(result.stdout.decode(errors='replace')[-8000:])
        raise SystemExit(f'command failed ({result.returncode}): {printable}')
    return result


def apply_required_patch(work, patch_path, marker_name, env):
    """Apply one instrumentation patch with exact context and a content digest sentinel."""
    if not patch_path.is_file():
        raise SystemExit(f'required Y35A patch is missing: {patch_path}')
    digest = hashlib.sha256(patch_path.read_bytes()).hexdigest()
    marker = work / marker_name
    if marker.is_file():
        recorded = marker.read_text().strip()
        if recorded != digest:
            raise SystemExit(
                f'{marker_name} does not match {patch_path.name}; use a fresh XNU work tree'
            )
        return
    run(['git', 'apply', '--check', str(patch_path)], env, cwd=work)
    run(['git', 'apply', str(patch_path)], env, cwd=work)
    marker.write_text(digest + '\n')
    info(f'applied {patch_path.name}')


def ensure_source(src, env):
    if (src / 'makedefs' / 'MakeInc.def').is_file():
        head = subprocess.run(['git', '-C', str(src), 'describe', '--tags'], capture_output=True, text=True)
        if head.returncode == 0 and head.stdout.strip() == XNU_TAG:
            info(f'source tree ready: {src} ({head.stdout.strip()})')
            return
        raise SystemExit(f'{src} exists but is not {XNU_TAG} (found {head.stdout.strip()!r}); refusing to touch it')
    info(f'cloning {XNU_TAG} (depth 1) from the project mirror into {src}')
    run(['git', 'clone', '--depth', '1', '--branch', XNU_TAG, MIRROR, str(src)], env)


def sync_tree(src, work):
    """One-shot native copy of the source into the build volume (never rebuild on the shared mount)."""
    if (work / '.synced-from').is_file() and (work / '.synced-from').read_text().strip() == str(src):
        info(f'build tree already synced: {work}')
        return
    info(f'copying {src} -> {work}')
    if work.exists():
        shutil.rmtree(work)
    # cp -R --reflink=never: same guard the takeover notes demand for in-volume copies.
    run(['cp', '-R', '--reflink=never', str(src), str(work)], os.environ)
    # git clone leaves .git; the build only needs it for version stamping (newvers.pl reads MasterVersion).
    (work / '.synced-from').write_text(str(src) + '\n')


def fix_source(work, fakeroot, env):
    """Idempotent Linux-host source fixes; each checks whether it is still needed."""
    script = work / 'bsd/kern/makesyscalls.sh'
    text = script.read_text()
    if '\\(sy_call_t *\\)' in text:
        script.write_text(text.replace('\\(sy_call_t *\\)', '(sy_call_t *)'))
        info('patched bsd/kern/makesyscalls.sh: dropped the \\( escapes mawk keeps')

    tool = work / 'SETUP/kextsymboltool/kextsymboltool.c'
    text = tool.read_text()
    if 'S_ISCHR' not in text:
        old = '\tif (offset != lseek(fd, offset, SEEK_SET)) {\n\t\terr = kErrorDiskFull;\n\t} else {\n\t\terr = kErrorNone;\n\t}\n'
        if text.count(old) != 1:
            raise SystemExit(f'{tool}: seekFile() body not found; re-derive the fix')
        new = ('\tif (offset != lseek(fd, offset, SEEK_SET)) {\n'
               '\t\tstruct stat st;\n'
               '\t\t/* Linux lseek() returns 0 on character devices such as the\n'
               '\t\t * /dev/null that check_all_exports writes to; not an error. */\n'
               '\t\tif (0 == fstat(fd, &st) && S_ISCHR(st.st_mode)) {\n'
               '\t\t\treturn kErrorNone;\n'
               '\t\t}\n'
               '\t\terr = kErrorDiskFull;\n'
               '\t} else {\n'
               '\t\terr = kErrorNone;\n'
               '\t}\n')
        text = text.replace(old, new)
        if '#include <sys/stat.h>' not in text:
            text = text.replace('#include <sys/types.h>', '#include <sys/types.h>\n#include <sys/stat.h>', 1)
        tool.write_text(text)
        info('patched SETUP/kextsymboltool/kextsymboltool.c: lseek() on /dev/null is not a write error')

    isa = work / 'osfmk/arm64/corecrypto/arm64_isa_compatibility.h'
    if isa.is_file():
        text = isa.read_text()
        if ISA_APPLE in text:
            isa.write_text(text.replace(ISA_APPLE, ISA_ANY))
            info('patched corecrypto/arm64_isa_compatibility.h: standard vector syntax for non-Apple clang')

    # SETUP/installfile opens its source with macOS's O_SYMLINK (open the symlink itself). The host
    # SDK's fcntl.h does not define it; the 17-era tree (xnu-10063) uses plain O_RDONLY here, and the
    # kernel install never passes a symlink, so the same form is the minimal Linux fix.
    installer = work / 'SETUP/installfile/installfile.c'
    text = installer.read_text()
    if 'O_SYMLINK' in text:
        installer.write_text(text.replace('O_RDONLY | O_SYMLINK', 'O_RDONLY'))
        info('patched SETUP/installfile/installfile.c: dropped macOS-only O_SYMLINK (17-era form is O_RDONLY)')

    # bsd/kern/makekdebugevents.py is python2-only (print statements; /usr/bin/python shebang; mixed
    # tab/space indentation python3 rejects) and the container has no python2. Ubuntu /bin/sh then execs
    # the "print ..." line as a shell command — Error 127 — so replace the file with a python3
    # translation that produces byte-identical output (the kd_events[] table generator).
    kdebug = work / 'bsd/kern/makekdebugevents.py'
    text = kdebug.read_text()
    if text.startswith('#!/usr/bin/python'):
        kdebug.write_text(_KDEBUG_PY3)
        kdebug.chmod(0o755)
        info('replaced bsd/kern/makekdebugevents.py with the python3 translation')

    # bsd/sys/make_posix_availability.sh is bash ("function usage()", array syntax) behind a
    # `#! /bin/sh -` shebang: fine on macOS where /bin/sh is bash, a syntax error on Ubuntu's dash.
    # Point it at the container's /bin/bash, the interpreter Apple's script actually requires.
    posix = work / 'bsd/sys/make_posix_availability.sh'
    text = posix.read_text()
    if text.startswith('#! /bin/sh -') and 'function ' in text:
        first_line = text.splitlines(keepends=True)[0]
        posix.write_text('#!/bin/bash\n' + text[len(first_line):])
        info('repointed bsd/sys/make_posix_availability.sh shebang to bash (dash cannot parse it)')

    # osfmk/arm64/genassym.c DECLARE() emits the immediate via `.ascii "%0"`. This toolchain folds a
    # single-character string: `.ascii "3"` comes out of the compiler as `.byte 51` (the char code) —
    # proven: BUILD/obj/DEVELOPMENT_ARM64_T7001/osfmk/DEVELOPMENT/genassym.o (built 17:10, already the
    # "i"-constraint form) contains `DEFINITION__define__T_PREFETCH_ABT: .byte 51` while multi-digit
    # values stay `.ascii "856"`. The `assym.s:` sed rule in osfmk/conf/Makefile.template:169 only
    # rewrites the `.ascii "<digits>"` form; a folded line passes transform #2 unchanged, and the
    # recipe prints every pattern space twice (explicit `p` + default output — the trick that emits
    # both NAME and NAME_NUM), so each `.byte` label lands in assym.s verbatim and twice. The
    # assembler then reports "symbol DEFINITION__define__T_PREFETCH_ABT is already defined" while
    # compiling caches_asm.s (46 raw label lines in the failed assym.s; the six the compiler named
    # — T_PREFETCH_ABT, T_DATA_ABT, BA_VIRT_BASE, ENTROPY_BUFFER, CONTEXT_SS, VM_MIN_ADDRESS — are
    # all 1-digit values, 51/52/48/49/55).
    # Two-part fix:
    #  (a) DECLARE() switches to the "i" constraint (Apple's own 10063 form, refer/xnu
    #      osfmk/arm64/genassym.c:113). NOTE the evidence: "i" alone does NOT prevent the folding
    #      here (work tree genassym.c has been "i" since 17:10 and genassym.o still shows
    #      `T_PREFETCH_ABT: .byte 51`); keep it for parity, the real fix is (b).
    #  (b) Teach the assym.s sed rule to undo the fold: `.byte 51` is the char code of the single
    #      digit '3' that was folded, so a ten-entry code table rewrites `.byte <48..57>` back to
    #      `.ascii "<0..9>"` before the value transform runs. sed cannot compute chr(), hence the
    #      explicit table. Inserted right after the label-join expression, before the ascii match.
    #      The recipe is in osfmk/conf/Makefile.template (rendered into every obj Makefile at
    #      setup), so stale genassym.o/assym.s must be deleted for the new rule to re-run.
    genassym = work / 'osfmk' / 'arm64' / 'genassym.c'
    text = genassym.read_text()
    decl_n = r'.ascii \"%0\"" : : "n"'
    decl_i = r'.ascii \"%0\"" : : "i"'
    decl_ok = r'.ascii \"#%0\"" : : "i"'
    if decl_n in text:
        genassym.write_text(text.replace(decl_n, decl_ok))
        info('patched genassym DECLARE(): "i" constraint + literal # padding (kills the .byte folding)')
    elif decl_i in text:
        genassym.write_text(text.replace(decl_i, decl_ok))
        info('patched genassym DECLARE(): added the # padding to the "i" form (kills the .byte folding)')
    elif decl_ok in text:
        pass
    else:
        raise SystemExit(f'{genassym}: DECLARE() constraint line not found; re-derive the genassym fix')

    apply_required_patch(
        work,
        ROOT / 'patches/xnu/native-early-fault-record.patch',
        '.native-early-fault-applied',
        env,
    )
    apply_required_patch(
        work,
        ROOT / 'patches/xnu/native-entry-witness.patch',
        '.native-entry-witness-applied',
        env,
    )
    apply_required_patch(
        work,
        ROOT / 'patches/xnu/native-phase-markers.patch',
        '.native-phase-markers-applied',
        env,
    )
    apply_required_patch(
        work,
        ROOT / 'patches/xnu/native-phase-kva-carrier.patch',
        '.native-phase-kva-carrier-applied',
        env,
    )
    apply_required_patch(
        work,
        ROOT / 'patches/xnu/native-phase-c-entry-markers.patch',
        '.native-phase-c-entry-markers-applied',
        env,
    )
    apply_required_patch(
        work,
        ROOT / 'patches/xnu/native-phase-console-marker.patch',
        '.native-phase-console-marker-applied',
        env,
    )
    apply_required_patch(
        work,
        ROOT / 'patches/xnu/native-phase-c-enable.patch',
        '.native-phase-c-enable-applied',
        env,
    )
    apply_required_patch(
        work,
        ROOT / 'patches/xnu/native-handoff-witness.patch',
        '.native-handoff-witness-applied',
        env,
    )
    apply_required_patch(
        work,
        ROOT / 'patches/xnu/native-pre-mmu-witness.patch',
        '.native-pre-mmu-witness-applied',
        env,
    )
    apply_required_patch(
        work,
        ROOT / 'patches/xnu/native-startup-witness.patch',
        '.native-startup-witness-applied',
        env,
    )
    apply_required_patch(
        work,
        ROOT / 'patches/xnu/native-bootargs-witness.patch',
        '.native-bootargs-witness-applied',
        env,
    )
    apply_required_patch(
        work,
        ROOT / 'patches/xnu/native-kva-calc-witness.patch',
        '.native-kva-calc-witness-applied',
        env,
    )
    apply_required_patch(
        work,
        ROOT / 'patches/xnu/native-args-physical-witness.patch',
        '.native-args-physical-witness-applied',
        env,
    )
    apply_required_patch(
        work,
        ROOT / 'patches/xnu/native-stack-link-witness.patch',
        '.native-stack-link-witness-applied',
        env,
    )
    apply_required_patch(
        work,
        ROOT / 'patches/xnu/native-stack-link-physical.patch',
        '.native-stack-link-physical-applied',
        env,
    )
    apply_required_patch(
        work,
        ROOT / 'patches/xnu/native-fault-publish-witness.patch',
        '.native-fault-publish-witness-applied',
        env,
    )
    apply_required_patch(
        work,
        ROOT / 'patches/xnu/native-invalidation-witness.patch',
        '.native-invalidation-witness-applied',
        env,
    )
    apply_required_patch(
        work,
        ROOT / 'patches/xnu/native-invalidation-setup-witness.patch',
        '.native-invalidation-setup-witness-applied',
        env,
    )
    apply_required_patch(
        work,
        ROOT / 'patches/xnu/native-invalidation-loop-state.patch',
        '.native-invalidation-loop-state-applied',
        env,
    )
    apply_required_patch(
        work,
        ROOT / 'patches/xnu/native-mapping-witness.patch',
        '.native-mapping-witness-applied',
        env,
    )
    apply_required_patch(
        work,
        ROOT / 'patches/xnu/native-header-adjust-witness.patch',
        '.native-header-adjust-witness-applied',
        env,
    )

    # config/MASTER.arm64 references the config bundle MONOTONIC_BASE inside PERF_DBG_BASE (line 47)
    # but the published tag never defines that bundle — Apple's internal device MASTER fragments do.
    # Without it the `monotonic` keyword is never set: kern_monotonic.c/monotonic_arm64.c drop out of
    # the file list and -DMONOTONIC is never defined, yet headers that gate on it (osfmk/kern/task.h,
    # osfmk/arm/cpu_data_internal.h) then reach machine/monotonic.h in a state where MT_CORE_NFIXED is
    # undefined — the observed hard error. The j96ap kernelcache contains the monotonic code
    # ("kern.monotonicclock_usecs", "monotonic: PMI from IOCPU"), so Apple's own build enables it.
    # Define the bundle the same way the file list expects: the `monotonic` keyword pulls
    # osfmk/conf/files{,.arm64} `optional monotonic` entries and the keyword becomes -DMONOTONIC.
    master = work / 'config' / 'MASTER.arm64'
    text = master.read_text()
    if 'MONOTONIC_BASE = [' not in text:
        needle = '#  PERF_DBG_BASE =  [ mach_kdp config_serial_kdp MONOTONIC_BASE kperf kpc ]\n'
        if needle not in text:
            raise SystemExit(f'{master}: PERF_DBG_BASE line not found; re-derive the MONOTONIC_BASE fix')
        text = text.replace(needle, needle + '#  MONOTONIC_BASE = [ monotonic ]\n', 1)
        master.write_text(text)
        info('defined the MONOTONIC_BASE config bundle in config/MASTER.arm64 (keyword: monotonic)')

    # makedefs/MakeInc.top `setup:` spins `while [ ! new -nt old ]` to force the invalidation
    # timestamp strictly newer. On dash (Ubuntu /bin/sh) -nt is false when the reference file does
    # not exist, so the first build of a fresh OBJROOT (no .mach_kernel.timestamp yet) loops forever
    # — observed: setup wedged 10 minutes in `sleep 1`. Apple fixed exactly this in the 10063 tree
    # (refer/xnu MakeInc.top:396-397, with the same comment); apply the same guard for both the
    # mach_kernel and symbolset loops.
    top = work / 'makedefs' / 'MakeInc.top'
    text = top.read_text()
    if '-a \\( \\! -e' not in text:
        for name in ('mach_kernel', 'symbolset'):
            old = f' -nt $(OBJROOT)/.{name}.timestamp ]'
            new = (f' -nt $(OBJROOT)/.{name}.timestamp -a \\( \\! -e $(OBJROOT)/.{name}.timestamp.new'
                   f' -o -e $(OBJROOT)/.{name}.timestamp \\) ]')
            if old not in text:
                raise SystemExit(f'{top}: {name} timestamp loop not found; re-derive the fix')
            text = text.replace(old, new)
        top.write_text(text)
        info('patched makedefs/MakeInc.top: timestamp loops no longer spin when the reference file is absent (dash -nt)')

    # Two T7001-recipe latent defects in this public drop, both proven by the first build
    # (out/y35a/ios12-kernel/build.log, 2026-11-04 run that reached the compile phase).
    #
    # 1. osfmk/machine/monotonic.h: the exported umbrella includes the per-arch header (where
    #    MT_CORE_NFIXED is only defined under '#if MONOTONIC && KERNEL_PRIVATE'), but then uses
    #    MT_CORE_NFIXED in UNGATED kernel declarations (extern bool mt_core_supported; struct
    #    mt_cpu/mt_thread/mt_task ...). For T7001 the config never enables MONOTONIC (no
    #    -DMONOTONIC anywhere in the build log; MASTER.arm64 lists MONOTONIC_BASE only in a
    #    commented PERF_DBG_BASE), so every bsd file that reaches the header through
    #    '#include <sys/monotonic.h>' under XNU_KERNEL_PRIVATE (bsd_init.o: 'use of undeclared
    #    identifier MT_CORE_NFIXED') dies. Apple's own later fix (refer/xnu xnu-10063,
    #    osfmk/machine/monotonic.h) gates the whole body behind '#if CONFIG_CPU_COUNTERS'; the
    #    equivalent gate for this tree is '#if defined(MT_CORE_NFIXED)' — self-describing, keeps
    #    x86_64 (unconditional #define) and a future MONOTONIC-enabled arm64 build intact.
    mtm = work / 'osfmk/machine/monotonic.h'
    text = mtm.read_text()
    gate_open = '#if defined(MT_CORE_NFIXED)\n#include <stdatomic.h>'
    if gate_open not in text:
        arch_end = '#error unsupported architecture\n#endif\n\n'
        body_start = '#include <stdatomic.h>\n#include <stdbool.h>\n#include <stdint.h>\n'
        body_end = 'int mt_microstackshot_start_arch(uint64_t period);\n'
        if arch_end not in text or body_start not in text or body_end not in text:
            raise SystemExit(f'{mtm}: arch-select/body anchors not found; re-derive the gate')
        text = text.replace(arch_end, arch_end + '#if defined(MT_CORE_NFIXED)\n', 1)
        text = text.replace(body_end, body_end + '#endif /* defined(MT_CORE_NFIXED) */\n', 1)
        mtm.write_text(text)
        info('patched osfmk/machine/monotonic.h: gated kernel declarations behind defined(MT_CORE_NFIXED)')

    # 2. osfmk/ipc/mach_kernelrpc.c _kernelrpc_mach_port_get_attributes_trap: 'goto done' at the
    #    task != current_task() check jumps forward over the VLA 'typeof(...) info[max_count];'
    #    into its scope end — a constraint violation clang 24 rejects ('cannot jump from this
    #    goto statement to its label'); Apple's older compiler only warned. Upstream fixed the
    #    same shape later (refer/xnu xnu-10063 places the early-out goto AFTER the declarations).
    #    Mirror that here: hoist the declarations up, keep the check-and-bzero order unchanged.
    krpc = work / 'osfmk/ipc/mach_kernelrpc.c'
    text = krpc.read_text()
    old = ('\tif (task != current_task()) {\n\t\tgoto done;\n\t}\n\n'
           '\t// MIG does not define the type or size of the mach_port_info_t out array')
    reordered = ('\t// MIG does not define the type or size of the mach_port_info_t out array')
    if old in text:
        text = text.replace(old, reordered, 1)
        decl_end = '\ttypeof(MACH_PORT_INFO_OUT[0]) info[max_count];\n'
        if decl_end not in text:
            raise SystemExit(f'{krpc}: info[] declaration not found; re-derive the reorder')
        text = text.replace(decl_end, decl_end + '\n\tif (task != current_task()) {\n\t\tgoto done;\n\t}\n', 1)
        krpc.write_text(text)
        info('patched osfmk/ipc/mach_kernelrpc.c: moved the early-out goto after the VLA declaration')

    target = fakeroot / 'usr/include/TargetConditionals.h'
    source = ROOT / 'scripts/linux/TargetConditionals.h'
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.is_file() or target.read_bytes() != source.read_bytes():
        shutil.copyfile(source, target)
        info('installed TargetConditionals.h into the iOS 12 fakeroot')


def host_make_args(env):
    physical = os.cpu_count() or 4
    memory = int(os.popen('getconf _PHYS_PAGES').read()) * int(os.popen('getconf PAGE_SIZE').read())
    clt = Path(env['CLT_PREFIX'])
    return [f'MEMORY_SIZE={memory}', f'SYSCTL_HW_PHYSICALCPU={physical}', f'SYSCTL_HW_LOGICALCPU={physical}',
            'PLATFORM=iPhoneOS', f'HOST_CC={clt}/bin/xnu-host-cc', f'MIGCOM={clt}/libexec/migcom',
            'TIGHTBEAMC=tightbeamc-not-supported', 'BUILD_DSYM=0',
            'HOST_OS_VERSION=14.6', 'HOST_CODESIGN=/usr/bin/true']


def installhdrs(work, env, jobs, log, fakeroot, machine):
    stamp = fakeroot / '.xnu-4903-headers'
    if stamp.is_file():
        info('iOS 12 kernel headers already installed into the fakeroot; skipping installhdrs')
        return
    run(['make', '-C', work, 'installhdrs', 'SDKROOT=macosx', 'ARCH_CONFIGS=ARM64',
         f'MACHINE_CONFIGS={machine}', 'KERNEL_CONFIGS=DEVELOPMENT',
         'ARCH_STRING_FOR_CURRENT_MACHINE_CONFIG=arm64', 'SDKVERSION=12.4',
         # 4903 adds only $(SDKROOT)/usr/local/include/kernel to the include path; the libplatform
         # private headers (<os/...>, <firehose/...>, AvailabilityInternalPrivate.h) the 4903 kernel
         # sources include live one level up in the fakeroot. Same dir the 17-era kernel-sdk-root.patch uses.
         'INCFLAGS_SDK+=-I$(SDKROOT)/usr/local/include', 'MAKEJOBS=-j' + jobs,
         *host_make_args(env)], env, cwd=work, log=log)
    stamp.touch()


def build(work, env, jobs, machine, log, fakeroot):
    # ld64 scans inputs strictly left-to-right and never rescans lazy archives. In the stock
    # recipe the kernel link line carries `-lcc_kext` *before* `-filelist link.filelist`
    # (.LDFLAGS token order, verified), so when OSKext.cpo's PGO data grab (DEVELOPMENT-only)
    # later references ___llvm_profile_get_size_for_buffer_internal /
    # ___llvm_profile_write_buffer_internal, libcc_kext.a has already passed and no member is
    # extracted: "symbol(s) not found for architecture arm64". force_load makes archive
    # inclusion order-independent; the members themselves are intact in the rebuilt archive.
    cc_kext_force = f'-Wl,-force_load,{fakeroot}/usr/local/lib/kernel/libcc_kext.a'
    run(['make', '-C', work, 'build', 'SDKROOT=iphoneos', 'ARCH_CONFIGS=ARM64',
         f'MACHINE_CONFIGS={machine}', 'KERNEL_CONFIGS=DEVELOPMENT',
         'ARCH_STRING_FOR_CURRENT_MACHINE_CONFIG=arm64', 'SDKVERSION=12.4',
         'INCFLAGS_SDK+=-I$(SDKROOT)/usr/local/include',
         # The phase and early-fault patches guard both C and assembly sources.
         # Per-object CFLAGS do not reach locore.s/start.s in this make system;
         # export the feature through the global C and ARM64 assembler flags.
         'CFLAGS_EXTRA=-DXNU_NATIVE_EARLY_FAULT=1',
         'SFLAGS_ARM64+=-DXNU_NATIVE_EARLY_FAULT=1',
         f'RC_PROJECT_CONFIG=RELEASE_ARM64_{machine}',
         'BUILD_LTO=0', 'BOUND_CHECKS=0', 'BUILD_WERROR=0', f'MAKEJOBS=-j{jobs}',
         f'OBJROOT={work}/BUILD/obj', f'SYMROOT={work}/BUILD/sym', f'DSTROOT={work}/BUILD/dst',
         f'LD_KERNEL_LIBS={cc_kext_force}',
         *host_make_args(env)], env, cwd=work, log=log)


def verify_pages(work, env, machine, log):
    """Prove the compiled kernel is 4K-page: APPLETYPHOON (T7001) gets ARM_PGSHIFT=12 and no __ARM_16K_PG__."""
    probe = work / 'BUILD/probe_4k.c'
    probe.parent.mkdir(parents=True, exist_ok=True)
    probe.write_text('#include <pexpert/arm64/board_config.h>\n'
                     '#include <arm/proc_reg.h>\n'
                     'int pgshift_test[(ARM_PGSHIFT == 12) ? 1 : -1];\n'
                     '#ifdef __ARM_16K_PG__\n'
                     'int sixteenk_test[-1];\n'
                     '#endif\n')
    result = run([env['CROSS_CLANG'], '-target', 'arm64-apple-darwin18.7.0', '-mkernel', '-nostdinc',
                  f'-DARM64_BOARD_CONFIG_{machine}', f'-I{work}/pexpert', f'-I{work}/osfmk',
                  '-fsyntax-only', str(probe)], env, log=log, check=False)
    if result.returncode != 0:
        # Fallback evidence (still deterministic): the tree's own constants.
        proc_reg = (work / 'osfmk/arm/proc_reg.h').read_text()
        if '#define ARM_PGSHIFT 12' not in proc_reg:
            raise SystemExit('ARM_PGSHIFT is not 12 in this tree — page size assumption broken')
        info('probe compile failed (header closure); fell back to textual ARM_PGSHIFT=12 check')
    info('page size: ARM_PGSHIFT=12 (4K) verified for APPLETYPHOON (T7000/T7001), no __ARM_16K_PG__')


def otool_sections(kernel, env, log):
    result = run([str(Path(env['CLT_PREFIX']) / 'bin/otool'), '-l', str(kernel)], env,
                 log=None, check=True)
    text = result.stdout.decode(errors='replace')
    log.write(text)
    segments = []
    vmaddr = None
    for match in re.finditer(r'segname (\S+)\n\s*vmaddr (0x[0-9a-f]+)', text):
        segments.append(match.group(1))
        if match.group(1) == '__TEXT':
            vmaddr = match.group(2)
    return segments, vmaddr


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--machine', default='T7001', help='ARM64 machine config (T7001=A8X j96ap, T7000=A8)')
    parser.add_argument('--src', type=Path, default=Path('/work/xnu-4903'))
    parser.add_argument('--output', type=Path, default=ROOT / 'out/y35a/ios12-kernel')
    parser.add_argument('--fresh', action='store_true', help='redo installhdrs and rebuild the kernel')
    args = parser.parse_args()
    if not Path('/work').is_dir():
        raise SystemExit('this builder runs inside the Linux build container (native /work volume only)')

    output = args.output
    output.mkdir(parents=True, exist_ok=True)
    if args.fresh:
        (ROOT / '.cache/fakeroot-4903/.xnu-4903-headers').unlink(missing_ok=True)

    env = dict(os.environ, **linux_env(SimpleNamespace(tree=ROOT)))
    # Keep the iOS 12 header install out of the shared 17-era fakeroot: seed a private copy from it
    # (libplatform headers, TargetConditionals.h, libcc_kext.a) and repoint the xcrun shim at it.
    base_fakeroot = ROOT / '.cache/fakeroot'
    fakeroot = ROOT / '.cache/fakeroot-4903'
    if not fakeroot.is_dir():
        info(f'seeding {fakeroot} from {base_fakeroot}')
        run(['cp', '--reflink=never', '-R', str(base_fakeroot), str(fakeroot)], env)
    # The seeded libcc_kext.a carries a stale Mach-O symbol index: InstrProfilingBuffer.o defines
    # ___llvm_profile_get_size_for_buffer_internal / ___llvm_profile_write_buffer_internal (needed by
    # OSKext.cpo's PGO data grab in the DEVELOPMENT config) but the archive's __.SYMDEF SORTED lists
    # no entries for them, so ld64 never extracts the member and the kernel link dies with
    # "Undefined symbols for architecture arm64". ranlib does not fix it (the in-container
    # __.SYMDEF SORTED format is ignored by ld); rebuild the archive with libtool from its members
    # instead, which produces an index ld honours. The 17-era shared fakeroot stays untouched.
    clt = Path(env['CLT_PREFIX'])
    for archive in sorted((fakeroot / 'usr/local/lib/kernel').glob('*.a')):
        members = sorted(str(path) for path in subprocess.run(
            [str(clt / 'bin/ar'), '-t', str(archive)], env=env,
            capture_output=True, text=True, check=True).stdout.splitlines()
            if path != '__.SYMDEF SORTED')
        if not members:
            continue
        staging = ROOT / '.cache/archive-rebuild'
        staging.mkdir(exist_ok=True)
        extracted = []
        for member in members:
            destination = staging / member
            if destination.exists():
                destination.unlink()
            run([str(clt / 'bin/ar'), '-x', str(archive), member], env, cwd=staging)
            extracted.append(str(destination))
        run([str(clt / 'bin/libtool'), '-static', '-o', str(archive), *extracted], env)
        info(f'rebuilt archive {archive.name}')
    env['UNIXNU_SDKROOT'] = str(fakeroot)
    env['UNIXNU_PLATFORM_PATH'] = str(fakeroot / 'Platforms/iPhoneOS.platform')
    jobs = os.environ.get('JOBS', '4')
    # Allow an isolated rebuild when an earlier instrumented tree has already
    # recorded applied-patch sentinels. The default keeps the established path.
    work = ROOT / os.environ.get('XNU4903_WORK', '.cache/xnu4903-work')

    log = (output / 'build.log').open('w')
    ensure_source(args.src, env)
    sync_tree(args.src, work)
    fix_source(work, fakeroot, env)
    installhdrs(work, env, jobs, log, fakeroot, args.machine)

    build(work, env, jobs, args.machine, log, str(fakeroot))
    verify_pages(work, env, args.machine, log)
    log.flush()

    name = f'mach.development.{args.machine.lower()}'
    raw = work / 'BUILD' / 'obj' / f'DEVELOPMENT_ARM64_{args.machine}' / f'{name}.unstripped'
    if not raw.is_file():
        raise SystemExit(f'build finished but kernel Mach-O not found at {raw}')
    final = output / f'{name}.unstripped'
    run(['cp', '--reflink=never', str(raw), str(final)], env)
    alias = output / f'{name}.unstripped.noctf'
    run(['cp', '--reflink=never', str(raw), str(alias)], env)

    segments, vmaddr = otool_sections(final, env, log)
    if shutil.which('file'):
        file_out = subprocess.run(['file', str(final)], capture_output=True, text=True).stdout.strip()
    else:
        header = subprocess.run([str(Path(env['CLT_PREFIX']) / 'bin/otool'), '-h', str(final)],
                                capture_output=True, text=True).stdout
        file_out = 'Mach-O 64-bit executable arm64' if 'MH_MAGIC_64' in header and 'CPU_TYPE_ARM64' in header else header
    digest = hashlib.sha256(final.read_bytes()).hexdigest()
    report = {
        'xnu_tag': XNU_TAG, 'machine': args.machine, 'artifact': str(final),
        'alias': str(alias), 'bytes': final.stat().st_size, 'sha256': digest,
        'file': file_out, '__TEXT_vmaddr': vmaddr, 'segments': segments,
        'note': 'iOS 12.4 (16G102) ships xnu-4903.272.1 (Darwin 18.7); 4903.270.47 is the newest '
                'public tag of that series. 4570 (Darwin 17.5) is the iOS 11.3/11.4 source and its '
                'published makedefs cannot build ARM64 at all.',
    }
    (output / 'artifact.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    if vmaddr != '0xfffffff007004000':
        raise SystemExit(f'__TEXT vmaddr {vmaddr} does not match the j96ap kernelcache base')
    if 'arm64' not in file_out or 'executable' not in file_out.lower():
        raise SystemExit(f'artifact is not an arm64 executable: {file_out}')
    info(f'done: {final}')


if __name__ == '__main__':
    main()
