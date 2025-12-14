"""
Guardian Source Ranker v1
Implements source ranking with authority-based weights and hard filters.
"""
from enum import Enum
from typing import List, Dict, Optional, Set
from pydantic import BaseModel
from datetime import datetime, date
import math
import logging

logger = logging.getLogger(__name__)


class SourceClass(str, Enum):
    """Source classification for authority scoring."""
    PRIMARY_INSTITUTION = "PRIMARY_INSTITUTION"  # EU, UN, gov, courts
    MULTILATERAL = "MULTILATERAL"                # World Bank, OECD, IMF
    REPUTABLE_NGO = "REPUTABLE_NGO"              # Transparency Intl, HRW
    PEER_REVIEWED = "PEER_REVIEWED"              # Journals, systematic reviews
    IFCN_FACTCHECK = "IFCN_FACTCHECK"            # IFCN certified fact-checkers
    REPUTABLE_MEDIA = "REPUTABLE_MEDIA"          # BBC, Reuters explainers
    WIKIPEDIA = "WIKIPEDIA"                       # Background only
    UNKNOWN = "UNKNOWN"


# Authority weights per source class
SOURCE_CLASS_WEIGHTS: Dict[SourceClass, float] = {
    SourceClass.PRIMARY_INSTITUTION: 1.00,
    SourceClass.MULTILATERAL: 0.95,
    SourceClass.REPUTABLE_NGO: 0.90,
    SourceClass.PEER_REVIEWED: 0.88,
    SourceClass.IFCN_FACTCHECK: 0.85,
    SourceClass.REPUTABLE_MEDIA: 0.70,
    SourceClass.WIKIPEDIA: 0.40,
    SourceClass.UNKNOWN: 0.20,
}


# =============================================================================
# GUARDIAN SOURCE PROFILES - Context-sensitive source selection per claim type
# =============================================================================
# Guardian bleibt Guardian – aber kontextsensitiv.
# Jeder ClaimType hat bevorzugte Authority Sources.

GUARDIAN_SOURCE_PROFILES: Dict[str, List[str]] = {
    # Hate Speech, Dehumanization, Threats
    "hate_or_dehumanization": [
        "fra.europa.eu",        # EU Fundamental Rights Agency
        "ohchr.org",            # UN Human Rights
        "bpb.de",               # Bundeszentrale politische Bildung
        "amnesty.org",
        "hrw.org",
    ],
    "threat_or_incitement": [
        "fra.europa.eu",
        "ohchr.org",
        "bpb.de",
        "amnesty.org",
    ],

    # Delegitimization & Policy Framing
    "delegitimization_frame": [
        "transparency.org",     # Transparency International
        "worldbank.org",        # World Bank (oversight, conditionality)
        "ec.europa.eu",         # European Commission
        "oecd.org",
        "freedomhouse.org",
    ],
    "policy_aid_oversight": [
        "ec.europa.eu",
        "worldbank.org",
        "imf.org",
        "oecd.org",
        "transparency.org",
    ],

    # Health & Science
    "health_misinformation": [
        "who.int",
        "cdc.gov",
        "nih.gov",
        "pubmed.ncbi.nlm.nih.gov",
        "thelancet.com",
        "nature.com",
    ],
    "science_denial": [
        "nature.com",
        "science.org",
        "pubmed.ncbi.nlm.nih.gov",
        "who.int",
        "nasa.gov",
    ],

    # Conspiracy & Foreign Influence
    "conspiracy_theory": [
        "euvsdisinfo.eu",       # EU vs Disinfo
        "correctiv.org",
        "snopes.com",
        "factcheck.org",
        "bpb.de",
    ],
    "foreign_influence": [
        "euvsdisinfo.eu",
        "eeas.europa.eu",       # EU External Action Service
        "state.gov",
        "nato.int",
        "osce.org",
    ],

    # Blanket Generalizations & Opinion with Factual Premise
    "blanket_generalization": [
        "bpb.de",
        "fra.europa.eu",
        "correctiv.org",
        "snopes.com",
    ],
    "opinion_with_factual_premise": [
        "correctiv.org",
        "snopes.com",
        "politifact.com",
        "reuters.com",
        "apnews.com",
    ],
}


# =============================================================================
# SOURCE USAGE DISTINCTION - Critical for Defence/EU Review
# =============================================================================
# MediaWiki and commercial APIs are used for signal discovery and claim context
# only, not as authoritative evidence sources.

class SourceUsageType(str, Enum):
    """Distinguishes retrieval sources from authority sources."""
    RETRIEVAL = "RETRIEVAL"      # Discovery, context, signal finding
    AUTHORITY = "AUTHORITY"       # May be cited as evidence


# Sources that may only be used for retrieval/discovery, NOT citation
RETRIEVAL_ONLY_SOURCES: Set[str] = {
    "wikipedia.org",
    "en.wikipedia.org",
    "de.wikipedia.org",
    "wikidata.org",
    # Commercial discovery APIs (results, not the API itself)
    # Google Fact Check API results need verification
    # News API results need classification
}

# Sources that may be cited as authoritative evidence
AUTHORITY_SOURCES: Set[str] = {
    # PRIMARY_INSTITUTION
    "europa.eu", "ec.europa.eu", "fra.europa.eu", "un.org", "ohchr.org",
    "who.int", "bundesregierung.de", "bpb.de", "cdc.gov", "nih.gov",
    # MULTILATERAL
    "worldbank.org", "oecd.org", "imf.org", "nato.int", "osce.org",
    # REPUTABLE_NGO
    "transparency.org", "hrw.org", "amnesty.org", "rsf.org",
    # PEER_REVIEWED
    "pubmed.ncbi.nlm.nih.gov", "nature.com", "science.org", "thelancet.com",
    # IFCN_FACTCHECK
    "correctiv.org", "snopes.com", "factcheck.org", "politifact.com",
}


# Domain to SourceClass mapping (whitelist)
DOMAIN_WHITELIST: Dict[str, SourceClass] = {
    # PRIMARY_INSTITUTION (EU, UN, Government)
    "europa.eu": SourceClass.PRIMARY_INSTITUTION,
    "ec.europa.eu": SourceClass.PRIMARY_INSTITUTION,
    "consilium.europa.eu": SourceClass.PRIMARY_INSTITUTION,
    "europarl.europa.eu": SourceClass.PRIMARY_INSTITUTION,
    "fra.europa.eu": SourceClass.PRIMARY_INSTITUTION,  # EU Fundamental Rights Agency
    "un.org": SourceClass.PRIMARY_INSTITUTION,
    "ohchr.org": SourceClass.PRIMARY_INSTITUTION,  # UN Human Rights
    "who.int": SourceClass.PRIMARY_INSTITUTION,
    "unesco.org": SourceClass.PRIMARY_INSTITUTION,
    "gov.uk": SourceClass.PRIMARY_INSTITUTION,
    "bundesregierung.de": SourceClass.PRIMARY_INSTITUTION,
    "bpb.de": SourceClass.PRIMARY_INSTITUTION,  # Bundeszentrale politische Bildung
    "state.gov": SourceClass.PRIMARY_INSTITUTION,
    "whitehouse.gov": SourceClass.PRIMARY_INSTITUTION,
    "cdc.gov": SourceClass.PRIMARY_INSTITUTION,
    "nih.gov": SourceClass.PRIMARY_INSTITUTION,
    "eeas.europa.eu": SourceClass.PRIMARY_INSTITUTION,  # EU External Action
    "euvsdisinfo.eu": SourceClass.PRIMARY_INSTITUTION,  # EU vs Disinfo

    # MULTILATERAL
    "worldbank.org": SourceClass.MULTILATERAL,
    "imf.org": SourceClass.MULTILATERAL,
    "oecd.org": SourceClass.MULTILATERAL,
    "nato.int": SourceClass.MULTILATERAL,
    "osce.org": SourceClass.MULTILATERAL,
    "wto.org": SourceClass.MULTILATERAL,

    # REPUTABLE_NGO
    "transparency.org": SourceClass.REPUTABLE_NGO,
    "hrw.org": SourceClass.REPUTABLE_NGO,  # Human Rights Watch
    "amnesty.org": SourceClass.REPUTABLE_NGO,
    "rsf.org": SourceClass.REPUTABLE_NGO,  # Reporters Without Borders
    "freedomhouse.org": SourceClass.REPUTABLE_NGO,
    "icij.org": SourceClass.REPUTABLE_NGO,  # Intl Consortium Investigative Journalists

    # PEER_REVIEWED
    "pubmed.ncbi.nlm.nih.gov": SourceClass.PEER_REVIEWED,
    "nature.com": SourceClass.PEER_REVIEWED,
    "science.org": SourceClass.PEER_REVIEWED,
    "thelancet.com": SourceClass.PEER_REVIEWED,
    "bmj.com": SourceClass.PEER_REVIEWED,
    "nejm.org": SourceClass.PEER_REVIEWED,
    "jstor.org": SourceClass.PEER_REVIEWED,
    "arxiv.org": SourceClass.PEER_REVIEWED,
    "ssrn.com": SourceClass.PEER_REVIEWED,

    # IFCN_FACTCHECK
    "factcheck.org": SourceClass.IFCN_FACTCHECK,
    "snopes.com": SourceClass.IFCN_FACTCHECK,
    "politifact.com": SourceClass.IFCN_FACTCHECK,
    "fullfact.org": SourceClass.IFCN_FACTCHECK,
    "correctiv.org": SourceClass.IFCN_FACTCHECK,
    "mimikama.org": SourceClass.IFCN_FACTCHECK,
    "dpa-factchecking.com": SourceClass.IFCN_FACTCHECK,
    "afp.com": SourceClass.IFCN_FACTCHECK,
    "leadstories.com": SourceClass.IFCN_FACTCHECK,

    # REPUTABLE_MEDIA
    "reuters.com": SourceClass.REPUTABLE_MEDIA,
    "apnews.com": SourceClass.REPUTABLE_MEDIA,
    "bbc.com": SourceClass.REPUTABLE_MEDIA,
    "bbc.co.uk": SourceClass.REPUTABLE_MEDIA,
    "nytimes.com": SourceClass.REPUTABLE_MEDIA,
    "washingtonpost.com": SourceClass.REPUTABLE_MEDIA,
    "theguardian.com": SourceClass.REPUTABLE_MEDIA,
    "economist.com": SourceClass.REPUTABLE_MEDIA,
    "dw.com": SourceClass.REPUTABLE_MEDIA,
    "spiegel.de": SourceClass.REPUTABLE_MEDIA,
    "zeit.de": SourceClass.REPUTABLE_MEDIA,
    "sueddeutsche.de": SourceClass.REPUTABLE_MEDIA,
    "tagesschau.de": SourceClass.REPUTABLE_MEDIA,
    "npr.org": SourceClass.REPUTABLE_MEDIA,
    "pbs.org": SourceClass.REPUTABLE_MEDIA,
    "ft.com": SourceClass.REPUTABLE_MEDIA,
    "bloomberg.com": SourceClass.REPUTABLE_MEDIA,
    "wsj.com": SourceClass.REPUTABLE_MEDIA,

    # WIKIPEDIA (background only)
    "wikipedia.org": SourceClass.WIKIPEDIA,
    "en.wikipedia.org": SourceClass.WIKIPEDIA,
    "de.wikipedia.org": SourceClass.WIKIPEDIA,
    "wikidata.org": SourceClass.WIKIPEDIA,
}


class SourceCandidate(BaseModel):
    """A candidate source for fact-checking."""
    url: str
    title: str
    snippet: str
    publisher: Optional[str] = None
    source_class: SourceClass = SourceClass.UNKNOWN
    published_at: Optional[date] = None
    language: str = "en"
    paywalled: bool = False
    retrieval_rank: int = 0

    # Computed scores
    relevance_score: float = 0.0
    authority_score: float = 0.0
    recency_score: float = 0.0
    specificity_score: float = 0.0
    final_score: float = 0.0

    # Metadata
    keywords: List[str] = []
    embedding: Optional[List[float]] = None


class RankerConfig(BaseModel):
    """Configuration for source ranking weights and thresholds."""
    # Scoring weights (must sum to 1.0)
    weight_relevance: float = 0.45
    weight_authority: float = 0.25
    weight_recency: float = 0.15
    weight_specificity: float = 0.10
    weight_prior: float = 0.05

    # Hard thresholds
    min_relevance: float = 0.55
    min_final_score: float = 0.60

    # Penalties
    paywall_penalty: float = 0.25
    broken_link_penalty: float = 0.50

    # Diversity requirements
    max_per_domain: int = 1
    min_source_classes: int = 2

    # Selection
    select_top_n: int = 3


class SourceRanker:
    """
    Guardian Source Ranker v1
    Ranks sources by relevance, authority, recency, specificity.
    Applies hard filters and enforces diversity.
    """

    def __init__(self, config: Optional[RankerConfig] = None):
        self.config = config or RankerConfig()
        self.source_class_weights = SOURCE_CLASS_WEIGHTS
        self.domain_whitelist = DOMAIN_WHITELIST
        logger.info("SourceRanker initialized with config: %s", self.config.model_dump())

    def classify_source(self, url: str) -> SourceClass:
        """Classify a source URL by its domain."""
        domain = self._extract_domain(url)

        # Check exact match
        if domain in self.domain_whitelist:
            return self.domain_whitelist[domain]

        # Check subdomain matches
        for whitelisted_domain, source_class in self.domain_whitelist.items():
            if domain.endswith("." + whitelisted_domain) or domain == whitelisted_domain:
                return source_class

        return SourceClass.UNKNOWN

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            # Remove www. prefix
            if domain.startswith("www."):
                domain = domain[4:]
            return domain
        except Exception:
            return ""

    def score_source(
        self,
        source: SourceCandidate,
        claim_keywords: List[str],
        now_date: Optional[date] = None
    ) -> float:
        """
        Score a single source candidate.

        Components:
        - Relevance: keyword overlap (semantic similarity requires embeddings)
        - Authority: source class weight
        - Recency: exponential decay over 1 year
        - Specificity: entity/keyword hit rate
        - Prior: weak retrieval rank signal
        """
        now_date = now_date or date.today()

        # 1) Relevance: keyword overlap (simplified, no embeddings yet)
        source_text = f"{source.title} {source.snippet}".lower()
        claim_keywords_lower = [kw.lower() for kw in claim_keywords]

        hits = sum(1 for kw in claim_keywords_lower if kw in source_text)
        relevance = min(1.0, hits / max(len(claim_keywords_lower), 1))
        source.relevance_score = relevance

        # 2) Authority: source class weight
        authority = self.source_class_weights.get(source.source_class, 0.2)
        source.authority_score = authority

        # 3) Recency: exponential decay
        if source.published_at:
            days = abs((now_date - source.published_at).days)
        else:
            days = 365  # Assume 1 year old if unknown
        recency = math.exp(-days / 365)
        source.recency_score = recency

        # 4) Specificity: how many key terms appear?
        specificity_hits = sum(1 for kw in claim_keywords_lower[:5] if kw in source_text)
        specificity = min(1.0, specificity_hits / 3)  # Normalize to max 3 hits
        source.specificity_score = specificity

        # 5) Prior: weak retrieval rank signal
        prior = 1.0 / (1 + math.log(1 + source.retrieval_rank))

        # 6) Accessibility penalty
        accessibility = 1.0
        if source.paywalled:
            accessibility -= self.config.paywall_penalty

        # Final weighted score
        score = (
            self.config.weight_relevance * relevance +
            self.config.weight_authority * authority +
            self.config.weight_recency * recency +
            self.config.weight_specificity * specificity +
            self.config.weight_prior * prior
        ) * accessibility

        source.final_score = score
        return score

    def apply_hard_filters(self, sources: List[SourceCandidate]) -> List[SourceCandidate]:
        """Apply hard filters to remove unsuitable sources."""
        filtered = []

        for source in sources:
            # Filter 1: Minimum relevance
            if source.relevance_score < self.config.min_relevance:
                logger.debug("Filtered %s: low relevance %.2f", source.url, source.relevance_score)
                continue

            # Filter 2: Unknown source class (not in whitelist)
            if source.source_class == SourceClass.UNKNOWN:
                logger.debug("Filtered %s: unknown source class", source.url)
                continue

            # Filter 3: Wikipedia for factual claims (Guardian mode)
            # Wikipedia is OK for background context but not as primary source
            # We'll allow it but with low weight (already handled in scoring)

            # Filter 4: Minimum final score
            if source.final_score < self.config.min_final_score:
                logger.debug("Filtered %s: low final score %.2f", source.url, source.final_score)
                continue

            filtered.append(source)

        return filtered

    def enforce_diversity(self, sources: List[SourceCandidate]) -> List[SourceCandidate]:
        """Enforce domain and source class diversity."""
        selected: List[SourceCandidate] = []
        seen_domains: Set[str] = set()
        source_classes_used: Set[SourceClass] = set()

        # Sort by final score descending
        sorted_sources = sorted(sources, key=lambda s: s.final_score, reverse=True)

        for source in sorted_sources:
            if len(selected) >= self.config.select_top_n:
                break

            domain = self._extract_domain(source.url)

            # Check domain limit
            domain_count = sum(1 for s in selected if self._extract_domain(s.url) == domain)
            if domain_count >= self.config.max_per_domain:
                continue

            # Prefer source class diversity
            if len(selected) < self.config.min_source_classes:
                # Still building diversity, prefer new source classes
                if source.source_class not in source_classes_used:
                    selected.append(source)
                    seen_domains.add(domain)
                    source_classes_used.add(source.source_class)
                    continue

            # Normal selection
            selected.append(source)
            seen_domains.add(domain)
            source_classes_used.add(source.source_class)

        # If we couldn't meet diversity, relax and fill
        if len(selected) < self.config.select_top_n:
            for source in sorted_sources:
                if source not in selected and len(selected) < self.config.select_top_n:
                    domain = self._extract_domain(source.url)
                    domain_count = sum(1 for s in selected if self._extract_domain(s.url) == domain)
                    if domain_count < self.config.max_per_domain:
                        selected.append(source)

        return selected

    def rank_sources(
        self,
        candidates: List[SourceCandidate],
        claim_keywords: List[str]
    ) -> List[SourceCandidate]:
        """
        Full ranking pipeline:
        1. Classify sources
        2. Score each source
        3. Apply hard filters
        4. Enforce diversity
        5. Return top N
        """
        logger.info("Ranking %d source candidates", len(candidates))

        # Step 1: Classify sources
        for source in candidates:
            if source.source_class == SourceClass.UNKNOWN:
                source.source_class = self.classify_source(source.url)

        # Step 2: Score all sources
        for source in candidates:
            self.score_source(source, claim_keywords)

        # Step 3: Apply hard filters
        filtered = self.apply_hard_filters(candidates)
        logger.info("After hard filters: %d sources", len(filtered))

        # Step 4: Enforce diversity and select top N
        selected = self.enforce_diversity(filtered)
        logger.info("Selected %d diverse sources", len(selected))

        return selected

    def get_rejection_reasons(
        self,
        candidates: List[SourceCandidate],
        selected: List[SourceCandidate]
    ) -> List[Dict]:
        """Get rejection reasons for non-selected sources (for logging)."""
        selected_urls = {s.url for s in selected}
        rejections = []

        for source in candidates:
            if source.url in selected_urls:
                continue

            reason = "unknown"
            if source.relevance_score < self.config.min_relevance:
                reason = "low_relevance"
            elif source.source_class == SourceClass.UNKNOWN:
                reason = "unknown_source"
            elif source.final_score < self.config.min_final_score:
                reason = "low_score"
            else:
                reason = "diversity_limit"

            rejections.append({
                "url": source.url,
                "reason": reason,
                "final_score": source.final_score
            })

        return rejections[:10]  # Top 10 rejections for logging
