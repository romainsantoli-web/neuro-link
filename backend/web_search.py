"""
Web Search & Scraping tool for the Email AI Agent.

Provides DuckDuckGo search + lightweight page scraping so the AI
can research companies, hospitals, investors before drafting emails.
"""

from __future__ import annotations

import logging
import re
from typing import Any
from urllib.request import Request, urlopen
from urllib.error import URLError
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# ── DuckDuckGo Search ──────────────────────────────────────────────────────

def web_search(query: str, max_results: int = 8) -> list[dict[str, str]]:
    """Search DuckDuckGo and return a list of {title, url, snippet}."""
    try:
        from ddgs import DDGS
        ddgs = DDGS()
        results = list(ddgs.text(query, region="fr-fr", max_results=max_results))
        return [
            {
                "title": r.get("title", ""),
                "url": r.get("href", r.get("link", "")),
                "snippet": r.get("body", ""),
            }
            for r in results
        ]
    except Exception as e:
        logger.warning(f"DuckDuckGo search failed: {e}")
        return []


# ── Page Scraper ───────────────────────────────────────────────────────────

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
}

def scrape_page(url: str, max_chars: int = 5000) -> dict[str, str]:
    """Scrape a web page and extract clean text content.

    Returns: {url, title, text, meta_description}
    """
    result: dict[str, str] = {"url": url, "title": "", "text": "", "meta_description": ""}

    try:
        req = Request(url, headers=_HEADERS)
        with urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except (URLError, Exception) as e:
        logger.warning(f"Failed to scrape {url}: {e}")
        result["text"] = f"[Erreur: impossible d'accéder à {url}]"
        return result

    soup = BeautifulSoup(html, "html.parser")

    # Title
    title_tag = soup.find("title")
    result["title"] = title_tag.get_text(strip=True) if title_tag else ""

    # Meta description
    meta = soup.find("meta", attrs={"name": "description"})
    if meta and meta.get("content"):
        result["meta_description"] = meta["content"][:500]

    # Remove scripts, styles, nav, footer
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "noscript", "iframe"]):
        tag.decompose()

    # Get main content (prefer <main>, <article>, or body)
    main = soup.find("main") or soup.find("article") or soup.find("body")
    if main:
        text = main.get_text(separator="\n", strip=True)
    else:
        text = soup.get_text(separator="\n", strip=True)

    # Clean up
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    result["text"] = text[:max_chars]

    return result


# ── Research Pipeline ──────────────────────────────────────────────────────

def research_company(
    company_name: str,
    company_type: str = "",
    extra_keywords: str = "",
    max_search_results: int = 6,
    max_pages_to_scrape: int = 3,
) -> dict[str, Any]:
    """Full research pipeline: search + scrape top results.

    Args:
        company_name: Name of the company/hospital/org to research
        company_type: Type (chu, ehpad, neurologue, investisseur, partenaire_tech)
        extra_keywords: Additional search terms
        max_search_results: Number of search results to fetch
        max_pages_to_scrape: How many pages to scrape for detail

    Returns:
        Dict with search_results, scraped_pages, and a compiled research_summary
    """
    # Build smart search queries based on target type
    queries = _build_queries(company_name, company_type, extra_keywords)

    all_results: list[dict[str, str]] = []
    seen_urls: set[str] = set()

    for q in queries[:3]:  # Max 3 searches
        results = web_search(q, max_results=max_search_results)
        for r in results:
            if r["url"] not in seen_urls:
                seen_urls.add(r["url"])
                all_results.append(r)

    # Scrape top pages for detailed info
    scraped: list[dict[str, str]] = []
    for r in all_results[:max_pages_to_scrape]:
        if r["url"] and not r["url"].endswith(".pdf"):
            page = scrape_page(r["url"], max_chars=3000)
            scraped.append(page)

    # Compile summary for the AI
    summary_parts = [
        f"=== RECHERCHE WEB: {company_name} ({company_type}) ===\n",
        f"Nombre de résultats: {len(all_results)}\n",
        f"Pages analysées: {len(scraped)}\n\n",
    ]

    summary_parts.append("--- RÉSULTATS DE RECHERCHE ---\n")
    for i, r in enumerate(all_results[:8], 1):
        summary_parts.append(f"{i}. {r['title']}\n   {r['url']}\n   {r['snippet']}\n")

    summary_parts.append("\n--- CONTENU DES PAGES ---\n")
    for page in scraped:
        summary_parts.append(
            f"\n[{page['title']}] ({page['url']})\n"
            f"Description: {page['meta_description']}\n"
            f"Contenu:\n{page['text'][:2000]}\n"
            f"{'─' * 40}\n"
        )

    return {
        "company_name": company_name,
        "company_type": company_type,
        "search_results": all_results[:10],
        "scraped_pages": [
            {"url": p["url"], "title": p["title"], "meta_description": p["meta_description"], "text_length": len(p["text"])}
            for p in scraped
        ],
        "research_summary": "".join(summary_parts),
    }


def _build_queries(name: str, ctype: str, extra: str) -> list[str]:
    """Build smart search queries based on target type."""
    base = name.strip()
    queries = [f"{base} {extra}".strip()]

    type_keywords: dict[str, list[str]] = {
        "chu": ["service neurologie", "alzheimer recherche"],
        "ehpad": ["accompagnement Alzheimer", "innovations santé"],
        "neurologue": ["publications neurologie", "recherche EEG"],
        "investisseur": ["portfolio healthtech medtech", "investissements santé"],
        "partenaire_tech": ["solutions EEG BCI neurotechnologie", "partenariats R&D"],
    }

    if ctype in type_keywords:
        for kw in type_keywords[ctype]:
            queries.append(f"{base} {kw}")

    # Always add a generic info query
    queries.append(f"{base} site officiel contact")

    return queries
