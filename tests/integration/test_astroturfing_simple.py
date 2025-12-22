#!/usr/bin/env python3
"""Simple test for astroturfing detection"""

def detect_astroturfing_indicators(text: str, context: dict = None) -> dict:
    """Detect potential astroturfing indicators in text and context"""
    text_lower = text.lower()
    
    # 1. Coordinated Language Patterns
    coordinated_phrases = [
        "i'm just a regular person", "as a concerned citizen", "i'm not political but",
        "i've never posted before", "i usually don't comment", "i'm just sharing",
        "this needs to be shared", "everyone needs to know", "spread the word",
        "wake up people", "open your eyes", "the truth is out there",
        "they don't want you to know", "mainstream media won't tell you",
        "i'm not a bot", "i'm real", "this is not fake"
    ]
    
    found_coordinated = []
    for phrase in coordinated_phrases:
        if phrase in text_lower:
            found_coordinated.append(phrase)
    
    # 2. Emotional Manipulation Patterns
    emotional_triggers = [
        "outraged", "disgusted", "shocked", "appalled", "furious",
        "this is unacceptable", "how dare they", "i can't believe",
        "this is sick", "disgraceful", "unbelievable"
    ]
    
    found_emotional = []
    for trigger in emotional_triggers:
        if trigger in text_lower:
            found_emotional.append(trigger)
    
    # 3. Astroturfing Language Patterns
    astroturf_patterns = [
        "grassroots", "organic", "natural", "authentic", "genuine",
        "real people", "ordinary citizens", "regular folks",
        "the silent majority", "the real americans", "patriots",
        "we the people", "enough is enough", "time to act"
    ]
    
    found_astroturf = []
    for pattern in astroturf_patterns:
        if pattern in text_lower:
            found_astroturf.append(pattern)
    
    # 4. Suspicious Repetition Patterns
    words = text_lower.split()
    word_freq = {}
    for word in words:
        if len(word) > 3:  # Ignore short words
            word_freq[word] = word_freq.get(word, 0) + 1
    
    # Check for unusual repetition
    suspicious_repetition = []
    for word, count in word_freq.items():
        if count > 3 and len(word) > 5:  # Word appears more than 3 times
            suspicious_repetition.append(f"{word}({count}x)")
    
    # 5. Calculate astroturfing score
    score = 0
    if found_coordinated:
        score += len(found_coordinated) * 0.2
    if found_emotional:
        score += len(found_emotional) * 0.15
    if found_astroturf:
        score += len(found_astroturf) * 0.25
    if suspicious_repetition:
        score += len(suspicious_repetition) * 0.1
    
    return {
        "astroturfing_score": min(score, 1.0),
        "has_coordinated_language": len(found_coordinated) > 0,
        "coordinated_phrases": found_coordinated,
        "has_emotional_manipulation": len(found_emotional) > 0,
        "emotional_triggers": found_emotional,
        "has_astroturf_patterns": len(found_astroturf) > 0,
        "astroturf_patterns": found_astroturf,
        "has_suspicious_repetition": len(suspicious_repetition) > 0,
        "suspicious_repetition": suspicious_repetition,
        "is_likely_astroturfing": score > 0.6
    }

def test_astroturfing():
    print("Testing astroturfing detection...")
    
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
        astroturfing_analysis = detect_astroturfing_indicators(claim)
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
    test_astroturfing()
