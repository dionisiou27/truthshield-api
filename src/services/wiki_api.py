"""
MediaWiki (Wikipedia + Wikidata) integration.
Uses public api.php endpoints to fetch authoritative encyclopedia context.
"""

import logging
from typing import Dict, List

import httpx

HEADERS = {
    "User-Agent": "TruthShield/1.0 (contact: support@truthshield.eu)",
}

logger = logging.getLogger(__name__)

WIKIPEDIA_BASE = "https://{lang}.wikipedia.org/w/api.php"
WIKIDATA_BASE = "https://www.wikidata.org/w/api.php"
META_WIKI_BASE = "https://meta.wikimedia.org/w/api.php"


async def fetch_wikipedia_pages(query: str, language: str = "de", limit: int = 5) -> List[Dict]:
    """
    Search the language-specific Wikipedia via action=query generator search.
    Returns the strongest summary paragraphs + canonical page URLs.
    """
    if not query:
        return []

    base_url = WIKIPEDIA_BASE.format(lang=language if language in {"de", "en", "fr", "es"} else "en")
    params = {
        "action": "query",
        "format": "json",
        "prop": "extracts|info",
        "exintro": 1,
        "explaintext": 1,
        "inprop": "url",
        "generator": "search",
        "gsrsearch": query,
        "gsrlimit": limit,
        "utf8": 1,
        "origin": "*",
    }

    try:
        async with httpx.AsyncClient(timeout=20.0, headers=HEADERS) as client:
            response = await client.get(base_url, params=params)
            response.raise_for_status()
            data = response.json()
            pages = data.get("query", {}).get("pages", {})
            results = []
            for page in pages.values():
                title = page.get("title")
                extract = page.get("extract", "")
                full_url = page.get("fullurl") or _build_wikipedia_url(language, title)
                if not title or not full_url:
                    continue
                results.append(
                    {
                        "project": "wikipedia",
                        "language": language,
                        "title": title,
                        "url": full_url,
                        "snippet": extract[:400] + ("…" if len(extract) > 400 else ""),
                        "credibility": 0.82,
                    }
                )
            logger.info(f"📚 Wikipedia returned {len(results)} results for '{query[:60]}…'")
            return results
    except httpx.HTTPStatusError as exc:
        logger.error(f"❌ Wikipedia API error: {exc.response.status_code}")
    except Exception as exc:
        logger.error(f"❌ Wikipedia fetch failed: {exc}")
    return []


async def fetch_wikidata_entities(query: str, language: str = "de", limit: int = 5) -> List[Dict]:
    """
    Query Wikidata entities for structured EU/government info.
    """
    if not query:
        return []

    params = {
        "action": "wbsearchentities",
        "format": "json",
        "language": language,
        "search": query,
        "limit": limit,
    }

    try:
        async with httpx.AsyncClient(timeout=20.0, headers=HEADERS) as client:
            response = await client.get(WIKIDATA_BASE, params=params)
            response.raise_for_status()
            data = response.json()
            search_results = data.get("search", [])
            results = []
            for entity in search_results:
                title = entity.get("label")
                description = entity.get("description", "")
                entity_id = entity.get("id")
                if not title or not entity_id:
                    continue
                results.append(
                    {
                        "project": "wikidata",
                        "language": language,
                        "title": title,
                        "url": f"https://www.wikidata.org/wiki/{entity_id}",
                        "snippet": description or "Wikidata structured entity.",
                        "credibility": 0.88,
                    }
                )
            logger.info(f"📘 Wikidata returned {len(results)} entities for '{query[:60]}…'")
            return results
    except httpx.HTTPStatusError as exc:
        logger.error(f"❌ Wikidata API error: {exc.response.status_code}")
    except Exception as exc:
        logger.error(f"❌ Wikidata fetch failed: {exc}")
    return []


async def fetch_meta_wiki_pages(query: str, limit: int = 5) -> List[Dict]:
    """
    Query Meta-Wiki (global Wikimedia policy/governance).
    """
    params = {
        "action": "query",
        "format": "json",
        "prop": "extracts|info",
        "exintro": 1,
        "explaintext": 1,
        "inprop": "url",
        "generator": "search",
        "gsrsearch": query,
        "gsrlimit": limit,
        "utf8": 1,
        "origin": "*",
    }

    try:
        async with httpx.AsyncClient(timeout=20.0, headers=HEADERS) as client:
            response = await client.get(META_WIKI_BASE, params=params)
            response.raise_for_status()
            data = response.json()
            pages = data.get("query", {}).get("pages", {})
            results = []
            for page in pages.values():
                title = page.get("title")
                extract = page.get("extract", "")
                full_url = page.get("fullurl")
                if not title or not full_url:
                    continue
                results.append(
                    {
                        "project": "meta",
                        "language": "en",
                        "title": title,
                        "url": full_url,
                        "snippet": extract[:400] + ("…" if len(extract) > 400 else ""),
                        "credibility": 0.8,
                    }
                )
            logger.info(f"📙 Meta-Wiki returned {len(results)} results for '{query[:60]}…'")
            return results
    except httpx.HTTPStatusError as exc:
        logger.error(f"❌ Meta-Wiki API error: {exc.response.status_code}")
    except Exception as exc:
        logger.error(f"❌ Meta-Wiki fetch failed: {exc}")
    return []


def _build_wikipedia_url(language: str, title: str) -> str:
    lang = language if language in {"de", "en", "fr", "es"} else "en"
    safe_title = title.replace(" ", "_")
    return f"https://{lang}.wikipedia.org/wiki/{safe_title}"


async def search_mediawiki_sources(query: str, language: str = "de") -> List[Dict]:
    """
    Fetch combined Wikipedia + Wikidata context for a claim.
    """
    wikipedia_results, wikidata_results, meta_results = await _gather_mediawiki(query, language)
    # Prioritize language-specific Wikipedia entries, then structured Wikidata
    combined: List[Dict] = []
    combined.extend(wikipedia_results[:3])
    combined.extend(wikidata_results[:2])
    combined.extend(meta_results[:1])
    return combined


async def _gather_mediawiki(query: str, language: str):
    wikipedia_task = fetch_wikipedia_pages(query, language)
    wikidata_task = fetch_wikidata_entities(query, language)
    meta_task = fetch_meta_wiki_pages(query)
    return await wikipedia_task, await wikidata_task, await meta_task

