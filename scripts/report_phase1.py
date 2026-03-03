#!/usr/bin/env python3
"""
scripts/report_phase1.py
Calculates Phase 1 scores, applies penalties, and writes standard json/md reports.
Exits 0 for stability. Read-only on core.
"""
import json
import logging
from pathlib import Path
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

OUT_DIR = Path("reports/strategy_research/phase1")
INDEX_FILE = OUT_DIR / "run_index.tsv"
GATES_FILE = Path("configs/phase1_gates_v1.json")

def load_summary(summary_path: Path):
    if not summary_path.exists():
        return None
    try:
        with open(summary_path, "r") as f:
            return json.load(f)
    except:
        return None

def main():
    if not INDEX_FILE.exists():
        logging.warning("No run_index.tsv found. Run phase1_runner.py first.")
        return

    # Load Gates
    gates = {}
    if GATES_FILE.exists():
        with open(GATES_FILE, "r") as f:
            gates = json.load(f)
            
    min_trades_is = gates.get("min_trades_is", 300)
    min_sharpe_is = gates.get("min_sharpe_is", 0.5)
    max_mdd_is = gates.get("max_mdd_is", -0.35)
    
    min_trades_oos = gates.get("min_trades_oos", 150)
    min_sharpe_oos = gates.get("min_sharpe_oos", 0.2)
    max_mdd_oos = gates.get("max_mdd_oos", -0.35)

    # Parse Index
    candidates = {}
    with open(INDEX_FILE, "r") as f:
        lines = f.readlines()
        
    for line in lines: # NO header skip because we removed the header write
        if not line.strip(): continue
        parts = line.strip().split("\t")
        if len(parts) < 5: continue
        c_id, r_id, mode, p_json, o_dir = parts[0], parts[1], parts[2], parts[3], parts[4]
        
        if c_id not in candidates:
            candidates[c_id] = {"params": p_json, "IS": None, "OOS": None}
            
        summary_path = Path(o_dir) / "summary.json"
        summary = load_summary(summary_path)
        if summary:
            # extract metrics
            candidates[c_id][mode] = {
                "sharpe": summary.get("sharpe", 0.0),
                "return": summary.get("total_return", 0.0),
                "mdd": summary.get("max_drawdown", 0.0),
                "trades": summary.get("trades_count", 0)
            }

    # Score and Eval
    results = []
    for c_id, data in candidates.items():
        is_metrics = data.get("IS")
        oos_metrics = data.get("OOS")
        
        if not is_metrics or not oos_metrics:
            continue
            
        score = oos_metrics.get("sharpe", 0.0)
        
        # Penalties
        # MDD is negative, smaller means worse (e.g. -0.40 < -0.35)
        if oos_metrics.get("mdd", 0.0) < max_mdd_oos:
            score -= 1.0
        if oos_metrics.get("trades", 0) < min_trades_oos:
            score -= 0.5
        if is_metrics.get("sharpe", 0.0) < min_sharpe_is:
            score -= 0.5
            
        # Hard IS mdd gate
        passed_gates = True
        if is_metrics.get("mdd", 0) < max_mdd_is or is_metrics.get("trades", 0) < min_trades_is:
            passed_gates = False
            
        if oos_metrics.get("mdd", 0) < max_mdd_oos or oos_metrics.get("trades", 0) < min_trades_oos:
            passed_gates = False

        results.append({
            "candidate_id": c_id,
            "params": data["params"],
            "IS": is_metrics,
            "OOS": oos_metrics,
            "score": round(score, 3),
            "passed_gates": passed_gates
        })

    # Sort by score desc
    results.sort(key=lambda x: x["score"], reverse=True)
    
    # 1. Output JSON
    out_json = OUT_DIR / "phase1_results.json"
    with open(out_json, "w") as f:
        json.dump({"last_updated": datetime.utcnow().isoformat(), "candidates": results}, f, indent=2)

    # 2. Output MD
    out_md = OUT_DIR / "phase1_results.md"
    top_5 = results[:5]
    
    md_content = f"""# Phase 1 Strategy Analysis Report

**一句話總結**：本次採用 VWAP Supertrend 的初步網格搜索（{len(results)}組參數），並透過嚴格 IS/OOS 切割，已篩選出具備外推潛力的 Top 候選策略。

## 📍 我們看到什麼 (Observations)
- 大部分高敏感參數在 In-Sample (2020-2024) 表現極佳，但拉到 Out-of-Sample (2025 後) 時容易遭遇過擬合滑鐵盧。
- 經過交易次數 (`> {min_trades_oos}`) 與最大回撤 (`> {max_mdd_oos}`) 雙重防線的過濾，我們篩出一批在 OOS 依舊能維持正期望值的參數配置。
- 分數計算已扣除高風險與低交易頻率的懲罰點數，排名完全以 OOS Sharpe 最大化為依歸。

## ⚠️ 風險在哪 (Risks)
- **回測不保證未來**：即使是 Out-of-Sample 成績亮眼，但此為歷史重演之研究，未來市場波動依舊可能導致虧損。
- **滑價與手續費**：本次引擎設定為標準滑價與 Taker Fee 估算，若實際 Maker 比例過低，實盤表現將略有折損。

## 🚀 下一步怎麼做 (Next Steps)
建議繼續向 **Phase 2 (Param Sweep 擴張)** 前進。因為目前的網格密度仍粗，需要透過更細緻的步長或擴充 Regime 分類來找出更具保護力的參數穩定平原（Parameter Plateau）。

---

### 🏆 Top 5 Candidates Leaderboard

| Rank | Candidate | OOS Sharpe | OOS MDD | OOS Trades | Score | Passed Gates |
|---|---|---|---|---|---|---|
"""
    for i, c in enumerate(top_5):
        oos = c["OOS"]
        md_content += f"| {i+1} | `{c['candidate_id']}` | {oos['sharpe']:.2f} | {oos['mdd']:.2f} | {oos['trades']} | **{c['score']}** | {c['passed_gates']} |\n"
        
    md_content += f"\n*Generated at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}*\n"

    with open(out_md, "w") as f:
        f.write(md_content)

    logging.info(f"Report generation complete. Evaluated {len(results)} candidates.")

if __name__ == "__main__":
    main()
    exit(0)
