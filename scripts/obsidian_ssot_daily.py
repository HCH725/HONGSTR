#!/usr/bin/env python3
"""scripts/obsidian_ssot_daily.py
Export SSOT state snapshots to an Obsidian KB daily note.

Usage:
    python scripts/obsidian_ssot_daily.py [--repo-root /path] [--date YYYY-MM-DD] [--dry-run]

Writes: _local/obsidian_vault/HONGSTR/KB/SSOT/Daily/YYYY-MM-DD.md
State:  (no separate state file; idempotent via content hash in the note itself)

stdlib-only; no external deps.
Exit 0 always (report-only). WARN on missing files logged to stderr.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_REPO_ROOT_DEFAULT = Path(__file__).resolve().parents[1]
_VAULT_REL = Path("_local/obsidian_vault/HONGSTR")
_KB_SSOT_REL = _VAULT_REL / "KB" / "SSOT" / "Daily"

UTC = timezone.utc

_SSOT_FILES = (
    "system_health_latest.json",
    "freshness_table.json",
    "coverage_matrix_latest.json",
    "regime_monitor_latest.json",
    "data_catalog_latest.json",
    "data_catalog_changes_latest.json",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_utc_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any] | None:
    """Load a JSON file; return None and warn if missing/invalid."""
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except (json.JSONDecodeError, OSError) as exc:
        print(f"WARN obsidian_ssot_daily: cannot read {path}: {exc}", file=sys.stderr)
        return None


def _extract_ts(payload: dict[str, Any] | None) -> str | None:
    if not isinstance(payload, dict):
        return None
    for key in ("ts_utc", "generated_utc", "updated_at_utc", "timestamp", "generated_at"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _latest_ts(timestamps: list[str | None]) -> str | None:
    valid = [t for t in timestamps if isinstance(t, str) and t]
    if not valid:
        return None
    return max(valid)  # ISO8601 strings sort lexicographically


def _note_date_from_ts(ts: str | None, fallback: str | None = None) -> str:
    for candidate in (ts, fallback, _now_utc_iso()):
        if candidate and len(candidate) >= 10:
            return candidate[:10]
    return datetime.now(UTC).strftime("%Y-%m-%d")


def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Status derivation
# ---------------------------------------------------------------------------

_STATUS_RANK = {"OK": 0, "WARN": 1, "WARNING": 1, "FAIL": 2, "BLOCKED": 2, "MISSING": 1}


def _rank(status: str | None) -> int:
    return _STATUS_RANK.get((status or "").upper(), 1)


def _status_label(rank: int) -> str:
    if rank >= 2:
        return "FAIL"
    if rank == 1:
        return "WARN"
    return "OK"


def _component_status(payload: dict[str, Any] | None, primary_key: str = "ssot_status") -> str:
    if payload is None:
        return "MISSING"
    for key in (primary_key, "status", "overall"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value.upper()
    return "UNKNOWN"


# ---------------------------------------------------------------------------
# Section builders
# ---------------------------------------------------------------------------

def _section_system_health(payload: dict[str, Any] | None) -> list[str]:
    if payload is None:
        return ["Missing data/state/system_health_latest.json – WARN."]
    bullets: list[str] = []
    top_status = payload.get("ssot_status", payload.get("status", "UNKNOWN"))
    bullets.append(f"Overall: {top_status}")
    components = payload.get("components")
    if isinstance(components, dict):
        for key in sorted(components):
            comp = components[key]
            if not isinstance(comp, dict):
                continue
            status = comp.get("status", "UNKNOWN")
            detail_parts = []
            for dk in ("max_age_h", "age_h", "blocked", "done", "total", "top_reason", "last_check_status"):
                if dk in comp:
                    detail_parts.append(f"{dk}={comp[dk]}")
            detail = f" ({', '.join(detail_parts)})" if detail_parts else ""
            bullets.append(f"  {key}: {status}{detail}")
    ts = _extract_ts(payload)
    if ts:
        bullets.append(f"ts_utc: {ts}")
    return bullets


def _section_freshness(
    freshness: dict[str, Any] | None,
    system_health: dict[str, Any] | None,
) -> list[str]:
    bullets: list[str] = []
    if freshness is None:
        bullets.append("Missing data/state/freshness_table.json – WARN.")
    else:
        rows = freshness.get("rows")
        if isinstance(rows, list):
            total = len(rows)
            non_ok = [r for r in rows if isinstance(r, dict) and r.get("status", "").upper() != "OK"]
            bullets.append(f"Rows total={total} non_ok={len(non_ok)}")
            for r in non_ok[:5]:
                sym = r.get("symbol", "?")
                tf = r.get("tf", "?")
                st = r.get("status", "?")
                bullets.append(f"  {sym}/{tf}: {st}")
            if len(non_ok) > 5:
                bullets.append(f"  … and {len(non_ok) - 5} more non-OK rows")
        ts = _extract_ts(freshness)
        if ts:
            bullets.append(f"ts_utc: {ts}")

    # Brake health surfaced here too
    if isinstance(system_health, dict):
        components = system_health.get("components") or {}
        brake = components.get("brake") or {}
        brake_status = brake.get("status", "UNKNOWN") if isinstance(brake, dict) else "UNKNOWN"
        bullets.append(f"Brake status: {brake_status}")

    return bullets or ["No freshness data available."]


def _section_coverage(payload: dict[str, Any] | None) -> list[str]:
    if payload is None:
        return ["Missing data/state/coverage_matrix_latest.json – WARN."]
    bullets: list[str] = []
    totals = payload.get("totals")
    if isinstance(totals, dict):
        done = totals.get("done", 0)
        blocked = totals.get("blocked", 0)
        rebase = totals.get("rebase", 0)
        in_prog = totals.get("inProgress", 0)
        bullets.append(f"done={done} blocked={blocked} rebase={rebase} inProgress={in_prog}")
    rows = payload.get("rows")
    if isinstance(rows, list):
        non_pass = [
            r for r in rows
            if isinstance(r, dict) and r.get("status", "").upper() not in ("OK", "PASS")
        ]
        if non_pass:
            sample = non_pass[0]
            bullets.append(
                f"First non-pass: {sample.get('symbol', '?')} "
                f"{sample.get('tf', '?')} status={sample.get('status', '?')}"
            )
            if len(non_pass) > 1:
                bullets.append(f"… {len(non_pass) - 1} more non-pass rows")
        else:
            bullets.append("All coverage rows PASS.")
    ts = _extract_ts(payload)
    if ts:
        bullets.append(f"ts_utc: {ts}")
    return bullets


def _section_regime(payload: dict[str, Any] | None) -> list[str]:
    if payload is None:
        return ["Missing data/state/regime_monitor_latest.json – WARN."]
    bullets: list[str] = []
    overall = payload.get("overall", "UNKNOWN")
    bullets.append(f"Overall: {overall}")
    reasons = payload.get("reason") or []
    if isinstance(reasons, list):
        for r in reasons[:3]:
            bullets.append(f"  Reason: {r}")
    elif isinstance(reasons, str):
        bullets.append(f"  Reason: {reasons}")
    suggestion = payload.get("suggestion")
    if suggestion:
        bullets.append(f"Suggestion: {suggestion}")
    ts = _extract_ts(payload)
    if ts:
        bullets.append(f"ts_utc: {ts}")
    return bullets


def _section_data_catalog(
    catalog: dict[str, Any] | None,
    changes: dict[str, Any] | None,
) -> list[str]:
    bullets: list[str] = []
    if catalog is None and changes is None:
        return ["data_catalog files not found – WARN."]

    if isinstance(catalog, dict):
        datasets = catalog.get("datasets") or catalog.get("entries") or []
        if isinstance(datasets, list):
            bullets.append(f"Catalog datasets: {len(datasets)}")
        ts = _extract_ts(catalog)
        if ts:
            bullets.append(f"Catalog ts_utc: {ts}")

    if isinstance(changes, dict):
        added = changes.get("added") or []
        removed = changes.get("removed") or []
        modified = changes.get("modified") or []
        total_changes = len(added) + len(removed) + len(modified)
        if total_changes == 0:
            bullets.append("No catalog changes since last run.")
        else:
            if added:
                bullets.append(f"Added ({len(added)}): {', '.join(str(a) for a in added[:5])}")
            if removed:
                bullets.append(f"Removed ({len(removed)}): {', '.join(str(r) for r in removed[:5])}")
            if modified:
                bullets.append(f"Modified ({len(modified)}): {', '.join(str(m) for m in modified[:5])}")
        ts = _extract_ts(changes)
        if ts:
            bullets.append(f"Changes ts_utc: {ts}")
    elif changes is None:
        bullets.append("data_catalog_changes_latest.json not found.")

    return bullets or ["No catalog data available."]


def _section_action_hints(
    system_health: dict[str, Any] | None,
    coverage: dict[str, Any] | None,
    regime: dict[str, Any] | None,
) -> list[str]:
    hints: list[str] = []

    # System health hint
    if isinstance(system_health, dict):
        status = system_health.get("ssot_status", system_health.get("status", ""))
        if status and status.upper() not in ("OK", ""):
            hints.append(f"SystemHealth is {status} → review component statuses and resolve blockers.")

    # Coverage hint
    if isinstance(coverage, dict):
        totals = coverage.get("totals") or {}
        if isinstance(totals, dict) and totals.get("blocked", 0):
            hints.append(
                f"Coverage has {totals['blocked']} blocked row(s) → investigate before promotion."
            )

    # Regime hint
    if isinstance(regime, dict):
        overall = (regime.get("overall") or "").upper()
        if overall not in ("OK", ""):
            hints.append(f"Regime is {overall} → pause promotions until signals normalize.")
            suggestion = regime.get("suggestion")
            if suggestion:
                hints.append(f"  Suggestion: {suggestion}")

    if not hints:
        hints.append("All systems nominal – no immediate action required.")

    hints.append("Refresh command: bash scripts/refresh_state.sh")
    return hints


# ---------------------------------------------------------------------------
# Frontmatter rendering (minimal, stable)
# ---------------------------------------------------------------------------

def _render_frontmatter(fields: dict[str, Any]) -> str:
    lines = ["---"]
    for key, value in fields.items():
        if isinstance(value, list):
            if not value:
                lines.append(f"{key}: []")
            else:
                lines.append(f"{key}:")
                for item in value:
                    lines.append(f'  - "{item}"')
        elif isinstance(value, dict):
            lines.append(f"{key}:")
            for dk, dv in value.items():
                lines.append(f'  {dk}: "{dv}"')
        elif value is None:
            lines.append(f"{key}: null")
        elif isinstance(value, bool):
            lines.append(f"{key}: {'true' if value else 'false'}")
        else:
            # Strings: quote if needed
            sv = str(value)
            if any(c in sv for c in (':', '#', '[', ']', '{', '}', '|', '>', '!')):
                lines.append(f'{key}: "{sv}"')
            else:
                lines.append(f"{key}: {sv}")
    lines.append("---")
    return "\n".join(lines)


def _render_section(heading: str, bullets: list[str]) -> str:
    lines = [f"## {heading}", ""]
    for b in bullets:
        if b.startswith("  "):
            lines.append(f"  - {b.strip()}")
        else:
            lines.append(f"- {b}")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main export logic
# ---------------------------------------------------------------------------

def export_ssot_daily(
    repo_root: Path,
    date_override: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Export SSOT daily note. Returns {"written": bool, "path": str, "status": str}."""
    state_dir = repo_root / "data" / "state"
    kb_dir = repo_root / _KB_SSOT_REL

    warnings: list[str] = []

    # ── Load all SSOT files gracefully ───────────────────────────────────────
    def _load(filename: str) -> dict[str, Any] | None:
        p = state_dir / filename
        d = _load_json(p)
        if d is None:
            warnings.append(f"WARN missing_or_invalid: {filename}")
        return d

    system_health = _load("system_health_latest.json")
    freshness = _load("freshness_table.json")
    coverage = _load("coverage_matrix_latest.json")
    regime = _load("regime_monitor_latest.json")
    catalog = _load("data_catalog_latest.json")
    changes = _load("data_catalog_changes_latest.json")

    all_missing = all(
        x is None for x in (system_health, freshness, coverage, regime, catalog, changes)
    )
    if all_missing:
        msg = "WARN obsidian_ssot_daily: no SSOT files found – skipping write"
        print(msg, file=sys.stderr)
        return {"written": False, "reason": "all_files_missing", "status": "WARN", "warnings": warnings}

    # ── Determine date and ts_utc ─────────────────────────────────────────────
    ts_utc = _latest_ts([
        _extract_ts(system_health),
        _extract_ts(freshness),
        _extract_ts(coverage),
        _extract_ts(regime),
        _extract_ts(catalog),
        _extract_ts(changes),
    ]) or _now_utc_iso()

    note_date = date_override or _note_date_from_ts(ts_utc)

    # ── Compute component statuses ────────────────────────────────────────────
    comp_health = _component_status(system_health, "ssot_status")
    comp_fresh = "MISSING" if freshness is None else (
        "WARN" if any(
            r.get("status", "OK").upper() != "OK"
            for r in (freshness.get("rows") or [])
            if isinstance(r, dict)
        ) else "OK"
    )
    comp_cov = "MISSING" if coverage is None else (
        "FAIL" if (coverage.get("totals") or {}).get("blocked", 0) > 0 else "OK"
    )
    comp_regime = _component_status(regime, "overall")
    comp_catalog = "MISSING" if (catalog is None and changes is None) else "OK"

    components = {
        "system_health": comp_health,
        "freshness": comp_fresh,
        "coverage": comp_cov,
        "regime": comp_regime,
        "data_catalog": comp_catalog,
    }

    overall_rank = max(_rank(v) for v in components.values())
    status_summary = _status_label(overall_rank)

    # ── Build ssot_refs ───────────────────────────────────────────────────────
    ssot_refs = [
        f"data/state/{f}" for f in _SSOT_FILES
        if (state_dir / f).exists()
    ]

    # ── Build frontmatter ─────────────────────────────────────────────────────
    frontmatter: dict[str, Any] = {
        "type": "daily_ssot",
        "date": note_date,
        "ts_utc": ts_utc,
        "status_summary": status_summary,
        "components": components,
        "ssot_refs": ssot_refs,
    }

    # ── Build body sections ───────────────────────────────────────────────────
    sections = [
        ("SystemHealth", _section_system_health(system_health)),
        ("Freshness", _section_freshness(freshness, system_health)),
        ("Coverage", _section_coverage(coverage)),
        ("RegimeSignal", _section_regime(regime)),
        ("DataCatalog Changes", _section_data_catalog(catalog, changes)),
        ("Action Hints", _section_action_hints(system_health, coverage, regime)),
    ]

    # ── Render full note ──────────────────────────────────────────────────────
    body_lines: list[str] = [
        _render_frontmatter(frontmatter),
        "",
        f"# SSOT Daily — {note_date}",
        "",
    ]
    for heading, bullets in sections:
        body_lines.append(_render_section(heading, bullets))

    note_content = "\n".join(body_lines).rstrip() + "\n"

    # ── Idempotency check: embed hash in note and compare ─────────────────────
    content_hash = _content_hash(note_content)
    # Re-render with hash embedded (stable: hash is of content without itself)
    # We do NOT embed hash in the note; we store it via file comparison.
    note_path = kb_dir / f"{note_date}.md"

    if note_path.exists():
        existing = note_path.read_text(encoding="utf-8")
        if existing == note_content:
            return {
                "written": False,
                "reason": "unchanged",
                "path": str(note_path),
                "status": "OK",
                "date": note_date,
                "warnings": warnings,
            }

    if dry_run:
        return {
            "written": False,
            "reason": "dry_run",
            "path": str(note_path),
            "status": status_summary,
            "date": note_date,
            "warnings": warnings,
            "content_hash": content_hash,
        }

    # ── Atomic write ──────────────────────────────────────────────────────────
    note_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = note_path.with_suffix(".tmp")
    tmp_path.write_text(note_content, encoding="utf-8")
    tmp_path.replace(note_path)

    return {
        "written": True,
        "path": str(note_path),
        "status": status_summary,
        "date": note_date,
        "content_hash": content_hash,
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--repo-root",
        type=Path,
        default=_REPO_ROOT_DEFAULT,
        help="Repo root path (default: auto-detected)",
    )
    p.add_argument(
        "--date",
        default=None,
        help="Override note date (YYYY-MM-DD); default: derived from SSOT ts_utc",
    )
    p.add_argument("--dry-run", action="store_true", help="Compute without writing")
    return p.parse_args()


def main() -> int:
    args = _parse_args()
    result = export_ssot_daily(
        repo_root=args.repo_root,
        date_override=args.date,
        dry_run=args.dry_run,
    )
    for w in result.get("warnings", []):
        print(w, file=sys.stderr)
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
