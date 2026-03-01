"""
Shared utilities for injecting SSOT provenance metadata into canonical states.
"""
import hashlib
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

def _get_producer_git_sha():
    try:
        ans = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True
        ).strip()
        return ans if ans else "UNKNOWN"
    except Exception:
        return "UNKNOWN"

def _fingerprint_file(p: Path) -> str:
    """Read up to 64KB from start and end of file for a secure, fast hash."""
    chunk_size = 65536
    try:
        h = hashlib.sha256()
        with open(p, "rb") as f:
            f.seek(0, 2)
            size = f.tell()
            
            if size <= chunk_size * 2:
                f.seek(0)
                h.update(f.read())
            else:
                f.seek(0)
                h.update(f.read(chunk_size))
                
                f.seek(size - chunk_size)
                h.update(f.read(chunk_size))
                
        return h.hexdigest()[:16]
    except Exception:
        return "UNKNOWN"

def add_ssot_meta(payload: dict, source_paths: list = None, notes: str = "") -> dict:
    """
    Inject robust SSOT provenance metadata.
    
    Args:
        payload: The business state dict.
        source_paths: Array of paths (strings or Path objects) from which state was derived.
        notes: Optional qualitative audit trail details.
    """
    repo_root = Path(__file__).resolve().parent.parent
    
    source_inputs = []
    if source_paths:
        for rp in source_paths:
            p = Path(rp) if os.path.isabs(rp) else (repo_root / rp).resolve()
            if p.exists():
                st = p.stat()
                try:
                    rel = str(p.relative_to(repo_root))
                except Exception:
                    rel = str(p)
                    
                source_inputs.append({
                    "path": rel,
                    "mtime_utc": datetime.fromtimestamp(st.st_mtime, timezone.utc).isoformat(),
                    "size_bytes": st.st_size,
                    "fingerprint": _fingerprint_file(p)
                })

    meta = {
        "schema_version": "1.0",
        "producer_git_sha": _get_producer_git_sha(),
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "source_inputs": source_inputs,
        "notes": notes
    }
    
    # Merge, keeping meta at the top logically if dumping later
    merged = {**meta, **payload}
    
    # Force 'source_inputs' to exist even if empty to satisfy schema
    if "source_inputs" not in merged:
         merged["source_inputs"] = source_inputs

    return merged
