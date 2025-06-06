import os
import asyncio
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import json

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
                "style": "engineering precision meets approachable communication"
            },
            "Vodafone": {
                "voice": "innovative, connected, tech-savvy",
                "tone": "friendly, educational, forward-thinking", 
                "style": "modern communication technology expert"
            },
            "Bayer": {
                "voice": "scientific, healthcare-focused, responsible",
                "tone": "professional, caring, evidence-based",
                "style": "trusted healthcare and science authority"
            },
            "Siemens": {
                "voice": "industrial innovation, German precision",
                "tone": "technical expertise, reliable, progressive",
                "style": "engineering excellence with human touch"
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
            analysis = await self._analyze_with_ai(text)
            
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
    
    async def _analyze_with_ai(self, text: str) -> Dict:
        """Enhanced AI analysis with better prompting for clear misinformation detection"""
        if not self.openai_client:
            return {"assessment": "limited", "reasoning": "No AI available"}
        
        try:
            prompt = f"""
            You are an expert fact-checker specializing in German automotive industry claims.
            
            Analyze this claim for factual accuracy:
            "{text}"
            
            CONTEXT KNOWLEDGE:
            - Electric vehicles (BMW i3, i4, iX) are extensively tested in extreme cold
            - BMW conducts winter testing at -40°C in Arjeplog, Sweden annually
            - EV batteries lose range in cold but DO NOT "explode"
            - Thermal management systems prevent dangerous overheating/cooling
            - No documented cases of EV explosions due to cold weather
            - Claims about "exploding" EVs are typically misinformation
            
            ANALYSIS CRITERIA:
            1. Does this contradict established automotive engineering facts?
            2. Are there inflammatory/sensational terms like "explode" without basis?
            3. Does this spread unfounded fear about established technology?
            4. Would this claim damage a company's reputation unfairly?
            
            Be DECISIVE in your assessment. If a claim is clearly false/misleading, rate it accordingly.
            
            Respond with JSON:
            {{
                "is_verifiable": true,
                "plausibility_score": 10,
                "red_flags": ["sensational explosion claim", "contradicts established EV safety", "no scientific basis"],
                "verification_needed": "BMW winter testing documentation",
                "reasoning": "Electric vehicles are extensively cold-weather tested and do not explode from temperature",
                "misinformation_indicators": ["inflammatory language", "unfounded safety fears", "contradicts engineering facts"],
                "factual_basis": "BMW and other manufacturers conduct extensive winter testing at -40°C with no explosion incidents"
            }}
            
            For claims about EVs exploding in cold weather, the plausibility_score should be very low (10-20) as this contradicts established automotive engineering and safety testing.
            
            Be confident in your assessment - don't default to 50/50 for clearly false claims.
            """
            
            response = await asyncio.to_thread(
                self.openai_client.chat.completions.create,
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system", 
                        "content": "You are a German automotive industry expert and misinformation detection specialist. Be decisive in identifying clear misinformation about electric vehicles."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                temperature=0.1  # Lower temperature for more consistent responses
            )
            
            content = response.choices[0].message.content
            return json.loads(content)
            
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
        """Search for sources to verify the claim"""
        sources = []
        
        try:
            # Use DuckDuckGo search (no API key needed)
            search_url = f"https://html.duckduckgo.com/html/?q={query}"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    search_url,
                    headers={"User-Agent": "TruthShield/1.0"}
                )
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Extract search results
                    for result in soup.find_all('a', class_='result__a')[:3]:
                        try:
                            url = result.get('href')
                            title = result.get_text().strip()
                            
                            if url and title:
                                sources.append(Source(
                                    url=url,
                                    title=title[:100],
                                    snippet="Search result",
                                    credibility_score=0.7  # Default score
                                ))
                        except Exception:
                            continue
                            
        except Exception as e:
            logger.error(f"Source search failed: {e}")
        
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
        
        return responses

    async def _generate_single_response(self,
                                      claim: str,
                                      fact_check: FactCheckResult,
                                      company: str,
                                      language: str) -> AIInfluencerResponse:
        """Generate response in specific language"""
        
        if not self.openai_client:
            # Fallback responses
            fallback_texts = {
                "en": f"As {company}, we take this claim seriously and verify all facts.",
                "de": f"Als {company} nehmen wir diese Behauptung ernst und prüfen alle Fakten."
            }
            
            return AIInfluencerResponse(
                response_text=fallback_texts.get(language, fallback_texts["en"]),
                tone="professional",
                engagement_score=0.6,
                hashtags=[f"#{company}Facts"],
                company_voice=company
            )
        
        try:
            persona = self.company_personas.get(company, self.company_personas["BMW"])
            
            # Language-specific instructions
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
            
            return AIInfluencerResponse(
                response_text=response_text,
                tone=persona["tone"],
                engagement_score=0.85,
                hashtags=[f"#{company}Facts", "#TruthShield"],
                company_voice=company
            )
            
        except Exception as e:
            logger.error(f"Brand response generation failed: {e}")
            fallback = {
                "en": f"We at {company} stand for facts and transparency.",
                "de": f"Wir bei {company} stehen für Fakten und Transparenz."
            }
            return AIInfluencerResponse(
                response_text=fallback.get(language, fallback["en"]),
                tone="professional", 
                engagement_score=0.5,
                hashtags=[f"#{company}"],
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