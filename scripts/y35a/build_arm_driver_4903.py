#!/usr/bin/env python3
"""Compile an isolated platform object using a prepared XNU 4903 header snapshot.

This does not build, link, install, or boot a kernel. ArmCpu requires explicit
boot-CPU-only mode; no SMP or hardware success is claimed. Failed runs are kept.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import plistlib
import re
import shlex
import struct
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BUILD = Path('/tmp/xnu4903-native-bqbvhqi_')
CONFIG = 'DEVELOPMENT_ARM64_T7001'
COMMIT = '494ffe1c29d37ca720c37328feb83069c9641b67'
TAG = 'xnu-4903.270.47'
PATCH = ROOT / 'patches/arm-driver-4903/0001-armdt-ownership.patch'
CPU_PATCH = PATCH.parent / '0002-armcpu-boot-only.patch'
CPU_SGI_PATCH = PATCH.parent / '0004-armcpu-sgi-probe-constraints.patch'
PERSONALITY_PATCH = PATCH.parent / '0003-kernel-personalities.patch'
SDCC_PERSONALITY_PATCH = PATCH.parent / '0005-qcom-sdcc-personality.patch'
DEFAULT_IOSTORAGE_SOURCE = ROOT / 'upstream-refresh/2026-11-15/sources/IOStorageFamily-191'
IOSTORAGE_FAMILY_TAG = 'IOStorageFamily-191'
IOSTORAGE_FAMILY_COMMIT = 'c95d31401f0ff950a883727f5e47d313685fde33'
IOSTORAGE_FAMILY_ARCHIVE_SHA256 = '2a8a4e216a4de2944e2e33aa07846cd152f821d7731bbfe7ddd47f7a94491bd3'
IOSTORAGE_DEVICE_HEADER_SHA256 = 'fe5807fdf2dc752d6c7bd0c6a6c4525bab5e0e99b4302ece767d3b0bc59d6e66'
IOSTORAGE_HEADER_FILES = (
    'IOAppleLabelScheme.h', 'IOApplePartitionScheme.h',
    'IOBlockStorageDevice.h', 'IOBlockStorageDriver.h',
    'IOFDiskPartitionScheme.h', 'IOFilterScheme.h',
    'IOGUIDPartitionScheme.h', 'IOMedia.h', 'IOMediaBSDClient.h',
    'IOPartitionScheme.h', 'IOStorage.h',
    'IOStorageDeviceCharacteristics.h', 'IOStorageProtocolCharacteristics.h',
    'IOStorageControllerCharacteristics.h', 'IOStorageCardCharacteristics.h',
)
IOSTORAGE_FAMILY_SOURCE_FILES = (
    'IOApplePartitionScheme.cpp', 'IOBlockStorageDevice.cpp',
    'IOBlockStorageDriver.cpp', 'IOFDiskPartitionScheme.cpp',
    'IOFilterScheme.cpp', 'IOGUIDPartitionScheme.cpp', 'IOMedia.cpp',
    'IOMediaBSDClient.cpp', 'IOPartitionScheme.cpp', 'IOStorage.cpp',
)

COMPONENT_SOURCES = {
    'ArmDTPlatform': ('ArmDTPlatform.cpp',),
    'ArmCpu': ('ArmCpu.cpp', 'GicV2.h'),
    'QcomSdcc': ('NativeSdcc.cpp', 'PersistStore.h', 'SdciCore.h'),
    'QcomSdcard': ('NativeSdcard.cpp', 'SdCardBus.h', 'SdCardCore.h'),
}

COMPONENT_INTEGRATION = {
    'QcomSdcc': {
        'role': 'userdata-window',
        'force_load': True,
        'consumer': 'scripts/build-xnu-4903-native.py',
    },
    'QcomSdcard': {
        'role': 'tf-storage',
        'force_load': True,
        'consumer': 'scripts/build-xnu-4903-native.py',
    },
}


def component_source_files(component: str) -> list[Path]:
    try:
        names = COMPONENT_SOURCES[component]
    except KeyError as error:
        raise ValueError(f'unsupported 4903 driver component: {component}') from error
    return [ROOT / 'drivers' / component / name for name in names]


def component_support_sources(component: str, iostorage_source: Path | None = None) -> list[Path]:
    if component in ('QcomSdcc', 'QcomSdcard'):
        if iostorage_source is None:
            raise ValueError('QcomSdcc needs the pinned IOStorageFamily source for ABI audit')
        return [iostorage_source.resolve(strict=True) / name
                for name in IOSTORAGE_FAMILY_SOURCE_FILES]
    if component in ('ArmDTPlatform', 'ArmCpu'):
        return []
    raise ValueError(f'unsupported 4903 driver component: {component}')


def component_patches(component: str) -> list[Path]:
    if component == 'ArmDTPlatform':
        return [PATCH]
    if component == 'ArmCpu':
        return [CPU_PATCH, CPU_SGI_PATCH]
    if component in ('QcomSdcc', 'QcomSdcard'):
        return []
    raise ValueError(f'unsupported 4903 driver component: {component}')


def component_personality_patch(component: str) -> Path | None:
    if component == 'QcomSdcc':
        return SDCC_PERSONALITY_PATCH
    if component == 'QcomSdcard':
        return PATCH.parent / '0006-qcom-sdcard-personality.patch'
    if component in ('ArmDTPlatform', 'ArmCpu'):
        return PERSONALITY_PATCH
    raise ValueError(f'unsupported 4903 driver component: {component}')


def component_defines(component: str) -> list[str]:
    if component == 'QcomSdcc':
        return ['-DXNU_NATIVE_SDCC=1']
    if component == 'QcomSdcard':
        return ['-DXNU_NATIVE_SDCARD=1']
    if component in ('ArmDTPlatform', 'ArmCpu'):
        return []
    raise ValueError(f'unsupported 4903 driver component: {component}')


def component_entry_source(component: str) -> str:
    if component == 'QcomSdcc':
        return 'NativeSdcc.cpp'
    if component == 'QcomSdcard':
        return 'NativeSdcard.cpp'
    if component in ('ArmDTPlatform', 'ArmCpu'):
        return component + '.cpp'
    raise ValueError(f'unsupported 4903 driver component: {component}')


def component_integration(component: str) -> dict:
    """Return the explicit 4903 consumer contract for a component."""
    return dict(COMPONENT_INTEGRATION.get(component, {
        'role': 'kernel-driver',
        'force_load': True,
        'consumer': 'scripts/build-xnu-4903-native.py',
    }))


def archive_members(component: str, run: Path, destination: Path) -> list[Path]:
    """Return the exact objects that the component archive must contain."""
    if component in ('QcomSdcc', 'QcomSdcard'):
        return [run / f'IOStorageFamily-{component}.o']
    return [destination]


def validate_iostorage_family_source(path: Path) -> dict:
    source = path.resolve(strict=True)
    if not source.is_dir():
        raise ValueError(f'IOStorageFamily source is not a directory: {source}')
    try:
        source_record = json.loads((source / 'SOURCE.json').read_text())
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f'cannot read pinned IOStorageFamily source record in {source}') from error
    expected_record = {
        'repository': 'https://github.com/apple-oss-distributions/IOStorageFamily',
        'tag': IOSTORAGE_FAMILY_TAG,
        'commit': IOSTORAGE_FAMILY_COMMIT,
        'git_archive_sha256': IOSTORAGE_FAMILY_ARCHIVE_SHA256,
    }
    if any(source_record.get(key) != value for key, value in expected_record.items()):
        raise ValueError('IOStorageFamily source identity differs from the pinned public archive')
    try:
        info = plistlib.loads((source / 'Info.plist').read_bytes())
        bundle_version = info['CFBundleVersion']
    except (OSError, KeyError, plistlib.InvalidFileException) as error:
        raise ValueError(f'cannot read IOStorageFamily bundle version from {source / "Info.plist"}') from error
    if bundle_version != '2.1' or source_record.get('bundle_version_in_tag') != '2.1':
        raise ValueError(f'expected IOStorageFamily bundle version 2.1, found {bundle_version!r}')
    missing = [name for name in IOSTORAGE_HEADER_FILES + IOSTORAGE_FAMILY_SOURCE_FILES
               if not (source / name).is_file()]
    if missing:
        raise ValueError('IOStorageFamily source lacks headers: ' + ', '.join(missing))
    hashes = source_record.get('header_sha256')
    if not isinstance(hashes, dict):
        raise ValueError('IOStorageFamily source record lacks header hashes')
    changed = [name for name in IOSTORAGE_HEADER_FILES + IOSTORAGE_FAMILY_SOURCE_FILES
               if hashes.get(name) != sha256(source / name)]
    if changed:
        raise ValueError('IOStorageFamily header hashes differ from source record: ' + ', '.join(changed))
    if hashes.get('IOBlockStorageDevice.h') != IOSTORAGE_DEVICE_HEADER_SHA256:
        raise ValueError('IOBlockStorageDevice.h differs from the cross-tag-stable 2.1 ABI header')
    return {'tag': IOSTORAGE_FAMILY_TAG, 'commit': IOSTORAGE_FAMILY_COMMIT,
            'git_archive_sha256': IOSTORAGE_FAMILY_ARCHIVE_SHA256,
            'bundle_version': bundle_version, 'IOBlockStorageDevice_h_sha256': IOSTORAGE_DEVICE_HEADER_SHA256,
            'source': str(source)}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def changed_inputs(records: list[dict]) -> list[str]:
    changed = []
    for item in records:
        path = Path(item['input'])
        if not path.is_file() or sha256(path) != item['sha256']:
            changed.append(str(path))
    return sorted(set(changed))


def effective_configuration(text: str) -> dict:
    macros = dict(re.findall(r'^#define (\w+) (.*)$', text, re.MULTILINE))
    if macros.get('WITH_CLASSIC_S2R') not in ('0', '1'):
        raise ValueError('missing or nonliteral effective WITH_CLASSIC_S2R')
    return {key: macros.get(key) for key in (
        'ARM64_BOARD_CONFIG_T7001', 'ARM_BOARD_CLASS_T7000', 'XNU_Y35A_A53',
        'WITH_CLASSIC_S2R', 'MAX_CPUS', 'MACH_ASSERT', 'DEVELOPMENT')}


def verify_inputs(run: Path) -> int:
    """Read-only freshness check. This cannot establish target kernel ABI identity."""
    manifest = json.loads((run / 'manifest.json').read_text())
    if manifest.get('status') != 'object-compiled' or 'configuration' not in manifest:
        raise ValueError('run lacks a completed configuration-bound build; rebuild required')
    if sha256(run / 'inputs.json') != manifest['inputs_sha256']:
        raise ValueError('input inventory changed')
    changed = changed_inputs(json.loads((run / 'inputs.json').read_text()))
    for item in json.loads((run / 'consumed-inputs.json').read_text()):
        path = Path(item['path'])
        if not path.is_file() or sha256(path) != item['sha256']:
            changed.append(str(path))
    if sha256(run / 'consumed-inputs.json') != manifest['consumed_inputs_sha256']:
        changed.append(str(run / 'consumed-inputs.json'))
    for key in ('object', 'archive', 'abi_probe'):
        item = manifest[key]
        if sha256(Path(item['path'])) != item['sha256']:
            changed.append(item['path'])
    if changed:
        print('Inputs/artifacts changed; rebuild required:\n' + '\n'.join(sorted(set(changed))))
        return 1
    print('Recorded inputs and artifacts unchanged. Target kernel must separately match '
          f'profile={manifest["configuration"]["profile"]}; no link/runtime validation.')
    return 0


def config_defines(text: str) -> list[str]:
    prefix = 'export CONFIG_DEFINES = '
    lines = [line[len(prefix):] for line in text.splitlines() if line.startswith(prefix)]
    if len(lines) != 1 or '$' in lines[0] or '`' in lines[0]:
        raise ValueError('expected one literal CONFIG_DEFINES line')
    flags = shlex.split(lines[0])
    if not flags or any(not flag.startswith('-D') for flag in flags):
        raise ValueError('CONFIG_DEFINES must contain only -D arguments')
    return flags


def allocate_run(path: Path | None, protected: list[Path]) -> Path:
    if path is None:
        return Path(tempfile.mkdtemp(prefix='arm-driver-4903-', dir='/tmp')).resolve()
    path = path.expanduser()
    if path.exists() or path.is_symlink():
        raise FileExistsError(f'refusing existing output: {path}')
    resolved = path.resolve()
    for parent in protected:
        if resolved == parent.resolve() or parent.resolve() in resolved.parents:
            raise ValueError(f'output must be outside input/repository: {resolved}')
    resolved.mkdir()  # Parent must already exist; never create directories in an input.
    return resolved


def audit_object(data: bytes) -> dict:
    if len(data) < 32:
        raise ValueError('truncated Mach-O header')
    magic, cpu, subtype, kind, count, size, _, _ = struct.unpack_from('<8I', data)
    if (magic, cpu, subtype, kind) != (0xFEEDFACF, 0x0100000C, 0, 1):
        raise ValueError('expected ordinary arm64 MH_OBJECT, not arm64e or linked kernel')
    end = 32 + size
    if end > len(data):
        raise ValueError('truncated load commands')
    offset, deployments = 32, []
    for _ in range(count):
        if offset + 8 > end:
            raise ValueError('truncated load command')
        command, length = struct.unpack_from('<2I', data, offset)
        if length < 8 or length % 8 or offset + length > end:
            raise ValueError('invalid load command length')
        if command == 0x32:
            if length < 24:
                raise ValueError('truncated LC_BUILD_VERSION')
            deployments.append(struct.unpack_from('<2I', data, offset + 8))
        elif command == 0x25:
            if length < 16:
                raise ValueError('truncated LC_VERSION_MIN_IPHONEOS')
            deployments.append((2, struct.unpack_from('<I', data, offset + 8)[0]))
        offset += length
    if offset != end or deployments != [(2, 0x0C0400)]:
        raise ValueError(f'expected one iOS 12.4 deployment: {deployments}')
    return {'architecture': 'arm64', 'filetype': 'MH_OBJECT', 'minimum_os': '12.4.0'}


def save(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + '\n')


def audit_dependencies(text: str, run: Path) -> list[dict]:
    """Reject accidental host/10063 includes; hash the actual compiler dependencies."""
    _, separator, dependencies = text.replace('\\\n', '').partition(':')
    if not separator:
        raise ValueError('invalid compiler dependency file')
    records = []
    for name in sorted(set(shlex.split(dependencies))):
        path = Path(name).resolve(strict=True)
        if run.resolve() not in path.parents:
            raise ValueError(f'compiler read outside isolated snapshot: {path}')
        records.append({'path': str(path), 'sha256': sha256(path)})
    if not records:
        raise ValueError('compiler emitted no dependencies')
    return records


def run_command(argv: list[str], run: Path, name: str, manifest: dict,
                *, check: bool = True) -> subprocess.CompletedProcess:
    save(run / (name + '-command.json'), {'argv': argv, 'cwd': str(run)})
    env = os.environ.copy()
    env['TMPDIR'] = str(run / 'tmp')
    env.pop('CPATH', None)
    env.pop('CPLUS_INCLUDE_PATH', None)
    env.pop('C_INCLUDE_PATH', None)
    result = subprocess.run(argv, cwd=run, env=env, capture_output=True, text=True)
    (run / (name + '.log')).write_text(result.stdout + result.stderr)
    manifest['steps'].append({'name': name, 'returncode': result.returncode,
                              'command': str(run / (name + '-command.json'))})
    save(run / 'manifest.json', manifest)
    if check and result.returncode:
        raise RuntimeError(f'{name} failed ({result.returncode}); see {run / (name + ".log")}')
    return result


def snapshot(source: Path, destination: Path, records: list[dict]) -> None:
    """Copy bytes, including symlink referents, without retaining writable input links."""
    if source.is_dir():
        destination.mkdir(parents=True)
        for item in sorted(source.iterdir()):
            snapshot(item, destination / item.name, records)
    else:
        destination.parent.mkdir(parents=True, exist_ok=True)
        data = source.read_bytes()
        with destination.open('xb') as output:
            output.write(data)
        records.append({'input': str(source), 'snapshot': str(destination),
                        'sha256': hashlib.sha256(data).hexdigest()})


def build(args: argparse.Namespace, run: Path, manifest: dict) -> None:
    manifest['snapshot_started_utc'] = datetime.now(timezone.utc).isoformat()
    native = args.native_build.resolve(strict=True)
    source = native / 'src'
    generated = native / 'obj' / CONFIG / 'iokit/DEVELOPMENT'
    identity = run_command(['git', '-C', str(source), 'rev-parse', 'HEAD'], run,
                           'source-head', manifest).stdout.strip()
    if identity != COMMIT or (source / 'config/MasterVersion').read_text().splitlines()[0] != '18.7.0':
        raise ValueError(f'expected {TAG} baseline, found {identity}')
    manifest['source'] = {'path': str(source), 'baseline_commit': identity, 'tag': TAG,
                          'note': 'Patched working tree; exact consumed bytes are in inputs.json.'}
    flags = config_defines((generated / 'Makefile').read_text())
    inputs = []
    include = run / 'headers'
    snapshot(native / 'obj/EXPORT_HDRS', include / 'export', inputs)
    snapshot(source / 'iokit/IOKit', include / 'iokit/IOKit', inputs)
    snapshot(source / 'EXTERNAL_HEADERS', include / 'external', inputs)
    for header in sorted(generated.glob('*.h')):
        snapshot(header, include / 'generated' / header.name, inputs)
    snapshot(generated / 'Makefile', run / 'inputs/iokit-Makefile', inputs)
    snapshot(source / 'config/MasterVersion', run / 'inputs/MasterVersion', inputs)
    # Track private layout/config sources even though these are not driver includes.
    # The kernel and generated assembly may depend on them across profile changes.
    for relative in ('osfmk/arm/cpu_data_internal.h', 'osfmk/arm/machine_routines.h',
                     'pexpert/pexpert/arm64/T7000.h', 'pexpert/pexpert/arm64/board_config.h'):
        snapshot(source / relative, run / 'inputs/abi-source' / relative, inputs)
    storage_include = None
    if args.component in ('QcomSdcc', 'QcomSdcard'):
        storage_source = args.iostorage_source or DEFAULT_IOSTORAGE_SOURCE
        storage_record = validate_iostorage_family_source(storage_source)
        manifest['iostorage_family_source'] = storage_record
        storage_include = run / 'headers/iostorage'
        snapshot(storage_source / 'SOURCE.json', run / 'inputs/iostorage-family-SOURCE.json', inputs)
        snapshot(storage_source / 'Info.plist', run / 'inputs/iostorage-family-Info.plist', inputs)
        for name in IOSTORAGE_HEADER_FILES:
            snapshot(storage_source / name, storage_include / 'IOKit/storage' / name, inputs)
        for support_source in component_support_sources(args.component, storage_source):
            snapshot(support_source, run / 'driver/IOStorageFamily' / support_source.name, inputs)
        snapshot(native / 'fakeroot/usr/include/TargetConditionals.h',
                 storage_include / 'TargetConditionals.h', inputs)
        snapshot(native / 'fakeroot/System/Library/Frameworks/Kernel.framework/Versions/A/Headers/sys/cdefs.h',
                 storage_include / 'sys/cdefs.h', inputs)
    for name in ('T7000.h', 'board_config.h'):
        original = run / 'inputs/abi-source/pexpert/pexpert/arm64' / name
        exported = include / 'export/pexpert/pexpert/arm64' / name
        if sha256(original) != sha256(exported):
            raise ValueError(f'source/exported {name} differ; refresh native installhdrs first')
    # Keep the generated configuration as one snapshot, not a second live read.
    if config_defines((run / 'inputs/iokit-Makefile').read_text()) != flags:
        raise RuntimeError('IOKit configuration changed during snapshot')
    staged = run / 'driver' / args.component
    for item in component_source_files(args.component):
        snapshot(item, staged / item.name, inputs)
    save(run / 'inputs.json', inputs)
    if not args.baseline:
        patches = component_patches(args.component)
        for patch in patches:
            snapshot(patch, run / 'inputs' / patch.name, inputs)
        if args.component == 'ArmCpu':
            snapshot(PATCH.parent / 'ArmCpu4903Support.h', staged / 'ArmCpu4903Support.h', inputs)
        # The patch names only the staged driver. Do not execute source Makefiles.
        for index, patch in enumerate(patches):
            for operation in ('--check', None):
                argv = ['git', 'apply', '--directory=driver']
                if operation:
                    argv.append(operation)
                argv.append(str(run / 'inputs' / patch.name))
                suffix = f'{index + 1}-' + ('check' if operation else 'apply')
                run_command(argv, run, 'patch-' + suffix, manifest)
    save(run / 'inputs.json', inputs)
    compiler = args.clang or subprocess.check_output(['xcrun', '--find', 'clang++'], text=True).strip()
    manifest['compiler'] = {'path': compiler, 'sha256': sha256(Path(compiler)),
                            'version': run_command([compiler, '--version'], run, 'compiler', manifest).stdout}
    argv = [compiler, '-target', 'arm64-apple-ios12.4', '-std=gnu++17', '-fapple-kext',
            '-mkernel', '-nostdinc', '-nostdinc++', '-fno-builtin', '-fno-common',
            '-fno-exceptions', '-fno-rtti', '-fno-strict-aliasing', '-fsigned-bitfields',
            '-mgeneral-regs-only', '-O2', '-Wall', '-Wextra', '-Werror',
            '-Wno-unused-parameter', '-ferror-limit=0',
            '-DARM64_BOARD_CONFIG_T7001', '-Darm64', '-DARM64', '-D__ARM64__',
            '-DLP64', '-DPAGE_SIZE_FIXED', '-D__API__=v4', '-DIOASSERT=1',
            '-DPLATFORM_iPhoneOS', '-DAPPLE', '-DKERNEL', '-DKERNEL_PRIVATE',
            '-DXNU_KERNEL_PRIVATE', '-DPRIVATE', '-D__MACHO__=1', '-Dvolatile=__volatile',
            '-DDRIVER_PRIVATE', '-DIOKIT_KERNEL_PRIVATE', '-DIOMATCHDEBUG=1', '-DIOALLOCDEBUG=1'] + flags
    if args.boot_cpu_only:
        argv.append('-DARMCPU_4903_BOOT_CPU_ONLY=1')
    if args.board_profile == 'y35a-a53':
        # Explicit counterpart of R75 OTHER_CFLAGS. Do not parse .CFLAGS with shlex:
        # that loses the generated quoting of space-containing -D values.
        argv.append('-DXNU_Y35A_A53=1')
    argv.extend(component_defines(args.component))
    # Treat original Apple headers as system headers; own driver warnings remain errors.
    for directory in [include / 'generated', include / 'iokit'] + [
            include / 'export' / name for name in
            ('iokit', 'osfmk', 'bsd', 'libkern', 'pexpert', 'libsa', 'security', 'san')
    ] + [include / 'external']:
        argv += ['-isystem', str(directory)]
    if storage_include:
        argv += ['-isystem', str(storage_include)]
    entry_source = component_entry_source(args.component)
    destination = run / (args.component + '.o')
    if storage_include:
        argv += ['-include', str(storage_include / 'sys/cdefs.h')]
    argv += ['-include', 'meta_features.h', '-MD', '-MF', str(run / 'headers.d'),
             '-c', str(staged / entry_source), '-o', str(destination)]
    macros = run_command(argv[:argv.index('-MD')] + ['-dM', '-E',
                         str(staged / entry_source)], run,
                         'effective-config', manifest).stdout
    effective = effective_configuration(macros)
    expected_s2r = '0' if args.board_profile == 'y35a-a53' else '1'
    if effective['WITH_CLASSIC_S2R'] != expected_s2r:
        raise ValueError(f'profile {args.board_profile} requires WITH_CLASSIC_S2R={expected_s2r}')
    manifest['configuration'] = {
        'profile': args.board_profile, 'native_configuration': CONFIG,
        'native_config_defines': flags, 'effective_macros': effective,
        'component_defines': component_defines(args.component),
        'explicit_other_cflags': ['-DXNU_Y35A_A53=1'] if args.board_profile == 'y35a-a53' else [],
        'deployment_scope': 'Driver/probe/personality objects only; excludes kernel dependencies such as libcc_kext.',
        'integration_policy': 'Rebuild after native headers or configuration change; symbol names alone do not establish ABI compatibility.'}
    manifest['staged_source_sha256'] = sha256(staged / entry_source)
    result = run_command(argv, run, 'compile', manifest, check=False)
    if result.returncode:
        manifest['compiler_errors'] = [line for line in result.stderr.splitlines() if 'error:' in line]
        raise RuntimeError(f'compile failed ({result.returncode}); see {run / "compile.log"}')
    dependencies = audit_dependencies((run / 'headers.d').read_text(), run)
    save(run / 'consumed-inputs.json', dependencies)
    manifest['consumed_input_count'] = len(dependencies)
    manifest['consumed_inputs_sha256'] = sha256(run / 'consumed-inputs.json')
    manifest['object'] = {'path': str(destination), 'sha256': sha256(destination),
                          **audit_object(destination.read_bytes())}
    if args.component in ('QcomSdcc', 'QcomSdcard'):
        support_sources = [run / 'driver/IOStorageFamily' / name
                           for name in IOSTORAGE_FAMILY_SOURCE_FILES]
        support_objects = []
        family_dependencies = []
        family_defined = set()
        for support_source in support_sources:
            stem = support_source.stem
            support_object = run / f'{stem}.o'
            depfile = run / f'iostorage-family-{stem}.d'
            # IOStorageFamily-191 is an older Apple source snapshot. Its
            # successful R156 object run compiled these support sources with
            # the embedded target macro enabled and without the driver's
            # -Werror policy; keep strict warnings on NativeSdcc itself while
            # preserving the historical base-family compile contract.
            support_base = [flag for flag in argv[:argv.index('-MD')]
                            if flag not in ('-Werror', '-std=gnu++17')]
            support_argv = support_base + [
                '-std=gnu++14',
                '-DTARGET_OS_EMBEDDED=1',
                '-Wno-deprecated-declarations', '-MD', '-MF', str(depfile),
                '-c', str(support_source), '-o', str(support_object)]
            result = run_command(support_argv, run, f'iostorage-family-{stem}-compile', manifest,
                                 check=False)
            if result.returncode:
                raise RuntimeError(f'{support_source.name} base compile failed; see {run / ("iostorage-family-" + stem + "-compile.log")}')
            family_dependencies.extend(audit_dependencies(depfile.read_text(), run))
            support_objects.append(support_object)
            family_defined.update(run_command(['xcrun', 'nm', '-g', '-U', '-j', str(support_object)],
                                              run, f'iostorage-family-{stem}-symbols', manifest).stdout.splitlines())
        save(run / 'iostorage-family-consumed-inputs.json', family_dependencies)
        driver_undefined = set(run_command(['xcrun', 'nm', '-u', '-j', str(destination)],
                                           run, 'qcom-sdcc-undefined-symbols', manifest).stdout.splitlines())
        class_imports = {symbol for symbol in driver_undefined if 'IOBlockStorageDevice' in symbol}
        manifest['iostorage_base_object'] = {
            'sources': [str(path) for path in support_sources],
            'objects': [{'path': str(path), 'sha256': sha256(path),
                         **audit_object(path.read_bytes())} for path in support_objects],
            'external_header_tag': IOSTORAGE_FAMILY_TAG,
            'component_symbol_import_count': len(class_imports),
            'resolved_by_base_object': sorted(class_imports & family_defined),
            'unresolved_after_combining_objects': sorted(class_imports - family_defined),
            'note': 'Object-level IOStorageFamily source closure only; no KEXT link or kernel/prelink was attempted.'}
        combined_object = run / f'IOStorageFamily-{args.component}.o'
        run_command(['xcrun', 'ld', '-r', '-arch', 'arm64', '-o', str(combined_object),
                     *[str(path) for path in [*support_objects, destination]]],
                    run, 'iostorage-family-qcom-combine', manifest)
        combined_undefined = sorted(set(run_command(
            ['xcrun', 'nm', '-u', '-j', str(combined_object)], run,
            'iostorage-family-qcom-undefined-symbols', manifest).stdout.splitlines()))
        manifest['combined_component_object'] = {
            'path': str(combined_object), 'sha256': sha256(combined_object),
            **audit_object(combined_object.read_bytes()),
            'undefined_external_symbols': combined_undefined,
            'note': 'Relocatable object combination only. It is not a KEXT bundle, kernel link, prelink, package, or device artifact.'}
    if args.check_personalities:
        table = run / 'personality/iokit/KernelConfigTables.cpp'
        snapshot(source / 'iokit/KernelConfigTables.cpp', table, inputs)
        personality_patch = component_personality_patch(args.component)
        snapshot(personality_patch, run / 'inputs' / personality_patch.name, inputs)
        for operation in ('--check', None):
            command = ['git', 'apply', '--directory=personality']
            if operation:
                command.append(operation)
            command.append(str(run / 'inputs' / personality_patch.name))
            run_command(command, run, 'personality-patch-check' if operation else 'personality-patch-apply', manifest)
        table_object = run / 'KernelConfigTables.o'
        run_command(argv[:argv.index('-MD')] + ['-c', str(table), '-o', str(table_object)],
                    run, 'personality-compile', manifest)
        manifest['personality_check'] = {
            'patch_sha256': sha256(personality_patch), 'source_sha256': sha256(table),
            'object_sha256': sha256(table_object), **audit_object(table_object.read_bytes()),
            'note': 'Independent patch application and object compile only; not linked or added to driver archive.'}
    probe = run / 'abi-probe.cpp'
    snapshot(PATCH.parent / 'abi-probe.cpp', probe, inputs)
    save(run / 'inputs.json', inputs)
    probe_object = run / 'abi-probe.o'
    run_command(argv[:argv.index('-MD')] + ['-c', str(probe), '-o', str(probe_object)],
                run, 'abi-probe', manifest)
    manifest['abi_probe'] = {'path': str(probe_object), 'sha256': sha256(probe_object),
                             **audit_object(probe_object.read_bytes())}
    run_command(['xcrun', 'otool', '-s', '__TEXT', '__const', str(probe_object)],
                run, 'abi-probe-layout', manifest)
    symbols = run_command(['xcrun', 'nm', '-u', '-j', str(destination)], run,
                          'undefined-symbols', manifest).stdout.splitlines()
    manifest['undefined_symbols'] = sorted(set(symbols))
    run_command(['xcrun', 'nm', '-g', str(destination)], run, 'global-symbols', manifest)
    if args.boot_cpu_only:
        forbidden = {'_ml_get_cluster_number', '_ml_get_boot_cluster_type', '_processor_start',
                     '_kernel_thread_start', '_LowResetVectorBase', '_ResetHandlerData', '_const_boot_args'}
        if forbidden.intersection(symbols):
            raise RuntimeError('boot-only object retains unsupported modern/SMP references')
        disassembly = run_command(['xcrun', 'otool', '-tvV', str(destination)], run,
                                  'disassembly', manifest).stdout
        if re.search(r'\t(?:smc|hvc)\s', disassembly):
            raise RuntimeError('boot-only object contains a PSCI call instruction')
        manifest['boot_only_object_audit'] = {
            'unsupported_symbol_references': [], 'smc_hvc_instructions': 0,
            'note': 'Static object inspection only; no IRQ, timer, or CPU execution test.'}
    archive = run / ('lib' + args.component + '.a')
    members = archive_members(args.component, run, destination)
    # The driver object alone only proves source-level symbol closure. The
    # userdata-window archive must carry the combined IOStorageFamily base
    # object too, so -force_load provides IOBlockStorageDevice's implementation.
    run_command(['xcrun', 'ar', 'rcs', str(archive),
                 *[str(path) for path in members]], run, 'archive', manifest)
    manifest['archive'] = {
        'path': str(archive),
        'sha256': sha256(archive),
        'members': [str(path) for path in members],
        'force_load': component_integration(args.component)['force_load'],
    }
    manifest['integration'] = component_integration(args.component)
    if args.kernel:
        kernel = args.kernel.resolve(strict=True)
        before = sha256(kernel)
        defined = run_command(['xcrun', 'nm', '-g', '-U', '-j', str(kernel)], run,
                              'kernel-symbols', manifest).stdout.splitlines()
        if sha256(kernel) != before:
            raise RuntimeError('kernel changed during symbol inventory')
        manifest['kernel_symbol_inventory'] = {
            'path': str(kernel), 'sha256': before,
            'missing_external_symbols': sorted(set(symbols) - set(defined)),
            'note': 'Name availability only; not a link, vtable, KPI export, or runtime validation.'}
        if args.component == 'QcomSdcc':
            combined_undefined = set(manifest['combined_component_object']['undefined_external_symbols'])
            manifest['combined_component_object']['kernel_symbol_names_available'] = sorted(
                combined_undefined & set(defined))
            manifest['combined_component_object']['kernel_symbol_names_missing'] = sorted(
                combined_undefined - set(defined))
    manifest['status'] = 'object-compiled'
    manifest['snapshot_finished_utc'] = datetime.now(timezone.utc).isoformat()
    manifest['inputs_sha256'] = sha256(run / 'inputs.json')
    changed = changed_inputs(inputs)
    if changed:
        raise RuntimeError('inputs changed during build; rebuild required: ' + ', '.join(changed))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native-build', type=Path, default=DEFAULT_BUILD)
    parser.add_argument('--component', choices=tuple(COMPONENT_SOURCES), default='ArmDTPlatform')
    parser.add_argument('--run-root', type=Path)
    parser.add_argument('--clang', help='Explicit local clang++ path')
    parser.add_argument('--board-profile', choices=('legacy-t7001', 'y35a-a53'), default='legacy-t7001',
                        help='y35a-a53 adds R75 OTHER_CFLAGS macro and requires classic S2R disabled')
    parser.add_argument('--verify-inputs', type=Path,
                        help='Read-only freshness check of a completed run; does not authorize linking')
    parser.add_argument('--kernel', type=Path, help='Read-only kernel symbol comparison')
    parser.add_argument('--iostorage-source', type=Path, default=DEFAULT_IOSTORAGE_SOURCE,
                        help='Pinned Apple IOStorageFamily source snapshot for QcomSdcc')
    parser.add_argument('--baseline', action='store_true', help='Compile original source without compatibility patch')
    parser.add_argument('--boot-cpu-only', action='store_true',
                        help='Explicit ArmCpu 4903 single boot CPU bring-up; requires cpus=1 at runtime')
    parser.add_argument('--check-personalities', action='store_true',
                        help='Apply personality patch and compile KernelConfigTables only in the run snapshot')
    args = parser.parse_args(argv)
    if args.verify_inputs:
        try:
            return verify_inputs(args.verify_inputs.resolve(strict=True))
        except (ValueError, KeyError, OSError) as error:
            print(str(error))
            return 1
    if args.component == 'ArmCpu' and not args.baseline and not args.boot_cpu_only:
        parser.error('ArmCpu adaptation requires --boot-cpu-only; SMP is unsupported')
    if args.boot_cpu_only and (args.component != 'ArmCpu' or args.baseline):
        parser.error('--boot-cpu-only requires ArmCpu without --baseline')
    try:
        run = allocate_run(args.run_root, [ROOT, DEFAULT_BUILD, args.native_build])
    except (ValueError, OSError) as error:
        print(str(error))
        return 1
    (run / 'tmp').mkdir()
    manifest = {'schema': 2, 'status': 'preparing', 'component': args.component,
                'baseline': args.baseline, 'run_root': str(run), 'steps': [],
                'scope': 'Compile only. No kernel link, no device verification, no iOS runtime claim.'}
    if args.component == 'ArmCpu':
        manifest.update({'cpu_mode': 'original-source-diagnostic' if args.baseline else 'boot-cpu-only',
                         'maximum_supported_cpus': None if args.baseline else 1,
                         'smp_supported': False,
                         'required_boot_args': [] if args.baseline else ['cpus=1'],
                         'secondary_cpu_policy': 'Reject nonboot CPU nubs; startCPU returns KERN_NOT_SUPPORTED.',
                         'unload_supported': False})
    save(run / 'manifest.json', manifest)
    print(f'Run directory: {run}', flush=True)
    try:
        build(args, run, manifest)
    except (ValueError, OSError, RuntimeError, subprocess.SubprocessError) as error:
        manifest['status'] = 'failed'
        manifest['failure'] = str(error)
        print(str(error), flush=True)
        return 1
    finally:
        save(run / 'manifest.json', manifest)
    print(f'{args.component}: arm64 iOS 12.4 object verified; {run / "manifest.json"}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
