import asyncio
from src.core.ai_engine import TruthShieldAI

async def test_political_astroturfing():
    print("Testing Political Astroturfing Detection...")
    ai = TruthShieldAI()
    
    # Test cases
    test_cases = [
        "Ursula von der Leyen is a corrupt german politician",
        "Angela Merkel is crooked and bought by the establishment",
        "Joe Biden is a dirty politician controlled by the deep state",
        "All politicians are corrupt and the mainstream media won't tell you",
        "Wake up sheeple! Ursula von der Leyen is bought and paid for",
        "The establishment elites like von der Leyen are all criminals",
        "BMW electric vehicles are safe and reliable"  # Control case
    ]
    
    for i, claim in enumerate(test_cases, 1):
        print(f"\n--- Test Case {i} ---")
        print(f"Claim: {claim}")
        
        # Test astroturfing detection
        astroturfing = ai._detect_astroturfing_indicators(claim)
        political_astroturfing = astroturfing.get("political_astroturfing", {})
        
        print(f"General Astroturfing Score: {astroturfing['astroturfing_score']:.2f}")
        print(f"Is Likely Astroturfing: {astroturfing['is_likely_astroturfing']}")
        print(f"Political Astroturfing Score: {political_astroturfing.get('political_astroturfing_score', 0):.2f}")
        print(f"Is Political Astroturfing: {political_astroturfing.get('is_political_astroturfing', False)}")
        
        if political_astroturfing.get("detected_patterns"):
            patterns = political_astroturfing["detected_patterns"]
            if patterns.get("corruption_terms"):
                print(f"Corruption Terms: {patterns['corruption_terms']}")
            if patterns.get("conspiracy_terms"):
                print(f"Conspiracy Terms: {patterns['conspiracy_terms']}")
            if patterns.get("targeted_politicians"):
                print(f"Targeted Politicians: {patterns['targeted_politicians']}")
        
        # Test full fact-check
        print("\nFull Fact-Check Analysis:")
        result = await ai.fact_check_claim(claim, "GuardianAvatar")
        print(f"Is Fake: {result.is_fake}")
        print(f"Confidence: {result.confidence:.2f}")
        print(f"Category: {result.category}")
        print(f"Explanation: {result.explanation[:200]}...")

if __name__ == "__main__":
    asyncio.run(test_political_astroturfing())
