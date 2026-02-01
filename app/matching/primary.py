from app.utils.db_helpers import find_po_by_number
from app.models.invoice_extraction_model import InvoiceExtractionResults
from app.utils.helpers import (
    within_date_window,
    string_similarity,
    pair_invoice_items_to_po_items,
    validate_item_price,
    validate_total_variance,
)
from datetime import datetime


def primary_matching(
    invoice: InvoiceExtractionResults,
    supplier_score_threshold=0.9,
    date_discrepencry_window_range=7,
    description_similarity_threshold=0.9,
):
    # Strict Po Checking
    po = find_po_by_number(invoice.po_number)
    if po is None:
        return {
            "matched": False,
            "reason": "no_dirct_po_match",
        }

    # Supplier sanity check (strict but normalized)
    supplier_score = string_similarity(
        invoice.supplier_name.strip().lower(),
        po.get("supplier", "").strip().lower(),
    )
    if supplier_score < supplier_score_threshold:
        return {
            "matched": False,
            "reason": "supplier_score_fail",
            "score_threshold": supplier_score_threshold,
        }

    ## Date sanity check
    if not within_date_window(
        invoice.invoice_date, po.get("date", ""), date_discrepencry_window_range
    ):
        return {
            "matched": False,
            "reason": "date_window_fail",
            "date_discrepencry_window_range": date_discrepencry_window_range,
        }

    invoice_line_items = [item.model_dump() for item in invoice.line_items]

    ## Item Wise pairing check (Strict)
    pairing_result = pair_invoice_items_to_po_items(
        invoice_items=invoice_line_items,
        po_items=po.get("line_items", []),
        desc_similarity_threshold=description_similarity_threshold,
    )

    total_invoice_items = len(invoice_line_items)
    matched_items = len(pairing_result["pairs"])

    # Require perfect structural match in Primary
    if matched_items != total_invoice_items:
        return {
            "matched": False,
            "reason": "partial_line_item_match",
            "pairing_result": pairing_result,
        }

    # Per-item price & quantity validation
    item_validations = []

    for pair in pairing_result["pairs"]:
        validation = validate_item_price(
            pair["invoice_item"],
            pair["po_item"],
        )
        item_validations.append(validation)

        # Strict primary tolerances
        if not (
            validation["quantity_match"]
            and validation["unit_price_within_2percent"]
            and validation["item_total_variance_within_1percent"]
        ):
            return {
                "matched": False,
                "reason": "item_level_variance",
                "pairing_result": pairing_result,
                "item_validations": item_validations,
            }

    # Net Total Validation (Strict)
    total_check = validate_total_variance(
        invoice_total=invoice.totals.total_due,
        invoice_subtotal=invoice.totals.subtotal,
        invoice_vat_amount=invoice.totals.vat_amount,
        po_total=po.get("total"),
    )

    if not total_check["valid"]:
        return {
            "matched": False,
            "reason": "total_variance_exceeded",
            "total_variance": total_check["total_variance"],
            "total_variance_percent": total_check["total_variance_percent"],
        }

    # Successful Primary Match
    return {
        "matched": True,
        "match_method": "exact_po_reference",
        "matched_po": po.get("po_number"),
        "confidence": 0.97,
        "supplier_similarity": round(supplier_score, 3),
        "date_variance_days": abs(
            (
                invoice.invoice_date
                - datetime.strptime(po.get("date"), "%Y-%m-%d").date()
            ).days
        ),
        "pairing_result": pairing_result,
        "item_validations": item_validations,
        "total_variance": total_check["variance_amount"],
        "total_variance_percent": total_check["variance_percent"],
    }
