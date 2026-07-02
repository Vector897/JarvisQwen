"""导出：Markdown（始终可用）、BibTeX（Zotero/其他文献管理器可直接导入）、
PDF（可选依赖 reportlab；未安装则调用方应捕获 ImportError 并提示）。
"""
from __future__ import annotations

import io
import re


def to_bibtex(papers: list[dict]) -> str:
    """papers: [{arxiv_id, title, authors, published_at, url}]"""
    entries = []
    for p in papers:
        key = re.sub(r"[^\w]", "", p.get("arxiv_id") or p["title"][:20]) or "paper"
        year = (p.get("published_at") or "")[:4] or "n.d."
        authors = " and ".join(a.strip() for a in (p.get("authors") or "").split(",") if a.strip())
        entries.append(
            f"@misc{{{key},\n"
            f"  title = {{{p['title']}}},\n"
            f"  author = {{{authors}}},\n"
            f"  year = {{{year}}},\n"
            f"  eprint = {{{p.get('arxiv_id', '')}}},\n"
            f"  archivePrefix = {{arXiv}},\n"
            f"  url = {{{p.get('url', '')}}}\n"
            f"}}"
        )
    return "\n\n".join(entries)


def markdown_to_pdf_bytes(title: str, markdown_text: str) -> bytes:
    """极简 Markdown → PDF（reportlab，纯 Python 无需系统依赖）。未安装时抛 ImportError。"""
    from reportlab.lib.pagesizes import A4  # type: ignore
    from reportlab.lib.styles import getSampleStyleSheet  # type: ignore
    from reportlab.lib.units import cm  # type: ignore
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer  # type: ignore

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=2 * cm, bottomMargin=2 * cm)
    styles = getSampleStyleSheet()
    story = [Paragraph(_escape(title), styles["Title"]), Spacer(1, 12)]
    for line in markdown_text.splitlines():
        line = line.strip()
        if not line:
            story.append(Spacer(1, 6))
            continue
        if line.startswith("### "):
            story.append(Paragraph(_escape(line[4:]), styles["Heading3"]))
        elif line.startswith("## "):
            story.append(Paragraph(_escape(line[3:]), styles["Heading2"]))
        elif line.startswith("# "):
            story.append(Paragraph(_escape(line[2:]), styles["Heading1"]))
        else:
            story.append(Paragraph(_escape(line), styles["BodyText"]))
    doc.build(story)
    return buf.getvalue()


def _escape(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
