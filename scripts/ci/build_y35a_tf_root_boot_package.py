#!/usr/bin/env python3
"""Create a non-boot-qualified Y35A RAM-loaded kernel package selecting a TF APFS root."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/y35a"))
sys.path.insert(0, str(ROOT / "scripts/ci"))

import package_native
from build_y35a_ci_package import verify_android_container
from build_y35a_tf_apfs_image import (
    extract_qcdt_from_pd1502a_boot_image,
    sha256,
    validate_root_tree_artifact_binding,
)
from extract_y35a_stock_qcdt import extract as extract_stock_qcdt

FALLBACK_V3_PATH = "patches/xnu/native-y35a-tf-emmc-root-fallback-v3.patch"
FALLBACK_V3_SHA256 = "01c105678d3c959a868bafb774cbded77bde3e5b01b31fd4f34db845e7a5cf25"


def validate_tf_artifact_binding(run: dict, artifact: dict, *, run_id: str,
                                 artifact_id: int, artifact_digest: str,
                                 expected_branch: str, expected_sha: str) -> dict:
    expected_name = f"y35a-tf-apfs-intermediate-{run_id}"
    jobs = run.get("jobs", [])
    if (str(run.get("databaseId")) != run_id
            or run.get("workflowName") != "Y35A CI RAM-boot package"
            or run.get("conclusion") != "success"
            or run.get("headBranch") != expected_branch
            or run.get("headSha") != expected_sha
            or not re.fullmatch(r"[0-9a-f]{40}", expected_sha)):
        raise ValueError("selected TF/APFS run is not the expected successful branch/SHA run")
    if not any(job.get("name") == "tf-apfs-intermediate" and job.get("conclusion") == "success"
               for job in jobs):
        raise ValueError("selected run has no successful tf-apfs-intermediate job")
    workflow_run = artifact.get("workflow_run", {})
    if (artifact.get("id") != artifact_id
            or artifact.get("name") != expected_name
            or artifact.get("digest") != artifact_digest
            or artifact.get("expired") is not False
            or workflow_run.get("id") != int(run_id)
            or workflow_run.get("head_sha") != expected_sha
            or workflow_run.get("head_branch") != expected_branch):
        raise ValueError("TF/APFS artifact API record does not match the selected run, branch and digest")
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", artifact_digest):
        raise ValueError("TF/APFS artifact digest is malformed")
    return {
        "run_id": run_id,
        "head_sha": expected_sha,
        "run_head_sha": expected_sha,
        "artifact_id": artifact_id,
        "artifact_name": expected_name,
        "artifact_digest": artifact_digest,
        "head_branch": expected_branch,
    }


def verify_tf_root_inputs(image: Path, report_path: Path, binding_path: Path,
                          report: dict, binding: dict, stock_boot: Path,
                          root_tree_artifact_binding: dict,
                          expected_source_commit: str, expected_branch: str) -> dict:
    image = image.resolve(strict=True)
    report_path = report_path.resolve(strict=True)
    binding_path = binding_path.resolve(strict=True)
    image_sha = sha256(image)
    report_sha = sha256(report_path)
    image_record = report.get("image", {})
    apfs_record = report.get("apfs", {})
    qcdt = report.get("device_tree_input", {})
    qualification = report.get("qualification")
    if (report.get("status") != "intermediate-built"
            or report.get("candidate_kind") != "stock-qcdt-intermediate"
            or report.get("bootable") is not False
            or report.get("device_ready") is not False
            or report.get("device_run_allowed") is not False):
        raise ValueError("TF/APFS root input is not the expected unqualified intermediate")
    if (image_record.get("path") != image.name
            or image_record.get("bytes") != image.stat().st_size
            or image_record.get("sha256") != image_sha):
        raise ValueError("TF/APFS image bytes do not match its report")
    if (binding.get("schema_version") != 1
            or binding.get("report_path") != report_path.name
            or binding.get("report_sha256") != report_sha):
        raise ValueError("TF/APFS report binding sidecar does not match report bytes")
    root_archive = image.parent / "root-tree.tar"
    verified_root_artifact = validate_root_tree_artifact_binding(
        root_tree_artifact_binding, root_archive,
    )
    if (verified_root_artifact["head_branch"] != expected_branch
            or report.get("root_tree_artifact") != verified_root_artifact
            or report.get("root_tree_transport", {}).get("archive_sha256") != verified_root_artifact["archive_sha256"]
            or report.get("root_tree_transport", {}).get("tree_sha256") != report.get("root_tree", {}).get("sha256")):
        raise ValueError("TF/APFS report does not bind the exact root-tree artifact and restored tree")
    stock_record = extract_qcdt_from_pd1502a_boot_image(stock_boot)
    stock_source = qcdt.get("stock_boot_source", {})
    if (qcdt.get("source_type") != "stock-qcdt"
            or qcdt.get("sha256") != stock_record["qcdt_sha256"]
            or qcdt.get("bytes") != stock_record["qcdt_bytes"]
            or stock_source.get("sha256") != stock_record["boot_sha256"]
            or stock_source.get("bytes") != stock_record["boot_bytes"]
            or stock_source.get("qcdt_offset") != stock_record["qcdt_offset"]
            or stock_source.get("qcdt_bytes") != stock_record["qcdt_bytes"]
            or stock_source.get("source_repository_commit") != expected_source_commit):
        raise ValueError("TF/APFS QCDT provenance does not match the pinned PD1502A stock boot")
    if stock_source.get("source_repository_path") != \
            "evidence/y35a-20261102/stock-boot.img":
        raise ValueError("TF/APFS report does not bind the tracked PD1502A stock boot path")
    volume_uuid = apfs_record.get("volume_uuid")
    if not volume_uuid:
        raise ValueError("TF/APFS report has no generated APFS volume UUID")
    if (report.get("gpt_apfs", {}).get("partition_map_type") != "GPT"
            or report.get("gpt_apfs", {}).get("filesystem_type") != "apfs"):
        raise ValueError("TF/APFS root input lacks the GPT/APFS structural checks")
    card_binding = report.get("card_binding", {})
    if card_binding.get("status") != "pending" or card_binding.get("device") is not None:
        raise ValueError("offline TF/APFS intermediate must not claim physical card binding")
    if (qualification != "stock-qcdt-intermediate-unqualified"
            or report.get("ios_system_image") is not False
            or report.get("springboard_included") is not False
            or report.get("touch_runtime_validated") is not False):
        raise ValueError("TF/APFS root input has an unexpected or qualified intermediate scope")
    return {
        "image_sha256": image_sha,
        "image_bytes": image.stat().st_size,
        "report_sha256": report_sha,
        "apfs_volume_uuid": volume_uuid,
        "apfs_volume_name": apfs_record.get("volume_name"),
        "root_tree_sha256": report.get("root_tree", {}).get("sha256"),
        "root_tree_scope": report.get("root_tree", {}).get("scope"),
        "root_tree_artifact": verified_root_artifact,
        "card_binding": card_binding,
        "stock_boot_source": qcdt["stock_boot_source"],
        "root_selection_status": report.get("root_selection", {}).get("status"),
        "fallback_status": report.get("fallback", {}).get("status"),
    }


def validate_package_root_tree(root_binding: dict, package_provenance: dict) -> None:
    rootfs = package_provenance.get("rootfs", {})
    if root_binding.get("root_tree_scope") != "diagnostic-root-until-production-root-is-bound":
        raise ValueError("external TF image must contain the current diagnostic root closure")
    if root_binding.get("root_tree_sha256") != rootfs.get("tree_sha256"):
        raise ValueError("TF APFS root tree differs from the tree whose Mach-Os are covered by this package TrustCache")
    coverage = package_provenance.get("trust_cache", {}).get("combined", {}).get("coverage", {})
    if coverage.get("coverage") != "complete" or coverage.get("staged_macho_count") != 58:
        raise ValueError("external diagnostic root lacks complete TrustCache coverage for the staged closure")


def build_bundle(*, package_dir: Path, tf_artifact_dir: Path, run_json: Path,
                 artifact_json: Path, run_id: str, artifact_id: int,
                 artifact_digest: str, expected_branch: str, expected_sha: str,
                 package_source_sha: str, stock_boot: Path, output: Path,
                 compiler: Path, objcopy: Path) -> dict:
    package_dir = package_dir.resolve(strict=True)
    tf_artifact_dir = tf_artifact_dir.resolve(strict=True)
    stock_boot = stock_boot.resolve(strict=True)
    if output.exists() and any(output.iterdir()):
        raise ValueError(f"refusing to overwrite non-empty TF/APFS boot bundle: {output}")
    output.mkdir(parents=True, exist_ok=True)
    run = json.loads(run_json.read_text())
    artifact = json.loads(artifact_json.read_text())
    artifact_binding = validate_tf_artifact_binding(
        run, artifact, run_id=run_id, artifact_id=artifact_id,
        artifact_digest=artifact_digest, expected_branch=expected_branch,
        expected_sha=expected_sha,
    )
    if expected_sha != package_source_sha:
        raise ValueError("TF/APFS artifact commit must equal the exact package-source commit")
    image = tf_artifact_dir / "y35a-tf-root.apfs.img"
    report_path = tf_artifact_dir / "y35a-tf-root.apfs.img.json"
    report_binding_path = tf_artifact_dir / "y35a-tf-root.apfs.img.json.binding.json"
    report = json.loads(report_path.read_text())
    report_binding = json.loads(report_binding_path.read_text())
    root_tree_artifact_binding = json.loads(
        (tf_artifact_dir / "root-tree-artifact-binding.json").read_text()
    )
    tf_binding = verify_tf_root_inputs(
        image, report_path, report_binding_path, report, report_binding,
        stock_boot, root_tree_artifact_binding,
        expected_source_commit=expected_sha, expected_branch=expected_branch,
    )
    if report.get("device_tree_input", {}).get("stock_boot_source", {}).get(
            "source_repository_commit") != artifact_binding["head_sha"]:
        raise ValueError("TF intermediate stock-boot provenance commit differs from its artifact run SHA")
    native_artifact = json.loads((package_dir / "native-kernel-artifact.json").read_text())
    package_provenance = json.loads((package_dir / "package-provenance.json").read_text())
    package_manifest = json.loads((package_dir / "package-manifest.json").read_text())
    native_plan = json.loads((package_dir / "native-build-plan.json").read_text())
    native_binding = package_provenance.get("native_build", {})
    native_api_binding = package_provenance.get("native_kernel_artifact_api", {})
    kernel = package_dir / "kernel.macho"
    trustcache = package_dir / "combined-trustcache.bin"
    if not kernel.is_file() or sha256(kernel) != native_artifact.get("kernel_sha256"):
        raise ValueError("RAM package kernel differs from its native artifact manifest")
    native_run_id = str(package_provenance.get("native_build", {}).get("run_id", ""))
    if (native_binding.get("head_sha") != native_artifact.get("head_sha")
            or str(native_artifact.get("run_id")) != native_run_id
            or native_api_binding.get("run_id") != native_run_id
            or native_api_binding.get("head_sha") != native_artifact.get("head_sha")
            or not isinstance(native_api_binding.get("id"), int)
            or not re.fullmatch(r"sha256:[0-9a-f]{64}", str(native_api_binding.get("digest", "")))
            or not native_run_id.isdecimal()):
        raise ValueError("RAM package does not carry a valid exact native build binding")
    trust_coverage = package_provenance.get("trust_cache", {}).get("combined", {}).get("coverage", {})
    if (package_provenance.get("status") != "offline-package-complete"
            or package_provenance.get("candidate_kind") != "launchd-diagnostic-ramboot"
            or package_provenance.get("package_source", {}).get("commit") != package_source_sha
            or package_provenance.get("native_build_status") != "complete"
            or package_provenance.get("qualification", {}).get("device_run_allowed") is not False
            or package_provenance.get("qualification", {}).get("runtime_qualified") is not False
            or package_manifest.get("status") != "offline-built experimental image; not device-boot validated"
            or package_manifest.get("kernel_sha256") != sha256(kernel)
            or package_manifest.get("boot_image_sha256") != sha256(package_dir / "boot3.img")
            or package_provenance.get("package", {}).get("image_sha256") != sha256(package_dir / "boot3.img")
            or trust_coverage.get("coverage") != "complete"
            or trust_coverage.get("staged_macho_count") != 58):
        raise ValueError("RAM package is not the expected complete, unqualified 58-Mach-O launchd diagnostic")
    fallback_patches = [
        item for item in native_plan.get("patches", [])
        if Path(item.get("path", "")).name == Path(FALLBACK_V3_PATH).name
        and item.get("sha256") == FALLBACK_V3_SHA256
    ]
    if len(fallback_patches) != 1:
        raise ValueError("native build plan does not bind the exact fallback-v3 patch once")
    if artifact_binding["head_sha"] != package_source_sha:
        raise ValueError("TF root artifact must use the exact package-source commit")
    validate_package_root_tree(tf_binding, package_provenance)
    if not trustcache.is_file() or package_provenance.get("qualification", {}).get("runtime_qualified") is not False:
        raise ValueError("diagnostic RAM package lacks its trust cache or qualification boundary")
    stock_boot_record = extract_qcdt_from_pd1502a_boot_image(stock_boot)
    stock_intake = extract_stock_qcdt(
        stock_boot, output / "stock-qcdt-intake", package_source_sha,
        "evidence/y35a-20261102/stock-boot.img",
    )
    if (stock_intake["provenance"]["sha256"] != report["device_tree_input"].get("sha256")
            or stock_intake["provenance"]["qcdt_offset"] !=
               report["device_tree_input"]["stock_boot_source"].get("qcdt_offset")
            or stock_intake["provenance"]["qcdt_bytes"] !=
               report["device_tree_input"]["stock_boot_source"].get("qcdt_bytes")):
        raise ValueError("TF/APFS report QCDT extraction differs from this package's stock boot intake")
    reference = {
        "schema_version": 1,
        "status": "verified-nonbootable-tf-apfs-input",
        "artifact": artifact_binding,
        **tf_binding,
        "stock_qcdt_sha256": stock_intake["provenance"]["sha256"],
        "stock_qcdt_provenance_sha256": sha256(stock_intake["provenance_path"]),
        "native_run_id": native_run_id,
        "native_head_sha": native_artifact["head_sha"],
        "native_artifact_id": native_api_binding["id"],
        "native_artifact_digest": native_api_binding["digest"],
        "native_kernel_sha256": sha256(kernel),
        "device_run_allowed": False,
        "bootable": False,
        "tf_root_uuid": {
            "status": "bound-to-this-apfs-artifact",
            "value": tf_binding["apfs_volume_uuid"],
            "sha256": hashlib.sha256(
                tf_binding["apfs_volume_uuid"].encode("utf-8")
            ).hexdigest(),
        },
        "emmc_root_uuid": {"status": "unavailable", "value": None, "sha256": None},
        "emmc_fallback_status": "unavailable-no-eMMC-APFS-root-UUID",
    }
    if reference["image_sha256"] != report["image"]["sha256"]:
        raise ValueError("TF root reference image hash differs from the report")
    ref_path = output / "tf-root-reference.json"
    ref_path.write_text(json.dumps(reference, indent=2, sort_keys=True) + "\n")
    package_output = output / "tf-boot3-package"
    command = [
        sys.executable, str(ROOT / "scripts/y35a/package_native.py"),
        "--kernel", str(kernel), "--stock-boot", str(stock_boot),
        "--directory", str(package_output), "--trust-cache", str(trustcache),
        "--compiler", str(compiler), "--objcopy", str(objcopy),
        "--external-root-uuid", reference["apfs_volume_uuid"],
        "--external-root-reference", str(ref_path),
    ]
    subprocess.run(command, cwd=ROOT, check=True)
    manifest = json.loads((package_output / "manifest.json").read_text())
    expected_cmdline = package_native.make_external_root_command_line(
        reference["apfs_volume_uuid"],
    )
    boot_args = (package_output / "boot-args.bin").read_bytes()
    actual_cmdline = boot_args[0x6C:0x6C + 256].split(b"\0", 1)[0].decode("ascii")
    if actual_cmdline != expected_cmdline:
        raise ValueError("TF external-root boot arguments do not match the APFS report UUID")
    container = verify_android_container(
        package_output / "boot3.img",
        manifest["device_tree"]["selected_qcdt_sha256"],
        manifest["package_components"]["entry.bin"]["sha256"],
        hashlib.sha256(b"").hexdigest(),
        allow_empty_second=True,
    )
    if (manifest.get("kernel_sha256") != sha256(kernel)
            or manifest.get("boot_image_sha256") != container["image_sha256"]
            or manifest.get("boot_arguments") != expected_cmdline
            or manifest.get("root_selection", {}).get("tf_volume_uuid") != reference["apfs_volume_uuid"]
            or manifest.get("root_selection", {}).get("mode") != "external-apfs-diagnostic"):
        raise ValueError("external-root boot3 manifest does not bind the kernel, UUID boot args, and APFS root")
    shutil.copy2(report_path, output / report_path.name)
    shutil.copy2(report_binding_path, output / report_binding_path.name)
    shutil.copy2(stock_intake["qcdt_path"], output / "y35a.qcdt")
    shutil.copy2(stock_intake["provenance_path"], output / "y35a.qcdt.json")
    files = {}
    for path in sorted(output.rglob("*")):
        if path.is_file() and path.name not in {"bundle-provenance.json", "SHA256SUMS"}:
            files[path.relative_to(output).as_posix()] = {
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
    bundle_provenance = {
        "schema_version": 1,
        "status": "offline-external-root-diagnostic-bundle-built",
        "candidate_kind": "launchd-diagnostic-tf-apfs-root",
        "native": {"run_id": native_run_id, "head_sha": native_artifact["head_sha"],
                   "kernel_sha256": sha256(kernel)},
        "tf_apfs_artifact": artifact_binding,
        "tf_root": tf_binding,
        "tf_apfs_image_delivery": {
            "artifact_name": artifact_binding["artifact_name"],
            "artifact_id": artifact_binding["artifact_id"],
            "artifact_digest": artifact_binding["artifact_digest"],
            "image_sha256": tf_binding["image_sha256"],
            "image_bytes": tf_binding["image_bytes"],
            "delivery_note": "download the separately bound TF/APFS intermediate artifact; image bytes are not duplicated in this boot bundle",
        },
        "stock_boot_sha256": stock_boot_record["boot_sha256"],
        "stock_qcdt_sha256": stock_intake["provenance"]["sha256"],
        "boot3": container,
        "boot_arguments": expected_cmdline,
        "root_tree_scope": tf_binding["root_tree_scope"],
        "fallback": {
            "selector": "emmc-boot-uuid",
            "patch_path": FALLBACK_V3_PATH,
            "patch_sha256": FALLBACK_V3_SHA256,
            "status": reference["emmc_fallback_status"],
            "device_run_allowed": False,
        },
        "qualification": {
            "bootable": False,
            "device_ready": False,
            "device_run_allowed": False,
            "runtime_qualified": False,
            "springboard_included": False,
            "touch_runtime_validated": False,
        },
        "files": files,
    }
    provenance_path = output / "bundle-provenance.json"
    provenance_path.write_text(json.dumps(bundle_provenance, indent=2, sort_keys=True) + "\n")
    checksum_paths = sorted(path for path in output.rglob("*")
                            if path.is_file() and path.name != "SHA256SUMS")
    (output / "SHA256SUMS").write_text("".join(
        f"{sha256(path)}  {path.relative_to(output).as_posix()}\n" for path in checksum_paths
    ))
    return bundle_provenance


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ram-package", type=Path, required=True)
    parser.add_argument("--tf-artifact-dir", type=Path, required=True)
    parser.add_argument("--tf-run-json", type=Path, required=True)
    parser.add_argument("--tf-artifact-json", type=Path, required=True)
    parser.add_argument("--tf-run-id", required=True)
    parser.add_argument("--tf-artifact-id", type=int, required=True)
    parser.add_argument("--tf-artifact-digest", required=True)
    parser.add_argument("--tf-branch", required=True)
    parser.add_argument("--tf-head-sha", required=True)
    parser.add_argument("--package-source-sha", required=True)
    parser.add_argument("--stock-boot", type=Path, required=True)
    parser.add_argument("--compiler", type=Path, required=True)
    parser.add_argument("--objcopy", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = build_bundle(
        package_dir=args.ram_package,
        tf_artifact_dir=args.tf_artifact_dir,
        run_json=args.tf_run_json,
        artifact_json=args.tf_artifact_json,
        run_id=args.tf_run_id,
        artifact_id=args.tf_artifact_id,
        artifact_digest=args.tf_artifact_digest,
        expected_branch=args.tf_branch,
        expected_sha=args.tf_head_sha,
        package_source_sha=args.package_source_sha,
        stock_boot=args.stock_boot,
        compiler=args.compiler,
        objcopy=args.objcopy,
        output=args.output,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
