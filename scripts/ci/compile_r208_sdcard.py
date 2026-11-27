#!/usr/bin/env python3
"""Compile the R208 NativeSdcard object against an exact public XNU checkout."""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import shutil


def normalize_ar_timestamps(path: Path) -> None:
    data = bytearray(path.read_bytes())
    if data[:8] != b"!<arch>\n":
        raise SystemExit(f"not an ar archive: {path}")
    offset = 8
    while offset < len(data):
        if offset + 60 > len(data) or data[offset + 58:offset + 60] != b"`\n":
            raise SystemExit(f"malformed ar member header at {offset}: {path}")
        size = int(bytes(data[offset + 48:offset + 58]).decode("ascii").strip())
        data[offset + 16:offset + 28] = b"0           "
        offset += 60 + size + (size & 1)
    if offset != len(data):
        raise SystemExit(f"ar archive has invalid trailing bytes: {path}")
    path.write_bytes(data)


def embedded_kext_abi_probe_source() -> str:
    return (
        "#include <libkern/c++/OSMetaClass.h>\n"
        "#if !defined(CONFIG_EMBEDDED) || CONFIG_EMBEDDED != 1\n"
        "#error CONFIG_EMBEDDED must match the embedded XNU kernel\n"
        "#endif\n"
        "static_assert(APPLE_KEXT_VTABLE_PADDING == 0, \"KEXT vtable padding mismatch\");\n"
        "static_assert(APPLE_KEXT_ALIGN_CONTAINERS == 1, \"KEXT container alignment mismatch\");\n"
    )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def run(command: list[str], *, env: dict[str, str] | None = None) -> str:
    result = subprocess.run(command, capture_output=True, text=True, env=env, check=False)
    if result.returncode:
        raise SystemExit(result.stderr.strip() or result.stdout.strip() or "command failed")
    return result.stdout.strip()


def verify_embedded_kext_abi(compile_prefix: list[str], *, env: dict[str, str]) -> dict:
    if "-DCONFIG_EMBEDDED=1" not in compile_prefix:
        raise SystemExit("embedded XNU KEXT ABI gate requires CONFIG_EMBEDDED=1")
    source = embedded_kext_abi_probe_source()
    command = compile_prefix + ["-x", "c++", "-fsyntax-only", "-"]
    result = subprocess.run(command, input=source, capture_output=True, text=True,
                            env=env, check=False)
    if result.returncode:
        raise SystemExit("embedded XNU KEXT ABI compile-time gate failed: " +
                         (result.stderr.strip() or result.stdout.strip()))
    return {
        "status": "passed",
        "config_embedded": 1,
        "apple_kext_vtable_padding": 0,
        "apple_kext_align_containers": 1,
        "probe_source_sha256": hashlib.sha256(source.encode()).hexdigest(),
        "argv": command,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def reject_reserved_abi_imports(archive: Path, *, env: dict[str, str]) -> dict:
    output = run(["/usr/bin/xcrun", "nm", "-u", str(archive)], env=env)
    imports = sorted({line.strip() for line in output.splitlines() if "_RESERVED" in line})
    if imports:
        raise SystemExit("storage archive imports embedded-incompatible reserved ABI slots: " +
                         "; ".join(imports))
    return {"status": "passed", "reserved_abi_imports": imports}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--xnu-source", type=Path, required=True)
    parser.add_argument("--generated-headers", type=Path, required=True)
    parser.add_argument("--iostorage-source", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    xnu = args.xnu_source.resolve(strict=True)
    generated = args.generated_headers.resolve(strict=True)
    iostorage = args.iostorage_source.resolve(strict=True)
    repo = args.repo_root.resolve(strict=True)
    source = repo / "drivers/QcomSdcard/NativeSdcard.cpp"
    if not source.is_file():
        raise SystemExit(f"missing source: {source}")
    commit = run(["git", "-C", str(xnu), "rev-parse", "HEAD"])
    expected = "494ffe1c29d37ca720c37328feb83069c9641b67"
    if commit != expected:
        raise SystemExit(f"XNU checkout {commit} does not match {expected}")
    iostorage_commit = run(["git", "-C", str(iostorage), "rev-parse", "HEAD"])
    expected_iostorage = "0e637763592184691a0e51a0995f10fa110f0780"
    if iostorage_commit != expected_iostorage:
        raise SystemExit(f"IOStorageFamily checkout {iostorage_commit} does not match {expected_iostorage}")
    iostorage_headers = generated / "r208-iostorage-headers/IOKit/storage"
    iostorage_headers.mkdir(parents=True, exist_ok=True)
    header_names = (
        "IOAppleLabelScheme.h", "IOApplePartitionScheme.h", "IOBlockStorageDevice.h",
        "IOBlockStorageDriver.h", "IOFDiskPartitionScheme.h", "IOFilterScheme.h",
        "IOGUIDPartitionScheme.h", "IOMedia.h", "IOMediaBSDClient.h",
        "IOPartitionScheme.h", "IOStorage.h", "IOStorageDeviceCharacteristics.h",
        "IOStorageProtocolCharacteristics.h", "IOStorageControllerCharacteristics.h",
        "IOStorageCardCharacteristics.h",
    )
    missing = []
    for name in header_names:
        source_header = iostorage / name
        if not source_header.is_file():
            missing.append(str(source_header))
        else:
            shutil.copy2(source_header, iostorage_headers / name)
    if missing:
        raise SystemExit("missing IOStorageFamily headers: " + ", ".join(missing))

    env = os.environ.copy()
    env["DEVELOPER_DIR"] = env.get("DEVELOPER_DIR", "/Applications/Xcode.app/Contents/Developer")
    clang = run(["/usr/bin/xcrun", "--find", "clang++"], env=env)
    sdk = run(["/usr/bin/xcrun", "--sdk", "iphoneos", "--show-sdk-path"], env=env)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    command = [
        clang, "-target", "arm64-apple-ios12.4", "-isysroot", sdk,
        "-std=gnu++17", "-fapple-kext", "-mkernel",
        "-fno-builtin", "-fno-common", "-fno-exceptions", "-fno-rtti",
        "-fno-strict-aliasing", "-mgeneral-regs-only", "-O2", "-Wall", "-Wextra",
        "-Werror", "-Wno-unused-parameter", "-ferror-limit=0",
        "-DARM64_BOARD_CONFIG_T7001", "-Darm64", "-DARM64", "-D__ARM64__",
        "-DLP64", "-D__API__=v4", "-DPLATFORM_iPhoneOS", "-DAPPLE", "-DKERNEL",
        "-DKERNEL_PRIVATE", "-DXNU_KERNEL_PRIVATE", "-DCONFIG_EMBEDDED=1",
        "-DPRIVATE", "-D__MACHO__=1",
        "-DDRIVER_PRIVATE", "-DIOKIT_KERNEL_PRIVATE", "-DIOASSERT=1",
        "-DIOMATCHDEBUG=1", "-DIOALLOCDEBUG=1", "-DXNU_NATIVE_SDCARD=1",
    ]
    include_roots = [
        xnu / "iokit", xnu / "osfmk", xnu / "bsd", xnu / "libkern",
        xnu / "pexpert", xnu / "EXTERNAL_HEADERS", xnu / "config",
    ]
    generated_roots = [
        generated / "System/Library/Frameworks/Kernel.framework/Headers",
        generated / "System/Library/Frameworks/Kernel.framework/PrivateHeaders",
        generated / "System/Library/Frameworks/IOKit.framework/Headers",
        generated / "System/Library/Frameworks/IOKit.framework/PrivateHeaders",
        generated / "usr/include", generated / "usr/local/include",
    ]
    missing_generated = [str(path) for path in generated_roots
                         if path.name == "Headers" and "Kernel.framework/Headers" in str(path)
                         and not path.is_dir()]
    if missing_generated:
        raise SystemExit("missing required generated Kernel headers: " + ", ".join(missing_generated))
    include_roots += [path for path in generated_roots if path.is_dir()]
    include_roots.append(generated / "r208-iostorage-headers")
    for include in include_roots:
        if not include.is_dir():
            raise SystemExit(f"missing XNU include root: {include}")
        command += ["-isystem", str(include)]
    command += ["-I", str(repo / "drivers/QcomSdcard"), "-c", str(source), "-o", str(args.output)]
    version = run([clang, "--version"], env=env)
    abi_contract = verify_embedded_kext_abi(command[:command.index("-c")], env=env)
    result = subprocess.run(command, capture_output=True, text=True, env=env, check=False)
    report = {
        "source": str(source), "source_sha256": sha256(source),
        "xnu_source": str(xnu), "xnu_commit": commit,
        "iostorage_source": str(iostorage), "iostorage_commit": iostorage_commit,
        "clang": clang, "clang_version": version, "sdk": sdk,
        "kext_abi": abi_contract,
        "argv": command, "exit_code": result.returncode,
    }
    if result.returncode:
        report["stderr"] = result.stderr
        report["stdout"] = result.stdout
        args.output.with_name("compile-report.json").write_text(json.dumps(report, indent=2) + "\n")
        raise SystemExit("NativeSdcard object compile failed; report preserved")
    report["object"] = {"path": str(args.output), "sha256": sha256(args.output), "size": args.output.stat().st_size}
    args.output.with_name("compile-report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    family_sources = (
        "IOApplePartitionScheme.cpp", "IOBlockStorageDevice.cpp",
        "IOBlockStorageDriver.cpp", "IOFDiskPartitionScheme.cpp",
        "IOFilterScheme.cpp", "IOGUIDPartitionScheme.cpp", "IOMedia.cpp",
        "IOMediaBSDClient.cpp", "IOPartitionScheme.cpp", "IOStorage.cpp",
    )
    family_objects = []
    support_base = [value for value in command[:command.index("-c")]
                    if value not in ("-Werror", "-std=gnu++17")]
    for name in family_sources:
        source_path = iostorage / name
        object_path = args.output.with_name(name.replace(".cpp", ".o"))
        support_command = support_base + [
            "-std=gnu++14", "-DTARGET_OS_EMBEDDED=1", "-Wno-deprecated-declarations",
            "-c", str(source_path), "-o", str(object_path),
        ]
        support_result = subprocess.run(support_command, capture_output=True, text=True, env=env, check=False)
        if support_result.returncode:
            report["family_compile_failure"] = {"source": str(source_path), "argv": support_command,
                                                  "stderr": support_result.stderr, "stdout": support_result.stdout}
            args.output.with_name("compile-report.json").write_text(json.dumps(report, indent=2) + "\n")
            raise SystemExit("IOStorageFamily base object compile failed; report preserved")
        family_objects.append(object_path)
    combined = args.output.with_name("IOStorageFamily-QcomSdcard.o")
    link = run(["/usr/bin/xcrun", "ld", "-r", "-arch", "arm64", "-o", str(combined),
                *[str(path) for path in [*family_objects, args.output]]], env=env)
    archive = args.output.with_name("libQcomSdcard.a")
    run(["/usr/bin/xcrun", "ar", "-rcs", str(archive), str(combined)], env=env)
    normalize_ar_timestamps(archive)
    try:
        archive_abi = reject_reserved_abi_imports(archive, env=env)
    except SystemExit as error:
        report["archive_kext_abi"] = {"status": "failed", "error": str(error)}
        report["archive"] = {"path": str(archive), "sha256": sha256(archive),
                             "size": archive.stat().st_size}
        args.output.with_name("compile-report.json").write_text(json.dumps(report, indent=2) + "\n")
        raise
    report["archive_kext_abi"] = archive_abi
    report["iostorage_objects"] = [{"path": str(path), "sha256": sha256(path)} for path in family_objects]
    report["combined_object"] = {"path": str(combined), "sha256": sha256(combined), "size": combined.stat().st_size}
    report["archive"] = {"path": str(archive), "sha256": sha256(archive), "size": archive.stat().st_size}
    driver_manifest = {
        "schema_version": 1,
        "component": "QcomSdcard",
        "integration": {"role": "tf-storage", "force_load": True,
                         "consumer": "scripts/build-xnu-4903-native.py"},
        "archive": report["archive"],
        "source": {"path": str(source), "sha256": sha256(source)},
        "xnu": {"commit": commit},
        "iostorage": {"commit": iostorage_commit},
        "ci_provenance": {
            "run_id": int(os.environ["GITHUB_RUN_ID"]),
            "artifact_name": f"r208-native-sdcard-{os.environ['GITHUB_RUN_ID']}",
            "head_sha": os.environ["GITHUB_SHA"],
            "head_branch": os.environ["GITHUB_REF_NAME"],
            "workflow_name": "R208 TF validation",
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        },
        "kext_abi": abi_contract,
        "archive_kext_abi": archive_abi,
        "object": report["object"],
        "combined_object": report["combined_object"],
    }
    driver_manifest_path = args.output.with_name("driver-manifest.json")
    driver_manifest_path.write_text(json.dumps(driver_manifest, indent=2, sort_keys=True) + "\n")
    report["driver_manifest"] = {"path": str(driver_manifest_path), "sha256": sha256(driver_manifest_path)}
    args.output.with_name("compile-report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
