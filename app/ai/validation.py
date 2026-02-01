from app.models.validation_model import ValidationAgentOutput
from app.llm.builder import LLMProviderFactory
from app.utils.db_helpers import find_po_by_number
from app.validation.validator import validate_invoice_wrt_po
from app.models.invoice_extraction_model import InvoiceExtractionResults

AUDIT_VALIDATION_PROMPT = """
## ROLE
You are a Senior Financial Auditor. Your task is to analyze Python-generated validation results to identify and categorize discrepancies between an Invoice and a Purchase Order (PO).

## CONTEXT & MATERIALITY (IMPORTANT)
An auditor distinguishes between "noise" and "material errors." Use the following guidelines to set severity and decide if a discrepancy is warranted:

### 1. Severity Thresholds:
- **HIGH**: Any error that indicates a fundamental breakdown in logic or a major financial risk.
    - Total variance > 10%.
    - Line item price variance > 15%.
    - Internal Math Errors (The invoice can't even calculate its own total).
    - Unexpected items not on the PO.
- **MEDIUM**: Variances that require a human to "sign off" but aren't necessarily fraudulent.
    - Price variances between 5% and 15%.
    - Supplier name mismatches (e.g., "Ltd" vs "Limited").
- **LOW**: Minor technicalities.
    - Price variances < 5%.
    - Partial deliveries (unless the math is also wrong).

### 2. When NOT to trigger a Discrepancy:
- **Rounding**: If a variance is < 0.05 (in any currency), ignore it. This is a floating-point or rounding nuisance, not an error.
- **Partial Delivery**: If `structure.status` is "partial_delivery" and all items present are price-valid, do NOT trigger a discrepancy for the *missing* items. The system already knows this is a subset.

## DISCREPANCY MAPPING RULES:
Map the Python `VALIDATION_RESULTS` to these specific objects:

1. **SupplierNameDiscrepancy**: Trigger only if `supplier_name_similarity` is < 0.90. If > 0.90, treat as a match.
2. **LineItemPriceDiscrepancy**: Trigger for items where `unit_price_within_2percent` is False AND the variance is > 0.05 absolute value.
3. **LineItemQuantityDiscrepancy**: Trigger if `invoice_quantity` != `po_quantity`. 
4. **UnexpectedItemDiscrepancy**: Trigger for any item in `unmatched_invoice_items`.
5. **TotalAmountVarianceDiscrepancy**: Trigger if `financials.valid` is False.
6. **FinancialArithmeticDiscrepancy**: Trigger if `internal_math_error` is True. This is ALWAYS HIGH severity.

## OUTPUT FORMAT
Return a JSON object matching the `ValidationAgentOutput` schema:
- **status**: "clean" | "minor failures" | "critical failures"
- **agent_reasoning**: Explain the "Why." (e.g., "The invoice is mathematically sound but includes a 7% price increase on shipping which was not authorized on the PO.")
- **discrepancies**: List of discrepancy objects.

# INVOICE TEXT
{INVOICE_DETAILS}

# EXPECTED PO RECORD
{PO_RECORD}

# VALIDATION RESULTS
{VALIDATION_RESULT}
"""


async def validate_invoice_with_po(
    invoice: InvoiceExtractionResults, matched_po_number: str
) -> ValidationAgentOutput:

    # Prepare the input for the prompt
    prompt_load = {
        "INVOICE_DETAILS": invoice.model_dump(),
        "PO_RECORD": find_po_by_number(matched_po_number),
        "VALIDATION_RESULT": validate_invoice_wrt_po(invoice, matched_po_number),
    }

    # Format the prompt using the template
    prompt = AUDIT_VALIDATION_PROMPT.format(**prompt_load)

    # Invoke the LLM with the formatted prompt
    llm = LLMProviderFactory.groq()

    return await llm.invoke(prompt, ValidationAgentOutput)
