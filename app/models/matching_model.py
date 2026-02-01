from typing import List, Optional, Literal, Self
from pydantic import BaseModel, Field, model_validator


class AlternativeMatch(BaseModel):
    po_number: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    match_method: Literal["exact_po_reference", "supplier_date_product", "product_only"]


class MatchingAgentOutput(BaseModel):
    matched_po: Optional[str] = None

    po_match_confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Final confidence score for the selected PO match",
    )

    match_method: Literal[
        "exact_po_reference",
        "supplier_date_product",
        "product_only",
        "no_confident_match",
    ]

    supplier_match: Optional[bool] = None
    date_variance_days: Optional[int] = None

    line_items_matched: Optional[int] = None
    line_items_total: Optional[int] = None
    match_rate: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="line_items_matched / line_items_total"
    )

    alternative_matches: List[AlternativeMatch] = []

    agent_reasoning: str = Field(
        ..., description="Human-readable explanation of how the match decision was made"
    )

    handoff_to: Literal["discrepancy_detection_agent", "manual_review"]

    ## Validator prevents selected PO from showing up in alternatives.
    @model_validator(mode="after")
    def remove_selected_po_from_alternatives(self) -> Self:
        if not self.matched_po:
            return self

        self.alternative_matches = [
            alt for alt in self.alternative_matches if alt.po_number != self.matched_po
        ]

        return self
