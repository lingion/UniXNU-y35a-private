#!/usr/bin/env python3
"""Host-only model of the recoverable iOS 12 v1 TrustCache ABI subset.

This models behavior recovered from the original 16G102 ARM64 kernelcache:
sorted static lookup, linked loaded-cache lookup, UUID duplicate rejection,
and the reserved-page pool. It does not claim to implement PPL or Image4.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
from dataclasses import dataclass
from pathlib import Path


HEADER_BYTES = 24
ENTRY_BYTES = 22
CDHASH_BYTES = 20
UUID_BYTES = 16


@dataclass(frozen=True)
class TrustEntry:
    cdhash: bytes
    hash_type: int
    flags: int


@dataclass
class LoadedCache:
    uuid: bytes
    entries: tuple[TrustEntry, ...]
    next: "LoadedCache | None" = None


class ReservedPagePool:
    def __init__(self, pages: list[int]):
        self._pages = list(pages)

    def claim(self) -> int:
        if not self._pages:
            raise RuntimeError("reserved PPL page pool exhausted")
        return self._pages.pop(0)

    def free(self, page: int) -> None:
        self._pages.insert(0, page)


def parse_v1(data: bytes) -> tuple[bytes, tuple[TrustEntry, ...]]:
    if len(data) < HEADER_BYTES:
        raise ValueError("TrustCache is shorter than the v1 header")
    version, uuid, count = struct.unpack_from("<I16sI", data, 0)
    if version != 1:
        raise ValueError(f"unsupported TrustCache version {version}")
    expected = HEADER_BYTES + count * ENTRY_BYTES
    if expected != len(data):
        raise ValueError(f"size mismatch: expected {expected}, got {len(data)}")
    entries = []
    previous = None
    for offset in range(HEADER_BYTES, len(data), ENTRY_BYTES):
        cdhash = data[offset:offset + CDHASH_BYTES]
        hash_type = data[offset + 20]
        flags = data[offset + 21]
        if previous is not None and cdhash < previous:
            raise ValueError("TrustCache CDHashes are not sorted")
        previous = cdhash
        entries.append(TrustEntry(cdhash, hash_type, flags))
    return uuid, tuple(entries)


def lookup_static(entries: tuple[TrustEntry, ...], cdhash: bytes) -> TrustEntry | None:
    lo, hi = 0, len(entries)
    while lo < hi:
        mid = (lo + hi) // 2
        candidate = entries[mid].cdhash
        if candidate == cdhash:
            return entries[mid]
        if candidate < cdhash:
            lo = mid + 1
        else:
            hi = mid
    return None


def lookup_loaded(head: LoadedCache | None, cdhash: bytes) -> TrustEntry | None:
    current = head
    while current is not None:
        found = lookup_static(current.entries, cdhash)
        if found is not None:
            return found
        current = current.next
    return None


def load_legacy(head: LoadedCache | None, uuid: bytes, entries: tuple[TrustEntry, ...]) -> tuple[LoadedCache, int]:
    current = head
    while current is not None:
        if current.uuid == uuid:
            return head, 11
        current = current.next
    return LoadedCache(uuid, entries, head), 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("trustcache", type=Path)
    parser.add_argument("--dyld-cdhash", required=True)
    parser.add_argument("--launchd-cdhash", required=True)
    args = parser.parse_args()

    data = args.trustcache.read_bytes()
    uuid, entries = parse_v1(data)
    dyld = bytes.fromhex(args.dyld_cdhash)
    launchd = bytes.fromhex(args.launchd_cdhash)
    missing = bytes(CDHASH_BYTES)
    if len(dyld) != CDHASH_BYTES or len(launchd) != CDHASH_BYTES:
        raise SystemExit("CDHash arguments must be 20-byte hex values")

    static_dyld = lookup_static(entries, dyld)
    static_launchd = lookup_static(entries, launchd)
    static_missing = lookup_static(entries, missing)
    head, first_load = load_legacy(None, uuid, entries)
    _, duplicate_load = load_legacy(head, uuid, entries)
    loaded_launchd = lookup_loaded(head, launchd)
    pool = ReservedPagePool([0x1000, 0x2000])
    first_page = pool.claim()
    pool.free(first_page)
    recycled_page = pool.claim()

    result = {
        "schema": 1,
        "input_sha256": hashlib.sha256(data).hexdigest(),
        "version": 1,
        "uuid": uuid.hex(),
        "entry_count": len(entries),
        "entry_bytes": ENTRY_BYTES,
        "static_dyld": None if static_dyld is None else {"hash_type": static_dyld.hash_type, "flags": static_dyld.flags},
        "static_launchd": None if static_launchd is None else {"hash_type": static_launchd.hash_type, "flags": static_launchd.flags},
        "static_missing": static_missing is not None,
        "loaded_launchd": None if loaded_launchd is None else {"hash_type": loaded_launchd.hash_type, "flags": loaded_launchd.flags},
        "first_legacy_load_return": first_load,
        "duplicate_legacy_load_return": duplicate_load,
        "reserved_page_first_claim": hex(first_page),
        "reserved_page_recycled_claim": hex(recycled_page),
        "image4_implementation": "unresolved; no constant-success path",
        "ppl_implementation": "pmap_in_ppl=false in original iOS 12 ARM64; page pool modeled separately",
    }
    print(json.dumps(result, indent=2))
    if not static_dyld or not static_launchd or static_missing or not loaded_launchd:
        raise SystemExit("TrustCache harness acceptance failed")
    if first_load != 0 or duplicate_load != 11 or recycled_page != first_page:
        raise SystemExit("legacy/page-pool acceptance failed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
