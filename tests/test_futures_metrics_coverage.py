import importlib.util
import sys
from datetime import datetime, timezone
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts/futures_metrics_lib.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("futures_metrics_lib_testmod", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _sample_row(symbol: str, metric: str, ts_utc: str, value_key: str = "value") -> dict:
    return {
        "symbol": symbol,
        "metric": metric,
        "period": "5m",
        "event_time_ms": int(
            datetime.fromisoformat(ts_utc.replace("Z", "+00:00")).timestamp() * 1000
        ),
        "ts_utc": ts_utc,
        value_key: "1",
    }


def test_write_metric_rows_and_scan_are_deduped(tmp_path):
    mod = _load_module()
    first = _sample_row("BTCUSDT", "funding_rate", "2026-03-03T00:00:00Z", "funding_rate")
    second = _sample_row("BTCUSDT", "funding_rate", "2026-03-03T08:00:00Z", "funding_rate")

    added_first = mod.write_metric_rows(tmp_path, "BTCUSDT", "funding_rate", [first, second])
    added_second = mod.write_metric_rows(tmp_path, "BTCUSDT", "funding_rate", [first])
    stats = mod.scan_metric_storage(tmp_path, "BTCUSDT", "funding_rate")

    assert added_first == 2
    assert added_second == 0
    assert stats["rows"] == 2
    assert stats["earliest_utc"] == "2026-03-03T00:00:00Z"
    assert stats["latest_utc"] == "2026-03-03T08:00:00Z"


def test_compose_coverage_row_keeps_probed_earliest_over_local_storage(tmp_path):
    mod = _load_module()
    row = _sample_row("ETHUSDT", "open_interest_hist", "2026-03-03T00:05:00Z", "sum_open_interest")
    mod.write_metric_rows(tmp_path, "ETHUSDT", "open_interest_hist", [row])

    coverage = mod.compose_coverage_row(
        repo_root=tmp_path,
        symbol="ETHUSDT",
        metric="open_interest_hist",
        existing_row={"earliest_utc": "2020-01-15T00:00:00Z", "status": "OK"},
        status="OK",
        reason="",
    )

    assert coverage["rows"] == 1
    assert coverage["earliest_utc"] == "2020-01-15T00:00:00Z"
    assert coverage["storage_earliest_utc"] == "2026-03-03T00:05:00Z"
    assert coverage["latest_utc"] == "2026-03-03T00:05:00Z"


def test_checkpoint_resume_starts_after_saved_window():
    mod = _load_module()
    checkpoint = {"checkpoints": {}}
    default_start = datetime(2020, 1, 1, tzinfo=timezone.utc)

    assert mod.next_window_start(checkpoint, "BNBUSDT", "funding_rate", default_start) == default_start

    mod.update_checkpoint_entry(
        checkpoint_payload=checkpoint,
        symbol="BNBUSDT",
        metric="funding_rate",
        next_start=datetime(2020, 1, 8, tzinfo=timezone.utc),
        last_end=datetime(2020, 1, 8, tzinfo=timezone.utc),
    )

    resumed = mod.next_window_start(checkpoint, "BNBUSDT", "funding_rate", default_start)
    windows = mod.build_windows(
        resumed,
        datetime(2020, 1, 20, tzinfo=timezone.utc),
        chunk_days=7,
    )

    assert resumed == datetime(2020, 1, 8, tzinfo=timezone.utc)
    assert windows[0][0] == datetime(2020, 1, 8, tzinfo=timezone.utc)
    assert windows[0][1] == datetime(2020, 1, 15, tzinfo=timezone.utc)
