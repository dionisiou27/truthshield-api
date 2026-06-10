"""
Guardian Source Ranker v3
Weighted ranking with HARD safety constraints (paper-aligned).

Two enforced constraints sit on top of the weighted scoring:
  1. Authority threshold — no source below ImmutableConstraints.MIN_SOURCE_AUTHORITY
     (0.70, i.e. REPUTABLE_MEDIA) may enter the CITATION pool. Such sources may
     still be used for retrieval/discovery (SourceUsageType.RETRIEVAL).
  2. Diversity — at most one source per domain, and at least two source classes
     per intervention. If diversity cannot be met, the result is flagged
     (diversity_constraint_unmet) for human review rather than silently violated.

Within those hard rules, topic-aware relevance boosting and soft diversity
preferences act only as tie-breakers.
"""
from enum import Enum
from typing import List, Dict, Optional, Set
from pydantic import BaseModel
from datetime import datetime, date
import math
import logging

from src.core.constraints import ImmutableConstraints

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
        "news.err.ee",          # Estonian Public Broadcasting - excellent IO coverage
        "state.gov",
        "nato.int",
        "osce.org",
    ],

    # TERRITORIAL / FRONTLINE CLAIMS - Critical for TikTok temporal awareness
    # These sources provide real-time frontline updates and IO-frame analysis
    "territorial_control": [
        "news.err.ee",          # ERR English - Baltic/Eastern European frontline coverage (Tier A)
        "euvsdisinfo.eu",       # IO pattern documentation (Tier A)
        "understandingwar.org", # Institute for Study of War
        "reuters.com",
        "apnews.com",
        "newsukraine.rbc.ua",   # RBC-Ukraine (Tier B - fast freshness, needs corroboration)
    ],

    # POLICY / MOBILIZATION - Ukraine-specific policy claims
    "policy_mobilization": [
        "newsukraine.rbc.ua",   # RBC covers mobilization policy + fakes
        "news.err.ee",
        "reuters.com",
        "apnews.com",
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
    # Baltic/Eastern European public broadcasters - excellent for frontline/IO coverage
    "news.err.ee": SourceClass.REPUTABLE_MEDIA,  # Estonian Public Broadcasting (English)
    "err.ee": SourceClass.REPUTABLE_MEDIA,        # ERR Estonian
    "lrt.lt": SourceClass.REPUTABLE_MEDIA,        # Lithuanian Radio & TV
    "lsm.lv": SourceClass.REPUTABLE_MEDIA,        # Latvian Public Broadcasting
    # Ukrainian news agencies - Tier B (good for freshness, require corroboration for frontline)
    "newsukraine.rbc.ua": SourceClass.REPUTABLE_MEDIA,  # RBC-Ukraine English
    "rbc.ua": SourceClass.REPUTABLE_MEDIA,              # RBC-Ukraine main

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

    # Whether this source may be cited as evidence (AUTHORITY) or is only valid
    # for discovery/context (RETRIEVAL). Set by the hard authority filter.
    usage_type: "SourceUsageType" = SourceUsageType.AUTHORITY

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
    """Configuration for source ranking weights."""
    # Scoring weights (must sum to 1.0)
    weight_relevance: float = 0.35      # Topic fit
    weight_authority: float = 0.30      # Source class weight
    weight_topic_fit: float = 0.20      # Claim-type-specific boost
    weight_recency: float = 0.10        # Freshness
    weight_prior: float = 0.05          # Retrieval rank signal

    # HARD authority filter (paper-aligned): any source whose class weight is
    # below ImmutableConstraints.MIN_SOURCE_AUTHORITY (0.70) is excluded from the
    # CITATION pool before ranking. It remains usable for retrieval/discovery.
    # This is enforced in rank_sources(), not configurable here.

    # Soft penalties (reduce score, don't exclude) — tie-breakers only
    paywall_penalty: float = 0.15
    unknown_source_penalty: float = 0.20  # For non-whitelisted sources

    # Soft diversity preferences — tie-breakers WITHIN the hard diversity rules
    # (max 1 source per domain, min 2 source classes enforced in select_top_n)
    same_domain_diminish: float = 0.30   # Reduce score for 2nd source from same domain
    prefer_class_diversity: float = 0.10  # Bonus for new source class

    # Selection
    select_top_n: int = 3


class SourceRanker:
    """
    Guardian Source Ranker v3
    Weighted ranking under two HARD constraints (paper-aligned):
      - authority threshold: sources below MIN_SOURCE_AUTHORITY cannot be cited
      - diversity: max 1 source per domain, min 2 source classes per intervention
    Soft scores only break ties within those hard rules.
    """

    def __init__(self, config: Optional[RankerConfig] = None):
        self.config = config or RankerConfig()
        self.source_class_weights = SOURCE_CLASS_WEIGHTS
        self.domain_whitelist = DOMAIN_WHITELIST
        self.source_profiles = GUARDIAN_SOURCE_PROFILES
        self.current_claim_type: Optional[str] = None
        # Set by select_top_n: True when the min-2-classes diversity rule could
        # not be satisfied, forcing human review instead of a silent violation.
        self.diversity_constraint_unmet: bool = False
        logger.info(
            "SourceRanker v3 initialized (hard authority threshold=%.2f, "
            "max 1/domain, min 2 classes)",
            ImmutableConstraints.MIN_SOURCE_AUTHORITY,
        )

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
        claim_type: Optional[str] = None,
        now_date: Optional[date] = None
    ) -> float:
        """
        Score a single source candidate. No filtering - pure scoring.

        Components:
        - Relevance: keyword overlap
        - Authority: source class weight
        - Topic-Fit: boost for claim-type-preferred sources
        - Recency: exponential decay
        - Prior: retrieval rank signal
        """
        now_date = now_date or date.today()
        domain = self._extract_domain(source.url)

        # 1) Relevance: keyword overlap
        source_text = f"{source.title} {source.snippet}".lower()
        claim_keywords_lower = [kw.lower() for kw in claim_keywords]

        hits = sum(1 for kw in claim_keywords_lower if kw in source_text)
        relevance = min(1.0, hits / max(len(claim_keywords_lower), 1))
        source.relevance_score = relevance

        # 2) Authority: source class weight (soft penalty for unknown, not exclusion)
        base_authority = self.source_class_weights.get(source.source_class, 0.2)
        if source.source_class == SourceClass.UNKNOWN:
            # Soft penalty instead of filtering out
            base_authority = max(0.1, base_authority - self.config.unknown_source_penalty)
        source.authority_score = base_authority

        # 3) Topic-Fit: boost sources that match the claim type profile
        topic_fit = 0.0
        if claim_type and claim_type in self.source_profiles:
            preferred_domains = self.source_profiles[claim_type]
            if any(pref in domain for pref in preferred_domains):
                topic_fit = 1.0  # Full boost for profile match
                logger.debug(f"Topic-fit boost for {domain} (claim_type={claim_type})")
            elif source.source_class in [SourceClass.PRIMARY_INSTITUTION, SourceClass.MULTILATERAL]:
                topic_fit = 0.5  # Half boost for high-authority sources

        # 4) Recency: exponential decay
        if source.published_at:
            days = abs((now_date - source.published_at).days)
        else:
            days = 180  # Assume 6 months old if unknown (less punitive)
        recency = math.exp(-days / 365)
        source.recency_score = recency

        # 5) Prior: weak retrieval rank signal
        prior = 1.0 / (1 + math.log(1 + source.retrieval_rank))

        # 6) Soft accessibility penalty (not exclusion)
        accessibility = 1.0
        if source.paywalled:
            accessibility -= self.config.paywall_penalty

        # Final weighted score - NO thresholds applied here
        score = (
            self.config.weight_relevance * relevance +
            self.config.weight_authority * base_authority +
            self.config.weight_topic_fit * topic_fit +
            self.config.weight_recency * recency +
            self.config.weight_prior * prior
        ) * accessibility

        source.final_score = score
        source.specificity_score = topic_fit  # Repurpose for topic fit
        return score

    def apply_soft_diversity(self, sources: List[SourceCandidate]) -> List[SourceCandidate]:
        """
        Apply soft diversity adjustments to scores - no exclusion, just re-ranking.
        Sources from same domain get diminished scores.
        New source classes get small bonus.
        """
        seen_domains: Dict[str, int] = {}
        seen_classes: Set[SourceClass] = set()

        # Sort by current score first
        sorted_sources = sorted(sources, key=lambda s: s.final_score, reverse=True)

        for source in sorted_sources:
            domain = self._extract_domain(source.url)

            # Diminish score for repeated domains
            if domain in seen_domains:
                count = seen_domains[domain]
                diminish = self.config.same_domain_diminish * count
                source.final_score = max(0.01, source.final_score - diminish)
                logger.debug(f"Diminished {domain} by {diminish:.2f} (seen {count}x)")

            # Small bonus for new source class (diversity reward)
            if source.source_class not in seen_classes:
                source.final_score += self.config.prefer_class_diversity
                seen_classes.add(source.source_class)

            # Track domain
            seen_domains[domain] = seen_domains.get(domain, 0) + 1

        # Re-sort after adjustments
        return sorted(sources, key=lambda s: s.final_score, reverse=True)

    def select_top_n(self, sources: List[SourceCandidate]) -> List[SourceCandidate]:
        """
        Select top N sources under HARD diversity constraints:
          - at most ONE source per domain (hard dedupe, not a score malus)
          - at least TWO distinct source classes per intervention

        If two classes cannot be reached (too few valid sources), the result is
        flagged via self.diversity_constraint_unmet to force human review.

        Inputs are expected to already be citation-eligible (authority filter
        applied in rank_sources) and diversity-adjusted for tie-breaking.
        """
        n = self.config.select_top_n
        ordered = sorted(sources, key=lambda s: s.final_score, reverse=True)

        selected: List[SourceCandidate] = []
        used_domains: Set[str] = set()
        used_classes: Set[SourceClass] = set()

        # First pass: best-scored, hard max one per domain
        for s in ordered:
            if len(selected) >= n:
                break
            domain = self._extract_domain(s.url)
            if domain in used_domains:
                logger.info(
                    "Diversity: dropping duplicate-domain source %s (1/domain rule)",
                    domain,
                )
                continue
            selected.append(s)
            used_domains.add(domain)
            used_classes.add(s.source_class)

        # Enforce minimum two source classes: pull in the best different-class,
        # different-domain candidate, swapping out the weakest pick if full.
        self.diversity_constraint_unmet = False
        if len(used_classes) < 2:
            for s in ordered:
                domain = self._extract_domain(s.url)
                if s.source_class in used_classes or domain in used_domains:
                    continue
                if len(selected) >= n:
                    removed = selected.pop()  # weakest (list is score-descending)
                    used_domains.discard(self._extract_domain(removed.url))
                selected.append(s)
                used_domains.add(domain)
                used_classes.add(s.source_class)
                break

        if len(used_classes) < 2:
            self.diversity_constraint_unmet = True
            logger.warning(
                "Diversity constraint UNMET: only %d source class(es) available "
                "among %d candidates — flagging for human review.",
                len(used_classes), len(sources),
            )

        logger.info(
            f"Selected {len(selected)} sources from {len(sources)} citation-eligible "
            f"candidates (classes={len(used_classes)}, "
            f"diversity_unmet={self.diversity_constraint_unmet})"
        )
        for i, s in enumerate(selected):
            logger.info(f"  {i+1}. {self._extract_domain(s.url)} (score={s.final_score:.3f}, class={s.source_class.value})")

        return selected

    def rank_sources(
        self,
        candidates: List[SourceCandidate],
        claim_keywords: List[str],
        claim_type: Optional[str] = None
    ) -> List[SourceCandidate]:
        """
        Full ranking pipeline v3 with HARD constraints:
        1. Classify sources
        2. HARD authority filter — exclude sub-threshold sources from citation
           (they remain available for retrieval/discovery)
        3. Score each citation-eligible source (with topic-fit boost)
        4. Apply soft diversity adjustments (tie-breaking)
        5. Select top N under hard diversity rules (1/domain, min 2 classes)
        """
        logger.info(f"Ranking {len(candidates)} source candidates (claim_type={claim_type})")
        self.current_claim_type = claim_type
        self.diversity_constraint_unmet = False

        if not candidates:
            return []

        # Step 1: Classify sources
        for source in candidates:
            if source.source_class == SourceClass.UNKNOWN:
                source.source_class = self.classify_source(source.url)

        # Step 2: HARD authority filter — split citation pool from retrieval-only
        threshold = ImmutableConstraints.MIN_SOURCE_AUTHORITY
        citation_pool: List[SourceCandidate] = []
        for source in candidates:
            weight = self.source_class_weights.get(source.source_class, 0.0)
            if weight < threshold:
                source.usage_type = SourceUsageType.RETRIEVAL
                logger.info(
                    "Excluded from citation pool: %s (class=%s, weight=%.2f < %.2f) "
                    "— retained for retrieval/context only",
                    self._extract_domain(source.url),
                    source.source_class.value,
                    weight,
                    threshold,
                )
            else:
                source.usage_type = SourceUsageType.AUTHORITY
                citation_pool.append(source)

        if not citation_pool:
            # No citable evidence — diversity can never be met.
            self.diversity_constraint_unmet = True
            logger.warning(
                "No citation-eligible sources after authority filter "
                "(%d candidates) — flagging for human review.",
                len(candidates),
            )
            return []

        # Step 3: Score citation-eligible sources (with topic-fit)
        for source in citation_pool:
            self.score_source(source, claim_keywords, claim_type=claim_type)

        # Step 4: Apply soft diversity adjustments (tie-breaking only)
        adjusted = self.apply_soft_diversity(citation_pool)

        # Step 5: Select top N under hard diversity constraints
        selected = self.select_top_n(adjusted)

        return selected

    def get_rejection_reasons(
        self,
        candidates: List[SourceCandidate],
        selected: List[SourceCandidate]
    ) -> List[Dict]:
        """Get rejection reasons for non-selected sources (for audit logging)."""
        selected_urls = {s.url for s in selected}
        threshold = ImmutableConstraints.MIN_SOURCE_AUTHORITY
        rejections = []

        for source in candidates:
            if source.url in selected_urls:
                continue

            weight = self.source_class_weights.get(source.source_class, 0.0)
            if getattr(source, "usage_type", SourceUsageType.AUTHORITY) == SourceUsageType.RETRIEVAL \
                    or weight < threshold:
                reason = "below_authority_threshold"
            elif source.source_class == SourceClass.UNKNOWN:
                reason = "unknown_source"
            else:
                reason = "diversity_or_rank_limit"

            rejections.append({
                "url": source.url,
                "reason": reason,
                "source_class": source.source_class.value,
                "final_score": source.final_score
            })

        return rejections[:10]  # Top 10 rejections for logging
