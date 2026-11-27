#!/usr/bin/env python3
"""Verify the linked R208 kernel against its build and forced-driver provenance."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts/y35a"))
from boot_layout import parse_macho  # noqa: E402


def tree_sha256(root: Path) -> str:
    root = root.resolve(strict=True)
    digest = hashlib.sha256()
    for item in sorted(root.rglob("*"), key=lambda path: path.relative_to(root).as_posix()):
        relative = item.relative_to(root).as_posix().encode("utf-8")
        mode = item.lstat().st_mode
        kind = b"L" if item.is_symlink() else b"D" if item.is_dir() else b"F"
        digest.update(kind)
        digest.update(struct.pack(">I", len(relative)))
        digest.update(relative)
        digest.update(struct.pack(">I", mode & 0o777))
        if item.is_symlink():
            digest.update(os.readlink(item).encode("utf-8"))
        elif item.is_file():
            digest.update(hashlib.sha256(item.read_bytes()).digest())
        elif not item.is_dir():
            raise ValueError(f"unsupported staged XNU filesystem entry: {item}")
    return digest.hexdigest()


def verify(kernel: Path, provenance_path: Path, driver_manifest_path: Path,
           staged_source_path: Path, *, nm_symbols: set[str] | None = None) -> dict:
    kernel = kernel.resolve(strict=True)
    provenance_path = provenance_path.resolve(strict=True)
    driver_manifest_path = driver_manifest_path.resolve(strict=True)
    staged_source_path = staged_source_path.resolve(strict=True)
    provenance = json.loads(provenance_path.read_text())
    driver_manifest = json.loads(driver_manifest_path.read_text())

    if provenance.get("status") not in {"prepared", "running", "failed", "complete"}:
        raise ValueError(f"unexpected native build terminal status: {provenance.get('status')!r}")
    if provenance.get("source_identity", {}).get("commit") != "494ffe1c29d37ca720c37328feb83069c9641b67":
        raise ValueError("kernel provenance does not bind pinned XNU 4903 source")
    if provenance.get("build_profile", {}).get("y35a_a53") is not True:
        raise ValueError("kernel was not built with Y35A A53 profile")
    if "-DXNU_Y35A_A53=1" not in provenance.get("build_profile", {}).get("other_cflags", []):
        raise ValueError("Y35A A53 macro is absent from recorded build flags")
    if provenance.get("build_profile", {}).get("phase_a_amfi") is not True:
        raise ValueError("kernel was not built with the requested Phase-A AMFI profile")
    if "-DXNU_Y35A_PHASE_A_AMFI=1" not in provenance.get("build_profile", {}).get("other_cflags", []):
        raise ValueError("Phase-A AMFI macro is absent from recorded build flags")
    build_profile = provenance.get("build_profile", {})
    source_patches = provenance.get("inputs", {}).get("source_diff", [])
    fallback_v3_present = any(
        item.get("path") == "patches/xnu/native-y35a-tf-emmc-root-fallback-v3.patch"
        for item in source_patches if isinstance(item, dict)
    )
    fallback_macro = "-DXNU_Y35A_STORAGE_FALLBACK=1"
    if fallback_v3_present and (
            build_profile.get("y35a_storage_fallback") is not True
            or fallback_macro not in build_profile.get("other_cflags", [])):
        raise ValueError("fallback-v3 source patch is present but its build macro is not enabled")
    if not fallback_v3_present and (
            build_profile.get("y35a_storage_fallback") is True
            or fallback_macro in build_profile.get("other_cflags", [])):
        raise ValueError("fallback build macro is enabled without the fallback-v3 source patch")
    if not provenance.get("staged_inputs", {}).get("source_tree_after_compatibility_sha256"):
        raise ValueError("final staged source tree hash is missing")
    if staged_source_path != Path(provenance.get("run_root", ""), "src").resolve(strict=True):
        raise ValueError("static verifier source root is not the staged source for this build")
    if tree_sha256(staged_source_path) != provenance["staged_inputs"]["source_tree_after_compatibility_sha256"]:
        raise ValueError("staged XNU tree bytes differ from build provenance")
    diff = provenance.get("staged_inputs", {}).get("source_compatibility_diff", {})
    if not diff.get("sha256") or not isinstance(diff.get("bytes"), int):
        raise ValueError("staged source compatibility diff is not bound")
    diff_path = Path(provenance["run_root"]) / "inputs/staged-source-compatibility.diff"
    if (not diff_path.is_file() or diff_path.stat().st_size != diff["bytes"]
            or hashlib.sha256(diff_path.read_bytes()).hexdigest() != diff["sha256"]):
        raise ValueError("staged source compatibility diff does not match its provenance")

    steps = {step.get("name"): step for step in provenance.get("steps", [])}
    for name in ("installhdrs", "build"):
        if steps.get(name, {}).get("status") != "passed" or steps[name].get("exit_code") != 0:
            raise ValueError(f"native build step {name} is not recorded as passed")

    artifact = provenance.get("kernel_artifact", {})
    digest = hashlib.sha256(kernel.read_bytes()).hexdigest()
    if artifact.get("sha256") != digest or artifact.get("bytes") != kernel.stat().st_size:
        raise ValueError("kernel bytes do not match build provenance")
    image = kernel.read_bytes()
    layout = parse_macho(image)

    integration = provenance.get("driver_integration", {})
    if (integration.get("status") != "passed" or integration.get("role") != "tf-storage"
            or integration.get("force_load") is not True):
        raise ValueError("build provenance does not contain a passed TF-storage force-load gate")
    if integration.get("missing_symbols") != []:
        raise ValueError("build provenance reports missing TF-storage symbols")
    archive_expected = driver_manifest.get("archive", {}).get("sha256")
    input_archives = provenance.get("inputs", {}).get("driver_archives", [])
    if len(input_archives) != 1 or input_archives[0].get("sha256") != archive_expected:
        raise ValueError("kernel build did not consume the archive bound by driver manifest")
    driver_manifest_input = provenance.get("inputs", {}).get("driver_manifest", {})
    if driver_manifest_input.get("sha256") != hashlib.sha256(driver_manifest_path.read_bytes()).hexdigest():
        raise ValueError("driver manifest differs from the native build input snapshot")

    if nm_symbols is None:
        result = subprocess.run(["xcrun", "nm", "-g", "-j", str(kernel)],
                                capture_output=True, text=True, check=False)
        if result.returncode:
            raise ValueError(result.stderr.strip() or "xcrun nm failed")
        nm_symbols = set(result.stdout.splitlines())
    required = set(integration.get("required_symbols", []))
    missing = sorted(required - nm_symbols)
    if not required or missing:
        raise ValueError("final kernel is missing TF-storage symbols: " + ", ".join(missing))

    return {
        "ok": True,
        "kernel_sha256": digest,
        "kernel_bytes": kernel.stat().st_size,
        "mach_o": {"cputype": 0x0100000C, "filetype": 2,
                   "base": hex(layout["base"]), "entry": hex(layout["entry"])},
        "xnu_commit": provenance["source_identity"]["commit"],
        "driver_archive_sha256": archive_expected,
        "required_driver_symbols": sorted(required),
        "missing_driver_symbols": [],
        "native_steps": {name: steps[name]["status"] for name in ("installhdrs", "build")},
        "staged_source_sha256": provenance["staged_inputs"]["source_tree_after_compatibility_sha256"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kernel", type=Path, required=True)
    parser.add_argument("--provenance", type=Path, required=True)
    parser.add_argument("--driver-manifest", type=Path, required=True)
    parser.add_argument("--staged-source", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = verify(args.kernel, args.provenance, args.driver_manifest, args.staged_source)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(json.dumps({"ok": False, "failure": str(error)}, indent=2))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
