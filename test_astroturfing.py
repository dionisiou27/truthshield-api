#!/usr/bin/env python3
"""Test astroturfing detection"""

import asyncio
from src.core.ai_engine import TruthShieldAI

async def test_astroturfing_detection():
    print("Testing astroturfing detection...")
    
    ai = TruthShieldAI()
    
    # Test various astroturfing examples
    test_claims = [
        # Classic astroturfing
        "I'm just a regular person, but I'm outraged by this! As a concerned citizen, I've never posted before but this needs to be shared. Wake up people!",
        
        # Coordinated language
        "I'm not political but this is unacceptable. The mainstream media won't tell you the truth. We the people need to act now!",
        
        # Emotional manipulation
        "I'm disgusted and shocked by this! How dare they! This is sick and disgraceful. Everyone needs to know about this!",
        
        # Astroturf patterns
        "This is a grassroots movement of real people. Ordinary citizens like me are speaking out. The silent majority is finally waking up!",
        
        # Suspicious repetition
        "This is important. This is very important. This is extremely important. This needs attention. This deserves attention.",
        
        # Normal content (should not trigger)
        "I think the new policy has some good points but also some concerns that should be addressed.",
        
        # Mixed astroturfing
        "As a regular person, I'm not usually political, but this is outrageous! The truth is out there and they don't want you to know. Spread the word!"
    ]
    
    for i, claim in enumerate(test_claims):
        print(f"\n--- Test {i+1}: {claim[:60]}... ---")
        
        # Test astroturfing detection
        astroturfing_analysis = ai._detect_astroturfing_indicators(claim)
        print(f"Astroturfing Score: {astroturfing_analysis['astroturfing_score']:.2f}")
        print(f"Likely Astroturfing: {astroturfing_analysis['is_likely_astroturfing']}")
        
        if astroturfing_analysis['coordinated_phrases']:
            print(f"Coordinated phrases: {astroturfing_analysis['coordinated_phrases']}")
        if astroturfing_analysis['emotional_triggers']:
            print(f"Emotional triggers: {astroturfing_analysis['emotional_triggers']}")
        if astroturfing_analysis['astroturf_patterns']:
            print(f"Astroturf patterns: {astroturfing_analysis['astroturf_patterns']}")
        if astroturfing_analysis['suspicious_repetition']:
            print(f"Suspicious repetition: {astroturfing_analysis['suspicious_repetition']}")

if __name__ == "__main__":
    asyncio.run(test_astroturfing_detection())
