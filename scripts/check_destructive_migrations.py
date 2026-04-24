#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import re
import sys


MIGRATIONS_DIR = Path("backend/migrations/versions")
DISALLOWED_PATTERNS = [
    re.compile(r"\bop\.drop_table\s*\("),
    re.compile(r"\bop\.drop_column\s*\("),
    re.compile(r"\bop\.rename_table\s*\("),
    re.compile(r"\bop\.alter_column\s*\([^)]*new_column_name="),
    re.compile(r"\bDROP\s+COLUMN\b", re.IGNORECASE),
    re.compile(r"\bDROP\s+TABLE\b", re.IGNORECASE),
]


def main() -> int:
    if not MIGRATIONS_DIR.exists():
        print(f"{MIGRATIONS_DIR} not found", file=sys.stderr)
        return 1

    violations: list[tuple[Path, int, str]] = []
    for path in sorted(MIGRATIONS_DIR.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        upgrade_match = re.search(r"def\s+upgrade\s*\(\s*\)\s*:\s*(.*?)(?:\n\s*def\s+downgrade\s*\(|\Z)", text, re.DOTALL)
        if upgrade_match is None:
            continue
        upgrade_text = upgrade_match.group(1)
        for pattern in DISALLOWED_PATTERNS:
            for match in pattern.finditer(upgrade_text):
                line = text.count("\n", 0, upgrade_match.start(1) + match.start()) + 1
                violations.append((path, line, pattern.pattern))

    if violations:
        print("Destructive migration pattern(s) detected:")
        for path, line, pattern in violations:
            print(f"- {path}:{line} matched {pattern}")
        print("Use the two-step migration policy (add/backfill/switch/drop later).")
        return 2

    print("No destructive migration patterns found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
