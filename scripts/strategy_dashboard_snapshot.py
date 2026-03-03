#!/usr/bin/env python3
"""
Read-only helper for building the strategy dashboard SSOT payload.

This module does not write canonical state files; state_snapshots.py remains the
only canonical writer for data/state/strategy_dashboard_latest.json.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Optional


UTC = timezone.utc
WINDOW_START_UTC = "2020-01-01T00:00:00Z"
WINDOW_START_DATE = date(2020, 1, 1)
REGIME_KEYS = ("BULL", "BEAR", "SIDEWAYS")
BLENDED_CURVE_CANDIDATES = (
    "blended_equity_curve.jsonl",
    "portfolio_equity_curve.jsonl",
    "hong_blended_equity_curve.jsonl",
    "strategy_blended_equity_curve.jsonl",
)


@dataclass(frozen=True)
class DailyPoint:
    day: date
    ts_utc: str
    value: float


def _now_utc_iso() -> str:
    return (
        datetime.now(UTC)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _to_iso_utc(dt: datetime) -> str:
    return dt.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _day_close_ts(day_value: date) -> str:
    return f"{day_value.isoformat()}T23:59:59Z"


def _safe_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        result = float(value)
        if math.isfinite(result):
            return result
        return None
    if isinstance(value, str) and value.strip():
        try:
            result = float(value)
        except ValueError:
            return None
        if math.isfinite(result):
            return result
    return None


def _relative_path(repo_root: Path, path: Optional[Path]) -> Optional[str]:
    if path is None:
        return None
    try:
        return str(path.resolve().relative_to(repo_root.resolve())).replace("\\", "/")
    except Exception:
        return str(path).replace("\\", "/")


def _read_json(path: Path) -> Optional[dict[str, Any]]:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def _find_latest_backtest_run(repo_root: Path) -> dict[str, Optional[Path]]:
    best_summary: Optional[Path] = None
    best_score: tuple[float, str] = (-1.0, "")
    for summary_path in (repo_root / "data/backtests").rglob("summary.json"):
        if summary_path.parent.parent == repo_root / "data/backtests":
            continue
        try:
            stat = summary_path.stat()
        except Exception:
            continue
        score = (stat.st_mtime, str(summary_path))
        if score > best_score:
            best_summary = summary_path
            best_score = score

    if best_summary is None:
        return {
            "run_dir": None,
            "summary": None,
            "selection": None,
            "gate": None,
            "blend_curve": None,
        }

    run_dir = best_summary.parent
    blend_curve = None
    for filename in BLENDED_CURVE_CANDIDATES:
        candidate = run_dir / filename
        if candidate.exists():
            blend_curve = candidate
            break

    return {
        "run_dir": run_dir,
        "summary": best_summary,
        "selection": run_dir / "selection.json" if (run_dir / "selection.json").exists() else None,
        "gate": run_dir / "gate.json" if (run_dir / "gate.json").exists() else None,
        "blend_curve": blend_curve,
    }


def _pick_btc_kline_path(repo_root: Path) -> Optional[Path]:
    candidates = (
        repo_root / "data/derived/BTCUSDT/1d/klines.jsonl",
        repo_root / "data/derived/BTCUSDT/4h/klines.jsonl",
        repo_root / "data/derived/BTCUSDT/1h/klines.jsonl",
        repo_root / "data/derived/BTCUSDT/15m/klines.jsonl",
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _read_daily_close_points_from_klines(path: Path, start_day: date) -> list[DailyPoint]:
    latest_close_by_day: dict[date, tuple[int, float]] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except Exception:
        return []

    for line in lines:
        raw = line.strip()
        if not raw:
            continue
        try:
            row = json.loads(raw)
        except Exception:
            continue
        ts_ms = row.get("ts")
        close = _safe_float(row.get("close"))
        if not isinstance(ts_ms, int) or close is None or close <= 0:
            continue
        dt = datetime.fromtimestamp(ts_ms / 1000.0, tz=UTC)
        day_value = dt.date()
        if day_value < start_day:
            continue
        prior = latest_close_by_day.get(day_value)
        if prior is None or ts_ms > prior[0]:
            latest_close_by_day[day_value] = (ts_ms, close)

    ordered_days = sorted(latest_close_by_day)
    if not ordered_days:
        return []
    base_close = latest_close_by_day[ordered_days[0]][1]
    if base_close <= 0:
        return []

    points: list[DailyPoint] = []
    for day_value in ordered_days:
        close = latest_close_by_day[day_value][1]
        points.append(
            DailyPoint(
                day=day_value,
                ts_utc=_day_close_ts(day_value),
                value=close / base_close,
            )
        )
    return points


def _read_daily_close_points_from_equity_curve(path: Path, start_day: date) -> list[DailyPoint]:
    latest_equity_by_day: dict[date, tuple[datetime, float]] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except Exception:
        return []

    for line in lines:
        raw = line.strip()
        if not raw:
            continue
        try:
            row = json.loads(raw)
        except Exception:
            continue
        ts_raw = str(row.get("ts") or "").strip()
        equity = _safe_float(row.get("equity"))
        if not ts_raw or equity is None or equity <= 0:
            continue
        if ts_raw.endswith("Z"):
            ts_raw = ts_raw[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(ts_raw)
        except ValueError:
            continue
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        dt = dt.astimezone(UTC)
        day_value = dt.date()
        if day_value < start_day:
            continue
        prior = latest_equity_by_day.get(day_value)
        if prior is None or dt > prior[0]:
            latest_equity_by_day[day_value] = (dt, equity)

    ordered_days = sorted(latest_equity_by_day)
    if not ordered_days:
        return []
    base_equity = latest_equity_by_day[ordered_days[0]][1]
    if base_equity <= 0:
        return []

    points: list[DailyPoint] = []
    for day_value in ordered_days:
        equity = latest_equity_by_day[day_value][1]
        points.append(
            DailyPoint(
                day=day_value,
                ts_utc=_day_close_ts(day_value),
                value=equity / base_equity,
            )
        )
    return points


def _series_metrics_from_points(points: Iterable[DailyPoint]) -> dict[str, Optional[float]]:
    ordered = list(points)
    if len(ordered) < 2:
        return {
            "total_return": None,
            "cagr": None,
            "sharpe": None,
            "max_drawdown": None,
            "points": len(ordered),
        }

    values = [point.value for point in ordered]
    total_return = values[-1] - 1.0

    elapsed_days = max((ordered[-1].day - ordered[0].day).days, 0)
    cagr = None
    if elapsed_days > 0 and values[0] > 0 and values[-1] > 0:
        try:
            cagr = (values[-1] / values[0]) ** (365.25 / elapsed_days) - 1.0
        except (ValueError, ZeroDivisionError):
            cagr = None

    returns: list[float] = []
    for prev, curr in zip(values, values[1:]):
        if prev > 0:
            returns.append((curr / prev) - 1.0)
    sharpe = None
    if len(returns) >= 2:
        avg = sum(returns) / len(returns)
        variance = sum((item - avg) ** 2 for item in returns) / (len(returns) - 1)
        std = math.sqrt(variance)
        if std > 0:
            sharpe = (avg / std) * math.sqrt(365.25)

    peak = values[0]
    max_drawdown = 0.0
    for value in values:
        if value > peak:
            peak = value
        drawdown = (value / peak) - 1.0 if peak > 0 else 0.0
        if drawdown < max_drawdown:
            max_drawdown = drawdown

    return {
        "total_return": total_return,
        "cagr": cagr,
        "sharpe": sharpe,
        "max_drawdown": max_drawdown,
        "points": len(ordered),
    }


def _summary_metrics(summary_payload: Optional[dict[str, Any]]) -> dict[str, Any]:
    payload = summary_payload or {}
    return {
        "run_id": payload.get("run_id"),
        "total_return": _safe_float(payload.get("total_return")),
        "cagr": _safe_float(payload.get("cagr")),
        "sharpe": _safe_float(payload.get("sharpe")),
        "max_drawdown": _safe_float(payload.get("max_drawdown")),
        "trades_count": int(_safe_float(payload.get("trades_count")) or 0) if payload.get("trades_count") is not None else None,
        "win_rate": _safe_float(payload.get("win_rate")),
        "start_ts": payload.get("start_ts"),
        "end_ts": payload.get("end_ts"),
    }


def _metric_delta(hong_value: Optional[float], btc_value: Optional[float]) -> Optional[float]:
    if hong_value is None or btc_value is None:
        return None
    return hong_value - btc_value


def _normalize_regime_name(raw: Any) -> Optional[str]:
    value = str(raw or "").strip().upper()
    if value == "NEUTRAL":
        value = "SIDEWAYS"
    if value in REGIME_KEYS:
        return value
    return None


def _strategy_name_from_candidate(candidate: dict[str, Any]) -> Optional[str]:
    params = candidate.get("params")
    if isinstance(params, dict):
        strategy = str(params.get("strategy") or "").strip()
        if strategy:
            return strategy
    strategy = str(candidate.get("strategy_id") or "").strip()
    return strategy or None


def _empty_regime_block(notes: Optional[list[str]] = None) -> dict[str, Any]:
    return {
        "status": "UNKNOWN",
        "strategies": [],
        "kpis": {
            "total_return": None,
            "cagr": None,
            "sharpe": None,
            "max_drawdown": None,
        },
        "notes": list(notes or []),
    }


def _build_regime_blocks(
    selection_payload: Optional[dict[str, Any]],
    regime_timeline_path: Optional[Path],
    hong_points: list[DailyPoint],
) -> dict[str, dict[str, Any]]:
    regimes = {regime: _empty_regime_block() for regime in REGIME_KEYS}

    selection_note = None
    selected_regime = None
    if selection_payload:
        selected_regime = _normalize_regime_name(selection_payload.get("regime"))
        selected_name = None
        selected_payload = selection_payload.get("selected")
        if isinstance(selected_payload, dict):
            selected_name = _strategy_name_from_candidate(selected_payload)
        candidates = selection_payload.get("candidates")
        candidate_names: list[str] = []
        if isinstance(candidates, list):
            for item in candidates[:4]:
                if isinstance(item, dict):
                    name = _strategy_name_from_candidate(item)
                    if name and name not in candidate_names:
                        candidate_names.append(name)
        if selected_regime:
            bucket = regimes[selected_regime]
            strategies: list[dict[str, Any]] = []
            if selected_name:
                strategies.append({"name": selected_name, "role": "selected"})
            for name in candidate_names:
                if name != selected_name:
                    strategies.append({"name": name, "role": "candidate"})
            bucket["strategies"] = strategies
            bucket["status"] = "WARN"
            selection_note = (
                "Current regime strategy list is sourced from latest selection.json; "
                "regime KPIs require research/policy/regime_timeline.json plus a blended HONG curve."
            )

    if regime_timeline_path is None:
        note = "research/policy/regime_timeline.json missing; per-regime KPIs unavailable."
        for regime in REGIME_KEYS:
            regimes[regime]["notes"].append(note)
            if selection_note and regime == selected_regime:
                regimes[regime]["notes"].append(selection_note)
        return regimes

    if not hong_points:
        note = "Blended HONG curve artifact unavailable; per-regime KPIs cannot be computed."
        for regime in REGIME_KEYS:
            regimes[regime]["notes"].append(note)
            if selection_note and regime == selected_regime:
                regimes[regime]["notes"].append(selection_note)
        return regimes

    try:
        timeline_payload = json.loads(regime_timeline_path.read_text(encoding="utf-8"))
    except Exception:
        note = "regime_timeline.json unreadable; per-regime KPIs unavailable."
        for regime in REGIME_KEYS:
            regimes[regime]["notes"].append(note)
            if selection_note and regime == selected_regime:
                regimes[regime]["notes"].append(selection_note)
        return regimes

    if not isinstance(timeline_payload, list):
        note = "regime_timeline.json schema unsupported; per-regime KPIs unavailable."
        for regime in REGIME_KEYS:
            regimes[regime]["notes"].append(note)
            if selection_note and regime == selected_regime:
                regimes[regime]["notes"].append(selection_note)
        return regimes

    day_lookup = {point.day: point for point in hong_points}
    for regime in REGIME_KEYS:
        regime_points: list[DailyPoint] = []
        for row in timeline_payload:
            if not isinstance(row, dict):
                continue
            if _normalize_regime_name(row.get("regime")) != regime:
                continue
            start_raw = str(row.get("start_utc") or "").strip()
            end_raw = str(row.get("end_utc") or "").strip()
            if not start_raw or not end_raw:
                continue
            if start_raw.endswith("Z"):
                start_raw = start_raw[:-1] + "+00:00"
            if end_raw.endswith("Z"):
                end_raw = end_raw[:-1] + "+00:00"
            try:
                start_dt = datetime.fromisoformat(start_raw)
                end_dt = datetime.fromisoformat(end_raw)
            except ValueError:
                continue
            if start_dt.tzinfo is None:
                start_dt = start_dt.replace(tzinfo=UTC)
            if end_dt.tzinfo is None:
                end_dt = end_dt.replace(tzinfo=UTC)
            start_day = start_dt.astimezone(UTC).date()
            end_day = end_dt.astimezone(UTC).date()
            current_day = start_day
            while current_day < end_day:
                point = day_lookup.get(current_day)
                if point is not None:
                    regime_points.append(point)
                current_day += timedelta(days=1)

        if regime_points:
            metrics = _series_metrics_from_points(regime_points)
            regimes[regime]["status"] = "OK"
            regimes[regime]["kpis"] = {
                "total_return": metrics.get("total_return"),
                "cagr": metrics.get("cagr"),
                "sharpe": metrics.get("sharpe"),
                "max_drawdown": metrics.get("max_drawdown"),
            }
        else:
            regimes[regime]["notes"].append("No HONG curve points overlapped this regime window.")

        if selection_note and regime == selected_regime:
            regimes[regime]["notes"].append(selection_note)

    return regimes


def build_strategy_dashboard_payload(repo_root: Path, now_utc: Optional[str] = None) -> dict[str, Any]:
    generated_utc = str(now_utc or _now_utc_iso())
    notes: list[str] = []

    btc_kline_path = _pick_btc_kline_path(repo_root)
    btc_points: list[DailyPoint] = []
    if btc_kline_path is None:
        notes.append("BTC kline source missing. Refresh market data before the dashboard can render a benchmark curve.")
    else:
        btc_points = _read_daily_close_points_from_klines(btc_kline_path, WINDOW_START_DATE)
        if len(btc_points) <= 1:
            notes.append(
                "BTC benchmark curve unavailable or too short. Ensure data/derived/BTCUSDT/*/klines.jsonl contains history back to 2020-01-01."
            )

    latest_run = _find_latest_backtest_run(repo_root)
    summary_payload = _read_json(latest_run["summary"]) if latest_run["summary"] else None
    selection_payload = _read_json(latest_run["selection"]) if latest_run["selection"] else None
    blend_curve_path = latest_run["blend_curve"]
    hong_points = _read_daily_close_points_from_equity_curve(blend_curve_path, WINDOW_START_DATE) if blend_curve_path else []

    if blend_curve_path is None:
        notes.append(
            "HONG curve unavailable: no dedicated blended equity curve artifact was found under the latest backtest run. "
            "Current equity_curve.jsonl is not treated as a blended portfolio curve. Run bash scripts/daily_backtest.sh to refresh summary KPIs; "
            "export a blended_equity_curve.jsonl runtime artifact to enable the HONG line."
        )
    elif len(hong_points) <= 1:
        notes.append("HONG blended curve artifact exists but does not have enough points for charting.")

    hong_by_day = {point.day: point.value for point in hong_points}
    series: list[dict[str, Any]] = []
    for point in btc_points:
        hong_value = hong_by_day.get(point.day)
        series.append(
            {
                "ts_utc": point.ts_utc,
                "btc_bh": round(point.value, 6),
                "hong": round(hong_value, 6) if hong_value is not None else None,
            }
        )

    btc_metrics = _series_metrics_from_points(btc_points)
    hong_metrics = _series_metrics_from_points(hong_points) if hong_points else {
        "total_return": None,
        "cagr": None,
        "sharpe": None,
        "max_drawdown": None,
        "points": 0,
    }

    blend_summary_metrics = _summary_metrics(summary_payload)
    if hong_points:
        effective_hong_metrics = {
            "total_return": hong_metrics.get("total_return"),
            "cagr": hong_metrics.get("cagr"),
            "sharpe": hong_metrics.get("sharpe"),
            "max_drawdown": hong_metrics.get("max_drawdown"),
        }
    else:
        effective_hong_metrics = {
            "total_return": blend_summary_metrics.get("total_return"),
            "cagr": blend_summary_metrics.get("cagr"),
            "sharpe": blend_summary_metrics.get("sharpe"),
            "max_drawdown": blend_summary_metrics.get("max_drawdown"),
        }

    regime_timeline_path = repo_root / "research/policy/regime_timeline.json"
    if not regime_timeline_path.exists():
        regime_timeline_path = None

    regime_blocks = _build_regime_blocks(selection_payload, regime_timeline_path, hong_points)

    end_utc = series[-1]["ts_utc"] if series else generated_utc
    payload = {
        "schema": "strategy_dashboard.v1",
        "generated_utc": generated_utc,
        "window": {
            "start_utc": WINDOW_START_UTC,
            "end_utc": end_utc,
        },
        "series": series,
        "kpis": {
            "btc_bh": {
                "total_return": btc_metrics.get("total_return"),
                "cagr": btc_metrics.get("cagr"),
                "sharpe": btc_metrics.get("sharpe"),
                "max_drawdown": btc_metrics.get("max_drawdown"),
                "series_points": btc_metrics.get("points"),
            },
            "hong": {
                "total_return": effective_hong_metrics.get("total_return"),
                "cagr": effective_hong_metrics.get("cagr"),
                "sharpe": effective_hong_metrics.get("sharpe"),
                "max_drawdown": effective_hong_metrics.get("max_drawdown"),
                "series_points": hong_metrics.get("points"),
                "curve_available": bool(hong_points),
            },
            "delta": {
                "total_return": _metric_delta(
                    effective_hong_metrics.get("total_return"),
                    btc_metrics.get("total_return"),
                ),
                "cagr": _metric_delta(
                    effective_hong_metrics.get("cagr"),
                    btc_metrics.get("cagr"),
                ),
                "sharpe": _metric_delta(
                    effective_hong_metrics.get("sharpe"),
                    btc_metrics.get("sharpe"),
                ),
                "max_drawdown": _metric_delta(
                    effective_hong_metrics.get("max_drawdown"),
                    btc_metrics.get("max_drawdown"),
                ),
            },
        },
        "regimes": regime_blocks,
        "blend": {
            "kpis": blend_summary_metrics,
            "notes": notes,
        },
        "sources": {
            "btc_bh_curve": {
                "path": _relative_path(repo_root, btc_kline_path),
                "series_points": len(btc_points),
            },
            "hong_curve": {
                "path": _relative_path(repo_root, blend_curve_path),
                "series_points": len(hong_points),
            },
            "latest_backtest_run": {
                "path": _relative_path(repo_root, latest_run["run_dir"]),
                "summary_path": _relative_path(repo_root, latest_run["summary"]),
                "selection_path": _relative_path(repo_root, latest_run["selection"]),
                "gate_path": _relative_path(repo_root, latest_run["gate"]),
            },
            "regime_timeline": {
                "path": _relative_path(repo_root, regime_timeline_path),
                "status": "OK" if regime_timeline_path else "MISSING",
            },
            "refresh_hint": "bash scripts/refresh_state.sh",
        },
    }
    return payload
