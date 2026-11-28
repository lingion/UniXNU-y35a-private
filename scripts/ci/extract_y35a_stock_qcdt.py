#!/usr/bin/env python3
"""Extract a provenance-bound PD1502A QCDT from the pinned full stock boot image."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from pathlib import PurePosixPath
import re

from build_y35a_tf_apfs_image import extract_qcdt_from_pd1502a_boot_image


def extract(stock_boot_image: Path, output_dir: Path, source_commit: str,
            source_boot_repo_path: str) -> dict:
    if not re.fullmatch(r"[0-9a-f]{40}", source_commit):
        raise ValueError("source commit must be a full lowercase Git SHA-1")
    repo_path = PurePosixPath(source_boot_repo_path)
    if (not source_boot_repo_path or repo_path.is_absolute()
            or any(part in ("", ".", "..") for part in repo_path.parts)):
        raise ValueError("source boot path must be a safe repository-relative path")
    source = extract_qcdt_from_pd1502a_boot_image(stock_boot_image)
    output_dir = output_dir.resolve()
    if output_dir.exists():
        if not output_dir.is_dir() or any(output_dir.iterdir()):
            raise ValueError(f"refusing to overwrite stock-QCDT intake output: {output_dir}")
    else:
        output_dir.mkdir(parents=True)
    qcdt_path = output_dir / "y35a.qcdt"
    provenance_path = output_dir / "y35a.qcdt.json"
    qcdt_path.write_bytes(source["qcdt_bytes_data"])
    provenance = {
        "schema_version": 1,
        "source_type": "stock-qcdt",
        "board": "PD1502A",
        "origin": "stock-boot-image",
        "sha256_scope": "qcdt-bytes",
        "sha256": source["qcdt_sha256"],
        "source_boot_path": repo_path.as_posix(),
        "source_boot_bytes": source["boot_bytes"],
        "source_boot_sha256": source["boot_sha256"],
        "source_boot_version": "PD1502A_A_1.18.0",
        "source_repository_commit": source_commit,
        "qcdt_offset": source["qcdt_offset"],
        "qcdt_bytes": source["qcdt_bytes"],
    }
    provenance_path.write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n")
    return {
        "qcdt_path": qcdt_path,
        "provenance_path": provenance_path,
        "provenance": provenance,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stock-boot-image", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--source-boot-repo-path", required=True)
    args = parser.parse_args()
    result = extract(args.stock_boot_image, args.output_dir, args.source_commit,
                     args.source_boot_repo_path)
    print(json.dumps({
        "qcdt_path": result["qcdt_path"].name,
        "qcdt_sha256": result["provenance"]["sha256"],
        "provenance_path": result["provenance_path"].name,
        "source_boot_sha256": result["provenance"]["source_boot_sha256"],
        "source_boot_bytes": result["provenance"]["source_boot_bytes"],
        "source_repository_commit": result["provenance"]["source_repository_commit"],
        "qcdt_offset": result["provenance"]["qcdt_offset"],
        "qcdt_bytes": result["provenance"]["qcdt_bytes"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
