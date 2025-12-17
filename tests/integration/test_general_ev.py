#!/usr/bin/env python3
"""Test general EV explosion claims"""

import asyncio
from src.core.ai_engine import TruthShieldAI

async def test_general_ev_claims():
    print("Testing general EV explosion claims...")
    
    ai = TruthShieldAI()
    
    # Test various EV explosion claims
    test_queries = [
        "EVs explode in winter",
        "electric vehicles explode in cold weather", 
        "Tesla cars explode in freezing temperatures",
        "electric car batteries explode",
        "EVs catch fire in winter"
    ]
    
    for query in test_queries:
        print(f"\n--- Testing: {query} ---")
        try:
            results = await ai._search_google_factcheck(query, "en")
            print(f"Found {len(results)} sources")
            
            for i, source in enumerate(results[:2]):  # Show first 2
                print(f"  {i+1}. {source.title[:60]}...")
                print(f"     Rating: {source.snippet}")
                
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_general_ev_claims())
