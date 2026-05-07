"""arXiv search and fetch tools for AgentForPaper.

Wraps the public arXiv Atom API (no key required, limit: 3 req/s).
"""

from __future__ import annotations

import asyncio
import time
import xml.etree.ElementTree as ET
from typing import Any

import httpx
from langchain_core.tools import tool

_ATOM_NS = "http://www.w3.org/2005/Atom"
_BASE = "https://export.arxiv.org/api/query"
_RATE_DELAY = 0.4

_last_request: float = 0.0
_lock: asyncio.Lock | None = None


def _get_lock() -> asyncio.Lock:
    global _lock
    if _lock is None:
        _lock = asyncio.Lock()
    return _lock


async def _fetch_atom(params: dict) -> list[dict[str, Any]]:
    global _last_request
    async with _get_lock():
        gap = _RATE_DELAY - (time.monotonic() - _last_request)
        if gap > 0:
            await asyncio.sleep(gap)
        _last_request = time.monotonic()
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(_BASE, params=params)
            resp.raise_for_status()

    root = ET.fromstring(resp.text)
    results = []
    for entry in root.findall(f"{{{_ATOM_NS}}}entry"):
        raw_id = entry.findtext(f"{{{_ATOM_NS}}}id") or ""
        arxiv_id = raw_id.rstrip("/").split("/")[-1].split("v")[0]
        title = (entry.findtext(f"{{{_ATOM_NS}}}title") or "").strip()
        summary = (entry.findtext(f"{{{_ATOM_NS}}}summary") or "").strip()
        published = entry.findtext(f"{{{_ATOM_NS}}}published") or ""
        year = int(published[:4]) if len(published) >= 4 else None
        authors = [
            a.findtext(f"{{{_ATOM_NS}}}name") or ""
            for a in entry.findall(f"{{{_ATOM_NS}}}author")
        ]
        results.append({
            "arxiv_id": arxiv_id,
            "title": title,
            "year": year,
            "authors": authors[:5],
            "abstract": summary[:400],
            "url": f"https://arxiv.org/abs/{arxiv_id}",
        })
    return results


@tool
async def arxiv_search(query: str, max_results: int = 8) -> str:
    """Search arXiv for papers matching a query.

    Args:
        query: Search terms, e.g. 'video diffusion model 2024'.
        max_results: Number of results to return (default 8, max 20).

    Returns:
        Formatted list of papers with title, authors, year, abstract and link.
    """
    max_results = min(max_results, 20)
    try:
        papers = await _fetch_atom({
            "search_query": f"all:{query}",
            "max_results": max_results,
            "sortBy": "relevance",
            "sortOrder": "descending",
        })
    except Exception as exc:
        return f"arXiv search failed: {exc}"

    if not papers:
        return f"No papers found for query: {query}"

    lines = [f"arXiv search results for: '{query}'\n"]
    for i, p in enumerate(papers, 1):
        lines.append(
            f"{i}. **{p['title']}**\n"
            f"   Authors: {', '.join(p['authors'])}\n"
            f"   Year: {p['year']}  |  arXiv: {p['arxiv_id']}\n"
            f"   Link: {p['url']}\n"
            f"   Abstract: {p['abstract'][:200]}...\n"
        )
    return "\n".join(lines)


@tool
async def arxiv_fetch(arxiv_id: str) -> str:
    """Fetch full metadata for a specific arXiv paper by ID.

    Args:
        arxiv_id: arXiv paper ID, e.g. '2412.03603' or 'arxiv:2412.03603'.

    Returns:
        Paper metadata including full abstract.
    """
    clean_id = arxiv_id.lower().removeprefix("arxiv:").strip()
    try:
        papers = await _fetch_atom({"id_list": clean_id, "max_results": 1})
    except Exception as exc:
        return f"arXiv fetch failed for {arxiv_id}: {exc}"

    if not papers:
        return f"Paper not found: {arxiv_id}"

    p = papers[0]
    return (
        f"**{p['title']}**\n"
        f"Authors: {', '.join(p['authors'])}\n"
        f"Year: {p['year']}\n"
        f"arXiv ID: {p['arxiv_id']}\n"
        f"Link: {p['url']}\n\n"
        f"Abstract:\n{p['abstract']}"
    )
