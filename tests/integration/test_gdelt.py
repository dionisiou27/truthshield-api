#!/usr/bin/env python3
"""Test GDELT integration"""

import asyncio
from src.core.ai_engine import TruthShieldAI

async def test_gdelt():
    print("Testing GDELT integration...")
    
    ai = TruthShieldAI()
    
    # Test GDELT with various queries
    test_queries = [
        "Charlie Kirk death",
        "BMW electric vehicles",
        "Tesla safety",
        "COVID vaccine",
        "Ukraine war"
    ]
    
    for query in test_queries:
        print(f"\n--- Testing GDELT: {query} ---")
        try:
            results = await ai._search_gdelt(query)
            print(f"Found {len(results)} GDELT sources")
            
            for i, source in enumerate(results[:3]):  # Show first 3
                print(f"  {i+1}. {source.title[:60]}...")
                print(f"     URL: {source.url}")
                print(f"     Score: {source.credibility_score}")
                print(f"     Snippet: {source.snippet[:80]}...")
                print()
                
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_gdelt())
