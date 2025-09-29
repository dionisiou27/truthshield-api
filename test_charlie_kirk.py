#!/usr/bin/env python3
"""Test Charlie Kirk death claim"""

import asyncio
from src.core.ai_engine import TruthShieldAI

async def test_charlie_kirk_claim():
    print("Testing Charlie Kirk death claim...")
    
    ai = TruthShieldAI()
    
    # Test the specific claim
    claim = "Charlie Kirk is not Dead and alive"
    print(f"Claim: {claim}")
    
    try:
        # Test Google Fact Check specifically
        print("\n--- Google Fact Check Results ---")
        google_results = await ai._search_google_factcheck(claim, "en")
        print(f"Found {len(google_results)} Google Fact Check sources")
        
        for i, source in enumerate(google_results[:3]):
            print(f"  {i+1}. {source.title}")
            print(f"     URL: {source.url}")
            print(f"     Rating: {source.snippet}")
            print(f"     Score: {source.credibility_score}")
            print()
        
        # Test other sources
        print("--- Testing other sources ---")
        all_sources = await ai._search_sources(claim)
        print(f"Total sources found: {len(all_sources)}")
        
        # Show source breakdown
        source_types = {}
        for source in all_sources:
            domain = source.url.split('/')[2] if '/' in source.url else 'unknown'
            source_types[domain] = source_types.get(domain, 0) + 1
        
        print("\nSource breakdown:")
        for domain, count in sorted(source_types.items(), key=lambda x: x[1], reverse=True):
            print(f"  {domain}: {count} sources")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_charlie_kirk_claim())
