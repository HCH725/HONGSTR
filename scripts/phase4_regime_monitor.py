#!/usr/bin/env python3
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

REPO = Path(__file__).parent.parent
PHASE3_RESULTS = REPO / "reports/strategy_research/phase3/phase3_results.json"
REGIME_POLICY_PATH = REPO / "research/policy/regime_thresholds.json"
ATOMIC_STATE_DIR = REPO / "reports/state_atomic"
REPORT_DIR = REPO / "reports/strategy_research/phase4"
PHASE3_THRESHOLD_VERSION = "phase4_regime_monitor.phase3_dynamic_v1"


def resolve_latest_run():
    """
    Search for the latest 'Full Run' (containing both selection.json and summary.json).
    Fallback to the latest 'Fragment Run' (any summary.json) if no Full Run exists.
    """
    backtest_root = REPO / "data/backtests"
    if not backtest_root.exists():
        return None, None, "no_data"

    all_summaries = list(backtest_root.glob("**/summary.json"))
    if not all_summaries:
        return None, None, "no_summary_found"

    # Sort all summaries by mtime to find the latest overall
    all_summaries.sort(key=lambda p: p.stat().st_mtime, reverse=True)

    # 1. Search for a Full Run
    for summary_p in all_summaries:
        run_dir = summary_p.parent
        if (run_dir / "selection.json").exists():
            return run_dir, summary_p, "full_run"

    # 2. Fallback to the latest fragment run
    latest_fragment = all_summaries[0]
    return latest_fragment.parent, latest_fragment, "fallback_fragment"


def compute_thresholds(phase3_data):
    walks = phase3_data.get("walks", [])
    if not walks:
        return None

    sharpes = [w["sharpe"] for w in walks]
    mdds = [w["mdd"] for w in walks]
    trades = [w["trades"] for w in walks]

    sharpe_median = np.median(sharpes)
    sharpe_iqr = np.percentile(sharpes, 75) - np.percentile(sharpes, 25)
    sharpe_p20 = np.percentile(sharpes, 20)
    sharpe_p40 = np.percentile(sharpes, 40)

    trade_median = np.median(trades)

    # MDD is negative, so p95 is the most negative (worst risk)
    mdd_p80 = np.percentile(mdds, 20)  # 20th percentile is more negative than 80th
    mdd_p95 = np.percentile(mdds, 5)  # 5th percentile is the extreme tail risk

    return {
        "sharpe": {
            "median": sharpe_median,
            "iqr": sharpe_iqr,
            "p20": sharpe_p20,
            "p40": sharpe_p40,
            "warn": sharpe_median - 0.5 * sharpe_iqr if sharpe_iqr > 0 else sharpe_p40,
            "fail": sharpe_median - 1.0 * sharpe_iqr if sharpe_iqr > 0 else sharpe_p20,
        },
        "trades": {
            "median": trade_median,
            "warn_gate": trade_median * 0.5,
        },
        "mdd": {
            "p80": mdd_p80,
            "p95": mdd_p95,
        },
    }


def compute_versioned_sha(raw_bytes: bytes, version_label: str) -> str:
    digest = hashlib.sha256()
    digest.update(version_label.encode("utf-8"))
    digest.update(b"\n")
    digest.update(raw_bytes)
    return digest.hexdigest()


def _safe_rel_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO)).replace("\\", "/")
    except Exception:
        return str(path).replace("\\", "/")


def _parse_iso_utc(value):
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    try:
        normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
        dt = datetime.fromisoformat(normalized)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        return dt
    except Exception:
        return None


def _calibration_status(last_calibrated_utc, stale_after_days, now_utc_dt):
    dt = _parse_iso_utc(last_calibrated_utc)
    if dt is None:
        return "UNKNOWN"
    age_days = (now_utc_dt - dt).total_seconds() / 86400.0
    if age_days <= max(1, int(stale_after_days)):
        return "OK"
    return "STALE"


def load_regime_policy(now_utc_dt):
    base = {
        "available": False,
        "source_path": _safe_rel_path(REGIME_POLICY_PATH),
        "policy_sha": None,
        "policy_version": "phase4_regime_monitor.policy_missing",
        "mdd_warn": None,
        "mdd_fail": None,
        "rationale": "Regime threshold policy unavailable; fallback to Phase 3 dynamic baseline.",
        "last_calibrated_utc": None,
        "calibration_status": "UNKNOWN",
    }
    if not REGIME_POLICY_PATH.exists():
        return base

    try:
        raw = REGIME_POLICY_PATH.read_bytes()
        policy = json.loads(raw.decode("utf-8"))
        if not isinstance(policy, dict):
            return base
    except Exception:
        return base

    thresholds = policy.get("thresholds", {}) if isinstance(policy.get("thresholds"), dict) else {}
    calibration = policy.get("calibration", {}) if isinstance(policy.get("calibration"), dict) else {}

    try:
        mdd_warn = float(thresholds.get("warn"))
        mdd_fail = float(thresholds.get("fail"))
    except Exception:
        return base
    if mdd_fail > mdd_warn:
        mdd_fail = mdd_warn

    stale_after_days = int(float(calibration.get("stale_after_days", 8) or 8))
    last_calibrated_utc = calibration.get("last_calibrated_utc")
    explicit_status = str(calibration.get("calibration_status") or "").upper().strip()
    derived_status = _calibration_status(last_calibrated_utc, stale_after_days, now_utc_dt)
    cal_status = explicit_status if explicit_status in {"OK", "STALE", "UNKNOWN"} else derived_status
    if cal_status == "UNKNOWN":
        cal_status = derived_status

    policy_name = str(policy.get("name") or "regime_thresholds_policy")
    return {
        "available": True,
        "source_path": _safe_rel_path(REGIME_POLICY_PATH),
        "policy_sha": compute_versioned_sha(raw, policy_name),
        "policy_version": policy_name,
        "mdd_warn": mdd_warn,
        "mdd_fail": mdd_fail,
        "rationale": str(policy.get("rationale") or "Regime thresholds loaded from approved policy."),
        "last_calibrated_utc": last_calibrated_utc,
        "calibration_status": cal_status,
    }


def _severity_rank(level):
    if level == "FAIL":
        return 2
    if level == "WARN":
        return 1
    return 0


def evaluate(current, thresholds, *, phase3_source, mdd_source):
    status = "OK"
    reason_events = []
    order_counter = 0

    try:
        curr_sharpe = float(current.get("sharpe", 0.0))
    except Exception:
        curr_sharpe = 0.0
    try:
        curr_trades = int(float(current.get("trades_count", 0)))
    except Exception:
        curr_trades = 0
    try:
        curr_mdd = float(current.get("max_drawdown", 0.0))
    except Exception:
        curr_mdd = 0.0

    def add_event(
        level,
        message,
        metric,
        threshold_value,
        observed_value,
        comparator,
        rationale,
        *,
        source_path,
        policy_sha,
        policy_version,
    ):
        nonlocal status, order_counter
        if level == "FAIL":
            status = "FAIL"
        elif status != "FAIL":
            status = "WARN"
        reason_events.append(
            {
                "level": level,
                "message": message,
                "metric": metric,
                "threshold_value": threshold_value,
                "observed_value": observed_value,
                "comparator": comparator,
                "rationale": rationale,
                "threshold_source_path": source_path,
                "threshold_policy_sha": policy_sha,
                "threshold_policy_version": policy_version,
                "order": order_counter,
            }
        )
        order_counter += 1

    # 1. Sharpe Check (phase3 dynamic)
    s_warn = thresholds["sharpe"]["warn"]
    s_fail = thresholds["sharpe"]["fail"]

    if curr_sharpe < s_fail:
        add_event(
            "FAIL",
            f"Sharpe ({curr_sharpe:.3f}) < FAIL threshold ({s_fail:.3f})",
            "sharpe",
            s_fail,
            curr_sharpe,
            "<",
            "Current OOS Sharpe dropped below FAIL line derived from Phase 3 distribution.",
            source_path=phase3_source["path"],
            policy_sha=phase3_source["sha"],
            policy_version=phase3_source["version"],
        )
    elif curr_sharpe < s_warn:
        add_event(
            "WARN",
            f"Sharpe ({curr_sharpe:.3f}) < WARN threshold ({s_warn:.3f})",
            "sharpe",
            s_warn,
            curr_sharpe,
            "<",
            "Current OOS Sharpe slipped below WARN line from Phase 3 IQR baseline.",
            source_path=phase3_source["path"],
            policy_sha=phase3_source["sha"],
            policy_version=phase3_source["version"],
        )

    # 2. Trade Count Gate (phase3 dynamic)
    t_gate = thresholds["trades"]["warn_gate"]
    if curr_trades < t_gate:
        add_event(
            "WARN",
            f"Trade Count ({curr_trades}) < 50% of Phase 3 median ({t_gate:.0f}) - Possible regime shift or data gap",
            "trades_count",
            t_gate,
            curr_trades,
            "<",
            "Trade frequency is below half of Phase 3 median; could indicate data gap or market regime shift.",
            source_path=phase3_source["path"],
            policy_sha=phase3_source["sha"],
            policy_version=phase3_source["version"],
        )

    # 3. MDD Risk Check (policy-preferred, fallback phase3)
    m_warn = float(mdd_source["warn"])
    m_fail = float(mdd_source["fail"])

    if curr_mdd < m_fail:
        add_event(
            "FAIL",
            f"MDD ({curr_mdd:.2%}) < FAIL threshold ({m_fail:.2%}) - Extreme risk detected",
            "max_drawdown",
            m_fail,
            curr_mdd,
            "<",
            f"Max drawdown breached FAIL threshold from {mdd_source['label']}.",
            source_path=mdd_source["path"],
            policy_sha=mdd_source["sha"],
            policy_version=mdd_source["version"],
        )
    elif curr_mdd < m_warn:
        add_event(
            "WARN",
            f"MDD ({curr_mdd:.2%}) < WARN threshold ({m_warn:.2%}) - Risk elevated",
            "max_drawdown",
            m_warn,
            curr_mdd,
            "<",
            f"Max drawdown crossed WARN threshold from {mdd_source['label']}.",
            source_path=mdd_source["path"],
            policy_sha=mdd_source["sha"],
            policy_version=mdd_source["version"],
        )

    if not reason_events:
        return status, ["All metrics within configured comfort zone."], None

    sorted_events = sorted(reason_events, key=lambda r: (-_severity_rank(r["level"]), r["order"]))
    reasons = [event["message"] for event in sorted_events]
    primary = sorted_events[0]
    primary_threshold = {
        "metric": primary["metric"],
        "level": primary["level"],
        "threshold_value": primary["threshold_value"],
        "observed_value": primary["observed_value"],
        "comparator": primary["comparator"],
        "rationale": primary["rationale"],
        "threshold_source_path": primary["threshold_source_path"],
        "threshold_policy_sha": primary["threshold_policy_sha"],
        "threshold_policy_version": primary["threshold_policy_version"],
    }
    return status, reasons, primary_threshold


def main():
    if not PHASE3_RESULTS.exists():
        print(f"Error: {PHASE3_RESULTS} not found.")
        sys.exit(0)  # report_only, exit 0

    now_dt = datetime.now(timezone.utc)
    regime_policy = load_regime_policy(now_dt)

    phase3_raw = PHASE3_RESULTS.read_bytes()
    with open(PHASE3_RESULTS, "r") as f:
        phase3_data = json.load(f)
    phase3_sha = compute_versioned_sha(phase3_raw, PHASE3_THRESHOLD_VERSION)
    phase3_path = str(PHASE3_RESULTS.relative_to(REPO))

    thresholds = compute_thresholds(phase3_data)
    if not thresholds:
        print("Error: Could not compute thresholds from Phase 3 data.")
        sys.exit(0)

    phase3_source = {
        "path": phase3_path,
        "sha": phase3_sha,
        "version": PHASE3_THRESHOLD_VERSION,
    }
    mdd_source = {
        "warn": thresholds["mdd"]["p80"],
        "fail": thresholds["mdd"]["p95"],
        "path": phase3_path,
        "sha": phase3_sha,
        "version": PHASE3_THRESHOLD_VERSION,
        "label": "Phase 3 dynamic baseline",
    }
    if regime_policy["available"]:
        mdd_source = {
            "warn": regime_policy["mdd_warn"],
            "fail": regime_policy["mdd_fail"],
            "path": regime_policy["source_path"],
            "sha": regime_policy["policy_sha"],
            "version": regime_policy["policy_version"],
            "label": "approved regime policy",
        }

    latest_run_dir, latest_summary_p, source_reason = resolve_latest_run()
    if not latest_summary_p:
        print(f"Error: {source_reason}")
        sys.exit(0)

    with open(latest_summary_p, "r") as f:
        current_data = json.load(f)

    status, reasons, primary_threshold = evaluate(
        current_data,
        thresholds,
        phase3_source=phase3_source,
        mdd_source=mdd_source,
    )

    threshold_value = None
    threshold_metric = None
    threshold_level = "OK"
    threshold_comparator = None
    threshold_observed_value = None
    threshold_rationale = regime_policy["rationale"]
    threshold_source_path = mdd_source["path"]
    threshold_policy_sha = mdd_source["sha"]
    threshold_policy_version = mdd_source["version"]
    if isinstance(primary_threshold, dict):
        threshold_value = primary_threshold.get("threshold_value")
        threshold_metric = primary_threshold.get("metric")
        threshold_level = primary_threshold.get("level") or "WARN"
        threshold_comparator = primary_threshold.get("comparator")
        threshold_observed_value = primary_threshold.get("observed_value")
        threshold_rationale = primary_threshold.get("rationale") or threshold_rationale
        threshold_source_path = primary_threshold.get("threshold_source_path") or threshold_source_path
        threshold_policy_sha = primary_threshold.get("threshold_policy_sha") or threshold_policy_sha
        threshold_policy_version = primary_threshold.get("threshold_policy_version") or threshold_policy_version

    snapshot = {
        "ts_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "overall": status,
        "reason": reasons,
        "threshold_value": threshold_value,
        "threshold_metric": threshold_metric,
        "threshold_level": threshold_level,
        "threshold_comparator": threshold_comparator,
        "threshold_observed_value": threshold_observed_value,
        "threshold_source_path": threshold_source_path,
        "threshold_policy_sha": threshold_policy_sha,
        "threshold_policy_version": threshold_policy_version,
        "threshold_rationale": threshold_rationale,
        "calibration_status": regime_policy.get("calibration_status", "UNKNOWN"),
        "last_calibrated_utc": regime_policy.get("last_calibrated_utc"),
        "phase3_baseline": {
            "oos_sharpe_median": thresholds["sharpe"]["median"],
            "p20": thresholds["sharpe"]["p20"],
            "p40": thresholds["sharpe"]["p40"],
            "trade_median": thresholds["trades"]["median"],
            "mdd_p80": thresholds["mdd"]["p80"],
            "mdd_p95": thresholds["mdd"]["p95"],
        },
        "current": {
            "sharpe": current_data.get("sharpe", 0.0),
            "mdd": current_data.get("max_drawdown", 0.0),
            "return": current_data.get("total_return", 0.0),
            "trades": current_data.get("trades_count", 0),
            "run_dir": str(latest_run_dir.relative_to(REPO)) if latest_run_dir else "N/A",
            "summary_path": str(latest_summary_p.relative_to(REPO)) if latest_summary_p else "N/A",
            "source_reason": source_reason,
        },
        "suggestion": "Monitor regime shifts. If FAIL, consider lowering exposure and pausing promotions (report_only).",
    }

    ATOMIC_STATE_DIR.mkdir(parents=True, exist_ok=True)
    atomic_regime_path = ATOMIC_STATE_DIR / "regime_monitor_latest.json"
    with open(atomic_regime_path, "w") as f:
        json.dump(snapshot, f, indent=2)

    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    report_md = f"""# Strategy Regime Monitor Report
Generated: {snapshot['ts_utc']}

## Overall Status: {status}

### What we see
- **Current Sharpe**: {snapshot['current']['sharpe']:.3f} (Threshold: WARN<{thresholds['sharpe']['warn']:.3f}, FAIL<{thresholds['sharpe']['fail']:.3f})
- **Current MDD**: {snapshot['current']['mdd']:.2%} (Threshold source: {mdd_source['label']}, WARN<{mdd_source['warn']:.2%}, FAIL<{mdd_source['fail']:.2%})
- **Trade Count**: {snapshot['current']['trades']} (Median: {thresholds['trades']['median']:.0f}, Warn Gate: {thresholds['trades']['warn_gate']:.0f})
- **Calibration**: status={snapshot.get('calibration_status','UNKNOWN')} last_calibrated_utc={snapshot.get('last_calibrated_utc')}

### Why it matters
{" ".join(reasons)}

### Threshold provenance
- source_path: `{snapshot.get('threshold_source_path')}`
- policy_sha: `{snapshot.get('threshold_policy_sha')}`
- policy_version: `{snapshot.get('threshold_policy_version')}`
- rationale: {snapshot.get('threshold_rationale')}

### What to do next (manual)
- {snapshot['suggestion']}
- Source Data: `{snapshot['current']['summary_path']}` ({snapshot['current']['source_reason']})

---
*Note: This is a report-only diagnostic. No automated actions were taken.*
"""

    with open(REPORT_DIR / "regime_monitor.md", "w") as f:
        f.write(report_md)

    print(f"Regime monitor finished with status: {status}")
    print(f"Atomic output: {atomic_regime_path.relative_to(REPO)}")
    sys.exit(0)


if __name__ == "__main__":
    main()
