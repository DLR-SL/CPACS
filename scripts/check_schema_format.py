"""Check whether the committed CPACS schema is canonically formatted."""

from __future__ import annotations

import difflib
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schema" / "cpacs_schema.xsd"
CLEANER = ROOT / "scripts" / "syntax_cleanup.py"


def main() -> int:
    if not SCHEMA.is_file():
        print(f"Schema not found: {SCHEMA}", file=sys.stderr)
        return 1

    with tempfile.TemporaryDirectory(prefix="cpacs-schema-check-") as temp_dir:
        formatted_schema = Path(temp_dir) / SCHEMA.name

        subprocess.run(
            [
                sys.executable,
                str(CLEANER),
                str(SCHEMA),
                str(formatted_schema),
                "--log",
                "WARNING",
            ],
            cwd=ROOT,
            check=True,
        )

        original = SCHEMA.read_text(encoding="utf-8")
        formatted = formatted_schema.read_text(encoding="utf-8")

    if original == formatted:
        print("Schema formatting OK. The schema is in canonical form.")
        return 0

    print(
        "Schema formatting differs from the canonical representation.",
        file=sys.stderr,
    )
    print(
        "Run `pixi run format-schema` and commit the result.",
        file=sys.stderr,
    )

    diff = difflib.unified_diff(
        original.splitlines(),
        formatted.splitlines(),
        fromfile="schema/cpacs_schema.xsd",
        tofile="Schema formatting OK. The schema is in canonical form.",
        lineterm="",
        n=3,
    )

    for line_number, line in enumerate(diff):
        if line_number >= 200:
            print("... diff truncated ...", file=sys.stderr)
            break
        print(line, file=sys.stderr)

    return 1


if __name__ == "__main__":
    raise SystemExit(main())