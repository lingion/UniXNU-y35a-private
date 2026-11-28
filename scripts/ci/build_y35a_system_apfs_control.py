#!/usr/bin/env python3
"""Build a non-bootable GPT/APFS control copy of a pinned iOS System source volume."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import plistlib
import re
import shutil
import subprocess
import tempfile

from build_y35a_tf_apfs_image import run_checked, tree_metadata_manifest, validate_gpt_apfs


ROOT = Path(__file__).resolve().parents[2]
CRITICAL_FILES = (
    "sbin/launchd",
    "usr/lib/dyld",
    "System/Library/CoreServices/SpringBoard.app/SpringBoard",
)
SYSTEM_VERSION_RELATIVE = "System/Library/CoreServices/SystemVersion.plist"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_source_checksums(image_path: Path, report_path: Path) -> None:
    manifest_path = image_path.parent / "SHA256SUMS"
    if not manifest_path.is_file():
        raise ValueError("selected System-source artifact is missing SHA256SUMS")
    records = {}
    for line in manifest_path.read_text().splitlines():
        fields = line.split(maxsplit=1)
        if len(fields) != 2 or not re.fullmatch(r"[0-9a-f]{64}", fields[0]):
            raise ValueError("System-source SHA256SUMS contains a malformed entry")
        name = fields[1].lstrip("*")
        if Path(name).name != name or name in records:
            raise ValueError("System-source SHA256SUMS contains an unsafe or duplicate path")
        records[name] = fields[0]
    if set(records) != {image_path.name, report_path.name}:
        raise ValueError("System-source SHA256SUMS must bind exactly the source image and report")
    for path in (image_path, report_path):
        if records[path.name] != sha256(path):
            raise ValueError(f"System-source checksum mismatch for {path.name}")


def find_volume_device(value, volume_name: str) -> str | None:
    if isinstance(value, dict):
        name = value.get("Name") or value.get("VolumeName")
        identifier = value.get("DeviceIdentifier") or value.get("APFSVolumeDisk")
        if name == volume_name and isinstance(identifier, str):
            return identifier.removeprefix("/dev/")
        for child in value.values():
            found = find_volume_device(child, volume_name)
            if found:
                return found
    elif isinstance(value, list):
        for child in value:
            found = find_volume_device(child, volume_name)
            if found:
                return found
    return None


def attached_device(output: bytes) -> str:
    entities = plistlib.loads(output).get("system-entities", [])
    for entity in entities:
        value = entity.get("dev-entry")
        if isinstance(value, str) and value.startswith("/dev/"):
            return value
    raise RuntimeError("hdiutil attach did not return a device node")


def validate_source_binding(
    image_path: Path,
    source_report_path: Path,
    run_record: dict,
    artifact_record: dict,
    *,
    source_run_id: str,
    artifact_id: int,
    artifact_digest: str,
    expected_branch: str,
) -> tuple[dict, dict]:
    report = json.loads(source_report_path.read_text())
    if report.get("schema_version") != 2 or report.get("status") != "full-system-volume-source-verified":
        raise ValueError("System source report is not a schema-2 verified source")
    if report.get("candidate_kind") != "pinned-ios12-system-volume-source":
        raise ValueError("selected artifact is not a pinned iOS System-volume source")
    run_id = str(run_record.get("databaseId"))
    artifact_name = f"y35a-ios12-system-root-{source_run_id}"
    if (run_id != str(source_run_id)
            or run_record.get("workflowName") != "Y35A CI RAM-boot package"
            or run_record.get("conclusion") != "success"
            or run_record.get("headBranch") != expected_branch
            or run_record.get("headSha") != report.get("package_source", {}).get("commit")
            or report.get("package_source", {}).get("workflow_run_id") != str(source_run_id)
            or report.get("artifact_name") != artifact_name):
        raise ValueError("System source workflow run does not match its report package binding")
    if (artifact_record.get("id") != artifact_id
            or artifact_record.get("name") != artifact_name
            or artifact_record.get("expired") is not False
            or artifact_record.get("digest") != artifact_digest
            or artifact_record.get("workflow_run", {}).get("id") != int(source_run_id)
            or artifact_record.get("workflow_run", {}).get("head_sha") != run_record.get("headSha")):
        raise ValueError("System source artifact API record does not match the selected run and digest")
    source_image = report.get("system_root_image", {})
    if (source_image.get("path") != image_path.name
            or source_image.get("bytes") != image_path.stat().st_size
            or source_image.get("sha256") != sha256(image_path)):
        raise ValueError("System source image bytes do not match its report")
    verify_source_checksums(image_path, source_report_path)
    firmware = report.get("firmware_identity", {})
    if (firmware.get("product_version") != "12.4.1"
            or firmware.get("build") != "16G102"
            or firmware.get("device_class") != "j96ap"
            or firmware.get("product") != "iPad5,1"):
        raise ValueError("System source artifact is not the pinned iOS 12.4.1 j96ap source")
    scope = report.get("scope", {})
    if (scope.get("system_volume_complete") is not True
            or scope.get("paired_data_volume_present") is not False
            or scope.get("device_ready") is not False
            or scope.get("device_run_allowed") is not False):
        raise ValueError("System source report has unexpected or qualified scope")
    return report, {
        "run_id": source_run_id,
        "head_sha": run_record["headSha"],
        "artifact_id": artifact_id,
        "artifact_name": artifact_name,
        "artifact_digest": artifact_digest,
    }


def mounted_apfs_volume(image: Path, mountpoint: Path, *, readonly: bool) -> tuple[str, dict]:
    mountpoint.mkdir(parents=True)
    attached = run_checked(
        ["hdiutil", "attach", "-nobrowse", "-nomount", "-plist"]
        + (["-readonly"] if readonly else []) + [str(image)],
        text=False,
    )
    device = attached_device(attached.stdout)
    mounted = False
    try:
        volumes = plistlib.loads(run_checked(["diskutil", "apfs", "list", "-plist"], text=False).stdout)
        volume_name = find_volume_device(volumes, "PeaceG16G102.J81J82J85mJ86mJ87mJ96J97OS")
        if volume_name is None:
            raise RuntimeError("pinned APFS System volume was not found in the attached source image")
        run_checked(["mount_apfs", *( ["-o", "rdonly"] if readonly else []),
                     f"/dev/{volume_name}", str(mountpoint)])
        mounted = True
        info = plistlib.loads(run_checked(["diskutil", "info", "-plist", str(mountpoint)], text=False).stdout)
        attached_info = plistlib.loads(run_checked(
            ["diskutil", "info", "-plist", device], text=False,
        ).stdout)
        attached_whole = (attached_info.get("ParentWholeDisk")
                          or attached_info.get("ParentWholeDiskDevice")
                          or attached_info.get("DeviceIdentifier"))
        mounted_parent = info.get("ParentWholeDisk") or info.get("ParentWholeDiskDevice")
        if mounted_parent != attached_whole:
            raise ValueError(
                f"mounted APFS volume parent {mounted_parent!r} differs from attached image parent {attached_whole!r}"
            )
        return device, info
    except Exception:
        if mounted:
            subprocess.run(["diskutil", "unmount", "force", str(mountpoint)], check=False)
        subprocess.run(["hdiutil", "detach", "-quiet", device], check=False)
        raise


def inspect_critical_system(root: Path, expected_report: dict) -> dict:
    version_path = root / SYSTEM_VERSION_RELATIVE
    if not version_path.is_file():
        raise ValueError("System source is missing SystemVersion.plist")
    version = plistlib.loads(version_path.read_bytes())
    system_version = expected_report.get("system_version", {})
    if (version.get("ProductVersion") != system_version.get("product_version")
            or version.get("ProductBuildVersion") != system_version.get("build")):
        raise ValueError("mounted source SystemVersion differs from its pinned report")
    critical = {}
    for relative in CRITICAL_FILES:
        path = root / relative
        if not path.is_file():
            raise ValueError(f"System source is missing critical path {relative}")
        critical[relative] = {"bytes": path.stat().st_size, "sha256": sha256(path)}
    if critical != expected_report.get("critical_system_files"):
        raise ValueError("mounted System critical-file hashes differ from the pinned source report")
    return {"product_version": version["ProductVersion"],
            "build": version["ProductBuildVersion"],
            "critical_files": critical}


def validate_control_contract(contract: dict) -> tuple[str, str]:
    if (contract.get("kind") != "offline-system-root-apfs-control"
            or contract.get("source_artifact_kind") != "pinned-ios12-system-volume-source"
            or contract.get("partition_layout") != "GPTSPUD"
            or contract.get("filesystem") != "APFS"
            or contract.get("metadata_round_trip_required") is not True
            or any(contract.get(key) is not False for key in (
                "bootable", "device_ready", "device_run_allowed", "runtime_qualified",
                "y35a_board_qualified",
            ))):
        raise ValueError("package manifest has an invalid System-root APFS control contract")
    size = contract.get("target_image_size")
    volume_name = contract.get("volume_name")
    if not isinstance(size, str) or not isinstance(volume_name, str) or not volume_name:
        raise ValueError("package manifest is missing the APFS control image size or volume name")
    return size, volume_name


def build_control_image(
    image_path: Path,
    source_report_path: Path,
    run_record: dict,
    artifact_record: dict,
    output_path: Path,
    *,
    source_run_id: str,
    artifact_id: int,
    artifact_digest: str,
    expected_branch: str,
    builder_commit: str,
    contract: dict,
    contract_manifest_path: Path,
) -> dict:
    if not re.fullmatch(r"[0-9a-f]{40}", builder_commit):
        raise ValueError("builder commit must be a full lowercase Git SHA-1")
    size, volume_name = validate_control_contract(contract)
    image_path = image_path.resolve(strict=True)
    source_report_path = source_report_path.resolve(strict=True)
    source_report, source_binding = validate_source_binding(
        image_path, source_report_path, run_record, artifact_record,
        source_run_id=source_run_id,
        artifact_id=artifact_id,
        artifact_digest=artifact_digest,
        expected_branch=expected_branch,
    )
    output_path = output_path.resolve()
    if output_path.exists():
        raise ValueError(f"refusing to overwrite System-root APFS control image: {output_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="y35a-system-apfs-control-", dir=output_path.parent))
    source_mount = work / "source"
    target_mount = work / "target"
    source_device = None
    target_device = None
    source_mounted = False
    target_mounted = False
    create_path = output_path.with_suffix(".dmg")
    if create_path.exists():
        raise ValueError(f"refusing to overwrite intermediate image path: {create_path}")
    try:
        source_device, source_info = mounted_apfs_volume(image_path, source_mount, readonly=True)
        source_mounted = True
        if (source_info.get("FilesystemType") != "apfs"
                or source_info.get("VolumeName") != source_report.get("apfs_volume", {}).get("name")
                or source_info.get("VolumeUUID") != source_report.get("apfs_volume", {}).get("uuid")):
            raise ValueError("mounted source APFS volume identity differs from the pinned report")
        source_inspection = inspect_critical_system(source_mount, source_report)
        source_tree = tree_metadata_manifest(source_mount)
        source_file_bytes = sum(
            entry.get("bytes", 0) for entry in source_tree["entries"] if entry.get("type") == "file"
        )
        size_match = re.fullmatch(r"([1-9][0-9]*)([kKmMgGtT])", size)
        if not size_match:
            raise ValueError("control image size must use a positive k/m/g/t suffix")
        capacity_bytes = int(size_match.group(1)) * {
            "k": 1 << 10, "m": 1 << 20, "g": 1 << 30, "t": 1 << 40,
        }[size_match.group(2).lower()]
        if source_file_bytes > capacity_bytes * 9 // 10:
            raise ValueError("selected APFS control-image capacity leaves less than 10% free space")
        free = os.statvfs(output_path.parent)
        if free.f_bavail * free.f_frsize < source_file_bytes + (1 << 30):
            raise ValueError("insufficient runner free space for the source tree plus APFS overhead")

        create_result = run_checked([
            "hdiutil", "create", "-size", size, "-layout", contract["partition_layout"],
            "-fs", contract["filesystem"], "-volname", volume_name, "-type", "UDIF",
            str(create_path),
        ])
        if not create_path.is_file():
            raise RuntimeError(
                f"hdiutil reported success without creating image {create_path}; "
                f"stdout={create_result.stdout}\nstderr={create_result.stderr}"
            )
        target_attach = run_checked(
            ["hdiutil", "attach", "-nobrowse", "-plist", str(create_path)], text=False,
        )
        target_device = attached_device(target_attach.stdout)
        target_entities = plistlib.loads(target_attach.stdout).get("system-entities", [])
        target_volume = next((item for item in target_entities if item.get("mount-point")), None)
        if not target_volume:
            raise RuntimeError("hdiutil did not expose the new control APFS mountpoint")
        target_mount = Path(target_volume["mount-point"])
        target_mounted = True
        run_checked(["sudo", "ditto", "--rsrc", "--extattr", "--acl",
                     str(source_mount), str(target_mount)])
        run_checked(["sync"])

        target_inspection = inspect_critical_system(target_mount, source_report)
        target_tree = tree_metadata_manifest(target_mount)
        if target_tree["tree_sha256"] != source_tree["tree_sha256"]:
            raise ValueError("full System-root metadata/content changed while copied into the control volume")

        target_info = plistlib.loads(run_checked(
            ["diskutil", "info", "-plist", str(target_mount)], text=False,
        ).stdout)
        whole_name = target_info.get("ParentWholeDisk") or target_info.get("ParentWholeDiskDevice")
        if not whole_name:
            raise RuntimeError("control APFS volume did not report its parent whole disk")
        whole_info = plistlib.loads(run_checked(
            ["diskutil", "info", "-plist", f"/dev/{whole_name}"], text=False,
        ).stdout)
        run_checked(["diskutil", "unmount", "force", str(target_mount)])
        target_mounted = False
        run_checked(["hdiutil", "detach", "-quiet", target_device])
        target_device = None
        partition_map = run_checked(["hdiutil", "pmap", "-simple", str(create_path)]).stdout
        gpt_apfs = validate_gpt_apfs(
            whole_info, target_info, partition_map, expected_whole_disk=whole_name,
        )

        run_checked(["diskutil", "unmount", "force", str(source_mount)])
        source_mounted = False
        run_checked(["hdiutil", "detach", "-quiet", source_device])
        source_device = None
        os.replace(create_path, output_path)
        tree_metadata_path = output_path.with_suffix(output_path.suffix + ".tree-metadata.json")
        tree_metadata = {
            "schema_version": 1,
            "tree_sha256": source_tree["tree_sha256"],
            "entries_sha256": hashlib.sha256(
                json.dumps(source_tree["entries"], sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest(),
            "source_file_bytes": source_file_bytes,
            "entry_count": len(source_tree["entries"]),
            "entries": source_tree["entries"],
        }
        tree_metadata_path.write_text(json.dumps(tree_metadata, indent=2, sort_keys=True) + "\n")
        tree_metadata_sha = sha256(tree_metadata_path)
        builder_path = Path(__file__).resolve()
        report = {
            "schema_version": 1,
            "status": "offline-system-root-apfs-control-built",
            "candidate_kind": "pinned-j96ap-system-root-apfs-control",
            "builder": {
                "path": "scripts/ci/build_y35a_system_apfs_control.py",
                "sha256": sha256(builder_path),
                "commit": builder_commit,
            },
            "contract": {
                "path": contract_manifest_path.relative_to(ROOT).as_posix(),
                "sha256": sha256(contract_manifest_path),
                "kind": contract["kind"],
            },
            "qualification": {
                "offline_control_only": True,
                "bootable": False,
                "device_ready": False,
                "device_run_allowed": False,
                "runtime_qualified": False,
                "y35a_board_qualified": False,
                "physical_card_binding": "pending",
                "stock_pd1502a_qcdt_bound": False,
                "root_selection_bound": False,
                "emmc_fallback_bound": False,
            },
            "source_system_artifact": source_binding,
            "source_system_report_sha256": sha256(source_report_path),
            "source_system_image_sha256": source_report["system_root_image"]["sha256"],
            "source_system_tree_sha256": source_tree["tree_sha256"],
            "source_tree_file_bytes": source_file_bytes,
            "target_image": {"path": output_path.name, "bytes": output_path.stat().st_size,
                             "sha256": sha256(output_path),
                             "format": f"UDIF {contract['partition_layout']} {contract['filesystem']}"},
            "target_apfs_volume": {
                "name": target_info.get("VolumeName"),
                "uuid": target_info.get("VolumeUUID"),
                "filesystem_type": target_info.get("FilesystemType"),
            },
            "target_tree_sha256": target_tree["tree_sha256"],
            "tree_metadata_manifest": {
                "path": tree_metadata_path.name,
                "sha256": tree_metadata_sha,
                "bytes": tree_metadata_path.stat().st_size,
                "entries": len(source_tree["entries"]),
                "entries_sha256": tree_metadata["entries_sha256"],
            },
            "metadata_round_trip": "passed",
            "critical_system": {"source": source_inspection, "target": target_inspection},
            "writable_state_paths": source_report["writable_state_paths"],
            "gpt_apfs": gpt_apfs,
            "limitations": [
                "Source System volume is pinned for j96ap/iPad5,1, not qualified for Y35A.",
                "The image is an offline structural control, not a boot package or device result.",
                "No stock PD1502A QCDT, TF card binding, linked root selector, or eMMC fallback is bound.",
                "Path metadata does not prove that private/var is writable at runtime.",
            ],
        }
        report_path = output_path.with_suffix(output_path.suffix + ".json")
        report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
        binding = {"schema_version": 1, "report_path": report_path.name,
                   "report_sha256": sha256(report_path)}
        binding_path = report_path.with_suffix(report_path.suffix + ".binding.json")
        binding_path.write_text(json.dumps(binding, indent=2, sort_keys=True) + "\n")
        (output_path.parent / "SHA256SUMS").write_text(
            f"{sha256(output_path)}  {output_path.name}\n"
            f"{sha256(report_path)}  {report_path.name}\n"
            f"{tree_metadata_sha}  {tree_metadata_path.name}\n"
            f"{sha256(binding_path)}  {binding_path.name}\n"
        )
        return report
    finally:
        if target_mounted:
            subprocess.run(["diskutil", "unmount", "force", str(target_mount)], check=False)
        if target_device:
            subprocess.run(["hdiutil", "detach", "-quiet", target_device], check=False)
        if source_mounted:
            subprocess.run(["diskutil", "unmount", "force", str(source_mount)], check=False)
        if source_device:
            subprocess.run(["hdiutil", "detach", "-quiet", source_device], check=False)
        if create_path.exists():
            create_path.unlink()
        shutil.rmtree(work, ignore_errors=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--system-image", type=Path, required=True)
    parser.add_argument("--system-source-report", type=Path, required=True)
    parser.add_argument("--system-run-json", type=Path, required=True)
    parser.add_argument("--system-artifact-json", type=Path, required=True)
    parser.add_argument("--system-run-id", required=True)
    parser.add_argument("--system-artifact-id", type=int, required=True)
    parser.add_argument("--system-artifact-digest", required=True)
    parser.add_argument("--expected-branch", required=True)
    parser.add_argument("--builder-commit", required=True)
    parser.add_argument("--manifest", type=Path, default=ROOT / "ci/y35a-ci-package-manifest.json")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest_path = args.manifest.resolve(strict=True)
    manifest = json.loads(manifest_path.read_text())
    report = build_control_image(
        args.system_image, args.system_source_report,
        json.loads(args.system_run_json.read_text()),
        json.loads(args.system_artifact_json.read_text()),
        args.output,
        source_run_id=args.system_run_id,
        artifact_id=args.system_artifact_id,
        artifact_digest=args.system_artifact_digest,
        expected_branch=args.expected_branch,
        builder_commit=args.builder_commit,
        contract=manifest.get("system_root_apfs_control", {}),
        contract_manifest_path=manifest_path,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
