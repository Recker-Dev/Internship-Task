from app.utils.db_helpers import find_po_by_number
from app.models.invoice_extraction_model import InvoiceExtractionResults
from app.utils.helpers import (
    get_date_window_variation,
    string_similarity,
    pair_invoice_items_to_po_items,
    validate_item_price,
    validate_total_variance,
)


def validate_invoice_wrt_po(
    invoice: InvoiceExtractionResults,
    matched_po_number: str,
    item_description_similarity_threshold: float = 0.7,
):
    # Exit if no valid matched_po_number to validate against
    po = find_po_by_number(matched_po_number)

    if po is None:
        return {
            "validated": False,
            "reason": "matched_po_number does not exist",
        }

    ## HEADER VALIDATION

    # Supplier sanity check
    supplier_score = string_similarity(
        invoice.supplier_name.strip().lower(),
        po.get("supplier", "").strip().lower(),
    )

    # Date window sanity check
    difference_in_days = get_date_window_variation(invoice.invoice_date, po.get("date"))

    # Currency Validation
    currency_ok = invoice.currency.strip().upper() == "GBP"

    header_report = {
        "supplier_name_similarity": round(supplier_score, 2),
        "days_difference": difference_in_days,
        "currency_ok": currency_ok,
    }

    ## STRUCTURAL VALIDATION
    invoice_line_items = [item.model_dump() for item in invoice.line_items]
    pairing_result = pair_invoice_items_to_po_items(
        invoice_items=invoice_line_items,
        po_items=po.get("line_items", []),
        desc_similarity_threshold=item_description_similarity_threshold,
    )

    pairs = pairing_result["pairs"]
    unmatched_invoice_items = pairing_result["unmatched_invoice_items"]
    unmatched_database_queried_po_items = pairing_result["unmatched_database_queried_po_items"]
    match_ratio = pairing_result["match_ratio"]

    if match_ratio == 1.0:
        # Check if it's a "Partial Delivery" (PO has items left over)
        if len(unmatched_database_queried_po_items) > 0:
            structural_report = {
                "status": "partial_delivery",
                "is_definitive_subset": True,
                "details": f"Invoice covers {len(pairs)} items. {len(unmatched_database_queried_po_items)} items remain on PO.",
            }
        else:
            # Everything matches exactly 1:1
            structural_report = {
                "status": "perfect_match",
                "is_definitive_subset": True,
                "details": "All invoice items match PO items exactly with no remainders.",
            }

    else:
        # Some items on the invoice do not exist on the PO
        structural_report = {
            "status": "mismatch",
            "is_definitive_subset": False,
            "unmatched_count": len(unmatched_invoice_items),
            "details": f"Found {len(unmatched_invoice_items)} items on invoice that do not exist on the matched PO.",
        }

    # Price Audit (Only audit paired items)
    item_price_results = []
    for pair in pairs:
        math_check = validate_item_price(
            invoice_item=pair["invoice_item"], po_item=pair["po_item"]
        )
        ## Attach Id and description
        if pair["invoice_item"].get("item_id"):
            math_check["item_id"] = pair["invoice_item"].get("item_id")
        if pair["invoice_item"].get("description"):
            math_check["description"] = pair["invoice_item"].get("description")

        item_price_results.append(math_check)

    # FINANCIALS VALIDATION
    total_check = validate_total_variance(
        invoice_total=invoice.totals.total_due,
        invoice_subtotal=invoice.totals.subtotal,
        invoice_vat_amount=invoice.totals.vat_amount,
        po_total=po.get("total"),
    )

    return {
        "header": header_report,
        "structure": structural_report,
        "item_audit": {
            "audited_count": len(item_price_results),
            "results": item_price_results,
            "all_items_paired": match_ratio == 1.0,
            "unmatched_invoice_items": unmatched_invoice_items,
        },
        "financials": total_check,
        "metadata": {
            "invoice_number": invoice.invoice_number,
            "invoice_po": invoice.po_number,
            "po_matched": matched_po_number,
        },
    }
