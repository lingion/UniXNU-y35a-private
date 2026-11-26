#!/usr/bin/env python3
"""Verify the two-area pram snapshot/report transport candidate."""
from __future__ import annotations

import argparse
import json


def interval(base: int, size: int) -> tuple[int, int]:
    if base < 0 or size <= 0:
        raise ValueError("addresses and sizes must be positive")
    return base, base + size


def overlaps(a: tuple[int, int], b: tuple[int, int]) -> bool:
    return a[0] < b[1] and b[0] < a[1]


def parse_int(value: str) -> int:
    return int(value, 0)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pram-base", required=True, type=parse_int)
    parser.add_argument("--pram-size", required=True, type=parse_int)
    parser.add_argument("--lk-stage-base", required=True, type=parse_int)
    parser.add_argument("--lk-stage-size", required=True, type=parse_int)
    parser.add_argument("--snapshot-base", required=True, type=parse_int)
    parser.add_argument("--snapshot-size", required=True, type=parse_int)
    parser.add_argument("--report-base", required=True, type=parse_int)
    parser.add_argument("--report-size", required=True, type=parse_int)
    parser.add_argument("--scratch-base", required=True, type=parse_int)
    parser.add_argument("--scratch-size", required=True, type=parse_int)
    parser.add_argument("--reserved", action="append", default=[], metavar="BASE:SIZE")
    args = parser.parse_args()

    pram = interval(args.pram_base, args.pram_size)
    lk_stage = interval(args.lk_stage_base, args.lk_stage_size)
    snapshot = interval(args.snapshot_base, args.snapshot_size)
    report = interval(args.report_base, args.report_size)
    scratch = interval(args.scratch_base, args.scratch_size)
    failures: list[str] = []

    if not (scratch[0] <= snapshot[0] and snapshot[1] <= scratch[1]):
        failures.append("snapshot is outside LK scratch mapping")
    if overlaps(snapshot, pram):
        failures.append("snapshot overlaps pram")
    if overlaps(snapshot, lk_stage):
        failures.append("snapshot overlaps LK staging source")
    if not (lk_stage[0] <= report[0] and report[1] <= lk_stage[1]):
        failures.append("report is outside the bytes staged by existing LK command")
    if overlaps(report, pram):
        failures.append("report overlaps pram")
    for raw in args.reserved:
        base, size = raw.split(":", 1)
        region = interval(parse_int(base), parse_int(size))
        if overlaps(snapshot, region):
            failures.append(f"snapshot overlaps reserved region {region[0]:#x}:{region[1] - region[0]:#x}")

    report_json = {
        "ok": not failures,
        "pram": [hex(x) for x in pram],
        "lk_stage": [hex(x) for x in lk_stage],
        "snapshot": [hex(x) for x in snapshot],
        "report": [hex(x) for x in report],
        "scratch": [hex(x) for x in scratch],
        "failures": failures,
    }
    print(json.dumps(report_json, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
