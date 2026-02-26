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
from src.core.text_detection import (
    detect_political_astroturfing,
    detect_astroturfing_indicators,
    detect_logical_contradictions,
)

logger = logging.getLogger(__name__)

class Source(BaseModel):
    """Fact-checking source"""
    url: str
    title: str
    snippet: str
    credibility_score: float
    date_published: Optional[str] = None

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
        self.last_api_usage: Dict[str, Dict[str, Any]] = {}
        self.last_mediawiki_results: List[Dict[str, Any]] = []

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

    def _get_tone_instructions(self, tone_variant: ToneVariant, language: str) -> str:
        """
        Get dynamic tone instructions based on ML-selected variant.
        4 distinct tone buckets for real ML differentiation.
        """
        tone_configs = {
            ToneVariant.EMPATHIC: {
                "de": """
                VIBE: Verstehend, dann korrigierend. Du checkst die Angst/Sorge dahinter.
                HOOK: "Ich versteh die Sorge, aber..." / "Klingt scary, ist aber..."
                ENERGIE: Warm aber klar. Kein Mitleid, sondern Verständnis.
                BEISPIEL: "Ich versteh warum das beunruhigt. Aber hier sind die Fakten: [Zahl]. Checkt die Quelle."
                """,
                "en": """
                VIBE: Understanding first, then correcting. You get why people worry.
                HOOK: "I get why this sounds scary, but..." / "Makes sense to worry, but..."
                ENERGY: Warm but clear. Not pity, just understanding.
                EXAMPLE: "I get why this sounds scary. But here's what's actually true: [fact]. Check the source."
                """
            },
            ToneVariant.WITTY: {
                "de": """
                VIBE: Locker, selbstbewusst, leicht frech. Fakten mit Persönlichkeit.
                HOOK: "Nope." / "Ähm, ne." / "Plot twist:"
                ENERGIE: Entspannt-überlegen. Kein Stress, nur Klarheit.
                BEISPIEL: "Nope. Was wirklich passiert ist: [Fakt]. Easy zu checken."
                """,
                "en": """
                VIBE: Casual, confident, slightly cheeky. Facts with personality.
                HOOK: "Nope." / "Um, no." / "Plot twist:"
                ENERGY: Relaxed-confident. No stress, just clarity.
                EXAMPLE: "Nope. Here's what actually happened: [fact]. Easy to check."
                """
            },
            ToneVariant.FIRM: {
                "de": """
                VIBE: Direkt, keine Umwege. Fakt rein, fertig.
                HOOK: "Falsch." / "Das stimmt nicht." / "Die Daten zeigen:"
                ENERGIE: Sachlich-autoritär. Kein Raum für Diskussion.
                BEISPIEL: "Falsch. [Konkreter Fakt mit Zahl]. Quelle steht unten."
                """,
                "en": """
                VIBE: Direct, no detours. Fact in, done.
                HOOK: "False." / "That's not true." / "The data shows:"
                ENERGY: Matter-of-fact authoritative. No room for debate.
                EXAMPLE: "False. [Specific fact with number]. Source below."
                """
            },
            ToneVariant.SPICY: {
                "de": """
                VIBE: Bold, etwas provokant, aber faktisch korrekt. Weckt auf.
                HOOK: "Wilder Take." / "Reality Check:" / "Uff, ne."
                ENERGIE: Selbstbewusst-frech. Bricht die Bubble.
                BEISPIEL: "Wilder Take. Realität: [krasser Fakt]. Kannst du nachschauen."
                """,
                "en": """
                VIBE: Bold, slightly provocative, but factually correct. Wakes people up.
                HOOK: "Wild take." / "Reality check:" / "Oof, no."
                ENERGY: Confident-sassy. Breaks the bubble.
                EXAMPLE: "Wild take. Reality: [striking fact]. Look it up."
                """
            }
        }
        return tone_configs.get(tone_variant, tone_configs[ToneVariant.FIRM]).get(language, "en")

    def _get_opening_style(self, tone_variant: ToneVariant, language: str) -> str:
        """
        Get dynamic opening phrases based on ML-selected tone.
        Each bucket has distinct hooks - this is where ML learns what works.
        """
        openings = {
            ToneVariant.EMPATHIC: {
                "de": [
                    "Ich versteh die Sorge.",
                    "Klingt scary, aber:",
                    "Verständlich, dass das nervt.",
                    "Die Angst ist echt, aber:",
                ],
                "en": [
                    "I get why this sounds scary.",
                    "Makes sense to worry, but:",
                    "I hear you, but here's the thing:",
                    "The concern is real, but:",
                ]
            },
            ToneVariant.WITTY: {
                "de": [
                    "Nope.",
                    "Ähm, ne.",
                    "Plot twist:",
                    "Spoiler:",
                    "Kurze Unterbrechung:",
                ],
                "en": [
                    "Nope.",
                    "Um, no.",
                    "Plot twist:",
                    "Spoiler alert:",
                    "Quick interruption:",
                ]
            },
            ToneVariant.FIRM: {
                "de": [
                    "Falsch.",
                    "Das stimmt nicht.",
                    "Die Daten zeigen:",
                    "Fakt:",
                    "Klarstellung:",
                ],
                "en": [
                    "False.",
                    "That's not true.",
                    "The data shows:",
                    "Fact:",
                    "Correction:",
                ]
            },
            ToneVariant.SPICY: {
                "de": [
                    "Wilder Take.",
                    "Reality Check:",
                    "Uff.",
                    "Bold move, aber:",
                    "Interessante Theorie.",
                ],
                "en": [
                    "Wild take.",
                    "Reality check:",
                    "Oof.",
                    "Bold claim, but:",
                    "Interesting theory.",
                ]
            }
        }
        import random
        options = openings.get(tone_variant, openings[ToneVariant.FIRM]).get(language, "en")
        return random.choice(options) if isinstance(options, list) else options

    def _get_temporal_instructions(
        self,
        temporal_mode: TemporalMode,
        volatility: ClaimVolatility,
        is_territorial: bool,
        language: str
    ) -> str:
        """
        Get time-aware response instructions based on claim volatility.
        Critical for TikTok where upload time ≠ claim time.
        """
        if temporal_mode == TemporalMode.LIVE_REQUIRED:
            if is_territorial:
                return {
                    "de": """
                    ⚡ ZEITKRITISCH: Territorial-Claim. Die Lage kann sich stündlich ändern.
                    - NIEMALS absolute Aussagen ("X kontrolliert Y")
                    - IMMER hedgen: "Nach aktuellen Berichten...", "Stand der letzten Meldungen..."
                    - Zeitliche Vorsicht: "Claims zur Gebietsrollen können sich schnell ändern"
                    """,
                    "en": """
                    ⚡ TIME-CRITICAL: Territorial claim. Situation can change hourly.
                    - NEVER make absolute statements ("X controls Y")
                    - ALWAYS hedge: "According to latest reports...", "As of recent updates..."
                    - Temporal caution: "Claims about territorial control change rapidly"
                    """
                }.get(language, "en")
            else:
                return {
                    "de": """
                    ⚡ LIVE-CHECK ERFORDERLICH: Volatile Situation.
                    - Vorsichtige Formulierung: "Nach aktuellen Informationen..."
                    - Keine absoluten Behauptungen
                    - Empfehlung: Aktuelle Quellen prüfen
                    """,
                    "en": """
                    ⚡ LIVE CHECK REQUIRED: Volatile situation.
                    - Cautious phrasing: "Based on current information..."
                    - No absolute claims
                    - Recommend: Check latest sources
                    """
                }.get(language, "en")

        elif temporal_mode == TemporalMode.AMBIGUOUS:
            return {
                "de": """
                ❓ ZEITLICH UNKLAR: Gemischte Signale.
                - Vorsichtig bleiben
                - Keine definitiven Aussagen
                - Bei Unsicherheit hedgen
                """,
                "en": """
                ❓ TEMPORALLY UNCLEAR: Mixed signals.
                - Stay cautious
                - No definitive statements
                - Hedge when uncertain
                """
            }.get(language, "en")

        # ARCHIVE_OK - can be more direct
        return {
            "de": "✅ Stabile Faktenlage. Direkte Aussagen möglich.",
            "en": "✅ Stable factual basis. Direct statements OK."
        }.get(language, "en")

    def _get_response_mode_instructions(
        self,
        response_mode_result: Optional[ResponseModeResult],
        is_io: bool,
        io_indicators: List[str],
        language: str
    ) -> str:
        """
        Get response framing instructions based on detected response mode.
        Now supports primary + secondary (overlay) modes.

        Routing Matrix:
        - CAUTIOUS > LIVE_SITUATION > IO_CONTEXT > DEBUNK
        - IO_CONTEXT can be overlay on LIVE_SITUATION
        """
        # Backwards compatibility: if no ResponseModeResult, use legacy logic
        if response_mode_result is None:
            return self._get_legacy_response_mode_instructions(
                ResponseMode.DEBUNK, is_io, io_indicators, language
            )

        primary = response_mode_result.primary
        secondary = response_mode_result.secondary
        evidence_quality = response_mode_result.evidence_quality
        io_score = response_mode_result.io_score

        instructions_parts = []

        # === EVIDENCE QUALITY WARNING (always first) ===
        if evidence_quality == EvidenceQuality.WEAK:
            instructions_parts.append({
                "de": """
⚠️ SCHWACHE EVIDENZLAGE
- Du MUSST Hedging verwenden: "nach verfügbaren Berichten", "stand jetzt"
- KEINE definitiven Aussagen
- Anerkenne Unsicherheit explizit
                """,
                "en": """
⚠️ WEAK EVIDENCE BASE
- You MUST use hedging: "according to available reports", "as of now"
- NO definitive statements
- Acknowledge uncertainty explicitly
                """
            }.get(language, "en"))

        # === PRIMARY MODE INSTRUCTIONS ===
        if primary == ResponseMode.CAUTIOUS:
            instructions_parts.append({
                "de": """
❓ VORSICHT-MODUS: Unklare Faktenlage.
- Hedging ist PFLICHT
- Keine definitiven Aussagen möglich
- Auf weitere Quellen verweisen
- "Die Sachlage ist nicht eindeutig geklärt..."
                """,
                "en": """
❓ CAUTION MODE: Unclear factual basis.
- Hedging is MANDATORY
- No definitive statements possible
- Refer to additional sources
- "The facts are not definitively established..."
                """
            }.get(language, "en"))

        elif primary == ResponseMode.LIVE_SITUATION:
            instructions_parts.append({
                "de": """
⚡ LIVE-SITUATION: Fakten sind fluid.
- Keine absoluten Aussagen über territoriale Kontrolle
- "Nach aktuellen Berichten...", "Stand der letzten Meldungen..."
- Die Lage ändert sich schnell
- Datum/Zeit des letzten Updates nennen wenn möglich
                """,
                "en": """
⚡ LIVE SITUATION: Facts are fluid.
- No absolute statements about territorial control
- "According to latest reports...", "As of recent updates..."
- Situation changes rapidly
- Mention date/time of last update if possible
                """
            }.get(language, "en"))

        elif primary == ResponseMode.IO_CONTEXT:
            instructions_parts.append({
                "de": f"""
📢 INFORMATIONSOPERATION ERKANNT (Score: {io_score:.2f})
Indikatoren: {', '.join(io_indicators) if io_indicators else 'Narrativ-Muster'}

WICHTIG: Dies ist KEIN einfacher Faktencheck.
Der Claim ist Teil einer koordinierten Narrative.

Deine Antwort MUSS:
1. Das Narrativ benennen, nicht nur den Fakt widerlegen
2. "Diese Behauptung ist Teil einer laufenden Informationskampagne..."
3. Kontext geben: WARUM wird das jetzt verbreitet?
4. Nuanciert bleiben: Teilwahrheiten anerkennen, Framing entlarven

NICHT: "Das ist falsch."
SONDERN: "Diese Behauptung zirkuliert im Rahmen einer Kampagne..."
                """,
                "en": f"""
📢 INFORMATION OPERATION DETECTED (Score: {io_score:.2f})
Indicators: {', '.join(io_indicators) if io_indicators else 'Narrative patterns'}

IMPORTANT: This is NOT a simple fact-check.
The claim is part of a coordinated narrative campaign.

Your response MUST:
1. Name the narrative, don't just refute the fact
2. "This claim is part of an ongoing information campaign..."
3. Give context: WHY is this being spread now?
4. Stay nuanced: Acknowledge partial truths, expose framing

NOT: "This is false."
BUT: "This claim circulates as part of a campaign..."
                """
            }.get(language, "en"))

        elif primary == ResponseMode.DEBUNK:
            instructions_parts.append({
                "de": "✅ Standard Faktencheck. Klare Aussagen erlaubt.",
                "en": "✅ Standard fact-check. Clear statements allowed."
            }.get(language, "en"))

        # === SECONDARY (OVERLAY) MODE INSTRUCTIONS ===
        if secondary == ResponseMode.IO_CONTEXT:
            # This is the key case: LIVE_SITUATION + IO_CONTEXT
            instructions_parts.append({
                "de": f"""
📢 ZUSÄTZLICH: IO-OVERLAY (Score: {io_score:.2f})
Indikatoren: {', '.join(io_indicators) if io_indicators else 'Narrativ-Muster'}

Diese Live-Situation wird im Rahmen einer IO instrumentalisiert.
- Nenne das Narrativ ZUSÄTZLICH zu den Live-Fakten
- "Diese sich schnell ändernde Lage wird im Rahmen einer Kampagne instrumentalisiert..."
- Trenne: Was wir wissen vs. Wie es geframed wird
                """,
                "en": f"""
📢 ADDITIONALLY: IO OVERLAY (Score: {io_score:.2f})
Indicators: {', '.join(io_indicators) if io_indicators else 'Narrative patterns'}

This live situation is being instrumentalized as part of an IO.
- Name the narrative IN ADDITION to live facts
- "This rapidly changing situation is being instrumentalized as part of a campaign..."
- Separate: What we know vs. How it's being framed
                """
            }.get(language, "en"))

        return "\n".join(instructions_parts)

    def _get_legacy_response_mode_instructions(
        self,
        response_mode: ResponseMode,
        is_io: bool,
        io_indicators: List[str],
        language: str
    ) -> str:
        """Legacy method for backwards compatibility."""
        if response_mode == ResponseMode.IO_CONTEXT:
            return {
                "de": f"""
📢 INFORMATIONSOPERATION ERKANNT
Indikatoren: {', '.join(io_indicators) if io_indicators else 'Narrativ-Muster'}
Der Claim ist Teil einer koordinierten Narrative.
                """,
                "en": f"""
📢 INFORMATION OPERATION DETECTED
Indicators: {', '.join(io_indicators) if io_indicators else 'Narrative patterns'}
The claim is part of a coordinated narrative campaign.
                """
            }.get(language, "en")

        elif response_mode == ResponseMode.LIVE_SITUATION:
            return {
                "de": "⚡ LIVE-SITUATION: Fakten sind fluid. Keine absoluten Aussagen.",
                "en": "⚡ LIVE SITUATION: Facts are fluid. No absolute statements."
            }.get(language, "en")

        elif response_mode == ResponseMode.CAUTIOUS:
            return {
                "de": "❓ VORSICHT: Unklare Faktenlage. Hedging verwenden.",
                "en": "❓ CAUTION: Unclear factual basis. Use hedging."
            }.get(language, "en")

        return {
            "de": "✅ Standard Faktencheck. Klare Aussagen erlaubt.",
            "en": "✅ Standard fact-check. Clear statements allowed."
        }.get(language, "en")

    async def fact_check_claim(self, text: str, company: str = "BMW") -> FactCheckResult:
        """Main fact-checking pipeline"""
        start_time = datetime.now()
        
        try:
            # Step 1: Analyze claim with AI
            analysis = await self._analyze_with_ai(text, company)
            
            # Step 2: Search for supporting sources  
            sources = await self._search_sources(text, company)
            
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
    
    async def _search_sources(self, query: str, company: str = "GuardianAvatar") -> List[Source]:
        """Search for sources to verify the claim using real fact-checking APIs and scrapers"""
        try:
            self.last_mediawiki_results = []
            # For political astroturfing claims, return minimal sources since they're not fact-checkable
            text_lower = query.lower()
            if any(politician in text_lower for politician in ["ursula", "von der leyen", "merkel", "biden", "trump", "macron"]):
                if any(term in text_lower for term in ["corrupt", "crooked", "dirty", "shady"]):
                    # This is likely political astroturfing - return minimal sources
                    return []
            
            # Trim overly long queries for site search endpoints
            truncated_query = (query or "").strip()
            if len(truncated_query) > 120:
                truncated_query = truncated_query[:120]

            # Detect language (very lightweight heuristic): 'de' if likely German, else 'en'
            def _detect_language(text: str) -> str:
                t = (text or "").lower()
                german_markers = ["ä", "ö", "ü", "ß", " der ", " die ", " das ", " und ", " nicht ", " ist ", " mit "]
                for m in german_markers:
                    if m in t:
                        return "de"
                return "en"

            detected_lang = _detect_language(truncated_query)
            logger.info(f"=== SEARCHING FOR: {truncated_query} (lang={detected_lang}) ===")
            
            # Check API availability
            from .config import settings
            google_api_available = bool(settings.google_api_key and settings.google_api_key != "your_google_api_key_here")
            news_api_available = bool(settings.news_api_key and settings.news_api_key != "your_news_api_key_here")
            claimbuster_api_available = bool(settings.claimbuster_api_key and settings.claimbuster_api_key != "your_claimbuster_api_key_here")
            api_usage = {
                "google_fact_check": {"available": google_api_available, "called": False, "results": 0, "error": None},
                "news_api": {"available": news_api_available, "called": False, "results": 0, "error": None},
                "claimbuster": {"available": claimbuster_api_available, "called": False, "results": 0, "error": None},
                "mediawiki": {"available": True, "called": False, "results": 0, "error": None},
                "fallback_sources_added": 0
            }
            logger.info(f"API Status - Google Fact Check: {'✅' if google_api_available else '❌'}, NewsAPI: {'✅' if news_api_available else '❌'}, ClaimBuster: {'✅' if claimbuster_api_available else '❌'}")
            
            # Start with real Google Fact Check API results
            sources = []
            
            # 🔍 REAL GOOGLE FACT CHECK API INTEGRATION
            if google_api_available:
                try:
                    from src.services.google_factcheck import search_google_factchecks
                    google_results = await search_google_factchecks(truncated_query, detected_lang)
                    api_usage["google_fact_check"]["called"] = True
                    
                    # Convert Google results to Source objects
                    for result in google_results[:5]:  # Max 5 Google results
                        source = Source(
                            url=result['url'],
                            title=result['title'],
                            snippet=result['snippet'],
                            credibility_score=result['credibility_score'],
                            date_published=result.get('date_published', '')
                        )
                        sources.append(source)
                        logger.info(f"✅ Google Fact Check: {result['publisher']} - {result['rating']}")
                    api_usage["google_fact_check"]["results"] = len(google_results)
                        
                except Exception as e:
                    logger.error(f"❌ Google Fact Check API error: {e}")
                    api_usage["google_fact_check"]["error"] = str(e)
            
            # 📰 REAL NEWS API INTEGRATION
            if news_api_available:
                try:
                    from src.services.news_api import search_news_context
                    news_results = await search_news_context(truncated_query, detected_lang)
                    api_usage["news_api"]["called"] = True
                    
                    # Convert News API results to Source objects
                    for result in news_results[:3]:  # Max 3 News results for context
                        source = Source(
                            url=result['url'],
                            title=result['title'],
                            snippet=result['snippet'],
                            credibility_score=result['credibility_score'],
                            date_published=result.get('published_at', '')
                        )
                        sources.append(source)
                        logger.info(f"✅ News Context: {result['source_name']} - {result['title'][:50]}...")
                    api_usage["news_api"]["results"] = len(news_results)
                        
                except Exception as e:
                    logger.error(f"❌ News API error: {e}")
                    api_usage["news_api"]["error"] = str(e)
            
            # 📘 MEDIAWIKI (Wikipedia + Wikidata) CONTEXT
            try:
                from src.services.wiki_api import search_mediawiki_sources
                wiki_results = await search_mediawiki_sources(truncated_query, detected_lang)
                if wiki_results:
                    api_usage["mediawiki"]["called"] = True
                    api_usage["mediawiki"]["results"] = len(wiki_results)
                    self.last_mediawiki_results = wiki_results
                    for result in wiki_results:
                        source = Source(
                            url=result["url"],
                            title=result["title"],
                            snippet=result.get("snippet", ""),
                            credibility_score=result.get("credibility", 0.8),
                            date_published=""
                        )
                        sources.append(source)
                        logger.info(f"📚 MediaWiki: {result['project']} - {result['title']}")
                else:
                    self.last_mediawiki_results = []
            except Exception as e:
                logger.error(f"❌ MediaWiki fetch error: {e}")
                api_usage["mediawiki"]["error"] = str(e)
                self.last_mediawiki_results = []
            
            # 🎯 REAL CLAIMBUSTER API INTEGRATION (Claim Scoring)
            if claimbuster_api_available:
                try:
                    from src.services.claimbuster_api import score_claim_worthiness
                    claimbuster_score = await score_claim_worthiness(truncated_query)
                    api_usage["claimbuster"]["called"] = True
                    
                    # Add ClaimBuster analysis as a source if claim-worthy
                    if claimbuster_score and claimbuster_score.get('claim_worthy', False):
                        score = claimbuster_score['max_score']
                        confidence = claimbuster_score['confidence']
                        
                        source = Source(
                            url='https://claimbuster.org',
                            title=f"ClaimBuster Analysis: Claim-worthy statement detected",
                            snippet=f"ClaimBuster scored this as claim-worthy (score: {score:.3f}, confidence: {confidence:.3f}). {claimbuster_score['claim_sentences']}/{claimbuster_score['total_sentences']} sentences contain factual claims requiring verification.",
                            credibility_score=0.85,  # ClaimBuster is high credibility
                            date_published=''
                        )
                        sources.append(source)
                        logger.info(f"✅ ClaimBuster: Claim-worthy detected (score: {score:.3f})")
                        api_usage["claimbuster"]["results"] = 1
                    else:
                        api_usage["claimbuster"]["results"] = 0
                        
                except Exception as e:
                    logger.error(f"❌ ClaimBuster API error: {e}")
                    api_usage["claimbuster"]["error"] = str(e)
            
            # Add bot-specific sources with primary/secondary prioritization
            try:
                prioritized_sources = self._get_prioritized_sources(query, company)
                sources.extend(prioritized_sources)
            except NameError:
                # Fallback if company parameter is not available
                logger.warning("Company parameter not available, skipping prioritized sources")
                pass
            
            # IMPROVED FALLBACK LOGIC: Only add fallbacks if we have 0 sources
            # This ensures we only use static fallbacks as last resort
            if len(sources) == 0:
                logger.warning(f"⚠️ No dynamic sources found for query, using static fallback sources as last resort")

                fallback_sources = [
                    Source(
                        url="https://www.factcheck.org",
                        title="FactCheck.org - Nonpartisan Fact-Checking",
                        snippet="Comprehensive fact-checking from the Annenberg Public Policy Center",
                        credibility_score=0.9,
                        date_published=""
                    ),
                    Source(
                        url="https://www.snopes.com",
                        title="Snopes - Fact-Checking and Debunking",
                        snippet="Urban legends, misinformation, and fact-checking since 1995",
                        credibility_score=0.85,
                        date_published=""
                    ),
                    Source(
                        url="https://correctiv.org",
                        title="CORRECTIV - Investigative Journalism",
                        snippet="German fact-checking and investigative journalism platform",
                        credibility_score=0.8,
                        date_published=""
                    )
                ]

                # Add up to 3 fallback sources
                for fallback in fallback_sources[:3]:
                    sources.append(fallback)
                    api_usage["fallback_sources_added"] += 1
                    logger.info(f"✅ Added static fallback: {fallback.title}")
            else:
                logger.info(f"✅ Found {len(sources)} dynamic sources - no fallbacks needed")
            
            logger.info(f"Final source count: {len(sources)}")
            self.last_api_usage = api_usage
            return sources
            
        except Exception as e:
            logger.error(f"Source search failed: {e}")
            self.last_api_usage = {"error": str(e)}
            return []
    
    def _get_prioritized_sources(self, query: str, company: str = "GuardianAvatar") -> List[Source]:
        """
        Get sources with bot-specific prioritization.
        Primary sources are checked first, then secondary sources as fallback.
        """
        sources = []
        text_lower = query.lower()
        
        # Define bot-specific source priorities
        bot_sources = {
            "EuroShieldAvatar": {
                "primary": [
                    Source(url="https://europa.eu/", title="European Union Official Website", 
                           snippet="Official EU information, policies, and legislative documents...", 
                           credibility_score=0.95, date_published="2024-01-01"),
                    Source(url="https://www.europarl.europa.eu/", title="European Parliament", 
                           snippet="Official European Parliament information and legislative procedures...", 
                           credibility_score=0.95, date_published="2024-01-01"),
                    Source(url="https://ec.europa.eu/", title="European Commission", 
                           snippet="Official European Commission policies, proposals, and official statements...", 
                           credibility_score=0.95, date_published="2024-01-01")
                ],
                "secondary": ["factcheckeu", "mimikama", "correctiv", "factcheck", "snopes"]
            },
            "MemeAvatar": {
                "primary": [
                    Source(url="https://www.reddit.com/r/", title="Reddit Community Discussions", 
                           snippet="Community-driven fact-checking and discussions on various topics...", 
                           credibility_score=0.7, date_published="2024-01-01"),
                    Source(url="https://www.reddit.com/r/OutOfTheLoop/", title="Reddit OutOfTheLoop", 
                           snippet="Community explanations and fact-checking of trending topics...", 
                           credibility_score=0.75, date_published="2024-01-01")
                ],
                "secondary": ["snopes", "factcheck", "mimikama", "correctiv", "wikipedia"]
            },
            "ScienceAvatar": {
                "primary": [
                    Source(url="https://www.nature.com/", title="Nature - Scientific Journal", 
                           snippet="Peer-reviewed scientific research and publications...", 
                           credibility_score=0.95, date_published="2024-01-01"),
                    Source(url="https://www.science.org/", title="Science Magazine", 
                           snippet="Leading scientific journal with peer-reviewed research...", 
                           credibility_score=0.95, date_published="2024-01-01"),
                    Source(url="https://www.who.int/", title="World Health Organization", 
                           snippet="Official WHO information on health topics and medical facts...", 
                           credibility_score=0.95, date_published="2024-01-01")
                ],
                "secondary": ["factcheck", "mimikama", "correctiv", "snopes", "wikipedia"]
            },
            "PolicyAvatar": {
                "primary": [
                    Source(url="https://www.factcheck.org/", title="FactCheck.org - Political Fact-Checking", 
                           snippet="Non-partisan fact-checking of political claims and statements...", 
                           credibility_score=0.9, date_published="2024-01-01"),
                    Source(url="https://www.politifact.com/", title="PolitiFact - Political Fact-Checking", 
                           snippet="Fact-checking political claims with Truth-O-Meter ratings...", 
                           credibility_score=0.9, date_published="2024-01-01"),
                    Source(url="https://www.transparency.org/", title="Transparency International", 
                           snippet="Global corruption perceptions and governance research...", 
                           credibility_score=0.95, date_published="2024-01-01"),
                    Source(url="https://meta.wikimedia.org/wiki/Public_policy", title="Meta-Wiki • Public policy & governance", 
                           snippet="Meta-Wiki's official hub for Wikimedia public policy, transparency, and governance initiatives.", 
                           credibility_score=0.82, date_published="2024-01-01")
                ],
                "secondary": ["mimikama", "correctiv", "snopes", "wikipedia", "factcheckeu"]
            },
            "GuardianAvatar": {
                "primary": [
                    Source(url="https://www.factcheck.org/", title="FactCheck.org",
                           snippet="Non-partisan fact-checking of political and social claims...",
                           credibility_score=0.9, date_published="2024-01-01"),
                    Source(url="https://correctiv.org/", title="Correctiv Faktencheck",
                           snippet="German investigative journalism and fact-checking...",
                           credibility_score=0.9, date_published="2024-01-01")
                ],
                "secondary": ["mimikama", "snopes", "wikipedia", "factcheckeu", "politifact"],
                # Claim-type-specific primary sources for Guardian
                "health_primaries": [
                    Source(url="https://www.who.int/", title="WHO - World Health Organization",
                           snippet="Official WHO health information, vaccine safety data, and disease guidance...",
                           credibility_score=0.98, date_published="2024-01-01"),
                    Source(url="https://www.ema.europa.eu/", title="EMA - European Medicines Agency",
                           snippet="EU regulatory authority for vaccine and medicine safety assessments...",
                           credibility_score=0.98, date_published="2024-01-01"),
                    Source(url="https://www.rki.de/", title="RKI - Robert Koch Institut",
                           snippet="Germany's federal disease control and vaccination recommendations...",
                           credibility_score=0.97, date_published="2024-01-01")
                ],
                "science_primaries": [
                    Source(url="https://www.ipcc.ch/", title="IPCC - Intergovernmental Panel on Climate Change",
                           snippet="UN body for assessing the science of climate change...",
                           credibility_score=0.98, date_published="2024-01-01"),
                    Source(url="https://www.nasa.gov/", title="NASA - National Aeronautics and Space Administration",
                           snippet="U.S. space agency with climate and earth science research...",
                           credibility_score=0.98, date_published="2024-01-01"),
                    Source(url="https://www.nature.com/", title="Nature - Scientific Journal",
                           snippet="Peer-reviewed scientific research and publications...",
                           credibility_score=0.95, date_published="2024-01-01")
                ],
                "eu_primaries": [
                    Source(url="https://www.europarl.europa.eu/", title="European Parliament",
                           snippet="Official European Parliament legislative records, votes, and resolutions...",
                           credibility_score=0.98, date_published="2024-01-01"),
                    Source(url="https://ec.europa.eu/", title="European Commission",
                           snippet="Official EU policies and legislative information...",
                           credibility_score=0.97, date_published="2024-01-01"),
                    Source(url="https://fra.europa.eu/", title="EU Agency for Fundamental Rights",
                           snippet="EU body monitoring fundamental rights and hate speech...",
                           credibility_score=0.97, date_published="2024-01-01")
                ]
            }
        }
        
        # Get avatar-specific sources or default to Guardian Avatar
        bot_config = bot_sources.get(company, bot_sources["GuardianAvatar"])

        # For GuardianAvatar: Check claim type and add appropriate primary authorities FIRST
        if company == "GuardianAvatar":
            # Health misinformation detection
            health_keywords = ["vaccine", "impf", "mrna", "covid", "corona", "virus", "medic", "health",
                               "microchip", "chip", "autism", "autis", "5g", "pfizer", "moderna", "biontech"]
            if any(kw in text_lower for kw in health_keywords):
                logger.info("🏥 Health claim detected - adding WHO/EMA/RKI as primary sources")
                sources.extend(bot_config.get("health_primaries", []))

            # Science denial detection
            science_keywords = ["climate", "klima", "earth", "erde", "evolution", "moon", "mond",
                                "flat", "flach", "nasa", "space", "weltraum", "co2", "warming"]
            if any(kw in text_lower for kw in science_keywords):
                logger.info("🔬 Science claim detected - adding IPCC/NASA/Nature as primary sources")
                sources.extend(bot_config.get("science_primaries", []))

            # EU/political claim detection
            eu_keywords = ["eu", "europa", "commission", "kommission", "brüssel", "brussels",
                           "merkel", "scholz", "macron", "von der leyen", "parliament", "parlam",
                           "europarl", "parlament", "abgeordnete", "fraktion"]
            if any(kw in text_lower for kw in eu_keywords):
                logger.info("🇪🇺 EU claim detected - adding EC/FRA as primary sources")
                sources.extend(bot_config.get("eu_primaries", []))

        # Always add primary sources
        sources.extend(bot_config["primary"])

        # Add secondary sources based on claim type
        secondary_sources = self._get_secondary_sources(text_lower, bot_config["secondary"])
        sources.extend(secondary_sources)

        return sources
    
    def _get_secondary_sources(self, text_lower: str, secondary_types: List[str]) -> List[Source]:
        """
        Get secondary sources based on claim type and available secondary source types.
        """
        sources = []
        
        # Define secondary source mappings
        secondary_source_map = {
            "factcheckeu": Source(url="https://www.factcheckeu.org/", title="FactCheckEU - European Fact-Checking", 
                                 snippet="Fact-checking European political claims and misinformation...", 
                                 credibility_score=0.9, date_published="2024-01-01"),
            "mimikama": Source(url="https://www.mimikama.at/", title="Mimikama - Austrian Fact-Checking", 
                              snippet="Austrian fact-checking organization specializing in EU and German misinformation...", 
                              credibility_score=0.85, date_published="2024-01-01"),
            "correctiv": Source(url="https://correctiv.org/", title="Correctiv - German Investigative Journalism", 
                               snippet="German investigative journalism and fact-checking organization...", 
                               credibility_score=0.9, date_published="2024-01-01"),
            "factcheck": Source(url="https://www.factcheck.org/", title="FactCheck.org", 
                               snippet="Non-partisan fact-checking of political and social claims...", 
                               credibility_score=0.9, date_published="2024-01-01"),
            "snopes": Source(url="https://www.snopes.com/", title="Snopes", 
                            snippet="Fact-checking urban legends, rumors, and misinformation...", 
                            credibility_score=0.85, date_published="2024-01-01"),
            "wikipedia": Source(url="https://en.wikipedia.org/wiki/Main_Page", title="Wikipedia", 
                               snippet="Collaborative encyclopedia with fact-checked information...", 
                               credibility_score=0.8, date_published="2024-01-01"),
            "politifact": Source(url="https://www.politifact.com/", title="PolitiFact - Political Fact-Checking", 
                                snippet="Fact-checking political claims with Truth-O-Meter ratings...", 
                                credibility_score=0.9, date_published="2024-01-01")
        }
        
        # Add up to 3 secondary sources based on claim type and available types
        added_count = 0
        for source_type in secondary_types:
            if added_count >= 3:
                break
                
            if source_type in secondary_source_map:
                sources.append(secondary_source_map[source_type])
                added_count += 1

        # Special handling for Ursula von der Leyen legitimacy claims
        if any(keyword in text_lower for keyword in ["ursula", "von der leyen", "leyen", "kommissionspräsidentin"]):
            eu_parliament_source = Source(
                url="https://www.europarl.europa.eu/news/de/press-room/20240710IPR22812/parlament-wahlt-ursula-von-der-leyen-erneut-zur-kommissionsprasidentin",
                title="Europäisches Parlament wählt Ursula von der Leyen erneut zur Kommissionspräsidentin",
                snippet="Am 18. Juli 2024 bestätigte das Europäische Parlament Ursula von der Leyen mit 401 Stimmen für eine zweite Amtszeit als EU-Kommissionspräsidentin.",
                credibility_score=0.97,
                date_published="2024-07-18"
            )
            if not any(src.url == eu_parliament_source.url for src in sources):
                sources.append(eu_parliament_source)
        
        return sources

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
                    tone_instructions = self._get_tone_instructions(tone_variant, language)
                    opening_style = self._get_opening_style(tone_variant, language)

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
                        "europarl.europa.eu": "Europäisches Parlament",
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
                    temporal_instructions = self._get_temporal_instructions(
                        claim_analysis.temporal_mode,
                        claim_analysis.volatility,
                        claim_analysis.is_territorial,
                        language
                    )

                    # Get response mode instructions (IO-awareness + Evidence Quality)
                    response_mode_instructions = self._get_response_mode_instructions(
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
                temperature=0.4  # Lowered: fact-checking accuracy > creative diversity
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
