from __future__ import annotations
from pathlib import Path
import json, math, datetime as dt

REPO = Path(__file__).resolve().parents[1]
OUT_DIR = REPO / "reports/strategy_research/phase1"
RUN_LOG = OUT_DIR / "run_index.tsv"

MIN_TRADES = int(Path(OUT_DIR/"gate_min_trades.txt").read_text().strip())
MIN_SHARPE = float(Path(OUT_DIR/"gate_min_sharpe.txt").read_text().strip())
MAX_MDD = float(Path(OUT_DIR/"gate_max_mdd.txt").read_text().strip())

def load_summary(run_dir: Path) -> dict:
    p = run_dir/"summary.json"
    if not p.exists():
        return {"_error":"missing summary.json", "_path": str(p)}
    return json.loads(p.read_text())

def pick_metrics(s: dict) -> dict:
    def g(*keys, default=None):
        for k in keys:
            if k in s:
                return s[k]
        return default
    return {
        "trades": g("trades","Trades","n_trades","trades_count", default=None),
        "sharpe": g("sharpe","Sharpe","sharpe_ratio", default=None),
        "mdd": g("max_drawdown","Max Drawdown","mdd", default=None),
        "ret": g("return","Return","total_return", default=None),
        "winrate": g("win_rate","Win Rate","winrate", default=None),
        "range": g("range","Range", default=None),
    }

def gate_ok(m: dict) -> tuple[bool, list[str]]:
    reasons=[]
    t=m.get("trades")
    s=m.get("sharpe")
    d=m.get("mdd")
    if t is None or t < MIN_TRADES:
        reasons.append(f"trades<{MIN_TRADES}")
    if s is None or s < MIN_SHARPE:
        reasons.append(f"sharpe<{MIN_SHARPE}")
    if d is None or d < MAX_MDD:
        reasons.append(f"mdd<{MAX_MDD}")
    return (len(reasons)==0, reasons)

def main():
    rows=[]
    if not RUN_LOG.exists():
        raise SystemExit(f"missing {RUN_LOG}")

    for line in RUN_LOG.read_text().splitlines()[1:]:
        if not line.strip():
            continue
        ts,strat,split,rc,run_dir=line.split("\t",4)
        rd=Path(run_dir) if run_dir else Path(".")
        s=load_summary(rd) if run_dir else {"_error":"missing run_dir"}
        m=pick_metrics(s)
        ok,reasons=gate_ok(m)
        rows.append({
            "ts": ts,
            "strategy": strat,
            "split": split,
            "rc": int(rc),
            "run_dir": run_dir,
            "gate": "PASS" if ok else "FAIL",
            "reasons": reasons,
            **m,
        })

    out_json=OUT_DIR/"phase1_results.json"
    out_md=OUT_DIR/"phase1_results.md"
    out_json.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")

    def fmt(x):
        if x is None:
            return "N/A"
        if isinstance(x, int):
            return str(x)
        if isinstance(x, float):
            if math.isnan(x):
                return "NaN"
            return f"{x:.4f}"
        return str(x)

    lines=[]
    lines.append("# HONGSTR Strategy Phase 1 Results\n")
    lines.append(f"- Generated (UTC): {dt.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}\n")
    lines.append(f"- Gate: MIN_TRADES={MIN_TRADES}, MIN_SHARPE={MIN_SHARPE}, MAX_MDD={MAX_MDD}\n")
    lines.append("\n## Summary Table\n")
    lines.append("|strategy|split|rc|gate|trades|sharpe|maxDD|return|winrate|run_dir|reasons|\n")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|\n")
    for r in rows:
        lines.append(
            "|{strategy}|{split}|{rc}|{gate}|{trades}|{sharpe}|{mdd}|{ret}|{winrate}|{run_dir}|{reasons}|\n".format(
                strategy=r["strategy"],
                split=r["split"],
                rc=r["rc"],
                gate=r["gate"],
                trades=fmt(r["trades"]),
                sharpe=fmt(r["sharpe"]),
                mdd=fmt(r["mdd"]),
                ret=fmt(r["ret"]),
                winrate=fmt(r["winrate"]),
                run_dir=r["run_dir"],
                reasons=",".join(r["reasons"]) if r["reasons"] else "",
            )
        )
    lines.append("\n## Plain-language takeaways\n")
    lines.append("- IS = 歷史訓練區間，OOS = 最近一年『沒看過的資料』測試。\n")
    lines.append("- 若 OOS 沒有資料或未過 gate，結果不可直接拿來決策，需要先修資料覆蓋。\n")

    out_md.write_text("".join(lines), encoding="utf-8")
    print("Wrote:", out_json)
    print("Wrote:", out_md)

if __name__=="__main__":
    main()
