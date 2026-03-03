import importlib.util
import json
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts/state_atomic/data_catalog_scan.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("data_catalog_scan_testmod", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _manifest(dataset_id: str, metrics: list[str], *, notes: str = "") -> dict:
    return {
        "dataset_id": dataset_id,
        "schema_version": "v1",
        "producer": "scripts/futures_metrics_fetch.py",
        "cadence": "daily_rolling",
        "path_patterns": {
            "root": f"data/derived/{dataset_id}",
            "template": f"data/derived/{dataset_id}/{{symbol}}/{{metric}}/period={{period}}/{{partition}}.jsonl",
        },
        "symbols": ["BTCUSDT", "ETHUSDT"],
        "metrics": metrics,
        "periods": ["5m"],
        "sources": [{"name": "binance_futures_public", "endpoints": ["/fapi/v1/fundingRate"]}],
        "provenance": {"generated_utc": "2026-03-03T00:00:00Z", "code_ref": "abc123"},
        "notes": notes,
    }


def test_catalog_diff_handles_add_update_remove():
    mod = _load_module()

    prev_catalog = {
        "ts_utc": "2026-03-03T00:00:00Z",
        "datasets": [
            _manifest("futures_metrics", ["funding_rate", "premium_index"]),
            _manifest("legacy_feed", ["legacy_metric"]),
        ],
    }
    current_catalog = {
        "ts_utc": "2026-03-04T00:00:00Z",
        "datasets": [
            _manifest("futures_metrics", ["funding_rate", "open_interest_hist", "premium_index"]),
            _manifest("macro_calendar", ["event_count"], notes="new dataset"),
        ],
    }

    changes = mod.build_catalog_changes(prev_catalog, current_catalog, ts_utc="2026-03-04T00:00:00Z")

    assert changes["prev_ts_utc"] == "2026-03-03T00:00:00Z"
    assert changes["added_datasets"] == [
        {
            "dataset_id": "macro_calendar",
            "summary": "dataset added: 1 metrics, 2 symbols, 5m",
        }
    ]
    assert changes["removed_datasets"] == [
        {
            "dataset_id": "legacy_feed",
            "summary": "dataset removed: 1 metrics, 2 symbols, 5m",
        }
    ]
    assert len(changes["updated_datasets"]) == 1
    updated = changes["updated_datasets"][0]
    assert updated["dataset_id"] == "futures_metrics"
    assert updated["fields_changed"] == ["metrics"]
    assert updated["summary"] == "updated fields: metrics"


def test_scan_manifest_dir_skips_bad_files(tmp_path: Path):
    mod = _load_module()
    manifest_dir = tmp_path / "reports" / "state_atomic" / "manifests"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    (manifest_dir / "good.json").write_text(json.dumps(_manifest("futures_metrics", ["funding_rate"])), encoding="utf-8")
    (manifest_dir / "broken.json").write_text("{not-json", encoding="utf-8")
    (manifest_dir / "invalid.json").write_text(json.dumps({"dataset_id": "oops"}), encoding="utf-8")

    payload = mod.scan_manifest_dir(manifest_dir)

    assert [row["dataset_id"] for row in payload["datasets"]] == ["futures_metrics"]
    assert len(payload["warnings"]) == 2
    assert payload["skipped_dataset_ids"] == ["broken", "invalid"]
