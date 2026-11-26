#!/usr/bin/env python3
"""Merge pinned iOS 12 v1 trust caches and verify staged Mach-O coverage."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess
import uuid


HEADER_BYTES = 24
ENTRY_BYTES = 22
CDHASH_BYTES = 20
MACHO_MAGICS = {
    b"\xce\xfa\xed\xfe", b"\xcf\xfa\xed\xfe",
    b"\xfe\xed\xfa\xce", b"\xfe\xed\xfa\xcf",
    b"\xca\xfe\xba\xbe", b"\xbe\xba\xfe\xca",
    b"\xca\xfe\xba\xbf", b"\xbf\xba\xfe\xca",
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_v1(data: bytes, label: str) -> tuple[bytes, dict[bytes, tuple[int, int]]]:
    if len(data) < HEADER_BYTES:
        raise ValueError(f"{label} is shorter than a v1 header")
    version, cache_uuid, count = struct.unpack_from("<I16sI", data)
    if version != 1:
        raise ValueError(f"{label} has unsupported version {version}")
    if len(data) != HEADER_BYTES + count * ENTRY_BYTES:
        raise ValueError(f"{label} size does not match its entry count")

    entries: dict[bytes, tuple[int, int]] = {}
    previous = None
    for offset in range(HEADER_BYTES, len(data), ENTRY_BYTES):
        cdhash = data[offset:offset + CDHASH_BYTES]
        metadata = (data[offset + 20], data[offset + 21])
        if previous is not None and cdhash < previous:
            raise ValueError(f"{label} CDHashes are not sorted")
        if cdhash in entries and entries[cdhash] != metadata:
            raise ValueError(f"{label} repeats a CDHash with conflicting metadata")
        entries[cdhash] = metadata
        previous = cdhash
    return cache_uuid, entries


def combine_v1(restore: bytes, static: bytes) -> tuple[bytes, dict]:
    restore_uuid, restore_entries = parse_v1(restore, "RestoreTrustCache")
    static_uuid, static_entries = parse_v1(static, "StaticTrustCache")
    entries = dict(restore_entries)
    for cdhash, metadata in static_entries.items():
        if cdhash in entries and entries[cdhash] != metadata:
            raise ValueError("TrustCache inputs repeat a CDHash with conflicting metadata")
        entries[cdhash] = metadata

    seed = f"{sha256_bytes(restore)}:{sha256_bytes(static)}"
    merged_uuid = uuid.uuid5(uuid.NAMESPACE_OID, f"y35a-ios12-v1:{seed}").bytes
    if merged_uuid in (restore_uuid, static_uuid):
        raise ValueError("derived TrustCache UUID collides with an input cache")
    output = bytearray(struct.pack("<I16sI", 1, merged_uuid, len(entries)))
    for cdhash in sorted(entries):
        hash_type, flags = entries[cdhash]
        output.extend(struct.pack("<20sBB", cdhash, hash_type, flags))

    parse_v1(bytes(output), "combined TrustCache")
    return bytes(output), {
        "uuid": merged_uuid.hex(),
        "restore_entries": len(restore_entries),
        "static_entries": len(static_entries),
        "combined_entries": len(entries),
        "duplicate_entries": len(restore_entries) + len(static_entries) - len(entries),
        "restore_sha256": sha256_bytes(restore),
        "static_sha256": sha256_bytes(static),
        "combined_sha256": sha256_bytes(output),
        "combined_bytes": len(output),
    }


def verify_coverage(trusted_cdhashes: set[bytes], staged_cdhashes: dict[str, bytes],
                    expected_count: int) -> dict:
    if len(staged_cdhashes) != expected_count:
        raise ValueError(
            f"staged Mach-O count mismatch: expected {expected_count}, found {len(staged_cdhashes)}"
        )
    uncovered = sorted(path for path, cdhash in staged_cdhashes.items()
                       if cdhash not in trusted_cdhashes)
    if uncovered:
        raise ValueError(f"combined TrustCache does not cover staged Mach-Os: {uncovered}")
    return {
        "staged_macho_count": len(staged_cdhashes),
        "covered_macho_count": len(staged_cdhashes),
        "coverage": "complete",
        "machos": {
            path: cdhash.hex() for path, cdhash in sorted(staged_cdhashes.items())
        },
    }


def is_macho(path: Path) -> bool:
    with path.open("rb") as source:
        return source.read(4) in MACHO_MAGICS


def codesign_cdhash(path: Path) -> bytes:
    result = subprocess.run(
        ["/usr/bin/codesign", "--display", "--verbose=4", str(path)],
        capture_output=True, text=True, check=False,
    )
    output = result.stdout + result.stderr
    if result.returncode:
        raise ValueError(f"codesign could not read staged Mach-O {path}: {output.strip()}")
    matches = re.findall(r"\bCDHash=([0-9a-fA-F]{40})\b", output)
    if len(matches) != 1:
        raise ValueError(f"expected one SHA-1 CDHash for staged Mach-O {path}, found {len(matches)}")
    return bytes.fromhex(matches[0])


def verify_staged_root(root: Path, closure: dict, restore_path: Path,
                       static_path: Path, output_path: Path,
                       expected_count: int) -> dict:
    root = root.resolve(strict=True)
    closure_entries = closure.get("entries")
    if not isinstance(closure_entries, dict):
        raise ValueError("rootfs closure is missing its entry map")

    staged_cdhashes = {}
    for relative, binding in sorted(closure_entries.items()):
        relative_path = Path(relative)
        if relative_path.is_absolute() or ".." in relative_path.parts:
            raise ValueError(f"rootfs closure path escapes its tree: {relative}")
        path = (root / relative_path).resolve(strict=True)
        try:
            path.relative_to(root)
        except ValueError as error:
            raise ValueError(f"rootfs closure path escapes its tree: {relative}") from error
        if not path.is_file():
            raise ValueError(f"rootfs closure entry is not a file: {relative}")
        data_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        if data_hash != binding.get("sha256") or path.stat().st_size != binding.get("size"):
            raise ValueError(f"rootfs staged bytes differ from closure evidence: {relative}")
        if is_macho(path):
            staged_cdhashes[relative] = codesign_cdhash(path)

    restore = restore_path.read_bytes()
    static = static_path.read_bytes()
    combined, merge_report = combine_v1(restore, static)
    _, combined_entries = parse_v1(combined, "combined TrustCache")
    coverage = verify_coverage(set(combined_entries), staged_cdhashes, expected_count)
    output_path.write_bytes(combined)
    return {
        "merge": merge_report,
        "coverage": coverage,
        "restore_path": restore_path.name,
        "static_path": static_path.name,
        "combined_path": output_path.name,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--closure", required=True, type=Path)
    parser.add_argument("--restore", required=True, type=Path)
    parser.add_argument("--static", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--expected-macho-count", required=True, type=int)
    args = parser.parse_args()
    report = verify_staged_root(
        args.root, json.loads(args.closure.read_text()), args.restore, args.static,
        args.output, args.expected_macho_count,
    )
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
