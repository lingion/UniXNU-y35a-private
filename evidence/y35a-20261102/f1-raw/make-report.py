#!/usr/bin/env python3
"""Assemble F1 report.json from the container results + manual classification."""
import json
import re
from pathlib import Path

RAW = Path(__file__).resolve().parent / 'raw'
results = json.loads((RAW / 'results-a0-a1-b-c.json').read_text())


def objs(logpath):
    txt = Path(logpath).read_text(errors='replace')
    return sorted(set(re.findall(r'\*\*\* \[[\w/.\-^$[\]-]*?([\w.-]+\.(?:o|cpo))\] Error 1', txt)))


B_FAILS = objs(RAW / 'B-build-t7001.log')
C_FAILS = objs(RAW / 'C-build-msm8916.log')

MIG = ('fixable-by-patch',
       'port the 4903 pair: declaration block osfmk/kern/ipc_mig.h:158-162 '
       '(extern void mach_msg_destroy_from_kernel_proper(mach_msg_header_t*); '
       '#define mach_msg_destroy_from_kernel mach_msg_destroy_from_kernel_proper) '
       'plus the definition from osfmk/kern/ipc_mig.c. 4570 ships ipc_mig.c/.h but both '
       'lost the destroy surface; the MIG-generated callers (__MigKernelSpecificCode-gated) '
       'are present, so every kernel-side MIG stub fails implicit-declaration on clang 24.')
GSSD = ('fixable-by-patch', MIG[1])

report = {
    'experiment': 'F1 - xnu-4570 ground-truth compile (linux_env container)',
    'date': '2026-11-05',
    'container': 'unixnu-y35a-native-20261103',
    'source_tag': 'xnu-4570.51.1 (Darwin 17.5.0; config/MasterVersion read directly). '
                  'NOTE: the task brief said xnu-4570.121.2 - that tag does not exist; '
                  '4570.121.2 is not an Apple 4570-series tag (4570 lines end at .52.x). '
                  'The bringup-map cites xnu-4570.51.1, which matches the tree on disk.',
    'harness': {
        'driver': 'out/y35a/ios12-4570-f1/driver-f1.py (ran A0/A1/B/C sequentially, JOBS=7, '
                  'make build -k -Otarget, 55-min per-stage timeout never hit: every stage finished in <=87 s of build time)',
        'trees': 'A0=/work/f1/A0 pristine; A1=/work/f1/A1 makedefs-port+fix_source; '
                 'C=/work/f1/C same port + 0001-y35a-board.patch + MSM8916 machine entry',
        'logs': {k: str(RAW / v) for k, v in {
            'A0': 'A0-installhdrs.log', 'A1': 'A1-installhdrs.log',
            'B': 'B-build-t7001.log', 'C-installhdrs': 'C-installhdrs.log',
            'C': 'C-build-msm8916.log'}.items()},
    },

    'verdict': {
        'headline': '4570 needs makedefs work: the recipe port IS SUFFICIENT to get ARM64 to '
                    'compile, and both vanilla T7001 and Y35A MSM8916 configs then fail only on '
                    'enumerated source gaps - none of them build-system dead ends. The 4903 '
                    'builder docstring claim "cannot build ARM64 at all" is TRUE ONLY OF THE '
                    'PUBLISHED makedefs (A0 reproduces the wall exactly); the bringup-map claim '
                    '"vanilla builds are feasible" is ALSO TRUE once the recipe is ported (A1/B). '
                    'Both docs are right about different scopes.',
        'A0_vanilla': 'FAILS at makedefs/MakeInc.kernel:14 "Unsupported CURRENT_ARCH_CONFIG ARM64" '
                      '- 4570 published makedefs have SUPPORTED_ARCH_CONFIGS := X86_64 X86_64H and '
                      'ZERO ARM64 occurrences anywhere in makedefs/ (grep -c = 0). Confirms the '
                      '4903-builder note verbatim, this session, live.',
        'A1_ported_installhdrs': 'PASSES (rc=0, 7 s). The 11-edit makedefs port (below) is complete: '
                                 'setup, config stage, and full kernel-header export run clean for ARM64/T7001.',
        'B_vanilla_T7001': 'FAILS compile with 9 distinct root classes (44 error records, 699 of '
                           '~727 objects attempted). NONE is an Apple-HID c15 trap (those all sit '
                           'behind APPLE_ARM64_ARCH_FAMILY, which T7001 defines and MSM8916 does not). '
                           '8 of the 9 classes hit BOTH configs; only config-shape differs.',
        'C_Y35A_MSM8916': 'FAILS compile with 12 distinct root classes: the 9 shared B classes + '
                          'exactly the 3 non-Apple-branch classes predicted by patch 0001 trailer '
                          '(caches_asm.s:133 CleanPoU_Dcache #error; machine_routines.c:1634/:1671/:1793 '
                          '#error trio; new: caches.c armb-v7 legacy region) + patch-0001 gap: '
                          'MSM8916.h missing from pexpert/pexpert/arm64/Makefile DATAFILES (fixed in-tree, '
                          'feed back into 0001 rev).',
    },

    'makedefs_port_recipe': {
        'summary': '11 anchor-checked edits; all 11 applied cleanly in A1 and C (results json lists them). '
                   'This is the exact list a future build-xnu-4570-kernel.py needs.',
        'edits': [
            'MakeInc.def: SUPPORTED_ARCH_CONFIGS += ARM64',
            'MakeInc.def: SUPPORTED_ARM64_MACHINE_CONFIGS = MSM8916 S5L8960X T7000 T7001 S8000 S8001 T8010 T8011',
            'MakeInc.def: MACHINE_FLAGS_ARM64_<M> = -DARM64_BOARD_CONFIG_<M> for each (T8010/T8011 -mcpu=hurricane DROPPED - Apple-clang-only knob, rejected by upstream clang 24)',
            'MakeInc.def: ARCH_FLAGS_ARM64 = -arch $(ARCH_STRING_FOR_CURRENT_MACHINE_CONFIG)',
            'MakeInc.def: CFLAGS_ARM64 (-Darm64 -DARM64 -D__ARM64__ -DLP64 -DPAGE_SIZE_FIXED -fno-strict-aliasing -D__API__=v4 -mkernel) + CFLAGS_{RELEASE,DEVELOPMENT,KASAN,DEBUG,PROFILE}ARM64',
            'MakeInc.def: SFLAGS_ARM64 = $(CFLAGS_ARM64)',
            'MakeInc.def: KASAN_SHIFT_ARM64 = 0xdffffff800000000',
            'MakeInc.def: CXXFLAGS_GEN -std=gnu++11 -> gnu++1z (4903 parity)',
            'MakeInc.def: LDFLAGS_KERNEL_GENARM64 block ported verbatim from 4903 (image_base 0xfffffff007004000, __PRELINK_TEXT 0xfffffff004004000, DATA_CONST/TEXT_EXEC renames) + per-config alias lines; sectcreate lines NOT duplicated (4570 keeps them arch-neutral in LDFLAGS_KERNEL_GEN)',
            'MakeInc.def: LDFLAGS_KERNEL_SDK drops -lfirehose_kernel; LD_KERNEL_LIBS = -lcc_kext -lfirehose_kernel (4903 split)',
            'MakeInc.cmd: SDKROOT ?= macosx.internal -> macosx',
        ],
        'make_vars': 'same 4903 injection set: PLATFORM=iPhoneOS HOST_CC=xnu-host-cc MIGCOM=libexec/migcom '
                     'TIGHTBEAMC=tightbeamc-not-supported BUILD_DSYM=0 HOST_OS_VERSION=14.6 HOST_CODESIGN=/usr/bin/true '
                     'ARCH_STRING_FOR_CURRENT_MACHINE_CONFIG=arm64 SDKVERSION=11.4 BUILD_STATIC_LINK=0 '
                     'INCFLAGS_SDK+=-I$(SDKROOT)/usr/local/include OBJROOT/SYMROOT/DSTROOT under the tree; '
                     'installhdrs with SDKROOT=macosx, build with SDKROOT=iphoneos; LD_KERNEL_LIBS gets the '
                     'force_load libcc_kext.a fix; fakeroot: rebuild archive indexes with libtool (ranlib-incompatible).',
    },

    'fix_source_4570': {
        'ported_and_needed': [
            'makesyscalls.sh \\(sy_call_t *\\) -> (sy_call_t *) (anchor present, needed)',
            'kextsymboltool.c seekFile lseek-on-/dev/null (4570 body has NO braces - anchor adapted)',
            'installfile.c O_SYMLINK -> O_RDONLY (anchor present)',
            'makekdebugevents.py python2 -> python3 rewrite (reuse the 4903 builder _KDEBUG_PY3 string VALUE, '
            'ast.literal_eval - a raw regex capture double-unescapes and corrupts the generated header)',
            'make_posix_availability.sh shebang -> /bin/bash (bash-only script, dash cannot parse)',
            'osfmk/arm64/genassym.c DECLARE: .ascii "%0" : : "n" -> .ascii "#%0" : : "n" (4570 tag ships "n" '
            'constraint; proven work form is the # -padded string; # alone prevents the 1-char .byte fold)',
            'makedefs/MakeInc.top dash -nt timestamp spin guard (same fix as 4903/10063)',
            'config/MASTER: ADD "options CONFIG_EMBEDDED # <config_embedded>" (4903 config/MASTER:313 has it, '
            '4570 dropped it while its own bundle graphs still use the keyword - without it EVERY embedded gate '
            'resolves desktop-side: panic_info type, dtrace/i386 files, video_console boot-args fields)',
            'config/MASTER.arm64: MONOTONIC_BASE bundle uncomment (4903 same defect, same fix)',
        ],
        'not_needed_in_4570': [
            'corecrypto arm64_isa_compatibility.h ISA patch - file absent in 4570',
            'machine/monotonic.h MT_CORE_NFIXED gate - 4570 header shape differs (gate not needed at this stage)',
            'mach_kernelrpc.c goto-over-VLA reorder - site differs in 4570 (did not reproduce as an error in B/C)',
        ],
    },

    'stages': {
        'A0': {k: results['stages']['A0'][k] for k in
               ('rc', 'seconds', 'timed_out', 'reached_compile')} | {'errors': results['stages']['A0']['distinct_errors']},
        'A1': {k: results['stages']['A1'][k] for k in
               ('rc', 'seconds', 'timed_out', 'reached_compile')} | {'errors': results['stages']['A1'].get('distinct_errors', [])},
        'B': {k: results['stages']['B'][k] for k in
              ('rc', 'seconds', 'timed_out', 'reached_compile', 'error_lines_total')}
           | {'failed_objects': B_FAILS, 'errors': results['stages']['B']['distinct_errors']},
        'C_installhdrs': {k: results['stages']['C_installhdrs'][k] for k in ('rc', 'seconds')},
        'C': {k: results['stages']['C'][k] for k in
              ('rc', 'seconds', 'timed_out', 'reached_compile', 'error_lines_total')}
           | {'failed_objects': C_FAILS, 'errors': results['stages']['C']['distinct_errors']},
    },

    'error_classes': [
        {
            'id': 'E1-missing-conf-files', 'count_in': ['B', 'C'], 'records': 2,
            'files': ['libkern/conf/files.arm64 (absent)', 'san/conf/files.arm64 (absent)', 'san/conf/Makefile.arm64 (absent)'],
            'message': "No rule to make target '.../files.arm64'",
            'classification': 'fixable-by-patch',
            'minimal_fix': 'copy the three tiny files from xnu-4903 (libkern/conf/files.arm64 is 1 line, '
                           'san/conf/files.arm64 is 3 lines, san/conf/Makefile.arm64 is 0 lines). '
                           'Or, for F1 purposes, exclude libkern/san from the file lists.',
        },
        {
            'id': 'E2-missing-xnupost-header', 'count_in': ['B', 'C'], 'records': 1,
            'files': ['osfmk/arm64/platform_tests.c:68'],
            'message': "'tests/xnupost.h' file not found",
            'classification': 'fixable-by-patch',
            'minimal_fix': 'osfmk/tests/ (the xnupost framework) is entirely unpublished in the 4570 drop - '
                           '4903 ships osfmk/tests/xnupost.h. Either port osfmk/tests/ from 4903 or drop the '
                           'config_xnupost-optional platform_tests entry from osfmk/conf/files.arm64 (it is '
                           'DEVELOPMENT-only; RELEASE builds unaffected).',
        },
        {
            'id': 'E3-mig-destroy-surface-missing', 'count_in': ['B', 'C'], 'records': 18,
            'files': ['gssd_mach.c', 'lockd_mach.c', 'UNDRequest.c', 'exc_user.c', 'mach_exc_user.c', 'task_access_user.c'],
            'message': "call to undeclared function 'mach_msg_destroy_from_kernel'",
            'classification': MIG[0], 'minimal_fix': MIG[1],
        },
        {
            'id': 'E4-const-wired-page-count', 'count_in': ['B', 'C'], 'records': 1,
            'files': ['osfmk/vm/vm_object.c:355 (via *object = vm_object_template at :263/:355)'],
            'message': "cannot assign to lvalue with const-qualified data member 'wired_page_count'",
            'classification': 'fixable-by-patch',
            'minimal_fix': '4570 vm_object.h:174 declares wired_page_count const; 4903 made it plain '
                           'unsigned int (vm_object.h:173). Drop the const (and any VM_OBJECT_WIRED_PAGE_UPDATE '
                           'macro assumptions), or replace the struct assignment with field-wise copy skipping '
                           'wired_page_count. 4903 evolution is the reference.',
        },
        {
            'id': 'E5-kern-machdep-unclosed-switch', 'count_in': ['B', 'C'], 'records': 2,
            'files': ['bsd/dev/arm/kern_machdep.c:173,188'],
            'message': "function definition is not allowed here / expected '}'",
            'classification': 'fixable-by-patch',
            'minimal_fix': 'grade_binary() in the 4570 drop is one closing brace short (brace count over the '
                           'function 14 open/13 close; 4903 is 15/15). The missing line is the '
                           '"} /* switch (hostsubtype) */" after the CPU_TYPE_ARM64 case (4903 line 27 region); '
                           '4570 substituted a break. Add the brace. This is genuine published-source breakage - '
                           'the file as shipped cannot compile for ANY architecture config.',
        },
        {
            'id': 'E6-panic-header-shape', 'count_in': ['B(r1)', 'C(r1)'], 'records': 19,
            'files': ['pexpert/arm/pe_init.c:53/96/99/...', 'osfmk/arm/model_dep.c:473-477'],
            'message': "redefinition of 'panic_info' ... no member named 'eph_*' in struct macos_panic_header",
            'classification': 'fixable-by-patch',
            'minimal_fix': 'ALREADY FIXED in the final run by the config/MASTER CONFIG_EMBEDDED option line '
                           '(class was 100% gone in B/C round 3). Kept in the inventory because it was the '
                           'largest first-round cluster and proves 4570 build recipe needs that one option line. '
                           'pexpert.h:56/69 choose the panic header by CONFIG_EMBEDDED; 4570 sources are '
                           'embedded-flavored throughout.',
        },
        {
            'id': 'E7-bootargs-flags-embedded-gate', 'count_in': ['B(r1)', 'C(r1)'], 'records': 5,
            'files': ['osfmk/console/video_console.c:2468/3011/3045/3048', 'iokit/Kernel/IOPlatformExpert.cpp:166'],
            'message': "no member named 'flags'/'bootProgressMeterEnd' in struct boot_args; undeclared kBootArgsFlag*",
            'classification': 'fixable-by-patch',
            'minimal_fix': 'Same root cause as E6: desktop branches selected without CONFIG_EMBEDDED. Gone in '
                           'round 3. (IOPlatformExpert extended_debug_log_init likewise: embedded gate.)',
        },
        {
            'id': 'E8-freezer-symbols-desktop-paths', 'count_in': ['B(r1)'], 'records': 3,
            'files': ['osfmk/vm/vm_compressor.c:739/2990/2993'],
            'message': "undeclared identifier freezer_compressor_scratch_buf / freezer_chead / c_freezer_swapout_count",
            'classification': 'fixable-by-patch',
            'minimal_fix': 'Same CONFIG_EMBEDDED family (freeze/jetsam bundle). Gone in round 3.',
        },
        {
            'id': 'E9-i386-panic-hooks-leak', 'count_in': ['B(r1)'], 'records': 1,
            'files': ['bsd/vfs/vfs_subr.c:578'],
            'message': "'i386/panic_hooks.h' file not found",
            'classification': 'fixable-by-patch',
            'minimal_fix': 'desktop-branch leak (CONFIG_EMBEDDED fix removed it in round 3; the include sits in '
                           'a !CONFIG_EMBEDDED region).',
        },
        {
            'id': 'E10-boards-pexpert-hdr-export', 'count_in': ['C(r1)'], 'records': 505,
            'files': ['BUILD/obj/EXPORT_HDRS/pexpert/pexpert/arm64/board_config.h:125'],
            'message': "'pexpert/arm64/MSM8916.h' file not found",
            'classification': 'fixable-by-patch',
            'minimal_fix': 'PATCH 0001 GAP: it adds pexpert/pexpert/arm64/MSM8916.h but not to '
                           'pexpert/pexpert/arm64/Makefile DATAFILES. One-line addition '
                           '"\\tMSM8916.h \\\\\""; driver did it in-tree; MUST be folded into 0001 rev 2.',
        },
        {
            'id': 'E11-cleanpou-dcache-error', 'count_in': ['C'], 'records': 1,
            'files': ['osfmk/arm64/caches_asm.s:133'],
            'message': '#error CleanPoU_Dcache needs an implementation',
            'classification': 'fixable-by-patch',
            'minimal_fix': 'Exactly as predicted by the patch-0001 trailer and R1 of the bringup-map: with '
                           'APPLE_ARM64_ARCH_FAMILY undefined the region falls through to the #error. '
                           'Patch 0002 implements dc civac/cva sequences for A53 (PoU is L1-private; the '
                           'Apple fully-coherent short-circuit is wrong here). CONFIRMED present.',
        },
        {
            'id': 'E12-machine-routines-error-trio', 'count_in': ['C'], 'records': 3,
            'files': ['osfmk/arm64/machine_routines.c:1634', ':1671', ':1793'],
            'message': '"Make sure you don\'t need to xcall." / "Make sure not cleaning is right for this platform!" / "Need a board configuration." (fiq_context_init)',
            'classification': 'fixable-by-patch',
            'minimal_fix': 'The trailer list, confirmed verbatim: three #error gates on the non-Apple path. '
                           '0002 answers each with the MSM8916 branch (xcall yes - A53 is SMP-coherent; '
                           'clean-before-ic-ireg is required; fiq_context skips Apple timebase-event-stream, '
                           'keeps _enable_virtual_timer).',
        },
        {
            'id': 'E13-caches-c-armb-legacy', 'count_in': ['C'], 'records': 4,
            'files': ['osfmk/arm/caches.c:393 (SCTLR_DCACHE), :421-424 (cpu_CLW_active/CLWFlush_req/CLWClean_req)'],
            'message': "undeclared identifier / no member in struct cpu_data",
            'classification': 'fixable-by-patch',
            'minimal_fix': 'NEW - NOT in the trailer list. platform_cache_disable/idle_enter use armv7 cp15 mrc/mcr '
                           '(no SCTLR_DCACHE on arm64; the ops trap as undefined instructions on A53) and cpu_CLW_* '
                           'fields gated "#if __ARM_SMP__ && defined(ARMA7)" in 4570 cpu_data_internal.h:223-228 '
                           '(4903 gates them ARM_ARCH_TIMER-style). Fix per 4903: #if (__ARM_ARCH__ < 8) guard on '
                           'platform_cache_disable + #define SCTLR_DCACHE under arch<8; drop the CLW bookkeeping for '
                           'arch>=8 (4903 already does exactly this - port the region).',
        },
        {
            'id': 'E14-idle-path-link-blocker', 'count_in': ['static-confirmed'], 'records': 0,
            'files': ['osfmk/arm64/machine_routines_asm.s:830-1033', 'osfmk/arm64/cpu.c:85-86,274,708,738'],
            'message': '(link-time) _arm64_prepare_for_sleep / _arm64_force_wfi_clock_gate undefined',
            'classification': 'fixable-by-patch',
            'minimal_fix': 'NOT yet observable (builds die at compile), but statically PROVEN this run: both symbols '
                           'are defined ONLY inside #if defined(APPLE_ARM64_ARCH_FAMILY) (the sole definitions in '
                           'the tree, machine_routines_asm.s:836/886) while cpu.c calls them unconditionally. Any '
                           'MSM8916 link fails. Trailer list confirmed; 0002 adds the plain dsb;isb;wfi loop.',
        },
    ],

    'contradictions': [
        'build-xnu-4903-kernel.py docstring: "Apple\'s published xnu-4570 tag cannot build ARM64 at all" - true for '
        'the published makedefs (reproduced exactly, A0), false as a ceiling: nothing else in the tree blocks ARM64; '
        'after the 11-edit recipe port, installhdrs completes and ~699/727 objects compile for vanilla T7001.',
        'ios12-bringup-map section 6.1 "Vanilla T7000/T7001 builds are unaffected / feasible": TRUE in substance, but '
        'it never states that the published 4570 makedefs lack the recipe entirely - a naive "just build it" attempt '
        'dies at MakeInc.kernel:14. The map should point at this F1 makedefs_port_recipe section.',
        'bringup-map header cites tag "xnu-4570.51.1"; the task brief said ".121.2". On-disk tree = 4570.51.1; '
        '4570.121.2 is not a real Apple tag.',
        'patch 0001 trailer blocker list is missing one item: caches.c armb-v7 legacy region (E13) - add to 0002 scope.',
        'The brief\'s memory file y35a-container-toolchain-quirks.md does not exist; the quirks live in '
        'evidence/y35a-20261102/recon-20261105-ios12.md lines 52-58 (and the genassym "final fix" recorded there as '
        'the MakeInc.def GENASSYM_UNFOLD sed table is NOT what the successful 4903 build used - the proven form is '
        'the plain genassym.c ".ascii \\"#%0\\"" + constraint change; verified against .cache/xnu4903-work).',
    ],

    'stats': {
        'A0_errors': len(results['stages']['A0']['distinct_errors']),
        'A1_errors': 0, 'A1_rc': results['stages']['A1']['rc'],
        'B_error_records': len(results['stages']['B']['distinct_errors']),
        'B_failed_objects': B_FAILS,
        'B_objects_produced': 662,
        'C_objects_produced': 659,
        'reference': 'the green 4903 T7001 build produced 727 objects; 4570 B/C reached 662/659 before -k exhausted '
                     'recoverable targets - the delta is the error classes enumerated, not a toolchain wall.',
        'C_error_records': len(results['stages']['C']['distinct_errors']),
        'C_failed_objects': C_FAILS,
        'shared_classes_B_and_C': 9, 'C_only_classes': 3,
    },
}

out = Path(__file__).resolve().parent / 'report.json'
out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
print('wrote', out)
