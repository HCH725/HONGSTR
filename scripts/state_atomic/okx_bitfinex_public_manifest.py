#!/usr/bin/env python3
"""
Helpers for OKX + Bitfinex public data manifests and atomic coverage payloads.
"""
from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


UTC = timezone.utc
ATOMIC_STATE_DIR = Path("reports/state_atomic")
MANIFEST_DIR = ATOMIC_STATE_DIR / "manifests"
OKX_MANIFEST_PATH = MANIFEST_DIR / "okx_public_v1.json"
BITFINEX_MANIFEST_PATH = MANIFEST_DIR / "bitfinex_public_v1.json"
OKX_ATOMIC_COVERAGE_PATH = ATOMIC_STATE_DIR / "okx_public_coverage.json"
BITFINEX_ATOMIC_COVERAGE_PATH = ATOMIC_STATE_DIR / "bitfinex_public_coverage.json"


def utc_now_iso() -> str:
    return (
        datetime.now(tz=UTC)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def write_atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    tmp_path.replace(path)


def git_code_ref(repo_root: Path) -> str:
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(repo_root),
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception:
        return "unknown"
    code_ref = proc.stdout.strip()
    return code_ref or "unknown"


def summarize_payload_rows(payload: Any) -> tuple[int, str, str]:
    if isinstance(payload, list):
        if not payload:
            return 0, "WARN", "empty array from endpoint"
        return len(payload), "OK", ""

    if isinstance(payload, dict):
        data = payload.get("data")
        if isinstance(data, list):
            if not data:
                return 0, "WARN", "empty array from endpoint"
            return len(data), "OK", ""
        if payload:
            return 1, "OK", "object response without array payload"
        return 0, "WARN", "empty object from endpoint"

    return 0, "FAIL", "non-json payload shape"


def build_coverage_row(
    *,
    dataset: str,
    key: str,
    payload: Any,
    latest_utc: str,
    source_path: str,
    request_path: str,
    status_override: str | None = None,
    reason_override: str | None = None,
) -> dict[str, Any]:
    rows, derived_status, derived_reason = summarize_payload_rows(payload)
    status = str(status_override or derived_status or "UNKNOWN").upper().strip()
    if status not in {"OK", "WARN", "FAIL"}:
        status = "UNKNOWN"
    reason = str(reason_override if reason_override is not None else derived_reason).strip()
    return {
        "dataset": dataset,
        "key": key,
        "rows": rows,
        "latest_utc": latest_utc,
        "status": status,
        "reason": reason,
        "request_path": request_path,
        "source_path": source_path,
    }


def build_coverage_payload(rows: list[dict[str, Any]]) -> dict[str, Any]:
    ordered = sorted(rows, key=lambda row: (str(row.get("dataset", "")), str(row.get("key", ""))))
    return {
        "schema": "public_market_coverage.v1",
        "ts_utc": utc_now_iso(),
        "rows": ordered,
    }


def write_okx_atomic_coverage(repo_root: Path, rows: list[dict[str, Any]]) -> Path:
    path = repo_root / OKX_ATOMIC_COVERAGE_PATH
    write_atomic_json(path, build_coverage_payload(rows))
    return path


def write_bitfinex_atomic_coverage(repo_root: Path, rows: list[dict[str, Any]]) -> Path:
    path = repo_root / BITFINEX_ATOMIC_COVERAGE_PATH
    write_atomic_json(path, build_coverage_payload(rows))
    return path


def build_okx_manifest(repo_root: Path, symbols: list[str]) -> dict[str, Any]:
    return {
        "dataset_id": "okx_public_v1",
        "schema_version": "v1",
        "producer": "scripts/okx_public_fetch.py",
        "cadence": "manual_rolling",
        "path_patterns": {
            "root": "data/derived/okx/public",
            "template": "data/derived/okx/public/{dataset}/{key}/{ts_utc}.json",
        },
        "symbols": sorted(dict.fromkeys(symbols)),
        "metrics": ["long_short_ratio", "open_interest"],
        "periods": ["snapshot"],
        "sources": [
            {
                "name": "okx_public",
                "endpoints": [
                    "/api/v5/public/open-interest",
                    "/api/v5/rubik/stat/contracts/long-short-account-ratio",
                ],
            }
        ],
        "provenance": {
            "generated_utc": utc_now_iso(),
            "code_ref": git_code_ref(repo_root),
        },
        "notes": (
            "OKX public derivatives snapshots for cross-exchange divergence research. "
            "Public endpoints only; no credential use required for this dataset."
        ),
    }


def build_bitfinex_manifest(repo_root: Path) -> dict[str, Any]:
    return {
        "dataset_id": "bitfinex_public_v1",
        "schema_version": "v1",
        "producer": "scripts/bitfinex_public_fetch.py",
        "cadence": "manual_rolling",
        "path_patterns": {
            "root": "data/derived/bitfinex/public",
            "template": "data/derived/bitfinex/public/{dataset}/{key}/{ts_utc}.json",
        },
        "symbols": ["ALL", "GLOBAL"],
        "metrics": ["deriv_status_hist", "liquidations_latest"],
        "periods": ["snapshot"],
        "sources": [
            {
                "name": "bitfinex_public",
                "endpoints": [
                    "/v2/liquidations/hist",
                    "/v2/status/deriv/ALL/hist",
                ],
            }
        ],
        "provenance": {
            "generated_utc": utc_now_iso(),
            "code_ref": git_code_ref(repo_root),
        },
        "notes": (
            "Bitfinex public market structure snapshots for cross-exchange divergence research. "
            "Empty arrays are valid responses and are tracked via coverage state."
        ),
    }


def write_okx_manifest(repo_root: Path, symbols: list[str]) -> Path:
    path = repo_root / OKX_MANIFEST_PATH
    write_atomic_json(path, build_okx_manifest(repo_root, symbols))
    return path


def write_bitfinex_manifest(repo_root: Path) -> Path:
    path = repo_root / BITFINEX_MANIFEST_PATH
    write_atomic_json(path, build_bitfinex_manifest(repo_root))
    return path


def main() -> int:
    repo_root = Path(".").resolve()
    okx_path = write_okx_manifest(repo_root, ["BTC", "ETH", "BNB"])
    bitfinex_path = write_bitfinex_manifest(repo_root)
    print(f"okx_manifest={okx_path}")
    print(f"bitfinex_manifest={bitfinex_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
