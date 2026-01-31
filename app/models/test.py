from typing import List, Literal, Optional, TypedDict
from pydantic import BaseModel, Field
from datetime import  date


class BillTo(BaseModel):
    company_name: str
    address: str


class ReceiptLineItem(BaseModel):
    item_code: str
    description: str
    quantity: float
    unit: str
    unit_price: float
    line_total: float
    extraction_confidence: float = Field(..., ge=0.0, le=1.0)


class ReceiptTotals(BaseModel):
    subtotal: float
    vat_rate: float
    vat_amount: float
    total_due: float
    currency: str


class InvoiceExtractionResults(BaseModel):
    invoice_number: str
    invoice_date: date
    supplier_name: str
    supplier_address: str
    supplier_vat: str
    po_reference: str
    payment_terms: str
    bill_to: BillTo
    line_items: List[ReceiptLineItem]
    totals: ReceiptTotals


class ExtractionConfidence(BaseModel):
    overall: float = Field(..., ge=0.0, le=1.0)
    invoice_number: float = Field(..., ge=0.0, le=1.0)
    po_reference: float = Field(..., ge=0.0, le=1.0)
    line_items_avg: float = Field(..., ge=0.0, le=1.0)
    totals: float = Field(..., ge=0.0, le=1.0)


class DocumentIntelligenceAgentOutput(BaseModel):
    extracted_data: InvoiceExtractionResults
    extraction_confidence: ExtractionConfidence
    document_quality: Literal["excellent", "average", "poor"]
    agent_reasoning: str


class GraphState(TypedDict):
    file_name: str
    document_intelligence_agent_state: Optional[DocumentIntelligenceAgentOutput]
