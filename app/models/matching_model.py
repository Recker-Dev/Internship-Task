from typing import List, Optional, Literal, Self, Union
from pydantic import BaseModel, Field, model_validator
from app.models.discrepancies_models.MatchingDiscrepancies import (
    POReferenceDiscrepancy,
    MultiplePOCandidatesDiscrepancy,
    PartialDeliveryDiscrepancy,
)


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

    line_items_matched: Optional[int] = Field(
        description="Items that matches from both Invoice and PO"
    )
    line_items_total: Optional[int] = Field(
        description="Items that are in total inside PO"
    )
    match_rate: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="line_items_matched / line_items_total"
    )

    alternative_matches: List[AlternativeMatch] = []

    agent_reasoning: str = Field(
        ..., description="Human-readable explanation of how the match decision was made"
    )

    discrepancies: Optional[
        List[
            Union[
                POReferenceDiscrepancy,
                MultiplePOCandidatesDiscrepancy,
                PartialDeliveryDiscrepancy,
            ]
        ]
    ] = []

    ## Validator prevents selected PO from showing up in alternatives.
    @model_validator(mode="after")
    def remove_selected_po_from_alternatives(self) -> Self:
        if not self.matched_po:
            return self

        self.alternative_matches = [
            alt for alt in self.alternative_matches if alt.po_number != self.matched_po
        ]

        return self

    ## Calculate Match Rate
    @model_validator(mode="after")
    def calculate_match_rate(self) -> Self:
        if (
            self.line_items_matched is not None
            and self.line_items_total is not None
            and self.line_items_total > 0
        ):
            self.match_rate = self.line_items_matched / self.line_items_total
        else:
            self.match_rate = 0

        return self

    ## Validator ensures confidence metric is present in child models
    @model_validator(mode="after")
    def sync_discrepancy_confidence(self):
        if not self.discrepancies:
            return self
        for d in self.discrepancies:
            # If it's a PO anomaly and the confidence is missing, sync it
            if (
                isinstance(d, POReferenceDiscrepancy)
                and d.suggested_po_match_confidence is None
            ):
                d.suggested_po_match_confidence = self.po_match_confidence
                # Trigger the child's logic to re-evaluate the action
                d._compute_recommended_action()
        return self
