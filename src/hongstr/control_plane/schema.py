from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class AllowedAction(str, Enum):
    RUN_DAILY_ETL = "RUN_DAILY_ETL"
    RUN_WEEKLY_BACKFILL = "RUN_WEEKLY_BACKFILL"
    RUN_RECOVER_DASHBOARD_FULL = "RUN_RECOVER_DASHBOARD_FULL"
    RUN_HEALTHCHECK_DASHBOARD = "RUN_HEALTHCHECK_DASHBOARD"
    RUN_CHECK_DATA_COVERAGE = "RUN_CHECK_DATA_COVERAGE"
    RUN_TG_SANITY = "RUN_TG_SANITY"
    OPEN_ISSUE_SUGGESTION = "OPEN_ISSUE_SUGGESTION"


class LLMStatus(str, Enum):
    OK = "OK"
    WARN = "WARN"
    FAIL = "FAIL"


class ControlPlaneInputEvent(BaseModel):
    schema_version: str = "1.0"
    event_id: str
    created_at_utc: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source: str = "event_router"
    payload: dict[str, Any] = Field(default_factory=dict)


class ActionPlan(BaseModel):
    action: AllowedAction
    reason: str = ""


class ControlPlaneDecision(BaseModel):
    schema_version: str = "1.0"
    created_at_utc: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    event_id: str = ""
    llm_mode: str = "null"
    status: LLMStatus = LLMStatus.WARN
    diagnosis: str = ""
    summary: str = ""
    next_tasks: list[str] = Field(default_factory=list)
    remediation_suggestions: list[str] = Field(default_factory=list)
    actions: list[ActionPlan] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)

    @field_validator("next_tasks", "remediation_suggestions", "notes", mode="before")
    @classmethod
    def _coerce_str_list(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(v).strip() for v in value if str(v).strip()]
        text = str(value).strip()
        return [text] if text else []
