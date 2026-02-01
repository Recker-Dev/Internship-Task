from app.models.matching_model import MatchingAgentOutput
from app.llm.builder import LLMProviderFactory
from app.matching.primary import primary_matching
from app.matching.secondary import secondary_matching
from app.matching.tertiary import tertiary_matching
from app.models.invoice_extraction_model import InvoiceExtractionResults


MATCHING_DECISION_AGENT_PROMPT = """
# ROLE
You are an Invoice-to-Purchase-Order Matching Decision Agent.

Your responsibility is to SELECT the best PO match from PRE-COMPUTED matching results,
apply strict priority rules, document discrepancies, and explain the decision.

You do NOT determine whether a match succeeded or failed.
You trust the match results provided to you.


# INPUTS (AUTHORITATIVE)
Each matching input already includes:
- success / failure status
- candidate PO(s)
- confidence score(s)

You MUST treat these as ground truth.

- EXTRACTED_INVOICE: {EXTRACTED_INVOICE}

- PRIMARY_MATCH (exact_po_reference): {PRIMARY_MATCH}
- SECONDARY_MATCH (supplier_date_product): {SECONDARY_MATCH}
- TERTIARY_MATCH (product_only): {TERTIARY_MATCH}


# MATCH SELECTION POLICY (STRICT PRIORITY)

You MUST evaluate match inputs in the order below.
You MUST NOT reinterpret or override their success/failure.

## 1. Primary Match — Exact PO Reference
- If PRIMARY_MATCH indicates success:
  - Select it immediately
  - Do NOT consider secondary or tertiary matches
- Expected confidence range: 0.90–0.99

## 2. Secondary Match — Supplier + Date + Product
- Consider ONLY if PRIMARY_MATCH indicates failure
- If SECONDARY_MATCH indicates success:
  - Select the best candidate as provided
- Expected confidence range: 0.70–0.85

## 3. Tertiary Match — Product-Only Fuzzy
- Consider ONLY if PRIMARY_MATCH and SECONDARY_MATCH both indicate failure
- If TERTIARY_MATCH indicates success:
  - Select the best candidate as provided
- Expected confidence range: 0.40–0.69

## 4. No Confident Match
- Use ONLY if all matching inputs indicate failure
- Confidence MUST be <0.50


# CONFIDENCE HANDLING (IMPORTANT)

- Use the confidence scores PROVIDED by the matching systems
- You MUST NOT invent, adjust, inflate, or reinterpret confidence values
- Confidence reflects upstream matching quality, not your judgment


# DISCREPANCY TRIGGERS (MANDATORY)

Discrepancies document risk.
They do NOT block matching.

## 1. POReferenceDiscrepancy
- TRIGGER:
  - PRIMARY_MATCH indicates failure
  - AND a PO is selected via SECONDARY or TERTIARY
- REQUIRED:
  - Explain that the invoice lacked a valid PO reference (or had an invalid one)
  - Explain how the selected PO was identified via fallback matching

## 2. MultiplePOCandidatesDiscrepancy
- TRIGGER:
  - Selected match input provides multiple PO candidates
  - AND their confidence scores are within 10 percentage points
- REQUIRED:
  - List ALL viable candidates
  - Set `recommended_action` to `"flag_for_review"`

## 3. PartialDeliveryDiscrepancy
- TRIGGER:
  - Upstream matching indicates partial item alignment
- SEVERITY:
  - "medium"


# MANDATE: STRUCTURAL PAIRING ONLY

You are NOT a financial auditor.

You MUST NOT raise discrepancies based on:
- Unit price
- VAT / tax
- Totals or arithmetic

You MAY reference financial differences ONLY if:
- Upstream systems used them to invalidate PRIMARY_MATCH
- AND only as explanatory context


# ASSERTIVE MATCH SELECTION

If any matching input indicates success,
YOU MUST select a PO — even if discrepancies exist.

Discrepancies explain risk.
They do NOT negate upstream success.


# OUTPUT FORMAT (STRICT)

Return JSON ONLY.

Required fields:
- matched_po: string or null
- match_method:
  - "exact_po_reference"
  - "supplier_date_product"
  - "product_only"
  - "no_confident_match"
- po_match_confidence: float (from upstream input)
- agent_reasoning:
  - Explain:
    - Which match inputs succeeded or failed
    - Why the selected match was chosen by priority
    - Why others were ignored
- discrepancies:
  - Array of applicable discrepancy objects (may be empty)

Be deterministic.
Do not reinterpret upstream results.
Explain the decision path clearly.

"""


async def match_invoice_with_db(
    extracted_invoice: InvoiceExtractionResults,
) -> MatchingAgentOutput:

    primary_match_result, secondary_match_result, tertiary_match_result = (
        None,
        None,
        None,
    )

    ## Carry Out Primary Search
    primary_match_result = primary_matching(extracted_invoice)
    ## Fallback to Secondary if Primary Fails
    if not primary_match_result.get("matched"):
        secondary_match_result = secondary_matching(extracted_invoice)
        if not secondary_match_result.get("matched"):
            ## Fallback to Tertiary if Secondary Fails
            tertiary_match_result = tertiary_matching(extracted_invoice)

    # Prepare the input for the prompt
    prompt_load = {
        "EXTRACTED_INVOICE": extracted_invoice,
        "PRIMARY_MATCH": primary_match_result,
        "SECONDARY_MATCH": secondary_match_result,
        "TERTIARY_MATCH": tertiary_match_result,
    }

    # Format the prompt using the template
    prompt = MATCHING_DECISION_AGENT_PROMPT.format(**prompt_load)

    # Invoke the LLM with the formatted prompt
    llm = LLMProviderFactory.groq()
    result = await llm.invoke(prompt, MatchingAgentOutput)

    return result
