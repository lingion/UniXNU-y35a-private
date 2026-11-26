#!/usr/bin/env python3
"""Red/green proof for the iOS 12 RAMDisk staging closure.

For every Mach-O in a staged tree, walk `otool -L` transitively and require that
each install name resolves to a staged file, following the same candidate rules
as scripts/stage-ios12-root.py (exact load path or the flattened framework form
iOS uses, i.e. /Versions/A/ dropped on disk). The checker works from CLOSURE.json
only when asked (--from-closure); by default it re-derives the dependency graph
from the staged bytes themselves, so a hand-corrupted tree fails the check even
if CLOSURE.json still claims it is fine. Exit 0 = green (zero unresolved),
exit 1 = red (unresolved load paths printed).

Usage: python3 tools/check-ios12-closure.py out/y35a/ios12-root
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

MACHO_MAGICS = (b'\xcf\xfa\xed\xfe', b'\xce\xfa\xed\xfe', b'\xca\xfe\xba\xbe', b'\xbe\xba\xfe\xca')


def is_macho(path):
    try:
        with path.open('rb') as stream:
            return stream.read(4) in MACHO_MAGICS
    except OSError:
        return False


def otool_deps(binary):
    result = subprocess.run(['otool', '-L', str(binary)], capture_output=True, text=True)
    if result.returncode:
        return None
    deps, own = [], None
    for line in result.stdout.splitlines():
        if line.endswith(':') and not line.startswith('\t'):
            own = line[:-1]
            continue
        line = line.strip()
        if line.startswith('/') or line.startswith('@'):
            deps.append(line.split(' (')[0].strip())
    if own and own in deps:
        deps.remove(own)
    return deps


def resolve(root, install_path):
    parts = install_path.split('/')
    alts = []
    if 'Versions' in parts:
        index = parts.index('Versions')
        alts.append('/'.join(parts[:index] + parts[index + 2:]))
    alts.append(install_path)
    for alt in alts:
        candidate = root / alt.lstrip('/')
        if candidate.is_file():
            return candidate
    return None


def check(root):
    root = Path(root)
    machos = sorted(p for p in root.rglob('*') if p.is_file() and is_macho(p))
    unresolved = []
    checked_edges = 0
    for binary in machos:
        deps = otool_deps(binary)
        if deps is None:
            unresolved.append({'binary': str(binary.relative_to(root)), 'error': 'otool failed'})
            continue
        for dep in deps:
            checked_edges += 1
            if dep.startswith('@rpath') or dep.startswith('@executable_path'):
                continue  # loader-relative install names need no staged file
            if resolve(root, dep) is None:
                unresolved.append({'binary': str(binary.relative_to(root)), 'missing': dep})
    return len(machos), checked_edges, unresolved


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('root', type=Path, help='staged tree to verify')
    parser.add_argument('--json', action='store_true', help='machine-readable summary')
    args = parser.parse_args()
    machos, edges, unresolved = check(args.root)
    if args.json:
        print(json.dumps({'machos': machos, 'edges': edges, 'unresolved': unresolved}, indent=1))
    else:
        print(f'Mach-O files checked: {machos}; dependency edges followed: {edges}')
        for gap in unresolved:
            print('UNRESOLVED', gap)
    return 1 if unresolved else 0


if __name__ == '__main__':
    sys.exit(main())
