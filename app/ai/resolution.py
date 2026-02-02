from app.models.validation_model import ValidationAgentOutput
from app.models.resolution_model import ResolutionAgentOutput
from typing import Optional
from app.llm.builder import LLMProviderFactory
from app.models.document_extraction_model import DocumentIntelligenceAgentOutput
from app.models.matching_model import MatchingAgentOutput
import json

RESOLUTION_AGENT_PROMPT = """
# ROLE
You are the Chief Resolution Officer for an automated Accounts Payable system. Your task is to review the aggregated findings from three specialized agents and issue a final verdict on an invoice.

# INPUT DATA
1. **Document Extraction Summary**: {EXTRACTION_SUMMARY}
2. **Matching Summary**: {MATCHING_SUMMARY}
3. **Validation Summary**: {VALIDATION_SUMMARY}
4. **Aggregated Discrepancies**: {DISCREPANCIES_LIST}

# BUSINESS RULES & EARLY EXIT CRITERIA
- **AUTO_APPROVE**: Allowed only if there are 0-2 Low severity discrepancies AND matching confidence is >85%.
- **FLAG_FOR_REVIEW**: Used for minor ambiguities (e.g., Partial Deliveries, Name Mismatches) or when a human needs to select between multiple PO candidates.
- **ESCALATE_TO_HUMAN**: 
    - MANDATORY if any discrepancy is "high" severity.
    - MANDATORY if there are 3 or more total discrepancies.
    - MANDATORY for Arithmetic Failures, Currency Mismatches, or Unexpected Items in Invoice.

# CRITICAL LOGIC: EARLY EXIT HANDLING
- If VALIDATION_SUMMARY is "Not Performed", it means the invoice failed a structural or matching check and never reached the audit phase. This is an AUTOMATIC ESCALATION.
- If MATCHING_SUMMARY is "Not Performed", it means the invoice failed at the extraction/sanity check level. This is an AUTOMATIC ESCALATION.

# APPROVAL RULES
- AUTO_APPROVE: Only possible if ALL three agents (Extraction, Matching, Validation) have run, found 0-2 low-severity issues, and reached a "clean" or "minor failures" status.
- ESCALATE_TO_HUMAN: 
    - Any "high" severity discrepancy.
    - 3 or more total discrepancies.
    - Any "Early Exit" where a node was skipped due to failure.

# TASK
Evaluate the "Risk Level" based on the severity of the discrepancies. Determine which "Approval Criteria" were met ('exact_po_match','all_items_match', 'high_extraction_confidence', 'verified_supplier', 'zero_variance')".
Write a concise reasoning narrative.

# OUTPUT INSTRUCTIONS
Return a valid JSON object matching the `ResolutionAgentOutput` schema.
"""


async def resolve_invoice_findings(
    extraction_results: Optional[DocumentIntelligenceAgentOutput],
    matching_results: Optional[MatchingAgentOutput],
    validation_results: Optional[ValidationAgentOutput],
) -> ResolutionAgentOutput:

    # 1. Collect all discrepancies from whatever nodes actually ran
    discrepancies = []
    nodes_run = []

    if extraction_results:
        nodes_run.append("extraction")
        if extraction_results.discrepancies:
            discrepancies.extend(extraction_results.discrepancies)

    if matching_results:
        nodes_run.append("matching")
        if matching_results.discrepancies:
            discrepancies.extend(matching_results.discrepancies)

    if validation_results:
        nodes_run.append("validation")
        if validation_results.discrepancies:
            discrepancies.extend(validation_results.discrepancies)

    # If we didn't reach validation, it's an automatic 'escalate' in spirit
    pipeline_reached_end = "validation" in nodes_run

    # 2. Creative Evidence Bundle
    evidence_bundle = {
        "extraction_summary": (
            extract_valid_document_states(extraction_results)
            if extraction_results
            else "NOT_PERFORMED"
        ),
        "matching_summary": (
            extract_valid_matching_states(matching_results)
            if matching_results
            else "NOT_PERFORMED"
        ),
        "validation_summary": (
            extract_valid_validation_states(validation_results)
            if validation_results
            else "NOT_PERFORMED"
        ),
        "discrepancies": [d.model_dump() for d in discrepancies],
    }

    # 3. Preparation of Payload
    prompt = RESOLUTION_AGENT_PROMPT.format(
        EXTRACTION_SUMMARY=evidence_bundle["extraction_summary"],
        MATCHING_SUMMARY=evidence_bundle["matching_summary"],
        VALIDATION_SUMMARY=evidence_bundle["validation_summary"],
        DISCREPANCIES_LIST=evidence_bundle["discrepancies"],
    )

    # 4. Invoke the LLM with the formatted prompt
    llm = LLMProviderFactory.groq()

    final_state = await llm.invoke(prompt, ResolutionAgentOutput)

    if not pipeline_reached_end:
        final_state.recommended_action = "escalate_to_human"
        final_state.reasoning = (
            f"Early exit triggered. Pipeline stopped at {nodes_run[-1]} node. "
            + final_state.reasoning
        )

    if len(discrepancies) >= 3:
        final_state.recommended_action = "escalate_to_human"
        if "3+ discrepancies" not in final_state.reasoning:
            final_state.reasoning += (
                " (Complexity threshold: 3+ discrepancies reached)."
            )

    return final_state


## HELPER FUNCS TO CREATE PAYLOAD

def extract_valid_document_states(doc_state: DocumentIntelligenceAgentOutput):
    return {
        "extraction": {
            "status": "Performed" if doc_state else "Not Performed",
            "overall_extraction_confidence": doc_state.extraction_confidence.overall,
            "critical_fields_extraction_confidence": doc_state.extraction_confidence.model_dump(
                exclude={"overall"}
            ),
            "document_quality": doc_state.document_quality,
            "agent_reasoning": doc_state.agent_reasoning,
        },
    }


def extract_valid_matching_states(match_state: MatchingAgentOutput):
    return {
        "matching": {
            "status": "Performed" if match_state else "Not Performed",
            "matched_po": match_state.matched_po,
            "match_confidence": match_state.po_match_confidence,
            "match_method": match_state.match_method,
            "supplier_match": match_state.supplier_match,
            "line_items_match_ratio": match_state.match_rate,
            "alternative_matches_length": (
                (
                    len(match_state.alternative_matches)
                    if match_state.alternative_matches
                    else 0
                ),
            ),
            "agent_reasoning": match_state.agent_reasoning,
        }
    }


def extract_valid_validation_states(val_state: ValidationAgentOutput):
    return {
        "validation": {
            "status": "Performed" if val_state else "Not Performed",
            "validation_state": val_state.status,
            "total_variance": (val_state.total_variance.model_dump(),),
            "line_item_total_variance": (
                val_state.line_item_total_variance.model_dump()
                if val_state.line_item_total_variance
                else "No Variance Found for Line Items or Failed to populate"
            ),
            "agent_reasoning": val_state.agent_reasoning,
        }
    }
