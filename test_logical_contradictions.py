#!/usr/bin/env python3
"""Test logical contradiction detection"""

import asyncio
from src.core.ai_engine import TruthShieldAI

async def test_logical_contradictions():
    print("Testing logical contradiction detection...")
    
    ai = TruthShieldAI()
    
    # Test various contradictory claims
    test_claims = [
        "Charlie Kirk is not Dead and alive",
        "This statement is true and false",
        "The vaccine is safe and dangerous",
        "The moon landing happened and didn't happen",
        "This is real and fake news",
        "The earth is flat and round",
        "Water is wet and dry"
    ]
    
    for claim in test_claims:
        print(f"\n--- Testing: {claim} ---")
        
        # Test contradiction detection
        contradiction_analysis = ai._detect_logical_contradictions(claim)
        print(f"Has contradictions: {contradiction_analysis['has_contradictions']}")
        print(f"Has ambiguous phrasing: {contradiction_analysis['has_ambiguous_phrasing']}")
        print(f"Logical consistency score: {contradiction_analysis['logical_consistency_score']}")
        
        if contradiction_analysis['contradictions']:
            print(f"Contradictions found: {contradiction_analysis['contradictions']}")
        if contradiction_analysis['ambiguous_phrases']:
            print(f"Ambiguous phrases: {contradiction_analysis['ambiguous_phrases']}")

if __name__ == "__main__":
    asyncio.run(test_logical_contradictions())
