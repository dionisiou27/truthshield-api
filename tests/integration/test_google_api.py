#!/usr/bin/env python3
"""Test Google Fact Check API specifically"""

import asyncio
import httpx
from src.core.config import settings

async def test_google_factcheck_api():
    print("Testing Google Fact Check API...")
    
    api_key = settings.google_api_key
    print(f"API Key: {api_key[:10]}..." if api_key else "No API Key")
    
    if not api_key:
        print("❌ No Google API Key found")
        return
    
    # Test different endpoints and parameters
    base_url = "https://factchecktools.googleapis.com/v1alpha1"
    
    # Test 1: Basic claims search
    print("\n1. Testing claims search...")
    try:
        url = f"{base_url}/claims:search"
        params = {
            "key": api_key,
            "query": "BMW electric vehicles",
            "languageCode": "en",
            "pageSize": 5
        }
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params)
            print(f"Status: {response.status_code}")
            print(f"Headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"SUCCESS! Found {len(data.get('claims', []))} claims")
                if data.get('claims'):
                    print(f"First claim: {data['claims'][0].get('text', 'No text')[:100]}...")
            else:
                print(f"ERROR: {response.text[:200]}")
                
    except Exception as e:
        print(f"Exception: {e}")
    
    # Test 2: Check if API is enabled
    print("\n2. Testing API discovery...")
    try:
        discovery_url = "https://factchecktools.googleapis.com/$discovery/rest?version=v1alpha1"
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(discovery_url)
            print(f"Discovery Status: {response.status_code}")
            if response.status_code == 200:
                print("API Discovery successful")
            else:
                print(f"Discovery failed: {response.text[:200]}")
                
    except Exception as e:
        print(f"Discovery Exception: {e}")
    
    # Test 3: Try with different parameters
    print("\n3. Testing with minimal parameters...")
    try:
        url = f"{base_url}/claims:search"
        params = {
            "key": api_key,
            "query": "test"
        }
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params)
            print(f"Minimal test Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"Minimal test success! Found {len(data.get('claims', []))} claims")
            else:
                print(f"Minimal test failed: {response.text[:200]}")
                
    except Exception as e:
        print(f"Minimal test Exception: {e}")

if __name__ == "__main__":
    asyncio.run(test_google_factcheck_api())
