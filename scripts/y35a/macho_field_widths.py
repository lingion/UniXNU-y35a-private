#!/usr/bin/env python3
"""Read the small subset of DWARF needed for XNU field provenance.

The parser intentionally consumes compiler-produced ``dwarfdump`` text and
returns structured facts. It refuses missing tools or files instead of
turning an unavailable DWARF lookup into a zero width.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path


class DwarfToolMissing(RuntimeError):
    """The requested object or the host DWARF reader is unavailable."""


_DIE_START = re.compile(r"^0x([0-9a-fA-F]+):\s+(DW_TAG_\S+|NULL)\s*$", re.MULTILINE)
_NAME = re.compile(r'DW_AT_name\s+\("([^"]+)"\)')
_TYPE = re.compile(r'DW_AT_type\s+\((0x[0-9a-fA-F]+)(?:\s+"([^"]+)")?\)')
_BYTE_SIZE = re.compile(r'DW_AT_byte_size\s+\((0x[0-9a-fA-F]+)\)')
_COUNT = re.compile(r'DW_AT_count\s+\((0x[0-9a-fA-F]+)\)')


def _dwarfdump(path: str | Path) -> str:
    object_path = Path(path)
    if not object_path.exists():
        raise DwarfToolMissing(f'DWARF object does not exist: {object_path}')
    tool = shutil.which('dwarfdump') or shutil.which('llvm-dwarfdump')
    if not tool:
        raise DwarfToolMissing('dwarfdump is not installed')
    try:
        return subprocess.check_output(
            [tool, '--debug-info', str(object_path)],
            text=True,
            stderr=subprocess.STDOUT,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise DwarfToolMissing(f'cannot read DWARF from {object_path}: {exc}') from exc


def _dies(dump: str) -> dict[int, str]:
    starts = list(_DIE_START.finditer(dump))
    result: dict[int, str] = {}
    for index, match in enumerate(starts):
        end = starts[index + 1].start() if index + 1 < len(starts) else len(dump)
        result[int(match.group(1), 16)] = dump[match.start():end]
    return result


def _type_ref(die: str) -> tuple[int, str | None] | None:
    match = _TYPE.search(die)
    if not match:
        return None
    return int(match.group(1), 16), match.group(2)


def _variable_dies(dies: dict[int, str]) -> dict[str, tuple[int, str]]:
    result: dict[str, tuple[int, str]] = {}
    for offset, die in dies.items():
        if 'DW_TAG_variable' not in die.splitlines()[0]:
            continue
        name = _NAME.search(die)
        type_ref = _type_ref(die)
        if name and type_ref:
            result[name.group(1)] = (offset, die)
    return result


def _resolve_type(dies: dict[int, str], offset: int, depth: int = 0):
    if depth > 8 or offset not in dies:
        return None
    die = dies[offset]
    first = die.splitlines()[0]
    if 'DW_TAG_base_type' in first:
        size = _BYTE_SIZE.search(die)
        return int(size.group(1), 16) if size else None
    if 'DW_TAG_pointer_type' in first:
        return 8
    if 'DW_TAG_typedef' in first:
        ref = _type_ref(die)
        return _resolve_type(dies, ref[0], depth + 1) if ref else None
    if 'DW_TAG_array_type' in first:
        ref = _type_ref(die)
        element = _resolve_type(dies, ref[0], depth + 1) if ref else None
        count = _COUNT.search(die)
        if not count:
            # dwarfdump prints the array's subrange DIE immediately after the
            # array DIE, so the child is a separate block in our offset map.
            for child_offset in sorted(candidate for candidate in dies if candidate > offset):
                child = dies[child_offset]
                if 'DW_TAG_subrange_type' in child.splitlines()[0]:
                    count = _COUNT.search(child)
                    if count:
                        break
        return {
            'scalar': None,
            'kind': 'array',
            'element': element,
            'count': int(count.group(1), 16) if count else None,
        }
    if any(tag in first for tag in ('DW_TAG_structure_type', 'DW_TAG_class_type',
                                    'DW_TAG_union_type', 'DW_TAG_enumeration_type')):
        size = _BYTE_SIZE.search(die)
        return {
            'scalar': None,
            'kind': 'aggregate',
            'byte_size': int(size.group(1), 16) if size else None,
        }
    return None


def dwarf_field_widths(path: str | Path) -> dict[str, int | dict]:
    """Return compiler-derived widths keyed by external variable name."""
    dies = _dies(_dwarfdump(path))
    variables = _variable_dies(dies)
    result: dict[str, int | dict] = {}
    for name, (_, die) in variables.items():
        ref = _type_ref(die)
        if ref:
            result[name] = _resolve_type(dies, ref[0])
    return result


def dwarf_type_kinds(path: str | Path, names: list[str]) -> dict[str, bool]:
    """Identify variables whose declared type is the ``boolean_t`` typedef."""
    dies = _dies(_dwarfdump(path))
    variables = _variable_dies(dies)
    result: dict[str, bool] = {}
    for name in names:
        entry = variables.get(name)
        if not entry:
            continue
        ref = _type_ref(entry[1])
        result[name] = bool(ref and ref[1] == 'boolean_t')
    return result

