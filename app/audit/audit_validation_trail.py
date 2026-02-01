from app.models.validation_model import ValidationAgentOutput
from app.models.discrepancies_models.ValidationDiscrepanices import (
    LineItemPriceDiscrepancy,
    LineItemQuantityDiscrepancy,
    SupplierNameDiscrepancy,
    TotalAmountVarianceDiscrepancy,
    FinancialArithmeticDiscrepancy,
    UnexpectedItemDiscrepancy,
)


def log_validation_agent_results(result: ValidationAgentOutput):
    """
    Standardized logger for the Validation Agent.
    Focuses on financial accuracy, unit price auditing, and arithmetic integrity.
    """
    print("\n" + "═" * 60)
    print("--- VALIDATION AGENT AUDIT LOG ---".center(60))
    print("═" * 60)

    # 1. Audit Metadata
    status_colors = {
        "clean": "✅ CLEAN",
        "minor failures": "⚠️ MINOR FAILURES",
        "critical failures": "🚨 CRITICAL FAILURES",
    }
    print(f"\nAUDIT ID: {result.audit_id}")
    print(f"STATUS:   {status_colors.get(result.status, result.status.upper())}")

    # 2. Discrepancy Breakdown
    print(f"\n[DETAILED DISCREPANCIES]")
    if not result.discrepancies:
        print("  ✅ No financial or line-item variances detected.")
    else:
        for i, d in enumerate(result.discrepancies, 1):
            severity_icon = (
                "🔴"
                if d.severity == "high"
                else ("🟡" if d.severity == "medium" else "⚪")
            )
            print(f"  {i}. {severity_icon} [{d.type.upper()}]")

            # --- Line Item Price Logic ---
            if isinstance(d, LineItemPriceDiscrepancy):
                print(f"     Item: {d.description} (ID: {d.item_id or 'N/A'})")
                print(
                    f"     Variance: {d.variance_percent:+.2f}% | Invoice: {d.invoice_unit_price} vs PO: {d.po_unit_price}"
                )

            # --- Line Item Quantity Logic ---
            elif isinstance(d, LineItemQuantityDiscrepancy):
                print(f"     Item: {d.description}")
                diff = d.invoice_quantity - d.po_quantity
                trend = "OVER-BILLED" if diff > 0 else "UNDER-BILLED"
                print(
                    f"     Trend: {trend} | Inv: {d.invoice_quantity} | PO: {d.po_quantity}"
                )

            # --- Supplier Name Logic ---
            elif isinstance(d, SupplierNameDiscrepancy):
                print(f"     Match Score: {d.similarity_score:.2%}")
                print(
                    f"     Inv Name: {d.invoice_supplier_name} | PO Name: {d.po_supplier_name}"
                )

            # --- Total Amount Logic ---
            elif isinstance(d, TotalAmountVarianceDiscrepancy):
                print(
                    f"     Global Variance: {d.variance_percent:+.2f}% ({d.variance_amount:+.2f} absolute)"
                )
                print(f"     Inv Total: {d.invoice_total} | PO Total: {d.po_total}")

            # --- Arithmetic Logic ---
            elif isinstance(d, FinancialArithmeticDiscrepancy):
                print(
                    f"     Calculated: {d.calculated_expected_total} | Stated Total: {d.invoice_total_due}"
                )
                print(
                    f"     Breakdown: Subtotal({d.invoice_subtotal}) + VAT({d.invoice_vat_amount})"
                )

            # --- Unexpected Item Logic ---
            elif isinstance(d, UnexpectedItemDiscrepancy):
                print(f"     Surprise Item: {d.item_description}")
                print(f"     Qty: {d.item_quantity} | Line Total: {d.item_total}")

            print(f"     Action: {d.recommended_action.upper()}")

    # 3. Agent Reasoning (The Narrative)
    print(f"\n[AGENT REASONING]")
    # Wrap text if necessary, but here we just print the breakdown
    print(f"  {result.agent_reasoning}")

    print("\n" + "═" * 60 + "\n")
