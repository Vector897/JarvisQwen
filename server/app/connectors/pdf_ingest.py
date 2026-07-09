"""PDF download and text extraction (pymupdf optional: if not installed, only archive without extracting full text)."""
from __future__ import annotations

import re

import httpx

from ..config import config


def download_pdf(url: str, arxiv_id: str) -> str:
    """Download the PDF to the archive directory and return its relative path; returns an empty string on failure (does not block the main flow)."""
    if not url:
        return ""
    safe_name = re.sub(r"[^\w.-]", "_", arxiv_id or url.rsplit("/", 1)[-1]) + ".pdf"
    dest = config.pdf_dir / safe_name
    if dest.exists():
        return str(dest)
    try:
        with httpx.stream("GET", url, timeout=120, follow_redirects=True) as r:
            r.raise_for_status()
            with open(dest, "wb") as f:
                for chunk in r.iter_bytes(65536):
                    f.write(chunk)
        return str(dest)
    except Exception:  # noqa: BLE001
        return ""


def extract_text(pdf_path: str, max_chars: int = 60000) -> str:
    if not pdf_path:
        return ""
    try:
        import fitz  # pymupdf

        doc = fitz.open(pdf_path)
        text = "".join(page.get_text() for page in doc)
        return text[:max_chars]
    except Exception:  # noqa: BLE001
        return ""
