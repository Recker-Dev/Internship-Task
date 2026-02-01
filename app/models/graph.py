from typing import Optional, List, Union
from typing_extensions import Annotated
from pydantic import BaseModel
import operator
from app.models.invoice_extraction_model import InvoiceExtractionResults
from app.models.document_extraction_model import DocumentIntelligenceAgentOutput
from app.models.matching_model import MatchingAgentOutput
from app.models.validation_model import ValidationAgentOutput

from app.models.discrepancies_models.DocumentIntelligenceDiscrepancies import (
    LowExtractionConfidenceDiscrepancy,
    CreditNoteDiscrepancy,
    CurrencyMismatchDiscrepancy,
)
from app.models.discrepancies_models.MatchingDiscrepancies import (
    POReferenceDiscrepancy,
    MultiplePOCandidatesDiscrepancy,
    PartialDeliveryDiscrepancy,
)
from app.models.discrepancies_models.ValidationDiscrepanices import (
    LineItemPriceDiscrepancy,
    LineItemQuantityDiscrepancy,
    SupplierNameDiscrepancy,
    TotalAmountVarianceDiscrepancy,
    FinancialArithmeticDiscrepancy,
    UnexpectedItemDiscrepancy,
)


class GraphState(BaseModel):
    file_name: str
    extracted_invoice_results: Optional[InvoiceExtractionResults] = None
    document_intelligence_agent_state: Optional[DocumentIntelligenceAgentOutput] = None
    matching_agent_state: Optional[MatchingAgentOutput] = None
    audit_validation_agent_state: Optional[ValidationAgentOutput] = None
    discrepancies: Annotated[
        List[
            Union[
                LowExtractionConfidenceDiscrepancy,
                CreditNoteDiscrepancy,
                CurrencyMismatchDiscrepancy,
                POReferenceDiscrepancy,
                MultiplePOCandidatesDiscrepancy,
                PartialDeliveryDiscrepancy,
                LineItemPriceDiscrepancy,
                LineItemQuantityDiscrepancy,
                SupplierNameDiscrepancy,
                FinancialArithmeticDiscrepancy,
                TotalAmountVarianceDiscrepancy,
                UnexpectedItemDiscrepancy,
            ]
        ],
        operator.add, ## Enables auto append
    ] = []
