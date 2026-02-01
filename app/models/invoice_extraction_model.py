from typing import List, Literal, Optional, TypedDict
from pydantic import BaseModel, Field
from datetime import date


class BillTo(BaseModel):
    company_name: str
    address: str


class ReceiptLineItem(BaseModel):
    item_id: str
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
    


class InvoiceExtractionResults(BaseModel):
    invoice_number: str
    invoice_date: date
    supplier_name: str
    supplier_address: str
    supplier_vat: str
    po_number: str
    payment_terms: str
    currency: str
    bill_to: BillTo
    line_items: List[ReceiptLineItem]
    totals: ReceiptTotals





