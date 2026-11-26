#!/usr/bin/env python3
"""Validate the offline TF/eMMC root fallback contract and its state model."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


TF_FAILURES = {"card_absent", "init_failed", "first_read_failed"}
ALLOWED_TF = TF_FAILURES | {"ready", "unknown"}
ALLOWED_EMMC = {"ready", "failed", "unavailable", "unknown"}


def select_root(tf_state: str, emmc_state: str) -> str:
    if tf_state == "ready":
        return "tf"
    if tf_state in TF_FAILURES and emmc_state == "ready":
        return "emmc"
    if tf_state in TF_FAILURES and emmc_state in {"failed", "unavailable"}:
        return "fail"
    return "unverified"


def validate_contract(contract: dict) -> list[str]:
    failures: list[str] = []
    if contract.get("schema_version") != 1:
        failures.append("schema_version must be 1")
    if contract.get("priority") != ["tf", "emmc"]:
        failures.append("priority must select tf before emmc")
    roots = contract.get("roots")
    if not isinstance(roots, dict) or set(roots) != {"tf", "emmc"}:
        failures.append("roots must contain exactly tf and emmc")
    policy = contract.get("failure_policy")
    expected_policy = {
        "tf_card_absent": "fallback-to-emmc-if-ready",
        "tf_init_failed": "fallback-to-emmc-if-ready",
        "tf_first_read_failed": "fallback-to-emmc-if-ready",
        "emmc_failed": "fail-closed",
        "both_failed": "fail-closed",
        "unknown": "unverified",
    }
    if policy != expected_policy:
        failures.append("failure_policy does not match the required matrix")
    implementation = contract.get("implementation", {})
    if implementation.get("coordinator_symbol") != "native_storage_select_root":
        failures.append("coordinator_symbol must be native_storage_select_root")
    if implementation.get("status") not in {"unverified", "implemented"}:
        failures.append("implementation.status must be unverified or implemented")
    if contract.get("device_run_allowed") is not False:
        failures.append("device_run_allowed must remain false")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, required=True)
    args = parser.parse_args()
    contract = json.loads(args.contract.read_text())
    failures = validate_contract(contract)
    result = {"ok": not failures, "failures": failures,
              "implementation": contract.get("implementation"),
              "device_run_allowed": contract.get("device_run_allowed")}
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
