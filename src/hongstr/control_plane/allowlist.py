from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from .schema import AllowedAction

REPO_ROOT = Path(__file__).resolve().parents[3]

ALLOWLIST_COMMANDS: dict[AllowedAction, list[str]] = {
    AllowedAction.RUN_DAILY_ETL: ["/bin/bash", str(REPO_ROOT / "scripts/daily_etl.sh")],
    AllowedAction.RUN_WEEKLY_BACKFILL: [
        "/bin/bash",
        str(REPO_ROOT / "scripts/backfill_1m_from_2020.sh"),
    ],
    AllowedAction.RUN_RECOVER_DASHBOARD_FULL: [
        "/bin/bash",
        str(REPO_ROOT / "scripts/recover_dashboard_full.sh"),
    ],
    AllowedAction.RUN_HEALTHCHECK_DASHBOARD: [
        "/bin/bash",
        str(REPO_ROOT / "scripts/healthcheck_dashboard.sh"),
    ],
    AllowedAction.RUN_CHECK_DATA_COVERAGE: [
        "/bin/bash",
        str(REPO_ROOT / "scripts/check_data_coverage.sh"),
    ],
    AllowedAction.RUN_TG_SANITY: ["/bin/bash", str(REPO_ROOT / "scripts/tg_sanity.sh")],
    AllowedAction.OPEN_ISSUE_SUGGESTION: [
        "/bin/bash",
        str(REPO_ROOT / "scripts/control_plane_run.sh"),
        "--suggest-issue",
    ],
}


def allowed_action_names() -> set[str]:
    return {a.value for a in AllowedAction}


def command_for_action(action: AllowedAction) -> list[str]:
    return ALLOWLIST_COMMANDS[action]


def sanitize_action_requests(
    raw_actions: Iterable[Any],
) -> tuple[list[dict[str, str]], list[str]]:
    allowed: list[dict[str, str]] = []
    rejected: list[str] = []
    allowed_names = allowed_action_names()

    for item in raw_actions:
        action_name = ""
        reason = ""
        if isinstance(item, dict):
            action_name = str(item.get("action", "")).strip()
            reason = str(item.get("reason", "")).strip()
        else:
            action_name = str(item).strip()

        if not action_name:
            continue

        if action_name in allowed_names:
            allowed.append({"action": action_name, "reason": reason})
        else:
            rejected.append(action_name)

    return allowed, rejected
