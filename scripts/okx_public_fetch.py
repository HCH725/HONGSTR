#!/usr/bin/env python3
"""
Fetch OKX public derivatives snapshots for cross-exchange research.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from state_atomic.okx_bitfinex_public_manifest import (
    build_coverage_row,
    utc_now_iso,
    write_atomic_json,
    write_okx_atomic_coverage,
    write_okx_manifest,
)


UTC = timezone.utc
DEFAULT_SYMBOLS = ("BTC", "ETH", "BNB")
DEFAULT_BASE_URL = "https://www.okx.com"
SWAP_INST_IDS = {
    "BTC": "BTC-USDT-SWAP",
    "ETH": "ETH-USDT-SWAP",
    "BNB": "BNB-USDT-SWAP",
}


class PublicFetchError(Exception):
    pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch OKX public market snapshots.")
    parser.add_argument("--symbols", nargs="+", default=list(DEFAULT_SYMBOLS))
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--timeout-s", type=float, default=15.0)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--repo-root", default=".")
    return parser.parse_args()


def _file_stamp(now_dt: datetime) -> str:
    return now_dt.astimezone(UTC).strftime("%Y%m%d_%H%M%S")


def _fetch_json(
    *,
    base_url: str,
    path: str,
    params: dict[str, Any],
    retries: int,
    timeout_s: float,
) -> Any:
    base = base_url.rstrip("/")
    query = urlencode({key: value for key, value in params.items() if value is not None})
    url = f"{base}{path}"
    if query:
        url = f"{url}?{query}"
    cmd = [
        "curl",
        "-fsS",
        "--connect-timeout",
        str(max(1, int(timeout_s))),
        "--max-time",
        str(max(1, int(timeout_s))),
        "--retry",
        str(max(1, retries)),
        "--retry-all-errors",
        "--retry-delay",
        "1",
        url,
    ]
    try:
        proc = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        reason = (exc.stderr or exc.stdout or "").strip() or f"curl_exit_{exc.returncode}"
        raise PublicFetchError(reason) from exc
    except Exception as exc:
        raise PublicFetchError(str(exc)) from exc

    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise PublicFetchError(f"invalid_json:{exc}") from exc


def _write_dataset_payload(
    *,
    repo_root: Path,
    dataset: str,
    key: str,
    fetched_at_utc: str,
    request_path: str,
    request_params: dict[str, Any],
    payload: Any,
) -> str:
    stamp = _file_stamp(datetime.fromisoformat(fetched_at_utc.replace("Z", "+00:00")))
    path = repo_root / "data/derived/okx/public" / dataset / key / f"{stamp}.json"
    envelope = {
        "fetched_at_utc": fetched_at_utc,
        "provider": "okx",
        "request": {
            "path": request_path,
            "params": request_params,
        },
        "payload": payload,
    }
    write_atomic_json(path, envelope)
    return str(path.relative_to(repo_root)).replace("\\", "/")


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    coverage_rows: list[dict[str, Any]] = []

    for raw_symbol in args.symbols:
        symbol = str(raw_symbol).upper().strip()
        inst_id = SWAP_INST_IDS.get(symbol)
        if not inst_id:
            continue

        fetched_at_utc = utc_now_iso()
        open_interest_path = "/api/v5/public/open-interest"
        open_interest_params = {"instType": "SWAP", "instId": inst_id}
        try:
            open_interest_payload = _fetch_json(
                base_url=args.base_url,
                path=open_interest_path,
                params=open_interest_params,
                retries=args.retries,
                timeout_s=args.timeout_s,
            )
            source_path = _write_dataset_payload(
                repo_root=repo_root,
                dataset="open_interest",
                key=inst_id,
                fetched_at_utc=fetched_at_utc,
                request_path=open_interest_path,
                request_params=open_interest_params,
                payload=open_interest_payload,
            )
            coverage_rows.append(
                build_coverage_row(
                    dataset="open_interest",
                    key=inst_id,
                    payload=open_interest_payload,
                    latest_utc=fetched_at_utc,
                    source_path=source_path,
                    request_path=open_interest_path,
                )
            )
        except PublicFetchError as exc:
            coverage_rows.append(
                build_coverage_row(
                    dataset="open_interest",
                    key=inst_id,
                    payload=[],
                    latest_utc=fetched_at_utc,
                    source_path="",
                    request_path=open_interest_path,
                    status_override="FAIL",
                    reason_override=f"fetch_failed:{exc}",
                )
            )

        fetched_at_utc = utc_now_iso()
        ratio_path = "/api/v5/rubik/stat/contracts/long-short-account-ratio"
        ratio_params = {"ccy": symbol}
        try:
            ratio_payload = _fetch_json(
                base_url=args.base_url,
                path=ratio_path,
                params=ratio_params,
                retries=args.retries,
                timeout_s=args.timeout_s,
            )
            source_path = _write_dataset_payload(
                repo_root=repo_root,
                dataset="long_short_ratio",
                key=symbol,
                fetched_at_utc=fetched_at_utc,
                request_path=ratio_path,
                request_params=ratio_params,
                payload=ratio_payload,
            )
            coverage_rows.append(
                build_coverage_row(
                    dataset="long_short_ratio",
                    key=symbol,
                    payload=ratio_payload,
                    latest_utc=fetched_at_utc,
                    source_path=source_path,
                    request_path=ratio_path,
                )
            )
        except PublicFetchError as exc:
            coverage_rows.append(
                build_coverage_row(
                    dataset="long_short_ratio",
                    key=symbol,
                    payload=[],
                    latest_utc=fetched_at_utc,
                    source_path="",
                    request_path=ratio_path,
                    status_override="FAIL",
                    reason_override=f"fetch_failed:{exc}",
                )
            )

    coverage_path = write_okx_atomic_coverage(repo_root, coverage_rows)
    manifest_path = write_okx_manifest(repo_root, [str(symbol).upper().strip() for symbol in args.symbols])
    print(f"coverage_atomic={coverage_path}")
    print(f"manifest_path={manifest_path}")
    for row in coverage_rows:
        print(
            f"{row['dataset']} {row['key']} status={row['status']} rows={row['rows']} "
            f"latest={row['latest_utc']} reason={row['reason']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
