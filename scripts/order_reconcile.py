import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Optional

# Add src and scripts to path
current_dir = Path(__file__).parent
sys.path.append(str(current_dir.parent / "src"))
sys.path.append(str(current_dir))

from execute_paper import generate_markdown_report  # noqa: E402

from hongstr.execution.binance_testnet import BinanceFuturesTestnetBroker  # noqa: E402


def load_json(path: Path) -> Optional[Dict]:
    if not path.exists():
        return None
    with open(path, "r") as f:
        return json.load(f)


def save_json(path: Path, data: Dict):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def update_markdown(path: Path, data: Dict):
    # Reuse generate_markdown_report logic or import it
    generate_markdown_report(path, data)


def main():
    parser = argparse.ArgumentParser(description="Order Reconciliation Script")
    parser.add_argument(
        "--report",
        type=str,
        default="reports/orders_latest.json",
        help="Path to orders report",
    )
    args = parser.parse_args()

    report_path = Path(args.report)
    data = load_json(report_path)

    if not data:
        print(f"No report found at {report_path}")
        return

    orders = data.get("orders", [])
    if not orders:
        print("No orders to reconcile.")
        return

    print(f"Reconciling {len(orders)} orders...")
    broker = BinanceFuturesTestnetBroker()
    changes = 0

    for i, order in enumerate(orders):
        order_id = order.get("orderId")
        symbol = order.get("symbol")
        status = order.get("status")

        if not order_id or not symbol:
            continue

        if status in ["FILLED", "CANCELED", "REJECTED"]:
            print(f"Order {order_id} is already in final state: {status}")
            continue

        print(f"Checking status for Order {order_id} ({symbol})...")
        try:
            details = broker.get_order(symbol, order_id=order_id)
            if "error" in details:
                print(f"Error fetching status: {details['error']}")
                continue

            new_status = details.get("status")
            if new_status != status:
                print(f"Status changed: {status} -> {new_status}")
                # Update order object
                orders[i].update(
                    {
                        "status": new_status,
                        "avgPrice": details.get("avgPrice"),
                        "executedQty": details.get("executedQty"),
                        "cumQuote": details.get("cumQuote"),
                        "updateTime": details.get("updateTime"),
                    }
                )
                changes += 1
            else:
                print(f"Status remains: {status}")
        except Exception as e:
            print(f"Exception during reconciliation: {e}")

    if changes > 0:
        print(f"Saving {changes} updates to {report_path}...")
        save_json(report_path, data)
        update_markdown(report_path.with_suffix(".md"), data)
        print("Done.")
    else:
        print("No changes needed.")


if __name__ == "__main__":
    main()
