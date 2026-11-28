#!/usr/bin/env python3
"""Validate the R208 TF/APFS device-package contract without claiming readiness."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


FALLBACK_SHA256 = "f886e829b94999e79af06964ee274992d975382827191912d2ab8c8a8bd291eb"
REQUIRED_TF_FAILURES = {"card_absent", "init_failed", "first_read_failed"}


def validate_contract(contract: dict) -> list[str]:
    failures: list[str] = []
    if contract.get("schema_version") != 1:
        failures.append("schema_version must be 1")
    if contract.get("kind") != "tf-apfs-device-package":
        failures.append("kind must be tf-apfs-device-package")
    if contract.get("status") not in {"design-only", "offline-only", "unverified"}:
        failures.append("status must remain non-device-qualified")

    qualification = contract.get("qualification", {})
    if qualification.get("device_run_allowed") is not False:
        failures.append("device_run_allowed must remain false")
    if qualification.get("runtime_qualified") is not False:
        failures.append("runtime_qualified must remain false")
    if qualification.get("device_ready") is not False:
        failures.append("device_ready must remain false")

    native = contract.get("native", {})
    if native.get("kernel_artifact_schema") != 2:
        failures.append("native kernel artifact schema 2 is required")
    if native.get("build_plan_required") is not True:
        failures.append("native build plan is required")
    if native.get("linked_gate_required") is not True:
        failures.append("linked gate is required")

    dt = contract.get("device_tree", {})
    if dt.get("source_type_required") != "stock-qcdt":
        failures.append("device package requires stock-qcdt provenance")
    if dt.get("status") not in {"unverified", "pending"}:
        failures.append("device-tree status must remain unverified")
    stock = dt.get("stock_qcdt_input", {})
    if stock.get("status") not in {"available", "unavailable", "pending"}:
        failures.append("stock-qcdt input status must be explicit")
    if stock.get("status") == "available" and not stock.get("sha256"):
        failures.append("available stock-qcdt input must have a SHA-256")
    if stock.get("status") == "unavailable" and stock.get("sha256") is not None:
        failures.append("unavailable stock-qcdt input cannot have a SHA-256")
    required_boot = stock.get("required_source_boot", {})
    if required_boot.get("status") != "historically-pinned-file-missing":
        failures.append("stock-QCDT source-boot availability status must be explicit")
    if required_boot.get("bytes") != 67108864:
        failures.append("stock PD1502A boot source must bind the historical full-partition size")
    if required_boot.get("sha256") != "92611f876a022fb5af1138f0591f5dafe2b359a226b2f0b28d292211f2fec012":
        failures.append("stock PD1502A boot source must bind the historical full-partition SHA-256")
    if required_boot.get("user_input_path") != "evidence/y35a-20261102/stock-boot.img":
        failures.append("stock PD1502A full-boot user input path must be fixed")
    if required_boot.get("transport") != "tracked-file-in-exact-dispatch-commit":
        failures.append("stock PD1502A boot input must be bound to the exact workflow commit")
    if required_boot.get("ci_generated_outputs") != ["y35a.qcdt", "y35a.qcdt.json"]:
        failures.append("stock-QCDT intake must generate the QCDT bytes and provenance in CI")
    if required_boot.get("qcdt_must_be_extracted_from_android_header_dt_range") is not True:
        failures.append("stock QCDT must be byte-matched to the Android header dt range")
    if required_boot.get("board_tuple") != [206, 8, 23]:
        failures.append("stock QCDT intake must bind the PD1502A board tuple")

    root_layout = contract.get("root_layout", {})
    if (root_layout.get("target_product_version") != "12.4.1"
            or root_layout.get("target_build") != "16G102"):
        failures.append("root-layout contract must remain bound to iOS 12.4.1 / 16G102")
    if root_layout.get("apfs_system_data_volume_group_required") is not False:
        failures.append("do not require iOS 13+ System/Data volume groups for the iOS 12.4.1 target")
    if root_layout.get("legacy_root_and_private_var_initialization") != "unverified":
        failures.append("legacy iOS 12 root and private/var initialization must remain unverified")
    if root_layout.get("status") != "target-specific-root-layout-pending-ci-source-review":
        failures.append("target-specific root-layout status must remain explicit")

    image = contract.get("tf_image", {})
    if image.get("partition_scheme") != "GPT":
        failures.append("TF image must use GPT")
    if image.get("root_filesystem") != "APFS":
        failures.append("TF root filesystem must be APFS")
    if image.get("card_binding_required") is not True:
        failures.append("exact card binding is required")
    if image.get("status") not in {"unverified", "pending"}:
        failures.append("TF image status must remain unverified")

    root = contract.get("root_selection", {})
    if root.get("coordinator_symbol") != "native_storage_select_root":
        failures.append("root coordinator symbol is not fixed")
    if root.get("linked_implementation_required") is not True:
        failures.append("linked root implementation is required")
    if root.get("status") not in {"unverified", "pending"}:
        failures.append("root-selection status must remain unverified")

    fallback = contract.get("fallback", {})
    patch = fallback.get("patch", {})
    if patch.get("sha256") != FALLBACK_SHA256:
        failures.append("fallback patch SHA does not match the audited candidate")
    if fallback.get("feature_macro") != "XNU_Y35A_STORAGE_FALLBACK":
        failures.append("fallback feature macro is not fixed")
    if fallback.get("boot_arg") != "emmc-boot-uuid":
        failures.append("fallback boot argument is not fixed")
    if not REQUIRED_TF_FAILURES.issubset(set(fallback.get("required_tf_failure_states", []))):
        failures.append("fallback must cover TF card absence, init failure and first-read failure")
    if fallback.get("emmc_ready_path_required") is not True:
        failures.append("eMMC ready path is required")
    if fallback.get("linked_implementation_status") not in {"unverified", "pending"}:
        failures.append("fallback implementation must remain unverified")

    for section in (contract.get("package", {}), contract.get("probe", {})):
        if section.get("status") not in {"unverified", "pending"}:
            failures.append("package and probe status must remain unverified")

    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, required=True)
    args = parser.parse_args()
    contract = json.loads(args.contract.read_text())
    failures = validate_contract(contract)
    result = {
        "ok": not failures,
        "failures": failures,
        "device_ready": contract.get("qualification", {}).get("device_ready"),
        "device_run_allowed": contract.get("qualification", {}).get("device_run_allowed"),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
