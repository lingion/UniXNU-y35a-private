#!/usr/bin/env python3
"""Validate a UniXNU experiment contract without touching a device."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


REQUIRED_TOP = ("identity", "source", "build", "package", "probe", "controls", "run", "verdict")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def check_file(item: dict, label: str, failures: list[str]) -> None:
    path_value = item.get("path")
    if not path_value:
        failures.append(f"{label}: missing path")
        return
    path = Path(path_value)
    if not path.is_file():
        failures.append(f"{label}: file does not exist: {path}")
        return
    expected_size = item.get("size")
    if expected_size is not None and path.stat().st_size != int(expected_size):
        failures.append(f"{label}: size mismatch")
    expected_sha = item.get("sha256")
    if expected_sha:
        actual_sha = sha256(path)
        if actual_sha != expected_sha:
            failures.append(f"{label}: sha256 mismatch")


def check_file_group(value: object, label: str, failures: list[str]) -> None:
    if isinstance(value, dict):
        check_file(value, label, failures)
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            if not isinstance(item, dict):
                failures.append(f"{label}[{index}]: expected object")
                continue
            check_file(item, f"{label}[{index}]", failures)
        return
    failures.append(f"{label}: expected file object or list")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--require-device", action="store_true")
    args = parser.parse_args()

    failures: list[str] = []
    try:
        contract = json.loads(args.contract.read_text())
    except Exception as exc:
        print(json.dumps({"ok": False, "failures": [f"cannot read contract: {exc}"]}, indent=2))
        return 2

    if not isinstance(contract, dict):
        failures.append("contract must be an object")
        contract = {}
    for key in REQUIRED_TOP:
        if key not in contract:
            failures.append(f"missing top-level field: {key}")

    identity = contract.get("identity", {})
    if not identity.get("run_id"):
        failures.append("identity.run_id is required")

    source = contract.get("source", {})
    if not source.get("commit") or not source.get("tree_sha256"):
        failures.append("source.commit and source.tree_sha256 are required")
    patches = source.get("patches", [])
    if not isinstance(patches, list):
        failures.append("source.patches must be a list")
    else:
        for index, patch in enumerate(patches):
            if not isinstance(patch, dict):
                failures.append(f"source.patches[{index}] must be an object")
                continue
            if patch.get("order") != index:
                failures.append(f"source.patches[{index}].order must equal {index}")
            check_file(patch, f"source.patches[{index}]", failures)

    build = contract.get("build", {})
    check_file_group(build.get("provenance"), "build.provenance", failures)
    check_file_group(build.get("kernel"), "build.kernel", failures)

    package = contract.get("package", {})
    check_file_group(package.get("manifest"), "package.manifest", failures)
    check_file_group(package.get("image"), "package.image", failures)
    dt = package.get("dt", {})
    if dt.get("source_type") not in {"stock", "derived", "unknown"}:
        failures.append("package.dt.source_type must be stock, derived, or unknown")
    if dt.get("source_type") == "unknown":
        failures.append("package.dt.source_type=unknown cannot pass")
    if dt.get("source_type") == "derived":
        check_file_group(dt.get("source"), "package.dt.source", failures)
        check_file_group(dt.get("output"), "package.dt.output", failures)

    probe = contract.get("probe", {})
    for name in ("regular", "clear"):
        check_file_group(probe.get(name), f"probe.{name}", failures)
    record_map = probe.get("record_map")
    if not isinstance(record_map, dict) or not record_map:
        failures.append("probe.record_map must be a non-empty object")

    controls = contract.get("controls", {})
    for name in ("positive", "negative"):
        if not isinstance(controls.get(name), dict) or not controls[name].get("status"):
            failures.append(f"controls.{name}.status is required")

    run = contract.get("run", {})
    if int(run.get("runs", 0)) != 1:
        failures.append("run.runs must equal 1")
    if int(run.get("max_seconds", 0)) <= 0:
        failures.append("run.max_seconds must be positive")
    if run.get("retry_same_inputs") is not False:
        failures.append("run.retry_same_inputs must be false")

    requested = bool(run.get("device_run_allowed", False))
    device_allowed = requested and not failures
    if args.require_device and not device_allowed:
        failures.append("device run requested but contract is not fully valid")
        device_allowed = False

    result = {
        "ok": not failures,
        "device_run_allowed": device_allowed,
        "contract": str(args.contract),
        "failures": failures,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
