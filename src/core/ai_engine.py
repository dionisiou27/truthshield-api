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
from urllib.parse import quote

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
                temperature=0.7  # Lower temperature for more consistent responses
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
            google_task = self._search_google_factcheck(query)
            news_task = self._search_news_api(query)
            snopes_task = self._search_snopes(query)
            factcheck_task = self._search_factcheck_org(query)
            politifact_task = self._search_politifact(query)
            mimikama_task = self._search_mimikama(query)
            correctiv_task = self._search_correctiv(query)

            google_results, news_results, snopes_results, factcheck_results, politifact_results, mimikama_results, correctiv_results = await asyncio.gather(
                google_task, news_task, snopes_task, factcheck_task, politifact_task, mimikama_task, correctiv_task, return_exceptions=True
            )

            all_sources: List[Source] = []

            if isinstance(google_results, Exception):
                logger.error(f"Google Fact Check search error: {google_results}")
            else:
                all_sources.extend(google_results)

            if isinstance(news_results, Exception):
                logger.error(f"News API search error: {news_results}")
            else:
                all_sources.extend(news_results)

            if isinstance(snopes_results, Exception):
                logger.error(f"Snopes search error: {snopes_results}")
            else:
                all_sources.extend(snopes_results)

            if isinstance(factcheck_results, Exception):
                logger.error(f"FactCheck.org search error: {factcheck_results}")
            else:
                all_sources.extend(factcheck_results)

            if isinstance(politifact_results, Exception):
                logger.error(f"PolitiFact search error: {politifact_results}")
            else:
                all_sources.extend(politifact_results)

            if isinstance(mimikama_results, Exception):
                logger.error(f"Mimikama search error: {mimikama_results}")
            else:
                all_sources.extend(mimikama_results)

            if isinstance(correctiv_results, Exception):
                logger.error(f"Correctiv search error: {correctiv_results}")
            else:
                all_sources.extend(correctiv_results)

            # Sort by credibility_score descending and return top 5
            all_sources.sort(key=lambda s: s.credibility_score, reverse=True)
            return all_sources[:5]

        except Exception as e:
            logger.error(f"Source search failed: {e}")
            return []

    async def _search_snopes(self, query: str) -> List[Source]:
        """Scrape Snopes for fact-check articles related to the query."""
        try:
            search_url = f"https://www.snopes.com/?s={quote(query, safe='')}"
            async with httpx.AsyncClient(timeout=10.0, headers={"User-Agent": "TruthShield/1.0"}) as client:
                resp = await client.get(search_url)
                if resp.status_code != 200:
                    return []
                soup = BeautifulSoup(resp.text, 'html.parser')
                results: List[Source] = []
                for card in soup.select('article a[href]')[:5]:
                    url = card.get('href')
                    title = (card.get_text() or "").strip()
                    if not url or not title:
                        continue
                    # Optional: try to find rating badge
                    rating_el = card.find_parent('article')
                    rating_text = None
                    if rating_el:
                        badge = rating_el.select_one('[class*="media-rating"]')
                        if badge:
                            rating_text = badge.get_text(strip=True)
                    snippet = f"Snopes rating: {rating_text}" if rating_text else "Snopes article"
                    results.append(Source(
                        url=url,
                        title=title[:180],
                        snippet=snippet[:240],
                        credibility_score=0.95
                    ))
                return results
        except Exception as e:
            logger.error(f"Snopes scraping error: {e}")
            return []

    async def _search_factcheck_org(self, query: str) -> List[Source]:
        """Scrape FactCheck.org for related articles."""
        try:
            search_url = f"https://www.factcheck.org/search/{quote(query, safe='')}"
            async with httpx.AsyncClient(timeout=10.0, headers={"User-Agent": "TruthShield/1.0"}) as client:
                resp = await client.get(search_url)
                if resp.status_code != 200:
                    return []
                soup = BeautifulSoup(resp.text, 'html.parser')
                results: List[Source] = []
                for item in soup.select('h3 a[href], h2 a[href]')[:5]:
                    url = item.get('href')
                    title = (item.get_text() or "").strip()
                    if not url or not title:
                        continue
                    results.append(Source(
                        url=url,
                        title=title[:180],
                        snippet="FactCheck.org article",
                        credibility_score=0.95
                    ))
                return results
        except Exception as e:
            logger.error(f"FactCheck.org scraping error: {e}")
            return []

    async def _search_politifact(self, query: str) -> List[Source]:
        """Scrape PolitiFact for related fact-checks."""
        try:
            search_url = f"https://www.politifact.com/search/?q={quote(query, safe='')}"
            async with httpx.AsyncClient(timeout=10.0, headers={"User-Agent": "TruthShield/1.0"}) as client:
                resp = await client.get(search_url)
                if resp.status_code != 200:
                    return []
                soup = BeautifulSoup(resp.text, 'html.parser')
                results: List[Source] = []
                for item in soup.select('a.m-statement__quote, article a[href]')[:5]:
                    title = (item.get_text() or "").strip()
                    url = item.get('href')
                    if url and url.startswith('/'):
                        url = f"https://www.politifact.com{url}"
                    if not url or not title:
                        continue
                    # Try to extract rating from nearby elements
                    rating = None
                    parent = item.find_parent(class_='m-statement') or item.find_parent('article')
                    if parent:
                        r = parent.select_one('.m-statement__meter .c-image__original')
                        if r and r.get('alt'):
                            rating = r.get('alt')
                    snippet = f"PolitiFact rating: {rating}" if rating else "PolitiFact article"
                    results.append(Source(
                        url=url,
                        title=title[:180],
                        snippet=snippet[:240],
                        credibility_score=0.95
                    ))
                return results
        except Exception as e:
            logger.error(f"PolitiFact scraping error: {e}")
            return []

    async def _search_mimikama(self, query: str) -> List[Source]:
        """Scrape Mimikama (DE) for related articles."""
        try:
            search_url = f"https://www.mimikama.org/?s={quote(query, safe='')}"
            async with httpx.AsyncClient(timeout=10.0, headers={"User-Agent": "TruthShield/1.0"}) as client:
                resp = await client.get(search_url)
                if resp.status_code != 200:
                    return []
                soup = BeautifulSoup(resp.text, 'html.parser')
                results: List[Source] = []
                for item in soup.select('h2.entry-title a[href], h3.entry-title a[href]')[:5]:
                    url = item.get('href')
                    title = (item.get_text() or "").strip()
                    if not url or not title:
                        continue
                    results.append(Source(
                        url=url,
                        title=title[:180],
                        snippet="Mimikama Artikel",
                        credibility_score=0.95
                    ))
                return results
        except Exception as e:
            logger.error(f"Mimikama scraping error: {e}")
            return []

    async def _search_correctiv(self, query: str) -> List[Source]:
        """Scrape Correctiv (DE) for related fact checks."""
        try:
            search_url = f"https://correctiv.org/?s={quote(query, safe='')}"
            async with httpx.AsyncClient(timeout=10.0, headers={"User-Agent": "TruthShield/1.0"}) as client:
                resp = await client.get(search_url)
                if resp.status_code != 200:
                    return []
                soup = BeautifulSoup(resp.text, 'html.parser')
                results: List[Source] = []
                for item in soup.select('h2 a[href], h3 a[href]')[:5]:
                    url = item.get('href')
                    title = (item.get_text() or "").strip()
                    if not url or not title:
                        continue
                    results.append(Source(
                        url=url,
                        title=title[:180],
                        snippet="CORRECTIV.Faktencheck",
                        credibility_score=0.95
                    ))
                return results
        except Exception as e:
            logger.error(f"Correctiv scraping error: {e}")
            return []

    async def _search_google_factcheck(self, query: str) -> List[Source]:
        """Query Google Fact Check Tools API for fact-checked claims.

        Uses GOOGLE_API_KEY from environment.
        """
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
            logger.debug(f"Google Fact Check query: {quote(query, safe='')}")
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, params=params)
                if resp.status_code != 200:
                    logger.error(f"Google Fact Check API HTTP {resp.status_code}: {resp.text[:200]}")
                    return []

                data = resp.json()
                claims = data.get("claims", []) or []

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

                        # Score mapping: stronger refutations score higher (more useful for debunking)
                        rating_lower = textual_rating.lower()
                        if any(k in rating_lower for k in ["false", "pants on fire", "mostly false", "incorrect", "fake"]):
                            score = 0.95
                        elif any(k in rating_lower for k in ["mixture", "half true", "partly true", "needs context", "unproven", "misleading"]):
                            score = 0.8
                        elif any(k in rating_lower for k in ["true", "mostly true", "accurate"]):
                            score = 0.75
                        else:
                            score = 0.7

                        # Boost well-known publishers slightly
                        reputable_publishers = {
                            "PolitiFact", "Snopes", "AP Fact Check", "AP News", "AFP Fact Check",
                            "FactCheck.org", "Reuters", "Full Fact", "Washington Post"
                        }
                        if publisher in reputable_publishers:
                            score += 0.03

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
        except httpx.TimeoutException:
            logger.error("Google Fact Check API request timed out")
            return []
        except Exception as e:
            logger.error(f"Google Fact Check API error: {e}")
            return []

    async def _search_news_api(self, query: str) -> List[Source]:
        """Query NewsAPI for relevant news articles about the claim.

        Uses NEWS_API_KEY from environment.
        """
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

        reputable_domains = {
            "reuters.com", "apnews.com", "bbc.com", "bbc.co.uk", "nytimes.com", "washingtonpost.com",
            "wsj.com", "bloomberg.com", "theguardian.com", "npr.org", "associatedpress.com"
        }

        try:
            logger.debug(f"NewsAPI query: {quote(query, safe='')}")
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

                    # Domain-based credibility scoring
                    domain = ""
                    try:
                        if url_art:
                            domain = url_art.split("//", 1)[-1].split("/", 1)[0].lower()
                    except Exception:
                        domain = ""

                    base_score = 0.65
                    if any(d in domain for d in reputable_domains):
                        base_score = 0.8

                    if url_art and title:
                        sources.append(Source(
                            url=url_art,
                            title=title[:180],
                            snippet=(description or "News article")[:240],
                            credibility_score=base_score,
                            date_published=published_at
                        ))

                return sources
        except httpx.TimeoutException:
            logger.error("NewsAPI request timed out")
            return []
        except Exception as e:
            logger.error(f"NewsAPI error: {e}")
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
