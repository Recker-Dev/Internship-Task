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
5. **TotalAmountVarianceDiscrepancy**: Trigger if `financials.invoice_total_is_valid` is False.
    - Auto-Approve:
        - If absolute variance_amount ≤ £5 OR variance_percent ≤ 1.0%, recommend "auto_approve".
        - Severity = "low".
    - Flag for Review:
        - If variance_amount > £5 AND variance_percent > 1.0% but variance_percent ≤ 10%, recommend "flag_for_review".
        - Severity = "medium".
    - Escalate to Human:
        - If variance_percent > 10%, recommend "escalate_to_human".
        - Severity = "high".
6. **FinancialArithmeticDiscrepancy**: Trigger if `internal_math_error` is True. This is ALWAYS HIGH severity.

## OUTPUT FORMAT (STRICT)

Return a SINGLE JSON object that fully conforms to the `ValidationAgentOutput` schema.
Do NOT include markdown, comments, or additional keys.
Do NOT omit required fields.
Do NOT change field names.

---

### Required Fields

#### status
- Type: string (enum)
- Allowed values:
  - "clean"
  - "minor failures"
  - "critical failures"
- Semantics:
  - "clean":
    - No discrepancies OR only informational discrepancies
    - All variances are within tolerance
  - "minor failures":
    - One or more discrepancies exist
    - All discrepancies are within defined tolerance thresholds
    - Manual review recommended but payment may proceed
  - "critical failures":
    - One or more discrepancies exceed tolerance
    - OR financial correctness cannot be guaranteed
    - Payment must be blocked or escalated

---

#### agent_reasoning
- Type: string
- REQUIRED
- Purpose:
  - Provide a concise, technical explanation of WHY the status was assigned
- Must include:
  - What was validated (items, quantities, totals)
  - What matched and what did not
  - Why discrepancies were or were not raised
- Example:
  - "All invoice line items were matched to the PO. One item shows a 5% unit price increase but remains within tolerance. Total invoice amount matches PO subtotal."

---

### Variance Fields

#### total_variance
- Type: object OR null
- Default behavior:
  - If no total variance exists, return the default object:
    - variance_amount: 0.0
    - variance_percent: 0.0
    - within_tolerance: true
- Semantics:
  - Represents the TOTAL invoice vs PO variance
  - within_tolerance indicates whether escalation is required
- MUST be consistent with:
  - TotalAmountVarianceDiscrepancy (if present)

---

#### line_item_total_variance
- Type: object OR null
- Semantics:
  - Represents the MOST SIGNIFICANT single line-item price variance
  - Should be populated only if at least one line item variance exists
- Fields:
  - item_code: string
  - item_desc: string
  - variance_amount: float
  - variance_percent: float
  - within_tolerance: boolean

---

### Discrepancies

#### discrepancies
- Type: array (may be empty)
- Each entry MUST be one of:
  - LineItemPriceDiscrepancy
  - LineItemQuantityDiscrepancy
  - SupplierNameDiscrepancy
  - FinancialArithmeticDiscrepancy
  - TotalAmountVarianceDiscrepancy
  - UnexpectedItemDiscrepancy
- Behavior:
  - Only include discrepancies that were actually triggered
  - Do NOT invent discrepancies
  - Each discrepancy must be internally consistent with variance fields
- Relationship to status:
  - If discrepancies is empty → status MUST be "clean"
  - If discrepancies exist:
    - status MUST be "minor failures" or "critical failures"
    - severity and tolerance determine which

---

### audit_id
- Type: string (UUID)
- Behavior:
  - If not explicitly provided, it will be auto-generated
  - You MAY omit it from output and allow the system to generate it

---

## CONSISTENCY RULES (NON-NEGOTIABLE)

- If `within_tolerance` is false in ANY variance object:
  → status MUST be "critical failures"
- If discrepancies exist but ALL variances are within tolerance:
  → status MUST be "minor failures"
- If no discrepancies exist:
  → status MUST be "clean"
- Variance objects and discrepancy objects MUST NOT contradict each other
- The recommended_action in TotalAmountVarianceDiscrepancy MUST follow the thresholds above.
- variance_amount and variance_percent must always align with recommended_action.

---

## FINAL REQUIREMENTS

- Output VALID JSON ONLY
- Must be parsable by Pydantic without coercion
- Be deterministic
- Be conservative
- Prefer null over fabrication


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
