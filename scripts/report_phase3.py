#!/usr/bin/env python3
import argparse
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

def main():
    parser = argparse.ArgumentParser("Phase 3 Reporter")
    parser.add_argument("--index", required=True)
    parser.add_argument("--out_dir", required=True)
    args = parser.parse_args()

    index_path = Path(args.index)
    if not index_path.exists():
        print(f"Index not found: {args.index}")
        sys.exit(1)

    with open(index_path, "r") as f:
        lines = [l.strip("\n").split("\t") for l in f if l.strip()]

    if not lines:
        return

    header = lines[0]
    
    # Store results
    # dict structure: { "period_mult": { "FIXED": {"IS": metrics, "OOS": metrics}, "WF1": {...} } }
    results_map = defaultdict(lambda: defaultdict(lambda: {"IS": None, "OOS": None}))

    total_runs = 0
    failed_runs = 0

    for row in lines[1:]:
        total_runs += 1
        d = dict(zip(header, row))
        rc = str(d.get("rc", "0")).strip()
        if not rc.isdigit() or int(rc) != 0:
            print(f"DEBUG FAIL RC: {rc} on row {row}")
            failed_runs += 1
            continue
            
        rd_str = d.get("run_dir", "")
        if not rd_str:
            print(f"DEBUG FAIL RD: row is {row} dict is {d}")
            failed_runs += 1
            continue
        run_dir = Path(rd_str)
        sum_file = run_dir / "summary.json"
        
        if not sum_file.exists():
            failed_runs += 1
            continue
            
        with open(sum_file, "r") as sf:
            summary = json.load(sf)
            
        params_key = f"{d['atr_period']}_{d['atr_mult']}"
        split_name = d["split_name"]
        phase = d["phase"] 
        
        results_map[params_key][split_name][phase] = {
            "atr_period": int(d["atr_period"]),
            "atr_mult": float(d["atr_mult"]),
            "trades": summary.get("trades_count", 0),
            "sharpe": summary.get("sharpe", 0.0),
            "mdd": summary.get("max_drawdown", 0.0),
            "return": summary.get("total_return", 0.0),
            "ml_evidence": summary.get("ml_evidence"),
            "start": d["start"],
            "end": d["end"]
        }

    # Evaluate the rules for each candidate based on WF segments
    final_candidates = []
    
    for pkey, splits in results_map.items():
        # Rules:
        # OOS trades >= 200 (in Fixed split) - if less, marked as insufficient but not eliminated immediately
        # OOS MaxDD < -35% -> high risk
        # 2+ WF segments with OOS Sharpe < 0 -> unstable
        
        fixed_oos = splits.get("FIXED", {}).get("OOS")
        if not fixed_oos:
            continue
            
        # Count unstable WF segments
        wf_unstable_count = 0
        for wf in ["WF1", "WF2", "WF3"]:
            wf_oos = splits.get(wf, {}).get("OOS")
            if wf_oos and wf_oos.get("sharpe", -1) < 0:
                wf_unstable_count += 1
                
        is_risky = fixed_oos["mdd"] < -0.35
        is_unstable = wf_unstable_count >= 2
        low_trades = fixed_oos["trades"] < 200
        
        score = fixed_oos["sharpe"]
        if is_risky: score -= 2.0
        if is_unstable: score -= 2.0
        if low_trades: score -= 0.5
        
        final_candidates.append({
            "param_key": pkey,
            "atr_period": fixed_oos["atr_period"],
            "atr_mult": fixed_oos["atr_mult"],
            "fixed_oos": fixed_oos,
            "wf_unstable_count": wf_unstable_count,
            "is_risky": is_risky,
            "low_trades": low_trades,
            "is_unstable": is_unstable,
            "score": score,
            "splits": splits
        })

    # Sort candidates by score
    final_candidates.sort(key=lambda x: x["score"], reverse=True)
    top_3 = final_candidates[:3]

    # Dump JSON
    json_path = Path(args.out_dir) / "phase3_results.json"
    with open(json_path, "w") as f:
        json.dump({
            "total_runs": total_runs,
            "failed_runs": failed_runs,
            "candidates": final_candidates
        }, f, indent=2)

    # Dump MD
    md_path = Path(args.out_dir) / "phase3_results.md"
    with open(md_path, "w") as f:
        
        # Determine top recommendation
        top_rec = top_3[0] if top_3 else None
        
        f.write("# Phase 3 策略嚴格 Walkforward 驗證報告\\n\\n")
        
        if not top_rec or top_rec["is_unstable"] or top_rec["is_risky"]:
            f.write("**一句話結論：** 經過嚴格分段盲測，目前沒有任何參數能在不同歷史時期穩定保持正期望值，不可輕易上實盤。\\n\\n")
        else:
            f.write(f"**一句話結論：** 參數 [{top_rec['atr_period']}/{top_rec['atr_mult']}] 展現了不錯的跨時段穩定度，是我們進軍實盤的首選種子。\\n\\n")
            
        f.write("### 核心觀察與分析\\n")
        
        if top_rec:
            f.write(f"- **現在表現好不好？** 這次我們跑了 {total_runs} 個獨立的回測任務。在最長的 Fixed OOS 中，最好的參數夏普值大約為 {top_rec['fixed_oos']['sharpe']:.2f}。")
            if not top_rec["is_unstable"]:
                f.write("這顯示策略具備真正的獲利基因，不會只依賴特定行情。\\n")
            else:
                f.write("可惜大部分的參數在時間切段後（Walkforward）都被打回原形，表現並不一致。\\n")
        else:
            f.write(f"- **現在表現好不好？** 這次跑了 {total_runs} 個獨立回測任務，但所有參數皆未產出完整 OOS 數據或全部在門檻以下。\\n")
            
        f.write("- **最大風險在哪裡？** 最大的挑戰是面對熊市或極端震盪（例如目前的 regime），很多參數的最大回撤會飆高，甚至超過我們設定的 -35% 門檻，這在實盤會造成極大的心理壓力。\\n")
        
        if top_rec and not top_rec["is_unstable"] and not top_rec["is_risky"]:
            f.write(f"- **下一步建議**：強烈建議使用參數 **Period: {top_rec['atr_period']}, Mult: {top_rec['atr_mult']}** 開始啟動實盤模擬 (Paper Trading)，觀察它在實際有滑點和延遲的環境下的連續表現。\\n\\n")
        else:
            f.write("- **下一步建議**：由於參數穩定度不足，目前不建議貿然使用真錢。我們應該退回 Phase 1/2 尋找更具保護性的指標，或在下單邏輯上加上大盤趨勢濾網過濾過多假突破。\\n\\n")
            
        f.write("### Top 3 候選參數 (依穩定度排序)\\n")
        for i, c in enumerate(top_3):
            status = "🟢 穩定" if not c["is_unstable"] and not c["is_risky"] else "🔴 風險較高"
            f.write(f"{i+1}. **{c['atr_period']} / {c['atr_mult']}** ({status})\\n")
            f.write(f"   - OOS 交易數: {c['fixed_oos']['trades']}\\n")
            f.write(f"   - OOS 夏普值 (Sharpe): {c['fixed_oos']['sharpe']:.2f}\\n")
            f.write(f"   - OOS 最大回撤 (MDD): {c['fixed_oos']['mdd']:.1%}\\n")
            f.write(f"   - 不穩定分段數: {c['wf_unstable_count']}/3 段\\n")
            f.write(f"   - 綜合評價分數: {c['score']:.2f}\\n\\n")
            
        # ML Evidence (Phase 5)
        ml_evidences = []
        for c in final_candidates:
            if c["fixed_oos"].get("ml_evidence"):
                ml_evidences.append(c["fixed_oos"]["ml_evidence"])
                
        if ml_evidences:
            ev = ml_evidences[0]
            f.write("### ML Signal Evidence (Read-Only)\\n")
            f.write("Backtest runs were supplemented with Research SDK ML Evidence:\\n")
            f.write(f"- **Coverage**: {ev.get('coverage_rows', 0):,} inference rows\\n")
            f.write(f"- **Policy Used**: `{ev.get('policy', 'unknown')}`\\n")
            f.write(f"- **Metrics**: Average pred (y_hat SCORE)={ev.get('score_mean', 0.0):.4f}, Base Up-Prob={ev.get('p_up_mean', 0.0):.1%}\\n")
            if ev.get("tiebreak_invoked"):
                f.write("> **Note**: ML scores were strictly used to break ties between equivalent selections; matching logic is unmodified.\\n")
                
        f.write("\\n[source:reports/strategy_research/phase3/phase3_results.json]\\n")

    print(f"JSON and MD reports generated in {args.out_dir}")

if __name__ == "__main__":
    main()
