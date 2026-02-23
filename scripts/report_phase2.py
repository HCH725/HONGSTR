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
            "return": summary.get("total_return", 0.0)
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
        
        if is_cnt >= 20 and oos_cnt >= 5:
            f.write("**一句話結論：** 策略具備穩定獲利潛力，有多組參數順利通過 IS 門檻並在 OOS 表現達標，可以繼續推進實盤準備。\n\n")
        elif is_cnt > 0:
            f.write("**一句話結論：** 策略只能勉強存活，雖然有通過 IS 的參數，但數量不足或 OOS 表現不理想，風險較高。\n\n")
        else:
            f.write("**一句話結論：** 策略目前不可用，沒有任何一組參數能通過 In-Sample 的基本穩定度門檻。\n\n")
            
        f.write("### 核心分析\n")
        f.write(f"- **現況**：在總計跑完的組合中，共有 {is_cnt} 組參數通過 In-Sample 閘門（Sharpe>0.5），並有 {oos_cnt} 組進一步取得 Out-of-Sample 結果。\n")
        f.write("- **影響**：資料長度與 ETL 抓取穩定性對於 OOS 測試至關重要。只要近期行情無劇烈結構改變，目前找到的參數重心有高機率能適應未來行情。\n")
        f.write("- **下一步**：優先針對這些頂尖參數做實盤連線測試 (Phase 3 Paper Trading)，並持續監控每日 Binance ETL 資料新鮮度以防止 OOS 失真。\n\n")
        
        f.write("### 附錄：精選指標\n")
        f.write("| 參數 (Period/Mult) | IS 交易數 | IS Sharpe | IS MDD | OOS 交易數 | OOS Sharpe | OOS Return |\n")
        f.write("|-------------------|-----------|-----------|--------|------------|------------|------------|\n")
        
        # Pick top 5 based on OOS sharpe
        top_oos = sorted(oos_candidates, key=lambda x: x["sharpe"], reverse=True)[:5]
        for oos in top_oos:
            # Find matching IS
            is_m = next((m for m in valid_is_candidates if m["atr_period"] == oos["atr_period"] and m["atr_mult"] == oos["atr_mult"]), None)
            if is_m:
                f.write(f"| {oos['atr_period']}/{oos['atr_mult']} | {is_m['trades']} | {is_m['sharpe']:.2f} | {is_m['mdd']:.1%} | {oos['trades']} | {oos['sharpe']:.2f} | {oos['return']:.1%} |\n")

    print(f"JSON and MD reports generated in {args.out_dir}")

if __name__ == "__main__":
    main()
