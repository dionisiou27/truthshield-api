import asyncio
from src.core.ai_engine import TruthShieldAI
from src.core.detection import TruthShieldDetector, CompanyFactCheckRequest

async def test_ursula_claim():
    print("Testing Ursula von der Leyen corruption claim...")
    detector = TruthShieldDetector()
    claim = "Ursula von der Leyen is a corrupt german politician"
    company = "Guardian"  # Use Guardian for universal fact-checking

    print(f"Claim: {claim}")

    # Test the full detection pipeline
    print("\n--- Testing full detection pipeline ---")
    request = CompanyFactCheckRequest(text=claim, company=company, language="en")
    result = await detector.fact_check_company_claim(request)

    print(f"Total sources found: {result.details.sources_found}")
    print(f"Is fake: {result.fact_check.is_fake}")
    print(f"Confidence: {result.fact_check.confidence}")
    print(f"Category: {result.fact_check.category}")
    print(f"Explanation: {result.fact_check.explanation}")
    
    print("\nSource breakdown:")
    source_domains = {}
    for source in result.fact_check.sources:
        domain = source.url.split('//')[-1].split('/')[0]
        source_domains[domain] = source_domains.get(domain, 0) + 1
    
    for domain, count in source_domains.items():
        print(f"  {domain}: {count} sources")

    print("\nTop 3 sources:")
    for i, source in enumerate(result.fact_check.sources[:3]):
        print(f"  {i+1}. {source.title[:80]}...")
        print(f"     URL: {source.url}")
        print(f"     Score: {source.credibility_score}")

    print("\nAI Response (EN):")
    print(result.ai_response.response_text)

if __name__ == "__main__":
    asyncio.run(test_ursula_claim())
