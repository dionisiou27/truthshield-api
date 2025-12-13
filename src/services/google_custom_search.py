"""
Google Custom Search API Integration
Enables domain-specific searches (e.g., site:nature.com)
"""

import asyncio
import logging
from typing import Dict, List, Optional
import httpx
from src.core.config import settings

logger = logging.getLogger(__name__)

class GoogleCustomSearchAPI:
    """Google Custom Search API for domain-specific searches"""

    def __init__(self):
        self.api_key = settings.google_api_key
        # Note: You need to create a Custom Search Engine at https://programmablesearchengine.google.com/
        # and get the CX (Search Engine ID)
        self.cx = getattr(settings, 'google_custom_search_cx', None)
        self.base_url = "https://www.googleapis.com/customsearch/v1"
        self.session = None

    async def __aenter__(self):
        self.session = httpx.AsyncClient(timeout=30.0)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.aclose()

    async def search(self, query: str, site_restrict: str = None, num_results: int = 5) -> List[Dict]:
        """
        Search using Google Custom Search API

        Args:
            query: Search query
            site_restrict: Domain restriction (e.g., "nature.com" or "nature.com OR science.org")
            num_results: Number of results to return (max 10)

        Returns:
            List of search results
        """
        if not self.api_key:
            logger.warning("Google API Key not configured")
            return []

        if not self.cx:
            logger.warning("Google Custom Search CX not configured - using site: operator")
            # Fallback to regular search with site: operator
            return await self._search_with_site_operator(query, site_restrict, num_results)

        try:
            params = {
                'key': self.api_key,
                'cx': self.cx,
                'q': query,
                'num': min(num_results, 10)
            }

            # Add site restriction if specified
            if site_restrict:
                params['siteSearch'] = site_restrict
                params['siteSearchFilter'] = 'i'  # Include only these sites

            logger.info(f"Searching Custom Search for: '{query[:50]}...' (sites: {site_restrict or 'all'})")

            if not self.session:
                self.session = httpx.AsyncClient(timeout=30.0)

            response = await self.session.get(self.base_url, params=params)
            response.raise_for_status()

            data = response.json()
            items = data.get('items', [])

            logger.info(f"Found {len(items)} results from Custom Search")

            # Format results
            formatted_results = []
            for item in items:
                formatted_item = self._format_result(item)
                if formatted_item:
                    formatted_results.append(formatted_item)

            return formatted_results

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403:
                logger.error("Google API Key invalid or quota exceeded")
            else:
                logger.error(f"Custom Search API error: {e.response.status_code}")
            return []

        except Exception as e:
            logger.error(f"Custom Search API error: {e}")
            return []

    async def _search_with_site_operator(self, query: str, site_restrict: str = None, num_results: int = 5) -> List[Dict]:
        """
        Fallback: Use site: operator in regular search
        Note: This uses the same API quota as Custom Search
        """
        if site_restrict:
            # Add site: operator to query
            search_query = f"{query} site:{site_restrict}"
        else:
            search_query = query

        try:
            params = {
                'key': self.api_key,
                'q': search_query,
                'num': min(num_results, 10)
            }

            logger.info(f"Using site: operator fallback: '{search_query[:50]}...'")

            # Note: This endpoint doesn't exist - you MUST use Custom Search with CX
            # This is just a placeholder to show the concept
            logger.warning("Site operator fallback requires Custom Search Engine setup")
            return []

        except Exception as e:
            logger.error(f"Site operator search failed: {e}")
            return []

    def _format_result(self, item: Dict) -> Optional[Dict]:
        """Format Custom Search result"""
        try:
            # Extract basic info
            title = item.get('title', '')
            link = item.get('link', '')
            snippet = item.get('snippet', '')

            if not title or not link:
                return None

            # Calculate credibility based on domain
            credibility = self._calculate_credibility(link)

            return {
                'source': 'google_custom_search',
                'title': title,
                'url': link,
                'snippet': snippet,
                'credibility_score': credibility,
                'display_link': item.get('displayLink', ''),
                'formatted_url': item.get('formattedUrl', ''),
            }

        except Exception as e:
            logger.error(f"Error formatting Custom Search result: {e}")
            return None

    def _calculate_credibility(self, url: str) -> float:
        """Calculate credibility score based on domain"""
        url_lower = url.lower()

        # High credibility domains
        high_cred = [
            'nature.com', 'science.org', 'who.int', 'cdc.gov', 'nih.gov',
            'europa.eu', 'europarl.europa.eu', 'ec.europa.eu',
            'factcheck.org', 'politifact.com', 'snopes.com', 'correctiv.org',
            '.gov', '.edu', 'pubmed', 'ncbi.nlm.nih.gov'
        ]

        for domain in high_cred:
            if domain in url_lower:
                return 0.9

        # Medium credibility
        medium_cred = [
            'bbc.com', 'reuters.com', 'ap.org', 'dw.com',
            'spiegel.de', 'zeit.de', 'tagesschau.de'
        ]

        for domain in medium_cred:
            if domain in url_lower:
                return 0.75

        # Default
        return 0.6


# Convenience functions
async def search_custom(query: str, site_restrict: str = None, num_results: int = 5) -> List[Dict]:
    """Convenience function for custom search"""
    async with GoogleCustomSearchAPI() as api:
        return await api.search(query, site_restrict, num_results)


async def search_science_sources(query: str) -> List[Dict]:
    """Search scientific sources"""
    return await search_custom(
        query,
        site_restrict="nature.com OR science.org OR who.int OR cdc.gov OR nih.gov",
        num_results=5
    )


async def search_policy_sources(query: str) -> List[Dict]:
    """Search policy fact-checking sources"""
    return await search_custom(
        query,
        site_restrict="factcheck.org OR politifact.com OR snopes.com OR correctiv.org",
        num_results=5
    )


async def search_eu_sources(query: str) -> List[Dict]:
    """Search EU official sources"""
    return await search_custom(
        query,
        site_restrict="europa.eu OR europarl.europa.eu OR ec.europa.eu",
        num_results=5
    )


# Test function
async def test_custom_search():
    """Test Google Custom Search API"""
    print("TESTING GOOGLE CUSTOM SEARCH API")
    print("="*80)

    async with GoogleCustomSearchAPI() as api:
        print(f"API Key: {'YES' if api.api_key else 'NO'}")
        print(f"Custom Search CX: {'YES' if api.cx else 'NO (will use fallback)'}")

        if not api.api_key:
            print("\nERROR: No Google API Key found")
            print("Add to .env: GOOGLE_API_KEY=...")
            return

        if not api.cx:
            print("\nWARNING: No Custom Search Engine ID found")
            print("Create one at: https://programmablesearchengine.google.com/")
            print("Add to .env: GOOGLE_CUSTOM_SEARCH_CX=...")
            return

        # Test searches
        print("\n\n1. Testing Science Sources:")
        results = await search_science_sources("COVID vaccines")
        print(f"   Found {len(results)} results")
        for i, result in enumerate(results[:2], 1):
            print(f"   [{i}] {result['title'][:60]}")
            print(f"       {result['display_link']}")

        print("\n\n2. Testing Policy Sources:")
        results = await search_policy_sources("election fraud")
        print(f"   Found {len(results)} results")
        for i, result in enumerate(results[:2], 1):
            print(f"   [{i}] {result['title'][:60]}")
            print(f"       {result['display_link']}")

        print("\n\n3. Testing EU Sources:")
        results = await search_eu_sources("von der Leyen election")
        print(f"   Found {len(results)} results")
        for i, result in enumerate(results[:2], 1):
            print(f"   [{i}] {result['title'][:60]}")
            print(f"       {result['display_link']}")


if __name__ == "__main__":
    asyncio.run(test_custom_search())
