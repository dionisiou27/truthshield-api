# TruthShield Services

# Fact-Checking APIs
from .google_factcheck import search_google_factchecks, GoogleFactCheckAPI
from .claimbuster_api import score_claim_worthiness, search_similar_claims, ClaimBusterAPI
from .news_api import search_news_context, get_headlines_context, NewsAPIClient

# Knowledge Base APIs
from .wiki_api import search_mediawiki_sources, fetch_wikipedia_pages, fetch_wikidata_entities

# Academic/Scientific APIs
from .pubmed_api import search_pubmed, PubMedAPI
from .arxiv_api import search_arxiv, ArXivAPI
from .core_api import search_core, CoreAPI
from .semantic_scholar_api import search_semantic_scholar, SemanticScholarAPI

# Health APIs
from .who_api import search_who, get_who_stats, WHOAPI

# Utility Services
from .ocr_service import OCRService
from .web_scraper import WebScraper

__all__ = [
    # Fact-Checking
    "search_google_factchecks",
    "GoogleFactCheckAPI",
    "score_claim_worthiness",
    "search_similar_claims",
    "ClaimBusterAPI",
    "search_news_context",
    "get_headlines_context",
    "NewsAPIClient",

    # Knowledge Base
    "search_mediawiki_sources",
    "fetch_wikipedia_pages",
    "fetch_wikidata_entities",

    # Academic
    "search_pubmed",
    "PubMedAPI",
    "search_arxiv",
    "ArXivAPI",
    "search_core",
    "CoreAPI",
    "search_semantic_scholar",
    "SemanticScholarAPI",

    # Health
    "search_who",
    "get_who_stats",
    "WHOAPI",

    # Utilities
    "OCRService",
    "WebScraper",
]
