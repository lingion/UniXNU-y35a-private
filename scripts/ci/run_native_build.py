#!/usr/bin/env python3
"""Plan or run the exact UniXNU native build described by a JSON manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def resolve(root: Path, value: str | None) -> Path | None:
    if not value:
        return None
    path = Path(value)
    return path if path.is_absolute() else root / path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--developer-dir", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
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
    for key in ("patches", "build"):
        if key not in manifest:
            failures.append(f"missing manifest field: {key}")
    patches = manifest.get("patches", [])
    if not isinstance(patches, list) or not patches:
        failures.append("patches must be a non-empty ordered list")
    if not args.source_root.is_dir():
        failures.append(f"source root missing: {args.source_root}")
    if not args.developer_dir.is_dir():
        failures.append(f"developer dir missing: {args.developer_dir}")

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

    report = {
        "ok": True,
        "manifest": str(manifest_path),
        "manifest_sha256": sha256(manifest_path),
        "source_root": str(args.source_root),
        "developer_dir": str(args.developer_dir),
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
