"""新闻检索（Google News RSS，免费、无需 Key、覆盖任意话题）。

让非学术查询（股票/财经/时事/政治等 arXiv 没有的主题）也能进入同一条
fetch→dedupe→triage→summarize→brief 管道。返回条目与 arxiv 连接器同构
（无 PDF：pdf_url 留空，管道会自动改用 abstract 作为总结素材）。
"""
from __future__ import annotations

import html
import re
import xml.etree.ElementTree as ET

import httpx

RSS = "https://news.google.com/rss/search"
_TAG = re.compile(r"<[^>]+>")
_CJK = re.compile(r"[一-鿿぀-ヿ가-힯]")

# 更适合走新闻源（而非 arXiv 学术库）的信号词
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
    """CJK 查询走中文区新闻，其余走英文区。"""
    if _CJK.search(query):
        return "zh-CN", "CN", "CN:zh-Hans"
    return "en-US", "US", "US:en"


def is_news_query(query: str) -> bool:
    """判断该查询更适合新闻源。命中信号词或主体为 CJK 即视为新闻类。"""
    q = query.lower()
    if any(sig in q for sig in _NEWS_SIGNALS):
        return True
    letters = [c for c in query if c.isalpha()]
    if letters and sum(1 for c in letters if _CJK.match(c)) / len(letters) > 0.3:
        return True
    return False


def search(query: str, max_results: int = 15) -> list[dict]:
    hl, gl, ceid = _locale(query)
    resp = httpx.get(
        RSS, params={"q": query, "hl": hl, "gl": gl, "ceid": ceid},
        timeout=30, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"},
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
        if desc == title:  # Google News 的 description 常只是标题链接，去重复
            desc = ""
        abstract = " ".join(x for x in (desc, f"Source: {source}." if source else "") if x)
        out.append({
            "arxiv_id": "",
            "title": title,
            "abstract": abstract or title,
            "authors": source,               # 用来源当"作者"
            "published_at": (it.findtext("pubDate", "") or "")[:16],
            "url": it.findtext("link", ""),
            "pdf_url": "",                    # 新闻无 PDF
            "kind": "news",
        })
    return out
