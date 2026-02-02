1. Where does OCR/extraction fail? How do your agents compensate?

    OCR remains the most challenging domain in document processing, specifically when dealing with low-quality scans and handwriting, where traditional rule-based parsers fail. While specialized frameworks like `PaddleOCR` offer phenomenal capabilities for these edge cases, they introduce significant hardware overhead and local dependency bloat.

    For this project, I chose an Agentic Strategy rather than a dedicated OCR-engine approach. This keeps the system lightweight for local execution while maintaining a path to high-performance scaling. If this system were moved to enterprise-grade hardware, integrating a tool like PaddleOCR would be a logical next step to reduce LLM costs, but for this prototype, simplicity and portability take priority.


    How my system compensates:

    - Hybrid Detection: Using PyMuPDF, the system distinguishes between native text and image-based content. If an image or handwriting is detected, the multi-modal agent is triggered to normalize the data.

    - Page-wise Buffering: Data is extracted and aggregated into a page-wise buffer. This ensures that even if extraction is messy, the spatial context (which line item belongs to which total) is preserved.

    - Low-Confidence Fallback: When the extraction yields high uncertainty or missing keys (e.g., a handwritten PO number that is illegible), the Document Intelligence Agent raises a LowExtractionConfidenceDiscrepancy.

    - Down-Pipeline Healing: Instead of failing the process, this flag tells the Matching Agent to bypass strict Exact_PO_Match and initiate fuzzy reconciliation (Supplier_Date_Product_Match). By cross-referencing the "messy" OCR data with the clean purchase_orders.json database, the system "heals" the extraction error through relational context.

---
2. How would you improve accuracy from 70% to 95%?

    I would focus on refining the Agentic Loops and using the data we are already collecting to "teach" the system:

    - Targeted Retries: Since the Validation Agent uses Python to find math errors, I would add a "Loop Back" feature. If Python finds a line-item error, the system sends a specific hint back to the Document Agent (e.g., "Line 3 math failed, re-read this specific section"). This gives the LLM a second chance to fix a simple reading mistake.

    - Prompt Specialization: Right now, the prompts are likely general. I would create a small library of "Vendor Hints." If the system sees a specific supplier name it recognizes, it can pull in a small tip like "This vendor usually puts the VAT at the bottom left" to help the extraction agent focus.

    - Using the "Escalate" Logs: The outputs/ folder is a goldmine. I would manually review the first 100 "Escalate to Human" cases to find patterns. If 20% are failing because of a specific date format, I can simply update the Pydantic validation or the regex in the utils module to handle it.

---


3. How would you validate this system at 10,000 invoices/day scale?

    Scaling to 10,000 invoices per day shifts the focus to cost efficiency and compute orchestration. At this volume, API costs would be prohibitive, so a local-first strategy is essential.

    - Tiered Local Compute: To manage the heavy compute load, I would implement a tiered model architecture. Smaller, faster models (e.g., 4B-7B parameters) would handle simple extraction and routing, while larger models (20B+ parameters) would be reserved for complex, multi-page PDFs or deep-nested table structures, optimizing hardware cycles.

    - The "Golden Set" Regression Test: I would maintain a curated dataset of 500 diverse invoices (the "Golden Set"). Any update to a prompt or a Python validation script must be run against this set first. If the accuracy on these known files drops by even 1%, the update is rejected to prevent breaking the 10k/day pipeline.

    - Automated Discrepancy Analytics: At this scale, manual review is impossible. I would build a script to monitor the outputs/ directory for "Flag Spikes." If the rate of FinancialArithmeticDiscrepancy suddenly jumps from 2% to 15%, the system automatically alerts an engineer, as this usually indicates a vendor has changed their template or a model has begun to drift.