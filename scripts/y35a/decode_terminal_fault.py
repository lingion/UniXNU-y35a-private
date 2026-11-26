#!/usr/bin/env python3
"""Decode one sealed Y35A terminal fault without device access or file writes.

JSON goes to stdout. Exit 0 means a fresh, bound, mapped terminal fault was
decoded, not that the kernel booted successfully. Missing, unchanged, partial,
unbound, or unmapped evidence returns 1. A baseline from the same probe is
needed to establish freshness; its preceding boot shim tag may be older.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess

from boot_layout import parse_macho
from verify_phase_instrumentation import (
    PHASE_MARKERS,
    find_tool,
    verify_capture_kernel_binding,
    verify_probe_image_binding,
    verify_transport_record_layout,
)

MAGICS = (b"Y35ALV01", b"Y35ALV02", b"Y35ALV03", b"Y35ALV04", b"Y35ALV05", b"Y35ALV06", b"Y35ALV07")
EC_NAMES = {
    0x00: "Uncategorized exception",
    0x07: "FP/SIMD access trap",
    0x18: "System register trap",
    0x20: "Instruction abort from lower EL",
    0x21: "Instruction abort at current EL",
    0x22: "PC alignment fault",
    0x24: "Data abort from lower EL",
    0x25: "Data abort at current EL",
    0x26: "SP alignment fault",
    0x2F: "SError",
}
ABORT_ECS = (0x20, 0x21, 0x24, 0x25)
# Conservative ARMv8-A abort FSC subset. Reserved or newer encodings stay unknown.
FAR_ABORT_FSCS = (set(range(8)) | {9, 10, 11, 13, 14, 15, 0x10, 0x18, 0x30}
                  | set(range(0x14, 0x18)) | set(range(0x1C, 0x20)))
LIMITATIONS = [
    "Only magic, ELR_EL1, ESR_EL1 and FAR_EL1 are stored; no full register snapshot.",
    "Artifact hashes and raw 64-bit tags correlate local inputs; they are not cryptographic authentication of a device run.",
    "Identical retained records cannot distinguish a repeated identical fault from stale data.",
    "Missing terminal evidence is not successful boot, absence of exceptions, or iOS completion.",
    "Probe-time CPU registers are not the fault-time register state.",
    "Nearest symbol is bounded to the same code section, not a proof of function extent.",
]


def number(value):
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise ValueError("expected integer or integer string")
    return int(value, 0) if isinstance(value, str) else value


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_json(path):
    data = json.loads(Path(path).read_text())
    if not isinstance(data, dict):
        raise ValueError("JSON manifest must be an object")
    return data


def carrier_layout(manifest):
    mode = manifest.get("transport_mode")
    if mode not in ("minimal-boundary", "full-readback"):
        raise ValueError("unsupported transport_mode")
    records = manifest.get("records")
    if not isinstance(records, list) or not all(isinstance(r, dict) for r in records):
        raise ValueError("readback manifest requires a records array")
    matches = [r for r in records if r.get("name") == "early-fault-record"]
    if len(matches) != 1:
        raise ValueError("exactly one early-fault-record is required")
    failures = verify_transport_record_layout(manifest)
    if failures:
        raise ValueError("; ".join(failures))
    record = matches[0]
    size = number(record["size"])
    if size < 32:
        raise ValueError("early-fault-record must cover all four 64-bit fields")
    if mode == "minimal-boundary":
        offset = 0x10000 + number(record["report_offset"])
        for alias in ("offset", "stage_offset"):
            if alias in record and number(record[alias]) != offset:
                raise ValueError(f"early-fault-record {alias} disagrees with report_offset")
    else:
        offset = number(record["offset"])
    if offset < 0 or offset % 8:
        raise ValueError("early-fault-record raw offset must be nonnegative and aligned")
    return offset, size


def code_sections_and_symbols(image):
    """Add bounded section/symbol metadata to boot_layout's segment validation."""
    count, command_bytes = struct.unpack_from("<II", image, 16)
    offset, sections, symtab = 32, [], None
    for _ in range(count):
        cmd, length = struct.unpack_from("<II", image, offset)
        if cmd == 25:
            va, extent, fileoff, filesize = struct.unpack_from("<QQQQ", image, offset + 24)
            protection, nsects = struct.unpack_from("<II", image, offset + 60)
            if 72 + nsects * 80 > length:
                raise ValueError("Mach-O section table is truncated")
            for i in range(nsects):
                pos = offset + 72 + i * 80
                name = image[pos:pos + 16].split(b"\0")[0].decode("ascii", "replace")
                address, size, sec_offset = struct.unpack_from("<QQI", image, pos + 32)
                flags = struct.unpack_from("<I", image, pos + 64)[0]
                if size and not (va <= address <= address + size <= va + extent):
                    raise ValueError("Mach-O section is outside its segment")
                is_code = bool(protection & 4 and flags & 0x80000400)
                if is_code and size:
                    if not (fileoff <= sec_offset <= sec_offset + size <= fileoff + filesize):
                        raise ValueError("Mach-O code section is not file-backed")
                    if sec_offset - fileoff != address - va:
                        raise ValueError("Mach-O code section disagrees with segment mapping")
                sections.append({"address": address, "size": size, "name": name,
                                 "code": is_code})
        elif cmd == 2:
            if length < 24 or symtab is not None:
                raise ValueError("invalid or duplicate Mach-O symbol table")
            symtab = struct.unpack_from("<IIII", image, offset + 8)
        offset += length
    if offset != 32 + command_bytes:
        raise ValueError("inconsistent Mach-O load commands")
    symbols = []
    if symtab is not None:
        symoff, count, stroff, strsize = symtab
        if symoff + 16 * count > len(image) or stroff + strsize > len(image):
            raise ValueError("Mach-O symbol/string table is truncated")
        for i in range(count):
            name, kind, section, _, address = struct.unpack_from("<IBBHQ", image, symoff + 16 * i)
            if kind & 0xE0 or kind & 0x0E != 0x0E:
                continue  # STAB, undefined and absolute symbols cannot bound code.
            if not 1 <= section <= len(sections) or name >= strsize:
                raise ValueError("Mach-O defined symbol has invalid section/string index")
            end = image.find(b"\0", stroff + name, stroff + strsize)
            if end == -1:
                raise ValueError("Mach-O symbol name is not terminated")
            sec = sections[section - 1]
            if sec["code"] and sec["address"] <= address < sec["address"] + sec["size"]:
                symbols.append((address, section - 1,
                                image[stroff + name:end].decode("utf-8", "replace")))
    return sections, symbols


def mapping_bases(manifest, boot, layout, kernel_sha):
    values = []
    for source, data in (("readback", manifest), ("boot", boot)):
        if data is None:
            continue
        if source == "boot":
            expected = data.get("kernel_sha256")
            if not isinstance(expected, str) or expected.lower() != kernel_sha:
                raise ValueError("boot manifest kernel_sha256 does not match supplied kernel")
        virtual = data.get("kernel_virtual_base")
        physical = data.get("kernel_physical_base")
        if virtual is None and physical is None:
            continue
        if virtual is None or physical is None:
            raise ValueError(f"{source} manifest must provide both mapping bases")
        virtual, physical = number(virtual), number(physical)
        if virtual != layout["base"]:
            raise ValueError(f"{source} kernel_virtual_base disagrees with Mach-O")
        if not 0 < physical < 1 << 63 or physical + layout["end"] - virtual > 1 << 64:
            raise ValueError(f"{source} kernel_physical_base is invalid")
        if physical % 4096:
            raise ValueError(f"{source} kernel_physical_base is not page aligned")
        values.append((virtual, physical))
    if values and any(v != values[0] for v in values[1:]):
        raise ValueError("boot and readback manifest mapping bases disagree")
    return values[0] if values else None


def instruction_at(elr, image, layout, sections, symbols, bases):
    result = {
        "status": "unmapped", "elr": hex(elr), "pc": None, "address_mode": None,
        "file_offset": None, "instruction_word": None, "instruction_bytes": None,
        "nearest_symbol": None, "symbol_address": None, "symbol_offset": None,
        "disassembly": None,
    }
    if elr % 4:
        result["reason"] = "ELR is not aligned to an AArch64 instruction"
        return result
    if elr >= 1 << 63:
        pc, mode = elr, "virtual"
    elif bases is not None:
        virtual, physical = bases
        if not 0 <= elr - physical < layout["end"] - virtual:
            result["reason"] = "low ELR is outside the explicitly described kernel physical window"
            return result
        pc, mode = virtual + elr - physical, "physical-to-virtual"
    else:
        result["reason"] = "low ELR has no explicit virtual/physical mapping bases"
        return result
    segments = [s for s in layout["segments"]
                if s["protection"] & 4 and s["address"] <= pc
                and pc + 4 <= s["address"] + s["file_size"]]
    code = [(i, s) for i, s in enumerate(sections) if s["code"]
            and s["address"] <= pc and pc + 4 <= s["address"] + s["size"]]
    if len(segments) != 1 or len(code) != 1:
        result["reason"] = "ELR does not identify one file-backed executable code section"
        return result
    seg, (section, _) = segments[0], code[0]
    offset = seg["offset"] + pc - seg["address"]
    encoded = image[offset:offset + 4]
    result.update(status="mapped", pc=hex(pc), address_mode=mode, file_offset=hex(offset),
                  instruction_word=hex(int.from_bytes(encoded, "little")),
                  instruction_bytes=encoded.hex(), section=code[0][1]["name"])
    preceding = [(address, name) for address, sec, name in symbols
                 if sec == section and address <= pc]
    if preceding:
        address = max(a for a, _ in preceding)
        aliases = sorted(name for a, name in preceding if a == address)
        result.update(nearest_symbol=aliases[0], symbol_aliases=aliases,
                      symbol_address=hex(address), symbol_offset=hex(pc - address))
    return result


def syndrome(elr, esr, far):
    ec = (esr >> 26) & 0x3F
    iss, fsc = esr & 0x1FFFFFF, esr & 0x3F
    valid, reason, fnv = False, "FAR is not an address for this exception class", None
    if ec in ABORT_ECS:
        fnv = (iss >> 10) & 1
        if fnv:
            reason = "abort syndrome has FnV set"
        elif fsc in FAR_ABORT_FSCS or (ec in (0x24, 0x25) and fsc == 0x21):
            valid, reason = True, "supported abort syndrome with FnV clear"
        else:
            reason = "abort fault status is not supported; FAR validity is unknown"
    return {
        "elr": hex(elr),
        "esr": {"value": hex(esr), "ec": ec, "ec_name": EC_NAMES.get(ec, "Unknown exception class"),
                "il": (esr >> 25) & 1, "iss": hex(iss)},
        "far": {"raw_value": hex(far), "valid": valid, "address": hex(far) if valid else None,
                "fnv": fnv, "reason": reason},
    }


def phase_markers(current, previous, offset, size):
    """Decode only slots 5..10 as independent checkpoints, never as faults."""
    result = {}
    for name, (slot, expected) in PHASE_MARKERS.items():
        end = slot * 8 + 8
        if end > size or offset + end > len(current):
            continue
        value = struct.unpack_from("<Q", current, offset + slot * 8)[0]
        old = (struct.unpack_from("<Q", previous, offset + slot * 8)[0]
               if previous is not None and offset + end <= len(previous) else None)
        present = value == expected
        freshness = ("absent" if not present else "unknown" if old is None
                     else "unchanged" if old == expected else "fresh")
        result[name] = {
            "slot": slot, "value": hex(value), "present": present,
            "freshness": freshness,
            "meaning": ("panic initialization checkpoint, not a panic event" if name == "PANICINI"
                        else "initialization checkpoint, not proof of iOS completion"),
        }
    return result


def add_disassembly(kernel, instruction):
    """Optional presentation only; raw mapped bytes remain the authority."""
    try:
        tool = find_tool("llvm-objdump")
        pc = int(instruction["pc"], 16)
        output = subprocess.run(
            [tool, "-d", f"--start-address={pc:#x}", f"--stop-address={pc + 4:#x}", str(kernel)],
            capture_output=True, text=True, check=True, timeout=15,
        ).stdout
        for line in output.splitlines():
            match = re.match(r"\s*([0-9a-fA-F]+):\s*((?:[0-9a-fA-F]{2}\s+){4})(.*)", line)
            if match and int(match[1], 16) == pc:
                if bytes.fromhex(match[2]).hex() != instruction["instruction_bytes"]:
                    raise ValueError("disassembler bytes disagree with the mapped kernel")
                instruction["disassembly"] = match[3].strip()
                return
        instruction["disassembly_note"] = "tool did not return matching instruction bytes"
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as exc:
        instruction["disassembly_note"] = str(exc)


def decode_terminal_fault(*, kernel: Path, manifest: Path, probe: Path, raw: Path,
                          baseline: Path | None = None, boot_manifest: Path | None = None,
                          disassemble: bool = True) -> dict:
    report = {
        "schema": 1, "status": "invalid", "freshness": "unknown", "verified_fault": False,
        "record": None, "fault": None, "instruction": None, "phase_markers": {},
        "errors": [], "notes": [],
        "limitations": list(LIMITATIONS),
    }
    try:
        kernel, manifest, probe, raw = map(Path, (kernel, manifest, probe, raw))
        data = read_json(manifest)
        image, raw_bytes = kernel.read_bytes(), raw.read_bytes()
        kernel_sha = digest(image)
        report["artifacts"] = {
            "kernel_sha256": kernel_sha, "probe_sha256": digest(probe.read_bytes()),
            "raw_sha256": digest(raw_bytes),
            "baseline_sha256": digest(Path(baseline).read_bytes()) if baseline is not None else None,
        }
        expected = data.get("kernel_sha256")
        if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", expected):
            raise ValueError("manifest kernel_sha256 must contain 64 hexadecimal characters")
        if expected.lower() != kernel_sha:
            raise ValueError("manifest kernel_sha256 does not match supplied kernel")
        errors = verify_probe_image_binding(probe, manifest, required=True)
        errors += verify_capture_kernel_binding(raw, manifest)
        if baseline is not None:
            errors += ["baseline: " + e for e in
                       verify_capture_kernel_binding(Path(baseline), manifest)]
        if data.get("transport_mode") == "minimal-boundary":
            # This head describes the preceding boot. It may legitimately differ
            # in the baseline, but the final capture must name the requested kernel.
            prefix = bytes.fromhex(kernel_sha[:16])
            if raw_bytes[0x10000:0x10010] != b"Y35AXNU2" + prefix:
                errors.append("final raw shim kernel tag does not match supplied kernel")
        if errors:
            report["errors"].extend(errors)
            return report
        offset, size = carrier_layout(data)
        layout = parse_macho(image)
        sections, symbols = code_sections_and_symbols(image)
        boot = read_json(boot_manifest) if boot_manifest is not None else None
        bases = mapping_bases(data, boot, layout, kernel_sha)
        report["binding"] = {
            "artifacts_match": True, "capture_kernel_tag": kernel_sha[:16],
            "final_shim_tag_checked": data["transport_mode"] == "minimal-boundary",
            "baseline_capture_checked": baseline is not None,
        }
        report["record"] = {"name": "early-fault-record", "raw_offset": hex(offset),
                            "manifest_size": size, "decoded_bytes": 32}
        if offset + size > len(raw_bytes):
            report["status"] = "partial"
            report["errors"].append("raw does not cover the declared early-fault-record")
            return report
        before = Path(baseline).read_bytes() if baseline is not None else None
        report["phase_markers"] = phase_markers(raw_bytes, before, offset, size)
        current = raw_bytes[offset:offset + 40]
        magic, elr, esr, far, link_register = struct.unpack("<8sQQQQ", current)
        committed_bytes = current[:32]
        if magic in (b"Y35ALV04", b"Y35ALV05", b"Y35ALV06", b"Y35ALV07"):
            if size < 40:
                report["status"] = "partial"
                report["errors"].append("Y35ALV04 requires the 40-byte link-register payload")
                return report
            report["record"]["decoded_bytes"] = 40
            report["record"]["link_register_slot"] = 4
            report["record"]["link_register"] = hex(link_register)
        else:
            current = committed_bytes
        report["record"].update(magic=magic.decode("ascii", "replace"), bytes=current.hex())
        if magic == b"\0" * 8:
            report["status"] = "missing" if current == bytes(32) else "partial"
            report["notes"].append("No committed terminal record; later phase markers do not change this classification.")
            return report
        if magic not in MAGICS:
            report["status"] = "unsupported"
            report["errors"].append("unrecognized terminal record magic")
            return report
        if elr == 0 or esr >> 32:
            report["status"] = "partial"
            report["errors"].append("committed marker has an empty ELR or invalid ESR payload")
            return report
        report["fault"] = syndrome(elr, esr, far)
        report["instruction"] = instruction_at(elr, image, layout, sections, symbols, bases)
        if magic in (b"Y35ALV04", b"Y35ALV05", b"Y35ALV06", b"Y35ALV07"):
            call_pc = link_register - 4 if link_register >= 4 else 0
            report["record"]["return_call_pc"] = hex(call_pc)
            call_site = instruction_at(call_pc, image, layout, sections, symbols, bases)
            if call_site.get("status") == "mapped":
                word = number(call_site["instruction_word"])
                call_site["is_bl"] = (word & 0xfc000000) == 0x94000000
            report["instruction"]["return_call_site"] = call_site
        if baseline is None:
            report["status"] = "unverified"
            report["notes"].append("Missing baseline: a retained record cannot establish this run's freshness.")
        else:
            if offset + size > len(before):
                report["status"] = "partial"
                report["errors"].append("baseline does not cover the declared early-fault-record")
                return report
            previous = before[offset:offset + len(committed_bytes)]
            report["record"]["baseline_bytes"] = previous.hex()
            if previous == committed_bytes:
                report.update(status="unchanged", freshness="unchanged")
            elif previous[:8] == magic:
                report.update(status="changed", freshness="ambiguous")
                report["notes"].append("Payload changed under the same retained commit magic; complete new publication is unproven.")
            else:
                report.update(status="fresh", freshness="fresh")
        if report["instruction"]["status"] == "mapped" and disassemble:
            add_disassembly(kernel, report["instruction"])
        report["verified_fault"] = (report["status"] == "fresh"
                                    and report["instruction"]["status"] == "mapped")
        return report
    except (OSError, ValueError, KeyError, TypeError, struct.error) as exc:
        report.update(status="invalid", verified_fault=False, fault=None, instruction=None)
        report["errors"].append(str(exc))
        return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kernel", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path, help="probe readback.json")
    parser.add_argument("--probe", required=True, type=Path)
    parser.add_argument("--raw", required=True, type=Path, help="final staged capture")
    parser.add_argument("--baseline", type=Path, help="baseline from the same probe manifest")
    parser.add_argument("--boot-manifest", type=Path, help="optional explicit kernel mapping bases")
    parser.add_argument("--no-disassembly", action="store_true", help="report exact instruction bytes without llvm-objdump")
    args = parser.parse_args(argv)
    result = decode_terminal_fault(
        kernel=args.kernel, manifest=args.manifest, probe=args.probe, raw=args.raw,
        baseline=args.baseline, boot_manifest=args.boot_manifest,
        disassemble=not args.no_disassembly,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["verified_fault"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
