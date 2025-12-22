#!/usr/bin/env python3
"""Test improved Google Fact Check API"""

import asyncio
from src.core.ai_engine import TruthShieldAI

async def test_improved_google():
    print("Testing improved Google Fact Check API...")
    
    ai = TruthShieldAI()
    
    # Test with the BMW claim
    query = "BMW electric vehicles explode in freezing temperatures"
    print(f"Query: {query}")
    
    try:
        results = await ai._search_google_factcheck(query, "en")
        print(f"Found {len(results)} sources")
        
        for i, source in enumerate(results[:3]):  # Show first 3
            print(f"\n{i+1}. {source.title}")
            print(f"   URL: {source.url}")
            print(f"   Rating: {source.snippet}")
            print(f"   Score: {source.credibility_score}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_improved_google())
