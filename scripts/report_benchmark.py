import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional


def load_json(path: Path) -> Optional[Dict]:
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {path}: {e}", file=sys.stderr)
        return None

def format_pct(val: Any) -> str:
    if val is None or not isinstance(val, (int, float)):
        return "N/A"
    return f"{float(val)*100:7.2f}%"

def format_float(val: Any) -> str:
    if val is None or not isinstance(val, (int, float)):
        return "N/A"
    return f"{float(val):7.3f}"

def format_int(val: Any) -> str:
    if val is None or not isinstance(val, (int, float)):
        return "N/A"
    return f"{int(val):>7}"

def print_table(data: Dict):
    print("\n" + "="*80)
    print(f" HONGSTR BENCHMARK REPORT (Generated: {data.get('generated_at', 'N/A')})")
    print("="*80)

    symbols = ["BTCUSDT_4h", "ETHUSDT_4h", "BNBUSDT_4h"]
    kinds = ["FULL", "SHORT"]

    for kind in kinds:
        mode_data = data.get(kind, {})
        if not mode_data:
            print(f"\n[{kind}] NO DATA")
            continue

        print(f"\n[{kind}] Run: {mode_data.get('run_dir', 'N/A')}")

        gate = mode_data.get("gate_overall", {})
        gate_status = "PASS" if gate.get("pass") else "FAIL"
        print(f"GATE: {gate_status}")
        if not gate.get("pass"):
            print(f"Reasons: {', '.join(gate.get('reasons', []))}")

        top = mode_data.get("top", {})
        print(f"OVERALL: Ret={format_pct(top.get('total_return'))} MDD={format_pct(top.get('max_drawdown'))} Sharpe={format_float(top.get('sharpe'))} Trades={format_int(top.get('trades_count'))}")

        print("-" * 80)
        print(f"{'SYMBOL':<15} | {'RET':>8} | {'MDD':>8} | {'SHARPE':>7} | {'TRADES':>7} | {'WIN%':>7} | {'SIGNALS':>7}")
        print("-" * 80)

        per_symbol = mode_data.get("per_symbol_4h", {})
        for sym in symbols:
            s = per_symbol.get(sym, {})
            if not s:
                 print(f"{sym:<15} | {'MISSING':^59}")
                 continue

            # Note: summary.json symbols might not have 'Signals' directly if not in debug_counts
            signals = s.get("debug_counts", {}).get("signal_emitted", "N/A")

            print(f"{sym:<15} | {format_pct(s.get('total_return')):>8} | {format_pct(s.get('max_drawdown')):>8} | {format_float(s.get('sharpe')):>7} | {format_int(s.get('trades_count')):>7} | {format_pct(s.get('win_rate')):>7} | {format_int(signals):>7}")
        print("-" * 80)

def main():
    parser = argparse.ArgumentParser(description="Report Benchmark Results")
    parser.add_argument("--path", default="reports/benchmark_latest.json", help="Path to benchmark_latest.json")
    parser.add_argument("--format", default="table", choices=["table", "json"], help="Output format")

    args = parser.parse_args()

    path = Path(args.path)
    data = load_json(path)

    if not data:
        print(f"Error: {path} not found or invalid.")
        sys.exit(1)

    if args.format == "json":
        print(json.dumps(data, indent=2))
    else:
        print_table(data)

if __name__ == "__main__":
    main()
