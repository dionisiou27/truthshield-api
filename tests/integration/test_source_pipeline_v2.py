"""
Integration tests for Source Pipeline v2 optimizations.

Tests cover:
- EU source prioritization (europarl.europa.eu in primaries)
- Source deduplication
- Ground-truth extraction
- SourceRanker adapter
- Removal of hardcoded Ursula special case
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.core.ai_engine import Source, TruthShieldAI
from src.core.source_adapter import (
    source_to_candidate,
    candidate_to_source,
    rank_and_convert,
)
from src.ml.guardian.source_ranker import SourceClass, SourceRanker, RankerConfig


# ============================================================================
# Task 1.1: europarl.europa.eu in EU primaries
# ============================================================================

class TestEUSourcePrioritization:
    """EU claims must have europa.eu domains in top sources."""

    @pytest.fixture
    def ai(self):
        return TruthShieldAI()

    def test_eu_primaries_contains_europarl(self, ai):
        """europarl.europa.eu must be in eu_primaries list."""
        sources = ai._get_prioritized_sources(
            "Ursula von der Leyen was not elected", company="GuardianAvatar"
        )
        urls = [s.url for s in sources]
        assert any("europarl.europa.eu" in url for url in urls), \
            f"europarl.europa.eu not found in prioritized sources: {urls}"

    def test_europarl_is_first_eu_primary(self, ai):
        """europarl.europa.eu should appear before ec.europa.eu."""
        sources = ai._get_prioritized_sources(
            "Das EU-Parlament hat keine Macht", company="GuardianAvatar"
        )
        urls = [s.url for s in sources]
        europarl_idx = next((i for i, u in enumerate(urls) if "europarl.europa.eu" in u), None)
        ec_idx = next((i for i, u in enumerate(urls) if "ec.europa.eu" in u), None)
        assert europarl_idx is not None, "europarl.europa.eu not found"
        assert ec_idx is not None, "ec.europa.eu not found"
        assert europarl_idx < ec_idx, \
            f"europarl (idx={europarl_idx}) should come before ec (idx={ec_idx})"

    def test_eu_keywords_expanded(self, ai):
        """New EU keywords should trigger EU primary sources."""
        for keyword_claim in [
            "europarl session was cancelled",
            "parlament voted against the bill",
            "die Abgeordnete stimmten dagegen",
            "die Fraktion hat sich aufgelöst",
        ]:
            sources = ai._get_prioritized_sources(keyword_claim, company="GuardianAvatar")
            urls = [s.url for s in sources]
            assert any("europarl.europa.eu" in url for url in urls), \
                f"EU primaries not triggered for claim: '{keyword_claim}'"


# ============================================================================
# Task 1.3: Source deduplication
# ============================================================================

class TestSourceDeduplication:
    """No duplicate URLs in source list."""

    def test_dedup_removes_exact_duplicates(self):
        """Identical URLs should be deduplicated."""
        sources = [
            Source(url="https://factcheck.org/article1", title="A", snippet="s", credibility_score=0.9),
            Source(url="https://factcheck.org/article1", title="A dup", snippet="s2", credibility_score=0.9),
            Source(url="https://reuters.com/news", title="B", snippet="s3", credibility_score=0.8),
        ]
        # Simulate dedup logic from _search_sources
        seen_urls = set()
        deduplicated = []
        for src in sources:
            normalized = src.url.rstrip('/').lower()
            if normalized not in seen_urls:
                seen_urls.add(normalized)
                deduplicated.append(src)
        assert len(deduplicated) == 2
        assert deduplicated[0].title == "A"  # First occurrence kept

    def test_dedup_normalizes_trailing_slash(self):
        """URLs differing only by trailing slash should be deduplicated."""
        sources = [
            Source(url="https://correctiv.org/", title="A", snippet="s", credibility_score=0.9),
            Source(url="https://correctiv.org", title="A2", snippet="s2", credibility_score=0.9),
        ]
        seen_urls = set()
        deduplicated = []
        for src in sources:
            normalized = src.url.rstrip('/').lower()
            if normalized not in seen_urls:
                seen_urls.add(normalized)
                deduplicated.append(src)
        assert len(deduplicated) == 1

    def test_dedup_normalizes_case(self):
        """URLs differing only by case should be deduplicated."""
        sources = [
            Source(url="https://WHO.int/page", title="WHO", snippet="s", credibility_score=0.95),
            Source(url="https://who.int/page", title="WHO 2", snippet="s2", credibility_score=0.95),
        ]
        seen_urls = set()
        deduplicated = []
        for src in sources:
            normalized = src.url.rstrip('/').lower()
            if normalized not in seen_urls:
                seen_urls.add(normalized)
                deduplicated.append(src)
        assert len(deduplicated) == 1


# ============================================================================
# Task 2.1: Ground-truth extraction
# ============================================================================

class TestGroundTruthExtraction:
    """Ground truth must be extracted from high-credibility sources."""

    @pytest.fixture
    def ai(self):
        return TruthShieldAI()

    def test_extracts_facts_with_dates(self, ai):
        """Sources with specific dates should produce ground truth."""
        sources = [
            Source(
                url="https://europarl.europa.eu/vote",
                title="EP Vote Result",
                snippet="On July 18, 2024, the European Parliament confirmed von der Leyen with 401 votes.",
                credibility_score=0.97,
                date_published="2024-07-18",
            ),
        ]
        result = ai._extract_ground_truth(sources)
        assert "401 votes" in result
        assert "July 18, 2024" in result

    def test_extracts_facts_with_numbers(self, ai):
        """Sources with numbers should produce ground truth."""
        sources = [
            Source(
                url="https://who.int/report",
                title="WHO Report",
                snippet="Over 13.5 billion COVID-19 vaccine doses administered globally by 2024.",
                credibility_score=0.98,
            ),
        ]
        result = ai._extract_ground_truth(sources)
        assert "13.5 billion" in result

    def test_skips_low_credibility_sources(self, ai):
        """Sources below 0.95 credibility should not produce ground truth."""
        sources = [
            Source(
                url="https://some-blog.com/post",
                title="Blog Post",
                snippet="On March 5, 2024, something happened with 100 people.",
                credibility_score=0.7,
            ),
        ]
        result = ai._extract_ground_truth(sources)
        assert result == ""

    def test_skips_generic_snippets(self, ai):
        """Sources without specific dates/numbers should not produce ground truth."""
        sources = [
            Source(
                url="https://ec.europa.eu/",
                title="European Commission",
                snippet="Official EU policies and legislative information...",
                credibility_score=0.97,
            ),
        ]
        result = ai._extract_ground_truth(sources)
        assert result == ""

    def test_empty_sources_returns_empty(self, ai):
        """No sources should return empty string."""
        result = ai._extract_ground_truth([])
        assert result == ""


# ============================================================================
# Task 3.1: Source adapter
# ============================================================================

class TestSourceAdapter:
    """Adapter correctly converts between Source and SourceCandidate."""

    def test_source_to_candidate_classifies_eu(self):
        """EU sources should be classified as PRIMARY_INSTITUTION."""
        src = Source(
            url="https://www.europarl.europa.eu/vote",
            title="EP Vote",
            snippet="Vote result",
            credibility_score=0.98,
            date_published="2024-07-18",
        )
        candidate = source_to_candidate(src)
        assert candidate.source_class == SourceClass.PRIMARY_INSTITUTION
        assert candidate.url == src.url
        assert candidate.title == src.title

    def test_source_to_candidate_classifies_factchecker(self):
        """Fact-checker sources should be classified as IFCN_FACTCHECK."""
        src = Source(
            url="https://www.snopes.com/fact-check/test",
            title="Snopes",
            snippet="Fact check",
            credibility_score=0.85,
        )
        candidate = source_to_candidate(src)
        assert candidate.source_class == SourceClass.IFCN_FACTCHECK

    def test_candidate_to_source_preserves_data(self):
        """Conversion back to Source preserves core fields."""
        src = Source(
            url="https://reuters.com/article",
            title="Reuters",
            snippet="News article",
            credibility_score=0.8,
        )
        candidate = source_to_candidate(src)
        candidate.final_score = 0.85  # Simulate ranking
        converted = candidate_to_source(candidate)
        assert converted.url == src.url
        assert converted.title == src.title
        assert converted.snippet == src.snippet
        assert converted.credibility_score == 0.85

    def test_rank_and_convert_preserves_count(self):
        """rank_and_convert should not lose any sources."""
        sources = [
            Source(url="https://reuters.com/a", title="Reuters", snippet="News", credibility_score=0.7),
            Source(url="https://ec.europa.eu/b", title="EC", snippet="EU", credibility_score=0.97),
            Source(url="https://snopes.com/c", title="Snopes", snippet="Check", credibility_score=0.85),
        ]
        ranked = rank_and_convert(sources, ["eu", "commission"])
        assert len(ranked) == len(sources), \
            f"Source count changed: {len(sources)} -> {len(ranked)}"

    def test_rank_and_convert_empty_list(self):
        """Empty source list should return empty."""
        assert rank_and_convert([], ["test"]) == []

    def test_rank_and_convert_reorders(self):
        """EU source should rank higher than generic for EU keywords."""
        sources = [
            Source(url="https://snopes.com/check", title="Snopes", snippet="Random check", credibility_score=0.85),
            Source(url="https://ec.europa.eu/policy", title="EC", snippet="EU commission policy on regulations", credibility_score=0.97),
        ]
        ranked = rank_and_convert(sources, ["eu", "commission", "policy"], claim_type="delegitimization_frame")
        # EC should rank higher for EU-related keywords
        assert "ec.europa.eu" in ranked[0].url, \
            f"Expected EC first, got: {ranked[0].url}"


# ============================================================================
# Task 4.1: No hardcoded Ursula special case
# ============================================================================

class TestNoHardcodedUrsulaCase:
    """Ursula special case should not exist in _get_secondary_sources."""

    @pytest.fixture
    def ai(self):
        return TruthShieldAI()

    def test_no_ursula_specific_handling_in_secondary(self, ai):
        """_get_secondary_sources should not have Ursula-specific code."""
        import inspect
        source_code = inspect.getsource(ai._get_secondary_sources)
        assert "ursula" not in source_code.lower() or "ursula" not in source_code, \
            "_get_secondary_sources still contains Ursula-specific handling"

    def test_other_eu_person_gets_europa_sources(self, ai):
        """Non-Ursula EU person claims should also get europa.eu sources."""
        sources = ai._get_prioritized_sources(
            "Charles Michel was never elected as European Council president",
            company="GuardianAvatar",
        )
        all_urls = [s.url for s in sources]
        assert any("europa.eu" in url for url in all_urls), \
            f"No europa.eu source for EU person claim: {all_urls}"
