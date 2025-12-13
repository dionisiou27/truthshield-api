"""
Comprehensive API Source Testing
Tests all configured APIs and analyzes source diversity per persona
"""

import asyncio
import json
from src.core.ai_engine import TruthShieldAI, AVATAR_COMPANIES
from src.core.config import settings

async def test_api_availability():
    """Test which APIs are actually configured and functional"""
    print("=" * 80)
    print("API AVAILABILITY TEST")
    print("=" * 80)

    # Check API Keys
    api_status = {
        "OpenAI": settings.openai_api_key is not None and settings.openai_api_key != "",
        "Google Fact Check": settings.google_api_key is not None and settings.google_api_key != "your_google_api_key_here",
        "NewsAPI": settings.news_api_key is not None and settings.news_api_key != "your_news_api_key_here",
        "ClaimBuster": settings.claimbuster_api_key is not None and settings.claimbuster_api_key != "your_claimbuster_api_key_here",
    }

    print("\n[*] API KEY STATUS:")
    for api_name, is_configured in api_status.items():
        status = "[OK] CONFIGURED" if is_configured else "[X] NOT CONFIGURED"
        print(f"  {api_name}: {status}")

    # Test actual API calls
    print("\n\n[*] TESTING API ENDPOINTS:")
    ai_engine = TruthShieldAI()

    test_claim = "Ursula von der Leyen was not elected"

    try:
        sources = await ai_engine._search_sources(test_claim, "GuardianAvatar")

        print(f"\n  Total sources returned: {len(sources)}")

        # Group by source type
        source_types = {}
        for source in sources:
            source_url = source.url.lower()

            if "factcheck" in source_url:
                source_type = "Fact-Checker"
            elif "google" in source_url or "claimbuster" in source_url:
                source_type = "API Result"
            elif "wikipedia" in source_url or "wikidata" in source_url:
                source_type = "MediaWiki"
            elif "snopes" in source_url or "correctiv" in source_url or "mimikama" in source_url:
                source_type = "Static Fallback"
            elif "europa.eu" in source_url or "europarl" in source_url:
                source_type = "Primary Source"
            else:
                source_type = "Other"

            if source_type not in source_types:
                source_types[source_type] = []
            source_types[source_type].append(source)

        print("\n  📊 Sources by Type:")
        for source_type, type_sources in source_types.items():
            print(f"    {source_type}: {len(type_sources)}")
            for src in type_sources[:2]:  # Show first 2 of each type
                print(f"      - {src.title[:60]}...")
                print(f"        URL: {src.url}")

        # Check API usage metadata
        if hasattr(ai_engine, 'last_api_usage'):
            print("\n  📡 API CALL DETAILS:")
            usage = ai_engine.last_api_usage
            for api_name, api_data in usage.items():
                if isinstance(api_data, dict):
                    available = api_data.get('available', False)
                    called = api_data.get('called', False)
                    results = api_data.get('results', 0)
                    error = api_data.get('error')

                    print(f"    {api_name}:")
                    print(f"      Available: {available}")
                    print(f"      Called: {called}")
                    print(f"      Results: {results}")
                    if error:
                        print(f"      Error: {error}")
                elif api_name == "fallback_sources_added":
                    print(f"    Fallback sources added: {api_data}")

    except Exception as e:
        print(f"  ❌ Error during source search: {e}")
        import traceback
        traceback.print_exc()

    return api_status

async def test_persona_source_routing():
    """Test if different personas use different sources"""
    print("\n\n" + "=" * 80)
    print("PERSONA-SPECIFIC SOURCE ROUTING TEST")
    print("=" * 80)

    ai_engine = TruthShieldAI()

    test_claims = {
        "ScienceAvatar": "COVID-19 vaccines cause autism",
        "PolicyAvatar": "Ursula von der Leyen was not elected",
        "EuroShieldAvatar": "The EU is planning to ban all cars",
        "MemeAvatar": "5G causes coronavirus",
        "GuardianAvatar": "Climate change is a hoax"
    }

    persona_sources = {}

    for persona, claim in test_claims.items():
        print(f"\n\n🤖 Testing {persona}:")
        print(f"   Claim: \"{claim}\"")
        print(f"   Expected sources: {_get_expected_sources(persona)}")

        try:
            sources = await ai_engine._search_sources(claim, persona)
            persona_sources[persona] = sources

            print(f"   Total sources: {len(sources)}")

            # Analyze source diversity
            source_domains = set()
            primary_sources = []
            secondary_sources = []
            api_sources = []

            for source in sources:
                domain = _extract_domain(source.url)
                source_domains.add(domain)

                # Categorize
                if any(s in source.url.lower() for s in ["nature.com", "science.org", "who.int", "europa.eu", "europarl", "reddit.com"]):
                    primary_sources.append(source)
                elif any(s in source.url.lower() for s in ["factcheck", "snopes", "correctiv", "mimikama"]):
                    secondary_sources.append(source)
                elif any(s in source.url.lower() for s in ["google", "claimbuster", "wikipedia", "wikidata"]):
                    api_sources.append(source)

            print(f"   Primary sources: {len(primary_sources)}")
            for src in primary_sources:
                print(f"     - {src.title[:50]}... ({_extract_domain(src.url)})")

            print(f"   Secondary sources: {len(secondary_sources)}")
            for src in secondary_sources[:2]:
                print(f"     - {src.title[:50]}... ({_extract_domain(src.url)})")

            print(f"   API sources: {len(api_sources)}")
            for src in api_sources[:2]:
                print(f"     - {src.title[:50]}... ({_extract_domain(src.url)})")

            print(f"   Unique domains: {len(source_domains)}")

        except Exception as e:
            print(f"   ❌ Error: {e}")

    # Compare persona diversity
    print("\n\n📊 PERSONA SOURCE DIVERSITY COMPARISON:")
    all_sources_equal = True
    first_persona_urls = set(s.url for s in list(persona_sources.values())[0]) if persona_sources else set()

    for persona, sources in persona_sources.items():
        current_urls = set(s.url for s in sources)
        if current_urls != first_persona_urls:
            all_sources_equal = False
            break

    if all_sources_equal and len(persona_sources) > 1:
        print("  ⚠️ WARNING: All personas are using IDENTICAL sources!")
        print("  ❌ Persona-specific source routing is NOT working properly")
    else:
        print("  ✅ Personas are using DIFFERENT sources (as expected)")

    return persona_sources

async def test_llm_output_diversity():
    """Test if LLM outputs are dynamic or static"""
    print("\n\n" + "=" * 80)
    print("LLM OUTPUT DIVERSITY TEST")
    print("=" * 80)

    ai_engine = TruthShieldAI()

    test_claim = "COVID-19 vaccines cause autism"
    persona = "GuardianAvatar"

    print(f"\n🧪 Testing same claim 3 times with {persona}:")
    print(f"   Claim: \"{test_claim}\"")

    responses = []

    for i in range(3):
        print(f"\n  Run #{i+1}:")
        try:
            # Simulate fact-check result
            from src.core.ai_engine import FactCheckResult, Source

            fact_check = FactCheckResult(
                is_fake=True,
                confidence=0.95,
                explanation="This claim has been debunked by multiple scientific studies",
                category="misinformation",
                sources=[
                    Source(
                        url="https://www.cdc.gov/vaccinesafety/concerns/autism.html",
                        title="CDC: Vaccines Do Not Cause Autism",
                        snippet="Multiple studies have shown no link between vaccines and autism",
                        credibility_score=0.95
                    )
                ],
                processing_time_ms=1000
            )

            response = await ai_engine.generate_brand_response(test_claim, fact_check, persona, "en")
            response_text = response['en'].response_text
            responses.append(response_text)

            print(f"    Response: {response_text[:100]}...")

        except Exception as e:
            print(f"    ❌ Error: {e}")

    # Analyze diversity
    print("\n  📊 DIVERSITY ANALYSIS:")
    unique_responses = len(set(responses))
    print(f"    Total runs: {len(responses)}")
    print(f"    Unique responses: {unique_responses}")

    if unique_responses == 1:
        print("    ❌ WARNING: All responses are IDENTICAL!")
        print("    The LLM output appears to be STATIC or highly deterministic")
    elif unique_responses < len(responses) * 0.7:
        print("    ⚠️  WARNING: Low diversity (< 70% unique)")
        print("    The LLM output has limited variation")
    else:
        print("    ✅ Good diversity - responses are varied")

    # Show differences
    if len(responses) >= 2:
        print("\n  📝 Response Comparison:")
        for i, resp in enumerate(responses, 1):
            print(f"    Response #{i}:")
            print(f"      {resp[:150]}...")

    return responses

def _get_expected_sources(persona):
    """Get expected source types for a persona"""
    expected = {
        "ScienceAvatar": "nature.com, science.org, who.int, pubmed",
        "PolicyAvatar": "factcheck.org, politifact.com, transparency.org, meta.wikimedia.org",
        "EuroShieldAvatar": "europa.eu, europarl.europa.eu, ec.europa.eu",
        "MemeAvatar": "reddit.com, outoftheloop",
        "GuardianAvatar": "factcheck.org, snopes.com"
    }
    return expected.get(persona, "general fact-checkers")

def _extract_domain(url):
    """Extract domain from URL"""
    from urllib.parse import urlparse
    parsed = urlparse(url)
    return parsed.netloc

async def main():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("TRUTHSHIELD API SOURCE ANALYSIS")
    print("=" * 80)

    # Test 1: API Availability
    api_status = await test_api_availability()

    # Test 2: Persona Source Routing
    persona_sources = await test_persona_source_routing()

    # Test 3: LLM Output Diversity
    if api_status.get("OpenAI", False):
        responses = await test_llm_output_diversity()
    else:
        print("\n\n⚠️  Skipping LLM diversity test (OpenAI API key not configured)")

    # Final Summary
    print("\n\n" + "=" * 80)
    print("📋 SUMMARY & RECOMMENDATIONS")
    print("=" * 80)

    issues_found = []

    # Check API configuration
    if not api_status.get("OpenAI", False):
        issues_found.append("❌ OpenAI API key not configured - AI responses will use fallback")
    if not api_status.get("NewsAPI", False):
        issues_found.append("⚠️  NewsAPI key not configured - missing news context")
    if not api_status.get("ClaimBuster", False):
        issues_found.append("⚠️  ClaimBuster API key not configured - missing claim scoring")

    # Check source diversity
    if persona_sources:
        first_persona_urls = set(s.url for s in list(persona_sources.values())[0])
        all_same = all(set(s.url for s in sources) == first_persona_urls for sources in persona_sources.values())
        if all_same:
            issues_found.append("❌ Persona-specific source routing NOT working - all personas use identical sources")

    if issues_found:
        print("\n🔍 Issues Found:")
        for issue in issues_found:
            print(f"  {issue}")
    else:
        print("\n✅ No major issues found!")

    print("\n📝 Recommendations:")
    print("  1. Configure missing API keys in .env file")
    print("  2. Verify persona-specific source selection is implemented")
    print("  3. Increase LLM temperature for more dynamic outputs")
    print("  4. Add more diverse primary sources per persona")
    print("  5. Implement actual API calls instead of static fallbacks")

if __name__ == "__main__":
    asyncio.run(main())
