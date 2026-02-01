from app.models.document_extraction_model import DocumentIntelligenceAgentOutput
from app.models.discrepancies_models.DocumentIntelligenceDiscrepancies import (
    CurrencyMismatchDiscrepancy,
    CreditNoteDiscrepancy,
    LowExtractionConfidenceDiscrepancy,
)


def log_document_intelligence_agent_results(result: DocumentIntelligenceAgentOutput):
    """
    Standardized logger for the Document Intelligence Agent.
    Explicitly handles Credit Notes, Currency Mismatches, and Extraction Confidence.
    """
    print("\n" + "█" * 60)
    print("--- DOCUMENT INTELLIGENCE AGENT AUDIT LOG ---".center(60))
    print("█" * 60)

    # 1. High-Level Summary
    quality_icon = {"excellent": "🟢", "average": "🟡", "poor": "🔴"}.get(
        result.document_quality, "⚪"
    )
    print(f"\nDOCUMENT QUALITY: {result.document_quality.upper()} {quality_icon}")
    print(f"AGENT REASONING:  {result.agent_reasoning}")

    # 2. Confidence Metrics
    conf = result.extraction_confidence
    print(f"\n[EXTRACTION CONFIDENCE]")
    print(f"  Overall: {conf.overall:.2%} | Totals: {conf.totals:.2%}")
    if conf.line_items_avg:
        print(f"  Line Items Avg: {conf.line_items_avg:.2%}")

    # 3. Discrepancy Audit (The "Red Flag" Killer)
    print(f"\n[DISCREPANCY AUDIT]")
    if not result.discrepancies:
        print("  ✅ No discrepancies detected. Document is clean.")
    else:
        for i, d in enumerate(result.discrepancies, 1):
            # --- Specific Handling for Credit Notes ---
            if isinstance(d, CreditNoteDiscrepancy):
                print(
                    f"     Status: DOCUMENT IDENTIFIED AS CREDIT NOTE / NEGATIVE VALUE"
                )
                print(
                    f"     Impact: Immediate escalation required for financial adjustment."
                )
                print(f"     Recommended Action: >> {d.recommended_action.upper()} <<")

            # --- Specific Handling for Currency ---
            elif isinstance(d, CurrencyMismatchDiscrepancy):
                print(
                    f"     Mismatch: {d.invoice_currency} found, expected {d.po_currency}"
                )
                print(f"     Recommended Action: >> {d.recommended_action.upper()} <<")

            # --- Specific Handling for Low Confidence ---
            elif isinstance(d, LowExtractionConfidenceDiscrepancy):
                for entry in d.fields:
                    print(f"     Affected Field: {entry.field}")
                    print(f"       Confidence of Field's Existence: {entry.field_existence_confidence}")
                    print(f"       Reasoning: {entry.reasoning}")
                    print(f"       Recommended Actions: {entry.recommended_action}")

    print("\n" + "█" * 60 + "\n")
