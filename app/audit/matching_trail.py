from app.models.matching_model import MatchingAgentOutput
from app.models.discrepancies_models.MatchingDiscrepancies import (
    POReferenceDiscrepancy,
    MultiplePOCandidatesDiscrepancy,
    PartialDeliveryDiscrepancy,
)


def log_matching_agent_results(result: MatchingAgentOutput):
    """
    Standardized logger for the Matching/Discovery Agent.
    Focuses on record reconciliation, pairing confidence, and structural gaps.
    """
    print("\n" + "█" * 60)
    print("--- MATCHING AGENT AUDIT LOG---".center(60))
    print("█" * 60)

    # 1. Primary Match Metadata
    print(f"\nMATCH METHOD: {result.match_method.upper()}")
    print(f"MATCHED PO:   {result.matched_po if result.matched_po else 'NONE'}")
    print(f"CONFIDENCE:   {result.po_match_confidence:.2%}")

    # 2. Pairing Metrics
    print(f"\n[PAIRING ATTRIBUTES]")
    print(
        f"  Supplier Match: {result.supplier_match} | Date Variance: {result.date_variance_days} days"
    )
    print(f"  Item Match Rate: {result.match_rate:.2%}")

    # 3. Alternative Candidates (For Multi-PO Logic)
    if result.alternative_matches:
        print(f"\n[ALTERNATIVE CANDIDATES]")
        for i, match in enumerate(result.alternative_matches, 1):
            print(
                f"  ({i}) PO: {match.po_number} | Conf: {match.confidence:.2%} | Method: {match.match_method}"
            )

    # 4. Matching Discrepancies (Structural & Identity gaps)
    print(f"\n[MATCHING DISCREPANCIES]")
    if not result.discrepancies:
        print("  ✅ Pairing is structurally identical to PO record.")
    else:
        for i, d in enumerate(result.discrepancies, 1):
            severity_icon = "🔴" if d.severity == "high" else "🟡"
            print(f"  {i}. {severity_icon} [{d.type.upper()}]")
            print(f"     Details: {d.details}")

            # Specific logic for Matching-only models
            if isinstance(d, POReferenceDiscrepancy):
                print(
                    f"     Recovery: Inferred {d.suggested_po_number} via fuzzy discovery."
                )

            elif isinstance(d, MultiplePOCandidatesDiscrepancy):
                candidate_ids = [c.suggested_po_number for c in d.candidates]
                print(f"     Conflict: Ambiguity between {', '.join(candidate_ids)}")

            elif isinstance(d, PartialDeliveryDiscrepancy):
                print(
                    f"     Subset: {d.matched_items}/{d.po_items_total} items paired."
                )
                status = (
                    "AUTO-APPROVE" if d.is_invoice_definitive_subset_of_po else "FLAG"
                )
                print(
                    f"     Sub-Logic: Definitive Subset? {d.is_invoice_definitive_subset_of_po} -> {status}"
                )

            print(f"     Action: {d.recommended_action.upper()}")

    # 5. Agent Reasoning
    print(f"\n[AGENT REASONING]")
    print(f"  {result.agent_reasoning}")
    print("\n" + "█" * 60 + "\n")
