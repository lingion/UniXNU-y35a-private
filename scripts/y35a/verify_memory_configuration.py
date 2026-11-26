#!/usr/bin/env python3
"""Verify the maximum single-span Y35A memory candidate offline.

This gate keeps three evidence scopes separate:

* the supplied candidate boot_args/ADT/manifest;
* a staged lk2nd DTB, which is a direct record of an earlier loader handoff;
* the recorded /proc/iomem windows, whose original dump is still a missing
  artifact in the current host tree.

It does not claim that the staged DTB is the DTB used by the candidate run.
"""

import argparse
import hashlib
import json
import struct
from pathlib import Path


DEFAULT_MEASURED_RANGES = (
    (0x80000000, 0x86000000),
    (0x8C300000, 0x9FF00000),
    (0xA0000000, 0xFFFFF000),
)
RESERVED_RANGES = (
    (0x83000000, 0x84400000, "continuous_splash"),
    (0x86000000, 0x86800000, "external_image_mem"),
    (0x86800000, 0x8BD00000, "modem_adsp_mem"),
    (0x8BD00000, 0x8C300000, "peripheral_mem"),
)


def parse_int(value):
    return int(str(value), 0)


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def overlaps(left, right):
    return left[0] < right[1] and right[0] < left[1]


def parse_adt(blob):
    if isinstance(blob, Path):
        blob = blob.read_bytes()

    def decode(offset):
        properties, children = struct.unpack_from("<II", blob, offset)
        offset += 8
        values = {}
        for _ in range(properties):
            name = blob[offset:offset + 32].split(b"\0", 1)[0].decode()
            length = struct.unpack_from("<I", blob, offset + 32)[0]
            offset += 36
            values[name] = blob[offset:offset + length]
            offset += (length + 3) & ~3
        nodes = {}
        for _ in range(children):
            child, offset = decode(offset)
            name = child[0]["name"].rstrip(b"\0").decode()
            nodes[name] = child
        return (values, nodes), offset

    root, _ = decode(0)
    return root[1]["chosen"][0]


def parse_fdt(path):
    blob = Path(path).read_bytes()
    if len(blob) < 40:
        raise ValueError("FDT header is truncated")
    fields = struct.unpack_from(">10I", blob, 0)
    magic, total, off_struct, off_strings, off_reserve, version, last, strings_size, struct_size = (
        fields[0], fields[1], fields[2], fields[3], fields[4], fields[5], fields[6], fields[8], fields[9]
    )
    if magic != 0xD00DFEED or total > len(blob) or version < 16:
        raise ValueError("unsupported or truncated FDT")
    reserve_map = []
    cursor = off_reserve
    while cursor + 16 <= off_struct:
        address, size = struct.unpack_from(">QQ", blob, cursor)
        cursor += 16
        if address == 0 and size == 0:
            break
        reserve_map.append((address, size))

    strings = blob[off_strings:off_strings + strings_size]

    def string_at(index):
        end = strings.find(b"\0", index)
        if end < 0:
            raise ValueError("FDT property name is not terminated")
        return strings[index:end].decode("ascii")

    nodes = []
    stack = []
    cursor = off_struct
    end = off_struct + struct_size
    while cursor < end:
        token = struct.unpack_from(">I", blob, cursor)[0]
        cursor += 4
        if token == 1:  # FDT_BEGIN_NODE
            name_end = blob.index(b"\0", cursor, end)
            name = blob[cursor:name_end].decode("ascii")
            cursor = (name_end + 4) & ~3
            stack.append(name)
            nodes.append(("/" + "/".join(x for x in stack if x), {}))
        elif token == 2:  # FDT_END_NODE
            stack.pop()
        elif token == 3:  # FDT_PROP
            length, name_index = struct.unpack_from(">II", blob, cursor)
            cursor += 8
            value = blob[cursor:cursor + length]
            cursor = (cursor + length + 3) & ~3
            nodes[-1][1][string_at(name_index)] = value
        elif token == 4:  # FDT_NOP
            continue
        elif token == 9:  # FDT_END
            break
        else:
            raise ValueError(f"unknown FDT token {token:#x}")

    root_props = next(props for path, props in nodes if path == "/")
    address_cells = struct.unpack(">I", root_props.get("#address-cells", b"\0\0\0\2"))[0]
    size_cells = struct.unpack(">I", root_props.get("#size-cells", b"\0\0\0\2"))[0]
    memory = []
    for path, props in nodes:
        if props.get("device_type") != b"memory\0" and not path.rsplit("/", 1)[-1].startswith("memory@"):
            continue
        raw = props.get("reg")
        if raw is None:
            continue
        stride = 4 * (address_cells + size_cells)
        if len(raw) % stride:
            raise ValueError(f"memory reg length is not cell aligned at {path}")
        for offset in range(0, len(raw), stride):
            address = int.from_bytes(raw[offset:offset + 4 * address_cells], "big")
            size_offset = offset + 4 * address_cells
            size = int.from_bytes(raw[size_offset:size_offset + 4 * size_cells], "big")
            memory.append((address, size))
    return {
        "sha256": hashlib.sha256(blob).hexdigest(),
        "model": next((props["model"].rstrip(b"\0").decode() for path, props in nodes if path == "/" and "model" in props), None),
        "memory_ranges": [[hex(address), hex(address + size), size] for address, size in memory],
        "memory_bytes": sum(size for _, size in memory),
        "reserve_map": [[hex(address), hex(size)] for address, size in reserve_map],
    }


def parse_range(raw):
    start, end = raw.split(":", 1)
    start, end = parse_int(start), parse_int(end)
    if start >= end:
        raise ValueError(f"invalid measured range {raw}")
    return start, end


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--boot-args", type=Path, required=True)
    parser.add_argument("--adt", type=Path, required=True)
    parser.add_argument("--runtime-dtb", type=Path)
    parser.add_argument("--expected-size", type=lambda value: int(value, 0), default=0x5FE00000)
    parser.add_argument("--measured-range", action="append", default=[])
    args = parser.parse_args()

    failures = []
    warnings = []
    manifest = json.loads(args.manifest.read_text())
    boot_args = args.boot_args.read_bytes()
    chosen = parse_adt(args.adt)
    virtual_base, physical_base, memory_size, top_of_kernel_data = struct.unpack_from("<QQQQ", boot_args, 8)
    owned_end = physical_base + memory_size
    measured = [parse_range(value) for value in args.measured_range] or list(DEFAULT_MEASURED_RANGES)
    measured_source = (
        "explicit --measured-range arguments"
        if args.measured_range
        else "recorded /proc/iomem ranges in evidence/y35a-20261102/PROGRESS.md:11; original dump not present"
    )

    if memory_size != args.expected_size:
        failures.append(f"boot_args memSize {memory_size:#x} != expected {args.expected_size:#x}")
    if parse_int(manifest["owned_memory"]) != memory_size:
        failures.append("manifest owned_memory != boot_args memSize")
    manifest_range = manifest.get("memory_range", {})
    if parse_int(manifest_range.get("base", "0")) != physical_base:
        failures.append("manifest memory_range.base != boot_args physBase")
    if parse_int(manifest_range.get("end", "0")) != owned_end:
        failures.append("manifest memory_range.end != boot_args physBase + memSize")
    for key, expected in (("dram-base", physical_base), ("dram-size", memory_size), ("darwinboot-memory-size", memory_size)):
        if key not in chosen:
            failures.append(f"ADT chosen is missing {key}")
        elif struct.unpack_from("<Q", chosen[key])[0] != expected:
            failures.append(f"ADT chosen {key} does not match boot_args")

    if not any(start <= physical_base and owned_end <= end for start, end in measured):
        failures.append(f"owned span {physical_base:#x}..{owned_end:#x} is not inside a recorded RAM window")
    for start, end, name in RESERVED_RANGES:
        if overlaps((physical_base, owned_end), (start, end)):
            failures.append(f"owned span overlaps reserved range {name}")
    if parse_int(manifest.get("args_physical", "0")) not in range(physical_base, owned_end):
        failures.append("manifest args_physical is outside owned span")
    if not physical_base <= parse_int(manifest.get("top_of_kernel_data", "0")) < owned_end:
        failures.append("manifest top_of_kernel_data is outside owned span")
    if manifest.get("memory_profile") != "max-contiguous-measured":
        failures.append("manifest memory_profile is not max-contiguous-measured")
    if manifest_range.get("multi_bank_supported") is not False:
        failures.append("manifest does not explicitly declare single-span XNU limitation")

    runtime = None
    if args.runtime_dtb:
        runtime = parse_fdt(args.runtime_dtb)
        if runtime["memory_bytes"] != 0x80000000:
            failures.append(f"staged runtime DTB reports {runtime['memory_bytes']:#x} bytes, expected 0x80000000")
        if runtime["reserve_map"]:
            warnings.append("staged runtime DTB contains FDT reserve-map entries; inspect them before treating all DRAM as free")
        if runtime["sha256"] != "36555c5e66b4a09cd38506706b0a301c2c8b8d6b883de51c51b89971825e9709":
            warnings.append("staged runtime DTB SHA differs from the recorded evidence hash")
        warnings.append("staged runtime DTB is prior loader evidence, not proof of the candidate's final DT")
    else:
        warnings.append("no staged runtime DTB supplied; physical 2 GiB identity remains unbound in this run")

    report = {
        "ok": not failures,
        "profile": manifest.get("memory_profile"),
        "inputs": {
            "manifest": {"path": str(args.manifest), "sha256": sha256_file(args.manifest)},
            "boot_args": {"path": str(args.boot_args), "sha256": sha256_file(args.boot_args)},
            "adt": {"path": str(args.adt), "sha256": sha256_file(args.adt)},
            "runtime_dtb": ({"path": str(args.runtime_dtb), "sha256": runtime["sha256"]}
                            if args.runtime_dtb else None),
        },
        "boot_args": {"virtual_base": hex(virtual_base), "physical_base": hex(physical_base), "memory_size": hex(memory_size), "top_of_kernel_data": hex(top_of_kernel_data)},
        "owned_span": [hex(physical_base), hex(owned_end)],
        "recorded_measured_ranges": [[hex(start), hex(end)] for start, end in measured],
        "measured_ranges_source": measured_source,
        "runtime_dtb": runtime,
        "warnings": warnings,
        "failures": failures,
    }
    print(json.dumps(report, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
