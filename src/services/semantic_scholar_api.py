"""
Semantic Scholar API Integration
Access to 200+ million papers with citation data and influence metrics
FREE - No API key required (optional key for higher rate limits)
"""

import asyncio
import logging
from typing import Dict, List, Optional
import httpx

logger = logging.getLogger(__name__)


class SemanticScholarAPI:
    """Semantic Scholar API for scientific paper search with citation context"""

    def __init__(self):
        self.base_url = "https://api.semanticscholar.org/graph/v1"
        self.session = None

    async def __aenter__(self):
        self.session = httpx.AsyncClient(timeout=30.0)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.aclose()

    async def search_papers(self, query: str, max_results: int = 5) -> List[Dict]:
        """
        Search Semantic Scholar for relevant papers with citation metrics

        Args:
            query: Search query
            max_results: Maximum number of results

        Returns:
            List of paper metadata with citation info
        """
        try:
            if not self.session:
                self.session = httpx.AsyncClient(timeout=30.0)

            logger.info(f"🎓 Searching Semantic Scholar for: '{query[:50]}...'")

            # Fields to retrieve
            fields = "paperId,title,abstract,authors,year,citationCount,influentialCitationCount,url,venue,publicationDate"

            params = {
                "query": query,
                "limit": max_results,
                "fields": fields
            }

            response = await self.session.get(
                f"{self.base_url}/paper/search",
                params=params
            )
            response.raise_for_status()
            data = response.json()

            papers_data = data.get("data", [])
            papers = []

            for paper_data in papers_data:
                paper = self._format_paper(paper_data)
                if paper:
                    papers.append(paper)

            logger.info(f"✅ Semantic Scholar: Retrieved {len(papers)} papers")
            return papers

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                logger.error("❌ Semantic Scholar rate limit exceeded - wait a moment")
            else:
                logger.error(f"❌ Semantic Scholar API HTTP error: {e.response.status_code}")
            return []
        except Exception as e:
            logger.error(f"❌ Semantic Scholar API error: {e}")
            return []

    def _format_paper(self, paper_data: Dict) -> Optional[Dict]:
        """Format Semantic Scholar paper data for TruthShield"""
        try:
            title = paper_data.get("title", "")
            if not title:
                return None

            paper_id = paper_data.get("paperId", "")

            # Get authors
            authors = paper_data.get("authors", [])
            author_names = [a.get("name", "") for a in authors[:3]]
            author_str = ", ".join(author_names)
            if len(authors) > 3:
                author_str += " et al."

            # Get abstract
            abstract = paper_data.get("abstract", "")
            snippet = abstract[:300] if abstract else "No abstract available."

            # Get citation metrics
            citation_count = paper_data.get("citationCount", 0)
            influential_citations = paper_data.get("influentialCitationCount", 0)

            # Get publication info
            year = paper_data.get("year", "")
            venue = paper_data.get("venue", "")
            pub_date = paper_data.get("publicationDate", "")

            # Build URL
            url = paper_data.get("url", "")
            if not url and paper_id:
                url = f"https://www.semanticscholar.org/paper/{paper_id}"

            if not url:
                return None

            # Calculate credibility based on citations
            # More citations = higher credibility (capped at 0.95)
            base_credibility = 0.85
            citation_boost = min(citation_count / 1000, 0.1)  # Max +0.1 for highly cited
            credibility = min(base_credibility + citation_boost, 0.95)

            return {
                "source": "semantic_scholar",
                "paper_id": paper_id,
                "title": title,
                "url": url,
                "snippet": snippet,
                "authors": author_str,
                "venue": venue,
                "pub_date": pub_date or str(year),
                "citation_count": citation_count,
                "influential_citations": influential_citations,
                "credibility_score": credibility,
            }

        except Exception as e:
            logger.error(f"❌ Error formatting Semantic Scholar paper: {e}")
            return None

    async def get_paper_details(self, paper_id: str) -> Optional[Dict]:
        """Get detailed information about a specific paper"""
        try:
            if not self.session:
                self.session = httpx.AsyncClient(timeout=30.0)

            fields = "paperId,title,abstract,authors,year,citationCount,references,citations,venue,url"

            response = await self.session.get(
                f"{self.base_url}/paper/{paper_id}",
                params={"fields": fields}
            )
            response.raise_for_status()

            return self._format_paper(response.json())

        except Exception as e:
            logger.error(f"❌ Error fetching paper details: {e}")
            return None

    async def search_by_field(self, query: str, field: str, max_results: int = 5) -> List[Dict]:
        """
        Search papers in a specific field of study

        Fields of study examples:
        - Computer Science
        - Medicine
        - Biology
        - Physics
        - Environmental Science
        """
        try:
            if not self.session:
                self.session = httpx.AsyncClient(timeout=30.0)

            # Add field filter to query
            filtered_query = f"{query} fieldsOfStudy:{field}"

            return await self.search_papers(filtered_query, max_results)

        except Exception as e:
            logger.error(f"❌ Error in field-specific search: {e}")
            return []


# Global instance
semantic_scholar_api = SemanticScholarAPI()


async def search_semantic_scholar(query: str, max_results: int = 5) -> List[Dict]:
    """Convenience function to search Semantic Scholar"""
    async with SemanticScholarAPI() as api:
        return await api.search_papers(query, max_results)


# Test function
async def test_semantic_scholar_api():
    """Test Semantic Scholar API"""
    test_queries = [
        "deep learning fake news detection",
        "COVID-19 vaccine efficacy",
        "climate change mitigation strategies",
        "social media misinformation"
    ]

    async with SemanticScholarAPI() as api:
        print("Testing Semantic Scholar API Integration")
        print("=" * 50)

        for query in test_queries:
            print(f"\n🔍 Query: '{query}'")
            print("-" * 40)

            results = await api.search_papers(query, max_results=3)

            if results:
                for i, paper in enumerate(results, 1):
                    print(f"\n  {i}. {paper['title'][:60]}...")
                    print(f"     👥 {paper['authors']}")
                    print(f"     📊 Citations: {paper['citation_count']} ({paper['influential_citations']} influential)")
                    print(f"     📰 {paper['venue']}")
                    print(f"     ⭐ Credibility: {paper['credibility_score']:.2f}")
                    print(f"     🔗 {paper['url']}")
            else:
                print("  ❌ No results found")

            # Rate limit protection
            await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(test_semantic_scholar_api())
