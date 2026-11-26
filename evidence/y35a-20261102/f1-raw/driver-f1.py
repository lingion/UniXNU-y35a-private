#!/usr/bin/env python3
"""F1 experiment driver: ground-truth compile of vanilla XNU-4570 in the Linux container.

Stages (each tree copy under /work/f1/, full logs under /work/out-f1/raw/):
  A0  pristine 4570 tree + 4903-style make args, installhdrs, NO makedefs port.
      Expected: makedefs/MakeInc.kernel:14 "Unsupported CURRENT_ARCH_CONFIG ARM64".
  A1  makedefs ARM64 recipe ported from the proven xnu-4903.270.47 makedefs +
      fix_source anchors; installhdrs T7001.
  B   A1 tree, `make build -k` MACHINE_CONFIGS=T7001 KERNEL_CONFIGS=DEVELOPMENT
      (keep-going, capped) -> full vanilla-Typhoon error inventory.
  C   fresh copy + port + patches/xnu4570/0001-y35a-board.patch + MSM8916
      machine-table entry; `make build -k` -> Y35A error inventory.

Runs inside container unixnu-y35a-native-20261103 (native /work volume only).
"""
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

PROJ = Path('/work/UniXNU-y35a')
sys.path.insert(0, str(PROJ / 'scripts'))
from unixnu.kernel import linux_env  # noqa: E402

SRC4570 = Path('/work/xnu-4570')
F1 = Path('/work/f1')
RAW = Path('/work/out-f1/raw')
RAW.mkdir(parents=True, exist_ok=True)
FAKEROOT_BASE = PROJ / '.cache/fakeroot'
FAKEROOT = PROJ / '.cache/fakeroot-4570'
PATCH0001 = Path('/work/out-f1/0001-y35a-board.patch')

TIMEOUT_INSTALL = 1200
TIMEOUT_BUILD = 3300
JOBS = os.environ.get('JOBS', '4')

env = None


def info(msg):
    print(f'[f1] {msg}', flush=True)


def sh(cmd, cwd=None, timeout=None, use_env=True):
    """Run via bash; GNU timeout kills the whole process group on expiry."""
    if timeout:
        cmd = f'timeout -k 15 {timeout} bash -c {shlex.quote(cmd)}'
    full = ['bash', '-c', cmd]
    t0 = time.time()
    try:
        r = subprocess.run(full, cwd=str(cwd) if cwd else None,
                           env=(env if use_env else dict(os.environ)),
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        out = r.stdout.decode('utf-8', 'replace')
        rc = r.returncode
        if rc == 124:
            out += f'\n[f1] TIMEOUT after {timeout}s (process group killed; log truncated here)\n'
        return rc, out, round(time.time() - t0, 1)
    except Exception as e:  # noqa: BLE001
        return 999, f'[f1] harness exception: {e}\n', round(time.time() - t0, 1)


def copy_tree(src, dst):
    if dst.exists():
        shutil.rmtree(dst)
    subprocess.run(['cp', '-R', '--reflink=never', str(src), str(dst)], check=True)
    g = dst / '.git'
    if g.exists():
        shutil.rmtree(g)


# ---------------------------------------------------------------- makedefs port
def apply_line(lines, idx, addition):
    """Append `addition` (list of lines) after lines[idx]."""
    return lines[:idx + 1] + addition + lines[idx + 1:]


def port_makedefs(tree):
    """Port the ARM64 build recipe from xnu-4903.270.47 into 4570's makedefs.

    Line-anchored (whitespace-tolerant): each edit finds a unique line by a
    plain prefix; failures are recorded, not guessed.
    """
    results = []
    defpath = tree / 'makedefs' / 'MakeInc.def'
    cmdpath = tree / 'makedefs' / 'MakeInc.cmd'
    lines = defpath.read_text().splitlines(keepends=True)

    def find_unique(prefix):
        hits = [i for i, l in enumerate(lines) if l.startswith(prefix)]
        return hits[0] if len(hits) == 1 else None

    def edit(name, prefix, replace=None, add=None, before=False):
        i = find_unique(prefix)
        if i is None:
            results.append({'edit': name, 'applied': False, 'why': f'anchor {prefix!r} not unique/found'})
            return
        if replace is not None:
            lines[i] = replace
        if add is not None:
            if before:
                lines[:] = lines[:i] + add + lines[i:]
            else:
                lines[:] = apply_line(lines, i, add)
        results.append({'edit': name, 'applied': True})

    edit('SUPPORTED_ARCH_CONFIGS+ARM64', 'SUPPORTED_ARCH_CONFIGS :=',
         replace='SUPPORTED_ARCH_CONFIGS := X86_64 X86_64H ARM64\n')

    edit('SUPPORTED_ARM64_MACHINE_CONFIGS+MACHINE_FLAGS', 'SUPPORTED_X86_64H_MACHINE_CONFIGS =',
         add=['SUPPORTED_ARM64_MACHINE_CONFIGS = MSM8916 S5L8960X T7000 T7001 S8000 S8001 T8010 T8011\n',
              '# MACHINE_FLAGS ported from xnu-4903.270.47 makedefs/MakeInc.def lines 53-63;\n'
              '# T8010/T8011 -mcpu=hurricane dropped: Apple-clang-specific tuning knob.\n',
              'MACHINE_FLAGS_ARM64_MSM8916 = -DARM64_BOARD_CONFIG_MSM8916\n',
              'MACHINE_FLAGS_ARM64_S5L8960X = -DARM64_BOARD_CONFIG_S5L8960X\n',
              'MACHINE_FLAGS_ARM64_T7000 = -DARM64_BOARD_CONFIG_T7000\n',
              'MACHINE_FLAGS_ARM64_T7001 = -DARM64_BOARD_CONFIG_T7001\n',
              'MACHINE_FLAGS_ARM64_S8000 = -DARM64_BOARD_CONFIG_S8000\n',
              'MACHINE_FLAGS_ARM64_S8001 = -DARM64_BOARD_CONFIG_S8001\n',
              'MACHINE_FLAGS_ARM64_T8010 = -DARM64_BOARD_CONFIG_T8010\n',
              'MACHINE_FLAGS_ARM64_T8011 = -DARM64_BOARD_CONFIG_T8011\n'])

    edit('ARCH_FLAGS_ARM64', 'ARCH_FLAGS_X86_64H',
         add=['ARCH_FLAGS_ARM64\t  = -arch $(ARCH_STRING_FOR_CURRENT_MACHINE_CONFIG)\n'])

    edit('CFLAGS_ARM64+per-config', 'CFLAGS_X86_64H =',
         add=['CFLAGS_ARM64\t= -Darm64 -DARM64 -D__ARM64__ -DLP64 -DPAGE_SIZE_FIXED \\\n',
              '\t\t\t\t-fno-strict-aliasing -D__API__=v4 -mkernel\n',
              'CFLAGS_RELEASEARM64 = -O2\n',
              'CFLAGS_DEVELOPMENTARM64 = -O2\n',
              'CFLAGS_KASANARM64 = $(CFLAGS_DEVELOPMENTARM64)\n',
              'CFLAGS_DEBUGARM64 = -O0\n',
              'CFLAGS_PROFILEARM64 = -O2\n'])

    edit('SFLAGS_ARM64', 'SFLAGS_X86_64H',
         add=['SFLAGS_ARM64\t= $(CFLAGS_ARM64)\n'])

    edit('KASAN_SHIFT_ARM64', 'KASAN_SHIFT_X86_64H=',
         add=['KASAN_SHIFT_ARM64=0xdffffff800000000\n'])

    edit('CXXFLAGS gnu++11->1z', 'CXXFLAGS_GEN  =',
         replace='CXXFLAGS_GEN  = -std=gnu++1z -fapple-kext $(OTHER_CXXFLAGS)\n')

    edit('LDFLAGS_KERNEL_SDK drop -lfirehose', 'LDFLAGS_KERNEL_SDK',
         replace='LDFLAGS_KERNEL_SDK\t= -L$(SDKROOT)/usr/local/lib/kernel\n')

    edit('LDFLAGS_KERNEL_GENARM64 recipe', 'LDFLAGS_KERNEL\t=', before=True,
         add=['# --- ARM64 kernel link recipe ported from xnu-4903.270.47 LDFLAGS_KERNEL_GENARM64;\n'
              '#     j96ap layout: __PRELINK_TEXT at 0xfffffff004004000, kernel at 0xfffffff007004000.\n'
              '#     sectcreate lines omitted: 4570 keeps them in LDFLAGS_KERNEL_GEN (arch-neutral).\n'
              'LDFLAGS_KERNEL_GENARM64 = \\\n',
              '\t-Wl,-pie \\\n',
              '\t-Wl,-static \\\n',
              '\t-Wl,-segaddr,__PRELINK_TEXT,0xfffffff004004000 \\\n',
              '\t-Wl,-image_base,0xfffffff007004000 \\\n',
              '\t-Wl,-sectalign,__DATA,__const,0x4000 \\\n',
              '\t-Wl,-rename_section,__DATA,__mod_init_func,__DATA_CONST,__mod_init_func \\\n',
              '\t-Wl,-rename_section,__DATA,__mod_term_func,__DATA_CONST,__mod_term_func \\\n',
              '\t-Wl,-rename_section,__DATA,__const,__DATA_CONST,__const \\\n',
              '\t-Wl,-rename_section,__TEXT,__text,__TEXT_EXEC,__text \\\n',
              '\t-Wl,-rename_section,__TEXT,__stubs,__TEXT_EXEC,__stubs \\\n',
              '\t-Wl,-rename_section,__TEXT,initcode,__TEXT_EXEC,initcode\n',
              'LDFLAGS_KERNEL_SEGARM64 ?= \\\n',
              '\t-Wl,-segment_order,__TEXT:__DATA_CONST:__LINKEDIT:__TEXT_EXEC:__LAST:__KLD:__DATA:__BOOTDATA\n',
              'LDFLAGS_KERNEL_RELEASEARM64 = $(LDFLAGS_KERNEL_GENARM64) $(LDFLAGS_KERNEL_SEGARM64)\n',
              'LDFLAGS_KERNEL_DEVELOPMENTARM64 = $(LDFLAGS_KERNEL_GENARM64) $(LDFLAGS_KERNEL_SEGARM64) $(LDFLAGS_NOSTRIP_FLAG)\n',
              'LDFLAGS_KERNEL_KASANARM64 = $(LDFLAGS_KERNEL_DEVELOPMENTARM64)\n',
              'LDFLAGS_KERNEL_DEBUGARM64 = $(LDFLAGS_KERNEL_DEVELOPMENTARM64)\n',
              'LDFLAGS_KERNEL_PROFILEARM64 = $(LDFLAGS_KERNEL_DEVELOPMENTARM64)\n'])

    edit('LD_KERNEL_LIBS add firehose', 'LD_KERNEL_LIBS',
         replace='LD_KERNEL_LIBS\t= -lcc_kext -lfirehose_kernel\n')

    defpath.write_text(''.join(lines))

    # MakeInc.cmd: macosx.internal default is unusable on the open-source SDK path
    ctext = cmdpath.read_text()
    ok = 'SDKROOT ?= macosx.internal\n' in ctext
    if ok:
        ctext = ctext.replace('SDKROOT ?= macosx.internal\n', 'SDKROOT ?= macosx\n')
        cmdpath.write_text(ctext)
    results.append({'edit': 'SDKROOT default macosx.internal->macosx', 'applied': ok})

    return results


# ---------------------------------------------------------------- fix_source
SEEKFILE_OLD = ('    if (offset != lseek(fd, offset, SEEK_SET))\n'
                '        err = kErrorDiskFull;\n'
                '    else\n'
                '        err = kErrorNone;\n')
SEEKFILE_NEW = ('    if (offset != lseek(fd, offset, SEEK_SET)) {\n'
                '        struct stat st;\n'
                '        /* Linux lseek() returns 0 on character devices such as the\n'
                '         * /dev/null that check_all_exports writes to; not an error. */\n'
                '        if (0 == fstat(fd, &st) && S_ISCHR(st.st_mode))\n'
                '            return kErrorNone;\n'
                '        err = kErrorDiskFull;\n'
                '    } else\n'
                '        err = kErrorNone;\n')


def fix_source(tree):
    """fix_source() of build-xnu-4903-kernel.py, re-anchored onto 4570. Returns (applied, failed)."""
    applied, failed = [], []

    def note(name, ok, detail=''):
        (applied if ok else failed).append(name + (f' ({detail})' if detail and not ok else ''))

    p = tree / 'bsd/kern/makesyscalls.sh'
    t = p.read_text()
    if '\\(sy_call_t *\\)' in t:
        p.write_text(t.replace('\\(sy_call_t *\\)', '(sy_call_t *)'))
        note('makesyscalls backslash escapes', True)
    else:
        note('makesyscalls backslash escapes', False, 'no anchor')

    p = tree / 'SETUP/kextsymboltool/kextsymboltool.c'
    t = p.read_text()
    if 'S_ISCHR' not in t and SEEKFILE_OLD in t:
        t = t.replace(SEEKFILE_OLD, SEEKFILE_NEW)
        if '#include <sys/stat.h>' not in t:
            t = t.replace('#include <sys/types.h>', '#include <sys/types.h>\n#include <sys/stat.h>', 1)
        p.write_text(t)
        note('kextsymboltool lseek /dev/null', True)
    else:
        note('kextsymboltool lseek /dev/null', False, 'anchor differs')

    p = tree / 'SETUP/installfile/installfile.c'
    t = p.read_text()
    if 'O_SYMLINK' in t:
        p.write_text(t.replace('O_RDONLY | O_SYMLINK', 'O_RDONLY'))
        note('installfile O_SYMLINK', True)
    else:
        note('installfile O_SYMLINK', False, 'absent')

    p = tree / 'bsd/kern/makekdebugevents.py'
    if p.is_file() and p.read_text().startswith('#!/usr/bin/python'):
        import ast
        builder_src = (PROJ / 'scripts/build-xnu-4903-kernel.py').read_text()
        value = None
        for node in ast.walk(ast.parse(builder_src)):
            if isinstance(node, ast.Assign) and any(
                    isinstance(t, ast.Name) and t.id == '_KDEBUG_PY3' for t in node.targets):
                value = ast.literal_eval(node.value)
                break
        if value and value.startswith('#!/usr/bin/env python3'):
            p.write_text(value)
            p.chmod(0o755)
            note('makekdebugevents.py py3 rewrite', True)
        else:
            note('makekdebugevents.py py3 rewrite', False, 'template not found/malformed')
    else:
        note('makekdebugevents.py py3 rewrite', False, 'not python2 / absent')

    p = tree / 'bsd/sys/make_posix_availability.sh'
    t = p.read_text()
    if t.startswith('#! /bin/sh -') and 'function ' in t:
        first = t.splitlines(keepends=True)[0]
        p.write_text('#!/bin/bash\n' + t[len(first):])
        note('make_posix_availability shebang', True)
    else:
        note('make_posix_availability shebang', False, 'shape differs')

    p = tree / 'osfmk/arm64/genassym.c'
    t = p.read_text()
    # The proven working form in .cache/xnu4903-work is `.ascii \"#%0\"" : : "i"`
    # (literal # makes the string >=2 chars so clang never byte-folds it; the "i"
    # constraint matches Apple's own 10063 form). Accept either published starting
    # form ("n" or "i").
    ok_form = r'.ascii \"#%0\"" : : "i"'
    for src_form in (r'.ascii \"%0\"" : : "n"', r'.ascii \"%0\"" : : "i"'):
        if src_form in t:
            p.write_text(t.replace(src_form, ok_form))
            note('genassym DECLARE # padding + "i" (proven 4903 work form)', True)
            break
    else:
        if ok_form in t:
            note('genassym DECLARE # padding', True, 'already ok')
        else:
            note('genassym DECLARE # padding', False, 'form differs')

    p = tree / 'makedefs/MakeInc.top'
    t = p.read_text()
    if '-a \\( \\! -e' not in t:
        ok = True
        for name in ('mach_kernel', 'symbolset'):
            old = f' -nt $(OBJROOT)/.{name}.timestamp ]'
            new = (f' -nt $(OBJROOT)/.{name}.timestamp -a \\( \\! -e $(OBJROOT)/.{name}.timestamp.new'
                   f' -o -e $(OBJROOT)/.{name}.timestamp \\) ]')
            if old not in t:
                ok = False
                break
            t = t.replace(old, new)
        if ok:
            p.write_text(t)
            note('MakeInc.top dash -nt loops', True)
        else:
            note('MakeInc.top dash -nt loops', False, 'anchor differs')
    else:
        note('MakeInc.top dash -nt loops', False, 'already patched')

    p = tree / 'config/MASTER'
    t = p.read_text()
    if 'CONFIG_EMBEDDED' not in t:
        # xnu-4903.270.47 ships this line unconditionally (config/MASTER:313);
        # the 4570 published drop omits it entirely, yet its own bundle graphs
        # (MASTER.arm:19, MASTER.arm64 KERNEL_BASE) reference the keyword
        # <config_embedded>. Without the option line every embedded gate
        # (panic header shape, jetsam/freeze, dtrace-excludes, video_console
        # boot-args flags) resolves to the desktop side and the arm64 tree
        # does not compile.
        t += ('\n#\n# configurable kernel - general switch to say we are building for an\n'
              '# embedded device (ported from xnu-4903 config/MASTER:313; the 4570\n'
              '# published drop lost it while its keyword bundles still use it)\n#\n'
              'options   CONFIG_EMBEDDED\t\t\t# <config_embedded>\n')
        p.write_text(t)
        note('config/MASTER options CONFIG_EMBEDDED', True)
    else:
        note('config/MASTER options CONFIG_EMBEDDED', False, 'already present')

    p = tree / 'config/MASTER.arm64'
    t = p.read_text()
    if 'MONOTONIC_BASE = [' not in t:
        m = re.search(r'^#  PERF_DBG_BASE =.*MONOTONIC_BASE.*\n', t, re.M)
        if m:
            t = t[:m.end()] + '#  MONOTONIC_BASE = [ monotonic ]\n' + t[m.end():]
            p.write_text(t)
            note('MONOTONIC_BASE bundle', True)
        else:
            note('MONOTONIC_BASE bundle', False, 'no commented anchor')
    else:
        note('MONOTONIC_BASE bundle', False, 'already defined')

    p = tree / 'osfmk/machine/monotonic.h'
    if p.is_file():
        t = p.read_text()
        if '#if defined(MT_CORE_NFIXED)' not in t:
            m1 = re.search(r'^#error unsupported architecture\n#endif\n\n', t, re.M)
            m2 = re.search(r'^int mt_microstackshot_start_arch.*\n', t, re.M)
            if m1 and m2:
                t = (t[:m1.end()] + '#if defined(MT_CORE_NFIXED)\n' + t[m1.end():m2.end()]
                     + '#endif /* defined(MT_CORE_NFIXED) */\n' + t[m2.end():])
                p.write_text(t)
                note('monotonic.h MT_CORE_NFIXED gate', True)
            else:
                note('monotonic.h gate', False, 'anchors differ')
        else:
            note('monotonic.h gate', False, 'already gated')

    p = tree / 'osfmk/ipc/mach_kernelrpc.c'
    if p.is_file():
        t = p.read_text()
        old = ('\tif (task != current_task()) {\n\t\tgoto done;\n\t}\n\n'
               '\t// MIG does not define the type or size of the mach_port_info_t out array')
        if old in t:
            t = t.replace(old, '\t// MIG does not define the type or size of the mach_port_info_t out array', 1)
            decl_end = '\ttypeof(MACH_PORT_INFO_OUT[0]) info[max_count];\n'
            if decl_end in t:
                t = t.replace(decl_end, decl_end + '\n\tif (task != current_task()) {\n\t\tgoto done;\n\t}\n', 1)
                p.write_text(t)
                note('mach_kernelrpc goto/VLA reorder', True)
            else:
                note('mach_kernelrpc goto/VLA', False, 'decl anchor differs')
        else:
            note('mach_kernelrpc goto/VLA', False, 'site differs in 4570')

    if not (tree / 'osfmk/arm64/corecrypto/arm64_isa_compatibility.h').is_file():
        note('corecrypto isa header absent in 4570 (fix not needed)', True)

    return applied, failed


# ---------------------------------------------------------------- fakeroot
def seed_fakeroot():
    if not FAKEROOT.is_dir():
        info(f'seeding {FAKEROOT} from {FAKEROOT_BASE}')
        subprocess.run(['cp', '--reflink=never', '-R', str(FAKEROOT_BASE), str(FAKEROOT)], check=True)
    clt = Path(env['CLT_PREFIX'])
    for archive in sorted((FAKEROOT / 'usr/local/lib/kernel').glob('*.a')):
        stamp = archive.with_suffix(archive.suffix + '.rebuilt')
        if stamp.exists():
            continue
        mt = subprocess.run([str(clt / 'bin/ar'), '-t', str(archive)], env=env,
                            capture_output=True, text=True)
        if mt.returncode != 0:
            continue
        members = [m for m in mt.stdout.splitlines() if m != '__.SYMDEF SORTED']
        if not members:
            continue
        staging = PROJ / '.cache/archive-rebuild-4570'
        staging.mkdir(exist_ok=True)
        extracted = []
        for member in sorted(members):
            dest = staging / member
            if dest.exists():
                dest.unlink()
            subprocess.run([str(clt / 'bin/ar'), '-x', str(archive), member], env=env, cwd=str(staging))
            extracted.append(str(dest))
        subprocess.run([str(clt / 'bin/libtool'), '-static', '-o', str(archive), *extracted],
                       env=env, check=True)
        stamp.touch()
        info(f'rebuilt archive {archive.name}')


# ---------------------------------------------------------------- make
def make_env():
    e = dict(os.environ)
    e.update(linux_env(SimpleNamespace(tree=PROJ)))
    e['UNIXNU_SDKROOT'] = str(FAKEROOT)
    e['UNIXNU_PLATFORM_PATH'] = str(FAKEROOT / 'Platforms/iPhoneOS.platform')
    return e


def common_make_args(machine, sdkversion='11.4'):
    mem = int(os.popen('getconf _PHYS_PAGES').read()) * int(os.popen('getconf PAGE_SIZE').read())
    phys = os.cpu_count() or 4
    clt = Path(env['CLT_PREFIX'])
    return [
        f'MEMORY_SIZE={mem}', f'SYSCTL_HW_PHYSICALCPU={phys}', f'SYSCTL_HW_LOGICALCPU={phys}',
        'PLATFORM=iPhoneOS', f'HOST_CC={clt}/bin/xnu-host-cc', f'MIGCOM={clt}/libexec/migcom',
        'TIGHTBEAMC=tightbeamc-not-supported', 'BUILD_DSYM=0', 'HOST_OS_VERSION=14.6',
        'HOST_CODESIGN=/usr/bin/true',
        'ARCH_CONFIGS=ARM64', f'MACHINE_CONFIGS={machine}', 'KERNEL_CONFIGS=DEVELOPMENT',
        'ARCH_STRING_FOR_CURRENT_MACHINE_CONFIG=arm64', f'SDKVERSION={sdkversion}',
        'BUILD_STATIC_LINK=0',
    ]


def run_logged(inner_cmd, logname, cwd, timeout):
    """Run a command whose stdout is redirected to the log FILE by the shell
    (no python-side capture of 100MB logs), return (rc, summary, seconds)."""
    logpath = RAW / logname
    rc, out, secs = sh(f'{inner_cmd} > {shlex.quote(str(logpath))} 2>&1', cwd=cwd, timeout=timeout)
    # parse from disk; head+tail slice for gigantic logs keeps memory bounded
    try:
        size = logpath.stat().st_size
        with logpath.open('r', errors='replace') as fh:
            if size > 200_000_000:
                text = fh.read(100_000_000)
            else:
                text = fh.read()
    except OSError:
        text = out
    s = summarize(text)
    s.update({'rc': rc, 'seconds': secs, 'log_bytes': size})
    return s


def run_installhdrs(tree, machine, logname):
    args = common_make_args(machine) + ['SDKROOT=macosx',
                                       'INCFLAGS_SDK+=-I$(SDKROOT)/usr/local/include',
                                       f'MAKEJOBS=-j{JOBS}']
    cmd = 'make -C {t} installhdrs {a}'.format(t=tree, a=' '.join(shlex.quote(x) for x in args))
    return run_logged(cmd, logname, tree, TIMEOUT_INSTALL)


def purge_config_cache(tree):
    """Force the config stage to re-run: the generated keyword files and
    .CFLAGS/.LDFLAGS stamp caches under BUILD/obj were produced BEFORE the
    CONFIG_EMBEDDED/MASTER options fix, and make's timestamps consider them
    current (config/MASTER mtime predates them). Deleting them guarantees
    the flags are regenerated from the patched tree inside this run."""
    n = 0
    for p in tree.glob('BUILD/obj/*/.CFLAGS'):
        p.unlink(); n += 1
    for p in tree.glob('BUILD/obj/*/config.*'):
        if p.is_file():
            p.unlink(); n += 1
    info(f'purged {n} stale config/flag cache files in {tree}')


def run_build(tree, machine, logname, extra_flags=None):
    purge_config_cache(tree)
    args = common_make_args(machine) + [
        'SDKROOT=iphoneos',
        'INCFLAGS_SDK+=-I$(SDKROOT)/usr/local/include',
        f'RC_PROJECT_CONFIG=RELEASE_ARM64_{machine}',
        'BUILD_LTO=0', 'BOUND_CHECKS=0', 'BUILD_WERROR=0',
        f'OBJROOT={tree}/BUILD/obj', f'SYMROOT={tree}/BUILD/sym', f'DSTROOT={tree}/BUILD/dst',
        'LD_KERNEL_LIBS=' + f'-Wl,-force_load,{FAKEROOT}/usr/local/lib/kernel/libcc_kext.a -lfirehose_kernel',
        f'MAKEJOBS=-j{JOBS}',
    ]
    if extra_flags:
        args.append('OTHER_CFLAGS=' + extra_flags)
    cmd = 'make -C {t} build -k -Otarget {a}'.format(t=tree, a=' '.join(shlex.quote(x) for x in args))
    return run_logged(cmd, logname, tree, TIMEOUT_BUILD)


# ---------------------------------------------------------------- errors
CLANG_ERR = re.compile(r'(?m)^(?P<loc>[\w./+-]+\.[cms]?\w*):(?P<line>\d+):(?:\d+:)?\s*(?:fatal )?error:\s*(?P<msg>.+)$')
MAKE_ERR = re.compile(r'(?m)^(?:(?P<f>[\w./-]+:\d+): \*\*\* (?P<m1>.*)|make(?:\[\d+\])?: \*\*\* (?P<m2>.*))$')
LINK_ERR = re.compile(r'(?m)^(?:ld|clang): (?:ld|clang): (?P<msg>.*)$|^ld(?::| `)\s*(?P<msg2>Undefined symbols.*|symbol\(s\) not found.*)$')
BUILD_CFG = re.compile(r'(?m)^Building ... (\w+) \| (\w+) \| (\w+)$')
FIREHOSE = re.compile(r'--add-library\s?')


def summarize(log):
    errors, seen = [], set()
    for m in CLANG_ERR.finditer(log):
        f = m['loc']
        if not re.search(r'\.(c|cc|cpp|m|s|S)$', f):
            continue
        key = (f, int(m['line']), m['msg'][:100])
        if key in seen:
            continue
        seen.add(key)
        errors.append({'file': f, 'line': int(m['line']), 'message': m['msg'].strip()})
    for m in MAKE_ERR.finditer(log):
        t = (m['m1'] or m['m2'] or '').strip()
        if not t:
            continue
        loc = m['f'] or '(make)'
        key = (loc, 0, t[:140])
        if key in seen:
            continue
        seen.add(key)
        errors.append({'file': loc.split(':')[0] if m['f'] else '(make)',
                       'line': int(m['f'].split(':')[1]) if m['f'] else 0,
                       'message': t})
    for m in LINK_ERR.finditer(log):
        t = (m['msg'] or m['msg2'] or '').strip()
        if not t or 'warning' in t:
            continue
        key = ('(ld)', 0, t[:140])
        if key not in seen:
            seen.add(key)
            errors.append({'file': '(ld)', 'line': 0, 'message': t})
    # error-ish shell-level failures: "cmd: Error 1", "make: *** [target] Error 1"
    err1 = re.findall(r'(?m)^.*Error \d+$', log)
    cfg = BUILD_CFG.findall(log)
    return {
        'distinct_errors': errors,
        'error_lines_total': len(re.findall(r'(?m)(?:^| )error: ', log)),
        'error1_tail_lines': len(err1),
        'configs_attempted': sorted({(c[1], c[2]) for c in cfg}),
        'reached_compile': bool(re.search(r'(?m)^\s*Compiling .*\.c$|clang.* -c ', log)),
        'reached_assemble': bool(re.search(r'(?m)^\s*Assembling ', log)),
        'reached_link': bool(re.search(r'(?m)^\s*Linking .*mach_kernel| -filelist ', log)),
        'timed_out': '[f1] TIMEOUT' in log,
    }


def classify(e):
    msg = e['message'].lower()
    if 'unsupported current_arch_config' in msg or 'unsupported current_machine_config' in msg:
        return ('makedefs-port-needed',
                'port the 4903 ARM64 recipe into makedefs (done by this experiment)')
    if msg.startswith('#error') or ' #error ' in msg:
        return ('fixable-by-patch', 'source gate; see ios12-bringup-map rows/patch trailer list')
    if 'undefined symbol' in msg or 'undefined symbols' in msg:
        return ('fixable-by-patch', 'missing non-Apple branch body (idle path/cache ops class) -> patch 0002')
    if 'redefinition' in msg or 'already defined' in msg:
        return ('fixable-by-patch', 'assym/genassym artifact or header double-include')
    return ('needs-inspection', '')


def annotate(s):
    for e in s['distinct_errors']:
        cls, fix = classify(e)
        e['classification'] = cls
        if fix:
            e['minimal_fix'] = fix
    return s


def ported_tree(machine, name):
    """A1-style tree: pristine copy + makedefs port + fix_source + installhdrs,
    each step stamped so re-runs never clobber a tree another stage is building in."""
    t = F1 / name
    stamp_setup = t / '.f1-setup-done'
    stamp_hdrs = t / '.f1-installhdrs-ok'
    info(f'Stage {name}: makedefs port + fix_source, installhdrs {machine}')
    if not stamp_setup.exists():
        copy_tree(SRC4570, t)
        port = port_makedefs(t)
        ap, fa = fix_source(t)
        t_setup = {'port': port, 'fix': {'applied': ap, 'failed_or_na': fa}}
    else:
        t_setup = None
        info(f'{name}: setup already stamped, reusing tree')
    if stamp_hdrs.exists():
        info(f'{name}: installhdrs already stamped, skipping')
        return t, t_setup, {'note': 'reused stamped installhdrs', 'rc': 0}
    s = run_installhdrs(t, machine, f'{name}-installhdrs.log')
    if s['rc'] == 0:
        stamp_setup.touch()
        stamp_hdrs.touch()
    return t, t_setup, s


# ---------------------------------------------------------------- main
def main():
    global env
    env = make_env()
    only = sys.argv[1:] or ['A0', 'A1', 'B', 'C']
    slug = '-'.join(only).lower()
    rj = RAW / f'results-{slug}.json'
    results = json.loads(rj.read_text()) if rj.is_file() else {}
    results.update({'xnu_tag': 'xnu-4570.51.1', 'container': 'unixnu-y35a-native-20261103'})
    results.setdefault('stages', {})
    F1.mkdir(exist_ok=True)
    seed_fakeroot()

    if 'A0' in only:
        info('Stage A0: pristine 4570 installhdrs, no makedefs port')
        t = F1 / 'A0'
        copy_tree(SRC4570, t)
        results['stages']['A0'] = annotate(run_installhdrs(t, 'T7001', 'A0-installhdrs.log'))

    a1_tree = None
    if {'A1', 'B'} & set(only):
        a1_tree, setup, s = ported_tree('T7001', 'A1')
        if setup:
            results['A1_port'] = setup['port']
            results['A1_fix'] = setup['fix']
        if 'A1' in only:
            results['stages']['A1'] = annotate(s) if isinstance(s, dict) and 'distinct_errors' in s else s

    if 'B' in only:
        info('Stage B: -k build T7001 DEVELOPMENT (cap %ds)' % TIMEOUT_BUILD)
        results['stages']['B'] = annotate(run_build(a1_tree or F1 / 'A1', 'T7001', 'B-build-t7001.log'))

    if 'C' in only:
        info('Stage C: 0001 board patch + MSM8916 build -k')
        tc = F1 / 'C'
        stamp_setup = tc / '.f1-setup-done'
        stamp_patch = tc / '.f1-patch0001-ok'
        stamp_hdrs = tc / '.f1-installhdrs-ok'
        if not stamp_setup.exists():
            copy_tree(SRC4570, tc)
            results['C_port'] = port_makedefs(tc)
            ap, fa = fix_source(tc)
            results['C_fix'] = {'applied': ap, 'failed_or_na': fa}
        else:
            results['C_port'] = results['C_fix'] = 'reused stamped setup'
        prc = None
        if not stamp_patch.exists():
            prc, pout, _ = sh(f'patch -p1 --forward < {PATCH0001}', cwd=tc, timeout=120, use_env=False)
            results['C_patch0001'] = {'rc': prc, 'out': pout.strip()[:1500]}
            info(f'0001 patch rc={prc}')
            if prc == 0:
                stamp_patch.touch()
        else:
            results['C_patch0001'] = {'rc': 0, 'out': 'reused stamped patch'}
        if prc == 0 or stamp_patch.exists():
            stamp_setup.touch()
            # patch 0001 adds pexpert/pexpert/arm64/MSM8916.h but NOT to the
            # DATAFILES export list; the exported board_config.h then cannot
            # find it (every compile dies). Close the gap here (and feed back
            # into the patch file).
            mkp = tc / 'pexpert/pexpert/arm64/Makefile'
            t = mkp.read_text()
            if 'MSM8916.h' not in t:
                t = t.replace('\tS5L8960X.h \\\n', '\tS5L8960X.h \\\n\tMSM8916.h \\\n', 1)
                mkp.write_text(t)
                info('added MSM8916.h to pexpert arm64 DATAFILES')
            if not stamp_hdrs.exists():
                s = run_installhdrs(tc, 'MSM8916', 'C-installhdrs.log')
                results['stages']['C_installhdrs'] = annotate(s)
                if s['rc'] == 0:
                    stamp_hdrs.touch()
            else:
                results['stages']['C_installhdrs'] = {'note': 'reused stamped installhdrs', 'rc': 0}
            if stamp_hdrs.exists():
                results['stages']['C'] = annotate(run_build(tc, 'MSM8916', 'C-build-msm8916.log'))

    tmp = rj.with_suffix('.json.tmp')
    tmp.write_text(json.dumps(results, indent=2))
    tmp.replace(rj)
    info('driver done')


if __name__ == '__main__':
    main()
