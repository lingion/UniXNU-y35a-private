#!/usr/bin/env python3
"""Apply the macOS runner compatibility fix to one exact XNU source copy."""
from __future__ import annotations

import argparse
from pathlib import Path
import hashlib

ORIGINAL_SHA256 = "c542aad946168755dff8739056716ade61b7b1f3632b95700d056ce22e333def"
PY3_SOURCE = '''#!/usr/bin/env python3
import re
import sys

if len(sys.argv) < 2:
    raise SystemExit(1)
code_table = []
pattern = re.compile(r"0x([0-9a-fA-F]+)\\s+([^\\s]*)")
with open(sys.argv[1], "rt") as codes:
    for line in codes:
        match = pattern.match(line)
        if match:
            code_table.append((int(match.group(1), 16), match.group(2)))
print("typedef struct {")
print("        uint32_t   id;")
print("        const char *name;")
print("} kd_event_t;")
print("kd_event_t kd_events[] = {")
for mapping in sorted(code_table, key=lambda value: value[0]):
    print('        {0x%x, "%s"},' % mapping)
print("};")
'''


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--xnu-source", type=Path, required=True)
    args = parser.parse_args()
    path = args.xnu_source.resolve(strict=True) / "bsd/kern/makekdebugevents.py"
    data = path.read_text()
    actual = hashlib.sha256(data.encode()).hexdigest()
    if actual == hashlib.sha256(PY3_SOURCE.encode()).hexdigest():
        return 0
    if actual != ORIGINAL_SHA256:
        raise SystemExit(f"unexpected makekdebugevents.py SHA: {actual}")
    path.write_text(PY3_SOURCE)
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
