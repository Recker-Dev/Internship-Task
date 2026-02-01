from app.utils.db_helpers import find_pos_by_supplier
from app.models.invoice_extraction_model import InvoiceExtractionResults
from app.utils.helpers import (
    within_date_window,
    pair_invoice_items_to_po_items,
)


def secondary_matching(
    invoice: InvoiceExtractionResults,
    supplier_score_threshold=0.7,  # Lowered from 0.9
    date_window_days=14,  # Expanded window
    min_item_match_ratio=0.7,  # 70% of items must match
):
    ## Sorted with most similar supplier match on top
    potential_pos = find_pos_by_supplier(
        invoice.supplier_name, supplier_score_threshold
    )

    for po in potential_pos:

        ## Check if valid date window or skip
        if not within_date_window(
            invoice.invoice_date, po.get("date"), date_window_days
        ):
            continue

        # Check Line Item Overlap
        pairing_result = pair_invoice_items_to_po_items(
            invoice_items=[item.model_dump() for item in invoice.line_items],
            po_items=po.get("line_items", []),
            desc_similarity_threshold=0.7,
        )

        match_ratio = pairing_result["match_ratio"]

        if match_ratio >= min_item_match_ratio:
            # Viable Candiate wrt Secondary Matching
            confidence = 0.60 + (match_ratio * 0.25)  # Scale confidence 60-85%

            ## Performs Early Exit for which-ever Po meets the criteria.
            return {
                "matched": True,
                "match_method": "supplier_contextual_fallback",
                "matched_po": po,
                "confidence": round(confidence, 2),
                "match_ratio": match_ratio,
                "pairing_result": pairing_result,
                "reason": "Supplier and date match with high item overlap",
            }

    return {"matched": False, "reason": "no_contextual_match_found"}
