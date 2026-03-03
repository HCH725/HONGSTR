from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


@dataclass
class AuditIssue:
    type: str
    severity: str
    description: str
    evidence: str = ""

    def to_dict(self) -> dict[str, Any]:
        out = {
            "type": self.type,
            "severity": self.severity,
            "description": self.description,
        }
        if self.evidence:
            out["evidence"] = self.evidence
        return out


class SignalLeakageAudit:
    """Read-only leakage + lookahead audit over research/report artifacts."""

    def __init__(self, max_allowed_lookahead_ms: int = 0) -> None:
        self.max_allowed_lookahead_ms = int(max_allowed_lookahead_ms)

    def audit(
        self,
        panel: pd.DataFrame,
        features: pd.DataFrame,
        labels: pd.DataFrame,
    ) -> dict[str, Any]:
        issues: list[AuditIssue] = []

        panel = _normalize_df(panel)
        features = _normalize_df(features)
        labels = _normalize_df(labels)

        # 1) strict index alignment
        if not features.index.equals(labels.index):
            issues.append(
                AuditIssue(
                    type="misalign",
                    severity="HIGH",
                    description="Features and labels indices are not aligned.",
                    evidence=f"features_rows={len(features)}, labels_rows={len(labels)}",
                )
            )

        # 2) future fill detection via source_ts metadata
        if "source_ts" in features.columns:
            src_ts = pd.to_datetime(features["source_ts"], utc=True, errors="coerce")
            idx_ts = pd.to_datetime(features.index.get_level_values("ts"), utc=True, errors="coerce")
            delta_ms = (src_ts - idx_ts).dt.total_seconds() * 1000.0
            bad = delta_ms > float(self.max_allowed_lookahead_ms)
            bad_count = int(bad.fillna(False).sum())
            if bad_count > 0:
                max_ms = float(delta_ms[bad].max())
                issues.append(
                    AuditIssue(
                        type="future_fill",
                        severity="HIGH",
                        description="Feature source timestamp is ahead of feature timestamp.",
                        evidence=f"bad_rows={bad_count}, max_future_ms={max_ms:.1f}",
                    )
                )

        # 3) lookahead leakage heuristic: perfect/near-perfect correlation to label
        if "direction" in labels.columns:
            y = _safe_numeric_series(labels["direction"]) if not labels.empty else pd.Series(dtype=float)
            for col in features.columns:
                if col == "source_ts":
                    continue
                x = _safe_numeric_series(features[col])
                if x.empty or y.empty or len(x) != len(y):
                    continue
                if x.nunique(dropna=True) <= 1:
                    continue
                corr = x.corr(y)
                if pd.notna(corr) and abs(float(corr)) >= 0.999:
                    issues.append(
                        AuditIssue(
                            type="lookahead",
                            severity="HIGH",
                            description=f"Feature '{col}' is near-perfectly correlated with label direction.",
                            evidence=f"corr={float(corr):.6f}",
                        )
                    )

        # 4) direct future-return equality check when close exists
        if "close" in panel.columns and "direction" in labels.columns:
            for sym in panel.index.get_level_values("symbol").unique():
                p_sym = panel.xs(sym, level="symbol", drop_level=False)
                if p_sym.empty:
                    continue
                fut_dir = (
                    p_sym["close"].groupby("symbol").shift(-1) > p_sym["close"]
                ).astype(float)
                common_idx = fut_dir.index.intersection(labels.index)
                if len(common_idx) == 0:
                    continue
                y = labels.loc[common_idx, "direction"].astype(float)
                # Use first numeric feature candidate
                for col in [c for c in features.columns if c != "source_ts"]:
                    x = pd.to_numeric(features.loc[common_idx, col], errors="coerce")
                    mask = x.notna() & y.notna()
                    if int(mask.sum()) == 0:
                        continue
                    if np.allclose(x[mask].to_numpy(), y[mask].to_numpy(), atol=1e-12, rtol=0.0):
                        issues.append(
                            AuditIssue(
                                type="lookahead",
                                severity="HIGH",
                                description=f"Feature '{col}' equals label direction for symbol={sym}.",
                                evidence="value-equality check",
                            )
                        )
                        break

        # dedupe by (type, description)
        uniq: dict[tuple[str, str], AuditIssue] = {}
        for iss in issues:
            uniq[(iss.type, iss.description)] = iss
        issues = list(uniq.values())

        status = "FAIL" if issues else "OK"
        summary = f"audit_complete issues={len(issues)} status={status}"
        return {
            "summary": summary,
            "issues": [i.to_dict() for i in issues],
            "status": status,
            "report_only": True,
        }


def audit_from_artifact(repo_root: Path, artifact_path: str, max_allowed_lookahead_ms: int = 0) -> dict[str, Any]:
    """Load panel/features/labels from artifact JSON under research/ or reports/ only."""
    repo_root = Path(repo_root).resolve()
    p = (repo_root / artifact_path).resolve()

    allowed_roots = [(repo_root / "research").resolve(), (repo_root / "reports").resolve()]
    if not any(_is_relative_to(p, root) for root in allowed_roots):
        return {
            "summary": "artifact_path_out_of_scope",
            "status": "UNKNOWN",
            "report_only": True,
            "issues": [
                {
                    "type": "scope",
                    "severity": "HIGH",
                    "description": "artifact_path must be under research/ or reports/",
                    "evidence": artifact_path,
                }
            ],
            "refresh_hint": "Use research/ or reports/ artifact paths only",
        }

    if not p.exists():
        return {
            "summary": "artifact_missing",
            "status": "UNKNOWN",
            "report_only": True,
            "issues": [
                {
                    "type": "missing",
                    "severity": "HIGH",
                    "description": "artifact file not found",
                    "evidence": str(p.relative_to(repo_root)),
                }
            ],
            "refresh_hint": "Provide artifact JSON under research/ or reports/",
        }

    payload = json.loads(p.read_text(encoding="utf-8"))
    panel = pd.DataFrame(payload.get("panel", []))
    features = pd.DataFrame(payload.get("features", []))
    labels = pd.DataFrame(payload.get("labels", []))

    audit = SignalLeakageAudit(max_allowed_lookahead_ms=max_allowed_lookahead_ms)
    out = audit.audit(panel=panel, features=features, labels=labels)
    out["artifact"] = str(p.relative_to(repo_root))
    return out


def _normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    if not isinstance(df, pd.DataFrame):
        return pd.DataFrame()
    if "ts" not in df.columns or "symbol" not in df.columns:
        return pd.DataFrame()
    out = df.copy()
    out["ts"] = pd.to_datetime(out["ts"], utc=True, errors="coerce")
    out = out.dropna(subset=["ts", "symbol"])  # type: ignore[arg-type]
    out = out.set_index(["ts", "symbol"]).sort_index()
    return out


def _safe_numeric_series(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce")


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except Exception:
        return False
