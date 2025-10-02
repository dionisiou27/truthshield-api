#!/usr/bin/env python3
"""
Test Improved ClaimBuster API Integration
Testing both GET and POST methods
"""

import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from services.claimbuster_api import ClaimBusterAPI
from core.config import settings

async def test_claimbuster_methods():
    """Test ClaimBuster API with both GET and POST methods"""
    
    print("Testing ClaimBuster API - GET vs POST Methods")
    print("=" * 60)
    
    if not settings.claimbuster_api_key:
        print("ERROR: No ClaimBuster API Key found in .env file")
        return
    
    test_claims = [
        "The sky is blue.",  # Simple test from documentation
        "COVID-19 vaccines cause autism",
        "Climate change is a hoax",
        "BMW electric vehicles are unreliable"
    ]
    
    async with ClaimBusterAPI() as api:
        for i, claim in enumerate(test_claims, 1):
            print(f"\nTEST {i}: '{claim}'")
            print("-" * 50)
            
            # Test GET method
            print("GET Method:")
            try:
                get_result = await api.score_text(claim, use_get=True)
                if get_result:
                    print(f"  SUCCESS - Score: {get_result['max_score']:.3f}, Claim-worthy: {get_result['claim_worthy']}")
                else:
                    print("  ERROR - No result")
            except Exception as e:
                print(f"  ERROR - {e}")
            
            # Test POST method
            print("POST Method:")
            try:
                post_result = await api.score_text(claim, use_get=False)
                if post_result:
                    print(f"  SUCCESS - Score: {post_result['max_score']:.3f}, Claim-worthy: {post_result['claim_worthy']}")
                else:
                    print("  ERROR - No result")
            except Exception as e:
                print(f"  ERROR - {e}")
            
            print()
    
    print("=" * 60)
    print("ClaimBuster API Test Complete!")
    print("Both GET and POST methods should work now.")

if __name__ == "__main__":
    asyncio.run(test_claimbuster_methods())
