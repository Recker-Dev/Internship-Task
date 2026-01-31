import pymupdf
from pathlib import Path
from pprint import pprint
from collections import defaultdict

ROOT_DIR = Path(__file__).resolve().parent.parent.parent  ## App level
DOCS_DIR = ROOT_DIR / "docs"


def process_file(file_name) -> str:
    pdf_path = DOCS_DIR / file_name
    pdf_path = pdf_path.resolve()

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    print("[Processing]:", pdf_path)

    doc = pymupdf.open(pdf_path)

    invoice_page = doc.load_page(0)

    text_dict = invoice_page.get_text("dict")
    if not isinstance(text_dict, dict):
        raise ValueError(
            f"PDF:  {pdf_path} cannot be parsed as dict for text extraction."
        )
    return extract_text(text_dict)


def extract_text(text_dict: dict, y_tolerance=5) -> str:
    spans = []
    for block in text_dict["blocks"]:
        if block["type"] != 0:
            continue  # skip non-text blocks

        for line in block["lines"]:
            # Sort spans left-to-right within the line
            sorted_spans = sorted(line["spans"], key=lambda s: s["bbox"][0])
            for span in sorted_spans:
                x0, y0, x1, y1 = span["bbox"]
                spans.append(
                    {
                        "text": span["text"].strip(),
                        "x": round(x0, 1),
                        "y": round(y0, 1),
                    }
                )

    spans.sort(key=lambda d: (d["y"], d["x"]))

    lines = defaultdict(list)
    for span in spans:
        line_key = round(span["y"] / y_tolerance) * y_tolerance
        lines[line_key].append(span)

    sorted_line_keys = sorted(lines.keys())

    output = []
    for key in sorted_line_keys:
        line_spans = sorted(lines[key], key=lambda s: s["x"])
        line_text = " | ".join([s["text"] for s in line_spans])
        output.append(line_text)


    return "\n".join(output)
