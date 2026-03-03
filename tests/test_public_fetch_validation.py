import importlib.util
import json
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
MANIFEST_SCRIPT = REPO / "scripts/state_atomic/okx_bitfinex_public_manifest.py"
SNAPSHOTS_SCRIPT = REPO / "scripts/state_snapshots.py"
EMPTY_ARRAY_FIXTURE = REPO / "tests/fixtures/public_fetch/empty_array.json"
OKX_SAMPLE_FIXTURE = REPO / "tests/fixtures/public_fetch/okx_open_interest_sample.json"


def _load_module(name: str, script_path: Path):
    spec = importlib.util.spec_from_file_location(name, script_path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_empty_array_fixture_is_valid_and_coverage_marks_warn():
    sys.path.insert(0, str((REPO / "scripts").resolve()))
    manifest_mod = _load_module("okx_bfx_manifest_testmod", MANIFEST_SCRIPT)
    snapshots_mod = _load_module("state_snapshots_public_fetch_testmod", SNAPSHOTS_SCRIPT)

    empty_payload = json.loads(EMPTY_ARRAY_FIXTURE.read_text(encoding="utf-8"))
    row = manifest_mod.build_coverage_row(
        dataset="liquidations_latest",
        key="latest",
        payload=empty_payload,
        latest_utc="2026-03-04T00:00:00Z",
        source_path="data/derived/bitfinex/public/liquidations_latest/latest/20260304_000000.json",
        request_path="/v2/liquidations/hist",
    )

    assert row["rows"] == 0
    assert row["status"] == "WARN"
    assert row["reason"] == "empty array from endpoint"

    normalized = snapshots_mod._normalize_public_market_coverage(
        {"ts_utc": "2026-03-04T00:00:00Z", "rows": [row]},
        "2026-03-04T00:00:00Z",
        "bitfinex_public",
    )
    assert normalized["rows"][0]["status"] == "WARN"
    assert normalized["rows"][0]["rows"] == 0
    assert normalized["rows"][0]["reason"] == "empty array from endpoint"


def test_okx_sample_fixture_counts_rows_without_crash():
    manifest_mod = _load_module("okx_bfx_manifest_testmod_sample", MANIFEST_SCRIPT)
    payload = json.loads(OKX_SAMPLE_FIXTURE.read_text(encoding="utf-8"))

    row = manifest_mod.build_coverage_row(
        dataset="open_interest",
        key="BTC-USDT-SWAP",
        payload=payload,
        latest_utc="2026-03-04T00:00:00Z",
        source_path="data/derived/okx/public/open_interest/BTC-USDT-SWAP/20260304_000000.json",
        request_path="/api/v5/public/open-interest",
    )

    assert row["rows"] == 1
    assert row["status"] == "OK"
    assert row["reason"] == ""
