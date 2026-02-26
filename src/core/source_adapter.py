"""Adapter between ai_engine.Source and source_ranker.SourceCandidate."""
from typing import List, Optional
from datetime import date
import logging

from src.core.ai_engine import Source
from src.ml.guardian.source_ranker import (
    SourceCandidate,
    SourceClass,
    SourceRanker,
    RankerConfig,
    DOMAIN_WHITELIST,
)

logger = logging.getLogger(__name__)


def _parse_date(date_str: Optional[str]) -> Optional[date]:
    """Parse a date string (YYYY-MM-DD) into a date object."""
    if not date_str:
        return None
    try:
        return date.fromisoformat(date_str)
    except (ValueError, TypeError):
        return None


def source_to_candidate(src: Source, rank: int = 0) -> SourceCandidate:
    """Convert ai_engine Source to SourceRanker SourceCandidate."""
    url_lower = src.url.lower()
    source_class = SourceClass.UNKNOWN

    for domain, sc in DOMAIN_WHITELIST.items():
        if domain in url_lower:
            source_class = sc
            break

    return SourceCandidate(
        url=src.url,
        title=src.title,
        snippet=src.snippet,
        source_class=source_class,
        published_at=_parse_date(src.date_published),
        retrieval_rank=rank,
    )


def candidate_to_source(candidate: SourceCandidate) -> Source:
    """Convert ranked SourceCandidate back to ai_engine Source."""
    return Source(
        url=candidate.url,
        title=candidate.title,
        snippet=candidate.snippet,
        credibility_score=candidate.final_score if candidate.final_score > 0 else 0.5,
        date_published=str(candidate.published_at) if candidate.published_at else "",
    )


def rank_and_convert(
    sources: List[Source],
    keywords: List[str],
    claim_type: Optional[str] = None,
) -> List[Source]:
    """Full pipeline: convert -> rank -> convert back. Returns ALL sources ranked."""
    if not sources:
        return sources

    # Use a config that returns all sources (not just top 3)
    config = RankerConfig(select_top_n=len(sources))
    ranker = SourceRanker(config=config)

    candidates = [source_to_candidate(s, rank=i) for i, s in enumerate(sources)]
    ranked = ranker.rank_sources(candidates, keywords, claim_type=claim_type)

    return [candidate_to_source(r) for r in ranked]
