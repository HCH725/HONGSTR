import importlib.util
import json
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts/governance/lightweight_ci_gate.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("lightweight_ci_gate_testmod", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def test_missing_sections_detects_required_governance_fields():
    mod = _load_module()
    content = "## Stage\n\n- Stage 0\n\n## Evidence\n\n- guardrail_check: PASS\n"

    missing = mod._missing_sections(content, mod.REQUIRED_SECTION_PATTERNS)

    assert "Stage" not in missing
    assert "Evidence" not in missing
    assert "Checklist item" in missing
    assert "Degrade" in missing
    assert "Legacy Impact" in missing


def test_governance_candidate_detects_signal_paths_and_pr_body():
    mod = _load_module()

    assert mod._is_governance_candidate(["docs/governance/acceptance_criteria.md"], "")
    assert mod._is_governance_candidate([".agents/rules/hongstr-solid-rules.md"], "")
    assert mod._is_governance_candidate([".opencode/rules.md"], "")
    assert mod._is_governance_candidate(["scripts/governance/lightweight_ci_gate.py"], "")
    assert mod._is_governance_candidate(
        ["scripts/run_dashboard.sh"], "## Plane\n\n- Governance / CI\n"
    )
    assert not mod._is_governance_candidate(
        ["scripts/run_dashboard.sh"], "## Plane\n\n- Runtime\n"
    )


def test_split_governance_path_violations_separates_forbidden_and_outside_scope():
    mod = _load_module()

    forbidden, outside_allowed = mod._split_governance_path_violations(
        [
            ".github/workflows/guardrails.yml",
            ".agents/rules/hongstr-solid-rules.md",
            ".opencode/rules.md",
            "web/app/api/status/route.ts",
            "ops/runbook.md",
        ]
    )

    assert forbidden == ["web/app/api/status/route.ts"]
    assert outside_allowed == ["ops/runbook.md"]


def test_load_pr_body_reads_github_event_payload(tmp_path, monkeypatch):
    mod = _load_module()
    event_path = tmp_path / "event.json"
    event_path.write_text(
        json.dumps(
            {
                "pull_request": {
                    "body": "## Stage\n\n- Stage 0\n\n## Checklist item\n\n- Guardrails\n"
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("GITHUB_EVENT_NAME", "pull_request")
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(event_path))

    body, has_pr_context = mod._load_pr_body()

    assert has_pr_context is True
    assert "## Stage" in body
    assert "## Checklist item" in body


def test_main_passes_for_lightweight_governance_pr(tmp_path):
    mod = _load_module()
    template_path = tmp_path / "pull_request_template.md"
    changed_files_path = tmp_path / "changed_files.txt"
    pr_body_path = tmp_path / "pr_body.md"

    template_path.write_text(
        REPO.joinpath(".github/pull_request_template.md").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    changed_files_path.write_text(
        ".github/pull_request_template.md\n.agents/rules/hongstr-solid-rules.md\n.opencode/rules.md\nscripts/governance/lightweight_ci_gate.py\n",
        encoding="utf-8",
    )
    pr_body_path.write_text(
        REPO.joinpath(".github/pull_request_template.md").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    rc = mod.main(
        [
            "--template-path",
            str(template_path),
            "--changed-files-file",
            str(changed_files_path),
            "--pr-body-file",
            str(pr_body_path),
        ]
    )

    assert rc == 0


def test_main_fails_when_governance_scope_touches_forbidden_path(tmp_path):
    mod = _load_module()
    template_path = tmp_path / "pull_request_template.md"
    changed_files_path = tmp_path / "changed_files.txt"
    pr_body_path = tmp_path / "pr_body.md"

    template_path.write_text(
        REPO.joinpath(".github/pull_request_template.md").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    changed_files_path.write_text(
        "docs/governance/acceptance_criteria.md\nweb/app/api/status/route.ts\n",
        encoding="utf-8",
    )
    pr_body_path.write_text(
        REPO.joinpath(".github/pull_request_template.md").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    rc = mod.main(
        [
            "--template-path",
            str(template_path),
            "--changed-files-file",
            str(changed_files_path),
            "--pr-body-file",
            str(pr_body_path),
        ]
    )

    assert rc == 1
