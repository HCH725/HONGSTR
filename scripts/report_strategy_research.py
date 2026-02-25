import json
import os
from pathlib import Path
from datetime import datetime, timezone


def safe_load(p: Path):
    if not p.exists():
        return None
    return json.loads(p.read_text())


def main():
    run_dir = Path(os.environ.get("RUN_DIR", "")).expanduser()
    out_dir = Path("reports/strategy_research")
    out_dir.mkdir(parents=True, exist_ok=True)

    if not run_dir.exists():
        raise SystemExit("RUN_DIR missing; set RUN_DIR env var")

    summary = safe_load(run_dir / "summary.json") or {}
    gate = safe_load(run_dir / "gate.json") or {}
    selection = safe_load(run_dir / "selection.json") or {}

    cfg = summary.get("config", {}) if isinstance(summary.get("config", {}), dict) else {}
    portfolio = summary.get("portfolio", {}) if isinstance(summary.get("portfolio", {}), dict) else {}
    if not portfolio:
        portfolio = {
            "trades": summary.get("trades_count"),
            "sharpe": summary.get("sharpe"),
            "max_drawdown": summary.get("max_drawdown"),
            "return": summary.get("total_return"),
            "win_rate": summary.get("win_rate"),
            "start_equity": summary.get("start_equity"),
            "end_equity": summary.get("end_equity"),
        }

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run_dir": str(run_dir),
        "strategy": summary.get("strategy") or summary.get("meta", {}).get("strategy") or cfg.get("strategy"),
        "symbols": summary.get("symbols") or summary.get("meta", {}).get("symbols") or cfg.get("symbols"),
        "timeframes": summary.get("timeframes") or summary.get("meta", {}).get("timeframes") or cfg.get("timeframes"),
        "range": summary.get("range") or summary.get("meta", {}).get("range") or {
            "start": summary.get("start_ts") or cfg.get("start"),
            "end": summary.get("end_ts") or cfg.get("end"),
        },
        "portfolio": portfolio,
        "gate": gate,
        "selection": selection,
    }

    (out_dir / "results_v1.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False))

    def fmt(x, d="N/A"):
        return d if x is None else x

    pf = payload.get("portfolio", {}) or {}
    md = []
    md.append("# Strategy Research Results v1")
    md.append("")
    md.append(f"- Generated (UTC): `{payload['generated_at']}`")
    md.append(f"- Run dir: `{payload['run_dir']}`")
    md.append(f"- Strategy: `{fmt(payload['strategy'])}`")
    md.append(f"- Symbols: `{fmt(payload['symbols'])}`")
    md.append(f"- Timeframes: `{fmt(payload['timeframes'])}`")
    md.append(f"- Range: `{fmt(payload['range'])}`")
    md.append("")
    md.append("## What this means (plain language)")
    md.append("- This is a backtest summary under the current engine assumptions.")
    md.append("- If trades are too few, results are statistically weak (the gate will warn/fail).")
    md.append("")
    md.append("## Key metrics (portfolio)")
    md.append(f"- Trades: `{fmt(pf.get('trades'))}`")
    md.append(f"- Sharpe: `{fmt(pf.get('sharpe'))}`")
    md.append(f"- Max Drawdown: `{fmt(pf.get('max_drawdown'))}`")
    md.append(f"- Return: `{fmt(pf.get('return'))}`")
    md.append(f"- Win Rate: `{fmt(pf.get('win_rate'))}`")
    md.append("")
    md.append("## Gate summary")
    overall = (payload.get("gate", {}) or {}).get("overall_gate") or (payload.get("gate", {}) or {}).get("overall")
    md.append(f"- Overall gate: `{fmt(overall)}`")
    md.append("")
    md.append("## Next actions")
    md.append("- If trades are low: tighten/loosen signal parameters or widen the time window; then re-run.")
    md.append("- If drawdown is high: reduce leverage/risk or add a regime filter; then re-run.")
    md.append("")
    (out_dir / "results_v1.md").write_text("\n".join(md))


if __name__ == "__main__":
    main()
