from app.models.document_extraction_model import DocumentIntelligenceAgentOutput
from app.llm.builder import LLMProviderFactory


INVOICE_VALIDATION_PROMPT = """
# ROLE
You are an Intelligent Invoice Auditor. Your goal is to extract data AND identify 
business discrepancies based on specific organizational rules.

# TASK
1. Extract structured data from the provided Invoice Text.
2. Evaluate the data against the "Discrepancy Rules" below.
3. Populate the `discrepancies` list ONLY if a rule is triggered. If no rules are 
   triggered, return an empty list `[]`.

# DISCREPANCY RULES

## 1. Currency Mismatch (CurrencyMismatchDiscrepancy)
- RULE: The standard operating currency is **GBP**.
- TRIGGER: If the extracted invoice currency is anything other than "GBP" (e.g., USD, EUR).
- SEVERITY: "high"
- ACTION: "escalate_to_human"

## 2. Credit Note Detection (CreditNoteDiscrepancy)
- RULE: Invoices should represent payable amounts. 
- TRIGGER: If the document contains negative totals, negative line item prices, 
  or is explicitly titled "Credit Note".
- SEVERITY: "high"
- ACTION: "escalate_to_human"

## 3. Low Extraction Confidence (LowExtractionConfidenceDiscrepancy)
- RULE: High data integrity is required for "Critical Fields". These fields should have a value and must not be empty or "" or "NA" or "Null" or "None". 
- CRITICAL FIELDS: `total_due`, `invoice_date`, `supplier_name`, `line_items`, `po_number`, `invoice_number`
- TRIGGER: If your internal confidence for any Critical Field is below 0.9.
- BEHAVIOR: 
    - Populate the `fields` list within the discrepancy.
    - field_existence_confidence should have a LOW value if the field have either of the above stated values.
    - field_existence_confidence < 0.7: Action "escalate_to_human".
    - field_existence_confidence 0.7 - 0.89: Action "flag_for_review".

# OUTPUT REQUIREMENTS
- Output valid JSON only.
- populate `document_quality`: "excellent" (no discrepancies), "average" (low confidence/mismatch), or "poor" (credit note/major errors).
- populate `agent_reasoning`: Provide a concise "Chain of Thought" explaining why specific 
  discrepancies were raised or why the invoice was deemed clean.

# INVOICE TEXT
{INVOICE_DETAILS}
"""


async def validate_invoice(invoice_str: str) -> DocumentIntelligenceAgentOutput:

    # Prepare the input for the prompt
    prompt_load = {
        "INVOICE_DETAILS": invoice_str,
    }

    # Format the prompt using the template
    prompt = INVOICE_VALIDATION_PROMPT.format(**prompt_load)

    # Invoke the LLM with the formatted prompt
    llm = LLMProviderFactory.groq()

    return await llm.invoke(prompt, DocumentIntelligenceAgentOutput)
