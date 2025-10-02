#!/usr/bin/env python3
"""
Test Google Fact Check API Integration
"""

import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from services.google_factcheck import search_google_factchecks
from core.config import settings

async def test_google_factcheck():
    """Test Google Fact Check API with real queries"""
    
    print("Testing Google Fact Check API Integration")
    print(f"API Key configured: {'YES' if settings.google_api_key else 'NO'}")
    
    if not settings.google_api_key:
        print("ERROR: No Google API Key found in .env file")
        return
    
    # Test queries
    test_queries = [
        ("COVID-19 vaccines cause autism", "en"),
        ("5G verursacht Coronavirus", "de"),
        ("Climate change is a hoax", "en"),
        ("Die Erde ist flach", "de")
    ]
    
    for query, lang in test_queries:
        print(f"\nTesting: '{query}' (lang: {lang})")
        print("-" * 50)
        
        try:
            results = await search_google_factchecks(query, lang)
            
            if results:
                print(f"SUCCESS: Found {len(results)} fact-check results:")
                
                for i, result in enumerate(results[:3], 1):
                    print(f"\n  {i}. {result['publisher']}")
                    print(f"     Rating: {result['rating']}")
                    print(f"     Verdict: {result['verdict']}")
                    print(f"     Credibility: {result['credibility_score']:.2f}")
                    print(f"     URL: {result['url'][:60]}...")
                    
            else:
                print("ERROR: No fact-check results found")
                
        except Exception as e:
            print(f"ERROR: {e}")
    
    print("\n" + "="*60)
    print("Google Fact Check API Test Complete!")

if __name__ == "__main__":
    asyncio.run(test_google_factcheck())
