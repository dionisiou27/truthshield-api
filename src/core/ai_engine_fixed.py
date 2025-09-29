import os
import asyncio
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import json
from urllib.parse import quote

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
    bot_name: Optional[str] = None  # Added for Guardian Bot
    bot_type: Optional[str] = None  # Added for Guardian Bot

class TruthShieldAI:
    """Real AI-powered fact-checking engine"""
    
    def __init__(self):
        self.openai_client = None
        self.setup_openai()
        
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
            # NEW: Guardian Bot for universal fact-checking
            "Guardian": {
                "voice": "universal truth defender, witty, sharp",
                "tone": "humorous, factual, engaging, unbiased",
                "style": "The digital Charlie Chaplin - making misinformation look ridiculous",
                "emoji": "🛡️",
                "examples": {
                    "de": [
                        "Guardian Bot hier! 🛡️ Diese alte Legende? Zeit für einen Reality-Check mit Humor...",
                        "Ach herrje, das klingt ja spannend! Aber die Wahrheit ist noch viel interessanter... 😄",
                        "Moment mal! *kramt in der Faktenkiste* Das riecht nach einer urbanen Legende..."
                    ],
                    "en": [
                        "Guardian Bot here! 🛡️ This old tale? Time for a reality check with humor...",
                        "Oh my, that sounds exciting! But the truth is even more interesting... 😄",
                        "Hold on! *digging through the fact box* This smells like an urban legend..."
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
            sources = await self._search_sources(text)
            
            # Step 3: Determine final verdict
            verdict = self._determine_verdict(analysis, sources)
            
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
        legitimate_politicians = [
            "ursula von der leyen", "von der leyen", "ursula",
            "angela merkel", "merkel", "angela",
            "emmanuel macron", "macron", "emmanuel",
            "olaf scholz", "scholz", "olaf",
            "joe biden", "biden", "joseph biden",
            "donald trump", "trump", "donald",
            "volodymyr zelensky", "zelensky", "volodymyr"
        ]
        
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
        
        # Check for corruption accusations
        has_corruption_accusations = any(pattern in text_lower for pattern in corruption_patterns)
        
        # Check for conspiracy language
        has_conspiracy_language = any(pattern in text_lower for pattern in conspiracy_language)
        
        # Calculate political astroturfing score
        score = 0
        if targets_politician and has_corruption_accusations:
            score += 0.6  # High score for targeting legitimate politicians with corruption claims
        if has_conspiracy_language:
            score += 0.3  # Medium score for conspiracy language
        if targets_politician and has_conspiracy_language:
            score += 0.2  # Additional score for both
        
        return {
            "targets_legitimate_politician": targets_politician,
            "has_corruption_accusations": has_corruption_accusations,
            "has_conspiracy_language": has_conspiracy_language,
            "political_astroturfing_score": min(score, 1.0),
            "is_political_astroturfing": score > 0.7,
            "detected_patterns": {
                "corruption_terms": [p for p in corruption_patterns if p in text_lower],
                "conspiracy_terms": [p for p in conspiracy_language if p in text_lower],
                "targeted_politicians": [p for p in legitimate_politicians if p in text_lower]
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
            if company == "Guardian":
                # Universal fact-checking prompt
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
                
                prompt = f"""
                You are Guardian Bot, a universal fact-checker and misinformation detective.
                
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
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system", 
                        "content": f"You are {'Guardian Bot, a universal misinformation detector' if company == 'Guardian' else f'a {company} industry expert and misinformation specialist'}. Be decisive in identifying clear misinformation."
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
    
    async def _search_sources(self, query: str) -> List[Source]:
        """Search for sources to verify the claim using real fact-checking APIs and scrapers"""
        try:
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
            logger.info(f"API Status - Google Fact Check: {'✅' if google_api_available else '❌'}, NewsAPI: {'✅' if news_api_available else '❌'}")
            
            # For now, return empty sources for political astroturfing
            return []
            
        except Exception as e:
            logger.error(f"Source search failed: {e}")
            return []

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
        
        # Add Guardian Bot metadata if applicable
        if company == "Guardian":
            for lang in responses:
                responses[lang].bot_name = "Guardian Bot 🛡️"
                responses[lang].bot_type = "universal"
        
        return responses

    async def _generate_single_response(self,
                                      claim: str,
                                      fact_check: FactCheckResult,
                                      company: str,
                                      language: str) -> AIInfluencerResponse:
        """Generate response in specific language"""
        
        if not self.openai_client:
            # Fallback responses
            if company == "Guardian":
                fallback_texts = {
                    "en": "Guardian Bot here! 🛡️ Let me fact-check this claim with humor and truth...",
                    "de": "Guardian Bot hier! 🛡️ Lass mich diese Behauptung mit Humor und Wahrheit prüfen..."
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
                hashtags=[f"#{company}Facts"] if company != "Guardian" else ["#TruthShield", "#FactCheck"],
                company_voice=company
            )
        
        try:
            persona = self.company_personas.get(company, self.company_personas["BMW"])
            
            # Special handling for Guardian Bot
            if company == "Guardian":
                lang_instructions = {
                    "en": "Create a witty English response that",
                    "de": "Erstelle eine witzige deutsche Antwort, die"
                }
                
                prompt = f"""
                You are Guardian Bot 🛡️, TruthShield's universal fact-checker.
                
                Style: {persona['style']}
                Tone: {persona['tone']}
                
                A claim is circulating:
                "{claim}"
                
                Fact-check result:
                - Is fake: {fact_check.is_fake}
                - Confidence: {fact_check.confidence}
                - Category: {fact_check.category}
                
                {lang_instructions.get(language)}:
                1. Uses humor to make misinformation look ridiculous
                2. Is witty and engaging
                3. Includes the truth in an entertaining way
                4. Uses 1-2 emojis maximum
                5. Is 2-3 sentences max
                
                {"Respond in German." if language == "de" else "Respond in English."}
                
                Examples of Guardian Bot style:
                {persona['examples'][language][0]}
                """
            else:
                # Existing company-specific prompt
                lang_instructions = {
                    "en": "Create an English response that",
                    "de": "Erstelle eine deutsche Antwort, die"
                }
                
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
                
                {"Respond in German." if language == "de" else "Respond in English."}
                Make it feel authentic to {company}'s communication style.
                """
            
            response = await asyncio.to_thread(
                self.openai_client.chat.completions.create,
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )
            
            response_text = response.choices[0].message.content
            
            # Determine hashtags
            if company == "Guardian":
                hashtags = ["#TruthShield", "#FactCheck", "#GuardianBot"]
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
            if company == "Guardian":
                fallback = {
                    "en": "Guardian Bot says: That's an interesting claim! Let me check the facts... 🛡️",
                    "de": "Guardian Bot sagt: Das ist eine interessante Behauptung! Lass mich die Fakten prüfen... 🛡️"
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
                hashtags=[f"#{company}"] if company != "Guardian" else ["#GuardianBot"],
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
