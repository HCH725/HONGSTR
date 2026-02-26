from __future__ import annotations

import itertools
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_CATALOG_PATH = REPO_ROOT / "research/policy/candidate_catalog.json"


@dataclass(frozen=True)
class CandidateSpec:
    candidate_id: str
    strategy_id: str
    family: str
    symbol: str
    timeframe: str
    direction: str
    variant: str
    parameters: dict[str, Any]
    execution_model: str
    base_strategy: str | None = None
    report_only: bool = True

    def as_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "strategy_id": self.strategy_id,
            "family": self.family,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "direction": self.direction,
            "variant": self.variant,
            "parameters": dict(self.parameters),
            "execution_model": self.execution_model,
            "base_strategy": self.base_strategy,
            "report_only": self.report_only,
        }


def load_candidate_catalog(path: Path | None = None) -> dict[str, Any]:
    p = (path or DEFAULT_CATALOG_PATH).resolve()
    raw = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"Candidate catalog must be an object: {p}")
    return raw


def _safe_token(v: Any) -> str:
    txt = str(v).strip().lower()
    allowed = []
    for ch in txt:
        if ch.isalnum():
            allowed.append(ch)
        elif ch in {"_", "-", "."}:
            allowed.append(ch)
        else:
            allowed.append("_")
    return "".join(allowed).strip("_") or "na"


def _build_candidate_id(strategy_id: str, direction: str, variant: str, sweep_idx: int | None = None) -> str:
    parts = [_safe_token(strategy_id), _safe_token(direction), _safe_token(variant)]
    if sweep_idx is not None:
        parts.append(f"s{sweep_idx:02d}")
    return "__".join(parts)


def _sweep_params(
    base: dict[str, Any],
    sweep_cfg: dict[str, Any] | None,
    max_sweep_variants: int,
) -> list[tuple[int | None, dict[str, Any]]]:
    if not sweep_cfg:
        return [(None, dict(base))]

    keys = sorted(k for k, v in sweep_cfg.items() if isinstance(v, list) and len(v) > 0)
    if not keys:
        return [(None, dict(base))]

    value_lists = [sweep_cfg[k] for k in keys]
    all_combos = list(itertools.product(*value_lists))

    if len(all_combos) > max_sweep_variants:
        if max_sweep_variants == 1:
            sampled = [all_combos[0]]
        else:
            step = (len(all_combos) - 1) / float(max_sweep_variants - 1)
            sampled_idx = sorted({int(round(i * step)) for i in range(max_sweep_variants)})
            sampled = [all_combos[i] for i in sampled_idx]
    else:
        sampled = all_combos

    out: list[tuple[int | None, dict[str, Any]]] = []
    for idx, combo in enumerate(sampled, start=1):
        params = dict(base)
        for key, value in zip(keys, combo):
            params[key] = value
        out.append((idx, params))
    return out or [(None, dict(base))]


def build_candidate_specs(
    catalog: dict[str, Any] | None = None,
    *,
    include_dca: bool | None = None,
    max_candidates: int | None = None,
    max_sweep_variants: int | None = None,
) -> list[CandidateSpec]:
    cfg = catalog or load_candidate_catalog()
    defaults = cfg.get("defaults", {}) if isinstance(cfg.get("defaults"), dict) else {}

    include_dca_flag = include_dca
    if include_dca_flag is None:
        include_dca_flag = os.getenv("HONGSTR_ENABLE_DCA1_SWEEP", "1").strip() not in {"0", "false", "False"}

    sweep_cap = max_sweep_variants
    if sweep_cap is None:
        sweep_cap = int(os.getenv("HONGSTR_DCA_SWEEP_MAX", "6"))
    sweep_cap = max(1, int(sweep_cap))

    specs: list[CandidateSpec] = []

    families = cfg.get("families", [])
    if not isinstance(families, list):
        return specs

    for fam in families:
        if not isinstance(fam, dict):
            continue
        family = str(fam.get("family", "")).strip().lower()
        if not family:
            continue
        if fam.get("enabled", True) is False:
            continue
        if family == "dca1" and not include_dca_flag:
            continue

        strategies = fam.get("strategies", [])
        if not isinstance(strategies, list):
            continue

        for raw in strategies:
            if not isinstance(raw, dict):
                continue
            strategy_id = str(raw.get("strategy_id", "")).strip()
            if not strategy_id:
                continue

            symbol = str(raw.get("symbol") or defaults.get("symbol") or "BTCUSDT")
            timeframe = str(raw.get("timeframe") or defaults.get("timeframe") or "1h")
            variant = str(raw.get("variant") or "base")
            directions = raw.get("directions") or ["LONG"]
            if not isinstance(directions, list):
                directions = ["LONG"]
            base_params = raw.get("parameters", {}) if isinstance(raw.get("parameters"), dict) else {}
            base_strategy = raw.get("base_strategy")
            execution_model = "dca1" if family == "dca1" else "spot"

            sweep_cfg = raw.get("sweep") if isinstance(raw.get("sweep"), dict) else None
            param_variants = _sweep_params(base_params, sweep_cfg, sweep_cap)

            for direction in directions:
                for sweep_idx, params in param_variants:
                    cid = _build_candidate_id(
                        strategy_id,
                        str(direction).upper(),
                        variant,
                        sweep_idx=sweep_idx if sweep_cfg else None,
                    )
                    specs.append(
                        CandidateSpec(
                            candidate_id=cid,
                            strategy_id=strategy_id,
                            family=family,
                            symbol=symbol,
                            timeframe=timeframe,
                            direction=str(direction).upper(),
                            variant=variant,
                            parameters=dict(params),
                            execution_model=execution_model,
                            base_strategy=str(base_strategy) if base_strategy else None,
                            report_only=True,
                        )
                    )
                    if max_candidates is not None and len(specs) >= max_candidates:
                        return specs

    return specs


def build_candidate_catalog(**kwargs: Any) -> list[dict[str, Any]]:
    return [s.as_dict() for s in build_candidate_specs(**kwargs)]


def summarize_catalog(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    fam_counts: dict[str, int] = {}
    direction_counts: dict[str, int] = {}
    strategy_ids: set[str] = set()

    for c in candidates:
        family = str(c.get("family", "unknown"))
        direction = str(c.get("direction", "unknown"))
        fam_counts[family] = fam_counts.get(family, 0) + 1
        direction_counts[direction] = direction_counts.get(direction, 0) + 1
        sid = str(c.get("strategy_id", "")).strip()
        if sid:
            strategy_ids.add(sid)

    return {
        "total_candidates": len(candidates),
        "family_counts": fam_counts,
        "direction_counts": direction_counts,
        "strategy_count": len(strategy_ids),
        "strategy_ids": sorted(strategy_ids),
    }
