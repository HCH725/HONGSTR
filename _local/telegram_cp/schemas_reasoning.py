from pydantic import BaseModel, Field
from typing import List

class ReasoningAnalysis(BaseModel):
    """
    Strict schema for Reasoning Specialist (deepseek-r1:7b) output.
    All fields are mandatory to ensure the Specialist provides structured insights.
    """
    status: str = Field(..., description="Overall status of the analysis: OK, WARN, or FAIL")
    problem: str = Field(..., description="Concise description of the problem being analyzed")
    key_findings: List[str] = Field(..., description="Bullet points of the most critical observations")
    hypotheses: List[str] = Field(..., description="Potential causes or theories for the observed phenomena")
    recommended_next_steps: List[str] = Field(..., description="Actionable SOP suggestions (Informational only)")
    risks: List[str] = Field(..., description="Potential risks or pitfalls (e.g. overfitting, data drift)")
    actions: List[str] = Field(default_factory=list, description="Must remain empty. Autonomous agent is read-only.")
    citations: List[str] = Field(..., description="References to specific files, logs, or metrics used in the analysis")
    refresh_hint: str = Field(
        default="bash scripts/refresh_state.sh",
        description="Recovery hint when evidence/state is missing or stale.",
    )

    def validate_actions_empty(self):
        """Force actions to be empty as per hard redline."""
        if self.actions:
            self.actions = []
