"""Zotero push (one-way: AAOS → Zotero). Uses the Zotero Web API v3.

True two-way sync would require an OAuth authorization flow and conflict-merge logic, which
is beyond the scope of V1; here we implement "one-click push of a single item/batch", meeting
the core need of "sync archived papers into my reference library".
Reference: https://www.zotero.org/support/dev/web_api/v3/basics
"""
from __future__ import annotations

import httpx
from sqlalchemy.orm import Session

from ..core.settings_store import get_setting


def _base_url(db: Session) -> tuple[str, dict[str, str]] | None:
    api_key = str(get_setting(db, "zotero_api_key") or "")
    library_id = str(get_setting(db, "zotero_library_id") or "")
    library_type = str(get_setting(db, "zotero_library_type") or "user")  # user/group
    if not api_key or not library_id:
        return None
    url = f"https://api.zotero.org/{library_type}s/{library_id}/items"
    headers = {"Zotero-API-Key": api_key, "Zotero-API-Version": "3", "Content-Type": "application/json"}
    return url, headers


def paper_to_zotero_item(title: str, authors: str, abstract: str, url: str,
                         published_at: str, arxiv_id: str) -> dict:
    creators = []
    for name in authors.split(","):
        name = name.strip()
        if not name:
            continue
        parts = name.rsplit(" ", 1)
        if len(parts) == 2:
            creators.append({"creatorType": "author", "firstName": parts[0], "lastName": parts[1]})
        else:
            creators.append({"creatorType": "author", "name": name})
    return {
        "itemType": "preprint",
        "title": title,
        "creators": creators[:50],
        "abstractNote": abstract[:4000],
        "url": url,
        "date": published_at,
        "archiveID": f"arXiv:{arxiv_id}" if arxiv_id else "",
        "repository": "arXiv",
        "tags": [{"tag": "AAOS"}],
    }


def push_papers(db: Session, items: list[dict]) -> tuple[bool, str]:
    conf = _base_url(db)
    if conf is None:
        return False, "Zotero API key / library ID not configured (Settings -> Zotero sync)"
    url, headers = conf
    try:
        resp = httpx.post(url, headers=headers, json=items, timeout=30)
        if resp.status_code in (200, 207):
            body = resp.json()
            ok_count = len(body.get("success", {}))
            fail_count = len(body.get("failed", {}))
            return ok_count > 0, f"{ok_count} succeeded, {fail_count} failed"
        return False, f"Zotero API error {resp.status_code}: {resp.text[:200]}"
    except Exception as e:  # noqa: BLE001
        return False, f"Zotero push error: {e}"
