"""PDF 下载与文本抽取（pymupdf 可选：未安装则只归档不抽取全文）。"""
from __future__ import annotations

import re

import httpx

from ..config import config


def download_pdf(url: str, arxiv_id: str) -> str:
    """下载 PDF 到归档目录，返回相对路径；失败返回空串（不阻断主流程）。"""
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
