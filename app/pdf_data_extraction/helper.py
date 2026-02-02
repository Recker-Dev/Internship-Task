import pymupdf
from pathlib import Path
import base64


def get_page_as_base64(pdf_path: Path, page_num: int, dpi: int = 300):
    """Renders a PDF page to a base64 encoded PNG string."""
    doc = pymupdf.open(pdf_path)
    page = doc.load_page(page_num)

    # 300 DPI is the sweet spot for receipt text clarity
    pix = page.get_pixmap(dpi=dpi)

    # Get PNG bytes directly from memory 
    image_bytes = pix.tobytes("png")

    # Encode to base64
    base64_string = base64.b64encode(image_bytes).decode("utf-8")

    doc.close()
    return base64_string
