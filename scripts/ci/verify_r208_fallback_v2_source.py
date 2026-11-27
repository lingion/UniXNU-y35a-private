#!/usr/bin/env python3
"""Verify the R208 fallback-v2 patch against the exact public XNU source in CI."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile


def run(command: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(command, cwd=cwd, check=True, capture_output=True, text=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    args = parser.parse_args()
    repo_root = args.repo_root.resolve(strict=True)
    manifest_path = args.manifest.resolve(strict=True)
    manifest = json.loads(manifest_path.read_text())
    source = manifest["source_ref"]
    provenance_path = (repo_root / manifest["source_provenance"]).resolve(strict=True)
    provenance_sha = hashlib.sha256(provenance_path.read_bytes()).hexdigest()
    if provenance_sha != manifest.get("source_provenance_sha256"):
        print(json.dumps({
            "ok": False,
            "source_provenance": manifest["source_provenance"],
            "expected_sha256": manifest.get("source_provenance_sha256"),
            "actual_sha256": provenance_sha,
        }, sort_keys=True))
        raise SystemExit("candidate source provenance SHA mismatch; bind the reported actual digest")
    provenance = json.loads(provenance_path.read_text())
    if provenance.get("source", {}).get("commit") != source:
        raise SystemExit("candidate source provenance commit does not match source_ref")
    manifest_patches = [
        {key: item.get(key) for key in ("order", "target_tree", "path", "sha256")}
        for item in manifest.get("patches", [])
    ]
    provenance_patches = [
        {key: item.get(key) for key in ("order", "target_tree", "path", "sha256")}
        for item in provenance.get("patches", [])
    ]
    if provenance_patches != manifest_patches:
        print(json.dumps({
            "ok": False,
            "source": source,
            "manifest_patches": manifest_patches,
            "provenance_patches": provenance_patches,
        }, sort_keys=True))
        raise SystemExit("candidate ordered patch list differs from source provenance")
    patch_entries = [item for item in manifest["patches"]
                     if item["path"] == "patches/xnu/native-y35a-tf-emmc-root-fallback-v2.patch"]
    if len(patch_entries) != 1:
        raise SystemExit("fallback-v2 patch must appear exactly once in the candidate manifest")
    patch = (repo_root / patch_entries[0]["path"]).resolve(strict=True)
    with tempfile.TemporaryDirectory(prefix="r208-xnu-fallback-v2-") as directory:
        checkout = Path(directory) / "xnu"
        run(["git", "clone", "--filter=blob:none", "--no-checkout",
             "https://github.com/apple-oss-distributions/xnu.git", str(checkout)])
        run(["git", "-C", str(checkout), "fetch", "--depth=1", "origin", source])
        run(["git", "-C", str(checkout), "checkout", "--detach", source])
        actual = run(["git", "-C", str(checkout), "rev-parse", "HEAD"]).stdout.strip()
        if actual != source:
            raise SystemExit(f"XNU source identity mismatch: {actual} != {source}")
        run(["git", "-C", str(checkout), "apply", "--check", str(patch)])
    print(json.dumps({"ok": True, "source_ref": source,
                      "patch": patch_entries[0]["path"],
                      "patch_sha256": patch_entries[0]["sha256"],
                      "source_provenance_sha256": provenance_sha}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
