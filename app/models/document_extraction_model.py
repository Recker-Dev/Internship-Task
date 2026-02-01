from pydantic import BaseModel, Field
from typing import List, Literal, Optional, Union
from app.models.invoice_extraction_model import InvoiceExtractionResults

from app.models.discrepancies_models.DocumentIntelligenceDiscrepancies import (
    LowExtractionConfidenceDiscrepancy,
    CreditNoteDiscrepancy,
    CurrencyMismatchDiscrepancy,
)


class ExtractionConfidence(BaseModel):
    overall: float = Field(
        ..., ge=0.0, le=1.0, description="Overall Extraction Confidence"
    )
    invoice_number: float = Field(
        ..., ge=0.0, le=1.0, description="Invoice Number Extraction Confidence"
    )
    po_number: float = Field(
        ..., ge=0.0, le=1.0, description="PO Number Extraction Confidence"
    )
    line_items_avg: float = Field(
        ..., ge=0.0, le=1.0, description="Line Items Extraction Average Confidence"
    )
    totals: float = Field(
        ..., ge=0.0, le=1.0, description="Total Amount Extraction Confidence"
    )


class DocumentIntelligenceAgentOutput(BaseModel):
    extracted_data: InvoiceExtractionResults
    extraction_confidence: ExtractionConfidence
    document_quality: Literal["excellent", "average", "poor"]
    agent_reasoning: str
    discrepancies: Optional[
        List[
            Union[
                LowExtractionConfidenceDiscrepancy,
                CreditNoteDiscrepancy,
                CurrencyMismatchDiscrepancy,
            ]
        ]
    ] = []
