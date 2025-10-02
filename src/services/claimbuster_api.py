"""
ClaimBuster API Integration
Real-time claim detection and fact-checking using ClaimBuster
"""

import asyncio
import logging
from typing import Dict, List, Optional
import httpx
from datetime import datetime
from src.core.config import settings

logger = logging.getLogger(__name__)

class ClaimBusterAPI:
    """ClaimBuster API Integration for claim detection and fact-checking"""
    
    def __init__(self):
        self.api_key = settings.claimbuster_api_key
        self.base_url = "https://idir.uta.edu/claimbuster/api/v2"
        self.session = None
        
    async def __aenter__(self):
        self.session = httpx.AsyncClient(timeout=30.0)
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.aclose()
    
    async def score_text(self, text: str, use_get: bool = True) -> Dict:
        """
        Score text for claim-worthiness using ClaimBuster API
        
        Args:
            text: Text to analyze for claims
            use_get: Use GET method (True) or POST method (False)
            
        Returns:
            Dictionary with claim scores and sentences
        """
        if not self.api_key:
            logger.warning("🔑 ClaimBuster API Key not configured")
            return {}
            
        try:
            headers = {
                'x-api-key': self.api_key
            }
            
            logger.info(f"🔍 Scoring text with ClaimBuster ({'GET' if use_get else 'POST'}): '{text[:50]}...'")
            
            if not self.session:
                self.session = httpx.AsyncClient(timeout=30.0)
            
            if use_get:
                # GET Request - text in URL path
                from urllib.parse import quote
                encoded_text = quote(text)
                response = await self.session.get(
                    f"{self.base_url}/score/text/{encoded_text}",
                    headers=headers
                )
            else:
                # POST Request - text in JSON payload
                headers['Content-Type'] = 'application/json'
                payload = {'input_text': text}
                response = await self.session.post(
                    f"{self.base_url}/score/text/",
                    headers=headers,
                    json=payload
                )
            
            response.raise_for_status()
            data = response.json()
            logger.info(f"✅ ClaimBuster analysis complete")
            
            return self._format_score_response(data)
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                logger.error("❌ ClaimBuster API Key invalid")
            elif e.response.status_code == 429:
                logger.error("❌ ClaimBuster API rate limit exceeded")
            elif e.response.status_code == 414 and use_get:
                # URL too long, fallback to POST
                logger.warning("⚠️ URL too long for GET, trying POST...")
                return await self.score_text(text, use_get=False)
            else:
                logger.error(f"❌ ClaimBuster API error: {e.response.status_code}")
            return {}
            
        except Exception as e:
            logger.error(f"❌ ClaimBuster API error: {e}")
            return {}
    
    async def search_claims(self, query: str, limit: int = 10) -> List[Dict]:
        """
        Search for similar claims in ClaimBuster database
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of similar claims with fact-check results
        """
        if not self.api_key:
            return []
            
        try:
            headers = {
                'x-api-key': self.api_key
            }
            
            params = {
                'input_claim': query,
                'top_k': limit
            }
            
            logger.info(f"🔍 Searching ClaimBuster for: '{query[:50]}...'")
            
            if not self.session:
                self.session = httpx.AsyncClient(timeout=30.0)
                
            response = await self.session.get(
                f"{self.base_url}/query/search/",
                headers=headers,
                params=params
            )
            response.raise_for_status()
            
            data = response.json()
            claims = data.get('claims', [])
            
            logger.info(f"✅ Found {len(claims)} similar claims in ClaimBuster")
            
            # Format results
            formatted_claims = []
            for claim in claims:
                formatted_claim = self._format_claim_result(claim)
                if formatted_claim:
                    formatted_claims.append(formatted_claim)
                    
            return formatted_claims
            
        except Exception as e:
            logger.error(f"❌ ClaimBuster search error: {e}")
            return []
    
    def _format_score_response(self, data: Dict) -> Dict:
        """Format ClaimBuster score response"""
        try:
            results = data.get('results', [])
            
            # Extract sentences and scores
            sentences = []
            max_score = 0.0
            
            for result in results:
                sentence_text = result.get('text', '')
                score = float(result.get('score', 0.0))
                
                sentences.append({
                    'text': sentence_text,
                    'score': score,
                    'claim_worthy': score > 0.5  # ClaimBuster threshold
                })
                
                max_score = max(max_score, score)
            
            # Determine overall assessment
            claim_worthy = max_score > 0.5
            confidence = min(max_score * 2, 1.0)  # Scale to 0-1
            
            return {
                'source': 'claimbuster',
                'claim_worthy': claim_worthy,
                'max_score': max_score,
                'confidence': confidence,
                'sentences': sentences,
                'total_sentences': len(sentences),
                'claim_sentences': sum(1 for s in sentences if s['claim_worthy'])
            }
            
        except Exception as e:
            logger.error(f"❌ Error formatting ClaimBuster score: {e}")
            return {}
    
    def _format_claim_result(self, claim_data: Dict) -> Optional[Dict]:
        """Format ClaimBuster claim search result"""
        try:
            # Extract claim info
            claim_text = claim_data.get('text', '')
            similarity = float(claim_data.get('similarity', 0.0))
            
            # Extract fact-check info if available
            fact_checkers = claim_data.get('fact_checkers', [])
            
            # Get the best fact-check result
            best_fact_check = None
            if fact_checkers:
                best_fact_check = fact_checkers[0]  # Usually sorted by relevance
            
            # Determine verdict from fact-check
            verdict = "uncertain"
            rating = "No rating"
            fact_checker_name = "ClaimBuster"
            
            if best_fact_check:
                rating = best_fact_check.get('rating', 'No rating')
                fact_checker_name = best_fact_check.get('fact_checker', 'ClaimBuster')
                verdict = self._determine_verdict_from_rating(rating)
            
            # Calculate credibility score
            credibility_score = 0.8  # ClaimBuster is high credibility
            if similarity < 0.7:
                credibility_score = 0.6  # Lower for less similar claims
            
            return {
                'source': 'claimbuster',
                'claim_text': claim_text,
                'similarity': similarity,
                'verdict': verdict,
                'rating': rating,
                'fact_checker': fact_checker_name,
                'credibility_score': credibility_score,
                'url': claim_data.get('url', ''),
                'title': f"Similar claim found by {fact_checker_name}",
                'snippet': f"Rated as '{rating}' (similarity: {similarity:.2f})"
            }
            
        except Exception as e:
            logger.error(f"❌ Error formatting ClaimBuster claim: {e}")
            return None
    
    def _determine_verdict_from_rating(self, rating: str) -> str:
        """Determine verdict from ClaimBuster rating"""
        if not rating:
            return "uncertain"
            
        rating_lower = rating.lower()
        
        # False indicators
        if any(word in rating_lower for word in ['false', 'pants on fire', 'incorrect', 'misleading']):
            return "false"
            
        # True indicators  
        if any(word in rating_lower for word in ['true', 'correct', 'accurate']):
            return "true"
            
        # Partially true indicators
        if any(word in rating_lower for word in ['mostly', 'partly', 'half']):
            return "partially_true"
            
        return "uncertain"

# Global instance
claimbuster_api = ClaimBusterAPI()

async def score_claim_worthiness(text: str) -> Dict:
    """Convenience function to score claim-worthiness"""
    async with ClaimBusterAPI() as api:
        return await api.score_text(text)

async def search_similar_claims(query: str) -> List[Dict]:
    """Convenience function to search similar claims"""
    async with ClaimBusterAPI() as api:
        return await api.search_claims(query)


# Test function
async def test_claimbuster_api():
    """Test ClaimBuster API"""
    test_texts = [
        "COVID-19 vaccines cause autism",
        "Climate change is a hoax created by scientists", 
        "5G networks cause coronavirus",
        "BMW electric vehicles are the most reliable cars"
    ]
    
    async with ClaimBusterAPI() as api:
        print("Testing ClaimBuster API Integration")
        print(f"API Key configured: {'YES' if api.api_key else 'NO'}")
        
        if not api.api_key:
            print("ERROR: No ClaimBuster API Key found in .env file")
            return
        
        for text in test_texts:
            print(f"\nTesting: '{text}'")
            print("-" * 50)
            
            # Test claim scoring
            print("1. Claim Worthiness Scoring:")
            score_result = await api.score_text(text)
            if score_result:
                print(f"   Claim-worthy: {score_result['claim_worthy']}")
                print(f"   Max Score: {score_result['max_score']:.3f}")
                print(f"   Confidence: {score_result['confidence']:.3f}")
                print(f"   Claim sentences: {score_result['claim_sentences']}/{score_result['total_sentences']}")
            else:
                print("   ERROR: No scoring results")
            
            # Test similar claims search
            print("\n2. Similar Claims Search:")
            search_results = await api.search_claims(text, limit=3)
            if search_results:
                print(f"   SUCCESS: {len(search_results)} similar claims found")
                for j, result in enumerate(search_results, 1):
                    print(f"   {j}. {result['fact_checker']} - {result['verdict']}")
                    print(f"      Similarity: {result['similarity']:.3f}")
            else:
                print("   No similar claims found")
            
            print()

if __name__ == "__main__":
    asyncio.run(test_claimbuster_api())
