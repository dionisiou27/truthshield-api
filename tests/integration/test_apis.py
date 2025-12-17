#!/usr/bin/env python3
"""Test API functionality"""

import asyncio
from src.core.ai_engine import TruthShieldAI

async def test_apis():
    print("Testing API functionality...")
    
    ai = TruthShieldAI()
    
    # Test Google Fact Check API
    print("\nTesting Google Fact Check API...")
    try:
        google_results = await ai._search_google_factcheck("BMW electric vehicles", "en")
        print(f"OK Google Fact Check: {len(google_results)} sources found")
        if google_results:
            print(f"   First result: {google_results[0].title[:50]}...")
    except Exception as e:
        print(f"FAILED Google Fact Check: {e}")
    
    # Test NewsAPI
    print("\nTesting NewsAPI...")
    try:
        news_results = await ai._search_news_api("BMW electric vehicles", "en")
        print(f"OK NewsAPI: {len(news_results)} sources found")
        if news_results:
            print(f"   First result: {news_results[0].title[:50]}...")
    except Exception as e:
        print(f"FAILED NewsAPI: {e}")
    
    # Test other sources
    print("\nTesting other sources...")
    try:
        wikipedia_results = await ai._search_wikipedia("BMW electric vehicles", "en")
        print(f"OK Wikipedia: {len(wikipedia_results)} sources found")
    except Exception as e:
        print(f"FAILED Wikipedia: {e}")
    
    print("\nAPI testing complete!")

if __name__ == "__main__":
    asyncio.run(test_apis())