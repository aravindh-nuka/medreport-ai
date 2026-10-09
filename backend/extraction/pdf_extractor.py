"""
Digital PDF text extraction.

Deliberately does NOT use OCR. Only text-based/digital PDFs are supported —
this is a product decision to avoid the accuracy problems of OCR on
handwritten or scanned medical reports. If a PDF yields near-zero
extractable text, we treat it as unsupported and tell the user clearly
rather than guessing from a scanned image.
"""
from dataclasses import dataclass

import fitz  # PyMuPDF
import pdfplumber


class UnsupportedPDFError(Exception):
    """Raised when a PDF appears to be scanned/image-based (no extractable text)."""


@dataclass
class ExtractedPage:
    page_number: int
    text: str
    tables: list[list[list[str | None]]]


@dataclass
class ExtractionResult:
    full_text: str
    pages: list[ExtractedPage]


MIN_CHARS_PER_PAGE_TO_BE_DIGITAL = 20


def extract_pdf(file_path: str) -> ExtractionResult:
    """
    Primary extraction via pdfplumber (best for tables + layout in lab reports).
    Falls back to PyMuPDF per-page if pdfplumber returns nothing for a page.
    Raises UnsupportedPDFError if the document has no meaningful extractable text,
    which signals a scanned/image-only PDF that this app intentionally does not support.
    """
    pages: list[ExtractedPage] = []

    with pdfplumber.open(file_path) as pdf:
        fitz_doc = fitz.open(file_path)
        for i, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            tables = page.extract_tables() or []

            if len(text.strip()) < MIN_CHARS_PER_PAGE_TO_BE_DIGITAL:
                # fallback attempt with PyMuPDF before giving up on this page
                try:
                    text = fitz_doc[i].get_text("text") or text
                except Exception:
                    pass

            pages.append(ExtractedPage(page_number=i + 1, text=text, tables=tables))
        fitz_doc.close()

    full_text = "\n\n".join(p.text for p in pages).strip()

    if len(full_text) < MIN_CHARS_PER_PAGE_TO_BE_DIGITAL:
        raise UnsupportedPDFError(
            "This PDF does not contain extractable digital text. It may be a scanned "
            "or image-based document, which this app does not support. Please upload "
            "a digitally generated PDF report."
        )

    return ExtractionResult(full_text=full_text, pages=pages)
