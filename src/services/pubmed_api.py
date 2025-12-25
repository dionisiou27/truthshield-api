"""
PubMed API Integration
Access to 35+ million biomedical literature citations via NCBI E-utilities
FREE - No API key required (but recommended for higher rate limits)
"""

import asyncio
import logging
from typing import Dict, List, Optional
import httpx
from datetime import datetime

logger = logging.getLogger(__name__)

class PubMedAPI:
    """PubMed/NCBI E-utilities API Integration for scientific fact-checking"""

    def __init__(self):
        self.base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
        self.session = None
        # Optional: Add email for higher rate limits (NCBI policy)
        self.email = "support@truthshield.eu"
        self.tool = "TruthShield"

    async def __aenter__(self):
        self.session = httpx.AsyncClient(timeout=30.0)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.aclose()

    async def search_articles(self, query: str, max_results: int = 5) -> List[Dict]:
        """
        Search PubMed for relevant scientific articles

        Args:
            query: Search query (medical/scientific claim)
            max_results: Maximum number of results to return

        Returns:
            List of article metadata with abstracts
        """
        try:
            if not self.session:
                self.session = httpx.AsyncClient(timeout=30.0)

            logger.info(f"🔬 Searching PubMed for: '{query[:50]}...'")

            # Step 1: Search for article IDs
            search_params = {
                "db": "pubmed",
                "term": query,
                "retmax": max_results,
                "retmode": "json",
                "sort": "relevance",
                "tool": self.tool,
                "email": self.email
            }

            search_response = await self.session.get(
                f"{self.base_url}/esearch.fcgi",
                params=search_params
            )
            search_response.raise_for_status()
            search_data = search_response.json()

            id_list = search_data.get("esearchresult", {}).get("idlist", [])

            if not id_list:
                logger.info("📭 No PubMed results found")
                return []

            logger.info(f"📚 Found {len(id_list)} PubMed articles, fetching details...")

            # Step 2: Fetch article details (summaries)
            fetch_params = {
                "db": "pubmed",
                "id": ",".join(id_list),
                "retmode": "json",
                "rettype": "abstract",
                "tool": self.tool,
                "email": self.email
            }

            fetch_response = await self.session.get(
                f"{self.base_url}/esummary.fcgi",
                params=fetch_params
            )
            fetch_response.raise_for_status()
            fetch_data = fetch_response.json()

            # Process results
            articles = []
            result_data = fetch_data.get("result", {})

            for pmid in id_list:
                article_data = result_data.get(pmid, {})
                if not article_data or pmid == "uids":
                    continue

                formatted_article = self._format_article(article_data, pmid)
                if formatted_article:
                    articles.append(formatted_article)

            logger.info(f"✅ PubMed: Retrieved {len(articles)} articles")
            return articles

        except httpx.HTTPStatusError as e:
            logger.error(f"❌ PubMed API HTTP error: {e.response.status_code}")
            return []
        except Exception as e:
            logger.error(f"❌ PubMed API error: {e}")
            return []

    def _format_article(self, article_data: Dict, pmid: str) -> Optional[Dict]:
        """Format PubMed article data for TruthShield"""
        try:
            title = article_data.get("title", "")

            # Get authors
            authors = article_data.get("authors", [])
            author_names = [a.get("name", "") for a in authors[:3]]
            author_str = ", ".join(author_names)
            if len(authors) > 3:
                author_str += " et al."

            # Get publication info
            source = article_data.get("source", "")  # Journal name
            pub_date = article_data.get("pubdate", "")

            # Build snippet
            snippet = f"{author_str}. {source}. {pub_date}."

            # Get DOI if available
            article_ids = article_data.get("articleids", [])
            doi = None
            for aid in article_ids:
                if aid.get("idtype") == "doi":
                    doi = aid.get("value")
                    break

            # Build URL
            url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
            if doi:
                url = f"https://doi.org/{doi}"

            return {
                "source": "pubmed",
                "pmid": pmid,
                "title": title,
                "url": url,
                "snippet": snippet,
                "authors": author_str,
                "journal": source,
                "pub_date": pub_date,
                "doi": doi,
                "credibility_score": 0.92,  # Peer-reviewed scientific literature
            }

        except Exception as e:
            logger.error(f"❌ Error formatting PubMed article: {e}")
            return None

    async def get_abstract(self, pmid: str) -> Optional[str]:
        """Fetch full abstract for a specific article"""
        try:
            if not self.session:
                self.session = httpx.AsyncClient(timeout=30.0)

            params = {
                "db": "pubmed",
                "id": pmid,
                "retmode": "xml",
                "rettype": "abstract",
                "tool": self.tool,
                "email": self.email
            }

            response = await self.session.get(
                f"{self.base_url}/efetch.fcgi",
                params=params
            )
            response.raise_for_status()

            # Simple XML parsing for abstract
            text = response.text
            if "<AbstractText>" in text:
                start = text.find("<AbstractText>") + len("<AbstractText>")
                end = text.find("</AbstractText>")
                if start > 0 and end > start:
                    return text[start:end][:500]  # Limit to 500 chars

            return None

        except Exception as e:
            logger.error(f"❌ Error fetching PubMed abstract: {e}")
            return None


# Global instance
pubmed_api = PubMedAPI()

async def search_pubmed(query: str, max_results: int = 5) -> List[Dict]:
    """Convenience function to search PubMed"""
    async with PubMedAPI() as api:
        return await api.search_articles(query, max_results)


# Test function
async def test_pubmed_api():
    """Test PubMed API"""
    test_queries = [
        "COVID-19 vaccine effectiveness",
        "climate change health effects",
        "5G radiation safety",
        "mRNA vaccine technology"
    ]

    async with PubMedAPI() as api:
        print("Testing PubMed API Integration")
        print("=" * 50)

        for query in test_queries:
            print(f"\n🔍 Query: '{query}'")
            print("-" * 40)

            results = await api.search_articles(query, max_results=3)

            if results:
                for i, article in enumerate(results, 1):
                    print(f"\n  {i}. {article['title'][:60]}...")
                    print(f"     📰 {article['journal']}")
                    print(f"     👥 {article['authors']}")
                    print(f"     🔗 {article['url']}")
                    print(f"     ⭐ Credibility: {article['credibility_score']}")
            else:
                print("  ❌ No results found")


if __name__ == "__main__":
    asyncio.run(test_pubmed_api())
