from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class ResolutionAgentOutput(BaseModel):
    """
    The final state of the Invoice Audit.
    Summarizes the journey from extraction to the final decision.
    """

    # The Verdict
    recommended_action: Literal["auto_approve", "flag_for_review", "escalate_to_human"]
    confidence: float = Field(..., ge=0.0, le=1.0)
    risk_level: Literal["none", "low", "medium", "high"]

    # Audit Trail
    approval_criteria_met: List[
        Literal[
            "exact_po_match",
            "all_items_match",
            "high_extraction_confidence",
            "verified_supplier",
            "zero_variance",
        ]
    ] = Field(
        default_factory=list,
        description="List of checks passed (e.g., 'exact_po_match','all_items_match', 'high_extraction_confidence', 'verified_supplier', 'zero_variance')",
    )

    human_review_required: bool = False
    reasoning: str = Field(
        ..., description="The logic behind the auto-approve or escalation."
    )


