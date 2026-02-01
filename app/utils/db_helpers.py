from app.utils.db import get_db
from app.utils.helpers import string_similarity


def find_po_by_number(po_number: str):
    """
    Returns the PO with the exact number, or None if not found.
    """
    db = get_db()
    for po in db:
        if po.get("po_number") == po_number:
            return po
    return None


def find_pos_by_supplier(invoice_supplier: str, min_similarity: float = 0.7):
    """
    Returns a list of PO candidates for a supplier.
    Exact matches first, then fuzzy matches above min_similarity.
    Sorted descending wrt similarity score.
    """
    if invoice_supplier == "":
        return []

    db = get_db()
    exact_matches = []
    fuzzy_matches = []

    for po in db:
        supplier = po.get("supplier", "")
        if supplier.strip().lower() == invoice_supplier.strip().lower():
            exact_matches.append({"po": po, "confidence": 0.99})
        else:
            sim = string_similarity(invoice_supplier, supplier)
            if sim >= min_similarity:
                fuzzy_matches.append({"po": po, "confidence": sim})

    final = exact_matches + fuzzy_matches
    final.sort(key=lambda x: x["confidence"], reverse=True)
    return [entry["po"] for entry in final]


def find_pos_by_item_desc(invoice_items, confidence_threshold=0.6):
    """
    Identifies candidate POs by fuzzy-matching line item descriptions.

    Implements a greedy 1-to-1 matching heuristic to associate invoice lines
    with PO lines. PO items are removed from the candidate pool once matched
    to prevent duplicate assignments.

    Args:
        invoice_items (list): Extracted invoice items with 'description' keys.
        confidence_threshold (float): Minimum similarity to accept a pair match.

    Returns:
        list: Candidate matches ranked by average similarity score.
    """
    db = get_db()
    all_candidate_matches = []

    for po in db:
        po_line_items = po.get("line_items", [])
        ## Greedy matching inside this specific PO
        matched_scores = []
        available_po_items = po_line_items.copy()  ## To keep track of what's left

        for inv_item in invoice_items:
            best_score_for_this_inv_line = 0
            best_po_line_idx = -1

            # Find the highest similarity match in current PO pool
            for i, po_item in enumerate(available_po_items):
                score = string_similarity(
                    inv_item.get("description"), po_item.get("description")
                )

                # Greedy: consume the PO item if threshold met so next invoice item can't check against it.
                if score > best_score_for_this_inv_line:
                    best_score_for_this_inv_line = score
                    best_po_line_idx = i

            # If we found a valid match within this PO
            if best_score_for_this_inv_line > confidence_threshold:
                matched_scores.append(best_score_for_this_inv_line)
                available_po_items.pop(best_po_line_idx)

        ## Score the PO as a whole
        if matched_scores:
            avg_po_score = sum(matched_scores) / len(invoice_items)

            all_candidate_matches.append(
                {
                    "po_number": po.get("po_number"),
                    "total_score": avg_po_score,
                    "match_count": len(matched_scores),
                    "original_po": po,
                }
            )

    # Sort all POs found by their total score
    all_candidate_matches.sort(key=lambda x: x["total_score"], reverse=True)

    return [candidate["original_po"] for candidate in all_candidate_matches]
