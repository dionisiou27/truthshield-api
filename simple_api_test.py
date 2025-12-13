"""Simple API Test - No Emojis"""
import asyncio
import sys
from src.core.ai_engine import TruthShieldAI
from src.core.config import settings

async def main():
    print("="*80)
    print("API SOURCE TEST")
    print("="*80)

    # Check API Keys
    print("\nAPI KEY STATUS:")
    print(f"  OpenAI: {'YES' if settings.openai_api_key else 'NO'}")
    print(f"  Google: {'YES' if settings.google_api_key else 'NO'}")
    print(f"  NewsAPI: {'YES' if settings.news_api_key else 'NO'}")
    print(f"  ClaimBuster: {'YES' if settings.claimbuster_api_key else 'NO'}")

    # Test source search
    print("\nTESTING SOURCE SEARCH:")
    ai_engine = TruthShieldAI()

    test_claim = "Ursula von der Leyen was not elected"
    print(f"Test claim: '{test_claim}'")

    try:
        sources = await ai_engine._search_sources(test_claim, "GuardianAvatar")
        print(f"\nTotal sources found: {len(sources)}")

        print("\nSOURCE LIST:")
        for i, src in enumerate(sources, 1):
            print(f"\n  [{i}] {src.title[:60]}")
            print(f"      URL: {src.url}")
            print(f"      Credibility: {src.credibility_score}")

        # Check API usage
        if hasattr(ai_engine, 'last_api_usage'):
            print("\n\nAPI USAGE DETAILS:")
            usage = ai_engine.last_api_usage
            for api_name, data in usage.items():
                if isinstance(data, dict):
                    print(f"\n  {api_name}:")
                    print(f"    Available: {data.get('available', False)}")
                    print(f"    Called: {data.get('called', False)}")
                    print(f"    Results: {data.get('results', 0)}")
                    if data.get('error'):
                        print(f"    Error: {data['error']}")

        # Test different personas
        print("\n\n" + "="*80)
        print("PERSONA SOURCE TEST")
        print("="*80)

        personas = {
            "ScienceAvatar": "COVID-19 vaccines",
            "PolicyAvatar": "election results",
            "EuroShieldAvatar": "EU policy",
        }

        for persona, claim in personas.items():
            print(f"\n{persona}: '{claim}'")
            sources = await ai_engine._search_sources(claim, persona)
            print(f"  Sources: {len(sources)}")

            # Show unique domains
            domains = set()
            for src in sources:
                domain = src.url.split('/')[2] if '/' in src.url else src.url
                domains.add(domain)
            print(f"  Unique domains: {', '.join(list(domains)[:5])}")

            # Check for persona-specific sources
            science_domains = ['nature.com', 'science.org', 'who.int']
            policy_domains = ['factcheck.org', 'politifact.com', 'meta.wikimedia.org']
            eu_domains = ['europa.eu', 'europarl.europa.eu']

            found_specific = False
            if persona == "ScienceAvatar":
                found_specific = any(d in str(domains) for d in science_domains)
            elif persona == "PolicyAvatar":
                found_specific = any(d in str(domains) for d in policy_domains)
            elif persona == "EuroShieldAvatar":
                found_specific = any(d in str(domains) for d in eu_domains)

            print(f"  Persona-specific sources: {'YES' if found_specific else 'NO'}")

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "="*80)
    print("TEST COMPLETE")
    print("="*80)

if __name__ == "__main__":
    asyncio.run(main())
