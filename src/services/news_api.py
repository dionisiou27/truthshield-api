"""
News API Integration
Real-time news monitoring and context gathering
"""

import asyncio
import logging
from typing import Dict, List, Optional
import httpx
from datetime import datetime, timedelta
from src.core.config import settings

logger = logging.getLogger(__name__)

class NewsAPIClient:
    """News API Integration for real-time news context"""
    
    def __init__(self):
        self.api_key = settings.news_api_key
        self.base_url = "https://newsapi.org/v2"
        self.session = None
        
    async def __aenter__(self):
        self.session = httpx.AsyncClient(timeout=30.0)
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.aclose()
    
    async def search_news(self, query: str, language: str = "de", days_back: int = 7) -> List[Dict]:
        """
        Search for news articles related to a claim
        
        Args:
            query: Search query
            language: Language code (de, en, etc.)
            days_back: How many days back to search
            
        Returns:
            List of news articles
        """
        if not self.api_key:
            logger.warning("🔑 News API Key not configured")
            return []
            
        try:
            # Calculate date range
            to_date = datetime.now()
            from_date = to_date - timedelta(days=days_back)
            
            params = {
                'apiKey': self.api_key,
                'q': query,
                'language': language,
                'sortBy': 'relevancy',
                'pageSize': 10,
                'from': from_date.strftime('%Y-%m-%d'),
                'to': to_date.strftime('%Y-%m-%d')
            }
            
            logger.info(f"🔍 Searching News API for: '{query[:50]}...' (lang={language})")
            
            if not self.session:
                self.session = httpx.AsyncClient(timeout=30.0)
                
            response = await self.session.get(f"{self.base_url}/everything", params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('status') != 'ok':
                logger.error(f"❌ News API error: {data.get('message', 'Unknown error')}")
                return []
            
            articles = data.get('articles', [])
            logger.info(f"✅ Found {len(articles)} news articles")
            
            # Process and format results
            formatted_articles = []
            for article in articles:
                formatted_article = self._format_article(article)
                if formatted_article:
                    formatted_articles.append(formatted_article)
                    
            return formatted_articles
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                logger.error("❌ News API Key invalid")
            elif e.response.status_code == 429:
                logger.error("❌ News API rate limit exceeded")
            else:
                logger.error(f"❌ News API error: {e.response.status_code}")
            return []
            
        except Exception as e:
            logger.error(f"❌ News API error: {e}")
            return []
    
    async def get_top_headlines(self, country: str = "de", category: str = None) -> List[Dict]:
        """
        Get top headlines for context
        
        Args:
            country: Country code (de, us, etc.)
            category: Category (business, entertainment, general, health, science, sports, technology)
            
        Returns:
            List of top headlines
        """
        if not self.api_key:
            return []
            
        try:
            params = {
                'apiKey': self.api_key,
                'country': country,
                'pageSize': 20
            }
            
            if category:
                params['category'] = category
            
            if not self.session:
                self.session = httpx.AsyncClient(timeout=30.0)
                
            response = await self.session.get(f"{self.base_url}/top-headlines", params=params)
            response.raise_for_status()
            
            data = response.json()
            articles = data.get('articles', [])
            
            formatted_articles = []
            for article in articles:
                formatted_article = self._format_article(article)
                if formatted_article:
                    formatted_articles.append(formatted_article)
                    
            return formatted_articles
            
        except Exception as e:
            logger.error(f"❌ News API headlines error: {e}")
            return []
    
    def _format_article(self, article_data: Dict) -> Optional[Dict]:
        """Format News API article data"""
        try:
            # Skip articles without essential data
            if not article_data.get('title') or not article_data.get('url'):
                return None
                
            # Skip removed articles
            if article_data.get('title') == '[Removed]':
                return None
            
            # Extract source info
            source = article_data.get('source', {})
            source_name = source.get('name', 'Unknown')
            
            # Calculate credibility score based on source
            credibility_score = self._calculate_credibility(source_name)
            
            # Format description/content
            description = article_data.get('description', '')
            content = article_data.get('content', '')
            
            # Use description or truncated content as snippet
            snippet = description or content[:200] + "..." if content else "No description available"
            
            return {
                'source': 'news_api',
                'title': article_data.get('title', ''),
                'url': article_data.get('url', ''),
                'source_name': source_name,
                'author': article_data.get('author', ''),
                'published_at': article_data.get('publishedAt', ''),
                'snippet': snippet,
                'credibility_score': credibility_score,
                'url_to_image': article_data.get('urlToImage', ''),
                'content': content
            }
            
        except Exception as e:
            logger.error(f"❌ Error formatting news article: {e}")
            return None
    
    def _calculate_credibility(self, source_name: str) -> float:
        """Calculate credibility score based on news source"""
        source_lower = source_name.lower()
        
        # High credibility sources
        high_credibility = [
            'reuters', 'associated press', 'ap news', 'bbc', 'dw.com', 
            'deutsche welle', 'tagesschau', 'zeit online', 'spiegel',
            'süddeutsche zeitung', 'faz', 'handelsblatt', 'npr',
            'the guardian', 'washington post', 'new york times'
        ]
        
        # Medium credibility sources
        medium_credibility = [
            'cnn', 'fox news', 'bloomberg', 'wall street journal',
            'focus', 'stern', 'welt', 'tagesspiegel', 'heise'
        ]
        
        # Check for high credibility
        for source in high_credibility:
            if source in source_lower:
                return 0.9
        
        # Check for medium credibility
        for source in medium_credibility:
            if source in source_lower:
                return 0.7
        
        # Default credibility for unknown sources
        return 0.6

# Global instance
news_api = NewsAPIClient()

async def search_news_context(query: str, language: str = "de") -> List[Dict]:
    """Convenience function to search news context"""
    async with NewsAPIClient() as api:
        return await api.search_news(query, language)

async def get_headlines_context(country: str = "de") -> List[Dict]:
    """Convenience function to get headlines context"""
    async with NewsAPIClient() as api:
        return await api.get_top_headlines(country)


# Test function
async def test_news_api():
    """Test News API"""
    test_queries = [
        ("COVID-19 vaccine", "en"),
        ("Klimawandel", "de"), 
        ("5G coronavirus", "en"),
        ("BMW electric vehicles", "en")
    ]
    
    async with NewsAPIClient() as api:
        print("Testing News API Integration")
        print(f"API Key configured: {'YES' if api.api_key else 'NO'}")
        
        if not api.api_key:
            print("ERROR: No News API Key found")
            return
        
        for query, lang in test_queries:
            print(f"\nTesting: '{query}' (lang: {lang})")
            print("-" * 50)
            
            results = await api.search_news(query, lang, days_back=30)
            
            if results:
                print(f"SUCCESS: Found {len(results)} news articles:")
                
                for i, result in enumerate(results[:3], 1):
                    print(f"\n  {i}. {result['source_name']}")
                    print(f"     Title: {result['title'][:60]}...")
                    print(f"     Credibility: {result['credibility_score']:.2f}")
                    print(f"     Published: {result['published_at'][:10]}")
                    
            else:
                print("ERROR: No news articles found")

if __name__ == "__main__":
    asyncio.run(test_news_api())
