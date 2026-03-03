#!/usr/bin/env python3
"""
Helpers for Binance Futures research-only metric ingestion.

This module keeps all writes inside gitignored data/** and only produces
state snapshots under data/state for SSOT consumers.
"""
from __future__ import annotations

import json
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen


API_BASE = "https://fapi.binance.com"
UTC = timezone.utc
DEFAULT_SYMBOLS = ("BTCUSDT", "ETHUSDT", "BNBUSDT")
ROLLING_METRICS = (
    "funding_rate",
    "open_interest_hist",
    "global_long_short_account_ratio",
    "premium_index",
)
HISTORICAL_METRICS = (
    "funding_rate",
    "open_interest_hist",
    "global_long_short_account_ratio",
)
PROBE_METRICS = ROLLING_METRICS + ("liquidations",)
DEFAULT_TARGET_START = "2020-01-01"
FIVE_MINUTES_MS = 5 * 60 * 1000
ATOMIC_STATE_DIR = Path("reports/state_atomic")
MANIFEST_DIR = ATOMIC_STATE_DIR / "manifests"
DEFAULT_COVERAGE_PATH = Path("data/state/futures_metrics_coverage_latest.json")
DEFAULT_CHECKPOINT_PATH = Path("data/state/_futures_metrics_backfill_checkpoint.json")
FUTURES_METRICS_DATASET_ID = "futures_metrics"


@dataclass(frozen=True)
class MetricSpec:
    metric: str
    endpoint: str
    period: str
    supports_history: bool
    api_limit: int
    api_window_hours: int


METRIC_SPECS = {
    "funding_rate": MetricSpec(
        metric="funding_rate",
        endpoint="/fapi/v1/fundingRate",
        period="5m",
        supports_history=True,
        api_limit=1000,
        api_window_hours=24 * 30,
    ),
    "open_interest_hist": MetricSpec(
        metric="open_interest_hist",
        endpoint="/futures/data/openInterestHist",
        period="5m",
        supports_history=True,
        api_limit=500,
        api_window_hours=24,
    ),
    "global_long_short_account_ratio": MetricSpec(
        metric="global_long_short_account_ratio",
        endpoint="/futures/data/globalLongShortAccountRatio",
        period="5m",
        supports_history=True,
        api_limit=500,
        api_window_hours=24,
    ),
    "premium_index": MetricSpec(
        metric="premium_index",
        endpoint="/fapi/v1/premiumIndex",
        period="5m",
        supports_history=False,
        api_limit=1,
        api_window_hours=0,
    ),
    "liquidations": MetricSpec(
        metric="liquidations",
        endpoint="/fapi/v1/allForceOrders",
        period="event",
        supports_history=False,
        api_limit=50,
        api_window_hours=0,
    ),
}


class BinanceAPIError(Exception):
    def __init__(self, endpoint: str, status_code: Optional[int], reason: str, payload: Any):
        super().__init__(f"{endpoint}: {reason}")
        self.endpoint = endpoint
        self.status_code = status_code
        self.reason = reason
        self.payload = payload


def utc_now() -> datetime:
    return datetime.now(tz=UTC)


def to_iso_utc(value: datetime) -> str:
    return value.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def ms_to_iso_utc(value_ms: int) -> str:
    return to_iso_utc(datetime.fromtimestamp(value_ms / 1000.0, tz=UTC))


def iso_to_datetime(value: str) -> datetime:
    raw = str(value or "").strip()
    if not raw:
        raise ValueError("empty datetime")
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    return datetime.fromisoformat(raw).astimezone(UTC)


def parse_date_floor(value: str) -> datetime:
    raw = str(value or "").strip()
    if not raw:
        raise ValueError("missing date")
    return datetime.fromisoformat(raw).replace(tzinfo=UTC)


def dt_to_ms(value: datetime) -> int:
    return int(value.astimezone(UTC).timestamp() * 1000)


def bucket_5m(value_ms: int) -> int:
    return (value_ms // FIVE_MINUTES_MS) * FIVE_MINUTES_MS


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def write_atomic_json(path: Path, payload: dict[str, Any], *, sort_keys: bool = False) -> None:
    ensure_parent(path)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(
        json.dumps(payload, indent=2, sort_keys=sort_keys) + "\n",
        encoding="utf-8",
    )
    tmp_path.replace(path)


def parse_json_line(line: str) -> Optional[dict[str, Any]]:
    raw = line.strip()
    if not raw:
        return None
    payload = json.loads(raw)
    if isinstance(payload, dict):
        return payload
    return None


def metric_spec(metric: str) -> MetricSpec:
    if metric not in METRIC_SPECS:
        raise KeyError(f"unsupported metric: {metric}")
    return METRIC_SPECS[metric]


def metric_storage_dir(repo_root: Path, symbol: str, metric: str) -> Path:
    spec = metric_spec(metric)
    return (
        repo_root
        / "data/derived/futures_metrics"
        / symbol
        / metric
        / f"period={spec.period}"
    )


def metric_partition_path(repo_root: Path, symbol: str, metric: str, ts_utc: str) -> Path:
    partition = ts_utc[:7]
    return metric_storage_dir(repo_root, symbol, metric) / f"{partition}.jsonl"


def coverage_key(symbol: str, metric: str) -> str:
    spec = metric_spec(metric)
    return f"{symbol}::{metric}::{spec.period}"


def checkpoint_key(symbol: str, metric: str) -> str:
    return coverage_key(symbol, metric)


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def load_coverage_rows(coverage_path: Path) -> list[dict[str, Any]]:
    payload = load_json(coverage_path, {"rows": []})
    rows = payload.get("rows")
    if isinstance(rows, list):
        return [row for row in rows if isinstance(row, dict)]
    return []


def write_coverage_rows(coverage_path: Path, rows: Iterable[dict[str, Any]]) -> None:
    ordered = sorted(
        [dict(row) for row in rows],
        key=lambda row: (
            str(row.get("symbol", "")),
            str(row.get("metric", "")),
            str(row.get("period", "")),
        ),
    )
    payload = {
        "schema": "futures_metrics_coverage.v1",
        "ts_utc": to_iso_utc(utc_now()),
        "rows": ordered,
    }
    write_atomic_json(coverage_path, payload, sort_keys=False)


def upsert_coverage_rows(
    coverage_path: Path, updates: Iterable[dict[str, Any]]
) -> list[dict[str, Any]]:
    merged = {
        coverage_key(str(row.get("symbol", "")), str(row.get("metric", ""))): dict(row)
        for row in load_coverage_rows(coverage_path)
        if row.get("symbol") and row.get("metric")
    }
    for row in updates:
        key = coverage_key(str(row.get("symbol", "")), str(row.get("metric", "")))
        merged[key] = dict(row)
    ordered = list(merged.values())
    write_coverage_rows(coverage_path, ordered)
    return ordered


def find_coverage_row(
    rows: Iterable[dict[str, Any]], symbol: str, metric: str
) -> Optional[dict[str, Any]]:
    target = coverage_key(symbol, metric)
    for row in rows:
        if coverage_key(str(row.get("symbol", "")), str(row.get("metric", ""))) == target:
            return dict(row)
    return None


def sanitize_coverage_reason(status: str, reason: str) -> str:
    reason_text = str(reason or "").strip()
    normalized_status = str(status or "UNKNOWN").upper().strip()
    if normalized_status != "OK":
        return reason_text
    if not reason_text:
        return ""
    if reason_text == "snapshot_only_endpoint":
        return reason_text

    lowered = reason_text.lower()
    error_markers = (
        "errno",
        "exception",
        "http ",
        "http_",
        "http:",
        "api_error",
        "urlerror",
        "network error",
        "network_error",
        "dns",
        "timed out",
        "timeout",
        "traceback",
        "fetch_failed",
        "probe_failed",
    )
    if any(marker in lowered for marker in error_markers):
        return ""
    return reason_text


def load_checkpoint(checkpoint_path: Path) -> dict[str, Any]:
    payload = load_json(checkpoint_path, {"schema": "futures_metrics_backfill_checkpoint.v1", "checkpoints": {}})
    checkpoints = payload.get("checkpoints")
    if not isinstance(checkpoints, dict):
        checkpoints = {}
    return {
        "schema": "futures_metrics_backfill_checkpoint.v1",
        "checkpoints": checkpoints,
    }


def save_checkpoint(checkpoint_path: Path, payload: dict[str, Any]) -> None:
    write_atomic_json(checkpoint_path, payload, sort_keys=True)


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


def build_futures_metrics_manifest(repo_root: Path) -> dict[str, Any]:
    return {
        "dataset_id": FUTURES_METRICS_DATASET_ID,
        "schema_version": "v1",
        "producer": "scripts/futures_metrics_fetch.py",
        "cadence": "daily_rolling",
        "path_patterns": {
            "root": "data/derived/futures_metrics",
            "template": "data/derived/futures_metrics/{symbol}/{metric}/period={period}/{partition}.jsonl",
        },
        "symbols": list(DEFAULT_SYMBOLS),
        "metrics": list(ROLLING_METRICS),
        "periods": ["5m"],
        "sources": [
            {
                "name": "binance_futures_public",
                "endpoints": [
                    metric_spec("funding_rate").endpoint,
                    metric_spec("open_interest_hist").endpoint,
                    metric_spec("global_long_short_account_ratio").endpoint,
                    metric_spec("premium_index").endpoint,
                ],
            }
        ],
        "provenance": {
            "generated_utc": to_iso_utc(utc_now()),
            "code_ref": git_code_ref(repo_root),
        },
        "notes": (
            "Generated by futures metrics producers. "
            "Rolling updates come from scripts/futures_metrics_fetch.py; "
            "manual backfill uses scripts/futures_metrics_backfill.py; "
            "availability probes use scripts/futures_metrics_probe.py."
        ),
    }


def write_futures_metrics_manifest(repo_root: Path) -> Path:
    path = repo_root / MANIFEST_DIR / f"{FUTURES_METRICS_DATASET_ID}.json"
    write_atomic_json(path, build_futures_metrics_manifest(repo_root), sort_keys=False)
    return path


def next_window_start(
    checkpoint_payload: dict[str, Any],
    symbol: str,
    metric: str,
    default_start: datetime,
) -> datetime:
    checkpoints = checkpoint_payload.get("checkpoints", {})
    entry = checkpoints.get(checkpoint_key(symbol, metric), {})
    next_start = entry.get("next_start_utc")
    if isinstance(next_start, str) and next_start.strip():
        try:
            parsed = iso_to_datetime(next_start)
        except ValueError:
            parsed = default_start
        return parsed if parsed > default_start else default_start
    return default_start


def update_checkpoint_entry(
    checkpoint_payload: dict[str, Any],
    symbol: str,
    metric: str,
    next_start: datetime,
    last_end: datetime,
) -> None:
    checkpoints = checkpoint_payload.setdefault("checkpoints", {})
    checkpoints[checkpoint_key(symbol, metric)] = {
        "symbol": symbol,
        "metric": metric,
        "period": metric_spec(metric).period,
        "next_start_utc": to_iso_utc(next_start),
        "last_window_end_utc": to_iso_utc(last_end),
        "updated_utc": to_iso_utc(utc_now()),
    }


def build_windows(
    start_dt: datetime, end_dt: datetime, chunk_days: int
) -> list[tuple[datetime, datetime]]:
    if chunk_days <= 0:
        raise ValueError("chunk_days must be > 0")
    windows: list[tuple[datetime, datetime]] = []
    cursor = start_dt
    span = timedelta(days=chunk_days)
    while cursor < end_dt:
        window_end = min(cursor + span, end_dt)
        windows.append((cursor, window_end))
        cursor = window_end
    return windows


def _load_partition_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        row = parse_json_line(line)
        if row is not None:
            rows.append(row)
    return rows


def _row_sort_key(row: dict[str, Any]) -> tuple[str, str]:
    return (
        str(row.get("ts_utc", "")),
        str(row.get("event_time_ms", "")),
    )


def merge_rows(existing_rows: Iterable[dict[str, Any]], new_rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for row in list(existing_rows) + list(new_rows):
        key = f"{row.get('ts_utc', '')}::{row.get('event_time_ms', '')}"
        merged[key] = dict(row)
    return sorted(merged.values(), key=_row_sort_key)


def write_metric_rows(
    repo_root: Path, symbol: str, metric: str, rows: Iterable[dict[str, Any]]
) -> int:
    grouped: dict[Path, list[dict[str, Any]]] = {}
    for row in rows:
        ts_utc = str(row.get("ts_utc", "")).strip()
        if not ts_utc:
            continue
        path = metric_partition_path(repo_root, symbol, metric, ts_utc)
        grouped.setdefault(path, []).append(dict(row))

    added = 0
    for path, partition_rows in grouped.items():
        existing_rows = _load_partition_rows(path)
        merged_rows = merge_rows(existing_rows, partition_rows)
        added += max(0, len(merged_rows) - len(existing_rows))
        ensure_parent(path)
        tmp_path = path.with_suffix(".jsonl.tmp")
        payload = "\n".join(json.dumps(row, sort_keys=True) for row in merged_rows)
        if payload:
            payload += "\n"
        tmp_path.write_text(payload, encoding="utf-8")
        tmp_path.replace(path)
    return added


def scan_metric_storage(repo_root: Path, symbol: str, metric: str) -> dict[str, Any]:
    base_dir = metric_storage_dir(repo_root, symbol, metric)
    if not base_dir.exists():
        return {
            "rows": 0,
            "earliest_utc": None,
            "latest_utc": None,
            "storage_paths": [],
        }

    total_rows = 0
    earliest: Optional[str] = None
    latest: Optional[str] = None
    paths = sorted(base_dir.glob("*.jsonl"))
    for path in paths:
        for line in path.read_text(encoding="utf-8").splitlines():
            row = parse_json_line(line)
            if row is None:
                continue
            ts_utc = str(row.get("ts_utc", "")).strip()
            if not ts_utc:
                continue
            total_rows += 1
            if earliest is None or ts_utc < earliest:
                earliest = ts_utc
            if latest is None or ts_utc > latest:
                latest = ts_utc

    return {
        "rows": total_rows,
        "earliest_utc": earliest,
        "latest_utc": latest,
        "storage_paths": [str(path) for path in paths],
    }


def compose_coverage_row(
    repo_root: Path,
    symbol: str,
    metric: str,
    existing_row: Optional[dict[str, Any]] = None,
    source_earliest_utc: Optional[str] = None,
    source_latest_utc: Optional[str] = None,
    status: str = "OK",
    reason: str = "",
) -> dict[str, Any]:
    spec = metric_spec(metric)
    prior = dict(existing_row or {})
    storage = scan_metric_storage(repo_root, symbol, metric)
    earliest_candidates = [
        str(value).strip()
        for value in (
            source_earliest_utc,
            prior.get("earliest_utc"),
            storage.get("earliest_utc"),
        )
        if str(value or "").strip()
    ]
    earliest_utc = min(earliest_candidates) if earliest_candidates else None
    latest_candidates = [
        str(value).strip()
        for value in (
            storage.get("latest_utc"),
            source_latest_utc,
            prior.get("latest_utc"),
        )
        if str(value or "").strip()
    ]
    latest_utc = max(latest_candidates) if latest_candidates else earliest_utc
    normalized_status = str(status or prior.get("status") or "UNKNOWN").upper().strip()
    if normalized_status not in {"OK", "WARN", "FAIL"}:
        normalized_status = "UNKNOWN"
    reason_text = sanitize_coverage_reason(
        normalized_status,
        str(reason or prior.get("reason") or "").strip(),
    )
    return {
        "ts_utc": to_iso_utc(utc_now()),
        "symbol": symbol,
        "metric": metric,
        "period": spec.period,
        "rows": int(storage.get("rows", 0)),
        "earliest_utc": earliest_utc,
        "latest_utc": latest_utc,
        "storage_earliest_utc": storage.get("earliest_utc"),
        "storage_latest_utc": storage.get("latest_utc"),
        "source_endpoint": spec.endpoint,
        "status": normalized_status,
        "reason": reason_text,
    }


def _parse_http_payload(raw_body: str) -> Any:
    body = raw_body.strip()
    if not body:
        return {}
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return {"message": body}


def fetch_json(
    endpoint: str,
    params: dict[str, Any],
    retries: int = 3,
    retry_sleep_s: float = 1.5,
    timeout_s: float = 20.0,
) -> Any:
    for attempt in range(retries):
        try:
            query = urlencode(
                {
                    key: value
                    for key, value in params.items()
                    if value is not None
                }
            )
            url = f"{API_BASE}{endpoint}"
            if query:
                url = f"{url}?{query}"
            with urlopen(url, timeout=timeout_s) as response:
                body = response.read().decode("utf-8")
            return _parse_http_payload(body)
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            payload = _parse_http_payload(body)
            reason = ""
            if isinstance(payload, dict):
                reason = str(payload.get("msg") or payload.get("message") or "").strip()
            if not reason:
                reason = str(exc.reason)
            if exc.code in {418, 429, 500, 502, 503, 504} and attempt + 1 < retries:
                time.sleep(retry_sleep_s * (attempt + 1))
                continue
            raise BinanceAPIError(endpoint, exc.code, reason, payload) from exc
        except URLError as exc:
            if attempt + 1 < retries:
                time.sleep(retry_sleep_s * (attempt + 1))
                continue
            raise BinanceAPIError(endpoint, None, str(exc.reason), {}) from exc


def _normalize_history_rows(
    metric: str, symbol: str, payload: Any, fetched_at: datetime
) -> list[dict[str, Any]]:
    if not isinstance(payload, list):
        return []

    rows: list[dict[str, Any]] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        if metric == "funding_rate":
            ts_ms = int(item.get("fundingTime", 0) or 0)
            if ts_ms <= 0:
                continue
            rows.append(
                {
                    "symbol": symbol,
                    "metric": metric,
                    "period": metric_spec(metric).period,
                    "event_time_ms": ts_ms,
                    "ts_utc": ms_to_iso_utc(ts_ms),
                    "fetched_at_utc": to_iso_utc(fetched_at),
                    "funding_rate": str(item.get("fundingRate", "")),
                    "mark_price": str(item.get("markPrice", "")),
                }
            )
            continue

        ts_ms = int(item.get("timestamp", 0) or 0)
        if ts_ms <= 0:
            continue
        if metric == "open_interest_hist":
            rows.append(
                {
                    "symbol": symbol,
                    "metric": metric,
                    "period": metric_spec(metric).period,
                    "event_time_ms": ts_ms,
                    "ts_utc": ms_to_iso_utc(ts_ms),
                    "fetched_at_utc": to_iso_utc(fetched_at),
                    "sum_open_interest": str(item.get("sumOpenInterest", "")),
                    "sum_open_interest_value": str(item.get("sumOpenInterestValue", "")),
                    "cmc": str(item.get("CMCCirculatingSupply", "")),
                }
            )
            continue

        if metric == "global_long_short_account_ratio":
            rows.append(
                {
                    "symbol": symbol,
                    "metric": metric,
                    "period": metric_spec(metric).period,
                    "event_time_ms": ts_ms,
                    "ts_utc": ms_to_iso_utc(ts_ms),
                    "fetched_at_utc": to_iso_utc(fetched_at),
                    "long_short_ratio": str(item.get("longShortRatio", "")),
                    "long_account": str(item.get("longAccount", "")),
                    "short_account": str(item.get("shortAccount", "")),
                }
            )
    return rows


def normalize_metric_rows(metric: str, symbol: str, payload: Any, fetched_at: datetime) -> list[dict[str, Any]]:
    if metric in HISTORICAL_METRICS:
        return _normalize_history_rows(metric, symbol, payload, fetched_at)

    if metric == "premium_index":
        if not isinstance(payload, dict):
            return []
        ts_ms = int(payload.get("time", 0) or dt_to_ms(fetched_at))
        bucket_ms = bucket_5m(ts_ms)
        return [
            {
                "symbol": symbol,
                "metric": metric,
                "period": metric_spec(metric).period,
                "event_time_ms": bucket_ms,
                "ts_utc": ms_to_iso_utc(bucket_ms),
                "observed_at_utc": ms_to_iso_utc(ts_ms),
                "fetched_at_utc": to_iso_utc(fetched_at),
                "mark_price": str(payload.get("markPrice", "")),
                "index_price": str(payload.get("indexPrice", "")),
                "estimated_settle_price": str(payload.get("estimatedSettlePrice", "")),
                "last_funding_rate": str(payload.get("lastFundingRate", "")),
                "interest_rate": str(payload.get("interestRate", "")),
                "next_funding_time_utc": (
                    ms_to_iso_utc(int(payload.get("nextFundingTime", 0)))
                    if int(payload.get("nextFundingTime", 0) or 0) > 0
                    else None
                ),
            }
        ]

    if metric == "liquidations":
        if not isinstance(payload, list):
            return []
        rows: list[dict[str, Any]] = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            order = item.get("o")
            if not isinstance(order, dict):
                continue
            ts_ms = int(order.get("T", 0) or 0)
            if ts_ms <= 0:
                continue
            rows.append(
                {
                    "symbol": symbol,
                    "metric": metric,
                    "period": metric_spec(metric).period,
                    "event_time_ms": ts_ms,
                    "ts_utc": ms_to_iso_utc(ts_ms),
                    "fetched_at_utc": to_iso_utc(fetched_at),
                    "side": str(order.get("S", "")),
                    "order_type": str(order.get("o", "")),
                    "time_in_force": str(order.get("f", "")),
                    "orig_qty": str(order.get("q", "")),
                    "price": str(order.get("p", "")),
                    "average_price": str(order.get("ap", "")),
                    "status": str(order.get("X", "")),
                }
            )
        return rows

    return []


def fetch_metric_range(
    metric: str, symbol: str, start_dt: datetime, end_dt: datetime
) -> list[dict[str, Any]]:
    spec = metric_spec(metric)
    if not spec.supports_history:
        raise ValueError(f"metric does not support ranged fetch: {metric}")

    rows: list[dict[str, Any]] = []
    for window_start, window_end in build_windows(
        start_dt, end_dt, max(1, int(spec.api_window_hours / 24) or 1)
    ):
        fetched_at = utc_now()
        params: dict[str, Any] = {
            "symbol": symbol,
            "limit": spec.api_limit,
            "startTime": dt_to_ms(window_start),
            "endTime": dt_to_ms(window_end),
        }
        if metric in {"open_interest_hist", "global_long_short_account_ratio"}:
            params["period"] = spec.period
        payload = fetch_json(spec.endpoint, params)
        rows.extend(normalize_metric_rows(metric, symbol, payload, fetched_at))
    return merge_rows([], rows)


def fetch_metric_snapshot(metric: str, symbol: str) -> list[dict[str, Any]]:
    spec = metric_spec(metric)
    if spec.supports_history:
        raise ValueError(f"metric requires ranged fetch: {metric}")
    fetched_at = utc_now()
    params: dict[str, Any] = {"symbol": symbol}
    if metric == "liquidations":
        params["limit"] = spec.api_limit
    payload = fetch_json(spec.endpoint, params)
    return normalize_metric_rows(metric, symbol, payload, fetched_at)


def probe_earliest_available(
    metric: str,
    symbol: str,
    start_dt: datetime,
    now_dt: Optional[datetime] = None,
    probe_step_days: int = 31,
) -> dict[str, Any]:
    current = now_dt or utc_now()
    if metric == "premium_index":
        rows = fetch_metric_snapshot(metric, symbol)
        if rows:
            ts_utc = rows[0]["ts_utc"]
            return {
                "status": "OK",
                "reason": "snapshot_only_endpoint",
                "earliest_utc": ts_utc,
                "latest_utc": ts_utc,
            }
        return {
            "status": "WARN",
            "reason": "snapshot_empty",
            "earliest_utc": None,
            "latest_utc": None,
        }

    if metric == "liquidations":
        return probe_liquidations(symbol)

    cursor = start_dt
    coarse_span = timedelta(days=max(1, probe_step_days))
    while cursor < current:
        coarse_end = min(cursor + coarse_span, current)
        for window_start, window_end in build_windows(
            cursor,
            coarse_end,
            max(1, int(metric_spec(metric).api_window_hours / 24) or 1),
        ):
            fetched_at = utc_now()
            params: dict[str, Any] = {
                "symbol": symbol,
                "limit": metric_spec(metric).api_limit,
                "startTime": dt_to_ms(window_start),
                "endTime": dt_to_ms(window_end),
            }
            if metric in {"open_interest_hist", "global_long_short_account_ratio"}:
                params["period"] = metric_spec(metric).period
            try:
                payload = fetch_json(metric_spec(metric).endpoint, params)
            except BinanceAPIError as exc:
                if (
                    metric in {"open_interest_hist", "global_long_short_account_ratio"}
                    and "starttime" in str(exc.reason or "").lower()
                    and "invalid" in str(exc.reason or "").lower()
                ):
                    return _probe_recent_retention_window(metric, symbol, current)
                raise
            rows = normalize_metric_rows(metric, symbol, payload, fetched_at)
            if rows:
                return {
                    "status": "OK",
                    "reason": "",
                    "earliest_utc": rows[0]["ts_utc"],
                    "latest_utc": rows[-1]["ts_utc"],
                }
        cursor = coarse_end

    return {
        "status": "WARN",
        "reason": "no_rows_from_api",
        "earliest_utc": None,
        "latest_utc": None,
    }


def _probe_recent_retention_window(metric: str, symbol: str, now_dt: datetime) -> dict[str, Any]:
    for lookback_days in range(30, 0, -1):
        window_start = now_dt - timedelta(days=lookback_days)
        window_end = min(window_start + timedelta(days=1), now_dt)
        fetched_at = utc_now()
        params: dict[str, Any] = {
            "symbol": symbol,
            "limit": metric_spec(metric).api_limit,
            "startTime": dt_to_ms(window_start),
            "endTime": dt_to_ms(window_end),
            "period": metric_spec(metric).period,
        }
        try:
            payload = fetch_json(metric_spec(metric).endpoint, params)
        except BinanceAPIError:
            continue
        rows = normalize_metric_rows(metric, symbol, payload, fetched_at)
        if rows:
            return {
                "status": "WARN",
                "reason": f"retention_limited_to_recent_{lookback_days}d",
                "earliest_utc": rows[0]["ts_utc"],
                "latest_utc": rows[-1]["ts_utc"],
            }

    return {
        "status": "WARN",
        "reason": "retention_window_not_found",
        "earliest_utc": None,
        "latest_utc": None,
    }


def probe_liquidations(symbol: str) -> dict[str, Any]:
    try:
        rows = fetch_metric_snapshot("liquidations", symbol)
    except BinanceAPIError as exc:
        reason = str(exc.reason or "").strip().lower()
        if "out of maintenance" in reason:
            return {
                "status": "WARN",
                "reason": "maintenance",
                "earliest_utc": None,
                "latest_utc": None,
            }
        return {
            "status": "FAIL",
            "reason": reason or "api_error",
            "earliest_utc": None,
            "latest_utc": None,
        }

    if not rows:
        return {
            "status": "WARN",
            "reason": "endpoint_empty",
            "earliest_utc": None,
            "latest_utc": None,
        }
    return {
        "status": "OK",
        "reason": "",
        "earliest_utc": rows[0]["ts_utc"],
        "latest_utc": rows[-1]["ts_utc"],
    }
