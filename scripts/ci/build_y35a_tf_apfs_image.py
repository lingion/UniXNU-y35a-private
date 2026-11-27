#!/usr/bin/env python3
"""Build a hash-bound GPT/APFS TF intermediate on a macOS CI runner.

This builder is deliberately separate from the Android RAM-boot package. It
requires a pure stock QCDT input and never marks the result device-ready:
card binding, root selection and eMMC fallback still need linked/runtime proof.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import plistlib
import shutil
import stat
import subprocess
import sys


REQUIRED_ROOT_FILES = ("sbin/launchd", "usr/lib/dyld")
Y35A_BOARD_TUPLE = (206, 8, 23)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def tree_sha256(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix().encode()
        metadata = os.lstat(path)
        mode = stat.S_IMODE(metadata.st_mode)
        acl_lines = []
        if sys.platform == "darwin":
            acl = subprocess.run(
                ["/bin/ls", "-lde", str(path)],
                check=True, capture_output=True, text=True,
            ).stdout.splitlines()
            if len(acl) > 1:
                acl_lines = [line.strip() for line in acl[1:]]
        elif shutil.which("getfacl"):
            acl_lines = subprocess.run(
                ["getfacl", "--absolute-names", "--omit-header", str(path)],
                check=True, capture_output=True, text=True,
            ).stdout.splitlines()
        meta = json.dumps({
            "mode": mode,
            "uid": metadata.st_uid,
            "gid": metadata.st_gid,
            "acl": acl_lines,
        }, sort_keys=True, separators=(",", ":")).encode()
        if path.is_symlink():
            digest.update(b"L\0" + relative + b"\0" + meta + b"\0" + path.readlink().as_posix().encode() + b"\n")
        elif path.is_file():
            digest.update(b"F\0" + relative + b"\0" + meta + b"\0")
            with path.open("rb") as source:
                for block in iter(lambda: source.read(1 << 20), b""):
                    digest.update(block)
            digest.update(b"\n")
        elif path.is_dir():
            digest.update(b"D\0" + relative + b"\0" + meta + b"\n")
    return digest.hexdigest()


def parse_stock_qcdt(path: Path, provenance_path: Path) -> dict:
    path = path.resolve(strict=True)
    provenance_path = provenance_path.resolve(strict=True)
    data = path.read_bytes()
    provenance = json.loads(provenance_path.read_text())
    if provenance.get("source_type") != "stock-qcdt":
        raise ValueError("QCDT provenance must identify a stock-qcdt source")
    if provenance.get("board") not in {"PD1502A", "vivo Y35A / PD1502A", "msm8916-vivo-pd1502a"}:
        raise ValueError("QCDT provenance is not bound to PD1502A")
    if provenance.get("origin") not in {"device-staged-stock-boot", "stock-boot-image"}:
        raise ValueError("QCDT provenance is not a stock firmware source")
    if provenance.get("sha256_scope") != "qcdt-bytes":
        raise ValueError("QCDT provenance must define its SHA-256 scope")
    actual_sha256 = hashlib.sha256(data).hexdigest()
    if provenance.get("sha256") != actual_sha256:
        raise ValueError("QCDT provenance SHA-256 does not match the input")
    if data[:4] != b"QCDT":
        raise ValueError("stock QCDT input must start with QCDT magic")
    if len(data) < 12:
        raise ValueError("stock QCDT input is shorter than its header")
    version = int.from_bytes(data[4:8], "little")
    count = int.from_bytes(data[8:12], "little")
    if version != 3 or count < 1:
        raise ValueError(f"unsupported stock QCDT version/count: {version}/{count}")
    table_end = 12 + count * 40
    if table_end > len(data):
        raise ValueError("stock QCDT table exceeds input")
    entries = []
    ranges = []
    for index in range(count):
        offset = 12 + index * 40
        fields = [int.from_bytes(data[offset + n:offset + n + 4], "little")
                  for n in range(0, 40, 4)]
        dt_offset, dt_size = fields[8:10]
        if dt_size == 0:
            raise ValueError(f"stock QCDT entry {index} has zero-length DTB payload")
        if dt_offset < table_end or dt_offset + dt_size > len(data):
            raise ValueError(f"stock QCDT entry {index} DTB overlaps header/table or exceeds file")
        if data[dt_offset:dt_offset + 4] != b"\xd0\x0d\xfe\xed":
            raise ValueError(f"stock QCDT entry {index} has invalid DTB range")
        ranges.append((dt_offset, dt_offset + dt_size, index))
        entries.append({
            "index": index,
            "platform_id": fields[0],
            "variant_id": fields[1],
            "subtype_id": fields[2],
            "offset": dt_offset,
            "bytes": dt_size,
        })
    for left, right in zip(sorted(ranges), sorted(ranges)[1:]):
        if right[0] < left[1]:
            raise ValueError(f"stock QCDT entries overlap: {left[2]} and {right[2]}")
    if not any((entry["platform_id"], entry["variant_id"], entry["subtype_id"]) == Y35A_BOARD_TUPLE
               for entry in entries):
        raise ValueError("stock QCDT has no Y35A board tuple 206/8/23")
    return {
        "source_type": "stock-qcdt",
        "path": path.name,
        "sha256": actual_sha256,
        "provenance_path": provenance_path.name,
        "provenance_sha256": sha256(provenance_path),
        "board": provenance["board"],
        "bytes": len(data),
        "version": version,
        "entries": entries,
    }


def plist_entities(value):
    if isinstance(value, dict):
        if "dev-entry" in value or "mount-point" in value:
            return [value]
        result = []
        for child in value.values():
            result.extend(plist_entities(child))
        return result
    if isinstance(value, list):
        result = []
        for child in value:
            result.extend(plist_entities(child))
        return result
    return []


def validate_gpt_apfs(whole_disk: dict, volume: dict) -> dict:
    partition_map = str(whole_disk.get("PartitionMapType", ""))
    content = str(whole_disk.get("Content", ""))
    volume_content = str(volume.get("Content", ""))
    filesystem = str(volume.get("FilesystemType", ""))
    if "GPT" not in partition_map.upper() and "GUID" not in partition_map.upper():
        raise ValueError(f"TF image does not report a GPT partition map: {partition_map}")
    if "APFS" not in volume_content.upper() and "APFS" not in filesystem.upper():
        raise ValueError(f"TF image volume is not APFS: {volume_content}/{filesystem}")
    return {
        "partition_map_type": partition_map,
        "whole_disk_content": content,
        "volume_content": volume_content,
        "filesystem_type": filesystem,
        "whole_disk": whole_disk.get("DeviceIdentifier") or whole_disk.get("DeviceNode"),
        "volume_device": volume.get("DeviceIdentifier") or volume.get("DeviceNode"),
    }


def write_report_binding(report_path: Path) -> dict:
    binding = {
        "schema_version": 1,
        "report_path": report_path.name,
        "report_sha256": sha256(report_path),
    }
    binding_path = report_path.with_suffix(report_path.suffix + ".binding.json")
    binding_path.write_text(json.dumps(binding, indent=2, sort_keys=True) + "\n")
    return {"path": binding_path.name, **binding}


def build_image(root_tree: Path, stock_qcdt: Path, stock_qcdt_provenance: Path, output: Path,
                size: str, volume_name: str) -> dict:
    root_tree = root_tree.resolve(strict=True)
    if not root_tree.is_dir():
        raise ValueError("root tree must be a directory")
    missing = [name for name in REQUIRED_ROOT_FILES if not (root_tree / name).exists()]
    if missing:
        raise ValueError(f"root tree is missing required boot files: {missing}")
    qcdt = parse_stock_qcdt(stock_qcdt, stock_qcdt_provenance)
    output = output.resolve()
    if output.exists():
        raise SystemExit(f"refusing to overwrite existing TF image: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)

    attached = None
    mountpoint = None
    try:
        subprocess.run([
            "hdiutil", "create", "-size", size, "-layout", "GPTSPUD",
            "-fs", "APFS", "-volname", volume_name, "-format", "UDRW",
            "-ov", str(output),
        ], check=True, capture_output=True, text=True)
        result = subprocess.run(
            ["hdiutil", "attach", "-nobrowse", "-owners", "on", "-plist", str(output)],
            check=True, capture_output=True,
        )
        entities = plist_entities(plistlib.loads(result.stdout))
        volume = next((item for item in entities if item.get("mount-point")), None)
        if not volume:
            raise RuntimeError("hdiutil did not expose a mounted APFS volume")
        attached = volume.get("dev-entry")
        mountpoint = volume["mount-point"]
        subprocess.run(["ditto", "--rsrc", "--extattr", "--acl",
                        str(root_tree), mountpoint], check=True)
        subprocess.run(["sync"], check=True)
        fs_info = plistlib.loads(subprocess.run(
            ["diskutil", "info", "-plist", mountpoint], check=True, capture_output=True,
        ).stdout)
        whole_name = fs_info.get("ParentWholeDisk") or fs_info.get("ParentWholeDiskDevice")
        if not whole_name:
            raise RuntimeError("APFS volume did not report its parent whole disk")
        whole_info = plistlib.loads(subprocess.run(
            ["diskutil", "info", "-plist", f"/dev/{whole_name}"],
            check=True, capture_output=True,
        ).stdout)
        gpt_apfs = validate_gpt_apfs(whole_info, fs_info)
        report = {
            "schema_version": 1,
            "status": "intermediate-built",
            "device_ready": False,
            "device_run_allowed": False,
            "image": {"path": output.name, "bytes": output.stat().st_size},
            "root_tree": {
                "path": root_tree.name,
                "sha256": tree_sha256(root_tree),
                "scope": "diagnostic-root-until-production-root-is-bound",
            },
            "stock_qcdt": qcdt,
            "gpt_apfs": gpt_apfs,
            "apfs": {
                "filesystem_type": fs_info.get("FilesystemType"),
                "volume_uuid": fs_info.get("VolumeUUID"),
                "volume_name": fs_info.get("VolumeName", volume_name),
            },
            "card_binding": {"status": "pending", "device": None},
            "root_selection": {
                "status": "unverified",
                "coordinator_symbol": "native_storage_select_root",
            },
            "fallback": {"status": "unverified", "target": "eMMC"},
        }
    finally:
        if mountpoint:
            subprocess.run(["diskutil", "unmount", "force", mountpoint], check=False)
        if attached:
            subprocess.run(["hdiutil", "detach", "-quiet", attached], check=False)
    report["image"]["sha256"] = sha256(output)
    report_path = output.with_suffix(output.suffix + ".json")
    report["report_binding_path"] = report_path.name + ".binding.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    write_report_binding(report_path)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root-tree", type=Path, required=True)
    parser.add_argument("--stock-qcdt", type=Path, required=True)
    parser.add_argument("--stock-qcdt-provenance", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--size", default="4g")
    parser.add_argument("--volume-name", default="Y35A-TF-ROOT")
    args = parser.parse_args()
    print(json.dumps(build_image(
        args.root_tree, args.stock_qcdt, args.stock_qcdt_provenance, args.output,
        args.size, args.volume_name,
    ), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
