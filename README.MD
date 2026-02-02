Here’s a clean, copy-pasteable **README.md** tailored to a **uv** project with the entry point `uv run -m app.main`, and clear instructions on cycling through the invoice test files.

---

# Invoice Processing Project

This project is a Python application managed with **uv**. It processes invoice PDF files one at a time via a configurable entry point.

## Prerequisites

- Python 3.9+ (recommended)
- `uv` installed

---

The main module is run using:

```bash
uv run -m app.main
```

---

## Project Structure

```text
.
├── app/
│   ├── ai/
│   │   ├── __init__.py
│   │   └── ...
│   ├── audit/
│   │   ├── __init__.py
│   │   └── ...
│   ├── core/
│   │   ├── __init__.py
│   │   └── ...
│   ├── llm/
│   │   ├── __init__.py
│   │   └── ...
│   ├── matching/
│   │   ├── __init__.py
│   │   └── ...
│   ├── models/
│   │   └── ...
│   ├── pdf_data_extraction/
│   │   ├── __init__.py
│   │   └── ...
│   ├── utils/
│   │   ├── __init__.py
│   │   └── ...
│   ├── validation/
│   │   ├── __init__.py
│   │   └── ...
│   ├── workflow/
│   │   ├── __init__.py
│   │   └── ...
│   └── main.py
├── docs/
│   └── ...files
├── output/
│   └── [Generated Output JSONs]
├── .env.example
├── .gitignore
├── .python-version
├── purchase_orders.json
├── pyproject.toml
└── uv.lock
```

## Module Summary

- ai: Houses core logic and prompt templates.

- audit: Handles structured logging and print utilities.

- core: Centralized environment variable and API key management.

- llm: The "Provider" layer for distributing LLM instances across the app.

- matching: Specialized logic for reconciling invoices against Purchase Orders (PO).

- models: All Pydantic Models with respect to agent's outputs and discrepancies.

- pdf_data_extraction: The OCR and text processing engine.

- utils: Contains database operations and common helper functions.

- validation: Mathematical and schema-based validation for financial data.

- workflow: The orchestration layer (LangGraph) that ties the modules together.

- main.py: The primary entry point for the application.

---

## Entry Point

The application is run using:

```bash
uv run -m app.main
```

This executes the `main.py` module inside the `app` package.

---

## Invoice Test Files

Inside `app/main.py`, there are several predefined invoice files for testing different scenarios:

```python
 file_name = "Invoice_1_Baseline.pdf"
# file_name = "Invoice_2_Scanned.pdf"
# file_name = "Invoice_3_Different_Format.pdf"
# file_name = "Invoice_4_Price_Trap.pdf"
# file_name = "Invoice_5_Missing_PO.pdf"
```

### How to Use

1. **Uncomment exactly one** `file_name` line at a time.
2. Leave all other `file_name` lines commented.
3. Run the application.
4. Review the output.
5. Comment the current file and uncomment the next one to continue testing.

This ensures each invoice is processed independently and results are easy to compare.

---


# Invoice Processing Pipeline: Technical Documentation

## 🏗️ Product Architecture

The system is architected as a sequential multi-agent pipeline powered by **LangGraph**. It is specifically designed to handle complex PDF extractions, fuzzy matching against Purchase Order (PO) databases, and automated financial auditing.

### 1. Document Intelligence Agent
* **Input:** PDF files.
* **Processing Logic:**
    * **Native Text:** If the PDF contains text blocks, data is extracted line-by-line via the `pdf_data_extraction` module.
    * **Embedded Images:** If pages are image-based, an **OCR pipeline** is triggered. A **multi-modal agent** processes the OCR output to normalize it into the same text-based stream as native PDFs.
* **Accumulation:** Text is gathered on a page-by-page basis into a string accumulator before being passed to the AI module.
* **Extraction:** Uses Pydantic models (from `models/`) to structure relevant fields.
* **Discrepancies Raised:** `LowExtractionConfidenceDiscrepancy`, `CreditNoteDiscrepancy` (High Risk), `CurrencyMismatchDiscrepancy` (High Risk).

### 2. Matching Agent
The sole purpose of this agent is to reconcile the extracted invoice data with the `purchase_orders.json` database using a tiered fallback strategy.

| Algorithm | Logic | Thresholds / Constraints |
| :--- | :--- | :--- |
| **Exact_PO_Match** | Strict Matching | < 2% Price Var; < 1% or £5 Total Var (whichever is smaller). |
| **Supplier_Date_Item_Match** | Fuzzy Reconcile | 5-15% Price Var; Dates within ±14 days; minor desc discrepancies. |
| **Product_Only** | Last Fallback | 40-70% match on product/item strings only. |

* **Behavior:** If multiple matches are found, the agent selects the most confident candidate as the `matched_PO`. 
* **Discrepancies Raised:** `MultiplePOCandidatesDiscrepancy`, `PartialDeliveryDiscrepancy`, `POReferenceDiscrepancy` (raised whenever primary exact match fails).

### 3. Validation Agent
Acts as a financial auditor, checking the integrity of the prices and item mapping between the Invoice and the Matched PO.
* **Scope:** Validates Line Item quantity, unit price, net price, subtotal, VAT, and Total Invoice price.
* **Fuzzy Validation:** Checks if mathematical variations lie within permissible limits.
* **Discrepancies Raised:** `LineItemPriceDiscrepancy`, `LineItemQuantityDiscrepancy`, `SupplierNameDiscrepancy`, `TotalAmountVarianceDiscrepancy`, `FinancialArithmeticDiscrepancy` (High Severity), `UnexpectedItemDiscrepancy` (High Severity).

### 4. Resolution Agent
The final decision engine that aggregates all data and flags from previous steps.
* **Early Exit:** If **3 or more** discrepancies have been raised throughout the pipeline, the system triggers an early exit.
* **Outputs:** The agent provides a decision (`auto_approve`, `flag_for_review`, or `escalate_to_human`) along with detailed reasoning.

---

## 🔍 Critical Test Case Analysis

### Case #4: The Price Trap (Variance Escalation)
* **Scenario:** A line item has an obvious 10% price variance.
* **Failure Point:** `Exact_PO_Match` fails immediately because it breaks the hard 2% limit. This raises a `POReferenceDiscrepancy` and flags the file for review.
* **Validation Audit:** The Validation Agent detects two further issues: a `LineItemPriceDiscrepancy` (the 10% shift) and a `TotalAmountVarianceDiscrepancy` (net total variation > 2%).
* **Result:** With a total of **3 discrepancies** (Reference + Line Item + Total Var), the Resolution Agent escalates the file to **Human** intervention.

### Case #5: The Missing PO (Identification Failure)
* **Scenario:** An invoice is submitted without a PO Number (N/A).
* **Extraction Point:** The Document Agent raises a `LowExtractionConfidenceDiscrepancy` with high risk due to the missing critical field.
* **Matching Point:** The Matching Agent raises a `POReferenceDiscrepancy` as the ID is missing, falling back to a `Supplier_Date_Product` fuzzy search to find a candidate.
* **Result:** Although the Validation Agent may find no arithmetic errors, the Resolution Agent identifies the combination of a missing PO and low extraction confidence as a critical integrity failure. It defaults to **Escalate to Human**, mirroring real-world financial safety protocols.

## 📁 Output Management
All successful pipeline executions generate a standardized JSON record stored in the `outputs/` directory.