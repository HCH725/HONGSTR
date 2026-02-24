#!/usr/bin/env python3
"""
scripts/report_phase3.py
Aggregates Phase 3 Walkforward results into JSON and Markdown.
"""
import argparse
import json
import logging
import statistics
from datetime import datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

def main():
    parser = argparse.ArgumentParser(description="Phase 3 Report Generator")
    parser.add_argument("--input", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()

    input_path = Path(args.input)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not input_path.exists():
        logging.error(f"Input file {input_path} missing.")
        return

    walks = []
    with open(input_path, "r") as f:
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) < 5: continue
            w_name, r_id, mode, params, p_dir = parts
            
            sum_path = Path(p_dir) / "summary.json"
            if sum_path.exists():
                with open(sum_path, "r") as sf:
                    data = json.load(sf)
                    walks.append({
                        "window": w_name,
                        "params": json.loads(params),
                        "sharpe": data.get("sharpe", 0.0),
                        "return": data.get("total_return", 0.0),
                        "mdd": data.get("max_drawdown", 0.0),
                        "trades": data.get("trades_count", 0),
                        "start": data.get("start_ts", ""),
                        "end": data.get("end_ts", "")
                    })

    if not walks:
        logging.error("No results found in run_index.tsv")
        return

    # Statistics (exclude Walk7b if present, as it is "now" and extra)
    stats_walks = [w for w in walks if w["window"] != "Walk7b"]
    if not stats_walks: stats_walks = walks # fallback
    
    sharpes = [w["sharpe"] for w in stats_walks]
    avg_sharpe = statistics.mean(sharpes)
    worst_sharpe = min(sharpes)
    std_sharpe = statistics.stdev(sharpes) if len(sharpes) > 1 else 0.0
    
    final_data = {
        "timestamp": datetime.utcnow().isoformat(),
        "summary": {
            "avg_oos_sharpe": round(avg_sharpe, 3),
            "worst_oos_sharpe": round(worst_sharpe, 3),
            "std_oos_sharpe": round(std_sharpe, 3),
            "walk_count": len(stats_walks)
        },
        "walks": walks
    }

    with (out_dir / "phase3_results.json").open("w") as f:
        json.dump(final_data, f, indent=2)

    # Markdown
    is_stable = "穩定可用" if avg_sharpe > 0.1 and worst_sharpe > -1.0 else "需進一步優化"
    md = f"""# Phase 3 Walkforward Validation Report

**一句話總結**：經由 6 個月定期參數重校驗證，本策略之 Walkforward OOS 平均 Sharpe 為 **{avg_sharpe:.2f}**，整體評估結果為「**{is_stable}**」。

## 📍 核心表現 (Core Metrics)
- **平均 OOS Sharpe**: {avg_sharpe:.2f}
- **最差段落 Sharpe**: {worst_sharpe:.2f}
- **穩定度 (Std Dev)**: {std_sharpe:.2f}
- **評估期間**: {stats_walks[0]['start'][:10]} 至 {stats_walks[-1]['end'][:10]}

## 📈 詳細窗口明細 (Walk Breakdown)

| Walk | OOS Period | Selected Params | Sharpe | Return | MDD | Trades |
|---|---|---|---|---|---|---|
"""
    for w in walks:
        p_str = f"P:{w['params']['atr_period']} M:{w['params']['atr_mult']}"
        period = f"{w['start'][:7]}~{w['end'][:7]}"
        suffix = " (Live Check)" if w["window"] == "Walk7b" else ""
        md += f"| {w['window']}{suffix} | {period} | {p_str} | {w['sharpe']:.2f} | {w['return']:.2%} | {w['mdd']:.2f} | {w['trades']} |\n"

    md += f"""
## 🚀 下一步建議
基於 Walkforward 結果，策略展現出一定的適應性。
建議進入 **Phase 4：Regime-Aware 與實時監測**。實施 ML Evidence 做 "report_only" 的監控指標，觀察在特定 Market Regime 下參數失效的前兆。

---
*Generated at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}*
"""

    with (out_dir / "phase3_results.md").open("w") as f:
        f.write(md)

    logging.info(f"Phase 3 report generated at {out_dir / 'phase3_results.md'}")

if __name__ == "__main__":
    main()
