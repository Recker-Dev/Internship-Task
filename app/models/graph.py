from typing import Optional
from pydantic import BaseModel
from app.models.invoice_extraction_model import InvoiceExtractionResults
from app.models.document_extraction_model import DocumentIntelligenceAgentOutput
from app.models.matching_model import MatchingAgentOutput


class GraphState(BaseModel):
    file_name: str
    extracted_invoice_results: Optional[InvoiceExtractionResults] = None
    document_intelligence_agent_state: Optional[DocumentIntelligenceAgentOutput] = None
    matching_agent_state: Optional[MatchingAgentOutput] = None
