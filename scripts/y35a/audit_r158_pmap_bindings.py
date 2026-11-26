#!/usr/bin/env python3
"""Audit the original 16G102 prelink bindings for the R155 pmap APIs.

This is an offline identity and ownership check. It reads one pinned kernelcache,
maps __PRELINK_LINKKASLROffsets to original KEXT data slots, and emits JSON on
stdout. It does not infer runtime reachability, emit a graft, or modify inputs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys
from capstone import CS_ARCH_ARM64, CS_MODE_ARM, Cs

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "kits/XnuPrelink"))
import native_prelink as np

EXPECTED_KERNEL_SHA256 = "70e80388d42fe2376096bb6248073b0380dd87b85b1a792b36205ba60c722ce1"
API_OWNERS = {
    0xFFFFFFF0071B6048: ("_pmap_claim_reserved_ppl_page", "com.apple.kec.corecrypto"),
    0xFFFFFFF0071B60E4: ("_pmap_free_reserved_ppl_page", "com.apple.kec.corecrypto"),
    0xFFFFFFF0071B6160: ("_pmap_load_image4_trust_cache", "com.apple.driver.AppleMobileFileIntegrity"),
    0xFFFFFFF0071B6958: ("_pmap_load_legacy_trust_cache", "com.apple.driver.AppleMobileFileIntegrity"),
    0xFFFFFFF0071B6B54: ("_pmap_is_trust_cache_loaded", "com.apple.driver.AppleMobileFileIntegrity"),
    0xFFFFFFF0071B6E00: ("_pmap_lookup_in_loaded_trust_caches", "com.apple.driver.AppleMobileFileIntegrity"),
    0xFFFFFFF0071B7240: ("_pmap_lookup_in_static_trust_cache", "com.apple.driver.AppleMobileFileIntegrity"),
    0xFFFFFFF0071B7484: ("_pmap_in_ppl", "com.apple.kec.corecrypto"),
}
EXPECTED_SITES = {
    0xFFFFFFF0071B6048: 0xFFFFFFF006DFC508,
    0xFFFFFFF0071B60E4: 0xFFFFFFF006DFC510,
    0xFFFFFFF0071B7484: 0xFFFFFFF006DFC518,
    0xFFFFFFF0071B6B54: 0xFFFFFFF006E1FF48,
    0xFFFFFFF0071B6160: 0xFFFFFFF006E1FF50,
    0xFFFFFFF0071B6958: 0xFFFFFFF006E1FF58,
    0xFFFFFFF0071B6E00: 0xFFFFFFF006E1FF60,
    0xFFFFFFF0071B7240: 0xFFFFFFF006E1FF68,
}
AMFI_THUNK_SLOTS = {
    0xF48: "_pmap_is_trust_cache_loaded",
    0xF50: "_pmap_load_image4_trust_cache",
    0xF58: "_pmap_load_legacy_trust_cache",
    0xF60: "_pmap_lookup_in_loaded_trust_caches",
    0xF68: "_pmap_lookup_in_static_trust_cache",
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--kernelcache",
        type=Path,
        default=ROOT / "out/ipsw/16G102/kernelcache.decompressed",
    )
    args = parser.parse_args()

    data = args.kernelcache.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != EXPECTED_KERNEL_SHA256:
        raise SystemExit(
            f"unexpected kernelcache SHA-256: {digest} (expected {EXPECTED_KERNEL_SHA256})"
        )

    image = np.macho(data)
    info = next((s for s in image["segments"] if s["name"] == "__PRELINK_INFO"), None)
    prelink_text = next((s for s in image["segments"] if s["name"] == "__PRELINK_TEXT"), None)
    if info is None or prelink_text is None:
        raise SystemExit("kernelcache lacks __PRELINK_INFO or __PRELINK_TEXT")
    info_offset = np.backed_offset(image["segments"], info["va"], info["filesize"], len(data))
    metadata = np.unserialize_xml(data[info_offset:info_offset + info["filesize"]])

    packed_offsets = metadata.get("_PrelinkLinkKASLROffsets")
    if not isinstance(packed_offsets, bytes) or len(packed_offsets) < 4:
        raise SystemExit("missing __PRELINK_LINKKASLROffsets")
    count, = struct.unpack_from("<I", packed_offsets)
    if len(packed_offsets) != 4 + count * 4:
        raise SystemExit("invalid __PRELINK_LINKKASLROffsets length")
    offsets = struct.unpack_from(f"<{count}I", packed_offsets, 4)
    if len(set(offsets)) != count:
        raise SystemExit("duplicate __PRELINK_LINKKASLROffsets entry")

    module_ranges: list[tuple[int, int, str, str]] = []
    for entry in metadata.get("_PrelinkInfoDictionary", []):
        bundle = entry.get("CFBundleIdentifier")
        load_address = entry.get("_PrelinkExecutableLoadAddr")
        executable_size = entry.get("_PrelinkExecutableSize")
        if not isinstance(bundle, str) or not isinstance(load_address, int) or not executable_size:
            continue
        try:
            module_offset = np.backed_offset(image["segments"], load_address, 32, len(data))
            module = np.macho(data, module_offset)
        except (ValueError, struct.error):
            continue
        for segment in module["segments"]:
            if segment["size"] and segment["name"] != "__LINKEDIT":
                module_ranges.append((segment["va"], segment["va"] + segment["size"], bundle, segment["name"]))

    prelink_bindings: dict[int, list[dict[str, str]]] = {target: [] for target in API_OWNERS}
    for offset in offsets:
        site = prelink_text["va"] + offset
        try:
            file_offset = np.backed_offset(image["segments"], site, 8, len(data))
        except ValueError:
            continue
        target, = struct.unpack_from("<Q", data, file_offset)
        if target not in API_OWNERS:
            continue
        owners = [item for item in module_ranges if item[0] <= site < item[1]]
        if len(owners) != 1:
            raise SystemExit(f"binding site {site:#x} has {len(owners)} KEXT owners")
        _, _, bundle, segment = owners[0]
        symbol, expected_owner = API_OWNERS[target]
        if bundle != expected_owner:
            raise SystemExit(f"{symbol} bound from unexpected owner {bundle}")
        prelink_bindings[target].append({
            "symbol": symbol,
            "target_va": f"0x{target:016x}",
            "site_va": f"0x{site:016x}",
            "site_file_offset": f"0x{file_offset:x}",
            "owner": bundle,
            "owner_segment": segment,
        })

    result = []
    for target, (symbol, owner) in API_OWNERS.items():
        bindings = prelink_bindings[target]
        if len(bindings) != 1:
            raise SystemExit(f"{symbol}: expected one pointer binding, found {len(bindings)}")
        binding = bindings[0]
        if int(binding["site_va"], 16) != EXPECTED_SITES[target]:
            raise SystemExit(f"{symbol}: unexpected pointer site {binding['site_va']}")
        result.append(binding)

    amfi_entry = next(
        (entry for entry in metadata.get("_PrelinkInfoDictionary", [])
         if entry.get("CFBundleIdentifier") == "com.apple.driver.AppleMobileFileIntegrity"),
        None,
    )
    if amfi_entry is None:
        raise SystemExit("AppleMobileFileIntegrity metadata entry is absent")
    amfi_offset = np.backed_offset(
        image["segments"], amfi_entry["_PrelinkExecutableLoadAddr"], 32, len(data)
    )
    amfi_image = np.macho(data, amfi_offset)
    amfi_text = next((segment for segment in amfi_image["segments"]
                      if segment["name"] == "__TEXT_EXEC"), None)
    if amfi_text is None:
        raise SystemExit("AppleMobileFileIntegrity __TEXT_EXEC is absent")
    amfi_text_offset = np.backed_offset(
        image["segments"], amfi_text["va"], amfi_text["filesize"], len(data)
    )
    amfi_code = data[amfi_text_offset:amfi_text_offset + amfi_text["filesize"]]
    disassembler = Cs(CS_ARCH_ARM64, CS_MODE_ARM)
    disassembler.detail = True
    amfi_instructions = list(disassembler.disasm(amfi_code, amfi_text["va"]))
    amfi_thunks = {}
    for index, instruction in enumerate(amfi_instructions[:-2]):
        if instruction.mnemonic != "adrp" or not instruction.operands:
            continue
        page = instruction.operands[1].imm & ((1 << 64) - 1)
        if page != 0xFFFFFFF006E1F000:
            continue
        load = amfi_instructions[index + 1]
        branch = amfi_instructions[index + 2]
        if load.mnemonic != "ldr" or branch.mnemonic != "br":
            continue
        if not load.operands or len(load.operands) < 2:
            continue
        memory = load.operands[1]
        if memory.type != 3 or memory.mem.base != instruction.operands[0].reg:
            continue
        slot = memory.mem.disp
        if slot in AMFI_THUNK_SLOTS:
            amfi_thunks[AMFI_THUNK_SLOTS[slot]] = {
                "slot": f"0x{slot:x}",
                "thunk_va": f"0x{instruction.address:016x}",
                "load": f"{instruction.mnemonic} {instruction.op_str}",
                "branch": f"{branch.mnemonic} {branch.op_str}",
            }
    if set(amfi_thunks) != set(AMFI_THUNK_SLOTS.values()):
        missing = sorted(set(AMFI_THUNK_SLOTS.values()) - set(amfi_thunks))
        raise SystemExit("missing AMFI pmap import thunks: " + ", ".join(missing))

    print(json.dumps({
        "schema": 1,
        "input": str(args.kernelcache),
        "kernelcache_sha256": digest,
        "prelink_pointer_count": count,
        "evidence_scope": "static original pointer bindings and KEXT ownership only; not runtime reachability",
        "bindings": result,
        "amfi_import_thunks": amfi_thunks,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
