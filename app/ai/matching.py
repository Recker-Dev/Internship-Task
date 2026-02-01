from app.models.matching_model import MatchingAgentOutput
from app.llm.builder import LLMProviderFactory
from app.matching.primary import primary_matching
from app.matching.secondary import secondary_matching
from app.matching.tertiary import tertiary_matching
from app.models.invoice_extraction_model import InvoiceExtractionResults
from pprint import pprint

MATCHING_DECISION_AGENT_PROMPT = """
You are an Invoice-to-Purchase-Order Matching Agent.

Your task is to determine the best matching Purchase Order (PO) for a given invoice
using a strict priority hierarchy and confidence scoring rules.

---

## Inputs

### Invoice Extraction Result
{EXTRACTED_INVOICE}

Contains:
- Supplier name
- Invoice number
- Invoice date
- PO reference (if present)
- Line items (description, quantity, unit price)
- Invoice totals

---

### Primary Matching Output (Exact PO Reference Match)
{PRIMARY_MATCH}

- Result of matching invoice PO reference to known POs
- May be null or empty if no valid PO reference was found
- Includes:
  - matched_po
  - line item comparison
  - price/totals variance
  - confidence score (if computed)

---

### Secondary Matching Output (Supplier + Date + Product Match)
{SECONDARY_MATCH}

- Fuzzy supplier name matching
- Invoice date vs PO date (±14 days)
- Product description fuzzy matching
- Includes:
  - candidate POs
  - match rates
  - confidence estimates

---

### Tertiary Matching Output (Product-Only Fuzzy Match)
{TERTIARY_MATCH}

- Product description–only similarity
- Used when PO reference and supplier match fail
- Includes:
  - candidate POs
  - item similarity scores
  - aggregate match confidence

---

## Matching Rules (Strict Priority)

1. **Primary Matching (Highest Priority)**
   - If a valid PO reference exists and matches a known PO:
     - Treat this as definitive unless major discrepancies exist
     - Expected confidence: 95–99%

2. **Secondary Matching**
   - Used only if primary matching fails or confidence < 85%
   - Requires:
     - Supplier name match (fuzzy allowed)
     - Invoice date within ±14 days of PO date
     - ≥70% product match rate
   - Expected confidence: 60–85%

3. **Tertiary Matching**
   - Used only if both primary and secondary fail
   - Product-only fuzzy matching
   - Requires >80% similarity across multiple items
   - Expected confidence: 40–70%

---

## Confidence Scoring Guidelines

- >95%: Exact PO match, all line items match, totals within tolerance
- 85–95%: Exact PO match with minor discrepancies
- 70–84%: Supplier + product + date fuzzy match
- 50–69%: Product-only fuzzy match
- <50%: No confident match → escalate

---

## Output Instructions

Return a structured JSON object that includes:
- Final selected PO (or null)
- Match method used
- Final confidence score
- Line-item match statistics
- Supplier and date match indicators
- Alternative candidate matches (if any)
- Clear, concise agent reasoning explaining *why* this match was chosen

If no match meets ≥50% confidence:
- Set matched_po to null
- Set match_method to "no_confident_match"
- Recommend escalation

Be deterministic, conservative, and explain tradeoffs clearly.
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
    # print(DocumentIntelligenceAgentOutput.model_json_schema())
    # return  "Hello"
