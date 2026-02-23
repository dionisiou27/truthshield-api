"""
arXiv API Integration
Access to preprints in Physics, Mathematics, Computer Science, Biology, etc.
FREE - No API key required
"""

import asyncio
import logging
from typing import Dict, List, Optional
import httpx
import re

logger = logging.getLogger(__name__)


class ArXivAPI:
    """arXiv API Integration for scientific preprint fact-checking"""

    def __init__(self):
        self.base_url = "https://export.arxiv.org/api/query"
        self.session = None

    async def __aenter__(self):
        self.session = httpx.AsyncClient(timeout=30.0)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.aclose()

    async def search_papers(self, query: str, max_results: int = 5) -> List[Dict]:
        """
        Search arXiv for relevant scientific papers

        Args:
            query: Search query
            max_results: Maximum number of results

        Returns:
            List of paper metadata
        """
        try:
            if not self.session:
                self.session = httpx.AsyncClient(timeout=30.0)

            logger.info(f"📄 Searching arXiv for: '{query[:50]}...'")

            # Build search query
            # arXiv uses a specific query syntax
            search_query = f"all:{query}"

            params = {
                "search_query": search_query,
                "start": 0,
                "max_results": max_results,
                "sortBy": "relevance",
                "sortOrder": "descending"
            }

            response = await self.session.get(self.base_url, params=params)
            response.raise_for_status()

            # Parse Atom XML response
            papers = self._parse_atom_response(response.text)

            logger.info(f"✅ arXiv: Retrieved {len(papers)} papers")
            return papers

        except httpx.HTTPStatusError as e:
            logger.error(f"❌ arXiv API HTTP error: {e.response.status_code}")
            return []
        except Exception as e:
            logger.error(f"❌ arXiv API error: {e}")
            return []

    def _parse_atom_response(self, xml_text: str) -> List[Dict]:
        """Parse arXiv Atom XML response"""
        papers = []

        try:
            # Simple regex-based XML parsing (avoiding heavy dependencies)
            entries = re.findall(r'<entry>(.*?)</entry>', xml_text, re.DOTALL)

            for entry in entries:
                paper = self._parse_entry(entry)
                if paper:
                    papers.append(paper)

        except Exception as e:
            logger.error(f"❌ Error parsing arXiv response: {e}")

        return papers

    def _parse_entry(self, entry_xml: str) -> Optional[Dict]:
        """Parse a single arXiv entry"""
        try:
            # Extract fields using regex
            def extract(pattern: str, text: str, default: str = "") -> str:
                match = re.search(pattern, text, re.DOTALL)
                return match.group(1).strip() if match else default

            # Get arXiv ID
            arxiv_id = extract(r'<id>http://arxiv.org/abs/([^<]+)</id>', entry_xml)
            if not arxiv_id:
                return None

            # Get title
            title = extract(r'<title>([^<]+)</title>', entry_xml)
            title = re.sub(r'\s+', ' ', title)  # Clean whitespace

            # Get summary/abstract
            summary = extract(r'<summary>([^<]+)</summary>', entry_xml)
            summary = re.sub(r'\s+', ' ', summary)[:300]  # Clean and limit

            # Get authors
            authors = re.findall(r'<author>\s*<name>([^<]+)</name>', entry_xml)
            author_str = ", ".join(authors[:3])
            if len(authors) > 3:
                author_str += " et al."

            # Get published date
            published = extract(r'<published>([^<]+)</published>', entry_xml)
            pub_date = published[:10] if published else ""  # Just the date part

            # Get categories
            categories = re.findall(r'<category[^>]*term="([^"]+)"', entry_xml)
            primary_category = categories[0] if categories else ""

            # Build URLs
            abs_url = f"https://arxiv.org/abs/{arxiv_id}"
            pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"

            return {
                "source": "arxiv",
                "arxiv_id": arxiv_id,
                "title": title,
                "url": abs_url,
                "pdf_url": pdf_url,
                "snippet": summary,
                "authors": author_str,
                "pub_date": pub_date,
                "category": primary_category,
                "credibility_score": 0.85,  # Preprints (not yet peer-reviewed)
            }

        except Exception as e:
            logger.error(f"❌ Error parsing arXiv entry: {e}")
            return None

    async def search_by_category(self, query: str, category: str, max_results: int = 5) -> List[Dict]:
        """
        Search arXiv within a specific category

        Categories:
        - cs.AI: Artificial Intelligence
        - cs.LG: Machine Learning
        - q-bio: Quantitative Biology
        - physics: Physics
        - math: Mathematics
        - stat: Statistics
        """
        try:
            if not self.session:
                self.session = httpx.AsyncClient(timeout=30.0)

            search_query = f"cat:{category} AND all:{query}"

            params = {
                "search_query": search_query,
                "start": 0,
                "max_results": max_results,
                "sortBy": "relevance",
                "sortOrder": "descending"
            }

            response = await self.session.get(self.base_url, params=params)
            response.raise_for_status()

            return self._parse_atom_response(response.text)

        except Exception as e:
            logger.error(f"❌ arXiv category search error: {e}")
            return []


# Global instance
arxiv_api = ArXivAPI()


async def search_arxiv(query: str, max_results: int = 5) -> List[Dict]:
    """Convenience function to search arXiv"""
    async with ArXivAPI() as api:
        return await api.search_papers(query, max_results)


# Test function
async def test_arxiv_api():
    """Test arXiv API"""
    test_queries = [
        "machine learning misinformation detection",
        "COVID-19 epidemiology",
        "climate change modeling",
        "neural network fact checking"
    ]

    async with ArXivAPI() as api:
        print("Testing arXiv API Integration")
        print("=" * 50)

        for query in test_queries:
            print(f"\n🔍 Query: '{query}'")
            print("-" * 40)

            results = await api.search_papers(query, max_results=3)

            if results:
                for i, paper in enumerate(results, 1):
                    print(f"\n  {i}. {paper['title'][:60]}...")
                    print(f"     👥 {paper['authors']}")
                    print(f"     📁 Category: {paper['category']}")
                    print(f"     📅 {paper['pub_date']}")
                    print(f"     🔗 {paper['url']}")
                    print(f"     ⭐ Credibility: {paper['credibility_score']}")
            else:
                print("  ❌ No results found")


if __name__ == "__main__":
    asyncio.run(test_arxiv_api())
