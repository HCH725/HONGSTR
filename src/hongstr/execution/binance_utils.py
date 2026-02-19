import hmac
import hashlib
import time
import urllib.parse
from typing import Dict, Tuple, Optional

def build_signed_request(
    method: str, 
    base_url: str, 
    endpoint_path: str, 
    params: Dict, 
    api_key: str, 
    api_secret: str, 
    debug: bool = False
) -> Tuple[str, Dict, Optional[str]]:
    """
    Centralized Binance signing and request building with deterministic debugging.
    Returns (final_url, headers, debug_output).
    """
    # 1. Prepare params copy to avoid mutation
    p = params.copy()
    if 'timestamp' not in p:
        p['timestamp'] = int(time.time() * 1000)
    
    # 2. Build pre-sign query string
    # Binance requires specific order often, or at least consistency.
    # We sort keys to be 100% deterministic.
    sorted_items = sorted(p.items())
    pre_sign_qs = urllib.parse.urlencode(sorted_items, doseq=True)
    
    # 3. Compute Signature
    signature = hmac.new(
        api_secret.encode('utf-8'), 
        pre_sign_qs.encode('utf-8'), 
        hashlib.sha256
    ).hexdigest()
    
    # 4. Build Final URL
    # Append signature to the same qs used for signing
    final_url = f"{base_url}{endpoint_path}?{pre_sign_qs}&signature={signature}"
    
    headers = {"X-MBX-APIKEY": api_key}
    
    debug_output = None
    if debug:
        # Redact secrets for display
        redacted_params = {k: ("****" if k in ["signature", "api_secret", "secret"] else v) for k, v in p.items()}
        # API key redaction: prefix 3 + len (e.g. KPV... (64))
        key_show = f"{api_key[:3]}... ({len(api_key)})" if api_key else "None"
        # signature redaction: prefix 8 + len
        sig_show = f"{signature[:8]}... ({len(signature)})"
        
        final_url_no_sig = f"{base_url}{endpoint_path}?{pre_sign_qs}"
        final_url_redacted_sig = f"{final_url_no_sig}&signature={signature[:8]}****"

        debug_lines = [
            "--- Binance Signing Debug ---",
            f"Base URL:      {base_url}",
            f"HTTP Method:   {method.upper()}",
            f"Endpoint:      {endpoint_path}",
            f"API Key:       {key_show}",
            f"Params (Raw):  {sorted(redacted_params.items())}",
            f"Pre-Sign QS:   {pre_sign_qs}",
            f"Signature:     {sig_show}",
            f"Final URL(S):  {final_url_redacted_sig}",
            f"Final URL(U):  {final_url_no_sig}",
            f"Timestamp:     {p['timestamp']}",
            f"RecvWindow:    {p.get('recvWindow', 'Default')}",
            "Sent Mode:     sent_with_final_url_only: true",
            "Note: urlencode performed exactly once on sorted items.",
            "------------------------------"
        ]
        debug_output = "\n".join(debug_lines)
        
    return final_url, headers, debug_output
