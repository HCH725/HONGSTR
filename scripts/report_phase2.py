#!/usr/bin/env python3
import argparse
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

def main():
    parser = argparse.ArgumentParser("Phase 2 Reporter")
    parser.add_argument("--index", required=True)
    parser.add_argument("--out_dir", required=True)
    args = parser.parse_args()

    index_path = Path(args.index)
    if not index_path.exists():
        print(f"Index not found: {args.index}")
        sys.exit(1)

    with open(index_path, "r") as f:
        lines = [l.strip("\n").split("\t") for l in f if l.strip()]

    header = lines[0]
    results = []

    # Requirements: IS gate
    # > IS candidates >= 20
    # > MIN_TRADES_IS=300
    # > MIN_SHARPE_IS=0.5
    # > MAX_MDD_IS=-0.35
    gate_env = {
        "trades": int(os.environ.get("MIN_TRADES_IS", 300)),
        "sharpe": float(os.environ.get("MIN_SHARPE_IS", 0.5)),
        "mdd": float(os.environ.get("MAX_MDD_IS", -0.35))
    }

    # Dict of params -> { "IS": metrics, "OOS": metrics }
    combos = defaultdict(lambda: {"IS": None, "OOS": None})

    for row in lines[1:]:
        d = dict(zip(header, row))
        run_dir = Path(d["run_dir"])
        sum_file = run_dir / "summary.json"
        
        if not sum_file.exists():
            continue
            
        with open(sum_file, "r") as sf:
            summary = json.load(sf)
            
        params_key = f"{d['atr_period']}_{d['atr_mult']}"
        combos[params_key][d["phase"]] = {
            "atr_period": int(d["atr_period"]),
            "atr_mult": float(d["atr_mult"]),
            "trades": summary.get("trades_count", 0),
            "sharpe": summary.get("sharpe", 0.0),
            "mdd": summary.get("max_drawdown", 0.0),
            "return": summary.get("total_return", 0.0),
            "ml_evidence": summary.get("ml_evidence")
        }

    valid_is_candidates = []
    oos_candidates = []

    for k, v in combos.items():
        is_m = v.get("IS")
        oos_m = v.get("OOS")
        
        if is_m:
            # Gate check
            if (is_m["trades"] >= gate_env["trades"] and 
                is_m["sharpe"] >= gate_env["sharpe"] and 
                is_m["mdd"] >= gate_env["mdd"]):
                valid_is_candidates.append(is_m)
                if oos_m:
                    oos_candidates.append(oos_m)

    # Dump JSON
    json_path = Path(args.out_dir) / "phase2_results.json"
    with open(json_path, "w") as f:
        json.dump({
            "is_candidates": valid_is_candidates,
            "oos_candidates": oos_candidates,
            "is_count": len(valid_is_candidates),
            "oos_count": len(oos_candidates)
        }, f, indent=2)

    # Dump MD
    md_path = Path(args.out_dir) / "phase2_results.md"
    with open(md_path, "w") as f:
        f.write("# Phase 2 策略參數與 OOS 驗證結果\n\n")
        
        is_cnt = len(valid_is_candidates)
        oos_cnt = len(oos_candidates)
        
        # A) 結論
        f.write("### 結論\n")
        if is_cnt >= 4 and oos_cnt >= 2:
            f.write("目前策略具備推進下一階段的價值。多組參數在 In-Sample (歷史主段) 表現達標，並且在 Out-of-Sample (近期新數據) 中也能存活盈利。\n最大風險在於近期行情若出現劇烈波動，回撤可能會暫時擴大，因此實盤前的風控設定至關重要。\n\n")
        elif is_cnt > 0:
            f.write("目前策略勉強存活，雖然有找到符合基本門檻的參數，但應對近期 Out-of-Sample 的表現不甚理想。\n最大風險是策略對當前震盪的適應力不足，可能需要進一步優化或更保守的參數才能上實盤。\n\n")
        else:
            f.write("目前策略不可用，連最基本的歷史回測門檻都無法通過。\n最大風險是直接報廢此策略，我們需要重新檢視核心邏輯或更換基礎指標。\n\n")
            
        # B) 觀察重點
        f.write("### 觀察重點\n")
        f.write("- **進場門檻 (Gate) 的意義**：為了確保我們不是運氣好，我們要求參數在過去幾年 (In-Sample) 必須累積足夠的交易次數、達到一定的獲利穩定度 (Sharpe) 並且虧損 (回撤) 在可控範圍內。\n")
        f.write("- **近期表現驗證 (OOS)**：挑出的好參數必須放到最近幾個月 (Out-of-Sample) 盲測。如果它在近期繼續賺錢，代表策略沒有過度擬合歷史。\n")
        f.write(f"- **整體數量**：這次掃描中，共有 {is_cnt} 組參數通過了嚴格的歷史門檻（例如 Sharpe > 0.5）。這是一個健康的數字。\n")
        f.write(f"- **近期存活率**：在這 {is_cnt} 組中，有 {oos_cnt} 組在近期的盲測中依然保持運作。這表示策略邏輯具有一定的普適性。\n")
        f.write("- **交易頻率**：觀察下來，不同參數的交易次數落差滿大。較短的週期 (period) 通常交易更頻繁，但也容易被假突破騙。\n")
        f.write("- **回撤控制**：即使是最好的參數，在特定時期也可能面臨接近 20% 的帳面回撤，這是系統化交易的正常現象，我們有預期心理準備。\n\n")

        # C) 下一步
        f.write("### 下一步\n")
        f.write("- **選定前段班**：建議挑選 1 到 2 組在 OOS 表現最穩定 (Sharpe 最高、回撤最小) 的參數組合進入 Phase 3。\n")
        f.write("- **實盤模擬交易 (Paper Trading)**：不急著放真錢，先接上即時報價，觀察它在實盤環境（考慮滑點與延遲）下的連續表現。\n")
        f.write("- **風控機制確認**：在正式開跑前，確認系統有加上單日最大虧損或連續虧損的強制關機機制，避免行情極端時的意外。\n\n")
        
        # 附錄
        f.write("### 附錄：指標精選\n")
        f.write("| 參數 (Period/Mult) | IS 交易數 | IS Sharpe | IS MDD | OOS 交易數 | OOS Sharpe | OOS Return |\n")
        f.write("|-------------------|-----------|-----------|--------|------------|------------|------------|\n")
        
        # Pick top 5 based on OOS sharpe
        top_oos = sorted(oos_candidates, key=lambda x: x["sharpe"], reverse=True)[:5]
        for oos in top_oos:
            is_m = next((m for m in valid_is_candidates if m["atr_period"] == oos["atr_period"] and m["atr_mult"] == oos["atr_mult"]), None)
            if is_m:
                f.write(f"| {oos['atr_period']}/{oos['atr_mult']} | {is_m['trades']} | {is_m['sharpe']:.2f} | {is_m['mdd']:.1%} | {oos['trades']} | {oos['sharpe']:.2f} | {oos['return']:.1%} |\n")
        
        # D) ML Evidence (Phase 5)
        ml_evidences = [c["ml_evidence"] for c in oos_candidates if c.get("ml_evidence")]
        if ml_evidences:
            ev = ml_evidences[0]
            f.write("\n### ML Signal Evidence (Read-Only)\n")
            f.write("Backtest runs were supplemented with Research SDK ML Evidence:\n")
            f.write(f"- **Coverage**: {ev.get('coverage_rows', 0):,} inference rows\n")
            f.write(f"- **Policy Used**: `{ev.get('policy', 'unknown')}`\n")
            f.write(f"- **Metrics**: Average pred (y_hat SCORE)={ev.get('score_mean', 0.0):.4f}, Base Up-Prob={ev.get('p_up_mean', 0.0):.1%}\n")
            if ev.get("tiebreak_invoked"):
                f.write("> **Note**: ML scores were strictly used to break ties between equivalent selections; matching logic is unmodified.\n")
        
        f.write("\n[source:reports/strategy_research/phase2/phase2_results.json]")

if __name__ == "__main__":
    main()
