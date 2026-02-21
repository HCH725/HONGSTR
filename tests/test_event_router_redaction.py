import json
import subprocess
import sys
from pathlib import Path


def test_event_router_redacts_sensitive_values(tmp_path):
    repo = tmp_path
    (repo / "reports").mkdir(parents=True, exist_ok=True)
    (repo / "logs").mkdir(parents=True, exist_ok=True)
    (repo / "scripts").mkdir(parents=True, exist_ok=True)

    (repo / "reports" / "gate_latest.md").write_text(
        "TG_BOT_TOKEN=123456:ABCDEF_secret\napi_key=HELLO\n",
        encoding="utf-8",
    )
    (repo / "logs" / "launchd_daily_etl.out.log").write_text(
        "TG_CHAT_ID=887536140\nhttps://api.example.com?token=abc123\n",
        encoding="utf-8",
    )

    out = repo / "data" / "events" / "latest_event.json"
    script = Path(__file__).resolve().parents[1] / "scripts" / "event_router.py"

    subprocess.run(
        [
            sys.executable,
            str(script),
            "--repo-root",
            str(repo),
            "--output",
            str(out),
            "--skip-commands",
            "--tail-lines",
            "20",
        ],
        check=True,
    )

    text = out.read_text(encoding="utf-8")
    assert "123456:ABCDEF_secret" not in text
    assert "887536140" not in text
    assert "token=abc123" not in text
    assert "***REDACTED***" in text

    data = json.loads(text)
    assert data["source"] == "event_router"
    assert "payload" in data
