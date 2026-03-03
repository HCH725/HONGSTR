import importlib.util
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts/futures_metrics_lib.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("futures_metrics_lib_sanitize_testmod", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_sanitize_reason_clears_error_text_for_ok_status():
    mod = _load_module()

    assert (
        mod.sanitize_coverage_reason("OK", "[Errno 8] nodename nor servname provided, or not known")
        == ""
    )


def test_sanitize_reason_keeps_error_text_for_warn_status():
    mod = _load_module()

    reason = "[Errno 8] nodename nor servname provided, or not known"
    assert mod.sanitize_coverage_reason("WARN", reason) == reason


def test_sanitize_reason_keeps_snapshot_only_marker_for_ok_status():
    mod = _load_module()

    assert mod.sanitize_coverage_reason("OK", "snapshot_only_endpoint") == "snapshot_only_endpoint"


def test_compose_coverage_row_drops_stale_error_reason_after_recovery(tmp_path):
    mod = _load_module()

    row = mod.compose_coverage_row(
        repo_root=tmp_path,
        symbol="BTCUSDT",
        metric="funding_rate",
        existing_row={
            "status": "FAIL",
            "reason": "[Errno 8] nodename nor servname provided, or not known",
        },
        status="OK",
        reason="",
    )

    assert row["status"] == "OK"
    assert row["reason"] == ""
