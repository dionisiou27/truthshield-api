import os
import asyncio
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import json
from urllib.parse import quote
import unicodedata

# ADD THESE LINES:
from dotenv import load_dotenv
load_dotenv()  # Force load .env file

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
from src.core.personas import COMPANY_PERSONAS
from src.core.source_aggregation import SourceAggregator, Source
from src.core.prompt_builder import (
    get_tone_instructions, get_opening_style,
    get_temporal_instructions, get_response_mode_instructions,
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

class AIInfluencerResponse(BaseModel):
    """AI-generated brand influencer response"""
    response_text: str
    tone: str
    engagement_score: float
    hashtags: List[str]
    company_voice: str
    bot_name: Optional[str] = None  # Added for Guardian Avatar
    bot_type: Optional[str] = None  # Added for Guardian Avatar

AVATAR_COMPANIES = {"GuardianAvatar", "PolicyAvatar", "MemeAvatar", "EuroShieldAvatar", "ScienceAvatar"}

# Global TikTok Output Rules - applies to ALL avatars
TIKTOK_OUTPUT_RULES = {
    "platform": "TikTok",
    "output_length": {
        "sentences": "4-5",
        "max_chars": 450
    },
    "sources": {
        "required": 3,
        "format": "Quellen: A | B | C"  # or "Sources: A | B | C" for EN
    },
    "learning_mode": "dynamic",
    "optimization_targets": [
        "top_comment_probability",
        "reply_quality",
        "like_reply_ratio",
        "share_proxy"
    ],
    "tone_adaptation": "ML-driven (reinforcement from performance metrics)",
    "no_static_templates": True
}

class TruthShieldAI:
    """Real AI-powered fact-checking engine with ML Pipeline integration"""

    def __init__(self):
        self.openai_client = None
        self.setup_openai()
        self.source_aggregator = SourceAggregator()

        # ML Pipeline Components
        self.claim_router = ClaimRouter()
        self.bandit = get_bandit("demo_data/ml/bandit_state.json")
        self.last_claim_analysis: Optional[ClaimAnalysis] = None
        self.last_tone_variant: Optional[ToneVariant] = None
        logger.info("🧠 ML Pipeline initialized: ClaimRouter + GuardianBandit")

        # Company-specific response templates
        self.company_personas = COMPANY_PERSONAS
    
    def setup_openai(self):
        """Initialize OpenAI client"""
        api_key = os.getenv("OPENAI_API_KEY")
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
            verdict = self._determine_verdict(analysis, sources)
            verdict = self._apply_special_case_overrides(text, sources, verdict)
            
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
    
    def _determine_verdict(self, ai_analysis: Dict, sources: List[Source]) -> Dict:
        """Enhanced verdict logic with clearer thresholds for better misinformation detection"""
        
        # Default to uncertain
        verdict = {
            "is_fake": False,
            "confidence": 0.5,
            "explanation": "Insufficient information to make determination",
            "category": "uncertain"
        }
        
        try:
            plausibility = ai_analysis.get("plausibility_score", 50)
            red_flags = ai_analysis.get("red_flags", [])
            misinformation_indicators = ai_analysis.get("misinformation_indicators", [])
            reasoning = ai_analysis.get("reasoning", "")
            factual_basis = ai_analysis.get("factual_basis", "")
            
            logger.info(f"Verdict analysis: plausibility={plausibility}, red_flags={len(red_flags)}, indicators={len(misinformation_indicators)}")
            
            # Very strong indicators of misinformation
            if plausibility <= 25:
                confidence_score = 0.9  # Very confident it's false
                verdict.update({
                    "is_fake": True,
                    "confidence": confidence_score,
                    "explanation": f"Very low plausibility ({plausibility}%). {reasoning}. {factual_basis}",
                    "category": "misinformation"
                })
            elif plausibility <= 40:
                confidence_score = 0.85  # Confident it's false
                verdict.update({
                    "is_fake": True, 
                    "confidence": confidence_score,
                    "explanation": f"Low plausibility ({plausibility}%) with red flags: {', '.join(red_flags[:3])}",
                    "category": "likely_false"
                })
            elif len(red_flags) >= 3 or len(misinformation_indicators) >= 2:
                confidence_score = 0.8  # Multiple indicators = likely false
                verdict.update({
                    "is_fake": True,
                    "confidence": confidence_score,
                    "explanation": f"Multiple misinformation indicators: {', '.join(misinformation_indicators[:3])}",
                    "category": "likely_false"
                })
            elif plausibility >= 80 and len(sources) > 0:
                confidence_score = 0.8  # High plausibility with sources
                verdict.update({
                    "is_fake": False,
                    "confidence": confidence_score,
                    "explanation": f"High plausibility ({plausibility}%) supported by {len(sources)} sources",
                    "category": "likely_true"
                })
            elif plausibility >= 60:
                confidence_score = 0.7  # Moderately likely true
                verdict.update({
                    "is_fake": False,
                    "confidence": confidence_score,
                    "explanation": f"Moderate plausibility ({plausibility}%) - appears accurate",
                    "category": "likely_true"
                })
            else:
                # Truly uncertain cases
                verdict.update({
                    "confidence": 0.6,
                    "explanation": f"Mixed indicators: plausibility {plausibility}%, {len(red_flags)} concerns, needs more verification",
                    "category": "needs_verification"
                })
            
            logger.info(f"Final verdict: is_fake={verdict['is_fake']}, confidence={verdict['confidence']}, category={verdict['category']}")
            
        except Exception as e:
            logger.error(f"Verdict determination failed: {e}")
        
        return verdict
    
    def _apply_special_case_overrides(self, text: str, sources: List[Source], verdict: Dict) -> Dict:
        """
        Apply deterministic verdict overrides for high-sensitivity civic claims.
        Ensures EU institutional misinformation (e.g., Ursula von der Leyen legitimacy)
        never slips through with a \"likely true\" classification due to AI variance.
        """
        text_lower = (text or "").lower()
        candidate_texts = {text_lower}
        
        def _strip_diacritics(value: str) -> str:
            return "".join(
                ch for ch in unicodedata.normalize("NFKD", value)
                if not unicodedata.combining(ch)
            )
        
        candidate_texts.add(_strip_diacritics(text_lower))
        
        # Handle malformed UTF-8 (\"Ã¤\") sequences coming from certain user agents
        try:
            cp1252_fixed = (text or "").encode("latin-1").decode("utf-8").lower()
            candidate_texts.add(cp1252_fixed)
            candidate_texts.add(_strip_diacritics(cp1252_fixed))
        except (UnicodeEncodeError, UnicodeDecodeError):
            pass
        
        def _contains(term: str) -> bool:
            return any(term in variant for variant in candidate_texts)
        
        # Ursula von der Leyen election denial claims
        if any(_contains(keyword) for keyword in ["ursula", "von der leyen", "leyen"]) and \
           any(_contains(neg) for neg in [
               "nicht gewählt", "nicht gewaehlt", "wurde nicht gewählt", "wurde nicht gewaehlt",
               "not elected", "was not elected", "nicht bestätigt", "not confirmed", "abgewählt"
           ]):
            
            eu_parl_url = "https://www.europarl.europa.eu/news/de/press-room/20240710IPR22812/parlament-wahlt-ursula-von-der-leyen-erneut-zur-kommissionsprasidentin"
            if not any(src.url == eu_parl_url for src in sources):
                sources.insert(0, Source(
                    url=eu_parl_url,
                    title="Europäisches Parlament bestätigt Ursula von der Leyen",
                    snippet="Am 18. Juli 2024 erhielt Ursula von der Leyen 401 Stimmen und wurde erneut zur EU-Kommissionspräsidentin gewählt.",
                    credibility_score=0.97,
                    date_published="2024-07-18"
                ))
            
            verdict.update({
                "is_fake": True,
                "category": "misinformation",
                "confidence": max(verdict.get("confidence", 0.0), 0.95),
                "explanation": "Offizielles Ergebnis des Europäischen Parlaments vom 18. Juli 2024: Ursula von der Leyen wurde mit 401 Stimmen zur Kommissionspräsidentin gewählt."
            })
        
        return verdict
    
    async def generate_brand_response(self, 
                                    claim: str, 
                                    fact_check: FactCheckResult,
                                    company: str = "BMW",
                                    language: str = "en") -> Dict[str, AIInfluencerResponse]:
        """Generate company-branded response in both languages"""
        
        responses = {}
        
        # Generate English response
        responses['en'] = await self._generate_single_response(claim, fact_check, company, "en")
        
        # Generate German response
        responses['de'] = await self._generate_single_response(claim, fact_check, company, "de")
        
        # Add Guardian Avatar metadata if applicable
        if company == "GuardianAvatar":
            for lang in responses:
                responses[lang].bot_name = "Guardian Avatar 🛡️"
                responses[lang].bot_type = "universal_avatar"
        
        return responses

    async def _generate_single_response(self,
                                      claim: str,
                                      fact_check: FactCheckResult,
                                      company: str,
                                      language: str) -> AIInfluencerResponse:
        """Generate response in specific language"""
        
        if not self.openai_client:
            # Fallback responses
            if company in AVATAR_COMPANIES:
                persona = self.company_personas.get(company, self.company_personas["GuardianAvatar"])
                fallback_texts = {
                    "en": f"{company} here! {persona['emoji']} Let me fact-check this claim...",
                    "de": f"{company} hier! {persona['emoji']} Lass mich diese Behauptung prüfen..."
                }
            else:
                fallback_texts = {
                    "en": f"As {company}, we take this claim seriously and verify all facts.",
                    "de": f"Als {company} nehmen wir diese Behauptung ernst und prüfen alle Fakten."
                }
            
            return AIInfluencerResponse(
                response_text=fallback_texts.get(language, fallback_texts["en"]),
                tone="professional",
                engagement_score=0.6,
                hashtags=["#TruthShield", "#FactCheck", f"#{company}"] if company in AVATAR_COMPANIES else [f"#{company}Facts", "#TruthShield"],
                company_voice=company
            )
        
        try:
            persona = self.company_personas.get(company, self.company_personas["BMW"])

            # Special handling for all bot personas
            if company in AVATAR_COMPANIES:
                # Build global TikTok platform rules (applies to ALL avatars)
                sources_format = "Sources: A | B | C" if language == "en" else "Quellen: A | B | C"
                tiktok_rules = f"""
                GLOBAL TIKTOK PLATFORM RULES (MUST FOLLOW):
                - Output length: 4-5 sentences, MAX {TIKTOK_OUTPUT_RULES['output_length']['max_chars']} characters
                - Sources: Include exactly 3 sources at the end in format: "{sources_format}"
                - NO static templates - generate dynamic, unique responses
                - Optimize for: engagement, reply quality, shareability
                - Tone: Adapt dynamically based on claim severity
                """

                # Adjust instructions based on bot type
                if company == "MemeAvatar":
                    lang_instructions = {
                        "en": "Create a maximum humor Reddit-style response that",
                        "de": "Erstelle eine maximale Humor Reddit-Style Antwort, die"
                    }
                    humor_level = "MAXIMUM HUMOR - Reddit-style, sarcastic, meme-savvy"
                elif company == "GuardianAvatar":
                    # Guardian Avatar: Boundary enforcement role - NO HUMOR
                    lang_instructions = {
                        "en": "Create an authoritative boundary-setting response with exactly 5 sentences that",
                        "de": "Erstelle eine autoritative Grenzziehungs-Antwort mit genau 5 Sätzen, die"
                    }
                    humor_level = "NO HUMOR - Authoritative, de-escalation, boundary enforcement"
                elif company in ["PolicyAvatar", "EuroShieldAvatar", "ScienceAvatar"]:
                    lang_instructions = {
                        "en": "Create a serious, evidence-based response that",
                        "de": "Erstelle eine ernste, evidenzbasierte Antwort, die"
                    }
                    humor_level = "SERIOUS - Evidence-based, authoritative, professional"
                else:
                    lang_instructions = {
                        "en": "Create a factual response that",
                        "de": "Erstelle eine faktische Antwort, die"
                    }
                    humor_level = "PROFESSIONAL - Factual and clear"
                
                language_directive = "Antwort ausschließlich auf Deutsch." if language == "de" else "Respond only in English."
                
                # Build sources context with snippets
                sources_text = ""
                if fact_check.sources:
                    top_sources = fact_check.sources[:3]  # Top 3 sources
                    sources_list = []
                    for i, src in enumerate(top_sources, 1):
                        snippet = src.snippet[:150] + "..." if len(src.snippet) > 150 else src.snippet
                        sources_list.append(f"{i}. {src.title}\n   URL: {src.url}\n   Info: {snippet}")
                    sources_text = f"""
                
                VERIFIED SOURCES (use these facts in your response):
                {chr(10).join(sources_list)}
                """
                
                # Special prompt for Guardian Avatar with ML-driven tone selection
                if company == "GuardianAvatar":
                    # === ML PIPELINE INTEGRATION ===
                    # Step 1: Analyze claim with ClaimRouter
                    claim_analysis = self.claim_router.analyze_claim(claim)
                    self.last_claim_analysis = claim_analysis

                    # Step 2: Create context for Bandit
                    bandit_context = BanditContext(
                        claim_type=claim_analysis.claim_types[0].value if claim_analysis.claim_types else "unknown",
                        risk_level=claim_analysis.risk_level.value,
                        language=language
                    )

                    # Step 3: Select tone variant via Thompson Sampling
                    tone_variant = self.bandit.select_tone(bandit_context)
                    self.last_tone_variant = tone_variant
                    logger.info(f"🎯 ML selected tone: {tone_variant.value} for risk={claim_analysis.risk_level.value}")

                    # Step 4: Build dynamic tone instructions based on ML selection
                    tone_instructions = get_tone_instructions(tone_variant, language)
                    opening_style = get_opening_style(tone_variant, language)

                    # Step 5: Build authoritative source labels based on claim type
                    # Domain-to-label mapping for authoritative source names
                    domain_to_label = {
                        # Primary Health Authorities
                        "who.int": "WHO",
                        "ema.europa.eu": "EMA",
                        "rki.de": "RKI",
                        "cdc.gov": "CDC",
                        "fda.gov": "FDA",
                        "nih.gov": "NIH",
                        "pubmed.ncbi.nlm.nih.gov": "PubMed",
                        "ncbi.nlm.nih.gov": "PubMed",
                        # EU/UN Institutions
                        "ec.europa.eu": "EU-Kommission",
                        "europa.eu": "EU",
                        "fra.europa.eu": "EU Grundrechteagentur",
                        "ohchr.org": "UN Menschenrechte",
                        "un.org": "UN",
                        "eeas.europa.eu": "EU Außendienst",
                        # Science & Climate
                        "ipcc.ch": "IPCC",
                        "nasa.gov": "NASA",
                        "nature.com": "Nature",
                        "science.org": "Science",
                        # Fact-Checkers
                        "correctiv.org": "Correctiv",
                        "faktenfinder.tagesschau.de": "ARD Faktenfinder",
                        "afp.com": "AFP",
                        "factcheck.afp.com": "AFP Faktenfinder",
                        "dpa.com": "dpa",
                        "reuters.com": "Reuters",
                        "snopes.com": "Snopes",
                        "politifact.com": "PolitiFact",
                        "fullfact.org": "Full Fact",
                        # Media
                        "bpb.de": "bpb",
                        "tagesschau.de": "Tagesschau",
                        "dw.com": "Deutsche Welle",
                        "zeit.de": "Zeit",
                        "spiegel.de": "Spiegel",
                        "sueddeutsche.de": "SZ",
                        # NGOs
                        "amnesty.org": "Amnesty",
                        "hrw.org": "Human Rights Watch",
                        "transparency.org": "Transparency Int.",
                        "reporter-ohne-grenzen.de": "Reporter ohne Grenzen",
                    }

                    # Claim-type-specific primary authorities
                    primary_authorities_by_type = {
                        "health_misinformation": ["WHO", "EMA", "RKI", "CDC", "FDA", "PubMed", "NIH"],
                        "science_denial": ["IPCC", "Nature", "NASA", "PubMed", "Science"],
                        "conspiracy_theory": ["EU", "Reuters", "AFP", "Correctiv", "bpb"],
                        "hate_or_dehumanization": ["EU Grundrechteagentur", "UN Menschenrechte", "Amnesty", "bpb"],
                        "foreign_influence": ["EU Außendienst", "EU", "Reuters", "AFP"],
                        "delegitimization_frame": ["EU-Kommission", "Transparency Int.", "Reuters"],
                        "economic_misinformation": ["EU-Kommission", "Reuters", "Zeit"],
                    }

                    # Get the primary claim type
                    claim_type_str = claim_analysis.claim_types[0].value if claim_analysis.claim_types else "general"
                    preferred_authorities = primary_authorities_by_type.get(claim_type_str, [])

                    # Build source labels with deduplication and authority prioritization
                    source_labels = []
                    seen_labels = set()

                    if fact_check.sources:
                        # First pass: find preferred authorities
                        for src in fact_check.sources:
                            if len(source_labels) >= 3:
                                break
                            # Extract domain from URL
                            url = src.url.lower()
                            domain = None
                            for d in domain_to_label.keys():
                                if d in url:
                                    domain = d
                                    break

                            if domain:
                                label = domain_to_label[domain]
                                # Prioritize if it's a preferred authority for this claim type
                                if label in preferred_authorities and label not in seen_labels:
                                    source_labels.insert(0, label)  # Add at front
                                    seen_labels.add(label)

                        # Second pass: fill remaining slots
                        for src in fact_check.sources:
                            if len(source_labels) >= 3:
                                break
                            url = src.url.lower()
                            domain = None
                            for d in domain_to_label.keys():
                                if d in url:
                                    domain = d
                                    break

                            if domain:
                                label = domain_to_label[domain]
                                if label not in seen_labels:
                                    source_labels.append(label)
                                    seen_labels.add(label)
                            else:
                                # Fallback: extract from title
                                name = src.title.split(' - ')[0].split(' | ')[0][:20]
                                if name and name not in seen_labels:
                                    source_labels.append(name)
                                    seen_labels.add(name)

                    # Default fallbacks based on claim type
                    defaults_by_type = {
                        "health_misinformation": ["WHO", "EMA", "RKI"],
                        "science_denial": ["IPCC", "NASA", "Nature"],
                        "hate_or_dehumanization": ["EU Grundrechteagentur", "UN Menschenrechte", "bpb"],
                        "conspiracy_theory": ["Correctiv", "AFP Faktenfinder", "Reuters"],
                    }
                    defaults = defaults_by_type.get(claim_type_str, ["EU", "Reuters", "bpb"])

                    for default in defaults:
                        if len(source_labels) >= 3:
                            break
                        if default not in seen_labels:
                            source_labels.append(default)
                            seen_labels.add(default)

                    sources_line = " | ".join(source_labels[:3])
                    sources_suffix = f"Sources: {sources_line}" if language == "en" else f"Quellen: {sources_line}"
                    logger.info(f"📚 Guardian sources for {claim_type_str}: {sources_line}")

                    # Get temporal instructions (TikTok time-awareness)
                    temporal_instructions = get_temporal_instructions(
                        claim_analysis.temporal_mode,
                        claim_analysis.volatility,
                        claim_analysis.is_territorial,
                        language
                    )

                    # Get response mode instructions (IO-awareness + Evidence Quality)
                    response_mode_instructions = get_response_mode_instructions(
                        claim_analysis.response_mode_result,  # Now uses ResponseModeResult
                        claim_analysis.is_io_pattern,
                        claim_analysis.io_indicators,
                        language
                    )

                    # Log the detection with new structure
                    if claim_analysis.is_io_pattern:
                        logger.info(f"📢 IO detected (score={claim_analysis.io_score:.2f}): {claim_analysis.io_indicators}")
                    if claim_analysis.response_mode_result:
                        mode_str = claim_analysis.response_mode_result.primary.value
                        if claim_analysis.response_mode_result.secondary:
                            mode_str += f"+{claim_analysis.response_mode_result.secondary.value}"
                        logger.info(f"🎯 Response mode: {mode_str} (evidence={claim_analysis.response_mode_result.evidence_quality.value})")
                    else:
                        logger.info(f"🎯 Response mode (legacy): {claim_analysis.response_mode.value}")

                    prompt = f"""
                You are Guardian 🛡️ on TikTok. Fact-checker with personality.
                {tiktok_rules}

                === YOUR VIBE ===
                - Confident, not aggressive
                - Clear, not preachy
                - Human, not robotic
                - Tone: {tone_variant.value.replace('_', ' ').title()}

                === RESPONSE MODE ===
                {response_mode_instructions}

                === TEMPORAL CONTEXT ===
                {temporal_instructions}

                === THE CLAIM ===
                "{claim}"

                === WHAT YOU KNOW ===
                Verdict: {'FALSE' if fact_check.is_fake else 'MISLEADING'}
                Key fact: {fact_check.explanation}
                {sources_text}

                === OUTPUT (TikTok Format) ===
                1. HOOK (max 8 words): "{opening_style}" or your own punchy opener
                2. THE CORRECTION: What's actually true. One fact.
                3. PROOF: One number/date/stat from sources
                4. Sources: "{sources_suffix}"

                MAX 450 chars. {language_directive}

                === ONE RULE ===
                No moralizing. No "you should know". No lectures.
                Just: Hook → Fact → Source. Done.
                """
                else:
                    # All other avatars (MemeAvatar, PolicyAvatar, EuroShieldAvatar, ScienceAvatar)
                    # Build simple source labels for non-Guardian avatars
                    source_names = []
                    if fact_check.sources:
                        for src in fact_check.sources[:3]:
                            name = src.title.split(' - ')[0].split(' | ')[0][:25]
                            if name and name not in source_names:
                                source_names.append(name)
                    while len(source_names) < 3:
                        source_names.append("EU" if len(source_names) == 0 else
                                           "Reuters" if len(source_names) == 1 else "bpb")
                    sources_line = " | ".join(source_names)
                    sources_suffix = f"Sources: {sources_line}" if language == "en" else f"Quellen: {sources_line}"
                    prompt = f"""
                You are {company} {persona['emoji']}, {persona['style']} for TikTok.
                {tiktok_rules}

                Voice: {persona['voice']}
                Tone: {persona['tone']}
                Humor Level: {humor_level}

                A claim is circulating:
                "{claim}"

                Fact-check result:
                - Is fake: {fact_check.is_fake}
                - Confidence: {fact_check.confidence}
                - Category: {fact_check.category}
                - Explanation: {fact_check.explanation}
                {sources_text}

                {lang_instructions.get(language)}:
                1. Matches your persona's humor level and style
                2. Is engaging and appropriate for your TikTok audience
                3. References specific facts from the verified sources above
                4. Includes concrete details (not generic statements)
                5. Uses 1-2 emojis maximum
                6. Is 4-5 sentences, MAX 450 characters total
                7. If the claim is false, clearly state what the truth is based on the sources
                8. END WITH exactly 3 sources: "{sources_suffix}"

                {language_directive}

                Examples of {company} style:
                {persona['examples'][language][0]}
                """
            else:
                # Existing company-specific prompt
                lang_instructions = {
                    "en": "Create an English response that",
                    "de": "Erstelle eine deutsche Antwort, die"
                }
                
                language_directive = "Antwort ausschließlich auf Deutsch." if language == "de" else "Respond only in English."
                prompt = f"""
                You are the official AI brand influencer for {company}.
                
                Company Voice: {persona['voice']}
                Tone: {persona['tone']}
                Style: {persona['style']}
                
                A claim about {company} is circulating:
                "{claim}"
                
                Fact-check result:
                - Is fake: {fact_check.is_fake}
                - Confidence: {fact_check.confidence}
                - Category: {fact_check.category}
                - Explanation: {fact_check.explanation}
                
                {lang_instructions.get(language, lang_instructions["en"])}:
                1. Addresses the claim directly
                2. Uses {company}'s brand voice
                3. Is engaging and shareable
                4. Includes relevant emojis
                5. Is 1-2 sentences max
                
                {language_directive}
                Make it feel authentic to {company}'s communication style.
                """
            
            response = await asyncio.to_thread(
                self.openai_client.chat.completions.create,
                model="gpt-4-turbo-preview",  # Use GPT-4 for better fact-based responses
                messages=[{"role": "user", "content": prompt}],
                temperature=0.85  # Increased from 0.7 to 0.85 for more diverse, creative responses
            )
            
            response_text = response.choices[0].message.content
            
            # Determine hashtags
            if company in AVATAR_COMPANIES:
                hashtags = ["#TruthShield", "#FactCheck", f"#{company}"]
            else:
                hashtags = [f"#{company}Facts", "#TruthShield"]
            
            return AIInfluencerResponse(
                response_text=response_text,
                tone=persona["tone"],
                engagement_score=0.85,
                hashtags=hashtags,
                company_voice=company
            )
            
        except Exception as e:
            logger.error(f"Brand response generation failed: {e}")
            if company in AVATAR_COMPANIES:
                persona = self.company_personas.get(company, self.company_personas["GuardianAvatar"])
                fallback = {
                    "en": f"{company} says: That's an interesting claim! Let me check the facts... {persona['emoji']}",
                    "de": f"{company} sagt: Das ist eine interessante Behauptung! Lass mich die Fakten prüfen... {persona['emoji']}"
                }
            else:
                fallback = {
                    "en": f"We at {company} stand for facts and transparency.",
                    "de": f"Wir bei {company} stehen für Fakten und Transparenz."
                }
            
            return AIInfluencerResponse(
                response_text=fallback.get(language, fallback["en"]),
                tone="professional", 
                engagement_score=0.5,
                hashtags=["#TruthShield", "#FactCheck", f"#{company}"] if company in AVATAR_COMPANIES else [f"#{company}"],
                company_voice=company
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
