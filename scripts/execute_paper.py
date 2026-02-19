import os
import json
import argparse
import sys
import glob
import requests
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# Add src to path for internal imports
sys.path.append(str(Path(__file__).parent.parent / "src"))
try:
    from hongstr.execution.binance_testnet import BinanceFuturesTestnetBroker
    from hongstr.execution.models import OrderRequest
except ImportError:
    # If installed as package
    from hongstr.execution.binance_testnet import BinanceFuturesTestnetBroker
    from hongstr.execution.models import OrderRequest

def save_report(path: Path, data: Dict):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def generate_markdown_report(path: Path, data: Dict):
    lines = [
        "# Paper Trading Execution Report",
        f"**Timestamp**: {data.get('timestamp')}",
        f"**Decision**: {data.get('decision')}",
        f"**Regime**: {data.get('regime', 'N/A')}",
        f"**Mode**: {'LIVE SEND' if not data.get('dry_run') else 'DRY RUN'}",
        ""
    ]
    
    if data.get("orders"):
        lines.append("## Orders Details")
        lines.append("| Symbol | Side | Status | Qty | AvgPrice | OrderId | ClientOrderId |")
        lines.append("|---|---|---|---|---|---|---|")
        for o in data["orders"]:
            lines.append(f"| {o.get('symbol')} | {o.get('side')} | {o.get('status')} | {o.get('executedQty', 0)} | {o.get('avgPrice', 0)} | {o.get('orderId', 'N/A')} | {o.get('clientOrderId', 'N/A')} |")
    else:
        lines.append("No orders were generated.")
        
    if data.get("error"):
        lines.append(f"\n**Error**: {data['error']}")
        
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

def get_latest_selection(data_root: Path) -> Optional[Path]:
    pattern = str(data_root / "backtests" / "*" / "*" / "selection.json")
    files = glob.glob(pattern)
    if not files:
        return None
    files.sort(key=os.path.getmtime, reverse=True)
    return Path(files[0])

def main():
    parser = argparse.ArgumentParser(description="Automated Paper Execution")
    parser.add_argument("--run_dir", type=str, help="Manually specify run directory with selection.json")
    parser.add_argument("--send", action="store_true", help="Actually send orders (dry-run by default)")
    parser.add_argument("--max_notional_usd", type=float, default=50.0, help="Max notional allowed per order")
    parser.add_argument("--data_dir", type=str, default="data", help="Data directory")
    
    # 1. Force Trade Arguments
    parser.add_argument("--force_trade", action="store_true", help="Force a TRADE execution regardless of selection (TESTNET ONLY)")
    parser.add_argument("--force_side", type=str, choices=["BUY", "SELL"], default="BUY", help="Side for forced trade")
    parser.add_argument("--force_symbol", type=str, default="BTCUSDT", help="Symbol for forced trade")
    parser.add_argument("--force_notional_usd", type=float, default=10.0, help="Notional for forced trade")
    parser.add_argument("--debug_signing", action="store_true", help="Print detailed signing debug info")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)
    
    sel_path = Path(args.run_dir) / "selection.json" if args.run_dir else get_latest_selection(data_dir)
    if not sel_path or not sel_path.exists():
        if args.force_trade:
            print("Notice: No selection.json found, but --force_trade is active.")
            sel_data = {"decision": "HOLD", "regime": "FORCED", "selected_symbol": args.force_symbol}
        else:
            print(f"ERROR: selection.json not found.", file=sys.stderr)
            sys.exit(1)
    else:
        print(f"Using selection from: {sel_path}")
        with open(sel_path, "r") as f:
            sel_data = json.load(f)
        
    decision = sel_data.get("decision", "HOLD")
    regime = sel_data.get("regime", "UNKNOWN")
    symbol = sel_data.get("selected_symbol", "BTCUSDT")
    side = "BUY"
    
    # 2. Check Force Trade Safety
    is_forced = False
    if args.force_trade:
        is_testnet = os.getenv("BINANCE_FUTURES_TESTNET") == "1" or os.getenv("BINANCE_TESTNET") == "1"
        if not is_testnet:
            print("ERROR: --force_trade is ONLY allowed on Binance Testnet (set BINANCE_FUTURES_TESTNET=1).", file=sys.stderr)
            sys.exit(1)
        
        print(f"!!! FORCE TRADE ACTIVE: Overriding decision {decision} -> TRADE !!!")
        decision = "TRADE"
        symbol = args.force_symbol
        side = args.force_side
        regime = "FORCED"
        is_forced = True

    output = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "source_selection": str(sel_path) if sel_path else "FORCED",
        "decision": decision,
        "regime": regime,
        "forced": is_forced,
        "orders": [],
        "dry_run": not args.send
    }
    
    if decision == "TRADE":
        notional_usd = args.force_notional_usd if is_forced else 10.0
        if notional_usd > args.max_notional_usd:
            msg = f"Rejected: Notional {notional_usd} > limit {args.max_notional_usd}"
            print(msg)
            output["error"] = msg
        elif not args.send:
            print(f"[DRY-RUN] Would send {side} {symbol} (~${notional_usd})")
            output["orders"].append({
                "symbol": symbol,
                "side": side,
                "status": "DRY_RUN",
                "notional_usd": notional_usd,
                "forced": is_forced
            })
        else:
            print(f"Executing TRADE order for {symbol}...")
            broker = BinanceFuturesTestnetBroker(debug_signing=args.debug_signing)
            
            # 1. Get current price for qty calculation
            try:
                r_p = requests.get(f"{broker.base_url}/fapi/v1/ticker/price", params={"symbol": symbol}, timeout=5)
                price = float(r_p.json()["price"])
                raw_qty = notional_usd / price
                qty = broker.filters.round_qty(symbol, raw_qty)
                min_qty = broker.filters.get_filters(symbol).get('min_qty', 0.001)
                if qty < min_qty:
                    qty = min_qty
                
                # 2. Place Order
                req = OrderRequest(symbol=symbol, side=side, qty=qty, order_type="MARKET")
                res = broker.place_order(req)
                
                # 3. Read back immediately for more details (Post-Trade Readback)
                if res.exchange_order_id:
                    print(f"Order Sent: {res.exchange_order_id}. Fetching full details...")
                    details = broker.get_order(symbol, order_id=res.exchange_order_id)
                    
                    # Store rich details
                    order_out = {
                        "symbol": symbol,
                        "side": side,
                        "orderId": details.get("orderId"),
                        "clientOrderId": details.get("clientOrderId"),
                        "status": details.get("status"),
                        "avgPrice": details.get("avgPrice"),
                        "executedQty": details.get("executedQty"),
                        "cumQuote": details.get("cumQuote"),
                        "updateTime": details.get("updateTime"),
                        "type": details.get("type"),
                        "forced": is_forced
                    }
                    output["orders"].append(order_out)
                else:
                    output["error"] = res.error or "Unknown error"
                    print(f"Order FAILED: {output['error']}")
                    
            except Exception as e:
                output["error"] = str(e)
                print(f"Execution Exception: {e}")
    else:
        print(f"Decision is {decision}. No orders generated.")

    save_report(reports_dir / "orders_latest.json", output)
    generate_markdown_report(reports_dir / "orders_latest.md", output)
    print(f"Reports written to {reports_dir}/orders_latest.json and .md")

if __name__ == "__main__":
    main()
