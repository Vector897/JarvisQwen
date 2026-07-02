"""arXiv API 轮询（免费，无需 Key）。返回论文元数据列表。"""
from __future__ import annotations

import xml.etree.ElementTree as ET

import httpx

ATOM = "{http://www.w3.org/2005/Atom}"
API = "https://export.arxiv.org/api/query"


def search(query: str, max_results: int = 20) -> list[dict]:
    params = {
        "search_query": f"all:{query}" if ":" not in query else query,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
        "max_results": str(max_results),
    }
    resp = httpx.get(API, params=params, timeout=60, follow_redirects=True)
    resp.raise_for_status()
    root = ET.fromstring(resp.text)
    papers = []
    for entry in root.findall(f"{ATOM}entry"):
        raw_id = entry.findtext(f"{ATOM}id", "")
        arxiv_id = raw_id.rsplit("/abs/", 1)[-1] if "/abs/" in raw_id else raw_id
        pdf_url = ""
        for link in entry.findall(f"{ATOM}link"):
            if link.get("title") == "pdf":
                pdf_url = link.get("href", "")
        papers.append({
            "arxiv_id": arxiv_id,
            "title": " ".join((entry.findtext(f"{ATOM}title") or "").split()),
            "abstract": " ".join((entry.findtext(f"{ATOM}summary") or "").split()),
            "authors": ", ".join(
                a.findtext(f"{ATOM}name", "") for a in entry.findall(f"{ATOM}author")
            ),
            "published_at": entry.findtext(f"{ATOM}published", "")[:10],
            "url": raw_id,
            "pdf_url": pdf_url,
        })
    return papers
