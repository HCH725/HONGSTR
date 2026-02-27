import json
from pathlib import Path

from research.loop.regime_timeline import (
    load_regime_timeline_policy,
    resolve_regime_context,
    resolve_regime_window,
)


def _write_policy(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_resolve_window_end_exclusive_boundary(tmp_path: Path):
    policy_path = tmp_path / "regime_timeline.json"
    _write_policy(
        policy_path,
        {
            "regimes": {
                "bull": [
                    {"start": "2026-01-01T00:00:00Z", "end": "2026-02-01T00:00:00Z"},
                    {"start": "2026-02-01T00:00:00Z", "end": "2026-03-01T00:00:00Z"},
                ],
                "bear": [],
                "sideways": [],
            }
        },
    )

    # End-exclusive: as_of == previous end should map to the second interval.
    window = resolve_regime_window("BULL", "2026-02-01T00:00:00Z", policy_path=policy_path)
    assert window == ("2026-02-01T00:00:00Z", "2026-03-01T00:00:00Z")


def test_load_policy_dedupes_overlap(tmp_path: Path):
    policy_path = tmp_path / "regime_timeline.json"
    _write_policy(
        policy_path,
        {
            "regimes": {
                "bull": [
                    {"start": "2026-01-01T00:00:00Z", "end": "2026-02-01T00:00:00Z"},
                    {"start": "2026-01-15T00:00:00Z", "end": "2026-02-15T00:00:00Z"},
                ],
                "bear": [],
                "sideways": [],
            }
        },
    )

    loaded = load_regime_timeline_policy(policy_path)
    assert loaded["status"] == "WARN"
    assert len(loaded["regimes"]["BULL"]) == 1
    assert any("bull_overlap" in msg for msg in loaded["warnings"])


def test_resolve_window_deterministic_for_each_regime(tmp_path: Path):
    policy_path = tmp_path / "regime_timeline.json"
    _write_policy(
        policy_path,
        {
            "regimes": {
                "bull": [{"start": "2026-01-01T00:00:00Z", "end": "2026-04-01T00:00:00Z"}],
                "bear": [{"start": "2025-07-01T00:00:00Z", "end": "2025-10-01T00:00:00Z"}],
                "sideways": [{"start": "2025-10-01T00:00:00Z", "end": "2026-01-01T00:00:00Z"}],
            }
        },
    )

    assert resolve_regime_window("BULL", "2026-02-15T00:00:00Z", policy_path=policy_path) == (
        "2026-01-01T00:00:00Z",
        "2026-04-01T00:00:00Z",
    )
    assert resolve_regime_window("BEAR", "2025-08-15T00:00:00Z", policy_path=policy_path) == (
        "2025-07-01T00:00:00Z",
        "2025-10-01T00:00:00Z",
    )
    assert resolve_regime_window("SIDEWAYS", "2025-12-15T00:00:00Z", policy_path=policy_path) == (
        "2025-10-01T00:00:00Z",
        "2026-01-01T00:00:00Z",
    )


def test_resolve_context_missing_policy_graceful_fallback(tmp_path: Path):
    missing = tmp_path / "not_found.json"
    ctx = resolve_regime_context("BULL", as_of_utc="2026-02-15T00:00:00Z", policy_path=missing)
    assert ctx["status"] == "WARN"
    assert ctx["requested"] == "BULL"
    assert ctx["applied"] == "ALL"
    assert ctx["window_start_utc"] is None
    assert ctx["window_end_utc"] is None
