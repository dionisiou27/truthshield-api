import asyncio
from src.core.ai_engine import TruthShieldAI

async def test_ursula_election_claim():
    print("Testing Ursula von der Leyen election claim...")
    ai = TruthShieldAI()
    
    # Test the claim that she is NOT elected
    claim = "Ursula von der Leyen is not elected politician"
    print(f"Claim: {claim}")
    
    # Test astroturfing detection
    astroturfing = ai._detect_astroturfing_indicators(claim)
    political_astroturfing = astroturfing.get("political_astroturfing", {})
    
    print(f"\nAstroturfing Analysis:")
    print(f"General Astroturfing Score: {astroturfing['astroturfing_score']:.2f}")
    print(f"Is Likely Astroturfing: {astroturfing['is_likely_astroturfing']}")
    print(f"Political Astroturfing Score: {political_astroturfing.get('political_astroturfing_score', 0):.2f}")
    print(f"Is Political Astroturfing: {political_astroturfing.get('is_political_astroturfing', False)}")
    print(f"Targets Elected Politician: {political_astroturfing.get('targets_elected_politician', False)}")
    print(f"Targets Appointed Official: {political_astroturfing.get('targets_appointed_official', False)}")
    
    if political_astroturfing.get("detected_patterns"):
        patterns = political_astroturfing["detected_patterns"]
        if patterns.get("targeted_elected"):
            print(f"Targeted Elected: {patterns['targeted_elected']}")
        if patterns.get("targeted_appointed"):
            print(f"Targeted Appointed: {patterns['targeted_appointed']}")
    
    # Test full fact-check
    print(f"\nFull Fact-Check Analysis:")
    result = await ai.fact_check_claim(claim, "Guardian")
    print(f"Is Fake: {result.is_fake}")
    print(f"Confidence: {result.confidence:.2f}")
    print(f"Category: {result.category}")
    print(f"Explanation: {result.explanation}")
    
    # Test AI response
    print(f"\nAI Response:")
    try:
        ai_response = await ai.generate_brand_response(claim, result, "Guardian", "en")
        print(f"Guardian Bot: {ai_response['en'].response_text}")
    except Exception as e:
        print(f"AI Response Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_ursula_election_claim())
