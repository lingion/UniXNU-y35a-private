#!/usr/bin/env python3
"""Verify the R208 fallback-v2 patch against the exact public XNU source in CI."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import tempfile


def run(command: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(command, cwd=cwd, check=True, capture_output=True, text=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    source = manifest["source_ref"]
    patch_entries = [item for item in manifest["patches"]
                     if item["path"] == "patches/xnu/native-y35a-tf-emmc-root-fallback-v2.patch"]
    if len(patch_entries) != 1:
        raise SystemExit("fallback-v2 patch must appear exactly once in the candidate manifest")
    patch = args.repo_root / patch_entries[0]["path"]
    if not patch.is_file():
        raise SystemExit(f"missing fallback-v2 patch: {patch}")
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
    print(json.dumps({"ok": True, "source_ref": source, "patch": str(patch)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
