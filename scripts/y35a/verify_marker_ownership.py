#!/usr/bin/env python3
"""Enforce exact source ownership for native external phase markers.

The contract is deliberately explicit. Every expected marker must occur once
with its declared name, value, source owner and aligned offset. Any unapproved
same-slot or partial overlap fails. A linked-disassembly check can be added by
the caller after the source gate; this script never treats an empty hit set as
success.
"""

import argparse
import json
import re
from pathlib import Path


CALL_RE = re.compile(
    r"native_external_phase_marker\s*\(\s*[^,;\n]+,\s*"
    r"(0x[0-9a-fA-F]+)(?:ULL|UL|U|L)?,\s*"
    r"(0x[0-9a-fA-F]+)(?:ULL|UL|U|L)?\s*\)\s*;"
    r"\s*(?:/\*\s*([^*]+?)\s*\*/)?"
)


def codeword_name(value):
    raw = int(value).to_bytes(8, "little", signed=False)
    try:
        return raw.rstrip(b"\0").decode("ascii")
    except UnicodeDecodeError:
        return f"0x{int(value):016x}"


def source_hits(root):
    hits = []
    for path in sorted(root.rglob("*")):
        if path.suffix not in {".c", ".h", ".cpp", ".S"}:
            continue
        try:
            text = path.read_text(errors="replace")
        except OSError:
            continue
        for match in CALL_RE.finditer(text):
            line = text.count("\n", 0, match.start()) + 1
            comment = (match.group(3) or "").strip()
            value = int(match.group(2), 16)
            name = comment.split(":", 1)[0].strip() if comment else codeword_name(value)
            hits.append({
                "path": path.relative_to(root).as_posix(),
                "line": line,
                "offset": int(match.group(1), 16),
                "value": value,
                "name": name,
                "comment": comment,
                "name_source": "comment" if comment else "codeword",
            })
    return hits


def interval(item):
    return item["offset"], item["offset"] + 8


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    args = parser.parse_args()
    contract = json.loads(args.contract.read_text())
    expected = contract.get("markers")
    failures = []
    if not isinstance(expected, list) or not expected:
        failures.append("contract must contain a non-empty markers list")
        expected = []

    expected_by_offset = {}
    for marker in expected:
        required = ("name", "value", "offset", "owner", "position")
        missing = [key for key in required if key not in marker]
        if missing:
            failures.append(f"contract marker missing fields: {missing}")
            continue
        marker = dict(marker)
        marker["value"] = int(str(marker["value"]), 0)
        marker["offset"] = int(str(marker["offset"]), 0)
        marker["owner"] = str(marker["owner"])
        marker["name"] = str(marker["name"])
        if marker.get("ascii_le"):
            try:
                encoded_name = marker["name"].encode("ascii")
            except UnicodeEncodeError:
                failures.append(f"marker {marker['name']} is not ASCII")
                encoded_name = b""
            if len(encoded_name) > 8:
                failures.append(f"marker {marker['name']} exceeds the 8-byte codeword width")
            elif marker["value"] != int.from_bytes(encoded_name, "little"):
                failures.append(
                    f"{marker['name']} codeword {marker['value']:#x} != little-endian ASCII name "
                    f"{int.from_bytes(encoded_name, 'little'):#x}"
                )
        if marker["offset"] % 8:
            failures.append(f"contract marker {marker['name']} is not 8-byte aligned")
        expected_by_offset.setdefault(marker["offset"], []).append(marker)

    for left in expected:
        if "offset" not in left:
            continue
        left_offset = int(str(left["offset"]), 0)
        for right in expected:
            if "offset" not in right or left is right:
                continue
            right_offset = int(str(right["offset"]), 0)
            if left_offset < right_offset < left_offset + 8 or right_offset < left_offset < right_offset + 8:
                failures.append(f"contract marker ranges overlap: {left.get('name')} and {right.get('name')}")

    hits = source_hits(args.source_root)
    by_offset = {}
    by_name = {}
    for hit in hits:
        by_offset.setdefault(hit["offset"], []).append(hit)
        by_name.setdefault(hit["name"], []).append(hit)

    # This is a global structural check, including inherited markers. A gate
    # that only inspects the newly requested offsets can otherwise pass an old
    # source tree with duplicate or unaligned writers elsewhere in the same
    # carrier.
    for hit in hits:
        if hit["offset"] % 8:
            failures.append(f"unaligned marker {hit['name']} at {hit['path']}:{hit['line']} ({hit['offset']:#x})")
    authorized_reuse = contract.get("authorized_reuse", {})
    if not isinstance(authorized_reuse, dict):
        failures.append("authorized_reuse must be an object")
        authorized_reuse = {}
    for offset, same_slot in by_offset.items():
        if len(same_slot) <= 1:
            continue
        key = hex(offset)
        allowed = authorized_reuse.get(key, authorized_reuse.get(str(offset)))
        identities = [hit["path"] + ":" + str(hit["line"]) for hit in same_slot]
        if allowed is None:
            failures.append(f"duplicate marker offset {offset:#x}: {identities}")
        elif list(allowed) != identities:
            failures.append(f"authorized source-order writers at {offset:#x} are {identities}, contract requires {list(allowed)}")

    carrier = contract.get("carrier")
    if not isinstance(carrier, dict) or "base_offset" not in carrier or "bytes" not in carrier:
        failures.append("contract must declare carrier.base_offset and carrier.bytes")
        carrier = None
    if carrier is not None:
        carrier_base = int(str(carrier["base_offset"]), 0)
        carrier_end = carrier_base + int(str(carrier["bytes"]), 0)
        for marker in expected:
            if "offset" not in marker or "name" not in marker:
                continue
            offset = int(str(marker["offset"]), 0)
            if not (carrier_base <= offset and offset + 8 <= carrier_end):
                failures.append(f"required marker {marker['name']} at {offset:#x} is outside carrier {carrier_base:#x}..{carrier_end:#x}")

    matched_hits = set()
    for marker in expected:
        if not all(key in marker for key in ("name", "value", "offset", "owner", "position")):
            continue
        name = str(marker["name"])
        offset = int(str(marker["offset"]), 0)
        value = int(str(marker["value"]), 0)
        owner = str(marker["owner"])
        candidates = [
            (index, hit) for index, hit in enumerate(hits)
            if hit["offset"] == offset and hit["path"] == owner
            and ("line" not in marker or hit["line"] == int(marker["line"]))
        ]
        if len(candidates) != 1:
            failures.append(f"expected exactly one source hit for {name} at {offset:#x} owned by {owner}, found {len(candidates)}")
            continue
        index, hit = candidates[0]
        matched_hits.add(index)
        if hit["name"] != name:
            failures.append(f"offset {offset:#x} is named {hit['name']}, expected {name}")
        if hit["value"] != value:
            failures.append(f"{name} value {hit['value']:#x} != contract {value:#x}")
        if hit["path"] != owner:
            failures.append(f"{name} owner {hit['path']} != contract {owner}")
    for index, hit in enumerate(hits):
        if index not in matched_hits:
            failures.append(f"uncontracted source writer {hit['name']} at {hit['path']}:{hit['line']} ({hit['offset']:#x})")

    report = {
        "ok": not failures,
        "expected_count": len(expected),
        "source_hit_count": len(hits),
        "reused_offsets": {hex(offset): [hit["name"] for hit in same_slot] for offset, same_slot in by_offset.items() if len(same_slot) > 1},
        "marker_width_bytes": 8,
        "failures": failures,
        "hits": hits,
    }
    print(json.dumps(report, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
