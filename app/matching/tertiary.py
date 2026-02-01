from app.utils.db_helpers import find_pos_by_item_desc
from app.models.invoice_extraction_model import InvoiceExtractionResults
from app.utils.helpers import (
    pair_invoice_items_to_po_items,
)


def tertiary_matching(
    invoice: InvoiceExtractionResults,
    desc_confidence_threshold=0.6,  # Minimum similarity for line match
    min_item_match_ratio=0.8,  # Require >80% of items matched
):
    """
    Tertiary / Product-Only Fallback Matching (Greedy):
    - Used when invoice has no PO reference or supplier mismatch.
    - Collects top candidates to allow for agentic comparison and reasoning.
    """

    invoice_items_list = [item.model_dump() for item in invoice.line_items]

    # Step 1: Find candidate POs by item description (Board Search)
    candidate_pos = find_pos_by_item_desc(
        invoice_items=invoice_items_list,
        confidence_threshold=desc_confidence_threshold,
    )

    candidates = []

    for po in candidate_pos:
        # Step 2: Pair invoice items to PO items (exact ID first, then fuzzy description)
        pairing_result = pair_invoice_items_to_po_items(
            invoice_items=invoice_items_list,
            po_items=po.get("line_items", []),
            desc_similarity_threshold=desc_confidence_threshold,
        )

        match_ratio = pairing_result.get("match_ratio", 0)

        if match_ratio >= min_item_match_ratio:
            # Step 3: Compute confidence (scale 40-70%)
            confidence = 0.4 + (match_ratio * 0.29)  # 0.4 → 0.69 scale

            candidates.append(
                {
                    "matched": True,
                    "match_method": "product_desc_only_fallback",
                    "matched_po": po,
                    "confidence": round(min(confidence, 0.69), 2),
                    "match_ratio": match_ratio,
                    "pairing_result": pairing_result,
                    "reasoning": (
                        f"Product-only match found for PO {po.get('po_number')}. "
                        f"Identified {int(match_ratio*100)}% of items based on description similarity."
                    ),
                }
            )

    # Step 4: Rank candidates by confidence
    candidates.sort(key=lambda x: x["confidence"], reverse=True)

    if not candidates:
        return {
            "matched": False,
            "reason": "No PO candidates met the 80% product match threshold",
            "candidates": [],
        }

    return {
        "matched": True,
        "candidates": candidates[:3],  # Return top 3 for agent review
    }
