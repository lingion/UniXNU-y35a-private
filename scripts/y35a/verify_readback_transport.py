#!/usr/bin/env python3
"""Verify the declared transport mode of a Y35A readback manifest."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


MODES = ("minimal-boundary", "full-readback")
MINIMAL_RECORDS_OFFSET = 0x100
FULL_RECORDS_OFFSET = 0x40


def interval(base: int, size: int) -> tuple[int, int]:
    if base < 0 or size <= 0:
        raise ValueError("addresses and sizes must be positive")
    return base, base + size


def overlaps(left: tuple[int, int], right: tuple[int, int]) -> bool:
    return left[0] < right[1] and right[0] < left[1]


def contains(outer: tuple[int, int], inner: tuple[int, int]) -> bool:
    return outer[0] <= inner[0] and inner[1] <= outer[1]


def parse_int(value: str) -> int:
    return int(value, 0)


def parse_reserved(raw: str) -> tuple[int, int]:
    base, size = raw.split(":", 1)
    return interval(parse_int(base), parse_int(size))


def record_offset(record: dict) -> int:
    for key in ("report_offset", "transport_offset", "offset"):
        if key in record:
            return int(record[key])
    raise ValueError(f"record {record.get('name', '<unnamed>')} has no transport offset")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--mode", required=True, choices=MODES)
    parser.add_argument("--pram-base", required=True, type=parse_int)
    parser.add_argument("--pram-size", required=True, type=parse_int)
    parser.add_argument("--lk-stage-base", required=True, type=parse_int)
    parser.add_argument("--lk-stage-size", required=True, type=parse_int)
    parser.add_argument("--report-base", required=True, type=parse_int)
    parser.add_argument("--report-size", required=True, type=parse_int)
    parser.add_argument("--snapshot-base", required=True, type=parse_int)
    parser.add_argument("--snapshot-size", required=True, type=parse_int)
    parser.add_argument("--scratch-base", required=True, type=parse_int)
    parser.add_argument("--scratch-size", required=True, type=parse_int)
    parser.add_argument("--reserved", action="append", default=[], metavar="BASE:SIZE")
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text())
    pram = interval(args.pram_base, args.pram_size)
    lk_stage = interval(args.lk_stage_base, args.lk_stage_size)
    report = interval(args.report_base, args.report_size)
    snapshot = interval(args.snapshot_base, args.snapshot_size)
    scratch = interval(args.scratch_base, args.scratch_size)
    reserved = [parse_reserved(raw) for raw in args.reserved]
    failures: list[str] = []

    if manifest.get("transport_mode") != args.mode:
        failures.append(
            f"manifest transport_mode={manifest.get('transport_mode')!r} "
            f"does not declare {args.mode!r}"
        )

    if not contains(lk_stage, report):
        failures.append("report is outside the bytes uploaded by the existing LK command")
    if overlaps(report, pram):
        failures.append("report overlaps pram")
    if not contains(scratch, snapshot):
        failures.append("snapshot is outside LK scratch mapping")
    if overlaps(snapshot, pram):
        failures.append("snapshot overlaps pram")
    if overlaps(snapshot, lk_stage):
        failures.append("snapshot overlaps LK staging source")
    for region in reserved:
        if overlaps(snapshot, region):
            failures.append(
                f"snapshot overlaps reserved region {region[0]:#x}..{region[1]:#x}"
            )

    report_bytes = int(manifest.get("report_bytes", 0))
    if report_bytes <= 0:
        failures.append("manifest report_bytes must be positive")
    if args.mode == "minimal-boundary" and report_bytes > 0x1000:
        failures.append(f"minimal-boundary report_bytes={report_bytes:#x} exceeds 0x1000")
    if report_bytes > args.report_size:
        failures.append(f"report_bytes={report_bytes:#x} exceeds report-size={args.report_size:#x}")

    preserves_pram = manifest.get("pram_preserved")
    if not isinstance(preserves_pram, bool):
        failures.append("manifest pram_preserved must be a boolean")
    if args.mode == "minimal-boundary" and preserves_pram is not True:
        failures.append("minimal-boundary must declare pram_preserved=true")

    staged_bytes = int(manifest.get("staged_bytes", 0))
    if staged_bytes <= 0 or staged_bytes > args.lk_stage_size:
        failures.append(f"staged_bytes={staged_bytes:#x} exceeds LK stage-size={args.lk_stage_size:#x}")

    transport_ranges = []
    reserved_end = MINIMAL_RECORDS_OFFSET if args.mode == "minimal-boundary" else FULL_RECORDS_OFFSET
    for record in manifest.get("records", []):
        try:
            offset = record_offset(record)
            size = int(record["size"])
            if size <= 0:
                raise ValueError("non-positive size")
            if offset < 0:
                failures.append(f"record {record.get('name', '<unnamed>')} has a negative transport offset")
            record_range = interval(
                (args.report_base if args.mode == "minimal-boundary" else args.lk_stage_base) + offset,
                size,
            )
        except (KeyError, TypeError, ValueError) as exc:
            failures.append(f"invalid record {record.get('name', '<unnamed>')}: {exc}")
            continue
        allocation = report if args.mode == "minimal-boundary" else lk_stage
        if not contains(allocation, record_range):
            failures.append(f"record {record.get('name', '<unnamed>')} exceeds {args.mode} allocation")
        if args.mode == "minimal-boundary" and overlaps(record_range, pram):
            failures.append(f"record {record.get('name', '<unnamed>')} overlaps pram")
        name = str(record.get("name", "<unnamed>"))
        if offset < reserved_end:
            failures.append(
                f"record {name} overlaps reserved report head 0x0..{reserved_end:#x}"
            )
        transport_ranges.append((name, offset, offset + size))

    for index, (left_name, left_start, left_end) in enumerate(transport_ranges):
        for right_name, right_start, right_end in transport_ranges[index + 1:]:
            if left_start < right_end and right_start < left_end:
                failures.append(
                    f"transport ranges overlap: {left_name} overlaps {right_name}"
                )

    if args.mode == "full-readback" and preserves_pram is True:
        for record in manifest.get("records", []):
            try:
                record_range = interval(args.lk_stage_base + record_offset(record), int(record["size"]))
            except (KeyError, TypeError, ValueError):
                continue
            if overlaps(record_range, pram):
                failures.append("full-readback declares pram_preserved=true while a record overwrites pram")
                break

    report_json = {
        "ok": not failures,
        "mode": args.mode,
        "pram": [hex(value) for value in pram],
        "lk_stage": [hex(value) for value in lk_stage],
        "report": [hex(value) for value in report],
        "snapshot": [hex(value) for value in snapshot],
        "failures": failures,
    }
    print(json.dumps(report_json, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
