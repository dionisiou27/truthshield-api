"""
RSS Freshness Service
Compliance-safe ingestion of trusted sources via RSS feeds.
No HTML scraping - only RSS polling + link pinning.

Primary Use Case: Territorial/frontline claims requiring LIVE verification.
"""
import asyncio
import logging
from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import hashlib
import re

import httpx
import feedparser

logger = logging.getLogger(__name__)


# =============================================================================
# SOURCE REGISTRY - RSS-enabled trusted sources
# =============================================================================
# Only sources with explicit RSS feeds for compliance-safe ingestion.
# GPTBot/robots.txt restrictions don't apply to RSS feeds.

@dataclass
class RSSSourceConfig:
    """Configuration for an RSS-enabled source."""
    id: str
    base_domain: str
    trust_tier: str  # A, B, C
    rss_url: str
    poll_minutes: int = 10
    language: str = "en"
    # What we can use the content for
    allowed_usage: Set[str] = field(default_factory=lambda: {"freshness_check", "citation_link", "snippet_only"})
    # IO-aware: does this source explicitly name IO campaigns?
    names_io_campaigns: bool = False
    # Topics this source is authoritative for
    topics: List[str] = field(default_factory=list)
    # Tier B sources: require corroboration for certain claim types
    corroboration_required_for: List[str] = field(default_factory=list)
    # Rationale for trust tier (for audit trail)
    trust_rationale: str = ""


RSS_SOURCE_REGISTRY: Dict[str, RSSSourceConfig] = {
    "ERR_NEWS_EN": RSSSourceConfig(
        id="ERR_NEWS_EN",
        base_domain="news.err.ee",
        trust_tier="A",
        rss_url="https://news.err.ee/rss",
        poll_minutes=10,
        language="en",
        names_io_campaigns=True,  # ERR explicitly names Russian IO campaigns
        topics=["territorial_control", "foreign_influence", "eastern_europe"],
    ),
    "REUTERS": RSSSourceConfig(
        id="REUTERS",
        base_domain="reuters.com",
        trust_tier="A",
        rss_url="https://www.reuters.com/rssFeed/worldNews",
        poll_minutes=15,
        language="en",
        topics=["territorial_control", "foreign_influence", "general"],
    ),
    "AP_NEWS": RSSSourceConfig(
        id="AP_NEWS",
        base_domain="apnews.com",
        trust_tier="A",
        rss_url="https://rsshub.app/apnews/topics/world-news",  # Via RSSHub
        poll_minutes=15,
        language="en",
        topics=["territorial_control", "general"],
    ),
    "DW_EN": RSSSourceConfig(
        id="DW_EN",
        base_domain="dw.com",
        trust_tier="A",
        rss_url="https://rss.dw.com/xml/rss-en-world",
        poll_minutes=15,
        language="en",
        topics=["territorial_control", "foreign_influence", "europe"],
    ),
    "EUVSDISINFO": RSSSourceConfig(
        id="EUVSDISINFO",
        base_domain="euvsdisinfo.eu",
        trust_tier="A",
        rss_url="https://euvsdisinfo.eu/feed/",
        poll_minutes=30,
        language="en",
        names_io_campaigns=True,  # Primary IO documentation source
        topics=["foreign_influence", "io_patterns"],
        trust_rationale="EU official IO documentation project",
    ),
    # =========================================================================
    # TIER B SOURCES - Useful for freshness, require corroboration for hard facts
    # =========================================================================
    "RBC_UKRAINE_EN": RSSSourceConfig(
        id="RBC_UKRAINE_EN",
        base_domain="newsukraine.rbc.ua",
        trust_tier="B",
        # RBC main RSS feed (covers all news including English edition content)
        rss_url="https://www.rbc.ua/rus/rss.shtml",
        poll_minutes=10,  # Fast polling for recency
        language="en",
        names_io_campaigns=True,  # RBC covers IO/fakes explicitly
        topics=["territorial_control", "policy_mobilization", "ukraine_war"],
        # CRITICAL: Tier B = require second source for territorial claims
        corroboration_required_for=["territorial_control", "frontline_update"],
        trust_rationale="Large Ukrainian news agency; useful for fast recency signals. "
                       "Not an official operational authority; treat frontline claims as corroboration-needed.",
    ),
}


@dataclass
class FreshnessHit:
    """A relevant article found via RSS freshness check."""
    source_id: str
    url: str
    title: str
    published: datetime
    snippet: str
    relevance_keywords: List[str]
    names_io_frame: bool = False  # If article explicitly names IO campaign
    # Trust tier from source config
    trust_tier: str = "A"
    # Does this source require corroboration for this claim type?
    requires_corroboration: bool = False


class RSSFreshnessService:
    """
    RSS-based freshness checking for territorial/frontline claims.

    Workflow:
    1. Poll RSS feeds of trusted sources
    2. Cache recent articles (24-72h window)
    3. On LIVE_REQUIRED claim: semantic match against cache
    4. If hit: boost evidence_quality, provide citation link
    """

    def __init__(self, cache_hours: int = 72):
        self.cache_hours = cache_hours
        self.registry = RSS_SOURCE_REGISTRY
        # In-memory cache: source_id -> List[FreshnessHit]
        self._cache: Dict[str, List[FreshnessHit]] = {}
        self._last_poll: Dict[str, datetime] = {}
        self._http_client: Optional[httpx.AsyncClient] = None
        logger.info(f"RSSFreshnessService initialized with {len(self.registry)} sources")

    async def _get_client(self) -> httpx.AsyncClient:
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(
                timeout=30.0,
                headers={"User-Agent": "TruthShield/1.0 RSS Reader"},
            )
        return self._http_client

    async def close(self):
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()

    async def poll_source(self, source_id: str) -> List[FreshnessHit]:
        """
        Poll a single RSS source and cache recent articles.
        """
        if source_id not in self.registry:
            logger.warning(f"Unknown source_id: {source_id}")
            return []

        config = self.registry[source_id]

        # Check if we need to poll (respect poll_minutes)
        last_poll = self._last_poll.get(source_id)
        if last_poll:
            minutes_since = (datetime.now() - last_poll).total_seconds() / 60
            if minutes_since < config.poll_minutes:
                logger.debug(f"Skipping {source_id} poll (last: {minutes_since:.1f}m ago)")
                return self._cache.get(source_id, [])

        try:
            client = await self._get_client()
            response = await client.get(config.rss_url)
            response.raise_for_status()

            # Parse RSS feed
            feed = feedparser.parse(response.text)

            hits = []
            cutoff = datetime.now() - timedelta(hours=self.cache_hours)

            for entry in feed.entries[:50]:  # Limit to recent 50
                # Parse publish date
                published = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    published = datetime(*entry.published_parsed[:6])
                elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                    published = datetime(*entry.updated_parsed[:6])
                else:
                    published = datetime.now()  # Assume recent if no date

                # Skip old articles
                if published < cutoff:
                    continue

                # Extract data
                title = entry.get('title', '')
                link = entry.get('link', '')
                summary = entry.get('summary', entry.get('description', ''))

                # Clean HTML from summary
                summary = re.sub(r'<[^>]+>', '', summary)[:500]

                hit = FreshnessHit(
                    source_id=source_id,
                    url=link,
                    title=title,
                    published=published,
                    snippet=summary,
                    relevance_keywords=self._extract_keywords(title + " " + summary),
                    names_io_frame=config.names_io_campaigns and self._detects_io_frame(title + " " + summary),
                    trust_tier=config.trust_tier,
                    # Will be set based on claim_type in check_freshness
                    requires_corroboration=False,
                )
                hits.append(hit)

            # Update cache
            self._cache[source_id] = hits
            self._last_poll[source_id] = datetime.now()

            logger.info(f"📰 Polled {source_id}: {len(hits)} articles in {self.cache_hours}h window")
            return hits

        except Exception as e:
            logger.error(f"Failed to poll {source_id}: {e}")
            return self._cache.get(source_id, [])

    async def poll_all_sources(self) -> Dict[str, int]:
        """Poll all registered RSS sources."""
        results = {}
        for source_id in self.registry:
            hits = await self.poll_source(source_id)
            results[source_id] = len(hits)
        return results

    async def check_freshness(
        self,
        keywords: List[str],
        locations: Optional[List[str]] = None,
        hours_window: int = 72,
        claim_type: Optional[str] = None,
    ) -> List[FreshnessHit]:
        """
        Check for fresh coverage of a claim.

        Args:
            keywords: Claim keywords to match
            locations: Specific locations (Kupiansk, Pokrovsk, etc.)
            hours_window: How recent the article must be
            claim_type: Claim type for corroboration checking (e.g., "territorial_control")

        Returns:
            List of relevant FreshnessHit objects with corroboration flags set
        """
        # Ensure sources are polled
        await self.poll_all_sources()

        cutoff = datetime.now() - timedelta(hours=hours_window)
        keywords_lower = [kw.lower() for kw in keywords]
        locations_lower = [loc.lower() for loc in (locations or [])]

        matches = []

        for source_id, hits in self._cache.items():
            # Get source config for corroboration check
            config = self.registry.get(source_id)

            for hit in hits:
                # Skip if too old
                if hit.published < cutoff:
                    continue

                # Check keyword match
                text = (hit.title + " " + hit.snippet).lower()
                keyword_hits = sum(1 for kw in keywords_lower if kw in text)

                # Check location match (stronger signal)
                location_hits = sum(1 for loc in locations_lower if loc in text)

                # Relevance threshold
                if keyword_hits >= 2 or location_hits >= 1:
                    # Set corroboration requirement based on claim_type
                    if claim_type and config and config.corroboration_required_for:
                        hit.requires_corroboration = claim_type in config.corroboration_required_for
                    matches.append(hit)

        # Sort by recency
        matches.sort(key=lambda h: h.published, reverse=True)

        logger.info(f"🔍 Freshness check: {len(matches)} matches for keywords={keywords[:3]}, locations={locations}")
        return matches[:10]  # Top 10

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract significant keywords from text."""
        # Simple keyword extraction
        words = re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())
        # Remove common words
        stop_words = {'this', 'that', 'with', 'from', 'have', 'been', 'were', 'they', 'their', 'said', 'would', 'could'}
        return [w for w in words if w not in stop_words][:20]

    def _detects_io_frame(self, text: str) -> bool:
        """
        Check if article explicitly names IO/propaganda campaign.
        This is gold for our IO-awareness routing.
        """
        text_lower = text.lower()
        io_indicators = [
            "fake news", "disinformation", "propaganda",
            "information operation", "information campaign",
            "russian narrative", "kremlin narrative",
            "influence operation", "coordinated campaign",
            "false claim", "debunked",
        ]
        return any(ind in text_lower for ind in io_indicators)


# =============================================================================
# INTEGRATION HELPERS
# =============================================================================

async def check_territorial_freshness(
    claim_keywords: List[str],
    locations: List[str],
    claim_type: str = "territorial_control",
) -> Dict:
    """
    Convenience function for territorial claims.
    Returns freshness assessment for routing decisions.

    Args:
        claim_keywords: Keywords to search for
        locations: Location names to match
        claim_type: Claim type for corroboration checking (default: territorial_control)
    """
    service = RSSFreshnessService()
    try:
        hits = await service.check_freshness(
            keywords=claim_keywords,
            locations=locations,
            hours_window=72,
            claim_type=claim_type,
        )

        # Analyze hits
        has_recent = len(hits) > 0
        has_io_frame = any(h.names_io_frame for h in hits)
        newest_hit = hits[0] if hits else None

        # Corroboration analysis
        # Tier A sources that don't require corroboration
        tier_a_hits = [h for h in hits if h.trust_tier == "A"]
        # Tier B sources that need corroboration for this claim type
        needs_corroboration = [h for h in hits if h.requires_corroboration]

        # Has corroborated evidence = at least one Tier A hit, or 2+ Tier B hits
        has_corroborated = len(tier_a_hits) >= 1 or len(hits) >= 2

        return {
            "has_fresh_coverage": has_recent,
            "article_count": len(hits),
            "has_io_frame_named": has_io_frame,
            "newest_article": {
                "url": newest_hit.url if newest_hit else None,
                "title": newest_hit.title if newest_hit else None,
                "published": newest_hit.published.isoformat() if newest_hit else None,
                "source": newest_hit.source_id if newest_hit else None,
                "trust_tier": newest_hit.trust_tier if newest_hit else None,
                "requires_corroboration": newest_hit.requires_corroboration if newest_hit else None,
            } if newest_hit else None,
            # Corroboration status
            "corroboration": {
                "tier_a_count": len(tier_a_hits),
                "needs_corroboration_count": len(needs_corroboration),
                "is_corroborated": has_corroborated,
                "warning": "Single Tier B source - seek corroboration" if (
                    len(hits) == 1 and hits[0].requires_corroboration
                ) else None,
            },
            "evidence_boost": 0.2 if has_recent else 0.0,  # Boost for routing
            "io_boost": 0.15 if has_io_frame else 0.0,     # Additional IO signal
            # Adjust evidence boost based on corroboration
            "corroborated_evidence_boost": 0.25 if has_corroborated else 0.1 if has_recent else 0.0,
        }
    finally:
        await service.close()


# Singleton instance for reuse
_rss_service: Optional[RSSFreshnessService] = None


def get_rss_service() -> RSSFreshnessService:
    """Get or create the global RSS service instance."""
    global _rss_service
    if _rss_service is None:
        _rss_service = RSSFreshnessService()
    return _rss_service
