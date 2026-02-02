from typing import List, Literal, Optional
from pydantic import BaseModel, Field, model_validator
from app.models.discrepancies_models.BaseDiscrepancy import BaseDiscrepancy


## handles Rule regarding the 2%, 5%, and 15%.
class LineItemPriceDiscrepancy(BaseDiscrepancy):
    type: str = "line_item_price_variance"
    severity: Literal["low", "medium", "high"] = "medium"
    item_id: Optional[str] = None
    description: str
    invoice_unit_price: float
    po_unit_price: float
    variance_percent: float
    recommended_action: Literal[
        "auto_approve", "flag_for_review", "escalate_to_human"
    ] = "flag_for_review"

    @model_validator(mode="after")
    def set_severity_and_action(self):
        abs_var = abs(self.variance_percent)
        if abs_var > 15.0:
            self.severity = "high"
            self.recommended_action = "escalate_to_human"
        elif abs_var > 5.0:
            self.severity = "medium"
            self.recommended_action = "flag_for_review"
        else:
            self.severity = "low"
            self.recommended_action = "flag_for_review"
        return self


## handles the Quantity Mismatch
class LineItemQuantityDiscrepancy(BaseDiscrepancy):
    type: str = "line_item_quantity_mismatch"
    severity: Literal["low", "medium", "high"] = "medium"
    item_id: Optional[str] = None
    description: str
    invoice_quantity: float
    po_quantity: float
    recommended_action: Literal[
        "auto_approve", "flag_for_review", "escalate_to_human"
    ] = "flag_for_review"

    @model_validator(mode="after")
    def set_severity(self):
        # Calculate the delta
        diff = self.invoice_quantity - self.po_quantity

        # Supplier is (Over-billing)
        if diff > 0:
            self.severity = "high"
            self.recommended_action = "escalate_to_human"

        # Supplier is billing for LESS than we ordered
        elif diff < 0:
            self.severity = "medium"
            self.recommended_action = "flag_for_review"

        return self


## handles Rule for minor vs. major name mismatches
class SupplierNameDiscrepancy(BaseDiscrepancy):
    type: str = "supplier_name_mismatch"
    severity: Literal["low", "medium", "high"] = "medium"
    invoice_supplier_name: str
    po_supplier_name: str
    similarity_score: float
    recommended_action: Literal[
        "auto_approve", "flag_for_review", "escalate_to_human"
    ] = "flag_for_review"


## handles Rule (5GBP or 1% rule, and the >10% escalation).
class TotalAmountVarianceDiscrepancy(BaseDiscrepancy):
    type: str = "total_amount_variance"
    severity: Literal["low", "medium", "high"] = "medium"
    invoice_total: float
    po_total: float
    variance_amount: float
    variance_percent: float
    recommended_action: Literal[
        "auto_approve", "flag_for_review", "escalate_to_human"
    ] = "flag_for_review"

    @model_validator(mode="after")
    def evaluate_variance(self):
        # High Priority: Escalate if variance > 10%
        if abs(self.variance_percent) > 10.0:
            self.severity = "high"
            self.recommended_action = "escalate_to_human"
        # Auto-Approve if within £5 OR 1% of PO total (whichever is smaller)
        elif abs(self.variance_amount) <= 5 or abs(self.variance_percent) <= 1.0:
            self.severity = "low"
            self.recommended_action = "auto_approve"
        # Otherwise, flag for review
        else:
            self.severity = "medium"
            self.recommended_action = "flag_for_review"

        return self


## handles the (Subtotal + VAT == Total).
class FinancialArithmeticDiscrepancy(BaseDiscrepancy):
    type: str = "financial_arithmetic_inconsistency"
    severity: Literal["high"] = "high"
    invoice_subtotal: float
    invoice_vat_amount: float
    invoice_total_due: float
    calculated_expected_total: float
    recommended_action: Literal["escalate_to_human"] = "escalate_to_human"
    details: str = (
        "The invoice totals do not sum correctly (Subtotal + VAT != Total Due)."
    )


## handles the "Surprise Item" found in Invoice that was never ordered.
class UnexpectedItemDiscrepancy(BaseDiscrepancy):
    type: str = "unexpected_line_item"
    severity: Literal["high"] = "high"
    item_description: str
    item_quantity: float
    item_total: float
    recommended_action: Literal["escalate_to_human"] = "escalate_to_human"
    details: str = (
        "This item exists on the invoice but was not found on the Purchase Order."
    )
