from typing import List, Literal, Optional
from pydantic import BaseModel, Field, model_validator
from app.models.discrepancies_models.BaseDiscrepancy import BaseDiscrepancy


class BadExtractionField(BaseModel):
    field: str
    field_existence_confidence: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Confidence in detection of the particular field with a VALID field not NA, NULL or NONE",
    )
    severity: Literal["low", "medium", "high"] = "medium"
    recommended_action: Literal[
        "auto_approve", "flag_for_review", "escalate_to_human"
    ] = "flag_for_review"

    reasoning: str

    @model_validator(mode="after")
    def compute_recommended_action(self):
        if self.field_existence_confidence is None:
            self.recommended_action = "escalate_to_human"
            self.severity = "high"
            return self
        if self.field_existence_confidence < 0.7:
            self.recommended_action = "escalate_to_human"
            self.severity = "high"
        elif 0.7 <= self.field_existence_confidence <= 0.89:
            self.recommended_action = "flag_for_review"
            self.severity = "medium"
        else:
            self.recommended_action = "auto_approve"
            self.severity = "low"
        return self


class LowExtractionConfidenceDiscrepancy(BaseDiscrepancy):
    type: str = "low_extraction_confidence"
    fields: List[BadExtractionField]
    detected_by: Literal["document_intelligence", "matching", "validation"] = (
        "document_intelligence"
    )


class CreditNoteDiscrepancy(BaseDiscrepancy):
    type: str = "credit_note"
    severity: Literal["low", "medium", "high"] = "high"
    detected_by: Literal["document_intelligence", "matching", "validation"] = (
        "document_intelligence"
    )
    recommended_action: Literal[
        "auto_approve", "flag_for_review", "escalate_to_human"
    ] = "escalate_to_human"


class CurrencyMismatchDiscrepancy(BaseDiscrepancy):
    type: str = "currency_mismatch"
    severity: Literal["low", "medium", "high"] = "high"
    invoice_currency: str
    po_currency: str
    detected_by: Literal["document_intelligence", "matching", "validation"] = (
        "document_intelligence"
    )
    recommended_action: Literal[
        "auto_approve", "flag_for_review", "escalate_to_human"
    ] = "escalate_to_human"
