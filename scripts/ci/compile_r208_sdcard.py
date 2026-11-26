#!/usr/bin/env python3
"""Compile the R208 NativeSdcard object against an exact public XNU checkout."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess


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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--xnu-source", type=Path, required=True)
    parser.add_argument("--generated-headers", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    xnu = args.xnu_source.resolve(strict=True)
    generated = args.generated_headers.resolve(strict=True)
    repo = args.repo_root.resolve(strict=True)
    source = repo / "drivers/QcomSdcard/NativeSdcard.cpp"
    if not source.is_file():
        raise SystemExit(f"missing source: {source}")
    commit = run(["git", "-C", str(xnu), "rev-parse", "HEAD"])
    expected = "494ffe1c29d37ca720c37328feb83069c9641b67"
    if commit != expected:
        raise SystemExit(f"XNU checkout {commit} does not match {expected}")

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
        "-DKERNEL_PRIVATE", "-DXNU_KERNEL_PRIVATE", "-DPRIVATE", "-D__MACHO__=1",
        "-DDRIVER_PRIVATE", "-DIOKIT_KERNEL_PRIVATE", "-DIOASSERT=1",
        "-DIOMATCHDEBUG=1", "-DIOALLOCDEBUG=1", "-DXNU_NATIVE_SDCARD=1",
    ]
    include_roots = [
        xnu / "iokit", xnu / "osfmk", xnu / "bsd", xnu / "libkern",
        xnu / "pexpert", xnu / "EXTERNAL_HEADERS", xnu / "config",
    ]
    include_roots += [
        generated / "System/Library/Frameworks/Kernel.framework/Headers",
        generated / "System/Library/Frameworks/Kernel.framework/PrivateHeaders",
        generated / "System/Library/Frameworks/IOKit.framework/Headers",
        generated / "System/Library/Frameworks/IOKit.framework/PrivateHeaders",
        generated / "usr/include", generated / "usr/local/include",
    ]
    for include in include_roots:
        if not include.is_dir():
            raise SystemExit(f"missing XNU include root: {include}")
        command += ["-isystem", str(include)]
    command += ["-I", str(repo / "drivers/QcomSdcard"), "-c", str(source), "-o", str(args.output)]
    version = run([clang, "--version"], env=env)
    result = subprocess.run(command, capture_output=True, text=True, env=env, check=False)
    report = {
        "source": str(source), "source_sha256": sha256(source),
        "xnu_source": str(xnu), "xnu_commit": commit,
        "clang": clang, "clang_version": version, "sdk": sdk,
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
