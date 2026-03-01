import subprocess
from datetime import datetime, timezone

def _get_git_sha(fallback="UNKNOWN_GIT_SHA"):
    """Robustly fetch short git SHAs, falling back on any system failure."""
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=2.0
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout.strip()
    except Exception:
        pass
    return fallback

def add_ssot_meta(payload: dict, source_inputs: list = None, notes: str = None) -> dict:
    """
    Inject central SSOT provenance metadata into identical payload level keys.
    Requires that the returned metadata structure is flat underneath payload.
    """
    now = datetime.now(timezone.utc)
    
    payload["schema_version"] = "1.0"
    
    sha = _get_git_sha()
    payload["producer_git_sha"] = sha
    
    payload["generated_utc"] = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    
    payload["source_inputs"] = source_inputs or []
    if notes:
        payload["notes"] = notes
    if sha == "UNKNOWN_GIT_SHA":
        payload["notes"] = (payload.get("notes", "") + " | git_sha_error").strip(" |")

    return payload
