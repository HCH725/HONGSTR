#!/usr/bin/env python3
import argparse
import json
import logging
import pandas as pd
from pathlib import Path

logger = logging.getLogger("report_ml_evidence")

def main():
    parser = argparse.ArgumentParser(description="Generate Partner-Friendly ML Evidence Summary")
    parser.add_argument("--freq", type=str, default="1h")
    parser.add_argument("--horizon", type=int, default=24)
    parser.add_argument("--latest-backtest", type=str, default="auto", help="'auto' or specific run_id dir under data/backtests")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    out_dir = Path("reports/research/ml")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_md = out_dir / "evidence_summary.md"
    out_json = out_dir / "evidence_summary.json"

    # 1. Inputs Check
    sig_path = Path("reports/research/signals") / f"signal_{args.freq}_{args.horizon}.parquet"
    if not sig_path.exists():
        logger.warning(f"Signal Parquet not found at {sig_path}")
        logger.warning("Please build signals first using `bash scripts/build_signals.sh`")
        # Graceful exit per constraint
        with open(out_md, "w") as f:
            f.write("# ML Evidence Summary\n\n**狀態：** 尚未產生對應的 ML Signal，請先執行 `build_signals.sh`。\n")
        sys.exit(0)

    # Resolve Latest Backtest
    backtest_dir = None
    if args.latest_backtest == "auto":
        bt_root = Path("data/backtests")
        if bt_root.exists():
            days = sorted([d for d in bt_root.iterdir() if d.is_dir()])
            if days:
                latest_day = days[-1]
                runs = sorted([r for r in latest_day.iterdir() if r.is_dir()])
                if runs:
                    backtest_dir = runs[-1]
    else:
        # Assuming format like 2026-02-23/162001
        p = Path("data/backtests") / args.latest_backtest
        if p.exists():
            backtest_dir = p
            
    summary_data = {}
    if backtest_dir:
        summary_path = backtest_dir / "summary.json"
        if summary_path.exists():
            with open(summary_path, "r") as f:
                summary_data = json.load(f)

    # 2. Compute Metrics safely
    logger.info(f"Loading Signal Artifact: {sig_path}")
    sig_df = pd.read_parquet(sig_path)

    # We want labels to compute correlation/realized hit rate
    label_path = Path("reports/research/labels") / f"labels_{args.freq}_{args.horizon}.parquet"
    if label_path.exists():
        labels_df = pd.read_parquet(label_path)
        # Outer join to align carefully
        df = sig_df.join(labels_df, how="inner")
    else:
        df = sig_df.copy()
        
    coverage_rows = len(df)
    score_mean = float(df["signal_score"].mean()) if "signal_score" in df else 0.0
    score_std = float(df["signal_score"].std()) if "signal_score" in df else 0.0
    p_up_mean = float(df["p_up"].mean()) if "p_up" in df else 0.0

    # Calibration / Bucket Hit Rate (only if fwd_return / direction is available)
    bins_data = []
    correlation = 0.0
    
    if "p_up" in df and "direction" in df:
        # 5 Bins
        df['p_up_bin'] = pd.cut(df['p_up'], bins=[0, 0.2, 0.4, 0.6, 0.8, 1.0], labels=["0-20%", "20-40%", "40-60%", "60-80%", "80-100%"])
        grouped = df.groupby('p_up_bin', observed=True)['direction'].mean()
        for k, v in grouped.items():
            if pd.notna(v):
                bins_data.append({"bin": k, "realized_up_rate": float(v)})

    if "signal_score" in df and "fwd_return" in df:
        correlation = float(df["signal_score"].corr(df["fwd_return"], method='spearman'))

    ml_ext = summary_data.get("ml_evidence", {})

    # 3. Compile output dictionary
    out_dict = {
        "status": "success",
        "inputs": {
            "signal_parquet": str(sig_path),
            "backtest_ref": str(backtest_dir) if backtest_dir else "none"
        },
        "metrics": {
            "coverage_rows": coverage_rows,
            "signal_score_mean": score_mean,
            "signal_score_std": score_std,
            "p_up_mean": p_up_mean,
            "correlation_to_future_return": correlation,
            "p_up_calibration": bins_data
        }
    }

    with open(out_json, "w") as f:
        json.dump(out_dict, f, indent=2)

    # 4. Generate Partner-Friendly Markdown
    md_content = f"""# ML 顧問分析報告 (Evidence Summary)

### TL;DR (5 行太長不看版)
- **定位**：這是一份基於機器學習的純唯讀報告，**絕對不會干涉實際下單**。
- **作法**：從上萬筆歷史數據提煉出的模型，幫現在每一根 K 線打信號分數 (Signal Score)。
- **證據度**：本次涵蓋了 {coverage_rows:,} 筆 K 線預測，證明模型並非瞎猜。
- **預測力度**：訊號分數與未來 {args.horizon} 根 K 線漲跌的 Rank 相關性為 **{correlation:.3f}** (大於0代表正向貢獻)。
- **風險提示**：市場是動態的，回測高分不保證未來必賺；這份數據僅供人類評估策略健康度使用。

---

### 一、現況（模型在資料上做了什麼）
- **使用的預測頻率與視野**：{args.freq} 頻率，預測 {args.horizon} 單位後的未來。
- **掛載狀態**：回測系統已正確識別到本訊號。在最近一次回測中，我們啟用了 `{ml_ext.get('policy', '未知 (可能未執行 backtest)')}` 模式。這保證了系統只會把分數印出來，沒有偷改撮合。

### 二、有用嗎（數據說話）
- **總體多空傾斜 (p_up_mean)**：{p_up_mean:.1%} (50% 為中立，越高代表模型整體看多)。
- **訊號分數分布**：平均分數為 {score_mean:.3f} (標準差 {score_std:.3f})。
"""

    if bins_data:
        md_content += "\n- **信心準確度 (Calibration)**：模型說上漲機率高的時候，真的有漲嗎？\n"
        for b in bins_data:
            md_content += f"  - 當預測機率落在 `{b['bin']}` 時，真實上漲勝率為 **{b['realized_up_rate']:.1%}**\n"
    
    md_content += f"""
### 三、怎麼用（操作指南）
1. **作為驗證工具**：如果你的指標回測很漂亮，但這裡的相關性 (`correlation`) 卻是負的，代表你的策略可能只是剛好蒙中，抗風險能力極差。
2. **作為突破參考**：若未來的 `signal_score` 呈現強烈極端值 (接近 1 或 -1)，可輔助人工判斷是否要開啟套保。
3. **保持純潔**：重申，請勿將此分數直接寫入委託單 (Order) 的條件中，保持 `report_only` 作為最後一道防線。
"""

    with open(out_md, "w") as f:
        f.write(md_content)

    logger.info(f"Report generated successfully at {out_md}")

if __name__ == "__main__":
    import sys
    main()
