"""新闻检索（Google News RSS，免费、无需 Key、覆盖任意话题）。

让非学术查询（股票/财经/时事/政治等 arXiv 没有的主题）也能进入同一条
fetch→dedupe→triage→summarize→brief 管道。返回条目与 arxiv 连接器同构
（无 PDF：pdf_url 留空，管道会自动改用 abstract 作为总结素材）。
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


def _bounded(fn, timeout: float, default):
    """在守护线程里跑 fn，最多等 timeout 秒。超时/异常都返回 default，
    绝不阻塞调用方（守护线程随进程退出，不会挂起 worker）。DNS 解析卡死
    不受 httpx 超时管辖，这层兜底是必要的。"""
    box = [default]

    def run() -> None:
        try:
            box[0] = fn()
        except Exception:  # noqa: BLE001  网络/解析失败 → 保持 default
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


def search(query: str, max_results: int = 15) -> list[dict]:
    """检索新闻，最多耗时 15 秒；不可达/超时/解析失败均返回空列表，绝不阻塞管道。"""
    return _bounded(lambda: _fetch(query, max_results), timeout=15.0, default=[])
