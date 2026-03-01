#!/usr/bin/env python3
from __future__ import annotations

import difflib
import json
import sys
from pathlib import Path


TARGET_PATH = "docs/tg_cp_watchdog.md"
INSERT_LINE = "TG_CP_MAX_AGE_SEC defaults to 7200 and can be tuned."
SECTION_HEADER = "## Deployment notes (macOS launchd)"


def fail(message: str, code: int = 2) -> int:
    print(message, file=sys.stderr)
    return code


def load_text(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8", errors="replace").splitlines()


def find_section_insert_at(lines: list[str]) -> int:
    try:
        header_index = lines.index(SECTION_HEADER)
    except ValueError:
        for index, line in enumerate(lines):
            if "Deployment notes" in line:
                header_index = index
                break
        else:
            return -1

    next_section = len(lines)
    for index in range(header_index + 1, len(lines)):
        if lines[index].startswith("## "):
            next_section = index
            break

    insert_at = next_section
    while insert_at > header_index + 1 and lines[insert_at - 1] == "":
        insert_at -= 1
    return insert_at


def main(argv: list[str]) -> int:
    if len(argv) != 5:
        return fail(
            "usage: build_patch_from_anchor.py <repo_root> <ticket_json> "
            "<anchor_excerpt_txt> <out_patch>"
        )

    repo_root = Path(argv[1]).resolve()
    ticket_path = Path(argv[2])
    anchor_excerpt_path = Path(argv[3])
    output_path = Path(argv[4])

    # Keep the ticket parse so malformed input still fails early.
    json.loads(ticket_path.read_text(encoding="utf-8"))

    target_file = repo_root / TARGET_PATH
    lines = load_text(target_file)

    if INSERT_LINE in lines:
        output_path.write_text("NO_DIFF\n", encoding="utf-8")
        return 0

    anchor_lines = [line for line in load_text(anchor_excerpt_path) if line.strip()]
    if not anchor_lines:
        return fail("NO_ANCHOR: anchor excerpt is empty", 10)
    if not any(line in lines for line in anchor_lines):
        return fail("NO_ANCHOR: excerpt lines do not match target file", 10)

    insert_at = find_section_insert_at(lines)
    if insert_at < 0:
        return fail("NO_SECTION: could not locate Deployment notes section", 11)

    original = target_file.read_text(encoding="utf-8", errors="replace").splitlines(
        keepends=True
    )
    updated = list(original)
    updated.insert(insert_at, INSERT_LINE + "\n")

    diff_text = "".join(
        difflib.unified_diff(
            original,
            updated,
            fromfile=f"a/{TARGET_PATH}",
            tofile=f"b/{TARGET_PATH}",
            lineterm="\n",
        )
    )
    if not diff_text:
        output_path.write_text("NO_DIFF\n", encoding="utf-8")
        return 0

    output_path.write_text(
        f"diff --git a/{TARGET_PATH} b/{TARGET_PATH}\n{diff_text}",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
