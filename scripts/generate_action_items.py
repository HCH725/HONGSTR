import argparse
import glob
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional


def load_json(path: Path) -> Optional[Dict]:
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {path}: {e}", file=sys.stderr)
        return None


def save_json(path: Path, data: Dict):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def get_latest_run_dir(base_dir: Path) -> Optional[Path]:
    # Find all summary.json files
    pattern = str(base_dir / "*" / "*" / "summary.json")
    files = glob.glob(pattern)
    if not files:
        return None
    # Sort by mtime, newest first
    files.sort(key=os.path.getmtime, reverse=True)
    return Path(files[0]).parent


def generate_action_items(reports_dir: Path, data_dir: Path):
    # 1. Determine Source
    wf_path = reports_dir / "walkforward_latest.json"
    wf_data = load_json(wf_path)

    run_dir = None
    run_gate = None
    run_summary = None

    # Try finding latest single run
    latest_run_dir = get_latest_run_dir(data_dir / "backtests")
    if latest_run_dir:
        run_dir = latest_run_dir
        run_gate = load_json(run_dir / "gate.json")
        run_summary = load_json(run_dir / "summary.json")

    # Deciding source: prefer Walkforward if recent?
    # Actually user said "Prefer walkforward_latest.json if exists".
    # But we might want to know if it's stale? For now, we use it if valid.

    source_type = "UNKNOWN"
    failing_windows = []
    top_actions = []

    # Check if Walkforward is the primary context
    # We assume if wf_data exists, it's the "latest" set of runs
    if wf_data:
        source_type = "WALKFORWARD"
        # Analyze failing windows
        windows = wf_data.get("windows", [])
        for w in windows:
            if w.get("gate_overall") != "PASS":
                failing_windows.append(
                    {
                        "name": w.get("name"),
                        "regime": w.get("regime", "UNKNOWN"),
                        # If unknown, try to infer from name
                        # actually wf report windows list usually has name/start/end. regime might be inferred from name.  # noqa: E501
                        "gate": w.get("gate_overall"),
                        "sharpe": w.get("sharpe"),
                        "mdd": w.get("mdd"),
                        "trades": w.get("trades"),  # trades_total?
                        "notes": w.get("notes")
                        or f"Decision: {w.get('selection_decision')}",
                    }
                )

                # Infer Regime if missing
                if failing_windows[-1]["regime"] == "UNKNOWN":
                    name = failing_windows[-1]["name"].upper()
                    if "BULL" in name:
                        failing_windows[-1]["regime"] = "BULL"
                    elif "BEAR" in name:
                        failing_windows[-1]["regime"] = "BEAR"
                    elif "NEUTRAL" in name:
                        failing_windows[-1]["regime"] = "NEUTRAL"

    # If no WF failures or no WF data, look at single run gate
    if not failing_windows and run_gate:
        source_type = "SINGLE_RUN"
        # Check overall gate
        results = run_gate.get("results", {})
        overall = results.get("overall", {})
        if not overall.get("pass", False):
            # Create a "pseudo-window" for the single run
            reasons = overall.get("reasons", [])
            failing_windows.append(
                {
                    "name": "CURRENT_RUN",
                    "regime": run_gate.get("inputs", {}).get("mode", "UNKNOWN"),
                    "gate": "FAIL",
                    "sharpe": run_summary.get("sharpe") if run_summary else None,
                    "mdd": run_summary.get("max_drawdown") if run_summary else None,
                    "trades": run_summary.get("trades_count") if run_summary else None,
                    "notes": "; ".join(reasons),
                }
            )

    # 2. Generate Actions based on Failures
    failing_windows_list = failing_windows  # Rename for clarity

    # Analyze Failures
    has_low_trades = False
    has_low_sharpe = False
    has_high_mdd = False
    has_high_exposure = False

    # Specific window failures for Type E
    regime_failures = {}  # regime -> list of window names

    for w in failing_windows_list:
        notes = (w.get("notes") or "").lower()
        reasons = []  # We might want to parse from notes if it contains explicit reason string  # noqa: E501

        # Check metrics vs strict thresholds if reasons vague,
        # but mostly rely on Gate output strings if available.
        # The gate.json usually has "reasons": ["sharpe -0.5 < 0.0", ...]
        # In WF report, "notes" might be just decision or summary.
        # Let's try to infer from metrics if notes are insufficient.

        tr = w.get("trades")
        sh = w.get("sharpe")
        mdd = w.get("mdd")

        # Heuristics
        if tr is not None and tr < 30:  # 30 is a safe default min
            has_low_trades = True

        if sh is not None and sh < 0.0:
            has_low_sharpe = True

        if mdd is not None and mdd < -0.25:  # Deeper than -25%
            has_high_mdd = True

        # Check explicit notes for "Exposure"
        if "exposure" in notes:
            has_high_exposure = True

        # For Type E (Regime specific)
        reg = w.get("regime", "UNKNOWN")
        if reg not in regime_failures:
            regime_failures[reg] = []
        regime_failures[reg].append(w.get("name"))

    # Generate Top Actions

    # A. Low Trades
    if has_low_trades:
        top_actions.append(
            {
                "rank": 1,
                "title": "Increase Signal Frequency (Low Trades)",
                "why": "Portfolio trade count is below statistical significance threshold (e.g., < 30).",  # noqa: E501
                "changes": [
                    "Reduce Supertrend ATR Length/Multiplier",
                    "Relax VWAP Trend Filter (e.g., use 1h instead of 4h)",
                    "Decrease Cooldown period",
                ],
                "commands": [
                    "scripts/run_backtest.py --strategy vwap_supertrend --grid preset_fast_freq"  # noqa: E501
                ],
                "verify": ["Daily Trades >= 0.8", "Portfolio Trades >= 30"],
            }
        )

    # B. Low Sharpe (but Trades OK - implied if we fix trades first or if trades are fine)  # noqa: E501
    if has_low_sharpe and not has_low_trades:
        top_actions.append(
            {
                "rank": 2,
                "title": "Improve Signal Quality (Noise Reduction)",
                "why": "Sharpe Ratio is negative or low, indicating poor risk-adjusted returns.",  # noqa: E501
                "changes": [
                    "Increase Supertrend ATR Multiplier (reduce churn)",
                    "Add Higher Timeframe (4h/1d) Trend Confirmation",
                    "Tighten Stop Loss / Enable Trailing Stop",
                ],
                "commands": [
                    "scripts/run_backtest.py --strategy vwap_supertrend --grid preset_high_quality"  # noqa: E501
                ],
                "verify": ["Sharpe > 0.0", "Win Rate > 40%"],
            }
        )

    # C. High MDD
    if has_high_mdd:
        top_actions.append(
            {
                "rank": 3,
                "title": "Tighten Risk Controls (Deep Drawdown)",
                "why": "Max Drawdown exceeds safety limits (e.g., < -25%).",
                "changes": [
                    "Reduce Position Size (size_notional_usd)",
                    "Reduce Max Leverage",
                    "Implement 'HOLD' logic for adverse regimes (e.g. NEUTRAL/BEAR)",
                ],
                "commands": [
                    "scripts/run_backtest.py --strategy vwap_supertrend --grid preset_safe"  # noqa: E501
                ],
                "verify": ["MDD > -0.20", "Sharpe remains positive"],
            }
        )

    # D. Exposure
    if has_high_exposure:
        top_actions.append(
            {
                "rank": 4,
                "title": "Reduce Market Exposure",
                "why": "Time in market exceeds threshold (e.g., > 98%), risking over-exposure.",  # noqa: E501
                "changes": [
                    "Add Max Hold Time (bars) exit",
                    "Require Stricter Re-entry logic (e.g., opposite signal)",
                ],
                "commands": [
                    "scripts/run_backtest.py --strategy vwap_supertrend --grid preset_low_exposure"  # noqa: E501
                ],
                "verify": ["Exposure Time < 0.90"],
            }
        )

    # E. Regime Specific (Optimizer)
    if not top_actions and regime_failures:
        # If no global issues but specific regimes fail
        for reg, wins in regime_failures.items():
            if reg in ["BULL", "BEAR", "NEUTRAL"]:
                top_actions.append(
                    {
                        "rank": 5,
                        "title": f"optimize {reg} Regime Parameters",
                        "why": f"Windows in {reg} regime are failing ({', '.join(wins)}).",  # noqa: E501
                        "changes": [
                            f"Apply optimized parameters for {reg} from optimizer_regime.json"  # noqa: E501
                        ],
                        "commands": [
                            "python3 scripts/generate_optimizer_regime_artifact.py",
                            f"scripts/run_backtest.py --mode {reg} --grid preset_optimized_{reg.lower()}",  # noqa: E501
                        ],
                        "verify": [f"{reg} Window Sharpe > 0.5"],
                    }
                )

    # Sort and slice
    top_actions.sort(key=lambda x: x["rank"])
    top_actions = top_actions[:3]

    # 3. Output
    output_data = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "source": {
            "type": source_type,
            "run_dir": str(run_dir) if run_dir else None,
            "walkforward": str(wf_path) if wf_data else None,
        },
        "decision": "UNKNOWN",  # Could infer from selection.json or notes
        "overall_gate": "FAIL" if failing_windows_list else "PASS",
        "top_actions": top_actions,
        "failing_windows": failing_windows_list,
    }

    # Save JSON and MD (same as before)

    # Save JSON
    json_out = reports_dir / "action_items_latest.json"
    save_json(json_out, output_data)

    # Save MD
    md_out = reports_dir / "action_items_latest.md"
    with open(md_out, "w", encoding="utf-8") as f:
        f.write("# Action Items & Remediation Plan\n\n")
        f.write(f"**Generated At:** {output_data['generated_at']}\n")
        f.write(f"**Source:** {source_type}\n\n")

        if top_actions:
            f.write("## Top Recommended Actions\n\n")
            for act in top_actions:
                f.write(f"### {act['rank']}. {act['title']}\n")
                f.write(f"**Why:** {act['why']}\n\n")
                f.write("**Suggested Changes:**\n")
                for c in act["changes"]:
                    f.write(f"- {c}\n")
                f.write("\n**Run Command:**\n")
                f.write("```bash\n")
                for cmd in act["commands"]:
                    f.write(f"{cmd}\n")
                f.write("```\n")
                f.write(f"**Verify:** {', '.join(act['verify'])}\n\n")
        else:
            f.write("## No Critical Actions Needed\n")
            f.write("System is passing all gates.\n\n")

        if failing_windows:
            f.write("## Failing Windows Analysis\n\n")
            f.write("| Window | Regime | Gate | Sharpe | MDD | Trades | Notes |\n")
            f.write("|---|---|---|---|---|---|---|\n")
            for w in failing_windows:
                # Safe formatting
                s_sh = (
                    f"{w.get('sharpe', 0.0):.2f}"
                    if w.get("sharpe") is not None
                    else "-"
                )
                s_mdd = f"{w.get('mdd', 0.0):.2%}" if w.get("mdd") is not None else "-"
                s_tr = str(w.get("trades", "-"))
                f.write(
                    f"| {w['name']} | {w['regime']} | {w['gate']} | {s_sh} | {s_mdd} | {s_tr} | {w['notes']} |\n"  # noqa: E501
                )

    print(f"Generated {md_out} and {json_out}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--reports_dir", default="reports")
    parser.add_argument("--data_dir", default="data")
    args = parser.parse_args()

    generate_action_items(Path(args.reports_dir), Path(args.data_dir))
