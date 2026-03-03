#!/usr/bin/env python3
"""
Fetch Bitfinex public market structure snapshots for cross-exchange research.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from state_atomic.okx_bitfinex_public_manifest import (
    build_coverage_row,
    utc_now_iso,
    write_atomic_json,
    write_bitfinex_atomic_coverage,
    write_bitfinex_manifest,
)


UTC = timezone.utc
DEFAULT_BASE_URL = "https://api-pub.bitfinex.com"


class PublicFetchError(Exception):
    pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch Bitfinex public market snapshots.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--timeout-s", type=float, default=15.0)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--repo-root", default=".")
    return parser.parse_args()


def _file_stamp(now_dt: datetime) -> str:
    return now_dt.astimezone(UTC).strftime("%Y%m%d_%H%M%S")


def _fetch_json(*, base_url: str, path: str, retries: int, timeout_s: float) -> Any:
    base = base_url.rstrip("/")
    url = f"{base}{path}"
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
    payload: Any,
) -> str:
    stamp = _file_stamp(datetime.fromisoformat(fetched_at_utc.replace("Z", "+00:00")))
    path = repo_root / "data/derived/bitfinex/public" / dataset / key / f"{stamp}.json"
    envelope = {
        "fetched_at_utc": fetched_at_utc,
        "provider": "bitfinex",
        "request": {
            "path": request_path,
        },
        "payload": payload,
    }
    write_atomic_json(path, envelope)
    return str(path.relative_to(repo_root)).replace("\\", "/")


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    coverage_rows: list[dict[str, Any]] = []
    datasets = (
        ("liquidations_latest", "latest", "/v2/liquidations/hist"),
        ("deriv_status_hist", "ALL", "/v2/status/deriv/ALL/hist"),
    )

    for dataset, key, request_path in datasets:
        fetched_at_utc = utc_now_iso()
        try:
            payload = _fetch_json(
                base_url=args.base_url,
                path=request_path,
                retries=args.retries,
                timeout_s=args.timeout_s,
            )
            source_path = _write_dataset_payload(
                repo_root=repo_root,
                dataset=dataset,
                key=key,
                fetched_at_utc=fetched_at_utc,
                request_path=request_path,
                payload=payload,
            )
            coverage_rows.append(
                build_coverage_row(
                    dataset=dataset,
                    key=key,
                    payload=payload,
                    latest_utc=fetched_at_utc,
                    source_path=source_path,
                    request_path=request_path,
                )
            )
        except PublicFetchError as exc:
            coverage_rows.append(
                build_coverage_row(
                    dataset=dataset,
                    key=key,
                    payload=[],
                    latest_utc=fetched_at_utc,
                    source_path="",
                    request_path=request_path,
                    status_override="FAIL",
                    reason_override=f"fetch_failed:{exc}",
                )
            )

    coverage_path = write_bitfinex_atomic_coverage(repo_root, coverage_rows)
    manifest_path = write_bitfinex_manifest(repo_root)
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
