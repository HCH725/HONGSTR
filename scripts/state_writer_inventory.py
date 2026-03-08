#!/usr/bin/env python3
"""
Canonical writer inventory for Stage 2 State Plane artifacts.

This module is the machine-checkable source of truth for:
- which data/state artifacts are canonical outputs
- which script is allowed to write them
- which script is only allowed to orchestrate publication
- which owner plane governs the artifacts
"""
from __future__ import annotations

from typing import Any


DESIGNATED_WRITER = "scripts/state_snapshots.py"
DESIGNATED_ORCHESTRATOR = "scripts/refresh_state.sh"
ALLOWED_OWNER_PLANES = ("STATE",)
DEFAULT_UPDATE_CADENCE = "per refresh_state run"
DEFAULT_OWNER_ROLE = "state_plane_ssot_writer"
DEFAULT_RESPONSIBILITY = "Publish canonical state-plane snapshot for read-only consumers."
DEFAULT_DEGRADE_HINT = (
    "If this artifact is missing or stale, rerun bash scripts/refresh_state.sh and treat downstream reads as "
    "UNKNOWN/stale instead of inventing a second writer."
)
DEFAULT_KILL_HINT = "Any non-test write outside scripts/state_snapshots.py is a writer-boundary violation."
DEFAULT_SOP_HINT = "bash scripts/refresh_state.sh"


def _entry(
    artifact_id: str,
    canonical_path: str,
    *,
    publication_tier: str,
    responsibility: str = DEFAULT_RESPONSIBILITY,
    update_cadence: str = DEFAULT_UPDATE_CADENCE,
    owner_plane: str = "STATE",
    owner_role: str = DEFAULT_OWNER_ROLE,
    status: str = "active",
    designated_writer: str = DESIGNATED_WRITER,
    designated_orchestrator: str = DESIGNATED_ORCHESTRATOR,
    degrade_hint: str = DEFAULT_DEGRADE_HINT,
    kill_hint: str = DEFAULT_KILL_HINT,
    sop_hint: str = DEFAULT_SOP_HINT,
) -> dict[str, Any]:
    return {
        "artifact_id": artifact_id,
        "canonical_path": canonical_path,
        "designated_writer": designated_writer,
        "designated_orchestrator": designated_orchestrator,
        "owner_plane": owner_plane,
        "owner_role": owner_role,
        "publication_tier": publication_tier,
        "status": status,
        "update_cadence": update_cadence,
        "responsibility": responsibility,
        "degrade_hint": degrade_hint,
        "kill_hint": kill_hint,
        "sop_hint": sop_hint,
    }


CANONICAL_STATE_WRITER_INVENTORY: tuple[dict[str, Any], ...] = (
    _entry(
        "coverage_table",
        "data/state/coverage_table.jsonl",
        publication_tier="coverage_input_table",
        responsibility="Publish the canonical coverage row table derived from atomic coverage inputs.",
    ),
    _entry(
        "coverage_latest",
        "data/state/coverage_latest.json",
        publication_tier="coverage_summary",
        responsibility="Publish the latest coverage row per symbol/timeframe/regime for read-only consumers.",
    ),
    _entry(
        "coverage_summary",
        "data/state/coverage_summary.json",
        publication_tier="coverage_summary",
        responsibility="Publish aggregate coverage counts and pass-rate summary for state-plane consumers.",
    ),
    _entry(
        "strategy_pool_summary",
        "data/state/strategy_pool_summary.json",
        publication_tier="strategy_summary",
        responsibility="Publish the read-only strategy pool summary derived from strategy_pool.json.",
    ),
    _entry(
        "regime_monitor_latest",
        "data/state/regime_monitor_latest.json",
        publication_tier="health_component",
        responsibility="Publish the canonical regime monitor snapshot from atomic regime input.",
    ),
    _entry(
        "regime_monitor_summary",
        "data/state/regime_monitor_summary.json",
        publication_tier="health_summary",
        responsibility="Publish the read-only regime monitor summary derived from regime_monitor_latest.",
    ),
    _entry(
        "freshness_table",
        "data/state/freshness_table.json",
        publication_tier="data_plane_contract",
        responsibility="Publish the canonical freshness table and row-level data-quality gate fields.",
    ),
    _entry(
        "execution_mode",
        "data/state/execution_mode.json",
        publication_tier="health_component",
        responsibility="Publish the canonical execution mode snapshot for state-plane consumers.",
    ),
    _entry(
        "cmc_market_intel_coverage_latest",
        "data/state/cmc_market_intel_coverage_latest.json",
        publication_tier="dataset_coverage",
        responsibility="Publish canonical CMC market intel coverage from atomic producer output.",
    ),
    _entry(
        "services_heartbeat",
        "data/state/services_heartbeat.json",
        publication_tier="health_component",
        responsibility="Publish the canonical services heartbeat snapshot for launchd/log consumers.",
    ),
    _entry(
        "coverage_matrix_latest",
        "data/state/coverage_matrix_latest.json",
        publication_tier="data_plane_contract",
        responsibility="Publish the canonical coverage matrix and row-level reason/source/evidence fields.",
    ),
    _entry(
        "brake_health_latest",
        "data/state/brake_health_latest.json",
        publication_tier="health_component",
        responsibility="Publish the canonical brake health snapshot from atomic brake input.",
    ),
    _entry(
        "watchdog_status_latest",
        "data/state/watchdog_status_latest.json",
        publication_tier="health_component",
        responsibility="Publish the canonical watchdog status snapshot from atomic watchdog input.",
    ),
    _entry(
        "cost_sensitivity_matrix_latest",
        "data/state/cost_sensitivity_matrix_latest.json",
        publication_tier="health_component",
        responsibility="Publish the canonical cost-sensitivity matrix for state-plane read-only consumers.",
    ),
    _entry(
        "data_catalog_latest",
        "data/state/data_catalog_latest.json",
        publication_tier="catalog_contract",
        responsibility="Publish the canonical data catalog compiled from atomic dataset manifests.",
    ),
    _entry(
        "data_catalog_changes_latest",
        "data/state/data_catalog_changes_latest.json",
        publication_tier="catalog_contract",
        responsibility="Publish the canonical data catalog diff versus the previous snapshot.",
    ),
    _entry(
        "changes_latest",
        "data/state/changes_latest.json",
        publication_tier="catalog_alias",
        responsibility="Publish the canonical alias view over data_catalog_changes_latest for read-only consumers.",
    ),
    _entry(
        "data_catalog_prev",
        "data/state/_history/data_catalog_prev.json",
        publication_tier="internal_history",
        responsibility="Persist the previous canonical data catalog snapshot for change diffing.",
    ),
    _entry(
        "okx_public_coverage_latest",
        "data/state/okx_public_coverage_latest.json",
        publication_tier="dataset_coverage",
        responsibility="Publish canonical OKX public coverage from atomic producer output.",
    ),
    _entry(
        "bitfinex_public_coverage_latest",
        "data/state/bitfinex_public_coverage_latest.json",
        publication_tier="dataset_coverage",
        responsibility="Publish canonical Bitfinex public coverage from atomic producer output.",
    ),
    _entry(
        "system_health_latest",
        "data/state/system_health_latest.json",
        publication_tier="health_pack",
        responsibility="Publish the canonical SystemHealth pack for status consumers.",
    ),
    _entry(
        "daily_report_latest",
        "data/state/daily_report_latest.json",
        publication_tier="daily_single_entry",
        responsibility="Publish the canonical daily report single-entry payload for read-only consumers.",
    ),
    _entry(
        "strategy_dashboard_latest",
        "data/state/strategy_dashboard_latest.json",
        publication_tier="strategy_surface",
        responsibility="Publish the canonical strategy dashboard payload for strategy-only surfaces.",
    ),
)

INVENTORY_BY_PATH = {
    entry["canonical_path"]: entry for entry in CANONICAL_STATE_WRITER_INVENTORY
}


def inventory_paths() -> tuple[str, ...]:
    return tuple(sorted(INVENTORY_BY_PATH))


def inventory_filenames() -> tuple[str, ...]:
    return tuple(sorted(path.rsplit("/", 1)[-1] for path in INVENTORY_BY_PATH))
