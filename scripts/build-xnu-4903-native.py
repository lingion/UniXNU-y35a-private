#!/usr/bin/env python3
"""Build a prepared XNU 4903 diagnostic tree with the local Xcode toolchain.

This Y35A-specific runner is intentionally isolated from the Linux/container
builder. It always creates a new run directory, preserves all failed runs, and
records source, patch, SDK, fakeroot, command, environment, and artifact hashes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
XNU_TAG = "xnu-4903.270.47"
XNU_COMMIT = "494ffe1c29d37ca720c37328feb83069c9641b67"
KERNEL_TEXT_BASE = 0xFFFF_FFF0_0700_4000
MACHO_MAGIC_64 = 0xFEEDFACF
CPU_TYPE_ARM64 = 0x0100000C
MH_EXECUTE = 2
LC_SEGMENT_64 = 0x19

EVIDENCE = ROOT / "evidence/y35a-20261102/boot3-20261106/phase-r68e7-store-boundary-v5-20261111"
DEFAULT_SOURCE = ROOT / "upstream-refresh/2026-11-11/sources/xnu-ios12/repo"
DEFAULT_SOURCE_DIFF = EVIDENCE / "kernel/source-worktree-diff.patch"
DEFAULT_SOURCE_PROVENANCE = EVIDENCE / "kernel/build-input-provenance.json"
DEFAULT_NATIVE_ROOT = Path("/tmp/xnu4903-r68e7-v5-native-20261111")
DEFAULT_FAKEROOT = DEFAULT_NATIVE_ROOT / "fakeroot"
DEFAULT_SDK_OVERLAY = DEFAULT_NATIVE_ROOT / "compat/overlay-iPhoneOS18.5.sdk"
DEFAULT_XCRUN_WRAPPER = DEFAULT_NATIVE_ROOT / "compat/bin/xcrun-overlay"
DRIVER_INTEGRATION_ROLE = "userdata-window"
DRIVER_REQUIRED_SYMBOLS = {
    "_native_sdcc_probe_bound",
    "_native_sdcc_started",
    "_native_sdcc_store_attached",
}
DRIVER_REQUIRED_SYMBOLS_BY_ROLE = {
    "userdata-window": DRIVER_REQUIRED_SYMBOLS,
    "tf-storage": {
        "_native_sdcard_probe_bound",
        "_native_sdcard_started",
        "_native_sdcard_ready",
    },
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def tree_sha256(path: Path) -> str:
    """Hash relative names, file bytes, symlink targets, and executable modes."""
    root = path.resolve(strict=True)
    if not root.is_dir():
        raise SystemExit(f"input tree is not a directory: {root}")
    digest = hashlib.sha256()
    for item in sorted(root.rglob("*"), key=lambda value: value.relative_to(root).as_posix()):
        relative = item.relative_to(root).as_posix().encode("utf-8")
        mode = item.lstat().st_mode
        kind = b"L" if item.is_symlink() else b"D" if item.is_dir() else b"F"
        digest.update(kind)
        digest.update(struct.pack(">I", len(relative)))
        digest.update(relative)
        digest.update(struct.pack(">I", mode & 0o777))
        if item.is_symlink():
            digest.update(os.readlink(item).encode("utf-8"))
        elif item.is_file():
            digest.update(bytes.fromhex(sha256_file(item)))
        elif not item.is_dir():
            raise SystemExit(f"unsupported filesystem entry in build input: {item}")
    return digest.hexdigest()


def _git_output(source: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(source), *args], capture_output=True, text=True, check=False
    )
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip()
        raise SystemExit(f"git {' '.join(args)} failed for {source}: {detail}")
    return result.stdout.strip()


def validate_source_tree(
    source: Path, *, expected_tag: str = XNU_TAG, expected_commit: str = XNU_COMMIT
) -> dict[str, str]:
    source = source.resolve(strict=True)
    if not (source / "makedefs/MakeInc.def").is_file():
        raise SystemExit(f"not an XNU source tree: {source}")
    commit = _git_output(source, "rev-parse", "HEAD")
    tag = _git_output(source, "describe", "--tags", "--exact-match", "HEAD")
    status = _git_output(source, "status", "--porcelain=v1", "--untracked-files=all")
    if tag != expected_tag or commit != expected_commit:
        raise SystemExit(
            f"source must be clean {expected_tag} ({expected_commit}); found {tag} ({commit})"
        )
    if status:
        raise SystemExit(f"source tree is not clean; refusing to snapshot it: {source}")
    return {"tag": tag, "commit": commit, "status": "clean"}


def allocate_run_root(
    *, explicit: Path | None = None, parent: Path | None = None
) -> Path:
    """Create a new output directory; never reuse, truncate, or delete one."""
    if explicit is not None:
        requested = Path(explicit).expanduser()
        if requested.exists() or requested.is_symlink():
            raise SystemExit(f"run root already exists; refusing to reuse it: {requested}")
        resolved = requested.resolve(strict=False)
        try:
            resolved.relative_to(ROOT.resolve())
        except ValueError:
            pass
        else:
            raise SystemExit(f"run root must be outside the repository: {resolved}")
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.mkdir()
        return resolved

    parent = Path(parent or "/tmp").expanduser().resolve(strict=True)
    try:
        parent.relative_to(ROOT.resolve())
    except ValueError:
        pass
    else:
        raise SystemExit(f"run parent must be outside the repository: {parent}")
    parent.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix="xnu4903-native-", dir=parent))


def stage_source_tree(source: Path, destination: Path, patches: list[Path], *, on_progress=None) -> str:
    """Copy the pinned clean tree, then apply patches only to the private copy."""
    source = source.resolve(strict=True)
    destination = Path(destination)
    if destination.exists() or destination.is_symlink():
        raise SystemExit(f"staged source already exists; refusing to overwrite: {destination}")

    def report(event: dict[str, object]) -> None:
        if on_progress is not None:
            on_progress(event)

    report({"phase": "source-copy", "status": "running", "source": str(source),
            "destination": str(destination)})
    try:
        shutil.copytree(source, destination, symlinks=True, copy_function=shutil.copy2)
    except BaseException as error:
        partial_digest = None
        if destination.exists():
            try:
                partial_digest = tree_sha256(destination)
            except (OSError, SystemExit):
                pass
        report({"phase": "source-copy", "status": "failed", "error_type": type(error).__name__,
                "error": str(error), "partial_tree_sha256": partial_digest})
        raise
    report({"phase": "source-copy", "status": "copied",
            "staged_tree_sha256": tree_sha256(destination)})
    applied = []
    for patch in patches:
        patch = Path(patch).resolve(strict=True)
        if not patch.is_file():
            raise SystemExit(f"source patch is not a file: {patch}")
        try:
            for operation in ("--check", ""):
                command = ["git", "-C", str(destination), "apply"]
                if operation:
                    command.append(operation)
                command.extend(("--binary", str(patch)))
                result = subprocess.run(command, capture_output=True, text=True, check=False)
                if result.returncode:
                    detail = result.stderr.strip() or result.stdout.strip()
                    raise SystemExit(
                        f"git apply {patch.name} {operation or ''} failed: {detail}"
                    )
        except BaseException as error:
            partial_digest = None
            try:
                partial_digest = tree_sha256(destination)
            except (OSError, SystemExit):
                pass
            report({"phase": "source-patch", "status": "failed", "patch": str(patch),
                    "patch_sha256": sha256_file(patch), "error_type": type(error).__name__,
                    "error": str(error), "applied_patches": applied,
                    "partial_tree_sha256": partial_digest})
            raise
        patch_record = {"path": str(patch), "sha256": sha256_file(patch)}
        applied.append(patch_record)
        report({"phase": "source-patch", "status": "patch-applied",
                "patch": patch_record, "applied_patches": list(applied)})
    return tree_sha256(destination)


def patch_genassym_for_clang(source: Path) -> dict[str, str]:
    """Apply the proven 4903 genassym source fix to the staged XNU tree."""
    genassym = source / "osfmk/arm64/genassym.c"
    gen_text = genassym.read_text()
    old_forms = (r'.ascii \"%0\"" : : "n"', r'.ascii \"%0\"" : : "i"')
    replacement = r'.ascii \"#%0\"" : : "i"'
    if replacement not in gen_text:
        for old in old_forms:
            if old in gen_text:
                genassym.write_text(gen_text.replace(old, replacement))
                break
        else:
            raise SystemExit(f"{genassym}: unsupported DECLARE() form")
    return {"genassym": str(genassym.relative_to(source)), "status": "passed"}


def patch_monotonic_header(source: Path) -> dict[str, str]:
    """Guard ARM monotonic declarations when T7001 does not enable MT_CORE_NFIXED."""
    header = source / "osfmk/machine/monotonic.h"
    text = header.read_text()
    guard = "#if defined(MT_CORE_NFIXED)\n"
    if guard in text:
        return {"header": str(header.relative_to(source)), "status": "already-applied"}
    arch_end = "#error unsupported architecture\n#endif\n\n"
    body_start = "#include <stdatomic.h>\n#include <stdbool.h>\n#include <stdint.h>\n"
    body_end = "int mt_microstackshot_start_arch(uint64_t period);\n"
    for anchor in (arch_end, body_start, body_end):
        if anchor not in text:
            raise SystemExit(f"{header}: monotonic guard anchor missing: {anchor.splitlines()[0]}")
    text = text.replace(arch_end, arch_end + guard, 1)
    text = text.replace(body_end, body_end + "#endif /* defined(MT_CORE_NFIXED) */\n", 1)
    header.write_text(text)
    return {"header": str(header.relative_to(source)), "status": "patched"}

def make_step_command(
    target: str,
    *,
    run_root: Path,
    source: Path,
    fakeroot: Path,
    overlay: Path,
    make: Path,
    host_sdkroot: Path,
    toolchain: Path,
    memory_bytes: int,
    physical_cpu_count: int,
    logical_cpu_count: int,
    jobs: int,
    host_os_version: str,
    y35a_a53: bool = False,
    y35a_low_vector: bool = False,
    phase_a_amfi: bool = False,
    driver_archives: list[Path] | None = None,
) -> list[str]:
    if target not in ("installhdrs", "build"):
        raise ValueError(f"unsupported XNU make target: {target}")
    if jobs < 1:
        raise ValueError("jobs must be positive")
    other_cflags = ["-DXNU_NATIVE_EARLY_FAULT=1", "-DOS_FIREHOSE_SPI=1"]
    if y35a_a53:
        other_cflags.append("-DXNU_Y35A_A53=1")
    if y35a_low_vector:
        other_cflags.append("-DXNU_Y35A_LOW_VECTOR=1")
    if phase_a_amfi:
        other_cflags.append("-DXNU_Y35A_PHASE_A_AMFI=1")
    command = [
        str(make), f"-j{jobs}", "-C", str(source), target,
        f"SDKROOT={overlay}", f"SDKROOT_RESOLVED={overlay}",
        f"HOST_SDKROOT={host_sdkroot}", f"HOST_SDKROOT_RESOLVED={host_sdkroot}",
        "SDKVERSION=12.4", "PLATFORM=iPhoneOS", "ARCH_CONFIGS=ARM64",
        "MACHINE_CONFIGS=T7001", "KERNEL_CONFIGS=DEVELOPMENT",
        "ARCH_STRING_FOR_CURRENT_MACHINE_CONFIG=arm64",
        f"XCRUN={run_root / 'compat/bin/xcrun'}",
        "EMBEDDED_DEVICE_MAP=/usr/bin/true", "CTFCONVERT=/usr/bin/true",
        "CTFMERGE=/usr/bin/true", "CTFINSERT=/usr/bin/true",
        "TIGHTBEAMC=tightbeamc-not-supported",
        f"HOST_CC={toolchain / 'bin/clang'}",
        f"MIG={toolchain / 'bin/mig'}", f"MIGCOM={toolchain / 'libexec/migcom'}",
        f"HOST_CODESIGN_ALLOCATE={toolchain / 'bin/codesign_allocate'}",
        "HOST_CODESIGN=/usr/bin/codesign", f"HOST_OS_VERSION={host_os_version}",
        f"MEMORY_SIZE={memory_bytes}",
        f"SYSCTL_HW_PHYSICALCPU={physical_cpu_count}",
        f"SYSCTL_HW_LOGICALCPU={logical_cpu_count}",
        f"MAKEJOBS=--jobs={jobs}",
        f"OBJROOT={run_root / 'obj'}", f"SYMROOT={run_root / 'sym'}",
        f"DSTROOT={run_root / 'dst'}", "BUILD_DSYM=0", "BUILD_LTO=0",
        "BOUND_CHECKS=0", "BUILD_WERROR=0",
    ]
    if target == "build":
        force_loads = [
            f"-Wl,-force_load,{path}" for path in (driver_archives or [])
        ]
        command.extend((
            "OTHER_CFLAGS=" + " ".join(other_cflags),
            "RC_PROJECT_CONFIG=RELEASE_ARM64_T7001",
            "LD_KERNEL_LIBS=" + " ".join([
                f"-Wl,-force_load,{fakeroot / 'usr/local/lib/kernel/libcc_kext.a'}",
                *force_loads,
            ]),
        ))
    return command


def validate_driver_manifest(manifest_path: Path, archive_paths: list[Path]) -> dict:
    data = json.loads(manifest_path.read_text())
    integration = data.get("integration", {})
    role = integration.get("role")
    if role not in DRIVER_REQUIRED_SYMBOLS_BY_ROLE:
        raise SystemExit(
            f"unsupported driver manifest role {role!r}; "
            f"expected one of {sorted(DRIVER_REQUIRED_SYMBOLS_BY_ROLE)}"
        )
    if integration.get("force_load") is not True:
        raise SystemExit("driver manifest must require force_load=true")
    archive = data.get("archive", {})
    expected = archive.get("sha256")
    if not expected or len(archive_paths) != 1:
        raise SystemExit("driver manifest must bind exactly one archive")
    actual = sha256_file(archive_paths[0])
    if actual != expected:
        raise SystemExit(
            f"driver archive SHA-256 {actual} does not match manifest {expected}"
        )
    return data


def audit_driver_kernel(kernel: Path, manifest: dict) -> dict:
    """Prove the force-loaded driver symbols survived the link."""
    result = subprocess.run(
        ["xcrun", "nm", "-g", "-j", str(kernel)],
        capture_output=True, text=True, check=False,
    )
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip()
        raise SystemExit(f"kernel symbol inventory failed: {detail}")
    symbols = set(result.stdout.splitlines())
    role = manifest["integration"]["role"]
    required = DRIVER_REQUIRED_SYMBOLS_BY_ROLE.get(role)
    if required is None:
        raise SystemExit(f"unsupported driver integration role: {role!r}")
    missing = sorted(required - symbols)
    if missing:
        raise SystemExit(
            f"force-loaded {role} driver symbols missing from kernel: "
            + ", ".join(missing)
        )
    return {
        "role": role,
        "force_load": manifest["integration"]["force_load"],
        "required_symbols": sorted(required),
        "missing_symbols": missing,
        "status": "passed",
    }


def load_driver_integration(archive_paths: list[Path], manifest_path: Path | None) -> dict | None:
    if archive_paths and manifest_path is None:
        raise SystemExit("--driver-archive requires --driver-manifest")
    if manifest_path is not None and not archive_paths:
        raise SystemExit("--driver-manifest requires --driver-archive")
    if manifest_path is None:
        return None
    return validate_driver_manifest(manifest_path.resolve(strict=True), archive_paths)


def _capture(command: list[str], *, env: dict[str, str] | None = None) -> str:
    result = subprocess.run(command, capture_output=True, text=True, check=False, env=env)
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip()
        raise SystemExit(f"command failed: {' '.join(command)}: {detail}")
    return result.stdout.strip()


def _xcode_inputs(developer_dir: Path) -> dict[str, object]:
    developer_dir = developer_dir.resolve(strict=True)
    selected_env = os.environ.copy()
    selected_env["DEVELOPER_DIR"] = str(developer_dir)
    xcrun = Path("/usr/bin/xcrun")
    version_lines = _capture(
        [str(developer_dir / "usr/bin/xcodebuild"), "-version"],
        env=selected_env,
    ).splitlines()
    iphoneos = Path(_capture(
        [str(xcrun), "--sdk", "iphoneos", "--show-sdk-path"], env=selected_env))
    iphoneos_version = _capture(
        [str(xcrun), "--sdk", "iphoneos", "--show-sdk-version"], env=selected_env)
    macosx = Path(_capture(
        [str(xcrun), "--sdk", "macosx", "--show-sdk-path"], env=selected_env))
    if version_lines[:2] != ["Xcode 16.4", "Build version 16F6"]:
        raise SystemExit(f"expected Xcode 16.4 (16F6); found {version_lines}")
    if iphoneos_version != "18.5":
        raise SystemExit(f"expected iPhoneOS SDK 18.5; found {iphoneos_version}")
    toolchain = developer_dir / "Toolchains/XcodeDefault.xctoolchain/usr"
    required_tools = (
        developer_dir / "usr/bin/make", toolchain / "bin/clang", toolchain / "bin/clang++",
        toolchain / "bin/mig", toolchain / "libexec/migcom", toolchain / "bin/codesign_allocate",
    )
    missing = [str(path) for path in required_tools if not path.is_file()]
    if missing:
        raise SystemExit("Xcode toolchain is missing required files: " + ", ".join(missing))
    memory = int(_capture(["/usr/sbin/sysctl", "-n", "hw.memsize"]))
    physical = int(_capture(["/usr/sbin/sysctl", "-n", "hw.physicalcpu"]))
    logical = int(_capture(["/usr/sbin/sysctl", "-n", "hw.logicalcpu"]))
    host_version = _capture(["/usr/bin/sw_vers", "-productVersion"])
    return {
        "xcode_version": version_lines,
        "iphoneos_sdk": str(iphoneos),
        "iphoneos_sdk_version": iphoneos_version,
        "macosx_sdk": str(macosx),
        "developer_dir": str(developer_dir),
        "toolchain": str(toolchain),
        "memory_bytes": memory,
        "physical_cpu_count": physical,
        "logical_cpu_count": logical,
        "host_os_version": host_version,
    }


def _validate_build_inputs(fakeroot: Path, overlay: Path, xcrun_wrapper: Path) -> None:
    required = (
        fakeroot / "usr/include/sys/_symbol_aliasing.h",
        fakeroot / "usr/local/libexec/availability.pl",
        fakeroot / "usr/local/lib/kernel/libcc_kext.a",
        overlay / "SDKSettings.plist",
        overlay / "usr/local/libexec/availability.pl",
        overlay / "usr/local/lib/kernel/libfirehose_kernel.a",
        overlay / "usr/local/include/kernel/os/firehose_buffer_private.h",
        xcrun_wrapper,
    )
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise SystemExit("native build inputs are missing: " + ", ".join(missing))
    dangling = [str(path) for path in overlay.rglob("*")
                if path.is_symlink() and not path.exists()]
    if dangling:
        raise SystemExit("SDK overlay contains dangling symlinks: " + ", ".join(dangling))


def _copy_tree(source: Path, destination: Path) -> None:
    if destination.exists() or destination.is_symlink():
        raise SystemExit(f"destination already exists; refusing to overwrite: {destination}")
    shutil.copytree(source, destination, symlinks=True, copy_function=shutil.copy2)


def _write_json(path: Path, value: object) -> None:
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, path)


def _run_logged(name: str, command: list[str], *, cwd: Path, env: dict[str, str],
                log_path: Path, provenance: dict[str, object]) -> None:
    step = {"name": name, "argv": command, "cwd": str(cwd), "log": str(log_path), "status": "running"}
    steps = provenance.setdefault("steps", [])
    steps.append(step)
    _write_json(Path(provenance["run_root"]) / "build-provenance.json", provenance)
    try:
        with log_path.open("wb") as log:
            result = subprocess.run(command, cwd=cwd, env=env, stdout=log,
                                    stderr=subprocess.STDOUT, check=False)
    except BaseException as error:
        step["status"] = "interrupted" if isinstance(error, KeyboardInterrupt) else "failed"
        step["error_type"] = type(error).__name__
        step["error"] = str(error)
        _write_json(Path(provenance["run_root"]) / "build-provenance.json", provenance)
        raise
    step["exit_code"] = result.returncode
    step["status"] = "passed" if result.returncode == 0 else "failed"
    _write_json(Path(provenance["run_root"]) / "build-provenance.json", provenance)
    if result.returncode:
        raise SystemExit(f"{name} failed with exit code {result.returncode}; log preserved at {log_path}")


def inspect_macho(path: Path) -> dict[str, object]:
    data = path.read_bytes()
    if len(data) < 32 or struct.unpack_from("<I", data, 0)[0] != MACHO_MAGIC_64:
        raise SystemExit(f"kernel is not a little-endian 64-bit Mach-O: {path}")
    cputype, cpusubtype, filetype, ncmds, sizeofcmds, flags, reserved = \
        struct.unpack_from("<iiIIIII", data, 4)
    if cputype != CPU_TYPE_ARM64 or filetype != MH_EXECUTE:
        raise SystemExit(f"kernel must be arm64 MH_EXECUTE; cputype={cputype} filetype={filetype}")
    offset = 32
    text_base = None
    segments = []
    for _ in range(ncmds):
        if offset + 8 > len(data):
            raise SystemExit("truncated Mach-O load commands")
        command, command_size = struct.unpack_from("<II", data, offset)
        if command_size < 8 or offset + command_size > len(data):
            raise SystemExit("invalid Mach-O load-command size")
        if command == LC_SEGMENT_64 and command_size >= 72:
            name = data[offset + 8:offset + 24].split(b"\0", 1)[0].decode("ascii", "replace")
            vmaddr, vmsize, fileoff, filesize = struct.unpack_from("<QQQQ", data, offset + 24)
            segments.append({"name": name, "vmaddr": hex(vmaddr), "vmsize": hex(vmsize),
                             "fileoff": hex(fileoff), "filesize": hex(filesize)})
            if name == "__TEXT":
                text_base = vmaddr
        offset += command_size
    if text_base != KERNEL_TEXT_BASE:
        raise SystemExit(f"__TEXT base {text_base!r} != expected {KERNEL_TEXT_BASE:#x}")
    return {
        "path": str(path), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
        "cputype": cputype, "cpusubtype": cpusubtype, "filetype": filetype,
        "__TEXT_vmaddr": hex(text_base), "segments": segments,
    }


def build_environment(run_root: Path, *, developer_dir: Path, fakeroot: Path,
                      overlay: Path, toolchain: Path) -> dict[str, str]:
    env = {key: os.environ[key] for key in ("HOME", "USER", "LOGNAME", "LANG", "LC_ALL")
           if key in os.environ}
    env.update({
        "DEVELOPER_DIR": str(developer_dir),
        "PATH": ":".join((str(run_root / "compat/bin"), str(toolchain / "bin"),
                           str(developer_dir / "usr/bin"), "/usr/bin", "/bin", "/usr/sbin", "/sbin")),
        "UNIXNU_SDKROOT": str(overlay),
        "UNIXNU_PLATFORM_PATH": str(fakeroot / "Platforms/iPhoneOS.platform"),
        "TMPDIR": str(run_root / "tmp"),
    })
    return env


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--source-diff", type=Path, default=DEFAULT_SOURCE_DIFF)
    parser.add_argument("--no-source-diff", dest="source_diff", action="store_const", const=None,
                        help="do not apply the historical default source diff")
    parser.add_argument("--patch", action="append", default=[], type=Path,
                        help="additional patch applied after --source-diff; repeatable")
    parser.add_argument("--source-provenance", type=Path, default=DEFAULT_SOURCE_PROVENANCE)
    parser.add_argument("--fakeroot", type=Path, default=DEFAULT_FAKEROOT)
    parser.add_argument("--sdk-overlay", type=Path, default=DEFAULT_SDK_OVERLAY)
    parser.add_argument("--xcrun-wrapper", type=Path, default=DEFAULT_XCRUN_WRAPPER)
    parser.add_argument("--developer-dir", type=Path,
                        help="explicit Xcode Developer directory; otherwise use xcode-select")
    parser.add_argument("--run-root", type=Path,
                        help="new output directory; must not already exist")
    parser.add_argument("--run-parent", type=Path, default=Path("/tmp"),
                        help="parent for the unique run directory when --run-root is omitted")
    parser.add_argument("--jobs", type=int, default=min(os.cpu_count() or 4, 8))
    parser.add_argument("--y35a-a53", action="store_true",
                        help="enable the explicit Y35A A53 configuration macro")
    parser.add_argument("--y35a-low-vector", action="store_true",
                        help="enable the Y35A low/high vector diagnostic macro")
    parser.add_argument("--phase-a-amfi", action="store_true",
                        help="enable Phase-A AMFI entry/return witness instrumentation")
    parser.add_argument("--expected-sha256", help="optional exact kernel hash gate")
    parser.add_argument("--manifest", type=Path,
                        help="optional matching readback manifest for the final XNU static gate")
    parser.add_argument("--driver-archive", action="append", type=Path, default=[],
                        help="archive to force-load into the 4903 kernel; repeatable")
    parser.add_argument("--driver-manifest", type=Path,
                        help="archive-builder manifest binding the force-loaded integration")
    parser.add_argument("--plan-only", action="store_true",
                        help="validate inputs and print argv without creating output or running make")
    return parser.parse_args(argv)


def _inside(path: Path, parent: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(parent.resolve(strict=False))
        return True
    except ValueError:
        return False


def _paths_overlap(left: Path, right: Path) -> bool:
    left = Path(left).resolve(strict=False)
    right = Path(right).resolve(strict=False)
    return _inside(left, right) or _inside(right, left)


def referenced_tree_paths(paths: list[Path]) -> list[Path]:
    """Return input roots plus valid symlink targets nested in those roots."""
    roots = [Path(path).resolve(strict=True) for path in paths]
    found = set(roots)
    for root in roots:
        if not root.is_dir():
            continue
        for item in root.rglob("*"):
            if not item.is_symlink():
                continue
            try:
                found.add(item.resolve(strict=True))
            except (OSError, RuntimeError):
                continue
    return sorted(found, key=lambda path: str(path))


def allocate_isolated_run_root(
    *, explicit: Path | None, parent: Path, input_paths: list[Path]
) -> Path:
    """Allocate output only after proving it cannot contain or be inside an input."""
    resolved_inputs = [Path(path).resolve(strict=True) for path in input_paths]
    if explicit is not None:
        candidate = Path(explicit).expanduser().resolve(strict=False)
        for input_path in resolved_inputs:
            if _paths_overlap(candidate, input_path):
                raise SystemExit(
                    f"run output overlaps build input: {candidate} and {input_path}"
                )
    else:
        resolved_parent = Path(parent).expanduser().resolve(strict=True)
        for input_path in resolved_inputs:
            if _inside(resolved_parent, input_path):
                raise SystemExit(
                    f"run parent is inside build input: {resolved_parent} and {input_path}"
                )

    run_root = allocate_run_root(explicit=explicit, parent=parent)
    for input_path in resolved_inputs:
        if _paths_overlap(run_root, input_path):
            raise SystemExit(f"run output overlaps build input: {run_root} and {input_path}")
    return run_root


def run_recorded(
    provenance_path: Path, provenance: dict[str, object], operation
) -> int:
    """Keep the run-level terminal state accurate for errors and interrupts."""
    try:
        return operation()
    except BaseException as error:
        provenance["status"] = "interrupted" if isinstance(error, KeyboardInterrupt) else "failed"
        provenance["failure"] = {"type": type(error).__name__, "message": str(error)}
        _write_json(provenance_path, provenance)
        raise


def _execute_run(
    args: argparse.Namespace,
    *,
    run_root: Path,
    provenance: dict[str, object],
    provenance_path: Path,
    source: Path,
    source_provenance: Path,
    fakeroot_input: Path,
    overlay_input: Path,
    wrapper_input: Path,
    patch_paths: list[Path],
    xcode_info: dict[str, object],
    assets: dict[str, object],
    driver_archives: list[Path] | None = None,
    driver_manifest: dict | None = None,
) -> int:
    driver_archives = list(driver_archives or [])
    (run_root / "logs").mkdir()
    (run_root / "tmp").mkdir()
    (run_root / "inputs").mkdir()
    staged_driver_archives = []
    for archive in driver_archives:
        staged = run_root / "inputs/archives" / archive.name
        staged.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(archive, staged)
        staged_driver_archives.append(staged)
    if driver_manifest is not None:
        _write_json(run_root / "inputs/driver-manifest.json", driver_manifest)
    staged_source = run_root / "src"
    fakeroot = run_root / "fakeroot"
    overlay = run_root / "sdk-overlay"
    _copy_tree(fakeroot_input, fakeroot)
    _copy_tree(overlay_input, overlay)
    compat_bin = run_root / "compat/bin"
    compat_bin.mkdir(parents=True)
    wrapper = compat_bin / "xcrun"
    shutil.copy2(wrapper_input, wrapper)
    input_patch_copies = []
    for index, patch_path in enumerate(patch_paths):
        snapshot = run_root / "inputs" / f"{index:02d}-{patch_path.name}"
        shutil.copy2(patch_path, snapshot)
        input_patch_copies.append(snapshot)
    shutil.copy2(source_provenance, run_root / "inputs/source-provenance.json")
    def record_staging(event: dict[str, object]) -> None:
        provenance["staging"] = event
        _write_json(provenance_path, provenance)

    source_hash_before = assets["source"]["tree_sha256"]
    source_hash_after_copy = stage_source_tree(
        source, staged_source, input_patch_copies, on_progress=record_staging,
    )
    if tree_sha256(source) != source_hash_before:
        raise SystemExit("input source changed during snapshot; preserving run root")
    provenance["staged_inputs"] = {
        "source_tree_after_patches_sha256": source_hash_after_copy,
        "fakeroot_tree_sha256": tree_sha256(fakeroot),
        "sdk_overlay_tree_sha256": tree_sha256(overlay),
        "xcrun_wrapper_sha256": sha256_file(wrapper),
    }
    compatibility = {
        "genassym": patch_genassym_for_clang(staged_source),
        "monotonic": patch_monotonic_header(staged_source),
    }
    provenance["staged_source_compatibility"] = compatibility
    _write_json(provenance_path, provenance)
    host_tool_patch = ROOT / "scripts/ci/patch_xnu_host_tools.py"
    compatibility_target = staged_source / "bsd/kern/makekdebugevents.py"
    if compatibility_target.is_file():
        host_tool_command = [sys.executable, str(host_tool_patch), "--xnu-source", str(staged_source)]
        host_tool_result = subprocess.run(host_tool_command, capture_output=True, text=True, check=False)
        compatibility["host_tools"] = {
            "status": "passed" if host_tool_result.returncode == 0 else "failed",
            "script": str(host_tool_patch),
            "script_sha256": sha256_file(host_tool_patch),
            "argv": host_tool_command,
            "exit_code": host_tool_result.returncode,
            "stdout": host_tool_result.stdout,
            "stderr": host_tool_result.stderr,
        }
        provenance["staged_source_compatibility"] = compatibility
        _write_json(provenance_path, provenance)
        if host_tool_result.returncode:
            raise SystemExit("XNU host-tool compatibility patch failed; run preserved")
    else:
        compatibility["host_tools"] = {
            "status": "not-applicable",
            "reason": "bsd/kern/makekdebugevents.py absent from staged source",
        }
        provenance["staged_source_compatibility"] = compatibility
        _write_json(provenance_path, provenance)
    provenance["status"] = "prepared"
    _write_json(provenance_path, provenance)

    developer_dir = Path(str(xcode_info["developer_dir"]))
    toolchain = Path(str(xcode_info["toolchain"]))
    env = build_environment(run_root, developer_dir=developer_dir, fakeroot=fakeroot,
                            overlay=overlay, toolchain=toolchain)
    provenance["build_environment"] = env
    _write_json(provenance_path, provenance)
    for target in ("installhdrs", "build"):
        command = make_step_command(
            target, run_root=run_root, source=staged_source, fakeroot=fakeroot,
            overlay=overlay, make=developer_dir / "usr/bin/make",
            host_sdkroot=Path(str(xcode_info["macosx_sdk"])), toolchain=toolchain,
            memory_bytes=int(xcode_info["memory_bytes"]),
            physical_cpu_count=int(xcode_info["physical_cpu_count"]),
            logical_cpu_count=int(xcode_info["logical_cpu_count"]),
            jobs=args.jobs, host_os_version=str(xcode_info["host_os_version"]),
            y35a_a53=args.y35a_a53, y35a_low_vector=args.y35a_low_vector,
            phase_a_amfi=args.phase_a_amfi,
            driver_archives=staged_driver_archives,
        )
        _run_logged(target, command, cwd=staged_source, env=env,
                    log_path=run_root / f"logs/{target}.log", provenance=provenance)

    kernel = run_root / "obj/DEVELOPMENT_ARM64_T7001/mach.development.t7001.unstripped"
    artifact = {"path": str(kernel), "bytes": kernel.stat().st_size,
                "sha256": sha256_file(kernel)}
    provenance["kernel_artifact"] = artifact
    _write_json(run_root / "kernel-artifact.json", artifact)
    _write_json(provenance_path, provenance)
    artifact.update(inspect_macho(kernel))
    _write_json(run_root / "kernel-artifact.json", artifact)
    _write_json(provenance_path, provenance)
    if driver_manifest is not None:
        provenance["driver_integration"] = audit_driver_kernel(kernel, driver_manifest)
        _write_json(provenance_path, provenance)
    if args.expected_sha256 and artifact["sha256"] != args.expected_sha256.lower():
        raise SystemExit(
            f"kernel SHA-256 {artifact['sha256']} does not match expected {args.expected_sha256}; "
            f"run preserved at {run_root}"
        )
    verifier = ROOT / "scripts/y35a/verify_phase_instrumentation.py"
    command = [sys.executable, str(verifier), "--kernel", str(kernel)]
    provenance["kernel_static_verification"] = {"status": "running"}
    provenance["manifest_verification"] = {"status": "not-requested"}
    _write_json(provenance_path, provenance)
    try:
        _run_logged("kernel-static-verification", command, cwd=ROOT, env=env,
                    log_path=run_root / "logs/kernel-static-verification.log", provenance=provenance)
    except BaseException as error:
        provenance["kernel_static_verification"]["status"] = (
            "interrupted" if isinstance(error, KeyboardInterrupt) else "failed")
        _write_json(provenance_path, provenance)
        raise
    provenance["kernel_static_verification"]["status"] = "passed"
    if args.manifest:
        snapshot = run_root / "inputs/readback-manifest.json"
        snapshot.write_bytes(args.manifest.resolve(strict=True).read_bytes())
        binding = {"status": "running", "path": str(snapshot),
                   "manifest_sha256": sha256_file(snapshot),
                   "kernel_sha256": artifact["sha256"]}
        provenance["manifest_verification"] = binding
        _write_json(provenance_path, provenance)
        try:
            manifest_data = json.loads(snapshot.read_text())
            if manifest_data.get("kernel_sha256") != artifact["sha256"]:
                raise SystemExit(
                    "manifest kernel_sha256 does not bind the newly linked kernel; "
                    "generate a new matching probe before paired verification")
            _run_logged("manifest-verification", command + ["--manifest", str(snapshot)],
                        cwd=ROOT, env=env, log_path=run_root / "logs/manifest-verification.log",
                        provenance=provenance)
        except BaseException as error:
            binding["status"] = "interrupted" if isinstance(error, KeyboardInterrupt) else "failed"
            _write_json(provenance_path, provenance)
            raise
        binding["status"] = "passed"
    provenance["kernel_artifact"] = artifact
    provenance["status"] = "complete"
    _write_json(run_root / "kernel-artifact.json", artifact)
    _write_json(provenance_path, provenance)
    print(json.dumps({"ok": True, "run_root": str(run_root), "kernel": artifact}, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.jobs < 1:
        raise SystemExit("--jobs must be a positive integer")
    driver_archives = [Path(path).resolve(strict=True) for path in args.driver_archive]
    driver_manifest = load_driver_integration(driver_archives, args.driver_manifest)
    source = args.source.resolve(strict=True)
    source_identity = validate_source_tree(source)
    source_diff = args.source_diff.resolve(strict=True) if args.source_diff else None
    source_provenance = args.source_provenance.resolve(strict=True)
    fakeroot_input = args.fakeroot.resolve(strict=True)
    overlay_input = args.sdk_overlay.resolve(strict=True)
    wrapper_input = args.xcrun_wrapper.resolve(strict=True)
    _validate_build_inputs(fakeroot_input, overlay_input, wrapper_input)
    if args.developer_dir is not None:
        developer_dir = args.developer_dir.expanduser().resolve(strict=True)
    else:
        xcode_select = Path(_capture(["/usr/bin/xcode-select", "-p"]))
        developer_dir = xcode_select.resolve(strict=True)
    xcode_info = _xcode_inputs(developer_dir)
    patch_paths = [path for path in (source_diff, *[Path(path).resolve(strict=True) for path in args.patch])
                   if path is not None]
    assets = {
        "source": {**source_identity, "path": str(source), "tree_sha256": tree_sha256(source)},
        "source_diff": [{"path": str(path), "sha256": sha256_file(path)} for path in patch_paths],
        "source_provenance": {"path": str(source_provenance), "sha256": sha256_file(source_provenance)},
        "fakeroot": {"path": str(fakeroot_input), "tree_sha256": tree_sha256(fakeroot_input)},
        "sdk_overlay": {"path": str(overlay_input), "tree_sha256": tree_sha256(overlay_input)},
        "xcrun_wrapper": {"path": str(wrapper_input), "sha256": sha256_file(wrapper_input)},
        "toolchain": xcode_info,
        "driver_archives": [{"path": str(path), "sha256": sha256_file(path)}
                            for path in driver_archives],
        "driver_manifest": ({"path": str(args.driver_manifest.resolve(strict=True)),
                             "sha256": sha256_file(args.driver_manifest.resolve(strict=True))}
                            if args.driver_manifest else None),
    }
    if args.plan_only:
        plan_root = Path("/tmp/<new-xnu4903-native-run>")
        planned = [make_step_command(
            target, run_root=plan_root, source=plan_root / "src",
            fakeroot=plan_root / "fakeroot", overlay=plan_root / "sdk-overlay",
            make=developer_dir / "usr/bin/make",
            host_sdkroot=Path(str(xcode_info["macosx_sdk"])),
            toolchain=Path(str(xcode_info["toolchain"])),
            memory_bytes=int(xcode_info["memory_bytes"]),
            physical_cpu_count=int(xcode_info["physical_cpu_count"]),
            logical_cpu_count=int(xcode_info["logical_cpu_count"]),
            jobs=args.jobs, host_os_version=str(xcode_info["host_os_version"]),
            y35a_a53=args.y35a_a53, y35a_low_vector=args.y35a_low_vector,
            phase_a_amfi=args.phase_a_amfi,
            driver_archives=[Path(path) for path in args.driver_archive],
        ) for target in ("installhdrs", "build")]
        print(json.dumps({"ok": True, "plan_only": True, "inputs": assets,
                          "build_profile": {
                              "y35a_a53": args.y35a_a53,
                              "y35a_low_vector": args.y35a_low_vector,
                              "phase_a_amfi": args.phase_a_amfi,
                              "other_cflags": ["-DXNU_NATIVE_EARLY_FAULT=1", "-DOS_FIREHOSE_SPI=1"]
                              + (["-DXNU_Y35A_A53=1"] if args.y35a_a53 else [])
                              + (["-DXNU_Y35A_LOW_VECTOR=1"] if args.y35a_low_vector else [])
                              + (["-DXNU_Y35A_PHASE_A_AMFI=1"] if args.phase_a_amfi else []),
                          }, "commands": planned}, indent=2))
        return 0

    xcode_paths = [
        Path(str(xcode_info[key]))
        for key in ("iphoneos_sdk", "macosx_sdk", "toolchain")
    ]
    xcode_paths.extend((
        Path(str(xcode_info["developer_dir"])) / "usr/bin/make",
        Path(str(xcode_info["developer_dir"])) / "usr/bin/xcodebuild",
    ))
    input_paths = [
        *referenced_tree_paths([overlay_input]), source, source_provenance,
        fakeroot_input, wrapper_input, *patch_paths, *xcode_paths, *driver_archives,
    ]
    if args.driver_manifest:
        input_paths.append(args.driver_manifest.resolve(strict=True))
    run_root = allocate_isolated_run_root(
        explicit=args.run_root, parent=args.run_parent, input_paths=input_paths,
    )
    provenance: dict[str, object] = {
        "schema": 1, "status": "preparing", "run_root": str(run_root),
        "source_identity": source_identity, "inputs": assets, "steps": [],
        "build_profile": {
            "y35a_a53": args.y35a_a53,
            "y35a_low_vector": args.y35a_low_vector,
            "phase_a_amfi": args.phase_a_amfi,
            "other_cflags": ["-DXNU_NATIVE_EARLY_FAULT=1", "-DOS_FIREHOSE_SPI=1"]
            + (["-DXNU_Y35A_A53=1"] if args.y35a_a53 else [])
            + (["-DXNU_Y35A_LOW_VECTOR=1"] if args.y35a_low_vector else [])
            + (["-DXNU_Y35A_PHASE_A_AMFI=1"] if args.phase_a_amfi else []),
        },
        "warning": "Diagnostic-patched XNU input; not a vanilla or production release build.",
    }
    provenance_path = run_root / "build-provenance.json"
    _write_json(provenance_path, provenance)
    return run_recorded(
        provenance_path, provenance,
        lambda: _execute_run(
            args, run_root=run_root, provenance=provenance, provenance_path=provenance_path,
            source=source, source_provenance=source_provenance,
            fakeroot_input=fakeroot_input, overlay_input=overlay_input,
            wrapper_input=wrapper_input, patch_paths=patch_paths,
            xcode_info=xcode_info, assets=assets,
            driver_archives=driver_archives, driver_manifest=driver_manifest,
        ),
    )


if __name__ == "__main__":
    raise SystemExit(main())
