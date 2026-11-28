#!/usr/bin/env python3
"""Build a non-bootable GPT/APFS intermediate on a macOS CI runner.

Stock-QCDT intermediates remain unqualified. Derived-QCDT mode is restricted to
offline control and is hash-bound to a diagnostic package artifact. No output is
an iOS system image or device-ready: boot selection, card binding and eMMC
fallback still require linked and runtime proof.
"""

from __future__ import annotations

import argparse
import errno
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import plistlib
import posixpath
import re
import shutil
import stat
import struct
import subprocess
import sys
import tarfile
import tempfile


REQUIRED_ROOT_FILES = ("sbin/launchd", "usr/lib/dyld")
Y35A_BOARD_TUPLE = (206, 8, 23)
KNOWN_PD1502A_STOCK_BOOT_BYTES = 67_108_864
KNOWN_PD1502A_STOCK_BOOT_SHA256 = "92611f876a022fb5af1138f0591f5dafe2b359a226b2f0b28d292211f2fec012"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def run_checked(command: list[str], *, text: bool = True) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(command, check=True, capture_output=True, text=text)
    except subprocess.CalledProcessError as error:
        stdout = error.stdout or (b"" if not text else "")
        stderr = error.stderr or (b"" if not text else "")
        if not text:
            stdout = stdout.decode("utf-8", errors="replace") if isinstance(stdout, bytes) else str(stdout)
            stderr = stderr.decode("utf-8", errors="replace") if isinstance(stderr, bytes) else str(stderr)
        raise RuntimeError(
            f"command failed with exit {error.returncode}: {command!r}\n"
            f"stdout:\n{stdout}\nstderr:\n{stderr}"
        ) from error


def xattr_manifest(path: Path) -> list:
    """Read xattrs through Python where supported, falling back to macOS xattr."""
    if hasattr(os, "listxattr") and hasattr(os, "getxattr"):
        try:
            names = sorted(os.listxattr(path, follow_symlinks=False))
            return [[name, hashlib.sha256(os.getxattr(path, name, follow_symlinks=False)).hexdigest()]
                    for name in names]
        except OSError as error:
            if error.errno not in {errno.EACCES, errno.EPERM}:
                raise
    executable = shutil.which("xattr")
    if not executable:
        raise RuntimeError("Python xattr APIs and the macOS xattr utility are unavailable")
    list_command = [executable]
    if path.is_symlink():
        list_command.append("-s")
    list_command.append(str(path))
    try:
        listed = run_checked(list_command, text=False)
    except RuntimeError as error:
        if "Permission denied" not in str(error) and "Operation not permitted" not in str(error):
            raise
        listed = run_checked(["/usr/bin/sudo", "-n", *list_command], text=False)
    names = sorted(line.decode("utf-8", errors="strict") for line in listed.stdout.splitlines() if line)
    values = []
    for name in names:
        value_command = [executable]
        if path.is_symlink():
            value_command.append("-s")
        value_command.extend(["-px", name, str(path)])
        try:
            encoded_value = run_checked(value_command, text=False).stdout
        except RuntimeError as error:
            if "Permission denied" not in str(error) and "Operation not permitted" not in str(error):
                raise
            encoded_value = run_checked(["/usr/bin/sudo", "-n", *value_command], text=False).stdout
        try:
            value = bytes.fromhex(encoded_value.decode("ascii"))
        except (UnicodeDecodeError, ValueError) as error:
            raise RuntimeError(f"xattr returned invalid hexadecimal data for {name!r}: {path}") from error
        values.append([name, hashlib.sha256(value).hexdigest()])
    return values


def file_content_sha256(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    try:
        with path.open("rb") as source:
            for block in iter(lambda: source.read(1 << 20), b""):
                digest.update(block)
                size += len(block)
        return digest.hexdigest(), size
    except PermissionError:
        if sys.platform != "darwin":
            raise
        result = run_checked(
            ["/usr/bin/sudo", "-n", "/usr/bin/shasum", "-a", "256", str(path)],
        )
        digest_text = result.stdout.split()[0] if result.stdout.split() else ""
        if not re.fullmatch(r"[0-9a-f]{64}", digest_text):
            raise RuntimeError(f"privileged shasum returned an invalid digest for {path}")
        return digest_text, path.stat().st_size


def tree_metadata_manifest(root: Path) -> dict:
    root = root.resolve(strict=True)
    entries = []
    hardlink_targets = {}
    for path in [root, *sorted(root.rglob("*"))]:
        relative_text = "." if path == root else path.relative_to(root).as_posix()
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
        xattrs = xattr_manifest(path)
        hardlink_to = None
        if stat.S_ISREG(metadata.st_mode) and metadata.st_nlink > 1:
            inode_key = (metadata.st_dev, metadata.st_ino)
            hardlink_to = hardlink_targets.setdefault(inode_key, path.relative_to(root).as_posix())
            if hardlink_to == path.relative_to(root).as_posix():
                hardlink_to = None
        attributes = {
            "mode": mode,
            "uid": metadata.st_uid,
            "gid": metadata.st_gid,
            "flags": getattr(metadata, "st_flags", 0),
            "mtime_ns": metadata.st_mtime_ns,
            "acl": acl_lines,
            "xattrs": xattrs,
            "hardlink_to": hardlink_to,
        }
        if path.is_symlink():
            entries.append({"path": relative_text, "type": "symlink", **attributes,
                            "target": path.readlink().as_posix()})
        elif path.is_file():
            content_digest, size = file_content_sha256(path)
            entries.append({"path": relative_text, "type": "file", **attributes,
                            "bytes": size, "content_sha256": content_digest})
        elif path.is_dir():
            entries.append({"path": relative_text, "type": "directory", **attributes})
        else:
            raise ValueError(f"root tree contains an unsupported filesystem object: {path}")
    canonical = json.dumps(entries, sort_keys=True, separators=(",", ":")).encode()
    return {"schema_version": 1, "entries": entries,
            "tree_sha256": hashlib.sha256(canonical).hexdigest()}


def tree_sha256(root: Path) -> str:
    return tree_metadata_manifest(root)["tree_sha256"]


def extract_qcdt_from_pd1502a_boot_image(boot_path: Path) -> dict:
    boot_path = boot_path.resolve(strict=True)
    boot_bytes = boot_path.read_bytes()
    boot_sha = hashlib.sha256(boot_bytes).hexdigest()
    if len(boot_bytes) != KNOWN_PD1502A_STOCK_BOOT_BYTES:
        raise ValueError("stock PD1502A boot image size does not match the historical full-partition input")
    if boot_sha != KNOWN_PD1502A_STOCK_BOOT_SHA256:
        raise ValueError("stock PD1502A boot image SHA-256 does not match the historical full-partition input")
    if boot_bytes[:8] != b"ANDROID!":
        raise ValueError("stock PD1502A boot image has no Android boot header")
    if len(boot_bytes) < 2048:
        raise ValueError("stock PD1502A boot image is shorter than its header page")
    kernel_size, _, ramdisk_size, _, second_size, _, _, page_size, dt_size, _ = struct.unpack_from(
        "<10I", boot_bytes, 8,
    )
    if page_size != 2048 or dt_size <= 0:
        raise ValueError("stock PD1502A boot image has unexpected page size or no QCDT payload")
    qcdt_offset = page_size
    for component_size in (kernel_size, ramdisk_size, second_size):
        qcdt_offset += ((component_size + page_size - 1) // page_size) * page_size
    qcdt_end = qcdt_offset + dt_size
    if qcdt_end > len(boot_bytes):
        raise ValueError("stock PD1502A boot header QCDT range exceeds the full boot image")
    qcdt_bytes = boot_bytes[qcdt_offset:qcdt_end]
    if qcdt_bytes[:4] != b"QCDT":
        raise ValueError("stock PD1502A boot image dt payload is not a QCDT table")
    return {
        "boot_path": boot_path.name,
        "boot_bytes": len(boot_bytes),
        "boot_sha256": boot_sha,
        "qcdt_offset": qcdt_offset,
        "qcdt_bytes": dt_size,
        "qcdt_sha256": hashlib.sha256(qcdt_bytes).hexdigest(),
        "qcdt_bytes_data": qcdt_bytes,
    }


def parse_qcdt(path: Path, provenance_path: Path, *, offline_control_derived: bool = False,
               stock_boot_image: Path | None = None) -> dict:
    path = path.resolve(strict=True)
    provenance_path = provenance_path.resolve(strict=True)
    data = path.read_bytes()
    provenance = json.loads(provenance_path.read_text())
    source_type = provenance.get("source_type")
    if source_type == "stock-qcdt":
        if offline_control_derived:
            raise ValueError("offline derived-QCDT control mode refuses stock inputs")
        if provenance.get("board") not in {"PD1502A", "vivo Y35A / PD1502A", "msm8916-vivo-pd1502a"}:
            raise ValueError("stock QCDT provenance is not bound to PD1502A")
        if provenance.get("origin") not in {"device-staged-stock-boot", "stock-boot-image"}:
            raise ValueError("QCDT provenance is not a stock firmware source")
        if stock_boot_image is None:
            raise ValueError("stock QCDT validation requires the original full stock boot image")
        boot = extract_qcdt_from_pd1502a_boot_image(stock_boot_image)
        expected_source = {
            "source_boot_sha256": boot["boot_sha256"],
            "source_boot_bytes": boot["boot_bytes"],
            "source_boot_version": "PD1502A_A_1.18.0",
            "qcdt_offset": boot["qcdt_offset"],
            "qcdt_bytes": boot["qcdt_bytes"],
            "sha256": boot["qcdt_sha256"],
        }
        for key, value in expected_source.items():
            if provenance.get(key) != value:
                raise ValueError(f"stock QCDT provenance does not match the original boot image: {key}")
        source_boot_path = provenance.get("source_boot_path")
        normalized_source_path = PurePosixPath(source_boot_path) if isinstance(source_boot_path, str) else None
        if (normalized_source_path is None or normalized_source_path.is_absolute()
                or any(part in ("", ".", "..") for part in normalized_source_path.parts)
                or normalized_source_path.name != boot["boot_path"]):
            raise ValueError("stock QCDT provenance must bind a safe tracked repository source path")
        if data != boot["qcdt_bytes_data"]:
            raise ValueError("stock QCDT bytes differ from the QCDT extracted from the original boot image")
        source_commit = provenance.get("source_repository_commit")
        if not isinstance(source_commit, str) or not re.fullmatch(r"[0-9a-f]{40}", source_commit):
            raise ValueError("stock QCDT provenance must bind the full repository source commit")
    elif source_type == "derived" and offline_control_derived:
        for key in ("dts_sha256", "dtc_sha256", "dtc_revision"):
            if not provenance.get(key):
                raise ValueError(f"offline derived QCDT provenance is missing {key}")
        if provenance.get("qcdt_path") != path.name:
            raise ValueError("derived QCDT provenance path does not match the input")
        if provenance.get("qcdt_sha256") != hashlib.sha256(data).hexdigest():
            raise ValueError("derived QCDT provenance SHA-256 does not match the input")
    else:
        raise ValueError("QCDT provenance must identify stock-qcdt, or derived with offline-control mode")
    if source_type == "stock-qcdt" and provenance.get("sha256_scope") != "qcdt-bytes":
        raise ValueError("stock QCDT provenance must define its SHA-256 scope")
    actual_sha256 = hashlib.sha256(data).hexdigest()
    expected_sha256 = provenance.get("sha256") if source_type == "stock-qcdt" else provenance.get("qcdt_sha256")
    if expected_sha256 != actual_sha256:
        raise ValueError("QCDT provenance SHA-256 does not match the input")
    if data[:4] != b"QCDT":
        raise ValueError("QCDT input must start with QCDT magic")
    if len(data) < 12:
        raise ValueError("QCDT input is shorter than its header")
    version = int.from_bytes(data[4:8], "little")
    count = int.from_bytes(data[8:12], "little")
    if version != 3 or count < 1:
        raise ValueError(f"unsupported QCDT version/count: {version}/{count}")
    table_end = 12 + count * 40
    if table_end > len(data):
        raise ValueError("QCDT table exceeds input")
    entries = []
    ranges = []
    for index in range(count):
        offset = 12 + index * 40
        fields = [int.from_bytes(data[offset + n:offset + n + 4], "little")
                  for n in range(0, 40, 4)]
        dt_offset, dt_size = fields[8:10]
        if dt_size == 0:
            raise ValueError(f"QCDT entry {index} has zero-length DTB payload")
        if dt_offset < table_end or dt_offset + dt_size > len(data):
            raise ValueError(f"QCDT entry {index} DTB overlaps header/table or exceeds file")
        if data[dt_offset:dt_offset + 4] != b"\xd0\x0d\xfe\xed":
            raise ValueError(f"QCDT entry {index} has invalid DTB range")
        ranges.append((dt_offset, dt_offset + dt_size, index))
        entries.append({
            "index": index,
            "platform_id": fields[0],
            "variant_id": fields[1],
            "subtype_id": fields[2],
            "offset": dt_offset,
            "bytes": dt_size,
        })
    # Qualcomm's QCDT table can contain multiple hardware-match rows that
    # intentionally point at one shared DTB payload. Accept only exact range
    # aliases; a partial overlap still makes the payload boundaries ambiguous.
    ordered_ranges = sorted(ranges)
    alias_groups = []
    index = 0
    while index < len(ordered_ranges):
        start, end, entry_index = ordered_ranges[index]
        aliases = [entry_index]
        index += 1
        while index < len(ordered_ranges) and ordered_ranges[index][:2] == (start, end):
            aliases.append(ordered_ranges[index][2])
            index += 1
        if index < len(ordered_ranges) and ordered_ranges[index][0] < end:
            raise ValueError(
                f"QCDT entries partially overlap: {aliases[0]} and {ordered_ranges[index][2]}"
            )
        if len(aliases) > 1:
            alias_groups.append({
                "offset": start,
                "bytes": end - start,
                "entry_indexes": aliases,
                "payload_sha256": hashlib.sha256(data[start:end]).hexdigest(),
            })
    if not any((entry["platform_id"], entry["variant_id"], entry["subtype_id"]) == Y35A_BOARD_TUPLE
               for entry in entries):
        raise ValueError("QCDT has no Y35A board tuple 206/8/23")
    return {
        "source_type": source_type,
        "path": path.name,
        "sha256": actual_sha256,
        "provenance_path": provenance_path.name,
        "provenance_sha256": sha256(provenance_path),
        "board": provenance.get("board", "PD1502A (derived from validated tuple 206/8/23)"),
        "bytes": len(data),
        "version": version,
        "entries": entries,
        "payload_alias_groups": alias_groups,
        "stock_boot_source": (
            {
                "bytes": boot["boot_bytes"],
                "sha256": boot["boot_sha256"],
                "qcdt_offset": boot["qcdt_offset"],
                "qcdt_bytes": boot["qcdt_bytes"],
                "source_repository_commit": provenance["source_repository_commit"],
                "source_repository_path": provenance["source_boot_path"],
            }
            if source_type == "stock-qcdt" else None
        ),
    }


def parse_stock_qcdt(path: Path, provenance_path: Path, stock_boot_image: Path | None = None) -> dict:
    return parse_qcdt(path, provenance_path, offline_control_derived=False,
                      stock_boot_image=stock_boot_image)


def validate_package_artifact_api(run_record: dict, artifact_record: dict, *,
                                  package_run_id: str, artifact_id: int,
                                  artifact_name: str, artifact_digest: str,
                                  expected_branch: str) -> None:
    if not package_run_id.isdecimal() or artifact_id < 1:
        raise ValueError("package artifact run and artifact IDs must be positive numeric values")
    allowed_names = {f"y35a-ramboot-{package_run_id}", "root-tree.tar"}
    if artifact_name not in allowed_names:
        raise ValueError("artifact name is not an approved package or root-tree transport name")
    digest_hex = artifact_digest.removeprefix("sha256:") if isinstance(artifact_digest, str) else ""
    if not isinstance(artifact_digest, str) or not artifact_digest.startswith("sha256:") or len(digest_hex) != 64 or any(
            character not in "0123456789abcdef" for character in digest_hex):
        raise ValueError("package artifact digest is malformed")
    if (str(run_record.get("databaseId")) != package_run_id
            or run_record.get("workflowName") != "Y35A CI RAM-boot package"
            or run_record.get("conclusion") != "success"
            or run_record.get("headBranch") != expected_branch
            or not isinstance(run_record.get("headSha"), str)
            or len(run_record["headSha"]) != 40):
        raise ValueError("selected package Actions run is not a successful RAM-boot package run")
    if (artifact_record.get("id") != artifact_id
            or artifact_record.get("name") != artifact_name
            or artifact_record.get("expired") is not False
            or artifact_record.get("digest") != artifact_digest
            or artifact_record.get("workflow_run", {}).get("id") != int(package_run_id)
            or artifact_record.get("workflow_run", {}).get("head_sha") != run_record.get("headSha")):
        raise ValueError("package artifact API metadata does not match the selected run, ID, name and digest")


def validate_root_tree_archive(archive_path: Path) -> dict:
    """Reject unsafe or incomplete package root-tree archives before extraction."""
    members = []
    seen_paths = set()
    prior_regular_files = set()
    top_level_names = set()
    with tarfile.open(archive_path, mode="r:*") as archive:
        for member in archive.getmembers():
            raw_name = member.name
            path = Path(raw_name)
            parts = raw_name.split("/")
            normalized = Path(raw_name).as_posix()
            if (not raw_name or path.is_absolute() or ".." in parts or "." in parts
                    or "" in parts[:-1]
                    or normalized != raw_name.rstrip("/")):
                raise ValueError(f"root-tree archive contains an unsafe path: {raw_name!r}")
            top_level_names.add(parts[0])
            canonical_name = raw_name.rstrip("/")
            if canonical_name in seen_paths:
                raise ValueError(f"root-tree archive contains a duplicate path: {raw_name!r}")
            seen_paths.add(canonical_name)
            if member.isdev() or member.isfifo():
                raise ValueError(f"root-tree archive contains an unsupported member: {raw_name!r}")
            if not (member.isdir() or member.isfile() or member.issym() or member.islnk()):
                raise ValueError(f"root-tree archive contains an unsupported member: {raw_name!r}")
            if member.islnk():
                target = Path(member.linkname)
                if (target.is_absolute() or ".." in target.parts
                        or member.linkname.split("/", 1)[0] != parts[0]
                        or member.linkname not in prior_regular_files):
                    raise ValueError(f"root-tree archive hard link escapes its tree: {member.name!r}")
            if member.isfile():
                prior_regular_files.add(canonical_name)
            members.append(member)
    if len(top_level_names) != 1:
        raise ValueError("root-tree archive must contain exactly one top-level directory")
    root_name = next(iter(top_level_names))
    if not members or not any(member.name.rstrip("/") == root_name and member.isdir()
                              for member in members):
        raise ValueError("root-tree archive does not contain its top-level root directory")
    symlink_names = {member.name.rstrip("/") for member in members if member.issym()}
    for member in members:
        parts = member.name.rstrip("/").split("/")
        ancestors = ["/".join(parts[:index]) for index in range(1, len(parts))]
        if any(parent in symlink_names for parent in ancestors):
            raise ValueError(f"root-tree archive descends through a symlink: {member.name!r}")
        # Symlink targets are filesystem semantics and may be absolute in an iOS
        # root. Extraction safety comes from rejecting archive member paths that
        # escape the tree and forbidding any archived child below a symlink.
    return {"members": len(members), "symlinks": len(symlink_names), "root_name": root_name}


def extract_root_tree_archive(archive_path: Path, destination: Path) -> Path:
    """Extract metadata-preserving tar data on macOS after rejecting unsafe paths."""
    archive_path = archive_path.resolve(strict=True)
    archive_info = validate_root_tree_archive(archive_path)
    destination = destination.resolve()
    if destination.exists() and any(destination.iterdir()):
        raise ValueError(f"root-tree extraction destination is not empty: {destination}")
    destination.mkdir(parents=True, exist_ok=True)
    tar = shutil.which("tar")
    if not tar:
        raise RuntimeError("tar is required to restore root-tree metadata")
    command = [tar, "--xattrs", "--fflags", "--mac-metadata",
               "--numeric-owner", "-p", "-xpf",
               str(archive_path), "-C", str(destination)]
    if os.geteuid() != 0 and shutil.which("sudo"):
        command.insert(0, shutil.which("sudo"))
    subprocess.run(command, check=True)
    extracted = destination / archive_info["root_name"]
    if not extracted.is_dir():
        raise ValueError("root-tree archive did not create the expected directory")
    return extracted


def verify_root_tree_metadata(archive_path: Path, metadata_path: Path, root_tree: Path) -> dict:
    archive_record = json.loads(metadata_path.read_text())
    if (archive_record.get("archive_path") != archive_path.name
            or archive_record.get("archive_bytes") != archive_path.stat().st_size
            or archive_record.get("archive_sha256") != sha256(archive_path)):
        raise ValueError("root-tree metadata manifest does not bind the archive")
    entries = archive_record.get("entries")
    if not isinstance(entries, list):
        raise ValueError("root-tree metadata manifest has no per-path entries")
    metadata_digest = hashlib.sha256(
        json.dumps(entries, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    actual_tree_digest = tree_sha256(root_tree)
    if (metadata_digest != actual_tree_digest or archive_record.get("tree_sha256") != actual_tree_digest
            or archive_record.get("entries_sha256") != metadata_digest):
        raise ValueError("root-tree archive restoration differs from the metadata manifest")
    return {"archive_sha256": sha256(archive_path), "tree_sha256": actual_tree_digest,
            "entries_sha256": metadata_digest, "entries": len(entries), "round_trip": "passed"}


def validate_control_package(root_tree: Path, qcdt_path: Path, qcdt_provenance_path: Path,
                             root_tree_archive_path: Path, package_provenance_path: Path,
                             root_tree_transport: dict,
                             run_record: dict, artifact_record: dict, root_tree_artifact_record: dict,
                             package_run_id: str,
                             package_artifact_id: int, package_artifact_name: str,
                             package_artifact_digest: str, root_tree_artifact_id: int,
                             root_tree_artifact_digest: str, expected_branch: str) -> dict:
    provenance = json.loads(package_provenance_path.read_text())
    if provenance.get("status") != "offline-package-complete":
        raise ValueError("offline TF control requires a completed diagnostic package artifact")
    if provenance.get("candidate_kind") != "launchd-diagnostic-ramboot":
        raise ValueError("offline TF control package kind is not the expected RAM diagnostic package")
    if provenance.get("qualification", {}).get("runtime_qualified") is not False:
        raise ValueError("diagnostic package must remain runtime-unqualified")
    if provenance.get("qualification", {}).get("device_run_allowed") is not False:
        raise ValueError("diagnostic package must not authorize device execution")
    qualification = provenance.get("qualification", {})
    if (qualification.get("springboard_included") is not False
            or qualification.get("touch_runtime_validated") is not False
            or qualification.get("device_boot") != "not-run"):
        raise ValueError("offline control source package has an unexpected device qualification")
    if provenance.get("package_source", {}).get("workflow_run_id") != package_run_id:
        raise ValueError("diagnostic package provenance does not match its Actions run")
    if not package_run_id.isdecimal():
        raise ValueError("diagnostic package run ID must be numeric")
    package_commit = provenance.get("package_source", {}).get("commit")
    if not isinstance(package_commit, str) or len(package_commit) != 40 or any(
            character not in "0123456789abcdef" for character in package_commit):
        raise ValueError("diagnostic package provenance has an invalid source commit")
    if package_commit != run_record.get("headSha"):
        raise ValueError("diagnostic package commit does not match the selected Actions run")
    expected_artifact_name = f"y35a-ramboot-{package_run_id}"
    validate_package_artifact_api(
        run_record, artifact_record, package_run_id=package_run_id,
        artifact_id=package_artifact_id, artifact_name=package_artifact_name,
        artifact_digest=package_artifact_digest, expected_branch=expected_branch,
    )
    validate_package_artifact_api(
        run_record, root_tree_artifact_record, package_run_id=package_run_id,
        artifact_id=root_tree_artifact_id, artifact_name="root-tree.tar",
        artifact_digest=root_tree_artifact_digest, expected_branch=expected_branch,
    )
    if package_artifact_name != expected_artifact_name:
        raise ValueError("offline control package artifact name is not bound to the selected run")
    package_file_map = provenance.get("files", {})
    qcdt_record = package_file_map.get("y35a.qcdt", {})
    actual_qcdt_sha = sha256(qcdt_path)
    if qcdt_record.get("sha256") != actual_qcdt_sha or qcdt_record.get("bytes") != qcdt_path.stat().st_size:
        raise ValueError("derived QCDT bytes do not match the source RAM package")
    qcdt_provenance_record = package_file_map.get("y35a.qcdt.json", {})
    if (qcdt_provenance_record.get("sha256") != sha256(qcdt_provenance_path)
            or qcdt_provenance_record.get("bytes") != qcdt_provenance_path.stat().st_size):
        raise ValueError("derived QCDT provenance does not match the source RAM package")
    qcdt_manifest = json.loads(qcdt_provenance_path.read_text())
    if qcdt_manifest.get("qcdt_sha256") != actual_qcdt_sha:
        raise ValueError("derived QCDT provenance does not bind the QCDT bytes")
    package_dt = provenance.get("device_tree", {})
    if (package_dt.get("source_type") != "derived"
            or package_dt.get("qcdt_sha256") != actual_qcdt_sha
            or package_dt.get("dts_sha256") != qcdt_manifest.get("dts_sha256")
            or package_dt.get("dtc_sha256") != qcdt_manifest.get("dtc_sha256")
            or package_dt.get("dtc_revision") != qcdt_manifest.get("dtc_revision")):
        raise ValueError("package device-tree provenance does not bind the derived QCDT inputs")
    root_hash = provenance.get("rootfs", {}).get("tree_sha256")
    if not root_hash:
        raise ValueError("source RAM package is missing the diagnostic root-tree hash")
    tree_archive_record = package_file_map.get("root-tree.tar", {})
    tree_archive_report = provenance.get("rootfs", {}).get("tree_archive", {})
    if (not tree_archive_record.get("sha256")
            or tree_archive_record.get("sha256") != tree_archive_report.get("sha256")
            or tree_archive_report.get("tree_sha256") != provenance.get("rootfs", {}).get("tree_sha256")
            or tree_archive_record.get("bytes") != tree_archive_report.get("bytes")
            or tree_archive_record.get("sha256") != sha256(root_tree_archive_path)
            or tree_archive_record.get("bytes") != root_tree_archive_path.stat().st_size):
        raise ValueError("source RAM package does not bind a metadata-preserving root-tree archive")
    metadata_record = package_file_map.get("root-tree.metadata.json", {})
    metadata_path = package_provenance_path.parent / "root-tree.metadata.json"
    if (not metadata_path.is_file()
            or metadata_record.get("sha256") != sha256(metadata_path)
            or metadata_record.get("bytes") != metadata_path.stat().st_size):
        raise ValueError("source RAM package is missing its bound root-tree metadata manifest")
    metadata = json.loads(metadata_path.read_text())
    metadata_copy_record = package_file_map.get("root-tree.metadata.json", {})
    if metadata_record.get("entries_sha256") != metadata.get("entries_sha256"):
        raise ValueError("package manifest tree metadata digest does not match its metadata file")
    if (metadata.get("archive_sha256") != tree_archive_record.get("sha256")
            or metadata.get("tree_sha256") != root_hash
            or metadata_record.get("entries_sha256") != metadata.get("entries_sha256")
            or metadata.get("entries_sha256") != tree_archive_report.get("entries_sha256")
            or metadata.get("archive_sha256") != tree_archive_report.get("sha256")
            or metadata.get("round_trip") != "passed"):
        raise ValueError("root-tree metadata manifest does not match the package archive and tree hashes")
    metadata_entries = metadata.get("entries")
    if not isinstance(metadata_entries, list):
        raise ValueError("root-tree metadata manifest has no per-path entries")
    metadata_tree_hash = hashlib.sha256(
        json.dumps(metadata_entries, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    if metadata_tree_hash != root_hash or metadata_tree_hash != tree_archive_report.get("entries_sha256"):
        raise ValueError("root-tree per-path metadata manifest does not match its tree hash")
    if root_tree_transport.get("tree_sha256") != root_hash:
        raise ValueError("root tree bytes do not match the source RAM package")
    if qcdt_manifest.get("source_type") != "derived":
        raise ValueError("offline TF control input must use the package's derived QCDT")
    native_build = provenance.get("native_build", {})
    native_run_id = native_build.get("run_id")
    kernel_sha = native_build.get("kernel_sha256")
    if (not isinstance(native_run_id, str) or not native_run_id.isdecimal()
            or not isinstance(kernel_sha, str) or len(kernel_sha) != 64
            or any(character not in "0123456789abcdef" for character in kernel_sha)):
        raise ValueError("diagnostic package is missing its bound native run or kernel hash")
    kernel_record = package_file_map.get("kernel.macho", {})
    if kernel_record.get("sha256") != kernel_sha or not isinstance(kernel_record.get("bytes"), int):
        raise ValueError("diagnostic package file list does not bind its native kernel")
    return {
        "package_run_id": package_run_id,
        "package_commit": package_commit,
        "package_source_sha": package_commit,
        "native_run_id": native_run_id,
        "native_kernel_sha256": kernel_sha,
        "package_artifact_name": package_artifact_name,
        "package_artifact_id": package_artifact_id,
        "package_artifact_digest": package_artifact_digest,
        "root_tree_artifact_id": root_tree_artifact_id,
        "root_tree_artifact_name": "root-tree.tar",
        "root_tree_artifact_digest": root_tree_artifact_digest,
        "package_workflow_run_sha256": hashlib.sha256(
            json.dumps({
                "databaseId": run_record["databaseId"],
                "workflowName": run_record["workflowName"],
                "conclusion": run_record["conclusion"],
                "headBranch": run_record.get("headBranch"),
                "headSha": run_record.get("headSha"),
            }, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        "package_provenance_sha256": sha256(package_provenance_path),
        "root_tree_sha256": root_hash,
        "root_tree_archive_sha256": tree_archive_record["sha256"],
        "derived_qcdt_sha256": actual_qcdt_sha,
        "qualification": "offline-control-only",
    }


def validate_root_tree_artifact_binding(binding: dict, archive_path: Path | None = None) -> dict:
    run_id = str(binding.get("run_id", ""))
    head_sha = binding.get("head_sha")
    artifact_id = binding.get("artifact_id")
    artifact_name = binding.get("artifact_name")
    artifact_digest = binding.get("artifact_digest")
    head_branch = binding.get("head_branch")
    if (not run_id.isdecimal()
            or not isinstance(head_sha, str) or not re.fullmatch(r"[0-9a-f]{40}", head_sha)
            or not isinstance(artifact_id, int) or isinstance(artifact_id, bool) or artifact_id <= 0
            or artifact_name != f"y35a-root-tree-{run_id}"
            or not isinstance(artifact_digest, str)
            or not re.fullmatch(r"sha256:[0-9a-f]{64}", artifact_digest)
            or not isinstance(head_branch, str) or not head_branch):
        raise ValueError("root-tree source artifact binding is incomplete or malformed")
    archive_name = binding.get("archive_path")
    archive_bytes = binding.get("archive_bytes")
    archive_sha = binding.get("archive_sha256")
    if (archive_name != "root-tree.tar"
            or not isinstance(archive_bytes, int) or isinstance(archive_bytes, bool) or archive_bytes <= 0
            or not isinstance(archive_sha, str) or not re.fullmatch(r"[0-9a-f]{64}", archive_sha)):
        raise ValueError("root-tree source archive must be named root-tree.tar")
    if (archive_path is not None
            and (archive_name != archive_path.name
                 or archive_bytes != archive_path.stat().st_size
                 or archive_sha != sha256(archive_path))):
        raise ValueError("root-tree artifact binding archive bytes do not match its SHA-256 and size")
    return {
        "run_id": run_id,
        "head_sha": head_sha,
        "artifact_id": artifact_id,
        "artifact_name": artifact_name,
        "artifact_digest": artifact_digest,
        "head_branch": head_branch,
        "archive_path": archive_name,
        "archive_bytes": archive_bytes,
        "archive_sha256": archive_sha,
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


_GPT_SCHEMES = {"GPT", "GUID_PARTITION_SCHEME"}


def _normalize_scheme(value: object) -> str:
    return re.sub(r"[^A-Z0-9]+", "_", str(value).upper()).strip("_")


def _normalize_disk_identifier(value: object) -> str:
    identifier = str(value or "").strip()
    return identifier.removeprefix("/dev/")


def parse_hdiutil_partition_scheme(output: str) -> str:
    """Extract hdiutil pmap's explicit top-level SCHEME record."""
    for line in output.splitlines():
        match = re.match(r"^\s*SCHEME:\s*\d+\s+([^,\[]+)", line, re.IGNORECASE)
        if match:
            value = match.group(1).strip()
            return value if _normalize_scheme(value) in _GPT_SCHEMES else ""
    return ""


def validate_gpt_apfs(
    whole_disk: dict,
    volume: dict,
    partition_map_output: str,
    *,
    expected_whole_disk: str,
) -> dict:
    """Require explicit GPT evidence, APFS volume facts, and parent-device binding.

    Partition-type GUIDs such as Apple's APFS GUID are not partition-map schemes.
    Only the hdiutil pmap top-level SCHEME record can establish GPT here.
    """
    pmap_scheme = parse_hdiutil_partition_scheme(partition_map_output)
    volume_content = str(volume.get("Content", ""))
    filesystem = str(volume.get("FilesystemType", ""))
    normalized_pmap_scheme = _normalize_scheme(pmap_scheme)
    if normalized_pmap_scheme not in _GPT_SCHEMES:
        raise ValueError(
            "TF image does not report a GPT partition map: "
            f"hdiutil={pmap_scheme or 'unreported'!r}"
        )
    if "APFS" not in volume_content.upper() and "APFS" not in filesystem.upper():
        raise ValueError(f"TF image volume is not APFS: {volume_content}/{filesystem}")
    whole_device = _normalize_disk_identifier(
        whole_disk.get("DeviceIdentifier") or whole_disk.get("DeviceNode")
    )
    volume_device = _normalize_disk_identifier(
        volume.get("DeviceIdentifier") or volume.get("DeviceNode")
    )
    parent_device = _normalize_disk_identifier(
        volume.get("ParentWholeDisk") or volume.get("ParentWholeDiskDevice")
    )
    expected_whole_disk = _normalize_disk_identifier(expected_whole_disk)
    if not expected_whole_disk:
        raise ValueError("expected whole-disk identifier is required")
    if not whole_device or not volume_device or not parent_device:
        raise ValueError("GPT/APFS relation is missing whole-disk, volume, or parent device identity")
    if whole_device != expected_whole_disk:
        raise ValueError(
            f"queried whole disk {whole_device!r} does not match expected {expected_whole_disk!r}"
        )
    if parent_device != expected_whole_disk:
        raise ValueError(
            f"APFS volume parent {parent_device!r} does not match expected whole disk {expected_whole_disk!r}"
        )
    if volume_device == expected_whole_disk:
        raise ValueError("APFS volume device must identify a partition or APFS volume, not the whole disk")
    return {
        "partition_map_type": pmap_scheme,
        "partition_map_source": "hdiutil-pmap:SCHEME",
        "partition_map_report_sha256": hashlib.sha256(partition_map_output.encode()).hexdigest(),
        "whole_disk_content": str(whole_disk.get("Content", "")),
        "volume_content": volume_content,
        "filesystem_type": filesystem,
        "whole_disk": whole_device,
        "volume_device": volume_device,
        "volume_parent_whole_disk": parent_device,
        "expected_whole_disk": expected_whole_disk,
    }


def detach_and_read_partition_map(image: Path, mountpoint: str, attached: str) -> str:
    """Read the image map only after the mounted volume and image are released."""
    if not mountpoint or not attached:
        raise ValueError("mounted volume and attached device are required before reading the image map")
    run_checked(["diskutil", "unmount", "force", mountpoint])
    run_checked(["hdiutil", "detach", "-quiet", attached])
    return run_checked(["hdiutil", "pmap", "-simple", str(image)]).stdout


def write_report_binding(report_path: Path) -> dict:
    binding = {
        "schema_version": 1,
        "report_path": report_path.name,
        "report_sha256": sha256(report_path),
    }
    binding_path = report_path.with_suffix(report_path.suffix + ".binding.json")
    binding_path.write_text(json.dumps(binding, indent=2, sort_keys=True) + "\n")
    return {"path": binding_path.name, **binding}


def build_image(root_tree: Path, qcdt_path: Path, qcdt_provenance: Path, output: Path,
                size: str, volume_name: str, *, offline_control_derived: bool = False,
                stock_boot_image: Path | None = None,
                control_package_binding: dict | None = None,
                root_tree_transport: dict | None = None,
                root_tree_artifact_binding: dict | None = None) -> dict:
    root_tree = root_tree.resolve(strict=True)
    if not root_tree.is_dir():
        raise ValueError("root tree must be a directory")
    missing = [name for name in REQUIRED_ROOT_FILES if not (root_tree / name).exists()]
    if missing:
        raise ValueError(f"root tree is missing required boot files: {missing}")
    qcdt = parse_qcdt(qcdt_path, qcdt_provenance,
                      offline_control_derived=offline_control_derived,
                      stock_boot_image=stock_boot_image)
    output = output.resolve()
    if output.exists():
        raise SystemExit(f"refusing to overwrite existing TF image: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)

    attached = None
    mountpoint = None
    try:
        create_path = output.with_suffix(".dmg")
        if create_path.exists():
            raise SystemExit(f"refusing to overwrite existing hdiutil image: {create_path}")
        create_result = run_checked([
            "hdiutil", "create", "-size", size, "-layout", "GPTSPUD",
            "-fs", "APFS", "-volname", volume_name, "-type", "UDIF", str(create_path),
        ])
        if not create_path.is_file():
            raise RuntimeError(
                f"hdiutil reported success but did not create the requested .dmg path: {create_path}; "
                f"stdout:\n{create_result.stdout}\nstderr:\n{create_result.stderr}"
            )
        if output.exists():
            raise SystemExit(f"refusing to overwrite existing TF image: {output}")
        os.rename(create_path, output)
        if not output.is_file() or output.stat().st_size == 0:
            raise RuntimeError(f"hdiutil image output is missing or empty after rename: {output}")
        result = run_checked(
            ["hdiutil", "attach", "-nobrowse", "-owners", "on", "-plist", str(output)],
            text=False,
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
        fs_info = plistlib.loads(run_checked(
            ["diskutil", "info", "-plist", mountpoint], text=False,
        ).stdout)
        whole_name = fs_info.get("ParentWholeDisk") or fs_info.get("ParentWholeDiskDevice")
        if not whole_name:
            raise RuntimeError("APFS volume did not report its parent whole disk")
        whole_info = plistlib.loads(run_checked(
            ["diskutil", "info", "-plist", f"/dev/{whole_name}"], text=False,
        ).stdout)
        partition_map_output = detach_and_read_partition_map(output, mountpoint, attached)
        mountpoint = None
        attached = None
        gpt_apfs = validate_gpt_apfs(
            whole_info, fs_info, partition_map_output, expected_whole_disk=whole_name,
        )
        report = {
            "schema_version": 1,
            "status": "intermediate-built",
            "candidate_kind": "derived-qcdt-offline-control" if qcdt["source_type"] == "derived" else "stock-qcdt-intermediate",
            "device_ready": False,
            "device_run_allowed": False,
            "qualification": "offline-control-only" if qcdt["source_type"] == "derived" else "stock-qcdt-intermediate-unqualified",
            "bootable": False,
            "ios_system_image": False,
            "springboard_included": False,
            "touch_runtime_validated": False,
            "stock_provenance_status": "verified-against-pinned-full-boot-image" if qcdt["source_type"] == "stock-qcdt" else "not-applicable-derived-input",
            "control_package_binding": control_package_binding,
            "image": {"path": output.name, "bytes": output.stat().st_size},
            "root_tree": {
                "path": root_tree.name,
                "sha256": root_tree_transport.get("tree_sha256") if root_tree_transport else tree_sha256(root_tree),
                "scope": "diagnostic-root-until-production-root-is-bound",
            },
            "root_tree_transport": root_tree_transport,
            "root_tree_artifact": root_tree_artifact_binding,
            "device_tree_input": qcdt,
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
    parser.add_argument("--root-tree", type=Path)
    parser.add_argument("--root-tree-archive", type=Path)
    parser.add_argument("--root-tree-metadata", type=Path)
    parser.add_argument("--root-tree-artifact-binding", type=Path)
    parser.add_argument("--qcdt", "--stock-qcdt", dest="qcdt_path", type=Path, required=True)
    parser.add_argument("--qcdt-provenance", "--stock-qcdt-provenance", dest="qcdt_provenance", type=Path, required=True)
    parser.add_argument("--stock-boot-image", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--size", default="4g")
    parser.add_argument("--volume-name", default="Y35A-TF-ROOT")
    parser.add_argument("--offline-control-derived-qcdt", action="store_true")
    parser.add_argument("--control-package-provenance", type=Path)
    parser.add_argument("--control-package-run-json", type=Path)
    parser.add_argument("--control-package-artifact-json", type=Path)
    parser.add_argument("--control-root-tree-artifact-json", type=Path)
    parser.add_argument("--control-package-branch")
    parser.add_argument("--control-package-root", type=Path)
    parser.add_argument("--control-package-run-id")
    parser.add_argument("--control-package-artifact-name")
    parser.add_argument("--control-package-artifact-id", type=int)
    parser.add_argument("--control-package-artifact-digest")
    parser.add_argument("--control-root-tree-artifact-id", type=int)
    parser.add_argument("--control-root-tree-artifact-digest")
    args = parser.parse_args()
    if bool(args.root_tree) == bool(args.root_tree_archive):
        raise SystemExit("provide exactly one of --root-tree or --root-tree-archive")
    if args.root_tree_archive and args.root_tree_metadata is None:
        raise SystemExit("--root-tree-archive requires its root-tree metadata manifest")
    if (args.root_tree_archive and args.root_tree_artifact_binding is None
            and not args.offline_control_derived_qcdt):
        raise SystemExit("--root-tree-archive requires its Actions artifact binding")
    if args.root_tree and args.root_tree_metadata:
        raise SystemExit("--root-tree-metadata must accompany --root-tree-archive")
    if args.root_tree_artifact_binding and args.root_tree_archive is None:
        raise SystemExit("--root-tree-artifact-binding requires --root-tree-archive")
    if args.offline_control_derived_qcdt:
        if args.stock_boot_image:
            raise SystemExit("offline derived-QCDT control does not accept a stock boot image")
        required = (args.control_package_provenance, args.control_package_root,
                    args.control_package_run_json, args.control_package_artifact_json,
                    args.control_root_tree_artifact_json,
                    args.control_package_branch,
                    args.control_package_run_id, args.control_package_artifact_name,
                    args.control_package_artifact_id, args.control_package_artifact_digest,
                    args.control_root_tree_artifact_id, args.control_root_tree_artifact_digest)
        if args.root_tree_archive is None or not all(required):
            raise SystemExit("derived-QCDT control requires a root-tree archive and exact package artifact binding")
    elif any((args.control_package_provenance, args.control_package_root,
              args.control_package_run_json, args.control_package_artifact_json,
                  args.control_root_tree_artifact_json,
              args.control_package_branch,
              args.control_package_run_id, args.control_package_artifact_name,
                  args.control_package_artifact_id, args.control_package_artifact_digest,
                  args.control_root_tree_artifact_id, args.control_root_tree_artifact_digest)):
        raise SystemExit("package artifact binding options are only valid in offline-control mode")
    elif args.stock_boot_image is None:
        raise SystemExit("stock-QCDT image construction requires --stock-boot-image")

    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise SystemExit(f"refusing to overwrite existing TF image: {output}")
    with tempfile.TemporaryDirectory(prefix="y35a-tf-input-", dir=output.parent) as temporary:
        temp_root = Path(temporary)
        if args.root_tree_archive:
            root_tree = extract_root_tree_archive(args.root_tree_archive, temp_root / "tree")
            restored_tree_binding = verify_root_tree_metadata(
                args.root_tree_archive.resolve(strict=True),
                args.root_tree_metadata.resolve(strict=True), root_tree,
            )
            root_tree_artifact_binding = (
                validate_root_tree_artifact_binding(
                    json.loads(args.root_tree_artifact_binding.read_text()),
                    args.root_tree_archive.resolve(strict=True),
                )
                if args.root_tree_artifact_binding else None
            )
        else:
            root_tree = args.root_tree.resolve(strict=True)
            restored_tree_binding = None
            root_tree_artifact_binding = None

        qcdt_path = args.qcdt_path.resolve(strict=True)
        qcdt_provenance = args.qcdt_provenance.resolve(strict=True)
        control_binding = None
        if args.offline_control_derived_qcdt:
            package_root = args.control_package_root.resolve(strict=True)
            package_provenance = args.control_package_provenance.resolve(strict=True)
            run_record = json.loads(args.control_package_run_json.read_text())
            artifact_record = json.loads(args.control_package_artifact_json.read_text())
            root_tree_artifact_record = json.loads(args.control_root_tree_artifact_json.read_text())
            control_binding = validate_control_package(
                root_tree, qcdt_path, qcdt_provenance, args.root_tree_archive,
                package_provenance_path=package_provenance,
                root_tree_transport=restored_tree_binding,
                run_record=run_record,
                artifact_record=artifact_record,
                root_tree_artifact_record=root_tree_artifact_record,
                package_run_id=args.control_package_run_id,
                package_artifact_id=args.control_package_artifact_id,
                package_artifact_name=args.control_package_artifact_name,
                package_artifact_digest=args.control_package_artifact_digest,
                root_tree_artifact_id=args.control_root_tree_artifact_id,
                root_tree_artifact_digest=args.control_root_tree_artifact_digest,
                expected_branch=args.control_package_branch,
            )
            if not (package_root / "package-provenance.json").is_file() or \
                    sha256(package_root / "package-provenance.json") != sha256(package_provenance):
                raise ValueError("selected package root does not contain the bound package provenance")
        report = build_image(
            root_tree, qcdt_path, qcdt_provenance, output,
            args.size, args.volume_name,
            offline_control_derived=args.offline_control_derived_qcdt,
            stock_boot_image=args.stock_boot_image,
            control_package_binding=control_binding,
            root_tree_transport=restored_tree_binding,
            root_tree_artifact_binding=root_tree_artifact_binding,
        )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
