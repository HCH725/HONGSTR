#!/usr/bin/env python3
"""
scripts/cmc_market_intel_fetch.py
Fetches CMC Market Intel P1 data: Narratives and Macro Events.
Strictly adheres to SSOT and red-line rules:
- No core diffs.
- No direct writes to data/state.
- Outputs derived data to data/derived/cmc/market_intel/...
- Outputs coverage telemetry to reports/state_atomic/...
- Outputs manifest to reports/state_atomic/manifests/...
- Retries and backoffs applied.
- API keys strictly protected.
"""
from __future__ import annotations

import json
import logging
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Tuple

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger("cmc_market_intel_fetch")

REPO_ROOT = Path(__file__).resolve().parent.parent
DERIVED_ROOT_NARRATIVES = REPO_ROOT / "data" / "derived" / "cmc" / "market_intel" / "narratives"
DERIVED_ROOT_MACRO = REPO_ROOT / "data" / "derived" / "cmc" / "market_intel" / "macro_events"

ATOMIC_COVERAGE_PATH = REPO_ROOT / "reports" / "state_atomic" / "cmc_market_intel_coverage.json"
MANIFEST_PATH = REPO_ROOT / "reports" / "state_atomic" / "manifests" / "cmc_market_intel_v1.json"

CMC_BASE_URL = "https://pro-api.coinmarketcap.com"
ENDPOINT_NARRATIVES = "/v1/cryptocurrency/categories"
ENDPOINT_MACRO = "/v1/content/latest"  # Placeholder for macro/news events

MAX_RETRIES = 3
TIMEOUT_SEC = 15


def _is_tier_gated_http_403(error_reason: Optional[str]) -> bool:
    return error_reason == "HTTP 403"


def _format_tier_gated_reason(components: list[str]) -> str:
    return f"tier_gated:{','.join(sorted(set(components)))}"


def _get_git_commit() -> str:
    try:
        import subprocess
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=REPO_ROOT).decode("utf-8").strip()
    except Exception:
        return "unknown"


def _load_api_key() -> Optional[str]:
    """Load CMC API key securely."""
    key = os.environ.get("CMC_API_KEY", "").strip()
    if not key:
        env_path = REPO_ROOT / ".env"
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                line = line.strip()
                if line.startswith("CMC_API_KEY=") and not line.startswith("#"):
                    key = line.split("=", 1)[1].strip().strip("'\"")
                    break
    return key if key else None


def _fetch_api_with_retry(endpoint: str, api_key: str, params: Optional[dict] = None) -> Tuple[Optional[dict], Optional[str]]:
    """Fetch from CMC with exponential backoff. Returns (data, error_reason)."""
    url = f"{CMC_BASE_URL}{endpoint}"
    if params:
        url += "?" + urllib.parse.urlencode(params)

    req = urllib.request.Request(url)
    req.add_header("X-CMC_PRO_API_KEY", api_key)
    req.add_header("Accept", "application/json")

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT_SEC) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data, None
        except urllib.error.HTTPError as e:
            if e.code == 403:
                return None, "HTTP 403"
            if e.code == 401:
                return None, "HTTP 401"
            if e.code == 429:
                log.warning("Rate limit hit, retrying if possible...")
            else:
                log.warning("HTTP %d error on attempt %d for %s", e.code, attempt, endpoint)
            
            if attempt == MAX_RETRIES:
                return None, f"HTTP {e.code}"
        except Exception as e:
            log.warning("Network error on attempt %d: %s", attempt, type(e).__name__)
            if attempt == MAX_RETRIES:
                return None, f"Network Error: {type(e).__name__}"
                
        time.sleep(2 ** attempt)

    return None, "Max retries exceeded"


def _safe_write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, path)


def write_manifest(ts_utc: str) -> None:
    """Write the data catalog manifest."""
    manifest = {
        "dataset_id": "cmc_market_intel_v1",
        "schema_version": "v1",
        "producer": "scripts/cmc_market_intel_fetch.py",
        "cadence": "daily",
        "path_patterns": {
            "root": "data/derived/cmc/market_intel",
            "template": "data/derived/cmc/market_intel/{dataset}/{ts_utc}.json"
        },
        "symbols": ["GLOBAL"],
        "metrics": ["narratives", "macro_events"],
        "periods": ["snapshot"],
        "sources": [
            {
                "name": "cmc",
                "endpoints": [ENDPOINT_NARRATIVES, ENDPOINT_MACRO]
            }
        ],
        "provenance": {
            "generated_utc": ts_utc,
            "code_ref": _get_git_commit()
        },
        "notes": "CMC P1 Market Intel: Narratives and Macro events. Excludes overlapping exchange data (funding/OI/OHLCV)."
    }
    _safe_write_json(MANIFEST_PATH, manifest)
    log.info("Wrote atomic manifest to %s", MANIFEST_PATH.name)


def main() -> int:
    now_utc = datetime.now(timezone.utc)
    ts_utc = now_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
    
    coverage = {
        "ts_utc": ts_utc,
        "latest_utc": ts_utc,
        "items": {
            "narratives_count": 0,
            "macro_events_count": 0
        },
        "status": "OK",
        "reason": "OK"
    }

    api_key = _load_api_key()
    if not api_key:
        log.error("CMC_API_KEY not found in environment.")
        coverage["status"] = "FAIL"
        coverage["reason"] = "API key missing"
        _safe_write_json(ATOMIC_COVERAGE_PATH, coverage)
        return 0  # Non-blocking

    # --- Fetch Narratives ---
    narratives_data, n_err = _fetch_api_with_retry(ENDPOINT_NARRATIVES, api_key)
    narratives_payload = narratives_data.get("data", []) if narratives_data else []
    
    # --- Fetch Macro Events ---
    macro_data, m_err = _fetch_api_with_retry(ENDPOINT_MACRO, api_key, {"news_type": "macro"})
    # Assuming standard empty data structure or failure due to tier
    macro_payload = macro_data.get("data", []) if macro_data else []

    # Calculate item counts
    if isinstance(narratives_payload, dict):
        coverage["items"]["narratives_count"] = len(narratives_payload)
    else:
        coverage["items"]["narratives_count"] = len(narratives_payload) if isinstance(narratives_payload, list) else 0
        
    if isinstance(macro_payload, dict):
        coverage["items"]["macro_events_count"] = len(macro_payload)
    else:
        coverage["items"]["macro_events_count"] = len(macro_payload) if isinstance(macro_payload, list) else 0

    # Determine aggregated status
    warn_reasons = []
    fail_reasons = []
    tier_gated_components = []

    if n_err:
        if _is_tier_gated_http_403(n_err):
            tier_gated_components.append("narratives")
        else:
            fail_reasons.append(f"narratives:{n_err}")
    elif coverage["items"]["narratives_count"] == 0:
        warn_reasons.append("Narratives Empty (Endpoint stubbed or no data)")

    if m_err:
        if _is_tier_gated_http_403(m_err):
            tier_gated_components.append("macro_events")
        else:
            fail_reasons.append(f"macro_events:{m_err}")
    elif coverage["items"]["macro_events_count"] == 0:
        warn_reasons.append("Macro Events Empty (Not exposed or Tier Gated)")

    if fail_reasons:
        coverage["status"] = "FAIL"
        reasons = []
        if tier_gated_components:
            reasons.append(_format_tier_gated_reason(tier_gated_components))
        reasons.extend(sorted(fail_reasons))
        coverage["reason"] = " | ".join(reasons)
    elif tier_gated_components:
        coverage["status"] = "WARN"
        coverage["reason"] = _format_tier_gated_reason(tier_gated_components)
    elif warn_reasons:
        coverage["status"] = "WARN"
        coverage["reason"] = " | ".join(warn_reasons)

    # Write derived files
    n_path = DERIVED_ROOT_NARRATIVES / f"{ts_utc}.json"
    m_path = DERIVED_ROOT_MACRO / f"{ts_utc}.json"
    
    _safe_write_json(n_path, narratives_payload)
    _safe_write_json(m_path, macro_payload)
    
    # Write Telemetry & Manifest
    _safe_write_json(ATOMIC_COVERAGE_PATH, coverage)
    log.info("Wrote atomic coverage: status=%s, reason=%s", coverage["status"], coverage.get("reason", "OK"))
    
    write_manifest(ts_utc)

    return 0


if __name__ == "__main__":
    sys.exit(main())
