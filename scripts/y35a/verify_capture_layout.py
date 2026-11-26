#!/usr/bin/env python3
"""Verify Y35A readback geometry under its explicitly declared transport mode."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def interval(base: int, size: int) -> tuple[int, int]:
    if base < 0 or size <= 0:
        raise ValueError("addresses and sizes must be positive")
    return base, base + size


def overlaps(left: tuple[int, int], right: tuple[int, int]) -> bool:
    return left[0] < right[1] and right[0] < left[1]


def parse_int(value: str) -> int:
    return int(value, 0)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--pram-base", required=True, type=parse_int)
    parser.add_argument("--pram-size", required=True, type=parse_int)
    parser.add_argument("--stage-base", required=True, type=parse_int)
    parser.add_argument("--stage-size", required=True, type=parse_int)
    parser.add_argument("--panic-dest", type=parse_int)
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text())
    pram = interval(args.pram_base, args.pram_size)
    stage = interval(args.stage_base, args.stage_size)
    failures: list[str] = []
    warnings: list[str] = []
    mode = manifest.get("transport_mode")
    preserves_pram = manifest.get("pram_preserved")
    destructive = mode == "full-readback" and preserves_pram is False
    minimal = mode == "minimal-boundary"

    if mode not in (None, "minimal-boundary", "full-readback"):
        failures.append(f"unsupported transport_mode={mode!r}")
    if mode == "minimal-boundary" and preserves_pram is not True:
        failures.append("minimal-boundary must declare pram_preserved=true")
    if mode == "full-readback" and preserves_pram is not False:
        failures.append("full-readback must explicitly declare pram_preserved=false")

    if overlaps(stage, pram) and not destructive:
        failures.append(
            f"stage {stage[0]:#x}..{stage[1]:#x} overlaps pram "
            f"{pram[0]:#x}..{pram[1]:#x}"
        )
    if destructive:
        warnings.append("pram is intentionally overwritten by full-readback records")

    staged_bytes = int(manifest.get("staged_bytes", 0))
    if staged_bytes <= 0 or staged_bytes > args.stage_size:
        failures.append(f"staged_bytes={staged_bytes:#x} exceeds stage-size={args.stage_size:#x}")

    record_ranges: list[tuple[str, tuple[int, int]]] = []
    for record in manifest.get("records", []):
        offset = int(record["offset"])
        size = int(record["size"])
        record_base = args.stage_base
        if minimal:
            offset = int(record.get("report_offset", offset))
            record_base = args.stage_base
        record_range = interval(record_base + offset, size)
        record_ranges.append((record["name"], record_range))
        if record_range[1] > stage[1]:
            failures.append(f"record {record['name']} exceeds staging allocation")
        if overlaps(record_range, pram) and not destructive:
            failures.append(f"record {record['name']} overlaps pram")

    panic_dest = None
    if args.panic_dest is not None and not minimal:
        panic_dest = interval(args.panic_dest, int(manifest.get("panic_log_limit", 0x1000)))
        if overlaps(panic_dest, pram):
            failures.append(f"panic destination overlaps pram: {panic_dest[0]:#x}..{panic_dest[1]:#x}")
        if not (stage[0] <= panic_dest[0] and panic_dest[1] <= stage[1]):
            failures.append("panic destination is outside staging allocation")
        for name, record_range in record_ranges:
            if overlaps(record_range, panic_dest):
                failures.append(f"record {name} overlaps panic report destination")

    if mode == "full-readback":
        try:
            snapshot_offset = int(manifest["eph_snapshot_offset"])
            snapshot_bytes = int(manifest["eph_snapshot_bytes"])
            snapshot_write_bytes = int(manifest["eph_snapshot_write_bytes"])
            snapshot = interval(args.stage_base + snapshot_offset, snapshot_write_bytes)
            if snapshot_bytes <= 0 or snapshot_bytes > snapshot_write_bytes:
                failures.append("EPH snapshot logical bytes exceed its physical write extent")
            if snapshot_write_bytes % 16:
                failures.append("EPH snapshot write extent must be 16-byte aligned")
            if not (stage[0] <= snapshot[0] and snapshot[1] <= stage[1]):
                failures.append("EPH snapshot write extent is outside the LK staging allocation")

            stamp_offset = int(manifest["stamp_snapshot_offset"])
            stamp_bytes = int(manifest["stamp_snapshot_bytes"])
            stamp = interval(args.stage_base + stamp_offset, stamp_bytes)
            if not (stage[0] <= stamp[0] and stamp[1] <= stage[1]):
                failures.append("stamp snapshot is outside the LK staging allocation")
            if overlaps(snapshot, stamp):
                failures.append("EPH and stamp snapshot slots overlap")
            for name, record_range in record_ranges:
                if overlaps(snapshot, record_range):
                    failures.append(f"EPH snapshot write extent overlaps record {name}")
                if overlaps(stamp, record_range):
                    failures.append(f"stamp snapshot overlaps record {name}")
            if panic_dest is not None and overlaps(snapshot, panic_dest):
                failures.append("EPH snapshot write extent overlaps panic report destination")
            if "fault_state_offset" not in manifest or "fault_state_bytes" not in manifest:
                failures.append("full-readback manifest must describe its fault-state interval")
            else:
                fault_state = interval(
                    args.stage_base + int(manifest["fault_state_offset"]),
                    int(manifest["fault_state_bytes"]),
                )
                if not (stage[0] <= fault_state[0] and fault_state[1] <= stage[1]):
                    failures.append("fault-state interval is outside the LK staging allocation")
                if overlaps(snapshot, fault_state):
                    failures.append("EPH snapshot write extent overlaps fault-state interval")
                if overlaps(stamp, fault_state):
                    failures.append("stamp snapshot overlaps fault-state interval")
                if panic_dest is not None and overlaps(fault_state, panic_dest):
                    failures.append("fault-state interval overlaps panic report destination")
        except (KeyError, TypeError, ValueError) as exc:
            failures.append(f"invalid full-readback snapshot write geometry: {exc}")

    report = {
        "ok": not failures,
        "mode": mode or "legacy-strict",
        "preservation": "destructive" if destructive else "preserved",
        "pram": [hex(x) for x in pram],
        "stage": [hex(x) for x in stage],
        "failures": failures,
        "warnings": warnings,
    }
    print(json.dumps(report, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
