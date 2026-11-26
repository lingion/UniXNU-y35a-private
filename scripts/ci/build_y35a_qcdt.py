#!/usr/bin/env python3
"""Compile the pinned Y35A DTS and wrap its FDT in the LK2nd QCDT v3 table."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import tempfile


PAGE_SIZE = 2048
QCDT_MAGIC = 0x54444351
BOARD_IDS = (206, 8, 23)
DTS_SHA256 = "4b2a7fda53ab9b4a69aa3bf9c1247feb7f767b577612914b353f076b391a8714"
ROOT = Path(__file__).resolve().parents[2]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def wrap_fdt(dtb: bytes) -> bytes:
    if len(dtb) < 40 or dtb[:4] != b"\xd0\x0d\xfe\xed":
        raise ValueError("dtc output is not an FDT")
    total_size = struct.unpack_from(">I", dtb, 4)[0]
    if total_size != len(dtb):
        raise ValueError(f"FDT totalsize {total_size} does not match file size {len(dtb)}")

    entry_offset = ((12 + 40 + PAGE_SIZE - 1) // PAGE_SIZE) * PAGE_SIZE
    table = bytearray(entry_offset)
    struct.pack_into("<III", table, 0, QCDT_MAGIC, 3, 1)
    fields = (*BOARD_IDS, 0, 0, 0, 0, 0, entry_offset, len(dtb))
    struct.pack_into("<10I", table, 12, *fields)
    table.extend(dtb)
    table.extend(bytes((-len(table)) % PAGE_SIZE))
    return bytes(table)


def build_qcdt(dts: Path, dtc: Path, output: Path, dtc_revision: str) -> dict:
    dts = dts.resolve(strict=True)
    dtc = dtc.resolve(strict=True)
    output = output.resolve()
    if output.exists():
        raise SystemExit(f"refusing to overwrite existing output: {output}")

    source_sha256 = sha256(dts)
    if source_sha256 != DTS_SHA256:
        raise SystemExit(f"Y35A DTS SHA-256 mismatch: {source_sha256}")

    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="y35a-dtc-", dir=output.parent) as temporary:
        dtb_path = Path(temporary) / "y35a.dtb"
        subprocess.run(
            [str(dtc), "-I", "dts", "-O", "dtb", "-o", str(dtb_path), str(dts)],
            check=True,
        )
        dtb = dtb_path.read_bytes()

    qcdt = wrap_fdt(dtb)
    output.write_bytes(qcdt)
    report = {
        "schema_version": 1,
        "source_type": "derived",
        "dts_path": dts.relative_to(ROOT).as_posix(),
        "dts_sha256": source_sha256,
        "dtc_sha256": sha256(dtc),
        "dtc_revision": dtc_revision,
        "dtb_sha256": hashlib.sha256(dtb).hexdigest(),
        "qcdt_path": output.name,
        "qcdt_sha256": hashlib.sha256(qcdt).hexdigest(),
        "qcdt_version": 3,
        "qcdt_entry": {
            "platform_id": BOARD_IDS[0],
            "variant_id": BOARD_IDS[1],
            "subtype_id": BOARD_IDS[2],
            "offset": PAGE_SIZE,
            "size": len(dtb),
        },
    }
    report_path = output.with_suffix(output.suffix + ".json")
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dts", required=True, type=Path)
    parser.add_argument("--dtc", required=True, type=Path)
    parser.add_argument("--dtc-revision", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(build_qcdt(args.dts, args.dtc, args.output, args.dtc_revision), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
