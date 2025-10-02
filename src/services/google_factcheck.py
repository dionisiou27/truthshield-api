"""
Google Fact Check Tools API Integration
Real-time fact-checking using Google's Fact Check Claims Search API
"""

import asyncio
import logging
from typing import Dict, List, Optional
import httpx
from datetime import datetime
from src.core.config import settings

logger = logging.getLogger(__name__)

class GoogleFactCheckAPI:
    """Google Fact Check Tools API Integration"""
    
    def __init__(self):
        self.api_key = settings.google_api_key
        self.base_url = "https://factchecktools.googleapis.com/v1alpha1/claims:search"
        self.session = None
        
    async def __aenter__(self):
        self.session = httpx.AsyncClient(timeout=30.0)
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.aclose()
    
    async def search_fact_checks(self, query: str, language: str = "de") -> List[Dict]:
        """
        Search for fact-checks using Google Fact Check Tools API
        
        Args:
            query: The claim to fact-check
            language: Language code (de, en, etc.)
            
        Returns:
            List of fact-check results
        """
        if not self.api_key:
            logger.warning("🔑 Google API Key not configured")
            return []
            
        try:
            params = {
                'key': self.api_key,
                'query': query,
                'languageCode': language,
                'pageSize': 10,  # Max 10 results
                'offset': 0
            }
            
            logger.info(f"🔍 Searching Google Fact Check for: '{query[:50]}...'")
            
            if not self.session:
                self.session = httpx.AsyncClient(timeout=30.0)
                
            response = await self.session.get(self.base_url, params=params)
            response.raise_for_status()
            
            data = response.json()
            claims = data.get('claims', [])
            
            logger.info(f"✅ Found {len(claims)} fact-check results from Google")
            
            # Process and format results
            formatted_results = []
            for claim in claims:
                formatted_claim = self._format_claim(claim)
                if formatted_claim:
                    formatted_results.append(formatted_claim)
                    
            return formatted_results
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403:
                logger.error("❌ Google API Key invalid or quota exceeded")
            else:
                logger.error(f"❌ Google Fact Check API error: {e.response.status_code}")
            return []
            
        except Exception as e:
            logger.error(f"❌ Google Fact Check API error: {e}")
            return []
    
    def _format_claim(self, claim_data: Dict) -> Optional[Dict]:
        """Format Google Fact Check claim data"""
        try:
            # Extract claim text
            claim_text = claim_data.get('text', '')
            
            # Extract claim reviews (fact-checks)
            claim_reviews = claim_data.get('claimReview', [])
            if not claim_reviews:
                return None
                
            # Get the first (most relevant) review
            review = claim_reviews[0]
            
            # Extract publisher info
            publisher = review.get('publisher', {})
            publisher_name = publisher.get('name', 'Unknown')
            publisher_site = publisher.get('site', '')
            
            # Extract rating
            review_rating = review.get('reviewRating', {})
            rating_value = review_rating.get('ratingValue')
            rating_explanation = review_rating.get('ratingExplanation', '')
            worst_rating = review_rating.get('worstRating', 1)
            best_rating = review_rating.get('bestRating', 5)
            
            # Calculate credibility score (0-1)
            credibility_score = 0.7  # Default for Google sources
            if rating_value and best_rating and worst_rating:
                try:
                    # Normalize rating to 0-1 scale
                    normalized_rating = (float(rating_value) - float(worst_rating)) / (float(best_rating) - float(worst_rating))
                    credibility_score = max(0.5, min(1.0, normalized_rating))  # Keep between 0.5-1.0
                except:
                    pass
            
            # Determine verdict based on rating explanation
            verdict = self._determine_verdict(rating_explanation, rating_value)
            
            return {
                'source': 'google_factcheck',
                'claim_text': claim_text,
                'url': review.get('url', ''),
                'title': review.get('title', f"Fact-check by {publisher_name}"),
                'publisher': publisher_name,
                'publisher_site': publisher_site,
                'rating': rating_explanation,
                'rating_value': rating_value,
                'verdict': verdict,
                'credibility_score': credibility_score,
                'date_published': review.get('datePublished', ''),
                'snippet': f"Rated as '{rating_explanation}' by {publisher_name}"
            }
            
        except Exception as e:
            logger.error(f"❌ Error formatting Google claim: {e}")
            return None
    
    def _determine_verdict(self, rating_explanation: str, rating_value) -> str:
        """Determine verdict from Google rating"""
        if not rating_explanation:
            return "uncertain"
            
        rating_lower = rating_explanation.lower()
        
        # False/Fake indicators
        if any(word in rating_lower for word in ['false', 'fake', 'incorrect', 'misleading', 'pants on fire']):
            return "false"
            
        # True indicators  
        if any(word in rating_lower for word in ['true', 'correct', 'accurate', 'verified']):
            return "true"
            
        # Partially true indicators
        if any(word in rating_lower for word in ['partly', 'partially', 'mixed', 'half']):
            return "partially_true"
            
        # Uncertain indicators
        if any(word in rating_lower for word in ['unproven', 'unclear', 'insufficient', 'research']):
            return "uncertain"
            
        return "uncertain"

# Global instance
google_factcheck = GoogleFactCheckAPI()

async def search_google_factchecks(query: str, language: str = "de") -> List[Dict]:
    """Convenience function to search Google fact-checks"""
    async with GoogleFactCheckAPI() as api:
        return await api.search_fact_checks(query, language)


# Test function
async def test_google_factcheck():
    """Test Google Fact Check API"""
    test_queries = [
        "COVID-19 vaccines cause autism",
        "Climate change is a hoax", 
        "5G causes coronavirus"
    ]
    
    async with GoogleFactCheckAPI() as api:
        for query in test_queries:
            print(f"\n🔍 Testing: {query}")
            results = await api.search_fact_checks(query, "en")
            
            if results:
                for result in results[:2]:  # Show first 2 results
                    print(f"  ✅ {result['publisher']}: {result['rating']}")
                    print(f"     {result['snippet']}")
            else:
                print("  ❌ No results found")

if __name__ == "__main__":
    asyncio.run(test_google_factcheck())
