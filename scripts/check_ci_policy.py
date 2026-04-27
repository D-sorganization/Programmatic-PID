"""Small CI policy checks that must run on Windows and Unix runners."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

EXPECTED_TOOL_REVS = {
    "Black": r"rev:\s*25\.12\.0",
    "Ruff": r"rev:\s*v0\.14\.10",
    "MyPy": r"rev:\s*v1\.13\.0",
}


def check_tool_versions() -> int:
    config = Path(".pre-commit-config.yaml").read_text(encoding="utf-8")
    missing = [tool for tool, pattern in EXPECTED_TOOL_REVS.items() if re.search(pattern, config) is None]
    if missing:
        for tool in missing:
            print(
                f"::error::{tool} version mismatch between CI and pre-commit config",
                file=sys.stderr,
            )
        return 1
    print("All tool versions consistent")
    return 0


def check_no_placeholders() -> int:
    matches: list[str] = []
    for root in (Path("src"), Path("tests")):
        for path in root.rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            for line_number, line in enumerate(text.splitlines(), start=1):
                if "TODO" in line or "FIXME" in line:
                    matches.append(f"{path}:{line_number}: {line.strip()}")

    if matches:
        for match in matches:
            print(match)
        print(
            "::error::Unresolved TODOs/FIXMEs found. Create GitHub issues instead.",
            file=sys.stderr,
        )
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("check", choices=("tool-versions", "no-placeholders"))
    args = parser.parse_args()

    if args.check == "tool-versions":
        return check_tool_versions()
    return check_no_placeholders()


if __name__ == "__main__":
    raise SystemExit(main())
