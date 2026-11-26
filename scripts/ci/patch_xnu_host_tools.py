#!/usr/bin/env python3
"""Apply the macOS runner compatibility fix to one exact XNU source copy."""
from __future__ import annotations

import argparse
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--xnu-source", type=Path, required=True)
    args = parser.parse_args()
    path = args.xnu_source.resolve(strict=True) / "bsd/kern/makekdebugevents.py"
    data = path.read_text()
    old = "#!/usr/bin/python\n"
    new = "#!/usr/bin/env python3\n"
    if data.startswith(new):
        return 0
    if not data.startswith(old):
        raise SystemExit(f"unexpected makekdebugevents.py shebang: {path}")
    path.write_text(new + data[len(old):])
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
