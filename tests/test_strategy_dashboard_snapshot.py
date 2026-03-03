import importlib.util
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts/strategy_dashboard_snapshot.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("strategy_dashboard_snapshot_testmod", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = "\n".join(json.dumps(row) for row in rows) + "\n"
    path.write_text(payload, encoding="utf-8")


def test_strategy_dashboard_payload_builds_multi_point_btc_series(tmp_path: Path):
    mod = _load_module()

    start = datetime(2020, 1, 1, 20, 0, tzinfo=timezone.utc)
    rows = []
    for idx in range(140):
        ts = start + timedelta(days=idx)
        rows.append(
            {
                "ts": int(ts.timestamp() * 1000),
                "open": 100 + idx,
                "high": 101 + idx,
                "low": 99 + idx,
                "close": 100 + idx,
                "volume": 1.0,
            }
        )
    _write_jsonl(tmp_path / "data/derived/BTCUSDT/4h/klines.jsonl", rows)

    summary_path = tmp_path / "data/backtests/2026-03-03/run_a/summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(
        json.dumps(
            {
                "run_id": "run_a",
                "total_return": 0.25,
                "cagr": 0.04,
                "sharpe": 1.1,
                "max_drawdown": -0.12,
                "trades_count": 42,
                "win_rate": 0.5,
                "start_ts": "2020-01-01T00:00:00+00:00",
                "end_ts": "2020-05-20T00:00:00+00:00",
            }
        ),
        encoding="utf-8",
    )

    payload = mod.build_strategy_dashboard_payload(tmp_path, now_utc="2026-03-04T00:00:00Z")

    assert payload["schema"] == "strategy_dashboard.v1"
    assert len(payload["series"]) > 100
    assert payload["series"][0]["btc_bh"] == 1.0
    assert payload["series"][0]["hong"] is None
    assert payload["sources"]["btc_bh_curve"]["series_points"] == len(payload["series"])
    assert payload["blend"]["kpis"]["run_id"] == "run_a"


def test_strategy_dashboard_payload_gracefully_handles_missing_btc_source(tmp_path: Path):
    mod = _load_module()

    payload = mod.build_strategy_dashboard_payload(tmp_path, now_utc="2026-03-04T00:00:00Z")

    assert payload["schema"] == "strategy_dashboard.v1"
    assert payload["series"] == []
    assert payload["sources"]["btc_bh_curve"]["path"] is None
    assert any("BTC kline source missing" in note for note in payload["blend"]["notes"])
