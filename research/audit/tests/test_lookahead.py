import json
from pathlib import Path

from research.audit.lookahead import SignalLeakageAudit, audit_from_artifact

FIX = Path("/Users/hong/Projects/HONGSTR/research/audit/tests/fixtures")


def _load_triplet(name: str):
    p = FIX / f"{name}.json"
    obj = json.loads(p.read_text(encoding="utf-8"))
    return obj["panel"], obj["features"], obj["labels"]


def test_clean_case_ok():
    panel, features, labels = _load_triplet("clean")
    import pandas as pd

    audit = SignalLeakageAudit(max_allowed_lookahead_ms=0)
    out = audit.audit(pd.DataFrame(panel), pd.DataFrame(features), pd.DataFrame(labels))
    assert out["status"] == "OK"
    assert out["issues"] == []
    assert out["report_only"] is True


def test_lookahead_case_detected():
    panel, features, labels = _load_triplet("lookahead")
    import pandas as pd

    audit = SignalLeakageAudit(max_allowed_lookahead_ms=0)
    out = audit.audit(pd.DataFrame(panel), pd.DataFrame(features), pd.DataFrame(labels))
    assert out["status"] == "FAIL"
    assert any(i["type"] == "lookahead" for i in out["issues"])


def test_misalign_case_detected():
    panel, features, labels = _load_triplet("misalign")
    import pandas as pd

    audit = SignalLeakageAudit(max_allowed_lookahead_ms=0)
    out = audit.audit(pd.DataFrame(panel), pd.DataFrame(features), pd.DataFrame(labels))
    assert out["status"] == "FAIL"
    assert any(i["type"] == "misalign" for i in out["issues"])


def test_future_fill_case_detected():
    panel, features, labels = _load_triplet("future_fill")
    import pandas as pd

    audit = SignalLeakageAudit(max_allowed_lookahead_ms=0)
    out = audit.audit(pd.DataFrame(panel), pd.DataFrame(features), pd.DataFrame(labels))
    assert out["status"] == "FAIL"
    assert any(i["type"] == "future_fill" for i in out["issues"])


def test_artifact_path_scope_guard(tmp_path):
    bad = tmp_path / "artifact.json"
    bad.write_text("{}", encoding="utf-8")
    out = audit_from_artifact(Path("/Users/hong/Projects/HONGSTR"), str(bad), max_allowed_lookahead_ms=0)
    assert out["status"] == "UNKNOWN"
    assert any(i["type"] == "scope" for i in out["issues"])
