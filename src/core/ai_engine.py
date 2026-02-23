import asyncio
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import json
from urllib.parse import quote
import unicodedata

import httpx
import openai
from bs4 import BeautifulSoup
from pydantic import BaseModel

# ML Pipeline Integration
from src.ml.guardian.claim_router import (
    ClaimRouter, ClaimAnalysis, ClaimType, RiskLevel,
    ClaimVolatility, TemporalMode, ResponseMode,
    ResponseModeResult, EvidenceQuality,
)
from src.ml.learning.bandit import (
    GuardianBandit, BanditContext, ToneVariant, SourceMixStrategy, get_bandit
)
from src.core.config import settings
from src.core.personas import COMPANY_PERSONAS
from src.core.source_aggregation import SourceAggregator, Source
from src.core.verdict import determine_verdict, apply_special_case_overrides
from src.core.prompt_builder import (
    get_tone_instructions, get_opening_style,
    get_temporal_instructions, get_response_mode_instructions,
)
from src.core.response_builder import (
    ResponseBuilder, AIInfluencerResponse, AVATAR_COMPANIES, TIKTOK_OUTPUT_RULES,
)
from src.core.text_detection import (
    detect_political_astroturfing,
    detect_astroturfing_indicators,
    detect_logical_contradictions,
)

logger = logging.getLogger(__name__)

class FactCheckResult(BaseModel):
    """Fact-checking analysis result"""
    is_fake: bool
    confidence: float
    explanation: str
    category: str  # "misinformation", "satire", "misleading", "true"
    sources: List[Source] = []
    processing_time_ms: int

class TruthShieldAI:
    """Real AI-powered fact-checking engine with ML Pipeline integration"""

    def __init__(self):
        self.openai_client = None
        self.setup_openai()
        self.source_aggregator = SourceAggregator()

        # ML Pipeline Components
        self.claim_router = ClaimRouter()
        self.bandit = get_bandit("demo_data/ml/bandit_state.json")
        logger.info("🧠 ML Pipeline initialized: ClaimRouter + GuardianBandit")

        # Company-specific response templates
        self.company_personas = COMPANY_PERSONAS

        # Response builder (extracted P3.7)
        self.response_builder = ResponseBuilder(
            openai_client=self.openai_client,
            claim_router=self.claim_router,
            bandit=self.bandit,
            company_personas=self.company_personas,
        )

    @property
    def last_claim_analysis(self) -> Optional[ClaimAnalysis]:
        return self.response_builder.last_claim_analysis

    @property
    def last_tone_variant(self) -> Optional[ToneVariant]:
        return self.response_builder.last_tone_variant

    def setup_openai(self):
        """Initialize OpenAI client"""
        api_key = settings.openai_api_key
        if not api_key:
            logger.warning("⚠️ OPENAI_API_KEY not found - fact-checking will be limited")
            return

        try:
            self.openai_client = openai.OpenAI(api_key=api_key)
            logger.info("✅ OpenAI client initialized")
        except Exception as e:
            logger.error(f"❌ OpenAI setup failed: {e}")

    async def fact_check_claim(self, text: str, company: str = "BMW") -> FactCheckResult:
        """Main fact-checking pipeline"""
        start_time = datetime.now()

        try:
            # Step 1: Analyze claim with AI
            analysis = await self._analyze_with_ai(text, company)

            # Step 2: Search for supporting sources
            sources = await self.source_aggregator.search_sources(text, company)

            # Step 3: Determine final verdict
            verdict = determine_verdict(analysis, sources)
            verdict = apply_special_case_overrides(text, sources, verdict)

            processing_time = (datetime.now() - start_time).total_seconds() * 1000

            return FactCheckResult(
                is_fake=verdict["is_fake"],
                confidence=verdict["confidence"],
                explanation=verdict["explanation"],
                category=verdict["category"],
                sources=sources,
                processing_time_ms=int(processing_time)
            )

        except Exception as e:
            logger.error(f"Fact-checking failed: {e}")
            # Return safe fallback
            return FactCheckResult(
                is_fake=False,
                confidence=0.3,
                explanation="Unable to verify claim - analysis inconclusive",
                category="unknown",
                sources=[],
                processing_time_ms=1000
            )

    def _detect_political_astroturfing(self, text_lower: str) -> Dict[str, any]:
        """Detect specific political astroturfing patterns"""
        return detect_political_astroturfing(text_lower)

    def _detect_astroturfing_indicators(self, text: str, context: Dict = None) -> Dict[str, any]:
        """Detect potential astroturfing indicators in text and context"""
        return detect_astroturfing_indicators(text, context)

    def _detect_logical_contradictions(self, text: str) -> Dict[str, any]:
        """Detect logical contradictions in the text"""
        return detect_logical_contradictions(text)

    async def _analyze_with_ai(self, text: str, company: str = "BMW") -> Dict:
        """Enhanced AI analysis with better prompting for clear misinformation detection"""
        if not self.openai_client:
            return {"assessment": "limited", "reasoning": "No AI available"}

        # First check for logical contradictions and astroturfing
        contradiction_analysis = self._detect_logical_contradictions(text)
        astroturfing_analysis = self._detect_astroturfing_indicators(text)

        try:
            # Adjust prompt based on company type
            if company in AVATAR_COMPANIES:
                # Universal fact-checking prompt for all bot personas
                # Add contradiction and astroturfing context to prompt
                contradiction_context = ""
                if contradiction_analysis["has_contradictions"]:
                    contradiction_context = f"""

                ⚠️ LOGICAL CONTRADICTION DETECTED:
                This claim contains contradictory terms: {', '.join(contradiction_analysis['contradictions'])}
                This makes the claim logically impossible and should be flagged as misinformation.
                """
                elif contradiction_analysis["has_ambiguous_phrasing"]:
                    contradiction_context = f"""

                ⚠️ AMBIGUOUS PHRASING DETECTED:
                This claim uses confusing language: {', '.join(contradiction_analysis['ambiguous_phrases'])}
                This appears to be intentionally misleading and should be flagged as misinformation.
                """

                astroturfing_context = ""
                if astroturfing_analysis["is_likely_astroturfing"]:
                    astroturfing_context = f"""

                🎭 ASTROTURFING INDICATORS DETECTED:
                This content shows signs of coordinated disinformation (astroturfing):
                - Coordinated language: {', '.join(astroturfing_analysis['coordinated_phrases'])}
                - Emotional manipulation: {', '.join(astroturfing_analysis['emotional_triggers'])}
                - Astroturf patterns: {', '.join(astroturfing_analysis['astroturf_patterns'])}
                - Suspicious repetition: {', '.join(astroturfing_analysis['suspicious_repetition'])}
                This appears to be artificially manufactured "grassroots" content and should be flagged as coordinated disinformation.
                """

                # Get persona info
                persona = self.company_personas.get(company, self.company_personas["GuardianAvatar"])

                prompt = f"""
                You are {company}, a {persona['style']}.

                Voice: {persona['voice']}
                Tone: {persona['tone']}

                Analyze this claim for factual accuracy:
                "{text}"
                {contradiction_context}
                {astroturfing_context}

                ANALYSIS CRITERIA:
                1. Is this claim supported by verifiable facts?
                2. Are there sensational/inflammatory terms without basis?
                3. Does this contradict established scientific/historical knowledge?
                4. Would believing this cause harm or spread fear?
                5. Does this contain logical contradictions (e.g., "dead and alive", "true and false")?
                6. Is this claim intentionally ambiguous or confusing?
                7. Does this show signs of coordinated disinformation (astroturfing)?
                8. Is this artificially manufactured "grassroots" content?

                Be DECISIVE in your assessment. Common misinformation includes:
                - Conspiracy theories (moon landing, flat earth, chemtrails)
                - Health misinformation (miracle cures, vaccine myths)
                - Political disinformation
                - Urban legends presented as fact
                - LOGICAL CONTRADICTIONS (dead/alive, true/false, etc.)
                - Intentionally ambiguous statements designed to confuse

                Respond with JSON:
                {{
                    "is_verifiable": true/false,
                    "plausibility_score": 0-100,
                    "red_flags": ["list", "of", "concerns"],
                    "verification_needed": "what to check",
                    "reasoning": "clear explanation",
                    "misinformation_indicators": ["list", "of", "indicators"],
                    "factual_basis": "what we actually know"
                }}

                Be confident - don't default to 50/50 for clearly false claims.
                """
            else:
                # Company-specific prompt (existing code)
                persona = self.company_personas.get(company, self.company_personas["BMW"])
                prompt = f"""
                You are an expert fact-checker specializing in {company} and German industry claims.

                Analyze this claim for factual accuracy:
                "{text}"

                CONTEXT KNOWLEDGE for {company}:
                - Electric vehicles (BMW i3, i4, iX) are extensively tested in extreme cold
                - BMW conducts winter testing at -40°C in Arjeplog, Sweden annually
                - EV batteries lose range in cold but DO NOT "explode"
                - Thermal management systems prevent dangerous overheating/cooling
                - No documented cases of EV explosions due to cold weather

                ANALYSIS CRITERIA:
                1. Does this contradict established facts about {company}?
                2. Are there inflammatory/sensational terms without basis?
                3. Does this spread unfounded fear about the technology?
                4. Would this claim damage the company's reputation unfairly?

                Respond with JSON:
                {{
                    "is_verifiable": true,
                    "plausibility_score": 0-100,
                    "red_flags": ["list", "of", "red", "flags"],
                    "verification_needed": "specific verification needed",
                    "reasoning": "detailed reasoning",
                    "misinformation_indicators": ["list", "of", "indicators"],
                    "factual_basis": "established facts"
                }}
                """

            response = await asyncio.to_thread(
                self.openai_client.chat.completions.create,
                model="gpt-4-turbo-preview",  # Use GPT-4 for better analysis
                messages=[
                    {
                        "role": "system",
                        "content": f"You are {company}, a {persona['style']}. Be decisive in identifying clear misinformation. Use factual knowledge and reasoning. IMPORTANT: Respond ONLY with valid JSON, no markdown, no code blocks, no explanation."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,  # Lower temperature for more consistent responses
                response_format={"type": "json_object"}  # Force JSON response
            )

            content = response.choices[0].message.content
            # Clean up potential markdown code blocks
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            content = content.strip()
            result = json.loads(content)

            # Override plausibility score for logical contradictions
            if contradiction_analysis["has_contradictions"] or contradiction_analysis["has_ambiguous_phrasing"]:
                result["plausibility_score"] = 0  # Logically impossible
                result["red_flags"] = result.get("red_flags", []) + ["logical_contradiction"]
                result["misinformation_indicators"] = result.get("misinformation_indicators", []) + ["contradictory_claim"]
                result["reasoning"] = f"LOGICAL CONTRADICTION: {result.get('reasoning', '')} This claim contains contradictory terms that make it logically impossible."

            # Override plausibility score for astroturfing
            elif astroturfing_analysis["is_likely_astroturfing"]:
                result["plausibility_score"] = max(0, result.get("plausibility_score", 50) - 40)  # Reduce by 40 points
                result["red_flags"] = result.get("red_flags", []) + ["astroturfing_indicators"]
                result["misinformation_indicators"] = result.get("misinformation_indicators", []) + ["coordinated_disinformation"]
                result["reasoning"] = f"ASTROTURFING DETECTED: {result.get('reasoning', '')} This content shows signs of coordinated disinformation with artificial 'grassroots' language patterns."

            # Special handling for political astroturfing
            political_astroturfing = astroturfing_analysis.get("political_astroturfing", {})
            if political_astroturfing.get("is_political_astroturfing", False):
                result["plausibility_score"] = 5  # Very low plausibility for political astroturfing
                result["red_flags"] = result.get("red_flags", []) + ["political_astroturfing", "unsubstantiated_corruption_claims"]
                result["misinformation_indicators"] = result.get("misinformation_indicators", []) + ["coordinated_political_smear", "astroturfing"]

                # Differentiate between elected and appointed officials
                if political_astroturfing.get("targets_elected_politician", False):
                    result["reasoning"] = f"POLITICAL ASTROTURFING DETECTED: This appears to be coordinated disinformation targeting elected politicians with unsubstantiated corruption claims. {result.get('reasoning', '')}"
                elif political_astroturfing.get("targets_appointed_official", False):
                    result["reasoning"] = f"POLITICAL ASTROTURFING DETECTED: This appears to be coordinated disinformation targeting appointed officials with unsubstantiated corruption claims. Note: Appointed officials have less direct democratic legitimacy than elected politicians. {result.get('reasoning', '')}"
                else:
                    result["reasoning"] = f"POLITICAL ASTROTURFING DETECTED: This appears to be coordinated disinformation targeting legitimate politicians with unsubstantiated corruption claims. {result.get('reasoning', '')}"

            return result

        except Exception as e:
            logger.error(f"AI analysis failed: {e}")
            return {
                "assessment": "error",
                "reasoning": str(e),
                "plausibility_score": 50,
                "red_flags": [],
                "misinformation_indicators": []
            }

    async def generate_brand_response(self,
                                    claim: str,
                                    fact_check: FactCheckResult,
                                    company: str = "BMW",
                                    language: str = "en") -> Dict[str, AIInfluencerResponse]:
        """Generate company-branded response in both languages"""
        return await self.response_builder.generate_brand_response(
            claim, fact_check, company, language
        )

    def translate_fact_check_result(self, result: FactCheckResult) -> Dict[str, str]:
        """Quick translation of fact check results for demo"""

        translations = {
            "misinformation": "Fehlinformation",
            "likely_false": "wahrscheinlich falsch",
            "likely_true": "wahrscheinlich wahr",
            "needs_verification": "benötigt Überprüfung",
            "uncertain": "unklar",
            "true": "wahr",
            "false": "falsch"
        }

        # Translate explanation
        explanation_de = result.explanation
        for en, de in translations.items():
            explanation_de = explanation_de.replace(en, de)

        # Common phrase translations
        phrase_translations = {
            "Very low plausibility": "Sehr geringe Plausibilität",
            "Low plausibility": "Geringe Plausibilität",
            "Multiple misinformation indicators": "Mehrere Fehlinformationsindikatoren",
            "High plausibility": "Hohe Plausibilität",
            "supported by": "unterstützt von",
            "sources": "Quellen"
        }

        for en, de in phrase_translations.items():
            explanation_de = explanation_de.replace(en, de)

        return {
            "category_de": translations.get(result.category, result.category),
            "explanation_de": explanation_de
        }

# Global AI engine instance
ai_engine = TruthShieldAI()
