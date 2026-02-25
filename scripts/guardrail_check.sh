#!/usr/bin/env bash
set -euo pipefail

# This script enforces HONGSTR guardrails for PR hygiene.
# It is intentionally dependency-free.

MAX_BYTES="${MAX_BYTES:-5242880}"  # 5MB

# Get staged files if any; otherwise use changed files in working tree.
files="$(git diff --name-only --cached || true)"
if [[ -z "${files}" ]]; then
  files="$(git diff --name-only || true)"
fi

# If still empty, nothing to check.
if [[ -z "${files}" ]]; then
  echo "guardrail_check: no changes detected."
  exit 0
fi

fail() { echo "GUARDRAIL_FAIL: $*" >&2; exit 1; }

# 1) Core engine must not change
if echo "${files}" | grep -E '^src/hongstr/' >/dev/null 2>&1; then
  fail "core engine change detected under src/hongstr/. This is forbidden."
fi

# 2) No parquet/pkl artifacts tracked
if echo "${files}" | grep -E '\.(parquet|pkl|pickle|joblib|onnx|pt|ckpt|npz)$' >/dev/null 2>&1; then
  fail "artifact file detected (*.parquet/*.pkl/...). Do not commit artifacts."
fi

# 3) No big files
while IFS= read -r f; do
  [[ -z "$f" ]] && continue
  if [[ -f "$f" ]]; then
    sz="$(wc -c < "$f" | tr -d ' ')"
    if [[ "$sz" -gt "$MAX_BYTES" ]]; then
      fail "file too large (> ${MAX_BYTES} bytes): $f (${sz} bytes)"
    fi
  fi
done <<< "${files}"

echo "guardrail_check: PASS"
