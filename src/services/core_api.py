"""
CORE.ac.uk API Integration
Access to 200+ million scientific articles from repositories worldwide
FREE with API key (get one at https://core.ac.uk/services/api)
"""

import asyncio
import logging
from typing import Dict, List, Optional
import httpx
from src.core.config import settings

logger = logging.getLogger(__name__)

class CoreAPI:
    """CORE.ac.uk API Integration for open access scientific papers"""

    def __init__(self):
        self.base_url = "https://api.core.ac.uk/v3"
        self.api_key = getattr(settings, 'core_api_key', None)
        self.session = None

    async def __aenter__(self):
        self.session = httpx.AsyncClient(timeout=30.0)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.aclose()

    async def search_papers(self, query: str, max_results: int = 5) -> List[Dict]:
        """
        Search CORE for open access scientific papers

        Args:
            query: Search query
            max_results: Maximum number of results

        Returns:
            List of paper metadata
        """
        if not self.api_key:
            logger.warning("🔑 CORE API Key not configured - skipping CORE search")
            return []

        try:
            if not self.session:
                self.session = httpx.AsyncClient(timeout=30.0)

            logger.info(f"📖 Searching CORE.ac.uk for: '{query[:50]}...'")

            headers = {
                "Authorization": f"Bearer {self.api_key}"
            }

            params = {
                "q": query,
                "limit": max_results,
                "scroll": "false"
            }

            response = await self.session.get(
                f"{self.base_url}/search/works",
                headers=headers,
                params=params
            )
            response.raise_for_status()
            data = response.json()

            results = data.get("results", [])
            papers = []

            for result in results:
                paper = self._format_paper(result)
                if paper:
                    papers.append(paper)

            logger.info(f"✅ CORE: Retrieved {len(papers)} papers")
            return papers

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                logger.error("❌ CORE API Key invalid")
            elif e.response.status_code == 429:
                logger.error("❌ CORE API rate limit exceeded")
            else:
                logger.error(f"❌ CORE API HTTP error: {e.response.status_code}")
            return []
        except Exception as e:
            logger.error(f"❌ CORE API error: {e}")
            return []

    def _format_paper(self, paper_data: Dict) -> Optional[Dict]:
        """Format CORE paper data for TruthShield"""
        try:
            title = paper_data.get("title", "")
            if not title:
                return None

            # Get authors
            authors = paper_data.get("authors", [])
            author_names = []
            for author in authors[:3]:
                if isinstance(author, dict):
                    author_names.append(author.get("name", ""))
                elif isinstance(author, str):
                    author_names.append(author)
            author_str = ", ".join(author_names)
            if len(authors) > 3:
                author_str += " et al."

            # Get abstract/description
            abstract = paper_data.get("abstract", "") or paper_data.get("description", "")
            snippet = abstract[:300] if abstract else "No abstract available."

            # Get publication info
            year = paper_data.get("yearPublished", "")
            publisher = paper_data.get("publisher", "")
            journal = paper_data.get("journals", [{}])
            journal_name = journal[0].get("title", "") if journal else ""

            # Get URLs
            doi = paper_data.get("doi", "")
            download_url = paper_data.get("downloadUrl", "")

            if doi:
                url = f"https://doi.org/{doi}"
            elif download_url:
                url = download_url
            else:
                core_id = paper_data.get("id", "")
                url = f"https://core.ac.uk/works/{core_id}" if core_id else ""

            if not url:
                return None

            return {
                "source": "core",
                "title": title,
                "url": url,
                "snippet": snippet,
                "authors": author_str,
                "journal": journal_name or publisher,
                "pub_date": str(year) if year else "",
                "doi": doi,
                "credibility_score": 0.88,  # Open access, often peer-reviewed
            }

        except Exception as e:
            logger.error(f"❌ Error formatting CORE paper: {e}")
            return None


# Global instance
core_api = CoreAPI()

async def search_core(query: str, max_results: int = 5) -> List[Dict]:
    """Convenience function to search CORE"""
    async with CoreAPI() as api:
        return await api.search_papers(query, max_results)


# Test function
async def test_core_api():
    """Test CORE API"""
    test_queries = [
        "vaccine effectiveness study",
        "climate change impact",
        "misinformation social media"
    ]

    async with CoreAPI() as api:
        print("Testing CORE.ac.uk API Integration")
        print(f"API Key configured: {'YES' if api.api_key else 'NO'}")
        print("=" * 50)

        if not api.api_key:
            print("❌ No CORE API Key - get one free at https://core.ac.uk/services/api")
            return

        for query in test_queries:
            print(f"\n🔍 Query: '{query}'")
            print("-" * 40)

            results = await api.search_papers(query, max_results=3)

            if results:
                for i, paper in enumerate(results, 1):
                    print(f"\n  {i}. {paper['title'][:60]}...")
                    print(f"     👥 {paper['authors']}")
                    print(f"     📰 {paper['journal']}")
                    print(f"     🔗 {paper['url']}")
            else:
                print("  ❌ No results found")


if __name__ == "__main__":
    asyncio.run(test_core_api())
