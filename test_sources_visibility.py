#!/usr/bin/env python3
"""
Test Sources Visibility in API Response
"""

import requests
import json

def test_sources():
    url = "http://localhost:8000/api/v1/detect/fact-check"
    payload = {
        "text": "COVID-19 vaccines cause autism",
        "company": "ScienceAvatar", 
        "language": "en"
    }
    
    print("Testing Sources Visibility...")
    print("=" * 50)
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        
        data = response.json()
        
        # Check sources
        details = data.get('details', {})
        sources_found = details.get('sources_found', 0)
        verified_sources = details.get('verified_sources', [])
        all_sources = details.get('all_sources_checked', [])
        
        print(f"Sources Found: {sources_found}")
        print(f"Verified Sources Count: {len(verified_sources)}")
        print(f"All Sources Count: {len(all_sources)}")
        
        if verified_sources:
            print("\nVerified Sources:")
            for i, source in enumerate(verified_sources, 1):
                print(f"{i}. {source.get('title', 'No title')}")
                print(f"   URL: {source.get('url', 'No URL')}")
                print(f"   Credibility: {source.get('credibility_score', 0)}")
                print()
        else:
            print("\nNo verified sources found!")
            
        if all_sources:
            print(f"\nAll Sources ({len(all_sources)}):")
            for i, source in enumerate(all_sources[:3], 1):
                print(f"{i}. {source.get('title', 'No title')}")
                print(f"   URL: {source.get('url', 'No URL')}")
        
        # Check fact_check sources
        fact_check = data.get('fact_check', {})
        fc_sources = fact_check.get('sources', [])
        print(f"\nFact Check Sources Count: {len(fc_sources)}")
        
        if fc_sources:
            print("Fact Check Sources:")
            for i, source in enumerate(fc_sources[:3], 1):
                print(f"{i}. {source.get('title', 'No title')}")
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_sources()
