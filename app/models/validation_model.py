from typing import List, Literal, Union, Optional
from pydantic import BaseModel, Field
from app.models.discrepancies_models.ValidationDiscrepanices import (
    LineItemPriceDiscrepancy,
    LineItemQuantityDiscrepancy,
    SupplierNameDiscrepancy,
    TotalAmountVarianceDiscrepancy,
    FinancialArithmeticDiscrepancy,
    UnexpectedItemDiscrepancy,
)
import uuid


class ValidationAgentOutput(BaseModel):
    """
    Output from the Validation Agent.
    Acts as a structured report for the Reasoning Agent to consume.
    """

    # Summary of the audit
    audit_id: str = Field(
        description="Unique ID for this validation run",
        default_factory=lambda: str(uuid.uuid4()),
    )
    status: Literal["clean", "minor failures", "critical failures"]
    # Narrative Evidence for the Reasoning Agent
    agent_reasoning: str = Field(
        ...,
        description="A technical breakdown of the findings (e.g., '3 items paired, 1 price variance of 5%, total due matches PO subtotal.')",
    )

    # The list of findings based on Python function outputs
    discrepancies: Optional[
        List[
            Union[
                LineItemPriceDiscrepancy,
                LineItemQuantityDiscrepancy,
                SupplierNameDiscrepancy,
                FinancialArithmeticDiscrepancy,
                TotalAmountVarianceDiscrepancy,
                UnexpectedItemDiscrepancy,
            ]
        ]
    ] = []
