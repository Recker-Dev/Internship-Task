import pymupdf
from pathlib import Path
from app.llm.builder import LLMProviderFactory
from app.pdf_data_extraction.helper import get_page_as_base64
from typing import Dict, Any, List, cast
from collections import defaultdict


ROOT_DIR = Path(__file__).resolve().parent.parent.parent  ## App level
DOCS_DIR = ROOT_DIR / "docs"


async def process_file(file_name) -> dict:
    pdf_path = DOCS_DIR / file_name
    pdf_path = pdf_path.resolve()

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    full_text_content = []
    print("[Processing]:", pdf_path)

    # Calculate file size in KB
    file_size_kb = round(pdf_path.stat().st_size / 1024, 2)

    doc = pymupdf.open(pdf_path)
    page_count = len(doc)

    full_text_content = []

    # Iterate through all pages
    for page_num in range(page_count):
        page = doc.load_page(page_num)
        text_dict = page.get_text("dict")
        if not isinstance(text_dict, dict):
            print(
                f"Skipping Page Number: {page_num} as it failed to return a valid dict for processing."
            )
            continue

        has_text = any(b["type"] == 0 for b in text_dict["blocks"])

        if has_text:
            f"--- Page {page_num + 1}: Normal text content detected. Aggregating Text... ---"
            # Traditional extraction for digital PDFs
            page_text = extract_text_from_dict(text_dict)
        else:
            # 2. Page is a scan. Render to image and run OCR
            print(
                f"--- Page {page_num + 1}: Scanned content detected. Running OCR... ---"
            )
            llm = LLMProviderFactory.groqImage()
            page_text = await llm.invoke(
                request="Extract all text from this receipt. If it is rotated, read it correctly. "
                "Return only the text, maintaining the logical structure.",
                base64_image=get_page_as_base64(pdf_path, page_num),
            )

        full_text_content.append(f"--- Page {page_num + 1} ---\n{page_text}")

    doc.close()

    return {
        "filename": file_name,
        "file_size_kb": file_size_kb,
        "page_count": page_count,
        "content": "\n\n".join(full_text_content),
    }


def extract_text_from_dict(text_dict: dict, y_tolerance=5) -> str:
    ## Extract Text from dict and format it
    spans = []
    for block in text_dict["blocks"]:
        if block["type"] == 0:
            for line in block["lines"]:
                for span in line["spans"]:
                    spans.append(
                        {
                            "text": span["text"].strip(),
                            "x": span["bbox"][0],
                            "y": span["bbox"][1],
                        }
                    )

    # Simple line grouping
    lines = defaultdict(list)
    for span in sorted(spans, key=lambda s: (s["y"], s["x"])):
        line_key = round(span["y"] / y_tolerance) * y_tolerance
        lines[line_key].append(span["text"])

    return "\n".join([" | ".join(l) for _, l in sorted(lines.items())])
