#!/usr/bin/env python3
import re
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: extract_unified_diff.py <input_txt> <output_diff>", file=sys.stderr)
        return 2

    inp = Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace")
    outp = Path(sys.argv[2])

    if re.search(r"^\s*NO_DIFF\s*$", inp, re.MULTILINE):
        print("NO_DIFF returned by model.", file=sys.stderr)
        return 10

    match = re.search(r"(^diff --git .*?$)", inp, re.MULTILINE)
    if not match:
        print("No unified diff found (missing 'diff --git').", file=sys.stderr)
        preview = "\n".join(inp.splitlines()[:60])
        print("=== MODEL_OUTPUT_PREVIEW_START ===", file=sys.stderr)
        print(preview, file=sys.stderr)
        print("=== MODEL_OUTPUT_PREVIEW_END ===", file=sys.stderr)
        return 11

    diff_txt = inp[match.start():].lstrip("\n")
    outp.write_text(diff_txt, encoding="utf-8")
    print(f"Wrote extracted unified diff: {outp}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
