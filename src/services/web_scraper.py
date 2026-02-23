"""
Web Scraping Service for Dynamic Source Retrieval
Scrapes fact-checking and authoritative websites
"""

import asyncio
import logging
from typing import Dict, List
from urllib.parse import quote
import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "TruthShield/1.0 (Fact-Checking Bot; +https://truthshield.eu)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


class WebScraper:
    """Web scraping service for dynamic source retrieval"""

    def __init__(self):
        self.session = None
        self.timeout = 15.0

    async def __aenter__(self):
        self.session = httpx.AsyncClient(timeout=self.timeout, headers=HEADERS, follow_redirects=True)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.aclose()

    async def scrape_factcheck_org(self, query: str, limit: int = 3) -> List[Dict]:
        """Scrape FactCheck.org search results"""
        try:
            search_url = f"https://www.factcheck.org/?s={quote(query)}"
            logger.info(f"Scraping FactCheck.org for: '{query[:50]}...'")

            if not self.session:
                self.session = httpx.AsyncClient(timeout=self.timeout, headers=HEADERS, follow_redirects=True)

            response = await self.session.get(search_url)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            articles = []

            # Find article entries
            for article in soup.find_all('article', limit=limit):
                try:
                    # Extract title and link
                    title_elem = article.find('h3') or article.find('h2')
                    if not title_elem:
                        continue

                    link_elem = title_elem.find('a')
                    if not link_elem:
                        continue

                    title = title_elem.get_text(strip=True)
                    url = link_elem.get('href', '')

                    # Extract snippet
                    snippet_elem = article.find('p')
                    snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""

                    if title and url:
                        articles.append({
                            'source': 'factcheck_org',
                            'title': title,
                            'url': url,
                            'snippet': snippet[:300],
                            'credibility_score': 0.9
                        })

                except Exception as e:
                    logger.debug(f"Error parsing FactCheck.org article: {e}")
                    continue

            logger.info(f"Found {len(articles)} articles from FactCheck.org")
            return articles

        except Exception as e:
            logger.error(f"Error scraping FactCheck.org: {e}")
            return []

    async def scrape_snopes(self, query: str, limit: int = 3) -> List[Dict]:
        """Scrape Snopes search results"""
        try:
            search_url = f"https://www.snopes.com/?s={quote(query)}"
            logger.info(f"Scraping Snopes for: '{query[:50]}...'")

            if not self.session:
                self.session = httpx.AsyncClient(timeout=self.timeout, headers=HEADERS, follow_redirects=True)

            response = await self.session.get(search_url)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            articles = []

            # Find article entries (Snopes uses different structure)
            for article in soup.find_all('article', limit=limit):
                try:
                    # Find title
                    title_elem = article.find('h3') or article.find('h2') or article.find('a', class_='title')
                    if not title_elem:
                        continue

                    # Extract link
                    link_elem = title_elem.find('a') if title_elem.name != 'a' else title_elem
                    if not link_elem:
                        continue

                    title = title_elem.get_text(strip=True)
                    url = link_elem.get('href', '')

                    # Make URL absolute
                    if url.startswith('/'):
                        url = f"https://www.snopes.com{url}"

                    # Extract snippet
                    snippet_elem = article.find('p')
                    snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""

                    if title and url:
                        articles.append({
                            'source': 'snopes',
                            'title': title,
                            'url': url,
                            'snippet': snippet[:300],
                            'credibility_score': 0.85
                        })

                except Exception as e:
                    logger.debug(f"Error parsing Snopes article: {e}")
                    continue

            logger.info(f"Found {len(articles)} articles from Snopes")
            return articles

        except Exception as e:
            logger.error(f"Error scraping Snopes: {e}")
            return []

    async def scrape_correctiv(self, query: str, limit: int = 3) -> List[Dict]:
        """Scrape Correctiv (German fact-checker) search results"""
        try:
            search_url = f"https://correctiv.org/faktencheck/?s={quote(query)}"
            logger.info(f"Scraping Correctiv for: '{query[:50]}...'")

            if not self.session:
                self.session = httpx.AsyncClient(timeout=self.timeout, headers=HEADERS, follow_redirects=True)

            response = await self.session.get(search_url)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            articles = []

            # Find article entries
            for article in soup.find_all('article', limit=limit):
                try:
                    # Extract title and link
                    title_elem = article.find('h2') or article.find('h3')
                    if not title_elem:
                        continue

                    link_elem = title_elem.find('a')
                    if not link_elem:
                        continue

                    title = title_elem.get_text(strip=True)
                    url = link_elem.get('href', '')

                    # Make URL absolute
                    if url.startswith('/'):
                        url = f"https://correctiv.org{url}"

                    # Extract snippet
                    snippet_elem = article.find('p')
                    snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""

                    if title and url:
                        articles.append({
                            'source': 'correctiv',
                            'title': title,
                            'url': url,
                            'snippet': snippet[:300],
                            'credibility_score': 0.9
                        })

                except Exception as e:
                    logger.debug(f"Error parsing Correctiv article: {e}")
                    continue

            logger.info(f"Found {len(articles)} articles from Correctiv")
            return articles

        except Exception as e:
            logger.error(f"Error scraping Correctiv: {e}")
            return []

    async def scrape_all_factcheckers(self, query: str, limit_per_site: int = 2) -> List[Dict]:
        """Scrape multiple fact-checking sites in parallel"""
        tasks = [
            self.scrape_factcheck_org(query, limit_per_site),
            self.scrape_snopes(query, limit_per_site),
            self.scrape_correctiv(query, limit_per_site),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_articles = []
        for result in results:
            if isinstance(result, list):
                all_articles.extend(result)
            elif isinstance(result, Exception):
                logger.error(f"Scraping error: {result}")

        logger.info(f"Total articles scraped: {len(all_articles)}")
        return all_articles


# Convenience functions
async def scrape_factcheckers(query: str, limit_per_site: int = 2) -> List[Dict]:
    """Convenience function to scrape fact-checkers"""
    async with WebScraper() as scraper:
        return await scraper.scrape_all_factcheckers(query, limit_per_site)


async def scrape_factcheck_org_search(query: str, limit: int = 3) -> List[Dict]:
    """Convenience function for FactCheck.org only"""
    async with WebScraper() as scraper:
        return await scraper.scrape_factcheck_org(query, limit)


async def scrape_snopes_search(query: str, limit: int = 3) -> List[Dict]:
    """Convenience function for Snopes only"""
    async with WebScraper() as scraper:
        return await scraper.scrape_snopes(query, limit)


async def scrape_correctiv_search(query: str, limit: int = 3) -> List[Dict]:
    """Convenience function for Correctiv only"""
    async with WebScraper() as scraper:
        return await scraper.scrape_correctiv(query, limit)


# Test function
async def test_web_scraper():
    """Test web scraping functionality"""
    print("=" * 80)
    print("WEB SCRAPER TEST")
    print("=" * 80)

    test_queries = [
        ("COVID vaccines cause autism", "en"),
        ("5G causes coronavirus", "en"),
        ("Impfungen verursachen Autismus", "de"),
    ]

    for query, lang in test_queries:
        print(f"\n\nQuery: '{query}' (lang={lang})")
        print("-" * 80)

        if lang == "de":
            # Test Correctiv for German
            print("\nScraping Correctiv:")
            results = await scrape_correctiv_search(query, limit=2)
            print(f"  Found {len(results)} results")
            for i, result in enumerate(results, 1):
                print(f"  [{i}] {result['title'][:60]}")
                print(f"      {result['url']}")
        else:
            # Test FactCheck.org and Snopes for English
            print("\n1. Scraping FactCheck.org:")
            results = await scrape_factcheck_org_search(query, limit=2)
            print(f"   Found {len(results)} results")
            for i, result in enumerate(results, 1):
                print(f"   [{i}] {result['title'][:60]}")
                print(f"       {result['url']}")

            print("\n2. Scraping Snopes:")
            results = await scrape_snopes_search(query, limit=2)
            print(f"   Found {len(results)} results")
            for i, result in enumerate(results, 1):
                print(f"   [{i}] {result['title'][:60]}")
                print(f"       {result['url']}")

        print("\n3. Scraping ALL fact-checkers:")
        results = await scrape_factcheckers(query, limit_per_site=1)
        print(f"   Total found: {len(results)} results")


if __name__ == "__main__":
    asyncio.run(test_web_scraper())
