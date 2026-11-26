#!/usr/bin/env python3
"""Verify the pinned iOS 12.4.1 IPSW and extract the package inputs."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import plistlib
import sys
import struct
import zipfile


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from unixnu.ipsw import im4p_payload


def file_hashes(path: Path) -> dict[str, int | str]:
    sha1 = hashlib.sha1()
    sha256 = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            sha1.update(block)
            sha256.update(block)
            size += len(block)
    return {"size": size, "sha1": sha1.hexdigest(), "sha256": sha256.hexdigest()}


def select_identity(manifest: dict, firmware: dict) -> dict:
    expected_version = firmware["version"]
    expected_build = firmware["build"]
    expected_product = firmware["product"]
    if manifest.get("ProductVersion") != expected_version:
        raise ValueError("IPSW ProductVersion does not match the package manifest")
    if manifest.get("ProductBuildVersion") != expected_build:
        raise ValueError("IPSW ProductBuildVersion does not match the package manifest")
    if expected_product not in manifest.get("SupportedProductTypes", []):
        raise ValueError("IPSW does not support the pinned product type")

    matches = []
    for identity in manifest.get("BuildIdentities", []):
        info = identity.get("Info", {})
        if (info.get("DeviceClass") == firmware["device_class"]
                and info.get("RestoreBehavior") == "Erase"
                and int(identity.get("ApChipID", "0"), 16) == 0x7000
                and int(identity.get("ApBoardID", "0"), 16) == 0x08):
            matches.append(identity)
    if len(matches) != 1:
        raise ValueError(f"expected one j96ap erase identity, found {len(matches)}")
    return matches[0]


def extract_component(archive: zipfile.ZipFile, identity: dict, name: str,
                      expected: dict, destination: Path) -> dict:
    component = identity.get("Manifest", {}).get(name)
    if not component:
        raise ValueError(f"BuildManifest is missing component {name}")
    member = component["Info"]["Path"]
    info = archive.getinfo(member)
    if info.file_size != expected["size"]:
        raise ValueError(f"{name} size mismatch: {info.file_size}")

    sha1 = hashlib.sha1()
    sha256 = hashlib.sha256()
    with archive.open(info) as source, destination.open("xb") as target:
        while block := source.read(1 << 20):
            target.write(block)
            sha1.update(block)
            sha256.update(block)
    result = {"member": member, "path": destination.name,
              "size": destination.stat().st_size,
              "sha1": sha1.hexdigest(), "sha256": sha256.hexdigest()}
    if expected.get("sha1") and result["sha1"] != expected["sha1"]:
        raise ValueError(f"{name} SHA-1 mismatch")
    if expected.get("sha256") and result["sha256"] != expected["sha256"]:
        raise ValueError(f"{name} SHA-256 mismatch")
    return result


def validate_trustcache_payload(payload: bytes, expected: dict, component: str) -> dict:
    if len(payload) < 24:
        raise ValueError(f"{component} payload is shorter than its v1 header")
    version, = struct.unpack_from("<I", payload, 0)
    entry_count, = struct.unpack_from("<I", payload, 20)
    if version != expected["payload_version"]:
        raise ValueError(f"unexpected {component} version: {version}")
    if entry_count != expected["payload_entries"]:
        raise ValueError(f"unexpected {component} entry count: {entry_count}")
    if len(payload) != 24 + entry_count * 22:
        raise ValueError(f"{component} payload length does not match its entry count")
    digest = hashlib.sha256(payload).hexdigest()
    if len(payload) != expected["payload_size"]:
        raise ValueError(f"{component} payload size mismatch")
    if expected.get("payload_sha256") and digest != expected["payload_sha256"]:
        raise ValueError(f"{component} payload SHA-256 mismatch")
    return {"version": version, "entries": entry_count,
            "size": len(payload), "sha256": digest}


def validate_restore_trustcache(payload: bytes, expected: dict) -> dict:
    return validate_trustcache_payload(payload, expected, "RestoreTrustCache")


def extract_inputs(ipsw: Path, output: Path, config_path: Path) -> dict:
    config = json.loads(config_path.read_text())
    firmware = config["firmware"]
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise SystemExit(f"Use a new or empty output directory: {output}")
    output.mkdir(parents=True, exist_ok=True)

    archive_hashes = file_hashes(ipsw)
    if archive_hashes["size"] != firmware["size"]:
        raise SystemExit("IPSW size does not match the pinned firmware")
    if archive_hashes["sha256"] != firmware["sha256"]:
        raise SystemExit("IPSW SHA-256 does not match the pinned firmware")

    with zipfile.ZipFile(ipsw) as archive:
        build_manifest = plistlib.loads(archive.read("BuildManifest.plist"))
        identity = select_identity(build_manifest, firmware)
        components = {}
        destinations = {
            "OS": output / "system.dmg",
            "RestoreRamDisk": output / "restore-ramdisk.im4p",
            "RestoreTrustCache": output / "restore-trustcache.im4p",
            "StaticTrustCache": output / "static-trustcache.im4p",
        }
        for name, destination in destinations.items():
            components[name] = extract_component(
                archive, identity, name, firmware["components"][name], destination,
            )

    ramdisk_im4p = (output / components["RestoreRamDisk"]["path"]).read_bytes()
    ramdisk_payload = im4p_payload(ramdisk_im4p)
    ramdisk_expected = firmware["components"]["RestoreRamDisk"]
    if len(ramdisk_payload) != ramdisk_expected["payload_size"]:
        raise SystemExit("RestoreRamDisk payload size mismatch")
    offset = ramdisk_expected["payload_magic_offset"]
    if ramdisk_payload[offset:offset + 2].hex() != ramdisk_expected["payload_magic_hex"]:
        raise SystemExit("RestoreRamDisk payload is not the expected HFSX image")
    payload_path = output / "restore-ramdisk.hfsx"
    payload_path.write_bytes(ramdisk_payload)

    trustcache_im4p = (output / components["RestoreTrustCache"]["path"]).read_bytes()
    trustcache_payload = im4p_payload(trustcache_im4p)
    trustcache_report = validate_restore_trustcache(
        trustcache_payload, firmware["components"]["RestoreTrustCache"],
    )
    trustcache_path = output / "restore-trustcache.bin"
    trustcache_path.write_bytes(trustcache_payload)

    static_trustcache_im4p = (output / components["StaticTrustCache"]["path"]).read_bytes()
    static_trustcache_payload = im4p_payload(static_trustcache_im4p)
    static_trustcache_expected = firmware["components"]["StaticTrustCache"]
    static_trustcache_report = validate_trustcache_payload(
        static_trustcache_payload, static_trustcache_expected, "StaticTrustCache",
    )
    static_trustcache_path = output / "static-trustcache.bin"
    static_trustcache_path.write_bytes(static_trustcache_payload)

    report = {
        "schema_version": 1,
        "ipsw": {"path": ipsw.name, **archive_hashes},
        "identity": {
            "device_class": identity["Info"]["DeviceClass"],
            "restore_behavior": identity["Info"]["RestoreBehavior"],
            "product_version": build_manifest["ProductVersion"],
            "build": build_manifest["ProductBuildVersion"],
            "product": firmware["product"],
        },
        "components": components,
        "restore_ramdisk_payload": {
            "path": payload_path.name,
            **file_hashes(payload_path),
            "format": "HFSX raw image extracted from the pinned IM4P",
        },
        "restore_trustcache_payload": {
            "path": trustcache_path.name,
            **trustcache_report,
            "format": "v1 TrustCache payload extracted from the pinned IM4P",
        },
        "static_trustcache_payload": {
            "path": static_trustcache_path.name,
            **static_trustcache_report,
            "format": "v1 StaticTrustCache payload extracted from the pinned IM4P",
        },
    }
    (output / "firmware-inputs.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ipsw", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--config", type=Path,
                        default=ROOT / "ci/y35a-ci-package-manifest.json")
    args = parser.parse_args()
    print(json.dumps(extract_inputs(args.ipsw, args.output, args.config), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
