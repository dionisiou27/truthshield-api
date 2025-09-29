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
        """Search for sources to verify the claim using real fact-checking APIs and scrapers"""
        try:
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
            
            # Enhance query for better relevance
            enhanced_query = truncated_query
            if "electric" in truncated_query.lower() and ("explode" in truncated_query.lower() or "explosion" in truncated_query.lower()):
                enhanced_query = f"{truncated_query} electric vehicle safety battery fires"
            elif "electric" in truncated_query.lower() and ("winter" in truncated_query.lower() or "cold" in truncated_query.lower()):
                enhanced_query = f"{truncated_query} electric vehicle cold weather safety"
            elif "BMW" in truncated_query.upper():
                enhanced_query = f"{truncated_query} BMW"

            # Run all searches in parallel - ordered by priority
            tasks = [
                # Static knowledge sources (highest priority)
                self._search_wikipedia(enhanced_query, detected_lang),
                self._search_wikidata(enhanced_query, detected_lang),
                self._search_dbpedia(enhanced_query, detected_lang),
                # Fact-checking sources
                self._search_google_factcheck(enhanced_query, detected_lang),
                self._search_snopes(enhanced_query),
                self._search_factcheck_org(enhanced_query),
                self._search_politifact(enhanced_query),
                self._search_mimikama(enhanced_query),
                self._search_correctiv(enhanced_query),
                self._search_euvsdisinfo(enhanced_query),
                # Academic sources
                self._search_pubmed(enhanced_query),
                self._search_core_ac_uk(enhanced_query),
                # Live news sources
                self._search_news_api(enhanced_query, detected_lang),
                self._search_reuters(enhanced_query, detected_lang),
                self._search_deutsche_welle(enhanced_query, detected_lang),
                self._search_rss_news(enhanced_query, detected_lang)
            ]

            wikipedia_results, wikidata_results, dbpedia_results, google_results, snopes_results, factcheck_results, politifact_results, mimikama_results, correctiv_results, euvsdisinfo_results, pubmed_results, core_results, news_results, reuters_results, dw_results, rss_results = await asyncio.gather(
                *tasks, return_exceptions=True
            )

            method_names = [
                "wikipedia",
                "wikidata",
                "dbpedia",
                "google_factcheck",
                "snopes",
                "factcheck_org",
                "politifact",
                "mimikama",
                "correctiv",
                "euvsdisinfo",
                "pubmed",
                "core_ac_uk",
                "news_api",
                "reuters",
                "deutsche_welle",
                "rss_news"
            ]
            for i, result in enumerate([
                wikipedia_results, wikidata_results, dbpedia_results, google_results, snopes_results, factcheck_results, politifact_results, mimikama_results, correctiv_results, euvsdisinfo_results, pubmed_results, core_results, news_results, reuters_results, dw_results, rss_results
            ]):
                name = method_names[i]
                if isinstance(result, Exception):
                    logger.error(f"search::{name} failed: {result}")
                elif isinstance(result, list):
                    logger.info(f"search::{name} returned {len(result)} sources")

            all_sources: List[Source] = []

            def extend_safe(results):
                if isinstance(results, Exception):
                    return []
                return results or []

            all_sources.extend(extend_safe(wikipedia_results))
            all_sources.extend(extend_safe(wikidata_results))
            all_sources.extend(extend_safe(dbpedia_results))
            all_sources.extend(extend_safe(google_results))
            all_sources.extend(extend_safe(snopes_results))
            all_sources.extend(extend_safe(factcheck_results))
            all_sources.extend(extend_safe(politifact_results))
            all_sources.extend(extend_safe(mimikama_results))
            all_sources.extend(extend_safe(correctiv_results))
            all_sources.extend(extend_safe(euvsdisinfo_results))
            all_sources.extend(extend_safe(pubmed_results))
            all_sources.extend(extend_safe(core_results))
            all_sources.extend(extend_safe(news_results))
            all_sources.extend(extend_safe(reuters_results))
            all_sources.extend(extend_safe(dw_results))
            all_sources.extend(extend_safe(rss_results))

            # De-duplicate by URL
            dedup: Dict[str, Source] = {}
            for src in all_sources:
                if src and src.url and src.url not in dedup:
                    dedup[src.url] = src

            agg_counts = {
                "wikipedia": 0 if isinstance(wikipedia_results, Exception) else len(wikipedia_results or []),
                "wikidata": 0 if isinstance(wikidata_results, Exception) else len(wikidata_results or []),
                "dbpedia": 0 if isinstance(dbpedia_results, Exception) else len(dbpedia_results or []),
                "google": 0 if isinstance(google_results, Exception) else len(google_results or []),
                "snopes": 0 if isinstance(snopes_results, Exception) else len(snopes_results or []),
                "factcheck": 0 if isinstance(factcheck_results, Exception) else len(factcheck_results or []),
                "politifact": 0 if isinstance(politifact_results, Exception) else len(politifact_results or []),
                "mimikama": 0 if isinstance(mimikama_results, Exception) else len(mimikama_results or []),
                "correctiv": 0 if isinstance(correctiv_results, Exception) else len(correctiv_results or []),
                "euvsdisinfo": 0 if isinstance(euvsdisinfo_results, Exception) else len(euvsdisinfo_results or []),
                "pubmed": 0 if isinstance(pubmed_results, Exception) else len(pubmed_results or []),
                "core": 0 if isinstance(core_results, Exception) else len(core_results or []),
                "news": 0 if isinstance(news_results, Exception) else len(news_results or []),
                "reuters": 0 if isinstance(reuters_results, Exception) else len(reuters_results or []),
                "dw": 0 if isinstance(dw_results, Exception) else len(dw_results or []),
                "rss": 0 if isinstance(rss_results, Exception) else len(rss_results or []),
            }
            logger.info(f"Source aggregation counts: {agg_counts}; dedup_total={len(dedup)}")

            # Sort by credibility_score descending, then limit to 2 per domain, top 10
            final_sources = list(dedup.values())
            final_sources.sort(key=lambda s: s.credibility_score, reverse=True)

            def _domain(url: str) -> str:
                try:
                    return url.split('//', 1)[-1].split('/', 1)[0].lower()
                except Exception:
                    return ""

            per_domain_count: Dict[str, int] = {}
            limited: List[Source] = []
            for src in final_sources:
                dom = _domain(src.url)
                cnt = per_domain_count.get(dom, 0)
                if cnt >= 2:
                    continue
                per_domain_count[dom] = cnt + 1
                limited.append(src)
                if len(limited) >= 10:
                    break
            return limited

        except Exception as e:
            logger.error(f"Source search failed: {e}")
            return []

    async def _search_google_factcheck(self, query: str, language: str = "en") -> List[Source]:
        """Query Google Fact Check Tools API for fact-checked claims"""
        from .config import settings
        api_key = settings.google_api_key
        if not api_key or api_key == "your_google_api_key_here":
            logger.warning("GOOGLE_API_KEY not set or invalid; skipping Google Fact Check search")
            # Return empty list but don't fail - other sources will still work
            return []

        # Try multiple query variations to increase chances of finding results
        query_variations = [
            query,  # Original query
            query.split()[0] if query.split() else query,  # First word only
            " ".join(query.split()[:3]) if len(query.split()) > 3 else query,  # First 3 words
        ]
        
        # Add specific variations for common topics
        if "electric" in query.lower() or "ev" in query.lower():
            query_variations.extend(["electric vehicles", "electric cars", "EV safety", "electric car safety"])
        if "explode" in query.lower() or "explosion" in query.lower():
            query_variations.extend(["car explosions", "vehicle safety", "car fires", "EV explosions"])
        if "winter" in query.lower() or "cold" in query.lower() or "freezing" in query.lower():
            query_variations.extend(["electric vehicles cold weather", "EV winter safety", "electric car cold"])
        if "battery" in query.lower():
            query_variations.extend(["electric vehicle battery", "EV battery safety", "battery fires"])

        url = "https://factchecktools.googleapis.com/v1alpha1/claims:search"
        all_sources = []
        
        for variation in query_variations[:3]:  # Try max 3 variations
            params = {
                "key": api_key,
                "query": variation,
                "languageCode": language if language in ("en", "de") else "en",
                "pageSize": 5
            }

            try:
                logger.debug(f"Google Fact Check query variation: {variation} lang={params['languageCode']}")
                async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:
                    resp = await client.get(url, params=params)
                    if resp.status_code != 200:
                        logger.warning(f"Google Fact Check API HTTP {resp.status_code} for '{variation}': {resp.text[:100]}")
                        continue  # Try next variation

                    data = resp.json()
                    claims = data.get("claims", [])
                    
                    if not claims:
                        logger.debug(f"No claims found for variation: {variation}")
                        continue

                    logger.info(f"Found {len(claims)} claims for variation: {variation}")

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
                                all_sources.append(Source(
                                    url=url_review,
                                    title=title[:180],
                                    snippet=snippet[:240],
                                    credibility_score=min(score, 0.99),
                                    date_published=review_date
                                ))

            except Exception as e:
                logger.warning(f"Google Fact Check API error for variation '{variation}': {e}")
                continue  # Try next variation

        # Remove duplicates by URL and return
        seen_urls = set()
        unique_sources = []
        for source in all_sources:
            if source.url not in seen_urls:
                seen_urls.add(source.url)
                unique_sources.append(source)
        
        logger.info(f"Google Fact Check total unique sources: {len(unique_sources)}")
        return unique_sources[:10]  # Limit to top 10 results

    async def _search_news_api(self, query: str, language: str = "en") -> List[Source]:
        """Query NewsAPI for relevant news articles about the claim"""
        from .config import settings
        api_key = settings.news_api_key
        if not api_key or api_key == "your_news_api_key_here":
            logger.warning("NEWS_API_KEY not set or invalid; skipping NewsAPI search")
            # Return empty list but don't fail - other sources will still work
            return []

        url = "https://newsapi.org/v2/everything"
        params = {
            "q": query,
            "language": language if language in ("en", "de") else "en",
            "sortBy": "relevancy",
            "pageSize": 10,
        }
        headers = {"X-Api-Key": api_key}

        try:
            logger.debug(f"NewsAPI query: {query} lang={params['language']}")
            async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:
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
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                response = await client.get(url, headers={"User-Agent": "TruthShield/1.0"})
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    sources = []
                    # Try multiple selectors for robustness
                    candidates = soup.select('h2 a[href], h3 a[href], article a.card-title[href], article a[href]')
                    for link in candidates[:8]:
                        url_link = link.get('href')
                        title_text = (link.get_text() or '').strip()
                        if not url_link or not title_text:
                            continue
                        if url_link.startswith('/'):
                            url_link = f"https://www.snopes.com{url_link}"
                        # Try to find rating near the link
                        rating_text = None
                        art = link.find_parent('article')
                        if art:
                            badge = art.select_one('[class*="media-rating"], [class*="rating"]')
                            if badge:
                                rating_text = badge.get_text(strip=True)
                        
                        sources.append(Source(
                            url=url_link,
                            title=title_text[:180],
                            snippet=(f"Snopes rating: {rating_text}" if rating_text else "Snopes article")[:240],
                            credibility_score=0.9,
                            date_published=None
                        ))
                    return sources
        except Exception as e:
            logger.error(f"Snopes search failed: {e}")
        return []

    async def _search_wikipedia(self, query: str, language: str = "en") -> List[Source]:
        """Search Wikipedia API for related articles (supports en/de)."""
        try:
            lang = "de" if language == "de" else "en"
            base = f"https://{lang}.wikipedia.org/w/api.php"
            
            # First try exact title search
            params = {
                "action": "query",
                "titles": query,
                "format": "json",
                "prop": "extracts",
                "exintro": True,
                "explaintext": True
            }
            
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(base, params=params, headers={"User-Agent": "TruthShield/1.0"})
                if resp.status_code != 200:
                    if resp.status_code == 429:
                        logger.warning("Wikipedia rate limited")
                    else:
                        logger.error(f"Wikipedia HTTP {resp.status_code}: {resp.text[:200]}")
                    return []
                
                data = resp.json()
                pages = (data.get("query") or {}).get("pages") or {}
                results: List[Source] = []
                
                # Check if we found exact matches
                for page_id, page_data in pages.items():
                    if page_id == "-1":  # No exact match
                        continue
                    title = page_data.get("title", "").strip()
                    extract = page_data.get("extract", "").strip()
                    if title and extract:
                        url = f"https://{lang}.wikipedia.org/wiki/{quote(title.replace(' ', '_'))}"
                        results.append(Source(
                                    url=url,
                            title=title[:180],
                            snippet=extract[:240] if extract else "Wikipedia article",
                            credibility_score=0.9,  # Higher score for exact matches
                            date_published=None
                        ))
                
                # If no exact matches, try search with better relevance
                if not results:
                    # Create more specific search terms for better relevance
                    search_terms = query.replace("explode", "safety").replace("exploding", "safety")
                    search_params = {
                        "action": "query",
                        "list": "search",
                        "format": "json",
                        "srsearch": f"{search_terms} BMW electric vehicle",
                        "srlimit": 3
                    }
                    resp = await client.get(base, params=search_params, headers={"User-Agent": "TruthShield/1.0"})
                    if resp.status_code == 200:
                        data = resp.json()
                        hits = ((data.get("query") or {}).get("search") or [])[:3]
                        for h in hits:
                            title = (h.get("title") or "").strip()
                            snippet_html = h.get("snippet") or ""
                            snippet = BeautifulSoup(snippet_html, 'html.parser').get_text(" ")
                            pageid = h.get("pageid")
                            url = f"https://{lang}.wikipedia.org/?curid={pageid}" if pageid else f"https://{lang}.wikipedia.org/wiki/{quote(title.replace(' ', '_'))}"
                            if title and url:
                                results.append(Source(
                                    url=url,
                                    title=title[:180],
                                    snippet=snippet[:240] if snippet else "Wikipedia article",
                                    credibility_score=0.85,
                                    date_published=None
                                ))
                
                return results
        except Exception as e:
            logger.error(f"Wikipedia error: {e}")
            return []

    async def _search_reuters(self, query: str, language: str = "en") -> List[Source]:
        """Search Reuters for recent news articles."""
        try:
            # Reuters RSS feeds
            rss_feeds = [
                "https://feeds.reuters.com/reuters/topNews",
                "https://feeds.reuters.com/reuters/worldNews",
                "https://feeds.reuters.com/reuters/politicsNews"
            ]
            
            if language == "de":
                rss_feeds.extend([
                    "https://feeds.reuters.com/reuters/DEWorldNews",
                    "https://feeds.reuters.com/reuters/DEBusinessNews"
                ])
            
            results: List[Source] = []
            query_lower = query.lower()
            
            async with httpx.AsyncClient(timeout=8.0) as client:
                for feed_url in rss_feeds:
                    try:
                        resp = await client.get(feed_url, headers={"User-Agent": "TruthShield/1.0"})
                        if resp.status_code != 200:
                            continue
                            
                        soup = BeautifulSoup(resp.text, 'xml')
                        items = soup.find_all('item')[:3]  # Top 3 items per feed
                        
                        for item in items:
                            title = item.find('title')
                            link = item.find('link')
                            description = item.find('description')
                            
                            if not all([title, link]):
                                continue
                                
                            title_text = title.get_text().strip()
                            link_text = link.get_text().strip()
                            desc_text = description.get_text().strip() if description else ""
                            
                            # Check if query terms appear in title or description
                            content = f"{title_text} {desc_text}".lower()
                            if any(term in content for term in query_lower.split()):
                                results.append(Source(
                                    url=link_text,
                                    title=title_text[:180],
                                    snippet=desc_text[:240] if desc_text else "Reuters article",
                                    credibility_score=0.95,  # Very high credibility for Reuters
                                    date_published=None
                                ))
                                
                    except Exception as e:
                        logger.warning(f"Reuters feed {feed_url} failed: {e}")
                        continue
                        
            return results[:5]  # Return top 5 Reuters results
            
        except Exception as e:
            logger.error(f"Reuters search failed: {e}")
            return []

    async def _search_deutsche_welle(self, query: str, language: str = "en") -> List[Source]:
        """Search Deutsche Welle for German and international news."""
        try:
            # Deutsche Welle RSS feeds
            rss_feeds = [
                "https://rss.dw.com/rdf/rss-en-all",
                "https://rss.dw.com/rdf/rss-en-top"
            ]
            
            if language == "de":
                rss_feeds.extend([
                    "https://rss.dw.com/rdf/rss-de-all",
                    "https://rss.dw.com/rdf/rss-de-top"
                ])
            
            results: List[Source] = []
            query_lower = query.lower()
            
            async with httpx.AsyncClient(timeout=8.0) as client:
                for feed_url in rss_feeds:
                    try:
                        resp = await client.get(feed_url, headers={"User-Agent": "TruthShield/1.0"})
                        if resp.status_code != 200:
                            continue
                            
                        soup = BeautifulSoup(resp.text, 'xml')
                        items = soup.find_all('item')[:3]  # Top 3 items per feed
                        
                        for item in items:
                            title = item.find('title')
                            link = item.find('link')
                            description = item.find('description')
                            
                            if not all([title, link]):
                                continue
                                
                            title_text = title.get_text().strip()
                            link_text = link.get_text().strip()
                            desc_text = description.get_text().strip() if description else ""
                            
                            # Check if query terms appear in title or description
                            content = f"{title_text} {desc_text}".lower()
                            if any(term in content for term in query_lower.split()):
                                results.append(Source(
                                    url=link_text,
                                    title=title_text[:180],
                                    snippet=desc_text[:240] if desc_text else "Deutsche Welle article",
                                    credibility_score=0.9,  # High credibility for DW
                                    date_published=None
                                ))
                                
                    except Exception as e:
                        logger.warning(f"Deutsche Welle feed {feed_url} failed: {e}")
                        continue
                        
            return results[:4]  # Return top 4 DW results
            
        except Exception as e:
            logger.error(f"Deutsche Welle search failed: {e}")
            return []

    async def _search_rss_news(self, query: str, language: str = "en") -> List[Source]:
        """Search RSS news feeds for recent articles about the claim."""
        try:
            # RSS feeds from major news sources
            rss_feeds = [
                "https://feeds.reuters.com/reuters/topNews",
                "https://feeds.bbci.co.uk/news/rss.xml",
                "https://rss.cnn.com/rss/edition.rss",
                "https://feeds.npr.org/1001/rss.xml",
                "https://feeds.washingtonpost.com/rss/world",
                "https://feeds.washingtonpost.com/rss/politics"
            ]
            
            if language == "de":
                rss_feeds.extend([
                    "https://www.tagesschau.de/xml/rss2/",
                    "https://www.spiegel.de/schlagzeilen/index.rss",
                    "https://www.zeit.de/news/index"
                ])
            
            results: List[Source] = []
            query_lower = query.lower()
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                for feed_url in rss_feeds[:3]:  # Limit to 3 feeds for performance
                    try:
                        resp = await client.get(feed_url, headers={"User-Agent": "TruthShield/1.0"})
                        if resp.status_code != 200:
                            continue
                            
                        soup = BeautifulSoup(resp.text, 'xml')
                        items = soup.find_all('item')[:5]  # Top 5 items per feed
                        
                        for item in items:
                            title = item.find('title')
                            link = item.find('link')
                            description = item.find('description')
                            
                            if not all([title, link]):
                                continue
                                
                            title_text = title.get_text().strip()
                            link_text = link.get_text().strip()
                            desc_text = description.get_text().strip() if description else ""
                            
                            # Check if query terms appear in title or description with better relevance
                            content = f"{title_text} {desc_text}".lower()
                            query_terms = query_lower.split()
                            
                            # Require at least 2 query terms to match for better relevance
                            matches = sum(1 for term in query_terms if term in content)
                            if matches >= 2 or (matches >= 1 and len(query_terms) == 1):
                                results.append(Source(
                                    url=link_text,
                                    title=title_text[:180],
                                    snippet=desc_text[:240] if desc_text else "News article",
                                    credibility_score=0.8,
                                    date_published=None
                                ))
                                
                    except Exception as e:
                        logger.warning(f"RSS feed {feed_url} failed: {e}")
                        continue
                        
            return results[:5]  # Return top 5 RSS results
            
        except Exception as e:
            logger.error(f"RSS news search failed: {e}")
            return []

    async def _search_dbpedia(self, query: str, language: str = "en") -> List[Source]:
        """Search DBPedia for structured knowledge about entities."""
        try:
            # DBPedia SPARQL endpoint
            sparql_url = "http://dbpedia.org/sparql"
            
            # Clean query for SPARQL
            clean_query = query.replace("'", "\\'").replace('"', '\\"')
            
            # SPARQL query to find entities matching the query
            sparql_query = f"""
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX dbo: <http://dbpedia.org/ontology/>
            PREFIX foaf: <http://xmlns.com/foaf/0.1/>
            
            SELECT DISTINCT ?entity ?label ?abstract ?url WHERE {{
              ?entity rdfs:label ?label .
              ?entity dbo:abstract ?abstract .
              ?entity foaf:isPrimaryTopicOf ?url .
              FILTER(LANG(?label) = "en" || LANG(?label) = "")
              FILTER(LANG(?abstract) = "en" || LANG(?abstract) = "")
              FILTER(CONTAINS(LCASE(?label), LCASE("{clean_query}")) || 
                     CONTAINS(LCASE(?abstract), LCASE("{clean_query}")))
            }} LIMIT 3
            """
            
            params = {
                "query": sparql_query,
                "format": "json"
            }
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(sparql_url, params=params, headers={"User-Agent": "TruthShield/1.0"})
                if resp.status_code != 200:
                    logger.warning(f"DBPedia HTTP {resp.status_code}")
                    return []
                
                data = resp.json()
                results: List[Source] = []
                
                bindings = data.get("results", {}).get("bindings", [])
                for binding in bindings:
                    entity = binding.get("entity", {}).get("value", "")
                    label = binding.get("label", {}).get("value", "")
                    abstract = binding.get("abstract", {}).get("value", "")
                    url = binding.get("url", {}).get("value", "")
                    
                    if entity and label:
                        results.append(Source(
                            url=url or entity,
                            title=label[:180],
                            snippet=abstract[:240] if abstract else "DBPedia entity",
                            credibility_score=0.9,  # High credibility for structured data
                            date_published=None
                        ))
                
                return results
                
        except Exception as e:
            logger.error(f"DBPedia search failed: {e}")
            return []

    async def _search_wikidata(self, query: str, language: str = "en") -> List[Source]:
        """Search Wikidata for entities and referenced facts.

        Returns Source items pointing to the entity page with a snippet summarizing matched description.
        """
        try:
            lang = "de" if language == "de" else "en"
            base = "https://www.wikidata.org/w/api.php"
            params = {
                "action": "wbsearchentities",
                "format": "json",
                "search": query,
                "language": lang,
                "limit": 3
            }
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(base, params=params, headers={"User-Agent": "TruthShield/1.0"})
                if resp.status_code != 200:
                    if resp.status_code == 429:
                        logger.warning("Wikidata rate limited")
                    else:
                        logger.error(f"Wikidata HTTP {resp.status_code}: {resp.text[:200]}")
                    return []
                data = resp.json()
                results_json = data.get("search") or []
                results: List[Source] = []
                for item in results_json[:3]:
                    title = (item.get("label") or item.get("id") or "").strip()
                    description = (item.get("description") or "").strip()
                    qid = item.get("id")
                    url = f"https://www.wikidata.org/wiki/{qid}" if qid else None
                    if not (title and url):
                        continue
                    # Credibility: referenced claims on Wikidata are generally curated; set 0.9
                    results.append(Source(
                        url=url,
                        title=title[:180],
                        snippet=(description or "Wikidata entity")[:240],
                        credibility_score=0.9,
                        date_published=None
                    ))
                return results
        except Exception as e:
            logger.error(f"Wikidata error: {e}")
            return []

    async def _search_factcheck_org(self, query: str) -> List[Source]:
        """Scrape FactCheck.org"""
        try:
            url = f"https://www.factcheck.org/?s={quote(query)}"
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                response = await client.get(url, headers={"User-Agent": "TruthShield/1.0"})
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    sources = []
                    for item in soup.select('h2.entry-title a[href], h3.entry-title a[href], h2 a[href], h3 a[href]')[:8]:
                        href = item.get('href')
                        title_text = (item.get_text() or '').strip()
                        if not href or not title_text:
                            continue
                        sources.append(Source(
                            url=href,
                            title=title_text[:180],
                            snippet="FactCheck.org article",
                            credibility_score=0.9,
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
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                response = await client.get(url, headers={"User-Agent": "TruthShield/1.0"})
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    sources = []
                    candidates = soup.select('a.m-statement__quote, article a[href], .c-list li a[href], h3 a[href]')
                    query_lower = query.lower()
                    query_terms = query_lower.split()
                    
                    for link in candidates[:8]:
                        title_text = (link.get_text() or '').strip()
                        href = link.get('href')
                        if href and href.startswith('/'):
                            href = f"https://www.politifact.com{href}"
                        if not href or not title_text:
                            continue
                        
                        # Check relevance - require at least 2 query terms to match
                        content = title_text.lower()
                        matches = sum(1 for term in query_terms if term in content)
                        if matches < 2 and len(query_terms) > 1:
                            continue
                        # Only accept actual factcheck article pages
                        if '/factchecks/' not in href:
                            # Try to find enclosing link to a factcheck
                            parent_article = link.find_parent('article')
                            if parent_article:
                                fact_link = parent_article.find('a', href=True)
                                if fact_link:
                                    fh = fact_link.get('href')
                                    if fh and '/factchecks/' in fh:
                                        href = fh if fh.startswith('http') else f"https://www.politifact.com{fh}"
                                    else:
                                        continue
                            else:
                                continue
                        # Prefer quote text inside statement if available
                        parent_stmt = link.find_parent(class_='m-statement') or link.find_parent('article')
                        if parent_stmt:
                            q = parent_stmt.select_one('.m-statement__quote')
                            if q:
                                tt = (q.get_text() or '').strip()
                                if tt:
                                    title_text = tt
                        # Try to extract rating from enclosing statement
                        rating = None
                        parent = link.find_parent(class_='m-statement') or link.find_parent('article')
                        if parent:
                            r = parent.select_one('.m-statement__meter .c-image__original, img[alt*="Truth-O-Meter"], img[alt]')
                            if r and r.get('alt'):
                                rating = r.get('alt')
                        snippet = f"PolitiFact rating: {rating}" if rating else "PolitiFact article"
                        sources.append(Source(
                            url=href,
                            title=title_text[:180],
                            snippet=snippet[:240],
                            credibility_score=0.9,
                            date_published=None
                        ))
                    return sources
        except Exception as e:
            logger.error(f"PolitiFact search failed: {e}")
        return []

    async def _search_mimikama(self, query: str) -> List[Source]:
        """Scrape Mimikama (DE)"""
        try:
            url = f"https://www.mimikama.org/?s={quote(query)}"
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                response = await client.get(url, headers={"User-Agent": "TruthShield/1.0"})
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    sources = []
                    for link in soup.select('h2.entry-title a[href], h3.entry-title a[href], h2 a[href], h3 a[href]')[:8]:
                        href = link.get('href')
                        title_text = (link.get_text() or '').strip()
                        if not href or not title_text:
                            continue
                        sources.append(Source(
                            url=href,
                            title=title_text[:180],
                            snippet="Mimikama Artikel",
                            credibility_score=0.9,
                            date_published=None
                        ))
                    return sources
        except Exception as e:
            logger.error(f"Mimikama search failed: {e}")
        return []

    async def _search_euvsdisinfo(self, query: str) -> List[Source]:
        """Scrape EUvsDISINFO for EU disinformation fact-checks."""
        try:
            url = f"https://euvsdisinfo.eu/?s={quote(query)}"
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                response = await client.get(url, headers={"User-Agent": "TruthShield/1.0"})
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    sources = []
                    for link in soup.select('h2 a[href], h3 a[href], .entry-title a[href], .post-title a[href]')[:6]:
                        href = link.get('href')
                        title_text = (link.get_text() or '').strip()
                        if not href or not title_text:
                            continue
                        sources.append(Source(
                            url=href,
                            title=title_text[:180],
                            snippet="EUvsDISINFO fact-check",
                            credibility_score=0.9,
                            date_published=None
                        ))
                    return sources
        except Exception as e:
            logger.error(f"EUvsDISINFO search failed: {e}")
        return []

    async def _search_pubmed(self, query: str) -> List[Source]:
        """Search PubMed for academic research articles."""
        try:
            # PubMed E-utilities API
            base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
            params = {
                "db": "pubmed",
                "term": query,
                "retmax": 3,
                "retmode": "json",
                "sort": "relevance"
            }
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                # First, search for article IDs
                resp = await client.get(base_url, params=params, headers={"User-Agent": "TruthShield/1.0"})
                if resp.status_code != 200:
                    return []
                
                data = resp.json()
                id_list = data.get("esearchresult", {}).get("idlist", [])
                
                if not id_list:
                    return []
                
                # Get article details
                fetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
                fetch_params = {
                    "db": "pubmed",
                    "id": ",".join(id_list),
                    "retmode": "xml"
                }
                
                fetch_resp = await client.get(fetch_url, params=fetch_params, headers={"User-Agent": "TruthShield/1.0"})
                if fetch_resp.status_code != 200:
                    return []
                
                soup = BeautifulSoup(fetch_resp.text, 'xml')
                results: List[Source] = []
                
                for article in soup.find_all('PubmedArticle')[:3]:
                    title_elem = article.find('ArticleTitle')
                    abstract_elem = article.find('AbstractText')
                    pmid_elem = article.find('PMID')
                    
                    if title_elem and pmid_elem:
                        title = title_elem.get_text().strip()
                        abstract = abstract_elem.get_text().strip() if abstract_elem else ""
                        pmid = pmid_elem.get_text().strip()
                        url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
                        
                        results.append(Source(
                            url=url,
                            title=title[:180],
                            snippet=abstract[:240] if abstract else "PubMed research article",
                            credibility_score=0.95,  # Very high credibility for peer-reviewed research
                            date_published=None
                        ))
                
                return results
                            
        except Exception as e:
            logger.error(f"PubMed search failed: {e}")
            return []

    async def _search_core_ac_uk(self, query: str) -> List[Source]:
        """Search CORE.ac.uk for open access academic papers."""
        try:
            # CORE API endpoint
            api_url = "https://core.ac.uk/api-v2/search/works"
            params = {
                "q": query,
                "limit": 3,
                "page": 1
            }
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(api_url, params=params, headers={"User-Agent": "TruthShield/1.0"})
                if resp.status_code != 200:
                    return []
                
                data = resp.json()
                results: List[Source] = []
                
                for item in data.get("data", [])[:3]:
                    title = item.get("title", "").strip()
                    abstract = item.get("abstract", "").strip()
                    download_url = item.get("downloadUrl", "")
                    view_url = item.get("links", {}).get("view", "")
                    url = view_url or download_url
                    
                    if title and url:
                        results.append(Source(
                            url=url,
                            title=title[:180],
                            snippet=abstract[:240] if abstract else "CORE.ac.uk research paper",
                            credibility_score=0.9,  # High credibility for academic papers
                            date_published=None
                        ))
                
                return results
                
        except Exception as e:
            logger.error(f"CORE.ac.uk search failed: {e}")
            return []

    async def _search_correctiv(self, query: str) -> List[Source]:
        """Scrape Correctiv (DE)"""
        try:
            url = f"https://correctiv.org/?s={quote(query)}"
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                response = await client.get(url, headers={"User-Agent": "TruthShield/1.0"})
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    sources = []
                    for link in soup.select('h2 a[href], h3 a[href], .c-archive__item a[href]')[:8]:
                        href = link.get('href')
                        title_text = (link.get_text() or '').strip()
                        if not href or not title_text:
                            continue
                        sources.append(Source(
                            url=href,
                            title=title_text[:180],
                            snippet="CORRECTIV.Faktencheck",
                            credibility_score=0.9,
                            date_published=None
                        ))
                    return sources
        except Exception as e:
            logger.error(f"Correctiv search failed: {e}")
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
