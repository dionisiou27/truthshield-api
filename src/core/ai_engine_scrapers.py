# Scraping methods for ai_engine.py
import asyncio
import logging
from typing import List
from urllib.parse import quote
import httpx
from bs4 import BeautifulSoup
from .ai_engine_new import Source

logger = logging.getLogger(__name__)

async def _search_snopes(query: str) -> List[Source]:
    """Scrape Snopes.com for fact-checks"""
    try:
        url = f"https://www.snopes.com/?s={quote(query)}"
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            response = await client.get(url, headers={"User-Agent": "TruthShield/1.0"})
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                sources = []
                # Try multiple selectors for robustness
                candidates = soup.select('h2 a[href], h3 a[href], article a.card-title[href], article a[href]')
                for link in candidates[:8]:
                    url_link = link.get('href')
                    title_text = (link.get_text() or '').strip()
                    if not url_link or not title_text:
                        continue
                    if url_link.startswith('/'):
                        url_link = f"https://www.snopes.com{url_link}"
                    # Try to find rating near the link
                    rating_text = None
                    art = link.find_parent('article')
                    if art:
                        badge = art.select_one('[class*="media-rating"], [class*="rating"]')
                        if badge:
                            rating_text = badge.get_text(strip=True)
                    
                    sources.append(Source(
                        url=url_link,
                        title=title_text[:180],
                        snippet=(f"Snopes rating: {rating_text}" if rating_text else "Snopes article")[:240],
                        credibility_score=0.9,
                        date_published=None
                    ))
                return sources
    except Exception as e:
        logger.error(f"Snopes search failed: {e}")
    return []

async def _search_factcheck_org(query: str) -> List[Source]:
    """Scrape FactCheck.org"""
    try:
        url = f"https://www.factcheck.org/?s={quote(query)}"
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            response = await client.get(url, headers={"User-Agent": "TruthShield/1.0"})
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                sources = []
                for item in soup.select('h2.entry-title a[href], h3.entry-title a[href], h2 a[href], h3 a[href]')[:8]:
                    href = item.get('href')
                    title_text = (item.get_text() or '').strip()
                    if not href or not title_text:
                        continue
                    sources.append(Source(
                        url=href,
                        title=title_text[:180],
                        snippet="FactCheck.org article",
                        credibility_score=0.9,
                        date_published=None
                    ))
                return sources
    except Exception as e:
        logger.error(f"FactCheck.org search failed: {e}")
    return []

async def _search_politifact(query: str) -> List[Source]:
    """Scrape PolitiFact"""
    try:
        url = f"https://www.politifact.com/search/?q={quote(query)}"
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            response = await client.get(url, headers={"User-Agent": "TruthShield/1.0"})
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                sources = []
                candidates = soup.select('a.m-statement__quote, article a[href], .c-list li a[href], h3 a[href]')
                query_lower = query.lower()
                query_terms = query_lower.split()
                
                for link in candidates[:8]:
                    title_text = (link.get_text() or '').strip()
                    href = link.get('href')
                    if href and href.startswith('/'):
                        href = f"https://www.politifact.com{href}"
                    if not href or not title_text:
                        continue
                    
                    # Check relevance - require at least 2 query terms to match
                    content = title_text.lower()
                    matches = sum(1 for term in query_terms if term in content)
                    if matches < 2 and len(query_terms) > 1:
                        continue
                    # Only accept actual factcheck article pages
                    if '/factchecks/' not in href:
                        # Try to find enclosing link to a factcheck
                        parent_article = link.find_parent('article')
                        if parent_article:
                            fact_link = parent_article.find('a', href=True)
                            if fact_link:
                                fh = fact_link.get('href')
                                if fh and '/factchecks/' in fh:
                                    href = fh if fh.startswith('http') else f"https://www.politifact.com{fh}"
                                else:
                                    continue
                        else:
                            continue
                    # Prefer quote text inside statement if available
                    parent_stmt = link.find_parent(class_='m-statement') or link.find_parent('article')
                    if parent_stmt:
                        q = parent_stmt.select_one('.m-statement__quote')
                        if q:
                            tt = (q.get_text() or '').strip()
                            if tt:
                                title_text = tt
                    # Try to extract rating from enclosing statement
                    rating = None
                    parent = link.find_parent(class_='m-statement') or link.find_parent('article')
                    if parent:
                        r = parent.select_one('.m-statement__meter .c-image__original, img[alt*="Truth-O-Meter"], img[alt]')
                        if r and r.get('alt'):
                            rating = r.get('alt')
                    snippet = f"PolitiFact rating: {rating}" if rating else "PolitiFact article"
                    sources.append(Source(
                        url=href,
                        title=title_text[:180],
                        snippet=snippet[:240],
                        credibility_score=0.9,
                        date_published=None
                    ))
                return sources
    except Exception as e:
        logger.error(f"PolitiFact search failed: {e}")
    return []

async def _search_mimikama(query: str) -> List[Source]:
    """Scrape Mimikama (DE)"""
    try:
        url = f"https://www.mimikama.org/?s={quote(query)}"
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            response = await client.get(url, headers={"User-Agent": "TruthShield/1.0"})
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                sources = []
                for link in soup.select('h2.entry-title a[href], h3.entry-title a[href], h2 a[href], h3 a[href]')[:8]:
                    href = link.get('href')
                    title_text = (link.get_text() or '').strip()
                    if not href or not title_text:
                        continue
                    sources.append(Source(
                        url=href,
                        title=title_text[:180],
                        snippet="Mimikama Artikel",
                        credibility_score=0.9,
                        date_published=None
                    ))
                return sources
    except Exception as e:
        logger.error(f"Mimikama search failed: {e}")
    return []

async def _search_correctiv(query: str) -> List[Source]:
    """Scrape Correctiv (DE)"""
    try:
        url = f"https://correctiv.org/?s={quote(query)}"
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            response = await client.get(url, headers={"User-Agent": "TruthShield/1.0"})
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                sources = []
                for link in soup.select('h2 a[href], h3 a[href], .c-archive__item a[href]')[:8]:
                    href = link.get('href')
                    title_text = (link.get_text() or '').strip()
                    if not href or not title_text:
                        continue
                    sources.append(Source(
                        url=href,
                        title=title_text[:180],
                        snippet="CORRECTIV.Faktencheck",
                        credibility_score=0.9,
                        date_published=None
                    ))
                return sources
    except Exception as e:
        logger.error(f"Correctiv search failed: {e}")
    return []

async def _search_euvsdisinfo(query: str) -> List[Source]:
    """Scrape EUvsDISINFO for EU disinformation fact-checks."""
    try:
        url = f"https://euvsdisinfo.eu/?s={quote(query)}"
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            response = await client.get(url, headers={"User-Agent": "TruthShield/1.0"})
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                sources = []
                for link in soup.select('h2 a[href], h3 a[href], .entry-title a[href], .post-title a[href]')[:6]:
                    href = link.get('href')
                    title_text = (link.get_text() or '').strip()
                    if not href or not title_text:
                        continue
                    sources.append(Source(
                        url=href,
                        title=title_text[:180],
                        snippet="EUvsDISINFO fact-check",
                        credibility_score=0.9,
                        date_published=None
                    ))
                return sources
    except Exception as e:
        logger.error(f"EUvsDISINFO search failed: {e}")
    return []
