#!/usr/bin/env python3
"""Plan or run the exact UniXNU native build described by a JSON manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path


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


def resolve(root: Path, value: str | None) -> Path | None:
    if not value:
        return None
    path = Path(value)
    return path if path.is_absolute() else root / path


def validate_native_provenance(manifest: dict, repo_root: Path) -> dict:
    source_provenance_path = resolve(repo_root, manifest.get("source_provenance"))
    if source_provenance_path is None or not source_provenance_path.is_file():
        raise SystemExit("native source provenance is missing")
    if sha256(source_provenance_path) != manifest.get("source_provenance_sha256"):
        raise SystemExit("native source provenance SHA-256 does not match native build manifest")
    source_provenance = json.loads(source_provenance_path.read_text())
    source = source_provenance.get("source", {})
    if source.get("commit") != manifest.get("source_ref"):
        raise SystemExit("native source provenance commit does not match source_ref")
    expected_patches = [
        {key: item.get(key) for key in ("order", "target_tree", "path", "sha256")}
        for item in manifest.get("patches", [])
    ]
    provenance_patches = [
        {key: item.get(key) for key in ("order", "target_tree", "path", "sha256")}
        for item in source_provenance.get("patches", [])
    ]
    if provenance_patches != expected_patches:
        raise SystemExit("ordered XNU patch list differs from source provenance")
    expected_external = manifest.get("external_driver_patches", [])
    actual_external = source_provenance.get("external_driver_patches", [])
    normalized_external = lambda entries: [
        {key: item.get(key) for key in ("scope", "path", "sha256")}
        for item in entries
    ]
    if normalized_external(actual_external) != normalized_external(expected_external):
        raise SystemExit("external driver patch list differs from source provenance")
    if source_provenance.get("source_diff") is not None:
        raise SystemExit("native source provenance unexpectedly includes a source diff")
    dependencies = source_provenance.get("kernel_dependency_versions", {})
    native_inputs = manifest.get("native_inputs", {})
    dependency_map = {
        "libdispatch": native_inputs.get("libdispatch_tag"),
        "libplatform": native_inputs.get("libplatform_tag"),
    }
    if dependencies != dependency_map:
        raise SystemExit("kernel dependency versions differ from native build manifest")
    commit_map = {
        "availability": native_inputs.get("availability_commit"),
        "libdispatch": native_inputs.get("libdispatch_commit"),
        "libplatform": native_inputs.get("libplatform_commit"),
        "llvm": native_inputs.get("llvm_commit"),
        "libc": native_inputs.get("libc_commit"),
    }
    if source_provenance.get("native_input_commits") != commit_map:
        raise SystemExit("native input commits differ from source provenance")
    static_contract = manifest.get("static_verification", {})
    static_path = resolve(repo_root, static_contract.get("script"))
    if (source_provenance.get("static_verification", {}).get("script")
            != static_contract.get("script")
            or source_provenance.get("static_verification", {}).get("sha256")
            != static_contract.get("sha256")
            or static_path is None or not static_path.is_file()
            or sha256(static_path) != static_contract.get("sha256")):
        raise SystemExit("candidate-specific static verifier does not match source provenance")
    return source_provenance


def validate_native_inputs_manifest(
    path: Path, expected: dict, *, source_ref: str,
    fakeroot: Path, sdk_overlay: Path, xcrun_wrapper: Path,
) -> dict:
    if not path.is_file():
        raise SystemExit(f"native inputs manifest is missing: {path}")
    data = json.loads(path.read_text())
    actual = data.get("source", {})
    expected_values = {
        "xnu_commit": source_ref,
        "availability_tag": expected.get("availability_tag"),
        "availability_commit": expected.get("availability_commit"),
        "libdispatch_tag": expected.get("libdispatch_tag"),
        "libdispatch_commit": expected.get("libdispatch_commit"),
        "libplatform_tag": expected.get("libplatform_tag"),
        "libplatform_commit": expected.get("libplatform_commit"),
        "llvm_commit": expected.get("llvm_commit"),
        "libc_commit": expected.get("libc_commit"),
    }
    if actual != expected_values:
        raise SystemExit(
            "prepared native input versions do not match manifest: "
            f"expected {expected_values}, found {actual}"
        )
    for key in ("fakeroot_sha256", "sdk_overlay_sha256", "xcrun_wrapper_sha256"):
        value = data.get("trees", {}).get(key)
        if not isinstance(value, str) or len(value) != 64:
            raise SystemExit(f"native inputs manifest has invalid {key}")
    actual_paths = {
        "fakeroot": fakeroot.resolve(strict=True),
        "sdk_overlay": sdk_overlay.resolve(strict=True),
        "xcrun_wrapper": xcrun_wrapper.resolve(strict=True),
    }
    for key, actual_path in actual_paths.items():
        recorded = Path(data.get("paths", {}).get(key, "")).resolve(strict=True)
        if recorded != actual_path:
            raise SystemExit(f"prepared native input path mismatch: {key}")
    if not os.access(xcrun_wrapper, os.X_OK):
        raise SystemExit("prepared xcrun wrapper is not executable")
    actual_trees = {
        "fakeroot_sha256": tree_sha256(fakeroot),
        "sdk_overlay_sha256": tree_sha256(sdk_overlay),
        "xcrun_wrapper_sha256": sha256(xcrun_wrapper),
    }
    if any(data.get("trees", {}).get(key) != value for key, value in actual_trees.items()):
        raise SystemExit("prepared native input tree hash does not match its manifest")
    return data


def validate_static_verifier(manifest: dict, repo_root: Path) -> tuple[Path, str]:
    contract = manifest.get("static_verification", {})
    path = resolve(repo_root, contract.get("script"))
    expected = contract.get("sha256")
    if path is None or not path.is_file() or not expected:
        raise SystemExit("native static verifier path and SHA-256 are required")
    actual = sha256(path)
    if actual != expected:
        raise SystemExit("native static verifier SHA-256 does not match native manifest")
    return path, actual


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--developer-dir", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--source-ref", required=True)
    parser.add_argument("--native-inputs-manifest", type=Path, required=True)
    parser.add_argument("--driver-run-id", required=True, type=int)
    parser.add_argument("--driver-artifact-name", required=True)
    parser.add_argument("--driver-head-branch", required=True)
    parser.add_argument("--plan-only", action="store_true")
    parser.add_argument("--fakeroot", type=Path)
    parser.add_argument("--sdk-overlay", type=Path)
    parser.add_argument("--xcrun-wrapper", type=Path)
    parser.add_argument("--driver-archive", type=Path)
    parser.add_argument("--driver-manifest", type=Path)
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    manifest_path = args.manifest.resolve()
    manifest = json.loads(manifest_path.read_text())
    failures: list[str] = []
    for key in ("source_ref", "source_provenance", "native_inputs", "driver_artifact",
                "static_verification", "patches", "build"):
        if key not in manifest:
            failures.append(f"missing manifest field: {key}")
    patches = manifest.get("patches", [])
    if not isinstance(patches, list) or not patches:
        failures.append("patches must be a non-empty ordered list")
    if not args.source_root.is_dir():
        failures.append(f"source root missing: {args.source_root}")
    if not args.developer_dir.is_dir():
        failures.append(f"developer dir missing: {args.developer_dir}")
    for name, value in (
        ("--fakeroot", args.fakeroot), ("--sdk-overlay", args.sdk_overlay),
        ("--xcrun-wrapper", args.xcrun_wrapper), ("--driver-archive", args.driver_archive),
        ("--driver-manifest", args.driver_manifest),
    ):
        if value is None:
            failures.append(f"{name} is required for the R208 native build contract")
    if manifest.get("source_ref") != args.source_ref:
        failures.append("workflow source_ref does not match native manifest")
    if not isinstance(manifest.get("driver_artifact"), dict):
        failures.append("native manifest driver_artifact must be an object")
    else:
        pinned_driver = manifest["driver_artifact"]
        if pinned_driver.get("run_id") != args.driver_run_id:
            failures.append("selected driver run ID does not match native manifest")
        if pinned_driver.get("name") != args.driver_artifact_name:
            failures.append("selected driver artifact name does not match native manifest")
        if pinned_driver.get("head_branch") != args.driver_head_branch:
            failures.append("selected driver artifact branch does not match native manifest")
        driver_source = repo_root / "drivers/QcomSdcard/NativeSdcard.cpp"
        if not driver_source.is_file() or sha256(driver_source) != pinned_driver.get("source_sha256"):
            failures.append("current NativeSdcard source does not match pinned driver artifact")

    patch_paths: list[Path] = []
    for index, item in enumerate(patches if isinstance(patches, list) else []):
        if not isinstance(item, dict):
            failures.append(f"patches[{index}] must be an object")
            continue
        if item.get("order") != index:
            failures.append(f"patches[{index}].order must equal {index}")
        if item.get("target_tree") != "xnu-source":
            failures.append(f"patches[{index}].target_tree must be xnu-source")
        path = resolve(repo_root, item.get("path"))
        if path is None or not path.is_file():
            failures.append(f"patches[{index}] missing: {item.get('path')}")
            continue
        actual = sha256(path)
        expected = item.get("sha256")
        if expected and actual != expected:
            failures.append(f"patches[{index}] sha256 mismatch")
        patch_paths.append(path)

    if failures:
        print(json.dumps({"ok": False, "failures": failures}, indent=2))
        return 1

    if not args.source_root.is_dir():
        print(json.dumps({"ok": False, "failures": [f"source root missing: {args.source_root}"]}, indent=2))
        return 1
    actual_source = subprocess.run(
        ["git", "-C", str(args.source_root), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=False,
    )
    if actual_source.returncode or actual_source.stdout.strip() != manifest["source_ref"]:
        print(json.dumps({"ok": False, "failures": ["XNU checkout does not match manifest source_ref"]}, indent=2))
        return 1
    try:
        source_provenance = validate_native_provenance(manifest, repo_root)
        static_verifier, static_verifier_sha = validate_static_verifier(manifest, repo_root)
        native_inputs = validate_native_inputs_manifest(
            args.native_inputs_manifest.resolve(strict=True), manifest["native_inputs"],
            source_ref=manifest["source_ref"], fakeroot=args.fakeroot,
            sdk_overlay=args.sdk_overlay, xcrun_wrapper=args.xcrun_wrapper)
        if not isinstance(native_inputs, dict):
            raise SystemExit("native inputs manifest is invalid")
        static_verifier, static_verifier_sha = validate_static_verifier(manifest, repo_root)
    except (OSError, ValueError, json.JSONDecodeError, SystemExit) as error:
        print(json.dumps({"ok": False, "failures": [str(error)]}, indent=2))
        return 1

    build = manifest["build"]
    command = [
        "python3",
        str(repo_root / "scripts/build-xnu-4903-native.py"),
        "--source",
        str(args.source_root),
        "--run-root",
        str(args.run_root),
        "--developer-dir",
        str(args.developer_dir),
        "--jobs",
        str(build.get("jobs", 4)),
    ]
    if manifest.get("source_diff"):
        command.extend(["--source-diff", str(resolve(repo_root, manifest["source_diff"]))])
    else:
        command.append("--no-source-diff")
    for path in patch_paths:
        command.extend(["--patch", str(path)])
    for flag in build.get("flags", []):
        command.append(str(flag))
    if build.get("expected_sha256"):
        command.extend(["--expected-sha256", str(build["expected_sha256"])])
    if build.get("manifest"):
        command.extend(["--manifest", str(resolve(repo_root, build["manifest"]))])
    if manifest.get("source_provenance"):
        command.extend(["--source-provenance", str(resolve(repo_root, manifest["source_provenance"]))])
    if args.fakeroot:
        command.extend(["--fakeroot", str(args.fakeroot.resolve())])
    if args.sdk_overlay:
        command.extend(["--sdk-overlay", str(args.sdk_overlay.resolve())])
    if args.xcrun_wrapper:
        command.extend(["--xcrun-wrapper", str(args.xcrun_wrapper.resolve())])
    if args.driver_archive:
        command.extend(["--driver-archive", str(args.driver_archive.resolve())])
    if args.driver_manifest:
        command.extend(["--driver-manifest", str(args.driver_manifest.resolve())])
    if args.driver_archive:
        command.extend(["--driver-contract", str(manifest_path)])
    command.extend(["--static-verifier", str(static_verifier),
                    "--static-verifier-sha256", static_verifier_sha])
    command.extend(["--static-verifier", str(static_verifier),
                    "--static-verifier-sha256", static_verifier_sha])

    report = {
        "ok": True,
        "manifest": str(manifest_path),
        "manifest_sha256": sha256(manifest_path),
        "source_root": str(args.source_root),
        "developer_dir": str(args.developer_dir),
        "source_ref": manifest["source_ref"],
        "source_provenance_sha256": sha256(resolve(repo_root, manifest["source_provenance"])),
        "native_inputs_manifest": str(args.native_inputs_manifest.resolve()),
        "native_inputs_manifest_sha256": sha256(args.native_inputs_manifest.resolve()),
        "driver_artifact": manifest["driver_artifact"],
        "driver_head_branch": manifest["driver_artifact"].get("head_branch"),
        "driver_manifest_sha256": sha256(args.driver_manifest.resolve()) if args.driver_manifest else None,
        "static_verifier": str(static_verifier),
        "static_verifier_sha256": static_verifier_sha,
        "static_verifier": str(static_verifier),
        "static_verifier_sha256": static_verifier_sha,
        "patches": [{"path": str(path), "sha256": sha256(path)} for path in patch_paths],
        "command": command,
        "plan_only": args.plan_only,
    }
    print(json.dumps(report, indent=2))
    if args.plan_only:
        return 0
    args.run_root.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(command, check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
