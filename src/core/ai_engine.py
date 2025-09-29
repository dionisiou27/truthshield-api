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
    
    async def _analyze_with_ai(self, text: str, company: str = "BMW") -> Dict:
        """Enhanced AI analysis with better prompting for clear misinformation detection"""
        if not self.openai_client:
            return {"assessment": "limited", "reasoning": "No AI available"}
        
        try:
            # Adjust prompt based on company type
            if company == "Guardian":
                # Universal fact-checking prompt
                prompt = f"""
                You are Guardian Bot, a universal fact-checker and misinformation detective.
                
                Analyze this claim for factual accuracy:
                "{text}"
                
                ANALYSIS CRITERIA:
                1. Is this claim supported by verifiable facts?
                2. Are there sensational/inflammatory terms without basis?
                3. Does this contradict established scientific/historical knowledge?
                4. Would believing this cause harm or spread fear?
                
                Be DECISIVE in your assessment. Common misinformation includes:
                - Conspiracy theories (moon landing, flat earth, chemtrails)
                - Health misinformation (miracle cures, vaccine myths)
                - Political disinformation
                - Urban legends presented as fact
                
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
        """Search for sources to verify the claim using real fact-checking APIs"""
        try:
            # Run all searches in parallel
            tasks = [
                self._search_google_factcheck(query),
                self._search_news_api(query),
                self._search_snopes(query),
                self._search_factcheck_org(query),
                self._search_politifact(query)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            all_sources: List[Source] = []
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Search method {i} failed: {result}")
                elif isinstance(result, list):
                    all_sources.extend(result)
            
            # Sort by credibility_score descending and return top sources
            all_sources.sort(key=lambda s: s.credibility_score, reverse=True)
            return all_sources[:7]  # Return more sources now
            
        except Exception as e:
            logger.error(f"Source search failed: {e}")
            return []

    async def _search_google_factcheck(self, query: str) -> List[Source]:
        """Query Google Fact Check Tools API for fact-checked claims"""
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            logger.warning("GOOGLE_API_KEY not set; skipping Google Fact Check search")
            return []

        url = "https://factchecktools.googleapis.com/v1alpha1/claims:search"
        params = {
            "key": api_key,
            "query": query,
            "languageCode": "en",
            "pageSize": 10
        }

        try:
            logger.debug(f"Google Fact Check query: {query}")
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, params=params)
                if resp.status_code != 200:
                    logger.error(f"Google Fact Check API HTTP {resp.status_code}: {resp.text[:200]}")
                    return []

                data = resp.json()
                claims = data.get("claims", [])

                sources: List[Source] = []
                for claim in claims:
                    claim_text = claim.get("text", "")
                    claim_reviews = claim.get("claimReview", []) or []
                    for review in claim_reviews:
                        publisher = (review.get("publisher") or {}).get("name") or ""
                        title = review.get("title") or claim_text or "Fact-check review"
                        url_review = review.get("url") or ""
                        textual_rating = (review.get("textualRating") or "").strip()
                        review_date = review.get("reviewDate") or None

                        # Score mapping
                        rating_lower = textual_rating.lower()
                        if any(k in rating_lower for k in ["false", "pants on fire", "mostly false", "incorrect", "fake"]):
                            score = 0.95
                        elif any(k in rating_lower for k in ["mixture", "half true", "partly true", "needs context", "unproven", "misleading"]):
                            score = 0.8
                        elif any(k in rating_lower for k in ["true", "mostly true", "accurate"]):
                            score = 0.75
                        else:
                            score = 0.7

                        snippet = f"{publisher} rated: {textual_rating}" if textual_rating else f"Review by {publisher}"

                        if url_review:
                            sources.append(Source(
                                url=url_review,
                                title=title[:180],
                                snippet=snippet[:240],
                                credibility_score=min(score, 0.99),
                                date_published=review_date
                            ))

                return sources
        except Exception as e:
            logger.error(f"Google Fact Check API error: {e}")
            return []

    async def _search_news_api(self, query: str) -> List[Source]:
        """Query NewsAPI for relevant news articles about the claim"""
        api_key = os.getenv("NEWS_API_KEY")
        if not api_key:
            logger.warning("NEWS_API_KEY not set; skipping NewsAPI search")
            return []

        url = "https://newsapi.org/v2/everything"
        params = {
            "q": query,
            "language": "en",
            "sortBy": "relevancy",
            "pageSize": 10,
        }
        headers = {"X-Api-Key": api_key}

        try:
            logger.debug(f"NewsAPI query: {query}")
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, params=params, headers=headers)
                if resp.status_code != 200:
                    logger.error(f"NewsAPI HTTP {resp.status_code}: {resp.text[:200]}")
                    return []

                data = resp.json()
                articles = data.get("articles", []) or []

                sources: List[Source] = []
                for art in articles:
                    title = (art.get("title") or "").strip()
                    description = (art.get("description") or art.get("content") or "").strip()
                    url_art = art.get("url") or ""
                    published_at = art.get("publishedAt") or None

                    if url_art and title:
                        sources.append(Source(
                            url=url_art,
                            title=title[:180],
                            snippet=(description or "News article")[:240],
                            credibility_score=0.75,
                            date_published=published_at
                        ))

                return sources
        except Exception as e:
            logger.error(f"NewsAPI error: {e}")
            return []

    async def _search_snopes(self, query: str) -> List[Source]:
        """Scrape Snopes.com for fact-checks"""
        try:
            url = f"https://www.snopes.com/?s={quote(query)}"
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers={"User-Agent": "TruthShield/1.0"})
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    sources = []
                    
                    # Find article cards
                    articles = soup.find_all('article', class_='media-wrapper')[:3]
                    for article in articles:
                        title_elem = article.find('h5', class_='title')
                        link_elem = article.find('a', href=True)
                        rating_elem = article.find('span', class_='rating-label')
                        
                        if title_elem and link_elem:
                            sources.append(Source(
                                url=f"https://www.snopes.com{link_elem['href']}",
                                title=title_elem.text.strip()[:180],
                                snippet=f"Snopes: {rating_elem.text if rating_elem else 'See article'}",
                                credibility_score=0.95,
                                date_published=None
                            ))
                    return sources
        except Exception as e:
            logger.error(f"Snopes search failed: {e}")
        return []

    async def _search_factcheck_org(self, query: str) -> List[Source]:
        """Scrape FactCheck.org"""
        try:
            url = f"https://www.factcheck.org/?s={quote(query)}"
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers={"User-Agent": "TruthShield/1.0"})
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    sources = []
                    
                    articles = soup.find_all('article', class_='entry')[:3]
                    for article in articles:
                        title_elem = article.find('h2', class_='entry-title')
                        if title_elem:
                            link = title_elem.find('a')
                            if link and link.get('href'):
                                sources.append(Source(
                                    url=link['href'],
                                    title=title_elem.text.strip()[:180],
                                    snippet="FactCheck.org verified analysis",
                                    credibility_score=0.95,
                                    date_published=None
                                ))
                    return sources
        except Exception as e:
            logger.error(f"FactCheck.org search failed: {e}")
        return []

    async def _search_politifact(self, query: str) -> List[Source]:
        """Scrape PolitiFact"""
        try:
            url = f"https://www.politifact.com/search/?q={quote(query)}"
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers={"User-Agent": "TruthShield/1.0"})
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    sources = []
                    
                    statements = soup.find_all('div', class_='m-statement')[:3]
                    for stmt in statements:
                        quote_elem = stmt.find('div', class_='m-statement__quote')
                        link_elem = stmt.find('a', class_='m-statement__link')
                        
                        if quote_elem and link_elem:
                            sources.append(Source(
                                url=f"https://www.politifact.com{link_elem.get('href', '')}",
                                title=quote_elem.text.strip()[:180],
                                snippet="PolitiFact fact-check",
                                credibility_score=0.95,
                                date_published=None
                            ))
                    return sources
        except Exception as e:
            logger.error(f"PolitiFact search failed: {e}")
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