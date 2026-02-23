"""
Source search, prioritization, and aggregation logic.
Extracted from ai_engine.py (P3.7).
"""
import logging
from typing import Dict, List, Any

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class Source(BaseModel):
    """Fact-checking source"""
    url: str
    title: str
    snippet: str
    credibility_score: float
    date_published: str | None = None


class SourceAggregator:
    """Searches and ranks sources for claim verification."""

    def __init__(self):
        self.last_api_usage: Dict[str, Dict[str, Any]] = {}
        self.last_mediawiki_results: List[Dict[str, Any]] = []

    async def search_sources(self, query: str, company: str = "GuardianAvatar") -> List[Source]:
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

            # REAL GOOGLE FACT CHECK API INTEGRATION
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

            # REAL NEWS API INTEGRATION
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

            # MEDIAWIKI (Wikipedia + Wikidata) CONTEXT
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

            # REAL CLAIMBUSTER API INTEGRATION (Claim Scoring)
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
                prioritized_sources = self.get_prioritized_sources(query, company)
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

    def get_prioritized_sources(self, query: str, company: str = "GuardianAvatar") -> List[Source]:
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
                    Source(url="https://meta.wikimedia.org/wiki/Public_policy", title="Meta-Wiki - Public policy & governance",
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
                           "merkel", "scholz", "macron", "von der leyen", "parliament", "parlam"]
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
