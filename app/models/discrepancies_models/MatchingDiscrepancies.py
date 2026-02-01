from typing import List, Literal, Optional
from pydantic import BaseModel, Field, model_validator
from app.models.discrepancies_models.BaseDiscrepancy import BaseDiscrepancy


class POReferenceDiscrepancy(BaseDiscrepancy):
    type: str = "po_reference_anomaly"
    severity: Literal["low", "medium", "high"] = "medium"
    suggested_po_number: Optional[str] = None
    suggested_po_match_confidence: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Confidence for the suggested PO Number"
    )
    recommended_action: Literal[
        "auto_approve", "flag_for_review", "escalate_to_human"
    ] = "flag_for_review"

    reasoning: str

    @model_validator(mode="after")
    def validate_recommended_action(self):
        return self._compute_recommended_action()

    ## Custom Func so parent model can call it.
    def _compute_recommended_action(self):
        ## Can be called manually
        ## Treat as a danger case
        if self.suggested_po_match_confidence is None:
            self.recommended_action = "escalate_to_human"
            return self
        if self.suggested_po_match_confidence < 0.7:
            self.recommended_action = "escalate_to_human"
        elif 0.7 <= self.suggested_po_match_confidence <= 0.89:
            self.recommended_action = "flag_for_review"
        else:
            self.recommended_action = "auto_approve"
        return self


class MultiplePOCandiate(BaseModel):
    suggested_po_number: str
    suggest_po_match_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    reasoning: str


class MultiplePOCandidatesDiscrepancy(BaseDiscrepancy):
    type: str = "multiple_po_candidates"
    severity: Literal["low", "medium", "high"] = "medium"
    candidates: List[MultiplePOCandiate]
    recommended_action: Literal[
        "auto_approve", "flag_for_review", "escalate_to_human"
    ] = "flag_for_review"


class PartialDeliveryDiscrepancy(BaseDiscrepancy):
    type: str = "partial_delivery"
    severity: Literal["low", "medium", "high"] = "medium"
    matched_items: int
    po_items_total: int
    is_invoice_definitive_subset_of_po: bool
    recommended_action: Literal[
        "auto_approve", "flag_for_review", "escalate_to_human"
    ] = "flag_for_review"

    reasoning: str

    @model_validator(mode="after")
    def compute_recommended_action(self):
        if self.is_invoice_definitive_subset_of_po:
            self.recommended_action = "auto_approve"
        else:
            self.recommended_action = "flag_for_review"
        return self


