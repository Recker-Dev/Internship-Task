from datetime import date, datetime
from difflib import SequenceMatcher


def string_similarity(str1: str, str2: str) -> float:
    """Returns a similarity ratio (0.0 to 1.0) between two strings."""
    return SequenceMatcher(None, str1.lower(), str2.lower()).ratio()


def within_date_window(invoice_date, po_date, window_range=14) -> bool:
    """Returns bool based on whether given date is within the window range"""
    if isinstance(po_date, str):
        return (
            abs((invoice_date - datetime.strptime(po_date, "%Y-%m-%d").date()).days)
            <= window_range
        )

    return abs((invoice_date - po_date).days) <= window_range


def check_items_desc_match(invoice_items_list, po_items_list, similarity_threshold=0.7):
    matched_count = 0
    used_po_key_signatures = set()

    for inv_item in invoice_items_list:
        inv_item_id = inv_item.get("item_id", "")
        inv_item_desc = inv_item.get("description", "")

        best_match_key = None
        best_score = 0.0

        for po_item in po_items_list:

            # Create a Unique Key
            key = (
                po_item.get("item_id"),
                po_item.get("description"),
                po_item.get("quantity"),
                po_item.get("unit_price"),
            )

            if key in used_po_key_signatures:
                continue

            # Exact item_id match
            if inv_item_id and po_item.get("item_id", "") == inv_item_id:
                best_match_key = key
                best_score = 1.0
                break

            # Fuzzy description match
            score = string_similarity(inv_item_desc, po_item.get("description", ""))

            if score > best_score:
                best_score = score
                best_match_key = key

        if best_match_key and best_score >= similarity_threshold:
            matched_count += 1
            used_po_key_signatures.add(best_match_key)

    total_items = len(invoice_items_list)
    match_ratio = matched_count / total_items if total_items else 0.0

    return {
        "matched_items": matched_count,
        "total_items": total_items,
        "match_ratio": match_ratio,
        "meets_threshold": match_ratio >= similarity_threshold,
    }


def pair_invoice_items_to_po_items(
    invoice_items,
    po_items,
    desc_similarity_threshold=0.7,
):
    """
    Pairs invoice items to Po items:
    1. Exact item_id match (highest priority)
    2. Fuzzy description match (fallback)

    Returns:
        {
          "pairs": [ { invoice_item, po_item, match_score, matched_by } ],
          "unmatched_invoice_items": [...],
          "unmatched_po_items": [...]
        }
    """

    used_po_keys = set()
    pairs = []
    unmatched_invoice_items = []

    for inv_item in invoice_items:
        inv_item_id = inv_item.get("item_id", "")
        inv_desc = inv_item.get("description", "")

        best_po_item = None
        best_score = 0.0
        matched_by = None
        best_key = None

        for po_item in po_items:
            key = (
                po_item.get("item_id"),
                po_item.get("description"),
                po_item.get("quantity"),
                po_item.get("unit_price"),
            )

            if key in used_po_keys:
                continue

            ## Exact Id match
            if inv_item_id and po_item.get("item_id") == inv_item_id:
                best_po_item = po_item
                best_score = 1.0
                matched_by = "item_id"
                best_key = key
                break

            ## Fuzzy Fallback to Item description
            score = string_similarity(inv_desc, po_item.get("description", ""))

            if score > best_score:
                best_po_item = po_item
                best_score = score
                matched_by = "description"
                best_key = key

        if best_po_item and best_score >= desc_similarity_threshold:
            pairs.append(
                {
                    "invoice_item": inv_item,
                    "po_item": best_po_item,
                    "match_score": round(best_score, 3),
                    "matched_by": matched_by,
                }
            )
            used_po_keys.add(best_key)

        else:
            unmatched_invoice_items.append(inv_item)

    unmatched_po_items = [
        po_item
        for po_item in po_items
        if (
            po_item.get("item_id"),
            po_item.get("description"),
            po_item.get("quantity"),
            po_item.get("unit_price"),
        )
        not in used_po_keys
    ]

    return {
        "pairs": pairs,
        "unmatched_invoice_items": unmatched_invoice_items,
        "unmatched_database_queried_po_items": unmatched_po_items,
        "match_ratio": len(pairs) / len(invoice_items),
    }


def validate_item_price(invoice_item, po_item, math_error_tolerance=0.01):
    """
    Validate quantity, pricing, and arithmetic consistency for a
    matched invoice–PO line item pair.

    This function assumes the invoice item and PO item have already
    been paired (e.g., by item_id or description matching) and performs
    detailed numerical validation only.

    Checks performed:
    - Quantity equality
    - Unit price variance (absolute and percentage)
    - Line total variance (absolute and percentage)
    - Internal arithmetic consistency (quantity × unit_price ≈ line_total)

    Args:
        invoice_item (dict): A single invoice line item.
        po_item (dict): The corresponding purchase order line item.
        math_error_tolerance (float): Allowed absolute difference when
            validating computed totals (default: 0.01).

    Returns:
        dict: {
            "quantity_match": bool,

            "unit_price_variance": float | None,
            "unit_price_variance_percent": float | None,
            "unit_price_within_2percent": bool,
            "unit_price_within_5percent": bool,
            "unit_price_within_15percent": bool,

            "item_total_variance": float | None,
            "item_total_variance_percent": float | None,
            "item_total_variance_within_1percent": bool,
            "item_total_variance_within_5percent": bool,
            "item_total_variance_within_15percent": bool,

            "invoice_math_consistent": bool,
            "po_math_consistent": bool
        }
    """

    inv_qt = invoice_item.get("quantity")
    po_qt = po_item.get("quantity")

    inv_unit_price = invoice_item.get("unit_price")
    po_unit_price = po_item.get("unit_price")

    inv_line_total = invoice_item.get("line_total")
    po_line_total = po_item.get("line_total")

    ## Quantity Count Match
    quantity_match = inv_qt == po_qt

    ## Unit Price Variation
    unit_price_variance = None
    unit_price_variance_percent = None

    if inv_unit_price is not None and po_unit_price:
        unit_price_variance = inv_unit_price - po_unit_price
        unit_price_variance_percent = (unit_price_variance / po_unit_price) * 100

    ## Total Variation
    item_total_variance = None
    item_total_variance_percent = None

    if inv_line_total is not None and po_line_total:
        item_total_variance = inv_line_total - po_line_total
        item_total_variance_percent = (item_total_variance / po_line_total) * 100

    ## Math Consistency Check

    inv_computed_total = (
        inv_qt * inv_unit_price
        if inv_qt is not None and inv_unit_price is not None
        else None
    )

    po_computed_total = (
        po_qt * po_unit_price
        if po_qt is not None and po_unit_price is not None
        else None
    )

    inv_math_ok = (
        abs(inv_computed_total - inv_line_total) <= math_error_tolerance
        if inv_computed_total is not None and inv_line_total is not None
        else False
    )

    po_math_ok = (
        abs(po_computed_total - po_line_total) <= math_error_tolerance
        if po_computed_total is not None and po_line_total is not None
        else False
    )

    return {
        "quantity_match": quantity_match,
        "unit_price_variance": (
            round(unit_price_variance, 2) if unit_price_variance is not None else None
        ),
        "unit_price_variance_percent": (
            round(unit_price_variance_percent, 2)
            if unit_price_variance_percent is not None
            else None
        ),
        "unit_price_within_2percent": (
            abs(unit_price_variance_percent) <= 2
            if unit_price_variance_percent is not None
            else False
        ),
        "unit_price_within_5percent": (
            abs(unit_price_variance_percent) <= 5
            if unit_price_variance_percent is not None
            else False
        ),
        "unit_price_within_15percent": (
            abs(unit_price_variance_percent) <= 15
            if unit_price_variance_percent is not None
            else False
        ),
        "item_total_variance": (
            round(item_total_variance, 2) if item_total_variance is not None else None
        ),
        "item_total_variance_percent": (
            round(item_total_variance_percent, 2)
            if item_total_variance_percent is not None
            else None
        ),
        "item_total_variance_within_1percent": (
            abs(item_total_variance_percent) <= 1
            if item_total_variance_percent is not None
            else False
        ),
        "item_total_variance_within_5percent": (
            abs(item_total_variance_percent) <= 5
            if item_total_variance_percent is not None
            else False
        ),
        "item_total_variance_within_15percent": (
            abs(item_total_variance_percent) <= 15
            if item_total_variance_percent is not None
            else False
        ),
        "invoice_math_consistent": inv_math_ok,
        "po_math_consistent": po_math_ok,
    }


def validate_total_variance(
    invoice_total, po_total, max_variance=5, max_percent_variance=1
):
    """
    Validates if the total variance between the invoice and PO is within acceptable limits.

    Args:
        invoice_total (float): The total amount from the invoice.
        po_total (float): The total amount from the purchase order.
        max_variance (float): The maximum allowable total variance (default is 5).
        max_percent_variance (float): The maximum allowable percentage variance (default is 1%).

    Returns:
        dict: A dictionary containing:
            - "valid": (bool) Whether the total variance is within acceptable limits.
            - "total_variance": (float) The absolute total variance.
            - "total_variance_percent": (float) The percentage total variance.
    """
    if po_total is None or invoice_total is None:
        return {"valid": False, "reason": "missing_total"}

    total_variance = abs(invoice_total - po_total)
    total_variance_percent = (total_variance / po_total) * 100 if po_total else None

    valid = total_variance <= max_variance or (
        total_variance_percent is not None
        and total_variance_percent <= max_percent_variance
    )

    return {
        "valid": valid,
        "total_variance": round(total_variance, 2),
        "total_variance_percent": (
            round(total_variance_percent, 2)
            if total_variance_percent is not None
            else None
        ),
    }
