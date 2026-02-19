import argparse
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, Tuple

import requests

sys.path.append(str(Path(__file__).parent.parent / "src"))
from hongstr.execution.binance_utils import build_signed_request

RC_PASS = 0
RC_FAIL = 1
RC_WARN = 2


def emit_result(status: str, reason: str, http_code: str, endpoint: str, elapsed_ms: int) -> None:
    print(
        f"SMOKE_RESULT status={status} reason={reason} "
        f"http={http_code} endpoint={endpoint} elapsed_ms={elapsed_ms}"
    )


def classify_exception(exc: Exception) -> Tuple[str, str]:
    if isinstance(exc, requests.exceptions.SSLError):
        return "WARN", "SSL_ERROR"
    if isinstance(exc, requests.exceptions.ConnectionError):
        return "WARN", "NETWORK_ERROR"
    if isinstance(exc, requests.exceptions.Timeout):
        return "WARN", "NETWORK_ERROR"
    return "FAIL", "REQUEST_EXCEPTION"


def classify_response(response: requests.Response) -> Tuple[str, str]:
    body: Dict[str, Any] = {}
    try:
        body = response.json()
    except Exception:
        body = {}

    code = body.get("code")
    msg = str(body.get("msg", ""))

    if code == -1022 or "signature" in msg.lower():
        return "WARN", "SIGNATURE_MISMATCH"
    if response.status_code in (401, 403):
        return "WARN", "AUTH_REJECTED"
    if response.status_code in (404, 405):
        return "WARN", "ENDPOINT_METHOD_MISMATCH"
    if response.status_code != 200:
        return "WARN", f"HTTP_ERROR_{response.status_code}"
    return "PASS", "OK"


def mode_endpoint(mode: str) -> str:
    if mode == "PING":
        return "/fapi/v1/ping"
    if mode == "TIME":
        return "/fapi/v1/time"
    return "/fapi/v2/account"


def main() -> int:
    parser = argparse.ArgumentParser(description="Binance Futures smoke diagnostics")
    parser.add_argument(
        "--mode",
        choices=["GET_ACCOUNT", "PING", "TIME"],
        default="GET_ACCOUNT",
        help="Smoke check mode",
    )
    parser.add_argument("--timeout_sec", type=float, default=10.0, help="Request timeout seconds")
    parser.add_argument("--classify_only", action="store_true", help="Validate env only; send no request")
    parser.add_argument("--debug_signing", action="store_true", help="Print detailed signing debug info")
    args = parser.parse_args()

    api_key = os.environ.get("BINANCE_API_KEY")
    api_secret = os.environ.get("BINANCE_API_SECRET")
    is_testnet = os.environ.get("BINANCE_FUTURES_TESTNET", "0") == "1"
    base_url = "https://testnet.binancefuture.com" if is_testnet else "https://fapi.binance.com"
    endpoint = mode_endpoint(args.mode)

    print("=== Binance Futures Smoke Test ===")
    print(f"Base URL: {base_url}")
    print(f"Testnet:  {is_testnet}")
    print(f"BINANCE_API_KEY present: {bool(api_key)}")
    print(f"BINANCE_API_SECRET present: {bool(api_secret)}")
    print(f"Mode: {args.mode}")

    start_ms = int(time.time() * 1000)
    if args.classify_only:
        if args.mode == "GET_ACCOUNT" and (not api_key or not api_secret):
            print("Required env vars for GET_ACCOUNT: BINANCE_API_KEY, BINANCE_API_SECRET")
            print("No network calls made: classify_only mode with missing keys.")
            emit_result("WARN", "ENV_MISSING_KEYS", "NA", endpoint, int(time.time() * 1000) - start_ms)
            return RC_WARN
        emit_result("PASS", "CLASSIFY_ONLY", "NA", endpoint, int(time.time() * 1000) - start_ms)
        return RC_PASS

    if args.mode == "GET_ACCOUNT" and (not api_key or not api_secret):
        print("Required env vars for GET_ACCOUNT: BINANCE_API_KEY, BINANCE_API_SECRET")
        print("Private account endpoint intentionally not run due to missing keys.")
        print("No network calls made for GET_ACCOUNT mode.")
        emit_result("WARN", "ENV_MISSING_KEYS", "NA", endpoint, int(time.time() * 1000) - start_ms)
        return RC_WARN

    try:
        if args.mode == "PING":
            response = requests.get(f"{base_url}{endpoint}", timeout=args.timeout_sec)
        elif args.mode == "TIME":
            response = requests.get(f"{base_url}{endpoint}", timeout=args.timeout_sec)
            if response.status_code == 200:
                payload = response.json()
                server_time = payload.get("serverTime")
                print(f"Server Time: {server_time}")
                if args.debug_signing and server_time is not None:
                    local_time = int(time.time() * 1000)
                    print(f"Local Time:  {local_time}")
                    print(f"Diff (local-server): {local_time - int(server_time)} ms")
        else:
            url, headers, debug_info = build_signed_request(
                "GET",
                base_url,
                endpoint,
                {},
                api_key,
                api_secret,
                debug=args.debug_signing,
            )
            if debug_info:
                print(debug_info)
            response = requests.request("GET", url, headers=headers, timeout=args.timeout_sec)
            if response.status_code == 200:
                payload = response.json()
                print(f"Available Balance: {payload.get('availableBalance', 'N/A')}")

        status, reason = classify_response(response)
        emit_result(
            status,
            reason,
            str(response.status_code),
            endpoint,
            int(time.time() * 1000) - start_ms,
        )
        if status == "PASS":
            return RC_PASS
        if status == "WARN":
            return RC_WARN
        return RC_FAIL
    except Exception as exc:
        status, reason = classify_exception(exc)
        emit_result(status, reason, "NA", endpoint, int(time.time() * 1000) - start_ms)
        if status == "WARN":
            return RC_WARN
        return RC_FAIL


if __name__ == "__main__":
    raise SystemExit(main())
