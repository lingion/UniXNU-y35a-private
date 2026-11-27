#!/usr/bin/env python3
"""Prepare the exact CI-local inputs required by the XNU 4903 native runner.

This script only runs inside the GitHub Actions macOS job. It creates a fresh
fakeroot, SDK overlay, and xcrun wrapper under the supplied run root, records
the exact source revisions and commands, and refuses to use an existing output.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


PROFILE_SOURCES = (
    "InstrProfiling", "InstrProfilingBuffer", "InstrProfilingPlatformDarwin",
    "InstrProfilingWriter", "InstrProfilingInternal", "InstrProfilingVersionVar",
)
LLVM_COMMIT = "58c46bae21181fb4240cf964461bea738d96d50e"
LIBC_COMMIT = "899a3b2d52d95d75e05fb286a5e64975ec3de757"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def tree_sha256(path: Path) -> str:
    root = path.resolve(strict=True)
    if not root.is_dir():
        raise SystemExit(f"native input is not a directory: {root}")
    digest = hashlib.sha256()
    for item in sorted(root.rglob("*"), key=lambda value: value.relative_to(root).as_posix()):
        relative = item.relative_to(root).as_posix().encode("utf-8")
        mode = item.lstat().st_mode
        kind = b"L" if item.is_symlink() else b"D" if item.is_dir() else b"F"
        digest.update(kind)
        digest.update(len(relative).to_bytes(4, "big"))
        digest.update(relative)
        digest.update((mode & 0o777).to_bytes(4, "big"))
        if item.is_symlink():
            digest.update(os.readlink(item).encode("utf-8"))
        elif item.is_file():
            digest.update(bytes.fromhex(sha256(item)))
        elif not item.is_dir():
            raise SystemExit(f"unsupported native input entry: {item}")
    return digest.hexdigest()


def run(command: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None) -> None:
    print("$", " ".join(str(part) for part in command), flush=True)
    subprocess.run(command, cwd=cwd, env=env, check=True)


@contextmanager
def temporary_xnu_host_tool_patch(xnu_source: Path, patch_tool: Path):
    host_tool = xnu_source / "bsd/kern/makekdebugevents.py"
    original = host_tool.read_bytes()
    try:
        run([sys.executable, str(patch_tool), "--xnu-source", str(xnu_source)])
        yield
    finally:
        if host_tool.is_file() and host_tool.read_bytes() != original:
            host_tool.write_bytes(original)


def copy_tree(source: Path, destination: Path) -> None:
    if destination.exists() or destination.is_symlink():
        raise SystemExit(f"refusing to overwrite: {destination}")
    shutil.copytree(source, destination, symlinks=True, copy_function=shutil.copy2)


def copy_dir_contents(source: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for item in source.iterdir():
        target = destination / item.name
        if target.exists() or target.is_symlink():
            if target.is_dir() and not target.is_symlink():
                shutil.rmtree(target)
            else:
                target.unlink()
        if item.is_dir() and not item.is_symlink():
            shutil.copytree(item, target, symlinks=True, copy_function=shutil.copy2)
        else:
            shutil.copy2(item, target, follow_symlinks=False)


def preprocess_dispatch_headers(libdispatch: Path, fakeroot: Path, clang: str) -> list[str]:
    output = fakeroot / "usr/local/include/os"
    output.mkdir(parents=True, exist_ok=True)
    unifdef = shutil.which("unifdef")
    commands: list[str] = []
    for header in sorted((libdispatch / "os").glob("*.h")):
        target = output / header.name
        if unifdef:
            command = [unifdef, "-DKERNEL=1", "-DOS_FIREHOSE_SPI=1",
                       "-DOS_VOUCHER_ACTIVITY_SPI_TYPES=1", "-UOS_VOUCHER_ACTIVITY_SPI",
                       str(header)]
            result = subprocess.run(command, capture_output=True, check=False)
            if result.returncode not in (0, 1):
                raise subprocess.CalledProcessError(result.returncode, command,
                                                    output=result.stdout, stderr=result.stderr)
            target.write_bytes(result.stdout)
            commands.append(" ".join(command))
        else:
            command = [clang, "-E", "-P", "-DKERNEL=1", "-DOS_FIREHOSE_SPI=1",
                       "-DOS_VOUCHER_ACTIVITY_SPI_TYPES=1", "-UOS_VOUCHER_ACTIVITY_SPI",
                       "-I", str(libdispatch), str(header)]
            result = subprocess.run(command, capture_output=True, check=True)
            target.write_bytes(result.stdout)
            commands.append(" ".join(command))
    if not commands:
        raise SystemExit(f"libdispatch has no os headers: {libdispatch}")
    return commands


def build_cc_kext(xnu: Path, llvm: Path, libc: Path, fakeroot: Path,
                  iphoneos_sdk: Path, clang: str) -> list[str]:
    output = fakeroot / "usr/local/lib/kernel/libcc_kext.a"
    objects_root = fakeroot / ".ci-cc-kext-objects"
    objects_root.mkdir(parents=True, exist_ok=True)
    runtime = llvm / "compiler-rt"
    commands: list[str] = []
    objects: list[Path] = []
    for name in PROFILE_SOURCES:
        obj = objects_root / f"{name}.o"
        command = [clang, "-target", "arm64-apple-ios12.4", "-arch", "arm64",
                   "-isysroot", str(fakeroot), "-mkernel", "-DKERNEL_USE", "-O3", "-fPIC", "-w",
                   "-I", str(runtime / "include"),
                   "-I", str(iphoneos_sdk / "usr/include"),
                   "-I", str(fakeroot / "System/Library/Frameworks/Kernel.framework/Headers"),
                   "-idirafter", str(libc / "include"), "-idirafter", str(xnu / "libsyscall/wrappers"),
                   "-c", str(runtime / f"lib/profile/{name}.c"), "-o", str(obj)]
        run(command)
        commands.append(" ".join(command))
        objects.append(obj)
    output.parent.mkdir(parents=True, exist_ok=True)
    command = ["/usr/bin/xcrun", "libtool", "-static", "-o", str(output), *map(str, objects)]
    run(command)
    commands.append(" ".join(command))
    return commands


def build_firehose(xnu: Path, libdispatch: Path, libplatform: Path,
                   fakeroot: Path, clang: str) -> list[str]:
    objects = fakeroot / ".ci-firehose-objects"
    objects.mkdir(parents=True, exist_ok=True)
    private_header = fakeroot / "usr/local/include/kernel/os/firehose_buffer_private.h"
    private_header.parent.mkdir(parents=True, exist_ok=True)
    commands = preprocess_dispatch_headers(libdispatch, fakeroot, clang)
    atomic_source = libplatform / "private/os/internal/atomic.h"
    lock_source = libplatform / "private/os/lock_private.h"
    atomic_target = fakeroot / "usr/local/include/os/internal/atomic.h"
    lock_target = fakeroot / "usr/local/include/os/lock_private.h"
    if not atomic_source.is_file() or not lock_source.is_file():
        raise SystemExit(
            f"libplatform atomic/lock private headers missing: {atomic_source}, {lock_source}"
        )
    atomic_target.parent.mkdir(parents=True, exist_ok=True)
    lock_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(atomic_source, atomic_target)
    shutil.copy2(lock_source, lock_target)
    firehose_source = libdispatch / "src/firehose/firehose_buffer.c"
    firehose_text = firehose_source.read_text()
    if "#include <os/atomic_private.h>" in firehose_text:
        atomic_header = fakeroot / "usr/local/include/kernel/os/atomic_private.h"
        atomic_header.parent.mkdir(parents=True, exist_ok=True)
        atomic_header.write_text(
            "#ifndef UNIXNU_LIBDISPATCH_ATOMIC_PRIVATE_COMPAT_H\n"
            "#define UNIXNU_LIBDISPATCH_ATOMIC_PRIVATE_COMPAT_H\n"
            "#define __OS_EXPOSE_INTERNALS_INDIRECT__ 1\n"
            "#include <internal/atomic.h>\n"
            "#endif\n"
        )
    elif "#include <internal/atomic.h>" in firehose_text:
        if not (fakeroot / "usr/local/include/os/internal/atomic.h").is_file():
            raise SystemExit("libplatform internal atomic header was not staged")
    else:
        raise SystemExit(f"unsupported firehose atomic include contract: {firehose_source}")
    source = firehose_source
    obj = objects / "firehose_buffer.o"
    command = [clang, "-target", "arm64-apple-ios12.4", "-std=gnu11", "-Os", "-g",
               "-mkernel", "-nostdinc", "-Wno-packed", "-DKERNEL=1",
               "-DDISPATCH_USE_DTRACE=0", "-DOS_ATOMIC_CONFIG_MEMORY_ORDER_DEPENDENCY=1",
               "-DOS_ATOMIC_CONFIG_STARVATION_FREE_ONLY=0", "-I", str(libdispatch),
               "-I", str(fakeroot / "System/Library/Frameworks/Kernel.framework/PrivateHeaders"),
               "-I", str(fakeroot / "System/Library/Frameworks/Kernel.framework/Headers"),
               "-I", str(fakeroot / "usr/local/include/os"),
               "-I", str(fakeroot / "usr/local/include/firehose"),
               "-I", str(fakeroot / "usr/local/include/kernel"),
               "-I", str(fakeroot / "usr/include"), "-I", str(fakeroot / "usr/local/include"),
               "-I", str(xnu / "EXTERNAL_HEADERS"), "-c", str(source), "-o", str(obj)]
    run(command)
    commands.append(" ".join(command))
    archive = fakeroot / "usr/local/lib/kernel/libfirehose_kernel.a"
    archive.parent.mkdir(parents=True, exist_ok=True)
    command = ["/usr/bin/xcrun", "libtool", "-static", "-o", str(archive), str(obj)]
    run(command)
    commands.append(" ".join(command))
    raw_header = libdispatch / "os/firehose_buffer_private.h"
    if raw_header.is_file():
        shutil.copy2(raw_header, private_header)
    else:
        raise SystemExit(f"missing firehose private header: {raw_header}")
    return commands


def make_overlay(iphoneos_sdk: Path, fakeroot: Path, overlay: Path) -> None:
    overlay.mkdir(parents=True)
    settings = iphoneos_sdk / "SDKSettings.plist"
    if not settings.is_file():
        raise SystemExit(f"missing SDKSettings.plist: {settings}")
    shutil.copy2(settings, overlay / "SDKSettings.plist")
    system = iphoneos_sdk / "System"
    if system.is_dir():
        (overlay / "System").symlink_to(system, target_is_directory=True)
    usr = overlay / "usr"
    usr.mkdir()
    for name in ("bin", "include", "lib", "libexec", "share"):
        source = iphoneos_sdk / "usr" / name
        if source.exists():
            (usr / name).symlink_to(source, target_is_directory=True)
    copy_dir_contents(fakeroot / "usr/local", usr / "local")


def copy_sdk_public_headers(iphoneos_sdk: Path, fakeroot: Path) -> list[str]:
    source = iphoneos_sdk / "usr/include"
    destination = fakeroot / "usr/include"
    destination.mkdir(parents=True, exist_ok=True)
    copied = []
    for header in sorted(source.glob("Availability*.h")):
        target = destination / header.name
        shutil.copy2(header, target)
        copied.append(header.name)
    target_conditions = source / "TargetConditionals.h"
    if target_conditions.is_file():
        shutil.copy2(target_conditions, destination / target_conditions.name)
        copied.append(target_conditions.name)
    if "Availability.h" not in copied:
        raise SystemExit(f"iPhoneOS SDK has no Availability.h: {source}")
    return copied


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--xnu-source", type=Path, required=True)
    parser.add_argument("--availability-source", type=Path, required=True)
    parser.add_argument("--libdispatch-source", type=Path, required=True)
    parser.add_argument("--libplatform-source", type=Path, required=True)
    parser.add_argument("--llvm-source", type=Path, required=True)
    parser.add_argument("--libc-source", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--developer-dir", type=Path, required=True)
    parser.add_argument("--iphoneos-sdk", type=Path, required=True)
    parser.add_argument("--macosx-sdk", type=Path, required=True)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--jobs", type=int, default=4)
    args = parser.parse_args()

    inputs = [args.xnu_source, args.availability_source, args.libdispatch_source,
              args.libplatform_source,
              args.llvm_source, args.libc_source, args.repo_root, args.developer_dir,
              args.iphoneos_sdk, args.macosx_sdk]
    for path in inputs:
        if not path.exists():
            raise SystemExit(f"missing input: {path}")
    root = args.run_root.resolve()
    if root.exists():
        raise SystemExit(f"refusing to overwrite native input root: {root}")
    root.mkdir(parents=True)
    fakeroot = root / "fakeroot"
    overlay = root / "sdk-overlay"
    wrapper = root / "compat/bin/xcrun"
    availability_dst = root / "availability-dst"
    availability_obj = root / "availability-obj"
    availability_sym = root / "availability-sym"
    fakeroot.mkdir()

    header_source = args.xnu_source
    patch_tool = args.repo_root / "scripts/ci/patch_xnu_host_tools.py"
    availability_pl = availability_dst / "usr/local/libexec/availability.pl"
    run(["make", "-C", str(args.availability_source), "install",
         f"SRCROOT={args.availability_source}", f"OBJROOT={availability_obj}",
         f"SYMROOT={availability_sym}", f"DSTROOT={availability_dst}",
         f"CMAKE={shutil.which('cmake') or 'cmake'}", f"NINJA={shutil.which('ninja') or 'ninja'}"])
    if not availability_pl.is_file():
        raise SystemExit(f"AvailabilityVersions did not produce {availability_pl}")
    copy_dir_contents(availability_dst / "usr/local", fakeroot / "usr/local")

    local_patch = args.repo_root / "patches/xnu/local-availability.patch"
    run(["git", "-C", str(header_source), "apply", "--check", str(local_patch)])
    run(["git", "-C", str(header_source), "apply", str(local_patch)])
    try:
        xcode = args.developer_dir
        toolchain = xcode / "Toolchains/XcodeDefault.xctoolchain/usr"
        make = xcode / "usr/bin/make"
        clang = str(toolchain / "bin/clang")
        with temporary_xnu_host_tool_patch(header_source, patch_tool):
            run([make, f"-j{args.jobs}", "-C", str(header_source), "installhdrs",
                 f"SDKROOT={args.macosx_sdk}", "ARCH_CONFIGS=ARM64", "KERNEL_CONFIGS=DEVELOPMENT",
                 "MACHINE_CONFIGS=T7001", "ARCH_STRING_FOR_CURRENT_MACHINE_CONFIG=arm64",
                 "SDKVERSION=12.4", f"XNU_AVAILABILITY_PL={availability_pl}",
                 "CTFCONVERT=/usr/bin/true", "CTFMERGE=/usr/bin/true", "CTFINSERT=/usr/bin/true",
                 "EMBEDDED_DEVICE_MAP=/usr/bin/true", "TIGHTBEAMC=tightbeamc-not-supported",
                 f"OBJROOT={root / 'xnu-obj'}", f"DSTROOT={fakeroot}", f"MAKEJOBS=-j{args.jobs}"])
        target_conditions = args.repo_root / "scripts/linux/TargetConditionals.h"
        target = fakeroot / "usr/include/TargetConditionals.h"
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(target_conditions, target)
        copied_headers = copy_sdk_public_headers(args.iphoneos_sdk, fakeroot)
        build_cc_kext(header_source, args.llvm_source, args.libc_source, fakeroot,
                      args.iphoneos_sdk, clang)
        build_firehose(header_source, args.libdispatch_source, args.libplatform_source,
                       fakeroot, clang)
        make_overlay(args.iphoneos_sdk, fakeroot, overlay)
    finally:
        run(["git", "-C", str(header_source), "apply", "--reverse", str(local_patch)])

    wrapper.parent.mkdir(parents=True)
    xcrun_body = (args.repo_root / "scripts/linux/xcrun").read_text()
    wrapper.write_text(
        "#!/bin/bash\nset -u\n"
        f'export UNIXNU_SDKROOT="{overlay}"\n'
        'export UNIXNU_SDK_VERSION="18.5"\n'
        f'export UNIXNU_PLATFORM_PATH="{fakeroot / "Platforms/iPhoneOS.platform"}"\n'
        f'export XNU_TOOLCHAIN_BIN="{args.developer_dir / "Toolchains/XcodeDefault.xctoolchain/usr/bin"} {args.developer_dir / "usr/bin"}"\n'
        + xcrun_body.split("set -u", 1)[1]
    )
    wrapper.chmod(0o755)
    manifest = {
        "schema": 1,
        "source": {"xnu_commit": "494ffe1c29d37ca720c37328feb83069c9641b67",
                    "availability_tag": "AvailabilityVersions-33.200.7",
                    "libdispatch_tag": "libdispatch-1477.100.9",
                    "llvm_commit": LLVM_COMMIT, "libc_commit": LIBC_COMMIT},
        "paths": {"fakeroot": str(fakeroot), "sdk_overlay": str(overlay), "xcrun_wrapper": str(wrapper)},
        "trees": {"fakeroot_sha256": tree_sha256(fakeroot), "sdk_overlay_sha256": tree_sha256(overlay),
                  "xcrun_wrapper_sha256": sha256(wrapper)},
        "sdk_public_headers": copied_headers,
        "local_build_allowed": False,
    }
    (root / "native-inputs-manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
