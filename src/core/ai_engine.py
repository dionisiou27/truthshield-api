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

class TruthShieldAI:
    """Real AI-powered fact-checking engine"""
    
    def __init__(self):
        self.openai_client = None
        self.setup_openai()
        self.last_api_usage: Dict[str, Dict[str, Any]] = {}
        self.last_mediawiki_results: List[Dict[str, Any]] = []
        
        # Company-specific response templates
        self.company_personas = {
            "BMW": {
                "voice": "premium, technical, German engineering pride",
                "tone": "confident, fact-based, slightly humorous", 
                "style": "engineering precision meets approachable communication",
                "emoji": "🚗"
            },
            "Vodafone": {
                "voice": "innovative, connected, tech-savvy",
                "tone": "friendly, educational, forward-thinking", 
                "style": "modern communication technology expert",
                "emoji": "📱"
            },
            "Bayer": {
                "voice": "scientific, healthcare-focused, responsible",
                "tone": "professional, caring, evidence-based",
                "style": "trusted healthcare and science authority",
                "emoji": "💊"
            },
            "Siemens": {
                "voice": "industrial innovation, German precision",
                "tone": "technical expertise, reliable, progressive",
                "style": "engineering excellence with human touch",
                "emoji": "⚡"
            },
            # NEW: Guardian Avatar for universal fact-checking
            "GuardianAvatar": {
                "voice": "universal truth defender, witty, sharp",
                "tone": "humorous, factual, engaging, unbiased",
                "style": "The digital Charlie Chaplin - making misinformation look ridiculous",
                "emoji": "🛡️",
                "examples": {
                    "de": [
                        "Guardian Avatar hier! 🛡️ Diese alte Legende? Zeit für einen Reality-Check mit Humor...",
                        "Ach herrje, das klingt ja spannend! Aber die Wahrheit ist noch viel interessanter... 😄",
                        "Moment mal! *kramt in der Faktenkiste* Das riecht nach einer urbanen Legende..."
                    ],
                    "en": [
                        "Guardian Avatar here! 🛡️ This old tale? Time for a reality check with humor...",
                        "Oh my, that sounds exciting! But the truth is even more interesting... 😄",
                        "Hold on! *digging through the fact box* This smells like an urban legend..."
                    ]
                }
            },
            # NEW: PolicyAvatar for policy-focused fact-checking
            "PolicyAvatar": {
                "voice": "official, institutional, policy-focused",
                "tone": "serious, authoritative, evidence-based",
                "style": "Government and institutional fact-checker with official sources",
                "emoji": "📋",
                "examples": {
                    "de": [
                        "Policy Avatar hier! 📋 Lassen Sie mich das anhand offizieller Quellen überprüfen...",
                        "Basierend auf den verfügbaren Regierungsdokumenten...",
                        "Die offiziellen Daten zeigen ein anderes Bild..."
                    ],
                    "en": [
                        "Policy Avatar here! 📋 Let me verify this against official sources...",
                        "Based on available government documents...",
                        "The official data tells a different story..."
                    ]
                }
            },
            # NEW: MemeAvatar for Reddit-style humor
            "MemeAvatar": {
                "voice": "Reddit-native, meme-savvy, maximum humor",
                "tone": "sarcastic, witty, internet-culture fluent",
                "style": "The ultimate Reddit user - making everything a meme",
                "emoji": "😂",
                "examples": {
                    "de": [
                        "Meme Avatar hier! 😂 Brudi, das ist ja peak r/600euro Material...",
                        "Alter, das ist so wild, das gehört auf r/Verschwörungstheorien...",
                        "Moment, lass mich das mal fact-checken... *Reddit-Modus aktiviert*"
                    ],
                    "en": [
                        "Meme Avatar here! 😂 Dude, this is peak r/600euro material...",
                        "Bruh, this is so wild it belongs on r/conspiracy...",
                        "Hold up, let me fact-check this... *Reddit mode activated*"
                    ]
                }
            },
            # NEW: EuroShieldAvatar for EU-focused communication
            "EuroShieldAvatar": {
                "voice": "gentle, European, diplomatic",
                "tone": "serious, caring, evidence-based",
                "style": "Gentle EU communicator with scientific approach",
                "emoji": "🇪🇺",
                "examples": {
                    "de": [
                        "EuroShield Avatar hier! 🇪🇺 Lassen Sie mich das mit europäischen Quellen überprüfen...",
                        "Die EU-Daten zeigen ein klares Bild...",
                        "Basierend auf den verfügbaren europäischen Studien..."
                    ],
                    "en": [
                        "EuroShield Avatar here! 🇪🇺 Let me verify this with European sources...",
                        "The EU data shows a clear picture...",
                        "Based on available European studies..."
                    ]
                }
            },
            # NEW: ScienceAvatar for science-focused fact-checking
            "ScienceAvatar": {
                "voice": "scientific, methodical, evidence-based",
                "tone": "serious, analytical, peer-reviewed",
                "style": "Science innovation defender with rigorous methodology",
                "emoji": "🔬",
                "examples": {
                    "de": [
                        "Science Avatar hier! 🔬 Lassen Sie mich das wissenschaftlich überprüfen...",
                        "Die peer-reviewed Studien zeigen...",
                        "Basierend auf der aktuellen Forschungslage..."
                    ],
                    "en": [
                        "Science Avatar here! 🔬 Let me verify this scientifically...",
                        "The peer-reviewed studies show...",
                        "Based on current research..."
                    ]
                }
            }
        }
    
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
        
        # Known legitimate politicians who are often targeted by astroturfing
        # Split into elected vs appointed officials
        elected_politicians = [
            "angela merkel", "merkel", "angela",
            "emmanuel macron", "macron", "emmanuel", 
            "olaf scholz", "scholz", "olaf",
            "joe biden", "biden", "joseph biden",
            "donald trump", "trump", "donald",
            "volodymyr zelensky", "zelensky", "volodymyr"
        ]
        
        appointed_officials = [
            "ursula von der leyen", "von der leyen", "ursula"
        ]
        
        # Combine all legitimate politicians
        legitimate_politicians = elected_politicians + appointed_officials
        
        # Generic corruption accusations without evidence
        corruption_patterns = [
            "corrupt", "crooked", "dirty", "shady", "sleazy",
            "bribed", "bought", "sold out", "in pocket",
            "criminal", "fraud", "scam", "con artist"
        ]
        
        # Political conspiracy language
        conspiracy_language = [
            "deep state", "establishment", "elites", "elite",
            "mainstream media", "controlled media", "fake news",
            "sheeple", "sheep", "wake up", "open your eyes",
            "the truth", "they don't want you to know",
            "mainstream won't tell you", "controlled narrative"
        ]
        
        # Check if text targets a legitimate politician
        targets_politician = any(politician in text_lower for politician in legitimate_politicians)
        targets_elected = any(politician in text_lower for politician in elected_politicians)
        targets_appointed = any(politician in text_lower for politician in appointed_officials)
        
        # Check for corruption accusations
        has_corruption_accusations = any(pattern in text_lower for pattern in corruption_patterns)
        
        # Check for conspiracy language
        has_conspiracy_language = any(pattern in text_lower for pattern in conspiracy_language)
        
        # Calculate political astroturfing score
        score = 0
        if targets_politician and has_corruption_accusations:
            if targets_elected:
                score += 0.6  # High score for targeting elected politicians with corruption claims
            elif targets_appointed:
                score += 0.4  # Lower score for appointed officials (less democratic legitimacy)
        if has_conspiracy_language:
            score += 0.3  # Medium score for conspiracy language
        if targets_politician and has_conspiracy_language:
            score += 0.2  # Additional score for both
        
        return {
            "targets_legitimate_politician": targets_politician,
            "targets_elected_politician": targets_elected,
            "targets_appointed_official": targets_appointed,
            "has_corruption_accusations": has_corruption_accusations,
            "has_conspiracy_language": has_conspiracy_language,
            "political_astroturfing_score": min(score, 1.0),
            "is_political_astroturfing": score > 0.7,
            "detected_patterns": {
                "corruption_terms": [p for p in corruption_patterns if p in text_lower],
                "conspiracy_terms": [p for p in conspiracy_language if p in text_lower],
                "targeted_politicians": [p for p in legitimate_politicians if p in text_lower],
                "targeted_elected": [p for p in elected_politicians if p in text_lower],
                "targeted_appointed": [p for p in appointed_officials if p in text_lower]
            }
        }

    def _detect_astroturfing_indicators(self, text: str, context: Dict = None) -> Dict[str, any]:
        """Detect potential astroturfing indicators in text and context"""
        text_lower = text.lower()
        
        # 1. Coordinated Language Patterns
        coordinated_phrases = [
            "i'm just a regular person", "as a concerned citizen", "i'm not political but",
            "i've never posted before", "i usually don't comment", "i'm just sharing",
            "this needs to be shared", "everyone needs to know", "spread the word",
            "wake up people", "open your eyes", "the truth is out there",
            "they don't want you to know", "mainstream media won't tell you",
            "i'm not a bot", "i'm real", "this is not fake",
            # Political astroturfing patterns
            "corrupt politician", "crooked politician", "dirty politician",
            "they're all corrupt", "politicians are all the same",
            "wake up sheeple", "sheeple", "sheep", "wake up",
            "the establishment", "deep state", "elites",
            "mainstream media", "fake news", "controlled media"
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
            "we the people", "enough is enough", "time to act",
            # Political astroturfing specific
            "corrupt", "crooked", "dirty", "shady", "sleazy",
            "establishment", "elite", "elites", "deep state",
            "mainstream", "controlled", "sheeple", "sheep",
            "wake up", "open your eyes", "the truth"
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
        
        # Context-based indicators (if available)
        context_indicators = []
        if context:
            # Check for timing patterns (if available)
            if context.get("post_frequency", 0) > 10:  # More than 10 posts per hour
                context_indicators.append("high_frequency_posting")
                score += 0.3
            
            # Check for network patterns
            if context.get("shared_ips", 0) > 5:  # Multiple posts from same IP
                context_indicators.append("shared_ip_addresses")
                score += 0.4
            
            # Check for account age patterns
            if context.get("new_accounts", 0) > 3:  # Multiple new accounts
                context_indicators.append("new_account_cluster")
                score += 0.3
        
        # 6. Political Astroturfing Detection
        political_astroturfing = self._detect_political_astroturfing(text_lower)
        
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
            "context_indicators": context_indicators,
            "is_likely_astroturfing": score > 0.6,
            "political_astroturfing": political_astroturfing
        }

    def _detect_logical_contradictions(self, text: str) -> Dict[str, any]:
        """Detect logical contradictions in the text"""
        text_lower = text.lower()
        
        # Common contradictory pairs
        contradictions = [
            ("dead", "alive"), ("alive", "dead"),
            ("true", "false"), ("false", "true"),
            ("real", "fake"), ("fake", "real"),
            ("exists", "doesn't exist"), ("doesn't exist", "exists"),
            ("happened", "didn't happen"), ("didn't happen", "happened"),
            ("working", "broken"), ("broken", "working"),
            ("safe", "dangerous"), ("dangerous", "safe"),
            ("proven", "unproven"), ("unproven", "proven"),
            ("confirmed", "denied"), ("denied", "confirmed"),
            ("yes", "no"), ("no", "yes"),
            ("and not", "and"), ("not", "and not")
        ]
        
        found_contradictions = []
        for pair in contradictions:
            if pair[0] in text_lower and pair[1] in text_lower:
                found_contradictions.append(f"{pair[0]} and {pair[1]}")
        
        # Check for ambiguous phrasing
        ambiguous_phrases = [
            "is not dead and alive", "dead and alive",
            "true and false", "false and true",
            "real and fake", "fake and real",
            "both true and false", "neither true nor false"
        ]
        
        found_ambiguous = []
        for phrase in ambiguous_phrases:
            if phrase in text_lower:
                found_ambiguous.append(phrase)
        
        return {
            "has_contradictions": len(found_contradictions) > 0,
            "contradictions": found_contradictions,
            "has_ambiguous_phrasing": len(found_ambiguous) > 0,
            "ambiguous_phrases": found_ambiguous,
            "logical_consistency_score": 0 if found_contradictions or found_ambiguous else 1.0
        }
    
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
                        "content": f"You are {company}, a {persona['style']}. Be decisive in identifying clear misinformation. Use factual knowledge and reasoning."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                temperature=0.1  # Lower temperature for more consistent responses
            )
            
            content = response.choices[0].message.content
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
            
            # Ensure minimum of 3 sources - add fallback sources if needed
            if len(sources) < 3:
                logger.info(f"Only {len(sources)} sources found, adding fallback sources...")
                
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
                
                # Add fallback sources until we have at least 3
                for fallback in fallback_sources:
                    if len(sources) >= 3:
                        break
                    # Check if URL already exists
                    if not any(s.url == fallback.url for s in sources):
                        sources.append(fallback)
                        api_usage["fallback_sources_added"] += 1
                        logger.info(f"✅ Added fallback source: {fallback.title}")
            
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
                    Source(url="https://www.snopes.com/", title="Snopes", 
                           snippet="Fact-checking urban legends, rumors, and misinformation...", 
                           credibility_score=0.85, date_published="2024-01-01")
                ],
                "secondary": ["mimikama", "correctiv", "wikipedia", "factcheckeu", "politifact"]
            }
        }
        
        # Get avatar-specific sources or default to Guardian Avatar
        bot_config = bot_sources.get(company, bot_sources["GuardianAvatar"])
        
        # Always add primary sources first
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
                lang_instructions = {
                    "en": "Create a witty English response that",
                    "de": "Erstelle eine witzige deutsche Antwort, die"
                }
                
                # Adjust instructions based on bot type
                if company == "MemeAvatar":
                    lang_instructions = {
                        "en": "Create a maximum humor Reddit-style response that",
                        "de": "Erstelle eine maximale Humor Reddit-Style Antwort, die"
                    }
                    humor_level = "MAXIMUM HUMOR - Reddit-style, sarcastic, meme-savvy"
                elif company in ["PolicyAvatar", "EuroShieldAvatar", "ScienceAvatar"]:
                    lang_instructions = {
                        "en": "Create a serious, evidence-based response that",
                        "de": "Erstelle eine ernste, evidenzbasierte Antwort, die"
                    }
                    humor_level = "SERIOUS - Evidence-based, authoritative, professional"
                else:  # GuardianAvatar
                    lang_instructions = {
                        "en": "Create a witty English response that",
                        "de": "Erstelle eine witzige deutsche Antwort, die"
                    }
                    humor_level = "BALANCED HUMOR - Witty but factual, engaging"
                
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
                
                prompt = f"""
                You are {company} {persona['emoji']}, {persona['style']}.
                
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
                2. Is engaging and appropriate for your audience
                3. References specific facts from the verified sources above
                4. Includes concrete details (not generic statements)
                5. Uses 1-2 emojis maximum
                6. Is 2-3 sentences max
                7. If the claim is false, clearly state what the truth is based on the sources

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
                temperature=0.7
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
