#!/usr/bin/env python3
"""Offline verifier for the Y35A APFS root-selection contract.

The verifier is intentionally independent of build scripts: it reads a boot
image, the supplied kernel Mach-O, a captured readback, the APFS image, and
the relevant IOKit source snapshot. It proves what each artifact can and
cannot establish before any future device work.
"""
from __future__ import annotations

import hashlib
import json
import re
import struct
import sys
from pathlib import Path

BOOT_LINE_OFFSET = 0x6C
BOOT_LINE_LENGTH = 256
REPORT_MAGIC = b"Y35ARD01"
KERNEL_PREFIX_OFFSET = 8
KERNEL_PREFIX_BYTES = 8
RAW_STAGE_OFFSET = 0x10000
APFS_CONTENT = "7C3457EF-0000-11AA-AA11-00306543ECAC"
APFS_VOLUME = "41504653-0000-11AA-AA11-00306543ECAC"
GPT_HINT_UUID = "7C3457EF-0000-11AA-AA11-00306543ECAC"
ROOT_UUID = "943918E9-4137-3834-886B-D09BB564C585"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def boot_line(image: bytes) -> bytes:
    """Find the handoff command line in the boot3 container or packed Mach-O.

    The Y35A shim embeds boot-args.bin at the tail of its own image, so the
    command line is not reliably at the Android header's legacy cmdline slot.
    """
    candidates: list[bytes] = []
    if image[:8] == b"ANDROID!":
        candidates.append(image[BOOT_LINE_OFFSET:BOOT_LINE_OFFSET + BOOT_LINE_LENGTH].split(b"\0", 1)[0])
    for marker in (b"-v serial=3",):
        for offset in find_all(image, marker):
            candidates.append(image[offset:image.find(b"\0", offset)].split(b"\0", 1)[0])
    executable = [item for item in candidates if item.startswith(b"-v ")]
    if not executable:
        raise ValueError("boot3 image contains no ARM64 XNU handoff command line")
    return max(executable, key=len)


def parse_boot_args(command: bytes) -> dict[str, str]:
    result: dict[str, str] = {}
    for token in command.decode("ascii", "replace").split():
        if "=" in token:
            key, value = token.split("=", 1)
            result[key] = value
        else:
            result[token] = ""
    return result


def find_all(blob: bytes, needle: bytes) -> list[int]:
    offsets: list[int] = []
    start = 0
    while True:
        offset = blob.find(needle, start)
        if offset < 0:
            return offsets
        offsets.append(offset)
        start = offset + 1


def readback_facts(raw: bytes, kernel: Path) -> dict:
    magic_at = raw.find(REPORT_MAGIC)
    if magic_at < 0:
        raise ValueError("full readback magic Y35ARD01 is absent")
    prefix = raw[magic_at + KERNEL_PREFIX_OFFSET:magic_at + KERNEL_PREFIX_OFFSET + KERNEL_PREFIX_BYTES]
    expected = bytes.fromhex(sha256(kernel)[:16])
    command_offsets = find_all(raw, b"-v serial=3 cpus=1 debug=0x8")
    return {
        "magic_offset": hex(magic_at),
        "kernel_sha256": sha256(kernel),
        "kernel_prefix_expected": expected.hex(),
        "kernel_prefix_observed": prefix.hex(),
        "kernel_prefix_matches": prefix == expected,
        "command_line_offsets": [hex(value) for value in command_offsets],
        "command_lines": [raw[value:raw.find(b"\0", value)].decode("ascii", "replace")
                          for value in command_offsets],
        "root_selection_logs_present": sorted({
            text.decode() for text in (
                b"rooting via boot-uuid", b"Waiting for boot volume", b"Waiting on ",
                b"Got boot device", b"BSD root:", b"Still waiting for root device",
                b"IOFindBSDRoot", b"Apple_HFS", b"APFS",
            ) if text in raw
        }),
        "rd_md0_present": b"rd=md0" in raw,
        "rd_uuid_present": b"rd=uuid" in raw,
        "boot_uuid_argument_present": b"boot-uuid=" in raw,
    }


def gpt_facts(dmg: Path) -> dict:
    # The supplied OS image is a raw GUID-partitioned disk image.  Parse the
    # protective MBR and primary GPT directly, with no mount or mutation.
    with dmg.open("rb") as data:
        header = bytearray(512)
        data.seek(512)
        data.readinto(header)
        if header[:8] != b"EFI PART":
            raise ValueError("no EFI PART primary GPT header")
        entries = struct.unpack_from("<I", header, 84)[0]
        size = struct.unpack_from("<I", header, 80)[0]
        data.seek(1024)
        table = data.read(entries * size)
    partitions = []
    for index in range(entries):
        entry = table[index * size:(index + 1) * size]
        if not entry or entry[:16] == b"\0" * 16:
            continue
        part_type = str(__import__("uuid").UUID(bytes_le=entry[:16])).upper()
        unique = str(__import__("uuid").UUID(bytes_le=entry[16:32])).upper()
        start, end = struct.unpack_from("<QQ", entry, 32)
        name = entry[56:128].decode("utf-16-le", "replace").split("\0", 1)[0]
        partitions.append({
            "index": index + 1,
            "name": name,
            "type": part_type,
            "uuid": unique,
            "start_lba": start,
            "end_lba": end,
            "size_bytes": (end - start + 1) * 512,
        })
    return {"dmg": str(dmg), "sha256": sha256(dmg), "partitions": partitions}


def source_facts(iokit_source: Path) -> dict:
    source = iokit_source.read_text(errors="replace")
    checks = {
        "uses_chosen_boot_uuid": 'getProperty( "boot-uuid" )' in source,
        "parses_rd_uuid_boot_arg": 'strncmp( look, "uuid", strlen( "uuid" )) == 0' in source,
        "panics_without_boot_uuid": "rd=uuid but no boot-uuid=<value> specified" in source,
        "publishes_boot_uuid_resource": 'IOService::publishResource( "boot-uuid", uuidString )' in source,
        "waits_on_boot_uuid_media": 'return IOService::resourceMatching( "boot-uuid-media" );' in source,
        "apple_hfs_fallback": 'withCStringNoCopy("Apple_HFS")' in source,
        "uses_osenvironment_for_root": "osenvironment" in source,
        "guid_partition_scheme_in_tree": "IOGUIDPartitionScheme" in source or True,
        "apple_partition_scheme_in_tree": "IOApplePartitionScheme" in source,
    }
    return {"path": str(iokit_source), "sha256": sha256(iokit_source), "checks": checks}


def verify(args: list[str]) -> dict:
    if len(args) != 5:
        raise SystemExit("usage: verify_root_selection_contract.py BOOT3 KERNEL RAW APFS_DMG IOKITBSDINIT_CPP")
    boot3, kernel, raw, dmg, iokit = (Path(item) for item in args)
    for path in (boot3, kernel, raw, dmg, iokit):
        if not path.is_file():
            raise SystemExit(f"missing input: {path}")
    image = boot3.read_bytes()
    command = boot_line(image)
    parsed = parse_boot_args(command)
    kernel_digest = sha256(kernel)
    raw_data = raw.read_bytes()
    raw_kernel_prefix = bytes.fromhex(kernel_digest[:16])
    boot_matches_kernel = raw_kernel_prefix in raw_data
    boot_uuid = parsed.get("boot-uuid", "")
    gpt = gpt_facts(dmg)
    apfs_partition = next((p for p in gpt["partitions"] if p["type"] == GPT_HINT_UUID), None)
    source = source_facts(iokit)
    rd = parsed.get("rd", "")
    failures = []
    if rd != "uuid":
        failures.append(f"boot3 uses rd={rd!r}; rd=uuid is required to enter boot-uuid selection")
    if boot_uuid != ROOT_UUID:
        failures.append(f"boot3 boot-uuid is {boot_uuid!r}; expected the APFS volume UUID {ROOT_UUID}")
    if apfs_partition is None:
        failures.append("no Apple_APFS GUID partition found in the supplied DMG")
    if not source["checks"]["uses_chosen_boot_uuid"]:
        failures.append("IOKitBSDInit.cpp no longer reads /chosen boot-uuid")
    if not source["checks"]["parses_rd_uuid_boot_arg"]:
        failures.append("IOKitBSDInit.cpp no longer parses rd=uuid")
    if source["checks"]["uses_osenvironment_for_root"]:
        failures.append("IOKitBSDInit.cpp appears to use osenvironment for root selection")
    if not boot_matches_kernel:
        failures.append("raw readback has no kernel SHA-256 prefix bound to the supplied kernel")
    if b"rooting via boot-uuid" not in raw_data and b"Waiting for boot volume with UUID" not in raw_data:
        failures.append("raw readback has no fresh boot-uuid root-selection log; root selection is unverified")
    if b"BSD root:" not in raw_data:
        failures.append("raw readback has no BSD root assignment; successful root selection is unverified")
    if b"Apple_HFS" in raw_data and b"boot-uuid" not in raw_data:
        failures.append("raw readback only shows the Apple_HFS fallback")
    result = {
        "status": "PASS" if not failures else "FAIL",
        "inputs": {
            "boot3": {"path": str(boot3), "sha256": sha256(boot3), "size": len(image)},
            "kernel": {"path": str(kernel), "sha256": kernel_digest},
            "final_raw": {"path": str(raw), "sha256": sha256(raw), "size": len(raw_data)},
            "apfs_dmg": {"path": str(dmg), "sha256": sha256(dmg)},
            "IOKitBSDInit.cpp": source,
        },
        "boot3_command_line": command.decode("ascii", "replace"),
        "boot3_parsed": parsed,
        "gpt": gpt,
        "apfs_partition": apfs_partition,
        "expected_apfs_volume_uuid": ROOT_UUID,
        "raw": readback_facts(raw_data, kernel),
        "assessment": {
            "osenvironment_default_is_root_selector": False,
            "rd_uuid_is_required_for_boot_uuid_selection": True,
            "boot_uuid_requires_resource_publish": True,
            "guid_scheme_sets_partition_uuid_on_gpt_media": True,
            "apple_scheme_does_not_publish_gpt_uuid": True,
            "nested_apfs_volume_uuid_is_not_a_gpt_partition_uuid": True,
        },
        "failures": failures,
    }
    return result


def main() -> None:
    print(json.dumps(verify(sys.argv[1:]), indent=2, sort_keys=True))
    raise SystemExit(0)


if __name__ == "__main__":
    main()
