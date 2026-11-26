#!/usr/bin/env python3
"""Sync reproducible UniXNU source and metadata into the private GitHub mirror."""

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path

EXCLUDED_DIRS = {
    ".git",
    ".superpowers",
    "build",
    "Build",
    "device-backups",
    "evidence",
    "out",
    "reboot-checkpoints",
    "refer",
    "upstream-refresh",
}
EXCLUDED_SUFFIXES = {
    ".a", ".bin", ".dbr", ".dmg", ".dylib", ".img", ".ipsw", ".macho", ".o", ".raw", ".tar"
}


def run(*args: str, cwd: Path) -> str:
    return subprocess.check_output(args, cwd=cwd, text=True).strip()


def excluded(path: Path) -> bool:
    if any(part in EXCLUDED_DIRS for part in path.parts):
        return True
    return path.suffix in EXCLUDED_SUFFIXES or path.name in {".device.lock"}


def source_files(source: Path) -> list[Path]:
    raw = subprocess.check_output(
        ["git", "ls-files", "-c", "-z"], cwd=source, text=False
    ).decode("utf-8", "surrogateescape")
    tracked = [Path(item) for item in raw.split("\0") if item]
    return [path for path in tracked if not excluded(path)]


def sync(source: Path, mirror: Path) -> int:
    changed = 0
    for relative in source_files(source):
        source_path = source / relative
        mirror_path = mirror / relative
        if not source_path.is_file():
            continue
        mirror_path.parent.mkdir(parents=True, exist_ok=True)
        if not mirror_path.exists() or source_path.read_bytes() != mirror_path.read_bytes():
            shutil.copy2(source_path, mirror_path)
            changed += 1
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--mirror-root", type=Path, required=True)
    parser.add_argument("--push", action="store_true")
    parser.add_argument("--message", default="chore(sync): update private UniXNU mirror")
    args = parser.parse_args()

    source = args.source_root.resolve()
    mirror = args.mirror_root.resolve()
    if not (source / ".git").exists() and not (source / ".git").is_file():
        raise SystemExit(f"source is not a git worktree: {source}")
    if not (mirror / ".git").exists():
        raise SystemExit(f"mirror is not a git repository: {mirror}")

    changed = sync(source, mirror)
    subprocess.run(["git", "-C", str(mirror), "diff", "--check"], check=True)
    status = run("git", "status", "--short", cwd=mirror)
    if not status:
        print("no changes")
        return 0

    subprocess.run(["git", "-C", str(mirror), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(mirror), "commit", "-m", args.message], check=True)
    if args.push:
        subprocess.run(["git", "-C", str(mirror), "push", "origin", "main"], check=True)
    print(f"synced_files={changed}")
    print(status)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
