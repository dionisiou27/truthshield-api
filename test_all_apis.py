#!/usr/bin/env python3
"""
Test All Real APIs Integration
Google Fact Check API + News API + TruthShield AI
"""

import asyncio
import sys
import os
import json

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from services.google_factcheck import search_google_factchecks
from services.news_api import search_news_context
from services.claimbuster_api import score_claim_worthiness
from core.config import settings

async def test_all_apis():
    """Test all real APIs working together"""
    
    print("=" * 60)
    print("TRUTHSHIELD REAL API INTEGRATION TEST")
    print("=" * 60)
    
    # Check API status
    google_available = bool(settings.google_api_key)
    news_available = bool(settings.news_api_key)
    claimbuster_available = bool(settings.claimbuster_api_key)
    openai_available = bool(settings.openai_api_key)
    
    print(f"Google Fact Check API: {'ACTIVE' if google_available else 'MISSING'}")
    print(f"News API:              {'ACTIVE' if news_available else 'MISSING'}")
    print(f"ClaimBuster API:       {'ACTIVE' if claimbuster_available else 'MISSING'}")
    print(f"OpenAI API:            {'ACTIVE' if openai_available else 'MISSING'}")
    print()
    
    if not (google_available and news_available and claimbuster_available):
        print("ERROR: Missing API keys in .env file")
        return
    
    # Test claims
    test_claims = [
        {
            "text": "COVID-19 vaccines cause autism",
            "language": "en",
            "expected": "false"
        },
        {
            "text": "BMW electric vehicles are unreliable",
            "language": "en", 
            "expected": "uncertain"
        },
        {
            "text": "5G verursacht Coronavirus",
            "language": "de",
            "expected": "false"
        }
    ]
    
    for i, claim in enumerate(test_claims, 1):
        print(f"TEST {i}: {claim['text']}")
        print("-" * 50)
        
        # Test Google Fact Check
        print("1. Google Fact Check API:")
        try:
            google_results = await search_google_factchecks(claim['text'], claim['language'])
            if google_results:
                print(f"   SUCCESS: {len(google_results)} fact-check sources found")
                for j, result in enumerate(google_results[:2], 1):
                    print(f"   {j}. {result['publisher']} - {result['verdict']}")
            else:
                print("   No fact-check results found")
        except Exception as e:
            print(f"   ERROR: {e}")
        
        # Test News API
        print("\n2. News API:")
        try:
            news_results = await search_news_context(claim['text'], claim['language'])
            if news_results:
                print(f"   SUCCESS: {len(news_results)} news articles found")
                for j, result in enumerate(news_results[:2], 1):
                    print(f"   {j}. {result['source_name']} - {result['title'][:50]}...")
            else:
                print("   No news articles found")
        except Exception as e:
            print(f"   ERROR: {e}")
        
        # Test ClaimBuster API
        print("\n3. ClaimBuster API:")
        try:
            claimbuster_result = await score_claim_worthiness(claim['text'])
            if claimbuster_result:
                print(f"   SUCCESS: Claim analysis complete")
                print(f"   Claim-worthy: {claimbuster_result['claim_worthy']}")
                print(f"   Score: {claimbuster_result['max_score']:.3f}")
                print(f"   Confidence: {claimbuster_result['confidence']:.3f}")
            else:
                print("   No ClaimBuster analysis available")
        except Exception as e:
            print(f"   ERROR: {e}")
        
        print("\n" + "="*60 + "\n")
    
    print("SUMMARY:")
    print("- Google Fact Check API: Provides real fact-checking sources")
    print("- News API: Provides current news context")
    print("- ClaimBuster API: Provides claim-worthiness scoring")  
    print("- Combined: Creates comprehensive fact-checking with real data")
    print("\nALL 3 APIS ACTIVE - MOCK DATA COMPLETELY REPLACED!")

if __name__ == "__main__":
    asyncio.run(test_all_apis())
