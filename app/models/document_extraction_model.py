from pydantic import BaseModel, Field
from app.models.invoice_extraction_model import InvoiceExtractionResults
from typing import Literal


class ExtractionConfidence(BaseModel):
    overall: float = Field(..., ge=0.0, le=1.0)
    invoice_number: float = Field(..., ge=0.0, le=1.0)
    po_number: float = Field(..., ge=0.0, le=1.0)
    line_items_avg: float = Field(..., ge=0.0, le=1.0)
    totals: float = Field(..., ge=0.0, le=1.0)


class DocumentIntelligenceAgentOutput(BaseModel):
    extracted_data: InvoiceExtractionResults
    extraction_confidence: ExtractionConfidence
    document_quality: Literal["excellent", "average", "poor"]
    agent_reasoning: str
