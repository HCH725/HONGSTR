from hongstr.control_plane.allowlist import (
    allowed_action_names,
    command_for_action,
    sanitize_action_requests,
)
from hongstr.control_plane.schema import AllowedAction, ControlPlaneDecision, ControlPlaneInputEvent


def test_input_event_schema_parses():
    event = ControlPlaneInputEvent(
        event_id="evt_test",
        source="unit",
        payload={"k": "v"},
    )
    assert event.event_id == "evt_test"
    assert event.payload["k"] == "v"


def test_allowlist_actions_and_commands():
    names = allowed_action_names()
    assert AllowedAction.RUN_DAILY_ETL.value in names
    cmd = command_for_action(AllowedAction.RUN_HEALTHCHECK_DASHBOARD)
    assert cmd[0] == "/bin/bash"
    assert cmd[1].endswith("scripts/healthcheck_dashboard.sh")


def test_disallow_unknown_action_and_keep_note():
    allowed, rejected = sanitize_action_requests(
        [
            {"action": "RUN_DAILY_ETL", "reason": "freshen data"},
            {"action": "DROP_DATABASE", "reason": "bad"},
        ]
    )
    assert allowed == [{"action": "RUN_DAILY_ETL", "reason": "freshen data"}]
    assert rejected == ["DROP_DATABASE"]


def test_decision_rejects_unknown_enum_action():
    try:
        ControlPlaneDecision.model_validate(
            {
                "status": "WARN",
                "diagnosis": "x",
                "summary": "y",
                "actions": [{"action": "DROP_DATABASE", "reason": "never"}],
            }
        )
    except Exception:
        assert True
    else:
        assert False, "Unknown action should fail strict schema validation"
