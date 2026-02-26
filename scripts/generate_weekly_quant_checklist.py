#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from research.loop.weekly_governance import generate_weekly_quant_checklist


if __name__ == "__main__":
    out = generate_weekly_quant_checklist(REPO_ROOT)
    print(json.dumps(out, indent=2, ensure_ascii=False))
