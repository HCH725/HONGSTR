#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import math
import re
import shutil
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_STATE_DIR = REPO_ROOT / "data" / "state"
DEFAULT_VAULT_ROOT = REPO_ROOT / "_local" / "obsidian_vault" / "HONGSTR"
DEFAULT_LANCEDB_DIR = REPO_ROOT / "_local" / "lancedb" / "hongstr_obsidian.lancedb"
DEFAULT_STATE_FILE = REPO_ROOT / "_local" / "obsidian_index_state.json"
INDEX_MANIFEST_NAME = "chunks.json"
INDEX_TABLE_NAME = "obsidian_chunks"
DEFAULT_SSOT_FILES = (
    "daily_report_latest.json",
    "system_health_latest.json",
    "freshness_table.json",
    "coverage_matrix_latest.json",
    "brake_health_latest.json",
    "regime_monitor_latest.json",
    "cost_sensitivity_matrix_latest.json",
    "strategy_pool.json",
    "strategy_pool_summary.json",
)

UTC = timezone.utc
FRONTMATTER_KEY_ORDER = (
    "type",
    "date",
    "strategy_id",
    "incident_id",
    "severity",
    "status",
    "generated_utc",
    "ssot_ts_utc",
    "first_seen_utc",
    "last_updated_utc",
    "detected_utc",
    "resolved_utc",
    "symbols",
    "timeframes",
    "regime_slice",
    "ssot_refs",
)
RUNTIME_NOTE_METADATA_KEYS = frozenset(
    {
        "generated_utc",
        "first_seen_utc",
        "last_updated_utc",
        "detected_utc",
        "resolved_utc",
    }
)


def utc_now() -> datetime:
    return datetime.now(UTC)


def ensure_aware_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def now_utc_iso() -> str:
    return utc_now().replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_iso8601(value: str | None) -> datetime | None:
    if not value:
        return None
    text = value.strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return ensure_aware_utc(datetime.fromisoformat(text))
    except ValueError:
        return None


def stable_json_hash(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()


def text_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def load_json_file(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except json.JSONDecodeError:
        return None


def write_json_file(path: Path, payload: Any) -> None:
    ensure_parent(path)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )


def write_text_if_changed(path: Path, text: str, dry_run: bool) -> bool:
    existing = path.read_text(encoding="utf-8") if path.exists() else None
    if existing == text:
        return False
    if not dry_run:
        ensure_parent(path)
        path.write_text(text, encoding="utf-8")
    return True


def relative_to_repo(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def sanitize_path(value: str | None, repo_root: Path) -> str | None:
    if not value:
        return value
    text = str(value)
    try:
        return Path(text).resolve().relative_to(repo_root.resolve()).as_posix()
    except Exception:
        return text.replace(str(repo_root.resolve()) + "/", "")


def extract_ts_utc(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    for key in ("ts_utc", "generated_utc", "updated_at_utc", "timestamp", "generated_at"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def latest_ts_utc(values: list[str | None]) -> str | None:
    parsed = [(value, parse_iso8601(value)) for value in values if value]
    parsed = [(raw, dt) for raw, dt in parsed if dt is not None]
    if not parsed:
        return None
    parsed.sort(key=lambda item: item[1])
    return parsed[-1][0]


def severity_rank(value: str | None) -> int:
    normalized = (value or "").upper()
    if normalized in {"FAIL", "BLOCKED"}:
        return 3
    if normalized in {"WARN", "WARNING"}:
        return 2
    if normalized in {"PASS_EXPECTED", "PASS", "OK"}:
        return 1
    return 0


def severity_label(rank: int) -> str:
    if rank >= 3:
        return "FAIL"
    if rank == 2:
        return "WARN"
    return "OK"


def collect_symbols_timeframes(payloads: list[Any]) -> tuple[list[str], list[str]]:
    symbols: set[str] = set()
    timeframes: set[str] = set()

    def visit(value: Any, depth: int) -> None:
        if depth > 6:
            return
        if isinstance(value, dict):
            for key in ("symbol", "strategy_symbol"):
                candidate = value.get(key)
                if isinstance(candidate, str) and candidate:
                    symbols.add(candidate)
            for key in ("symbols",):
                candidate = value.get(key)
                if isinstance(candidate, list):
                    for item in candidate:
                        if isinstance(item, str) and item:
                            symbols.add(item)
            for key in ("tf", "timeframe"):
                candidate = value.get(key)
                if isinstance(candidate, str) and candidate:
                    timeframes.add(candidate)
            for key in ("timeframes",):
                candidate = value.get(key)
                if isinstance(candidate, list):
                    for item in candidate:
                        if isinstance(item, str) and item:
                            timeframes.add(item)
            for child in value.values():
                visit(child, depth + 1)
            return
        if isinstance(value, list):
            for child in value[:200]:
                visit(child, depth + 1)

    for payload in payloads:
        visit(payload, 0)
    return sorted(symbols), sorted(timeframes)


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "note"


def _frontmatter_scalar(value: Any) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, (int, float)):
        return json.dumps(value, ensure_ascii=False)
    return json.dumps(str(value), ensure_ascii=False)


def _frontmatter_sort_key(key: str) -> tuple[int, int, str]:
    try:
        return (0, FRONTMATTER_KEY_ORDER.index(key), key)
    except ValueError:
        return (1, len(FRONTMATTER_KEY_ORDER), key)


def _ordered_metadata_items(metadata: dict[str, Any]) -> list[tuple[str, Any]]:
    return sorted(metadata.items(), key=lambda item: _frontmatter_sort_key(item[0]))


def render_frontmatter(metadata: dict[str, Any]) -> str:
    lines = ["---"]
    for key, value in _ordered_metadata_items(metadata):
        if isinstance(value, list):
            if not value:
                lines.append(f"{key}: []")
                continue
            lines.append(f"{key}:")
            for item in value:
                lines.append(f"  - {_frontmatter_scalar(item)}")
            continue
        lines.append(f"{key}: {_frontmatter_scalar(value)}")
    lines.append("---")
    return "\n".join(lines)


def parse_frontmatter(markdown_text: str) -> tuple[dict[str, Any], str]:
    if not markdown_text.startswith("---\n"):
        return {}, markdown_text
    lines = markdown_text.splitlines()
    metadata: dict[str, Any] = {}
    index = 1
    while index < len(lines):
        line = lines[index]
        if line == "---":
            body = "\n".join(lines[index + 1 :]).lstrip("\n")
            return metadata, body
        if not line:
            index += 1
            continue
        if ":" not in line:
            index += 1
            continue
        key, raw_value = line.split(":", 1)
        raw_value = raw_value.strip()
        if not raw_value:
            items: list[Any] = []
            index += 1
            while index < len(lines) and lines[index].startswith("  - "):
                items.append(_parse_frontmatter_scalar(lines[index][4:].strip()))
                index += 1
            metadata[key.strip()] = items
            continue
        metadata[key.strip()] = _parse_frontmatter_scalar(raw_value)
        index += 1
    return {}, markdown_text


def _parse_frontmatter_scalar(raw_value: str) -> Any:
    if raw_value in {"null", "true", "false"}:
        return {"null": None, "true": True, "false": False}[raw_value]
    if raw_value == "[]":
        return []
    try:
        return json.loads(raw_value)
    except json.JSONDecodeError:
        return raw_value


def note_signature(
    note_type: str,
    metadata: dict[str, Any],
    sections: list[tuple[str, list[str]]],
) -> str:
    stable_metadata = {
        key: value
        for key, value in _ordered_metadata_items(metadata)
        if key not in RUNTIME_NOTE_METADATA_KEYS
    }
    return stable_json_hash(
        {
            "type": note_type,
            "metadata": stable_metadata,
            "sections": sections,
        }
    )


def build_markdown_note(metadata: dict[str, Any], sections: list[tuple[str, list[str]]]) -> str:
    body_lines: list[str] = [render_frontmatter(metadata), ""]
    for heading, bullets in sections:
        body_lines.append(f"# {heading}")
        if bullets:
            body_lines.extend(f"- {bullet}" for bullet in bullets)
        else:
            body_lines.append("- None.")
        body_lines.append("")
    return "\n".join(body_lines).rstrip() + "\n"


def load_sync_state(state_path: Path) -> dict[str, Any]:
    existing = load_json_file(state_path)
    if not isinstance(existing, dict):
        return {"version": 1, "notes": {}, "index": {"files": {}}}
    existing.setdefault("version", 1)
    existing.setdefault("notes", {})
    existing.setdefault("index", {})
    existing["index"].setdefault("files", {})
    return existing


def save_sync_state(state_path: Path, payload: dict[str, Any], dry_run: bool) -> None:
    if dry_run:
        return
    write_json_file(state_path, payload)


def load_ssot_payloads(state_dir: Path) -> dict[str, dict[str, Any]]:
    payloads: dict[str, dict[str, Any]] = {}
    for filename in DEFAULT_SSOT_FILES:
        path = state_dir / filename
        data = load_json_file(path)
        if isinstance(data, dict):
            payloads[filename] = data
    return payloads


def _format_ref(path: str, payload: dict[str, Any] | None) -> str:
    ts_utc = extract_ts_utc(payload) if payload else None
    if ts_utc:
        return f"{path} (ts_utc: {ts_utc})"
    return path


def _system_component_bullets(system_health: dict[str, Any] | None) -> list[str]:
    if not isinstance(system_health, dict):
        return ["Missing data/state/system_health_latest.json."]
    components = system_health.get("components")
    if not isinstance(components, dict):
        return ["No component health payload available.", _format_ref("data/state/system_health_latest.json", system_health)]
    bullets = []
    for key in sorted(components):
        component = components.get(key)
        if not isinstance(component, dict):
            continue
        status = component.get("status", "UNKNOWN")
        detail_bits = []
        for detail_key in (
            "max_age_h",
            "blocked",
            "done",
            "total",
            "last_check_status",
            "last_check_age_sec",
            "top_reason",
            "age_h",
        ):
            if detail_key in component:
                detail_bits.append(f"{detail_key}={component[detail_key]}")
        detail = f" ({', '.join(detail_bits)})" if detail_bits else ""
        bullets.append(f"{key}: {status}{detail}")
    bullets.append(_format_ref("data/state/system_health_latest.json", system_health))
    return bullets


def _freshness_bullets(
    daily_report: dict[str, Any] | None,
    freshness_table: dict[str, Any] | None,
    brake_health: dict[str, Any] | None,
) -> list[str]:
    bullets: list[str] = []
    summary = daily_report.get("freshness_summary") if isinstance(daily_report, dict) else None
    if isinstance(summary, dict):
        profile_totals = summary.get("profile_totals")
        if isinstance(profile_totals, dict):
            for key in sorted(profile_totals):
                value = profile_totals.get(key)
                if isinstance(value, dict):
                    bullets.append(
                        f"{key}: ok={value.get('ok', 0)} warn={value.get('warn', 0)} fail={value.get('fail', 0)}"
                    )
        if "non_ok_rows" in summary:
            bullets.append(f"Non-OK rows: {summary.get('non_ok_rows')}")
    rows = freshness_table.get("rows") if isinstance(freshness_table, dict) else None
    if isinstance(rows, list):
        non_ok = [row for row in rows if isinstance(row, dict) and row.get("status") != "OK"]
        bullets.append(f"Freshness rows: total={len(rows)} non_ok={len(non_ok)}")
    if isinstance(brake_health, dict):
        bullets.append(f"Brake status: {brake_health.get('status', 'UNKNOWN')}")
    bullets.extend(
        [
            _format_ref("data/state/freshness_table.json", freshness_table),
            _format_ref("data/state/brake_health_latest.json", brake_health),
        ]
    )
    return bullets or ["No freshness metrics available."]


def _coverage_bullets(coverage_matrix: dict[str, Any] | None) -> list[str]:
    if not isinstance(coverage_matrix, dict):
        return ["Missing data/state/coverage_matrix_latest.json."]
    totals = coverage_matrix.get("totals")
    bullets: list[str] = []
    if isinstance(totals, dict):
        bullets.append(
            "Coverage totals: "
            f"done={totals.get('done', 0)} "
            f"blocked={totals.get('blocked', 0)} "
            f"rebase={totals.get('rebase', 0)} "
            f"inProgress={totals.get('inProgress', 0)}"
        )
    rows = coverage_matrix.get("rows")
    if isinstance(rows, list):
        blocked = [
            row
            for row in rows
            if isinstance(row, dict) and str(row.get("status", "")).upper() not in {"PASS", "OK"}
        ]
        if blocked:
            sample = blocked[0]
            bullets.append(
                "First non-pass: "
                f"{sample.get('symbol', 'UNKNOWN')} {sample.get('tf', '?')} status={sample.get('status', 'UNKNOWN')}"
            )
        else:
            bullets.append("All coverage rows PASS.")
    bullets.append(_format_ref("data/state/coverage_matrix_latest.json", coverage_matrix))
    return bullets


def _regime_bullets(
    daily_report: dict[str, Any] | None,
    regime_monitor: dict[str, Any] | None,
) -> list[str]:
    bullets: list[str] = []
    daily_components = daily_report.get("ssot_components") if isinstance(daily_report, dict) else None
    regime_component = (
        daily_components.get("regime_signal")
        if isinstance(daily_components, dict)
        else None
    )
    if isinstance(regime_component, dict):
        bullets.append(
            f"Daily signal: {regime_component.get('status', 'UNKNOWN')} - {regime_component.get('top_reason', 'No reason')}"
        )
    if isinstance(regime_monitor, dict):
        reasons = regime_monitor.get("reason")
        if isinstance(reasons, list) and reasons:
            bullets.append(f"Monitor: {regime_monitor.get('overall', 'UNKNOWN')} - {reasons[0]}")
        else:
            bullets.append(f"Monitor: {regime_monitor.get('overall', 'UNKNOWN')}")
        if regime_monitor.get("suggestion"):
            bullets.append(f"Suggestion: {regime_monitor['suggestion']}")
    bullets.extend(
        [
            _format_ref("data/state/daily_report_latest.json", daily_report),
            _format_ref("data/state/regime_monitor_latest.json", regime_monitor),
        ]
    )
    return bullets or ["No regime signal data available."]


def _strategy_top_bullets(daily_report: dict[str, Any] | None) -> list[str]:
    if not isinstance(daily_report, dict):
        return ["Missing data/state/daily_report_latest.json."]
    strategy_pool = daily_report.get("strategy_pool")
    if not isinstance(strategy_pool, dict):
        return ["No strategy summary found.", _format_ref("data/state/daily_report_latest.json", daily_report)]
    leaderboard = strategy_pool.get("leaderboard_top")
    bullets: list[str] = []
    if isinstance(leaderboard, list) and leaderboard:
        for entry in leaderboard[:3]:
            if not isinstance(entry, dict):
                continue
            bullets.append(
                f"{entry.get('strategy_id', 'UNKNOWN')} "
                f"score={entry.get('score', 'NA')} "
                f"rec={entry.get('recommendation', 'UNKNOWN')} "
                f"gate={entry.get('gate_overall', 'UNKNOWN')}"
            )
    else:
        bullets.append("No leaderboard entries available.")
    bullets.append(_format_ref("data/state/daily_report_latest.json", daily_report))
    return bullets


def _actions_next_bullets(
    daily_report: dict[str, Any] | None,
    system_health: dict[str, Any] | None,
    coverage_matrix: dict[str, Any] | None,
    regime_monitor: dict[str, Any] | None,
) -> list[str]:
    bullets: list[str] = []
    refresh_hint = daily_report.get("refresh_hint") if isinstance(daily_report, dict) else None
    if isinstance(refresh_hint, str) and refresh_hint:
        bullets.append(f"Refresh command: {refresh_hint}")
    system_status = system_health.get("ssot_status") if isinstance(system_health, dict) else None
    if system_status and system_status != "OK":
        bullets.append(f"System status is {system_status}; review SystemHealth and Incidents.")
    totals = coverage_matrix.get("totals") if isinstance(coverage_matrix, dict) else None
    if isinstance(totals, dict) and totals.get("blocked", 0):
        bullets.append("Coverage is blocked; investigate coverage matrix blockers before promotion.")
    if isinstance(regime_monitor, dict) and regime_monitor.get("overall") not in {None, "OK"}:
        bullets.append("Regime monitor is not OK; pause promotions until signals normalize.")
    bullets.append(_format_ref("data/state/daily_report_latest.json", daily_report))
    return bullets


def build_daily_note_payload(
    payloads: dict[str, dict[str, Any]],
    now_utc: str,
) -> dict[str, Any] | None:
    if not payloads:
        return None
    refs = [
        f"data/state/{name}"
        for name in DEFAULT_SSOT_FILES
        if name in payloads and name in {
            "daily_report_latest.json",
            "system_health_latest.json",
            "freshness_table.json",
            "coverage_matrix_latest.json",
            "brake_health_latest.json",
            "regime_monitor_latest.json",
        }
    ]
    daily_report = payloads.get("daily_report_latest.json")
    system_health = payloads.get("system_health_latest.json")
    freshness_table = payloads.get("freshness_table.json")
    coverage_matrix = payloads.get("coverage_matrix_latest.json")
    brake_health = payloads.get("brake_health_latest.json")
    regime_monitor = payloads.get("regime_monitor_latest.json")
    symbols, timeframes = collect_symbols_timeframes(
        [daily_report, system_health, freshness_table, coverage_matrix, brake_health, regime_monitor]
    )
    regime_slice = "ALL"
    if isinstance(regime_monitor, dict) and isinstance(regime_monitor.get("overall"), str):
        regime_slice = str(regime_monitor.get("overall") or "ALL")
    ssot_ts_utc = latest_ts_utc([extract_ts_utc(payloads.get(name)) for name in payloads])
    note_dt = parse_iso8601(ssot_ts_utc) or parse_iso8601(now_utc) or utc_now()
    note_date = note_dt.date().isoformat()
    note_path = Path("Daily") / note_date[:4] / note_date[5:7] / f"{note_date}.md"
    metadata = {
        "type": "daily",
        "date": note_date,
        "generated_utc": ssot_ts_utc,
        "ssot_ts_utc": ssot_ts_utc,
        "ssot_refs": refs,
        "symbols": symbols,
        "timeframes": timeframes,
        "regime_slice": regime_slice,
    }
    sections = [
        (
            "Summary",
            [
                f"SSOT status: {daily_report.get('ssot_status', 'UNKNOWN') if isinstance(daily_report, dict) else 'UNKNOWN'}",
                f"Generated UTC: {ssot_ts_utc or 'UNKNOWN'}",
                _format_ref("data/state/daily_report_latest.json", daily_report),
            ],
        ),
        ("SystemHealth", _system_component_bullets(system_health)),
        ("DataQuality", _freshness_bullets(daily_report, freshness_table, brake_health)),
        ("Coverage", _coverage_bullets(coverage_matrix)),
        ("RegimeSignal", _regime_bullets(daily_report, regime_monitor)),
        ("StrategyTop", _strategy_top_bullets(daily_report)),
        ("ActionsNext", _actions_next_bullets(daily_report, system_health, coverage_matrix, regime_monitor)),
    ]
    content = build_markdown_note(metadata, sections)
    source_hash = note_signature("daily", metadata, sections)
    return {
        "vault_rel_path": note_path.as_posix(),
        "content": content,
        "source_hash": source_hash,
        "first_seen_utc": now_utc,
        "type": "daily",
    }


def _strategy_status_for_entries(
    strategy_id: str,
    entries: list[dict[str, Any]],
    promoted: set[str],
    demoted: set[str],
) -> str:
    candidate_ids = {str(entry.get("candidate_id")) for entry in entries if entry.get("candidate_id")}
    if candidate_ids & promoted:
        return "ADOPTED"
    if candidate_ids & demoted:
        return "REJECTED"
    if entries:
        return "CANDIDATE"
    return "UNKNOWN"


def build_strategy_note_payloads(
    payloads: dict[str, dict[str, Any]],
    state: dict[str, Any],
    now_utc: str,
) -> list[dict[str, Any]]:
    daily_report = payloads.get("daily_report_latest.json")
    strategy_pool = payloads.get("strategy_pool.json")
    regime_monitor = payloads.get("regime_monitor_latest.json")
    if not isinstance(daily_report, dict) and not isinstance(strategy_pool, dict):
        return []
    entries_by_strategy: dict[str, list[dict[str, Any]]] = defaultdict(list)
    if isinstance(daily_report, dict):
        pool = daily_report.get("strategy_pool")
        leaderboard = pool.get("leaderboard_top") if isinstance(pool, dict) else None
        if isinstance(leaderboard, list):
            for entry in leaderboard:
                if isinstance(entry, dict) and entry.get("strategy_id"):
                    entries_by_strategy[str(entry["strategy_id"])].append(entry)
    if isinstance(strategy_pool, dict):
        for entry in strategy_pool.get("candidates", []):
            if isinstance(entry, dict) and entry.get("strategy_id"):
                entries_by_strategy[str(entry["strategy_id"])].append(entry)
    promoted = set()
    demoted = set()
    if isinstance(strategy_pool, dict):
        promoted = {str(value) for value in strategy_pool.get("promoted", [])}
        demoted = {str(value) for value in strategy_pool.get("demoted", [])}
    global_symbols, global_timeframes = collect_symbols_timeframes(
        [daily_report, strategy_pool, regime_monitor]
    )
    outputs: list[dict[str, Any]] = []
    for strategy_id in sorted(entries_by_strategy):
        entries = entries_by_strategy[strategy_id]
        primary = entries[0]
        status = _strategy_status_for_entries(strategy_id, entries, promoted, demoted)
        ssot_ts_utc = latest_ts_utc(
            [
                extract_ts_utc(daily_report),
                extract_ts_utc(strategy_pool),
                extract_ts_utc(regime_monitor),
            ]
        )
        regime_slice = (
            str(regime_monitor.get("overall"))
            if isinstance(regime_monitor, dict) and regime_monitor.get("overall")
            else "ALL"
        )
        evidence_payload = {
            "strategy_id": strategy_id,
            "status": status,
            "entries": [
                {
                    "candidate_id": entry.get("candidate_id"),
                    "score": entry.get("score", entry.get("last_score")),
                    "gate_overall": entry.get("gate_overall"),
                    "recommendation": entry.get("recommendation"),
                    "direction": entry.get("direction"),
                    "variant": entry.get("variant"),
                    "metrics": entry.get("last_oos_metrics")
                    if isinstance(entry.get("last_oos_metrics"), dict)
                    else {
                        "sharpe": entry.get("oos_sharpe"),
                        "return": entry.get("oos_return"),
                        "mdd": entry.get("oos_mdd"),
                    },
                }
                for entry in entries
            ],
            "regime_slice": regime_slice,
            "ssot_ts_utc": ssot_ts_utc,
        }
        evidence_hash = stable_json_hash(evidence_payload)
        vault_rel_path = f"Strategies/{strategy_id}.md"
        prior_note = state.get("notes", {}).get(vault_rel_path, {})
        first_seen_utc = prior_note.get("first_seen_utc", ssot_ts_utc or now_utc)
        metadata = {
            "type": "strategy",
            "strategy_id": strategy_id,
            "first_seen_utc": first_seen_utc,
            "last_updated_utc": ssot_ts_utc,
            "ssot_ts_utc": ssot_ts_utc,
            "symbols": global_symbols,
            "timeframes": global_timeframes,
            "regime_slice": regime_slice,
            "status": status,
            "ssot_refs": [
                "data/state/daily_report_latest.json",
                "data/state/strategy_pool.json",
                "data/state/regime_monitor_latest.json",
            ],
        }
        costs_summary = payloads.get("cost_sensitivity_matrix_latest.json")
        cost_rows = 0
        if isinstance(costs_summary, dict):
            rows = costs_summary.get("rows")
            if isinstance(rows, list):
                cost_rows = len(rows)
        sections = [
            (
                "Thesis",
                [
                    f"Family={primary.get('family', 'UNKNOWN')} direction={primary.get('direction', 'UNKNOWN')} variant={primary.get('variant', 'UNKNOWN')}",
                    f"Current status: {status}",
                    _format_ref("data/state/strategy_pool.json", strategy_pool),
                ],
            ),
            (
                "Evidence",
                [
                    f"{entry.get('candidate_id', strategy_id)} score={entry.get('score', entry.get('last_score', 'NA'))} gate={entry.get('gate_overall', 'UNKNOWN')} rec={entry.get('recommendation', 'UNKNOWN')}"
                    for entry in entries[:3]
                ]
                + [_format_ref("data/state/daily_report_latest.json", daily_report)],
            ),
            (
                "CostsSensitivity",
                [
                    f"Local cost sensitivity snapshot rows={cost_rows}" if cost_rows else "No cost sensitivity summary attached.",
                    _format_ref("data/state/system_health_latest.json", payloads.get("system_health_latest.json")),
                ],
            ),
            (
                "FailureModes",
                [
                    f"MDD risk={entry.get('oos_mdd', entry.get('last_oos_metrics', {}).get('mdd', 'NA'))} metrics_status={entry.get('metrics_status', 'UNKNOWN')}"
                    for entry in entries[:2]
                ]
                or ["No explicit failure metrics available."],
            ),
            (
                "RegimeNotes",
                [
                    f"Regime slice: {regime_slice}",
                    _format_ref("data/state/regime_monitor_latest.json", regime_monitor),
                ],
            ),
            (
                "DecisionLog",
                [
                    f"Evidence hash: {evidence_hash[:12]}",
                    f"Updated: {ssot_ts_utc or 'UNKNOWN'}",
                ],
            ),
        ]
        content = build_markdown_note(metadata, sections)
        source_hash = note_signature("strategy", metadata, sections)
        outputs.append(
            {
                "vault_rel_path": vault_rel_path,
                "content": content,
                "source_hash": source_hash,
                "first_seen_utc": first_seen_utc,
                "type": "strategy",
            }
        )
    return outputs


def build_incident_note_payloads(
    payloads: dict[str, dict[str, Any]],
    now_utc: str,
) -> list[dict[str, Any]]:
    outputs: list[dict[str, Any]] = []
    system_health = payloads.get("system_health_latest.json")
    coverage_matrix = payloads.get("coverage_matrix_latest.json")
    brake_health = payloads.get("brake_health_latest.json")
    ssot_ts_utc = latest_ts_utc(
        [
            extract_ts_utc(system_health),
            extract_ts_utc(coverage_matrix),
            extract_ts_utc(brake_health),
        ]
    )
    note_date = (parse_iso8601(ssot_ts_utc) or parse_iso8601(now_utc) or utc_now()).date().isoformat()
    incident_specs: list[tuple[str, str, list[str], list[str]]] = []

    system_rank = 0
    if isinstance(system_health, dict):
        system_rank = severity_rank(str(system_health.get("ssot_status")))
        components = system_health.get("components")
        if isinstance(components, dict):
            for component in components.values():
                if isinstance(component, dict):
                    system_rank = max(system_rank, severity_rank(str(component.get("status"))))
    if system_rank >= 2:
        incident_specs.append(
            (
                "system-health",
                severity_label(system_rank),
                [
                    f"system_health ssot_status={system_health.get('ssot_status', 'UNKNOWN') if isinstance(system_health, dict) else 'UNKNOWN'}",
                    _format_ref("data/state/system_health_latest.json", system_health),
                ],
                ["Review refresh_state outputs and inspect component-level warnings."],
            )
        )

    coverage_rank = 0
    if isinstance(coverage_matrix, dict):
        totals = coverage_matrix.get("totals")
        if isinstance(totals, dict) and totals.get("blocked", 0):
            coverage_rank = 3
        rows = coverage_matrix.get("rows")
        if isinstance(rows, list):
            if any(
                isinstance(row, dict)
                and str(row.get("status", "")).upper() not in {"PASS", "OK"}
                for row in rows
            ):
                coverage_rank = max(coverage_rank, 2)
    if coverage_rank >= 2:
        incident_specs.append(
            (
                "coverage-blocked",
                severity_label(coverage_rank),
                [
                    "Coverage matrix contains blocked or non-pass rows.",
                    _format_ref("data/state/coverage_matrix_latest.json", coverage_matrix),
                ],
                ["Resolve blocked coverage rows before promotion or dispatch."],
            )
        )

    brake_rank = 0
    if isinstance(brake_health, dict):
        brake_rank = severity_rank(str(brake_health.get("status")))
        if brake_health.get("overall_fail") is True:
            brake_rank = 3
    if brake_rank >= 2:
        incident_specs.append(
            (
                "brake-health",
                severity_label(brake_rank),
                [
                    f"Brake health status={brake_health.get('status', 'UNKNOWN') if isinstance(brake_health, dict) else 'UNKNOWN'}",
                    _format_ref("data/state/brake_health_latest.json", brake_health),
                ],
                ["Run brake healthcheck and inspect referenced stale inputs."],
            )
        )

    for slug, severity, what_happened, preventive in incident_specs:
        incident_id = f"{note_date}-{slug}"
        metadata = {
            "type": "incident",
            "incident_id": incident_id,
            "severity": severity,
            "detected_utc": ssot_ts_utc or now_utc,
            "resolved_utc": None,
            "ssot_ts_utc": ssot_ts_utc,
            "ssot_refs": [
                "data/state/system_health_latest.json",
                "data/state/coverage_matrix_latest.json",
                "data/state/brake_health_latest.json",
            ],
        }
        sections = [
            ("WhatHappened", what_happened),
            ("Impact", [f"Severity={severity}", "May block promotion, review, or trust in SSOT summaries."]),
            (
                "RootCauseHypotheses",
                [
                    "Snapshot producer lagged or upstream state is inconsistent.",
                    "Recent refresh did not complete cleanly across all SSOT components.",
                ],
            ),
            ("FixSOP", ["Run `bash scripts/refresh_state.sh` and inspect the referenced SSOT files."]),
            ("PreventiveActions", preventive),
        ]
        content = build_markdown_note(metadata, sections)
        source_hash = note_signature("incident", metadata, sections)
        outputs.append(
            {
                "vault_rel_path": f"Incidents/{note_date}_{slugify(slug)}.md",
                "content": content,
                "source_hash": source_hash,
                "first_seen_utc": now_utc,
                "type": "incident",
            }
        )
    return outputs


@dataclass(frozen=True)
class NoteChunk:
    vault_rel_path: str
    heading_path: str
    chunk_text: str
    chunk_hash: str
    metadata: dict[str, Any]
    chunk_index: int


def _split_markdown_sections(body: str) -> list[tuple[str, str]]:
    lines = body.splitlines()
    sections: list[tuple[str, str]] = []
    current_heading = "Document"
    current_lines: list[str] = []
    for line in lines:
        if line.startswith("# "):
            if current_lines:
                sections.append((current_heading, "\n".join(current_lines).strip()))
            current_heading = line[2:].strip() or "Document"
            current_lines = []
            continue
        current_lines.append(line)
    if current_lines or not sections:
        sections.append((current_heading, "\n".join(current_lines).strip()))
    return sections


def _chunk_text(section_text: str, max_chars: int, overlap: int) -> list[str]:
    text = section_text.strip()
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + max_chars)
        candidate = text[start:end]
        if end < len(text):
            split_at = candidate.rfind("\n")
            if split_at >= max_chars // 2:
                end = start + split_at
                candidate = text[start:end]
        candidate = candidate.strip()
        if candidate:
            chunks.append(candidate)
        if end >= len(text):
            break
        start = max(0, end - overlap)
    return chunks


def build_note_chunks(
    vault_rel_path: str,
    note_text: str,
    max_chars: int = 1400,
    overlap: int = 200,
) -> list[NoteChunk]:
    metadata, body = parse_frontmatter(note_text)
    chunks: list[NoteChunk] = []
    chunk_counter = 0
    for heading, section_body in _split_markdown_sections(body):
        section_text = f"# {heading}\n{section_body}".strip()
        for chunk_text_value in _chunk_text(section_text, max_chars=max_chars, overlap=overlap):
            chunk_hash = text_hash(chunk_text_value)
            chunk_id_basis = f"{vault_rel_path}|{chunk_counter}|{chunk_hash}"
            stable_chunk_id = hashlib.sha256(chunk_id_basis.encode("utf-8")).hexdigest()
            chunk_metadata = dict(metadata)
            chunk_metadata["id"] = stable_chunk_id
            chunks.append(
                NoteChunk(
                    vault_rel_path=vault_rel_path,
                    heading_path=f"{vault_rel_path}#{heading}",
                    chunk_text=chunk_text_value,
                    chunk_hash=chunk_hash,
                    metadata=chunk_metadata,
                    chunk_index=chunk_counter,
                )
            )
            chunk_counter += 1
    return chunks


class EmbeddingProvider:
    name = "base"

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError


class FallbackEmbeddingProvider(EmbeddingProvider):
    name = "fallback"

    def __init__(self, dimension: int = 64) -> None:
        self.dimension = dimension

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        vectors = [self._embed_one(text) for text in texts]
        return vectors

    def _embed_one(self, text: str) -> list[float]:
        vector = [0.0] * self.dimension
        tokens = re.findall(r"[a-z0-9_]+", text.lower())
        if not tokens:
            return vector
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            for offset in range(0, min(len(digest), self.dimension), 4):
                slot = (offset // 4) % self.dimension
                value = int.from_bytes(digest[offset : offset + 4], "big", signed=False)
                signed = 1.0 if value % 2 else -1.0
                vector[slot] += signed * ((value % 1000) / 1000.0)
        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector
        return [value / norm for value in vector]


class OllamaEmbeddingProvider(EmbeddingProvider):
    name = "ollama"

    def __init__(
        self,
        model: str = "nomic-embed-text",
        endpoint: str = "http://127.0.0.1:11434",
        timeout: float = 10.0,
    ) -> None:
        self.model = model
        self.endpoint = endpoint.rstrip("/")
        self.timeout = timeout

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        try:
            return self._embed_batch(texts)
        except Exception:
            return [self._embed_single(text) for text in texts]

    def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        response = requests.post(
            f"{self.endpoint}/api/embed",
            json={"model": self.model, "input": texts},
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        vectors = payload.get("embeddings")
        if not isinstance(vectors, list) or len(vectors) != len(texts):
            raise RuntimeError("unexpected Ollama embedding payload")
        return [[float(value) for value in vector] for vector in vectors]

    def _embed_single(self, text: str) -> list[float]:
        response = requests.post(
            f"{self.endpoint}/api/embeddings",
            json={"model": self.model, "prompt": text},
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        vector = payload.get("embedding")
        if not isinstance(vector, list):
            raise RuntimeError("unexpected Ollama single embedding payload")
        return [float(value) for value in vector]


def make_embedding_provider(provider_name: str, ollama_model: str | None = None) -> EmbeddingProvider:
    normalized = provider_name.lower()
    if normalized == "ollama":
        return OllamaEmbeddingProvider(model=ollama_model or "nomic-embed-text")
    return FallbackEmbeddingProvider()


def cosine_similarity(lhs: list[float], rhs: list[float]) -> float:
    if not lhs or not rhs or len(lhs) != len(rhs):
        return -1.0
    numerator = sum(left * right for left, right in zip(lhs, rhs))
    left_norm = math.sqrt(sum(left * left for left in lhs))
    right_norm = math.sqrt(sum(right * right for right in rhs))
    if left_norm == 0 or right_norm == 0:
        return -1.0
    return numerator / (left_norm * right_norm)


def load_index_rows(db_dir: Path) -> list[dict[str, Any]]:
    manifest_path = db_dir / INDEX_MANIFEST_NAME
    payload = load_json_file(manifest_path)
    if isinstance(payload, dict):
        rows = payload.get("rows")
        if isinstance(rows, list):
            return [row for row in rows if isinstance(row, dict)]
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    return []


def save_index_rows(
    db_dir: Path,
    rows: list[dict[str, Any]],
    provider_name: str,
    ollama_model: str | None,
) -> None:
    db_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "provider": provider_name,
        "ollama_model": ollama_model,
        "rows": rows,
    }
    write_json_file(db_dir / INDEX_MANIFEST_NAME, payload)
    _sync_native_lancedb(db_dir, rows)


def maybe_clear_index(db_dir: Path) -> None:
    if db_dir.exists():
        shutil.rmtree(db_dir)


def _sync_native_lancedb(db_dir: Path, rows: list[dict[str, Any]]) -> None:
    try:
        import lancedb  # type: ignore
    except Exception:
        return
    db = lancedb.connect(str(db_dir))
    table_rows = []
    for row in rows:
        native_row = dict(row)
        native_row["metadata_json"] = json.dumps(row.get("metadata", {}), ensure_ascii=False, sort_keys=True)
        table_rows.append(native_row)
    db.create_table(INDEX_TABLE_NAME, data=table_rows, mode="overwrite")


def compose_context(rows: list[dict[str, Any]]) -> str:
    blocks: list[str] = []
    for row in rows:
        metadata = row.get("metadata", {})
        header = row.get("heading_path", row.get("vault_rel_path", "UNKNOWN"))
        blocks.append(
            "\n".join(
                [
                    f"## {header}",
                    row.get("chunk_text", ""),
                    f"Pointer: {row.get('vault_rel_path', 'UNKNOWN')}",
                    f"Type: {metadata.get('type', 'UNKNOWN')}",
                ]
            ).strip()
        )
    return "\n\n".join(blocks).strip() + ("\n" if blocks else "")
