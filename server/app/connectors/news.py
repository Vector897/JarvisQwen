"""News retrieval (Google News RSS: free, no key required, covers any topic).

Lets non-academic queries (stocks/finance/current-affairs/politics and other topics
arXiv doesn't cover) flow into the same fetch→dedupe→triage→summarize→brief pipeline.
Returned items are structurally identical to the arxiv connector (no PDF: pdf_url is
left empty, and the pipeline automatically falls back to the abstract as summary material).
"""
from __future__ import annotations

import html
import re
import threading
import xml.etree.ElementTree as ET

import httpx

RSS = "https://news.google.com/rss/search"
_TAG = re.compile(r"<[^>]+>")
_CJK = re.compile(r"[一-鿿぀-ヿ가-힯]")

# Signal words indicating the query fits a news source (rather than the arXiv academic library)
_NEWS_SIGNALS = (
    "stock", "shares", "share price", "price target", "market", "earnings", "ipo",
    "merger", "acquisition", "acquire", "ceo", "revenue", "nasdaq", "dow", "s&p",
    "crypto", "bitcoin", "ethereum", "etf", "dividend", "quarterly", "guidance",
    "election", "president", "prime minister", "minister", "senate", "congress",
    "parliament", "war", "sanction", "lawsuit", "court", "verdict", "layoff",
    "launch", "unveil", "release date", "recall", "outage",
    "股", "财报", "上市", "收购", "并购", "首相", "总统", "大选", "选举", "发布",
    "战争", "制裁", "诉讼", "价格", "行情", "新闻", "换届", "涨", "跌",
)


def _clean(s: str) -> str:
    return " ".join(html.unescape(_TAG.sub(" ", s or "")).split())


def _locale(query: str) -> tuple[str, str, str]:
    """CJK queries route to the Chinese news region, everything else to the English region."""
    if _CJK.search(query):
        return "zh-CN", "CN", "CN:zh-Hans"
    return "en-US", "US", "US:en"


def is_news_query(query: str) -> bool:
    """Decide whether the query fits a news source. Treated as news if it matches a signal word or is predominantly CJK."""
    q = query.lower()
    if any(sig in q for sig in _NEWS_SIGNALS):
        return True
    letters = [c for c in query if c.isalpha()]
    if letters and sum(1 for c in letters if _CJK.match(c)) / len(letters) > 0.3:
        return True
    return False


def _bounded(fn, timeout: float, default):
    """Run fn in a daemon thread, waiting at most `timeout` seconds. Returns default on
    timeout/exception, never blocking the caller (the daemon thread exits with the process
    and won't hang the worker). A stuck DNS resolution is not governed by httpx timeouts,
    so this safety net is necessary."""
    box = [default]

    def run() -> None:
        try:
            box[0] = fn()
        except Exception:  # noqa: BLE001  network/parse failure → keep default
            pass

    t = threading.Thread(target=run, daemon=True)
    t.start()
    t.join(timeout)
    return box[0]


def _fetch(query: str, max_results: int) -> list[dict]:
    hl, gl, ceid = _locale(query)
    resp = httpx.get(
        RSS, params={"q": query, "hl": hl, "gl": gl, "ceid": ceid},
        timeout=httpx.Timeout(12.0, connect=5.0), follow_redirects=True,
        headers={"User-Agent": "Mozilla/5.0"},
    )
    resp.raise_for_status()
    root = ET.fromstring(resp.text)
    out: list[dict] = []
    for it in root.findall(".//item")[:max_results]:
        title = _clean(it.findtext("title", ""))
        if not title:
            continue
        src_el = it.find("{*}source")
        source = (src_el.text if src_el is not None else "").strip()
        desc = _clean(it.findtext("description", ""))
        if desc == title:  # Google News description is often just the title link, deduplicate
            desc = ""
        abstract = " ".join(x for x in (desc, f"Source: {source}." if source else "") if x)
        out.append({
            "arxiv_id": "",
            "title": title,
            "abstract": abstract or title,
            "authors": source,               # use the source as the "author"
            "published_at": (it.findtext("pubDate", "") or "")[:16],
            "url": it.findtext("link", ""),
            "pdf_url": "",                    # news items have no PDF
            "kind": "news",
        })
    return out


def search(query: str, max_results: int = 15) -> list[dict]:
    """Retrieve news, taking at most 15 seconds; returns an empty list on unreachable/timeout/parse failure, never blocking the pipeline."""
    return _bounded(lambda: _fetch(query, max_results), timeout=15.0, default=[])
