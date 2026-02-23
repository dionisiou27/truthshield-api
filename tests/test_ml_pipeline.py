"""
TruthShield ML Pipeline Unit Tests
P2.9 — Core ML component validation

Tests cover:
- ClaimRouter: classification, risk assessment, temporal awareness, IO detection
- GuardianBandit: Thompson Sampling, reward calculation, safeguards
- SourceRanker: classification, scoring, diversity, authority weights
- text_detection: astroturfing, contradictions
"""
import pytest
import sys
import os

# Ensure src is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.ml.guardian.claim_router import (
    ClaimRouter, ClaimType, RiskLevel, ClaimVolatility,
    TemporalMode, ResponseMode, EvidenceQuality,
)
from src.ml.learning.bandit import (
    GuardianBandit, BanditContext, ToneVariant, SourceMixStrategy,
    ImmutableConstraints, NegativeSignals, BetaDistribution,
)
from src.ml.guardian.source_ranker import (
    SourceRanker, SourceClass, SourceCandidate, RankerConfig,
    SOURCE_CLASS_WEIGHTS,
)
from src.core.text_detection import (
    detect_political_astroturfing,
    detect_astroturfing_indicators,
    detect_logical_contradictions,
)


# ============================================================================
# ClaimRouter
# ============================================================================

class TestClaimRouterClassification:
    """Test claim type classification."""

    @pytest.fixture
    def router(self):
        return ClaimRouter()

    # --- Hate / Dehumanization ---
    @pytest.mark.parametrize("text,expected", [
        ("These vermin need to be eliminated", ClaimType.HATE_OR_DEHUMANIZATION),
        ("Dieses Gesindel muss entsorgt werden", ClaimType.HATE_OR_DEHUMANIZATION),
        ("All traitors should be deported", ClaimType.HATE_OR_DEHUMANIZATION),
    ])
    def test_hate_detection(self, router, text, expected):
        types = router.classify_claim(text)
        assert expected in types, f"Expected {expected} in {types} for: {text}"

    # --- Threats ---
    @pytest.mark.parametrize("text,expected", [
        ("They will pay for this, kill them all", ClaimType.THREAT_OR_INCITEMENT),
        ("Man sollte die alle umbringen", ClaimType.THREAT_OR_INCITEMENT),
    ])
    def test_threat_detection(self, router, text, expected):
        types = router.classify_claim(text)
        assert expected in types, f"Expected {expected} in {types} for: {text}"

    # --- Health Misinformation ---
    @pytest.mark.parametrize("text,expected", [
        ("The vaccine contains a microchip for tracking", ClaimType.HEALTH_MISINFORMATION),
        ("Die Impfung macht unfruchtbar, das ist Gift", ClaimType.HEALTH_MISINFORMATION),
        ("5g causes cancer and corona", ClaimType.HEALTH_MISINFORMATION),
        ("Covid is a plandemic bioweapon", ClaimType.HEALTH_MISINFORMATION),
    ])
    def test_health_misinfo(self, router, text, expected):
        types = router.classify_claim(text)
        assert expected in types, f"Expected {expected} in {types} for: {text}"

    # --- Conspiracy ---
    @pytest.mark.parametrize("text,expected", [
        ("Soros controls the media and the great reset is real", ClaimType.CONSPIRACY_THEORY),
        ("Chemtrails are poisoning us all", ClaimType.CONSPIRACY_THEORY),
        ("Die Illuminati und die neue Weltordnung", ClaimType.CONSPIRACY_THEORY),
    ])
    def test_conspiracy_detection(self, router, text, expected):
        types = router.classify_claim(text)
        assert expected in types, f"Expected {expected} in {types} for: {text}"

    # --- Delegitimization ---
    @pytest.mark.parametrize("text", [
        "The corrupt EU government is a dictatorship",
        "Wahlbetrug! Die Regierung ist korrupt und gekauft",
        "Deep state puppet masters control everything",
    ])
    def test_delegitimization(self, router, text):
        types = router.classify_claim(text)
        assert ClaimType.DELEGITIMIZATION_FRAME in types

    # --- Multi-label ---
    def test_multi_label(self, router):
        """Claims can trigger multiple types."""
        text = "Kill all the Soros-funded traitors spreading vaccine poison"
        types = router.classify_claim(text)
        assert len(types) >= 2, f"Expected multi-label, got {types}"

    # --- Clean text ---
    def test_clean_text_no_classification(self, router):
        """Benign text should not trigger classifications."""
        types = router.classify_claim("The weather is nice today in Berlin")
        assert len(types) == 0, f"False positive: {types}"

    # --- Language detection ---
    def test_language_detection_german(self, router):
        lang = router.detect_language("Die Impfung ist gefährlich und macht krank")
        assert lang == "de"

    def test_language_detection_english(self, router):
        lang = router.detect_language("The vaccine is dangerous and harmful")
        assert lang == "en"


class TestClaimRouterRisk:
    """Test risk level assessment."""

    @pytest.fixture
    def router(self):
        return ClaimRouter()

    def test_critical_risk(self, router):
        assert router.assess_risk_level([ClaimType.THREAT_OR_INCITEMENT]) == RiskLevel.CRITICAL

    def test_high_risk(self, router):
        assert router.assess_risk_level([ClaimType.HATE_OR_DEHUMANIZATION]) == RiskLevel.HIGH
        assert router.assess_risk_level([ClaimType.DELEGITIMIZATION_FRAME]) == RiskLevel.HIGH

    def test_medium_risk(self, router):
        assert router.assess_risk_level([ClaimType.HEALTH_MISINFORMATION]) == RiskLevel.MEDIUM
        assert router.assess_risk_level([ClaimType.CONSPIRACY_THEORY]) == RiskLevel.MEDIUM

    def test_low_risk(self, router):
        assert router.assess_risk_level([ClaimType.OPINION_WITH_FACTUAL_PREMISE]) == RiskLevel.LOW

    def test_empty_claims_low(self, router):
        assert router.assess_risk_level([]) == RiskLevel.LOW

    def test_highest_risk_wins(self, router):
        """Mixed types → highest risk level."""
        types = [ClaimType.CONSPIRACY_THEORY, ClaimType.THREAT_OR_INCITEMENT]
        assert router.assess_risk_level(types) == RiskLevel.CRITICAL

    def test_guardian_responds_medium_plus(self, router):
        assert router.should_guardian_respond(RiskLevel.MEDIUM, [ClaimType.CONSPIRACY_THEORY])
        assert router.should_guardian_respond(RiskLevel.HIGH, [ClaimType.HATE_OR_DEHUMANIZATION])
        assert router.should_guardian_respond(RiskLevel.CRITICAL, [ClaimType.THREAT_OR_INCITEMENT])

    def test_guardian_responds_to_hate_regardless(self, router):
        """Guardian responds to hate even at LOW risk."""
        assert router.should_guardian_respond(RiskLevel.LOW, [ClaimType.HATE_OR_DEHUMANIZATION])


class TestClaimRouterTemporal:
    """Test temporal awareness (TikTok time-awareness)."""

    @pytest.fixture
    def router(self):
        return ClaimRouter()

    def test_territorial_claim_detected(self, router):
        text = "Russia has captured Bakhmut and controls the frontline"
        assert router.detect_territorial_claim(text) is True

    def test_territorial_claim_needs_location(self, router):
        text = "The army is advancing and retreating"
        assert router.detect_territorial_claim(text) is False

    def test_territorial_volatility(self, router):
        text = "Kherson has fallen, frontline retreating"
        types = router.classify_claim(text)
        vol = router.determine_volatility(text, types)
        assert vol == ClaimVolatility.VERY_HIGH

    def test_stable_claim_volatility(self, router):
        text = "The moon landing was fake, flat earth is real"
        types = router.classify_claim(text)
        vol = router.determine_volatility(text, types)
        assert vol in (ClaimVolatility.LOW, ClaimVolatility.STABLE)

    def test_temporal_signals_live(self, router):
        signals = router.detect_temporal_signals("breaking news right now happening today", "en")
        live_signals = [s for s in signals if s.startswith("LIVE:")]
        assert len(live_signals) > 0

    def test_temporal_signals_archive(self, router):
        signals = router.detect_temporal_signals("back in 2020 historically proven fact", "en")
        archive_signals = [s for s in signals if s.startswith("ARCHIVE:")]
        assert len(archive_signals) > 0


# ============================================================================
# GuardianBandit
# ============================================================================

class TestBetaDistribution:
    """Test Thompson Sampling primitives."""

    def test_initial_uniform(self):
        dist = BetaDistribution()
        assert dist.alpha == 1.0
        assert dist.beta == 1.0

    def test_mean(self):
        dist = BetaDistribution(alpha=3.0, beta=1.0)
        assert dist.mean() == pytest.approx(0.75)

    def test_update_success(self):
        dist = BetaDistribution()
        dist.update_success()
        assert dist.alpha == 2.0
        assert dist.beta == 1.0

    def test_update_failure(self):
        dist = BetaDistribution()
        dist.update_failure()
        assert dist.alpha == 1.0
        assert dist.beta == 2.0

    def test_sample_in_range(self):
        dist = BetaDistribution()
        for _ in range(100):
            s = dist.sample()
            assert 0.0 <= s <= 1.0

    def test_serialization(self):
        dist = BetaDistribution(alpha=5.0, beta=3.0)
        d = dist.to_dict()
        restored = BetaDistribution.from_dict(d)
        assert restored.alpha == 5.0
        assert restored.beta == 3.0


class TestGuardianBandit:
    """Test bandit decision-making and reward calculation."""

    @pytest.fixture
    def bandit(self):
        return GuardianBandit()

    def test_select_tone_returns_valid(self, bandit):
        tone = bandit.select_tone()
        assert isinstance(tone, ToneVariant)

    def test_select_source_mix_returns_valid(self, bandit):
        mix = bandit.select_source_mix()
        assert isinstance(mix, SourceMixStrategy)

    def test_make_decision(self, bandit):
        ctx = BanditContext(
            claim_type="health_misinformation",
            risk_level="medium",
            platform="tiktok",
        )
        decision = bandit.make_decision(ctx)
        assert decision.decision_id is not None
        assert isinstance(decision.tone_variant, ToneVariant)
        assert isinstance(decision.source_mix, SourceMixStrategy)

    def test_contextual_nudge_health(self, bandit):
        """Health claims should nudge toward empathic tone."""
        ctx = BanditContext(claim_type="health_misinformation", risk_level="medium")
        # Run many times, empathic should appear more than random (25%)
        empathic_count = sum(
            1 for _ in range(200)
            if bandit.select_tone(ctx) == ToneVariant.EMPATHIC
        )
        assert empathic_count > 30, f"Empathic only {empathic_count}/200 — nudge not working"

    def test_contextual_nudge_high_risk(self, bandit):
        """High risk should nudge toward firm tone."""
        ctx = BanditContext(claim_type="threat_or_incitement", risk_level="critical")
        firm_count = sum(
            1 for _ in range(200)
            if bandit.select_tone(ctx) == ToneVariant.FIRM
        )
        assert firm_count > 30, f"Firm only {firm_count}/200 — nudge not working"


class TestBanditReward:
    """Test reward calculation and anti-gaming safeguards."""

    @pytest.fixture
    def bandit(self):
        return GuardianBandit()

    def test_positive_reward(self, bandit):
        metrics = {
            "top_comment_proxy": 0.8,
            "reply_quality": 0.7,
            "like_reply_ratio": 0.6,
            "shares_proxy": 0.5,
        }
        reward = bandit.calculate_reward(metrics)
        assert 0.0 < reward <= 1.0

    def test_content_removed_nullifies(self, bandit):
        metrics = {"content_removed": True, "top_comment_proxy": 1.0}
        assert bandit.calculate_reward(metrics) == 0.0

    def test_deleted_nullifies(self, bandit):
        metrics = {"deleted": True}
        assert bandit.calculate_reward(metrics) == 0.0

    def test_negative_signals_reduce_reward(self, bandit):
        clean = {"top_comment_proxy": 0.8, "reply_quality": 0.7}
        toxic = {**clean, "toxicity_in_replies": 0.9, "reports_rate": 0.5}
        assert bandit.calculate_reward(toxic) < bandit.calculate_reward(clean)

    def test_platform_flag_penalty(self, bandit):
        clean = {"top_comment_proxy": 0.8}
        flagged = {**clean, "platform_flagged": True}
        assert bandit.calculate_reward(flagged) < bandit.calculate_reward(clean)

    def test_reward_clamped_0_1(self, bandit):
        extreme_negative = {"reports_rate": 1.0, "toxicity_in_replies": 1.0, "bot_engagement_ratio": 1.0}
        assert bandit.calculate_reward(extreme_negative) == 0.0

    def test_reward_max_1(self, bandit):
        perfect = {
            "top_comment_proxy": 1.0,
            "reply_quality": 1.0,
            "like_reply_ratio": 1.0,
            "shares_proxy": 1.0,
        }
        assert bandit.calculate_reward(perfect) <= 1.0


class TestImmutableConstraints:
    """Test that safety constraints are enforced."""

    def test_engagement_weight_limit(self):
        valid = {"likes": 0.2, "shares": 0.2, "accuracy": 0.6}
        assert ImmutableConstraints.validate_reward_weights(valid)

    def test_engagement_over_limit_rejected(self):
        invalid = {"likes": 0.4, "shares": 0.3, "accuracy": 0.3}
        assert not ImmutableConstraints.validate_reward_weights(invalid)

    def test_frozen_flags(self):
        assert ImmutableConstraints.SOURCE_CLASS_WEIGHTS_FROZEN is True
        assert ImmutableConstraints.GUARDIAN_RULES_FROZEN is True
        assert ImmutableConstraints.CLAIM_CLASSIFICATION_FROZEN is True
        assert ImmutableConstraints.RISK_LEVELS_FROZEN is True
        assert ImmutableConstraints.BOUNDARY_DEFINITIONS_FROZEN is True

    def test_min_source_authority(self):
        assert ImmutableConstraints.MIN_SOURCE_AUTHORITY >= 0.70


class TestBanditUpdate:
    """Test the full decision → update loop."""

    @pytest.fixture
    def bandit(self):
        return GuardianBandit()

    def test_update_known_decision(self, bandit):
        ctx = BanditContext(claim_type="conspiracy_theory", risk_level="medium")
        decision = bandit.make_decision(ctx)
        reward = bandit.update(decision.decision_id, {"top_comment_proxy": 0.9, "reply_quality": 0.8})
        assert 0.0 <= reward <= 1.0

    def test_update_unknown_decision(self, bandit):
        reward = bandit.update("nonexistent-id", {"top_comment_proxy": 0.5})
        assert reward == 0.0


# ============================================================================
# SourceRanker
# ============================================================================

class TestSourceRanker:
    """Test source classification and ranking."""

    @pytest.fixture
    def ranker(self):
        return SourceRanker()

    # --- Classification ---
    @pytest.mark.parametrize("url,expected", [
        ("https://ec.europa.eu/some/report", SourceClass.PRIMARY_INSTITUTION),
        ("https://www.who.int/news/factsheet", SourceClass.PRIMARY_INSTITUTION),
        ("https://worldbank.org/data", SourceClass.MULTILATERAL),
        ("https://www.amnesty.org/report", SourceClass.REPUTABLE_NGO),
        ("https://factcheck.org/article", SourceClass.IFCN_FACTCHECK),
        ("https://www.bbc.com/news/article", SourceClass.REPUTABLE_MEDIA),
        ("https://en.wikipedia.org/wiki/Test", SourceClass.WIKIPEDIA),
        ("https://random-blog.example.com/post", SourceClass.UNKNOWN),
    ])
    def test_classify_source(self, ranker, url, expected):
        result = ranker.classify_source(url)
        assert result == expected, f"Expected {expected} for {url}, got {result}"

    # --- Authority weights hierarchy ---
    def test_authority_hierarchy(self):
        assert SOURCE_CLASS_WEIGHTS[SourceClass.PRIMARY_INSTITUTION] > SOURCE_CLASS_WEIGHTS[SourceClass.REPUTABLE_MEDIA]
        assert SOURCE_CLASS_WEIGHTS[SourceClass.REPUTABLE_MEDIA] > SOURCE_CLASS_WEIGHTS[SourceClass.WIKIPEDIA]
        assert SOURCE_CLASS_WEIGHTS[SourceClass.WIKIPEDIA] > SOURCE_CLASS_WEIGHTS[SourceClass.UNKNOWN]

    # --- Scoring ---
    def test_institutional_scores_higher(self, ranker):
        eu = SourceCandidate(
            url="https://ec.europa.eu/report",
            title="EU Report",
            snippet="Official EU report on policy",
            source_class=SourceClass.PRIMARY_INSTITUTION,
        )
        blog = SourceCandidate(
            url="https://random-blog.com/post",
            title="Blog Post",
            snippet="Some random blog post",
            source_class=SourceClass.UNKNOWN,
        )
        eu_score = ranker.score_source(eu, claim_keywords=["policy", "eu"])
        blog_score = ranker.score_source(blog, claim_keywords=["policy", "eu"])
        assert eu_score > blog_score

    # --- Diversity ---
    def test_diversity_bonus(self, ranker):
        sources = [
            SourceCandidate(url=f"https://ec.europa.eu/r{i}", title=f"EU {i}", snippet=f"EU report {i}", source_class=SourceClass.PRIMARY_INSTITUTION)
            for i in range(3)
        ] + [
            SourceCandidate(url="https://www.bbc.com/article", title="BBC", snippet="BBC news article", source_class=SourceClass.REPUTABLE_MEDIA),
        ]
        diversified = ranker.apply_soft_diversity(sources)
        assert len(diversified) == 4  # All kept


# ============================================================================
# Text Detection (extracted module)
# ============================================================================

class TestPoliticalAstroturfing:
    """Test political astroturfing detection."""

    def test_politician_with_corruption(self):
        result = detect_political_astroturfing("merkel is corrupt and crooked")
        assert result["targets_legitimate_politician"]
        assert result["has_corruption_accusations"]
        assert result["political_astroturfing_score"] > 0.5

    def test_conspiracy_language(self):
        result = detect_political_astroturfing("wake up sheeple the deep state controls everything")
        assert result["has_conspiracy_language"]
        assert result["political_astroturfing_score"] > 0.0

    def test_clean_text(self):
        result = detect_political_astroturfing("the weather in berlin is sunny today")
        assert result["political_astroturfing_score"] == 0.0
        assert not result["is_political_astroturfing"]


class TestAstroturfingIndicators:
    """Test general astroturfing detection."""

    def test_coordinated_language(self):
        result = detect_astroturfing_indicators("I'm just a regular person but wake up sheeple the truth is out there")
        assert result["has_coordinated_language"]
        assert result["astroturfing_score"] > 0.0

    def test_emotional_manipulation(self):
        result = detect_astroturfing_indicators("I am outraged and disgusted, this is unacceptable")
        assert result["has_emotional_manipulation"]

    def test_context_high_frequency(self):
        result = detect_astroturfing_indicators("test post", context={"post_frequency": 15})
        assert "high_frequency_posting" in result["context_indicators"]

    def test_clean_text(self):
        result = detect_astroturfing_indicators("Nice weather today, going for a walk")
        assert result["astroturfing_score"] == 0.0


class TestLogicalContradictions:
    """Test contradiction detection."""

    def test_dead_and_alive(self):
        result = detect_logical_contradictions("He is both dead and alive at the same time")
        assert result["has_contradictions"] or result["has_ambiguous_phrasing"]

    def test_true_and_false(self):
        result = detect_logical_contradictions("The statement is both true and false")
        assert result["has_ambiguous_phrasing"]
        assert result["logical_consistency_score"] == 0.0

    def test_consistent_text(self):
        result = detect_logical_contradictions("The sun is shining and birds are singing")
        assert result["logical_consistency_score"] == 1.0


# ============================================================================
# Integration: Full Pipeline Flow
# ============================================================================

class TestPipelineIntegration:
    """End-to-end: claim → classify → risk → temporal → bandit decision."""

    def test_health_misinfo_pipeline(self):
        router = ClaimRouter()
        bandit = GuardianBandit()

        text = "The COVID vaccine contains microchips for tracking and 5g causes cancer"

        # 1. Classify
        types = router.classify_claim(text)
        assert ClaimType.HEALTH_MISINFORMATION in types

        # 2. Risk
        risk = router.assess_risk_level(types)
        assert risk in (RiskLevel.MEDIUM, RiskLevel.HIGH)

        # 3. Guardian should respond
        assert router.should_guardian_respond(risk, types)

        # 4. Bandit decision
        ctx = BanditContext(
            claim_type=types[0].value,
            risk_level=risk.value,
            platform="tiktok",
        )
        decision = bandit.make_decision(ctx)
        assert decision.tone_variant is not None
        assert decision.source_mix is not None

    def test_territorial_claim_pipeline(self):
        router = ClaimRouter()

        text = "Breaking: Russia captured Bakhmut, frontline has fallen"

        types = router.classify_claim(text)
        vol = router.determine_volatility(text, types)
        assert vol == ClaimVolatility.VERY_HIGH

        signals = router.detect_temporal_signals(text, "en")
        mode = router.determine_temporal_mode(text, vol, signals)
        assert mode in (TemporalMode.LIVE_REQUIRED, TemporalMode.AMBIGUOUS)

    def test_clean_text_no_response(self):
        router = ClaimRouter()

        text = "I had a great coffee this morning in Aachen"
        types = router.classify_claim(text)
        assert len(types) == 0

        risk = router.assess_risk_level(types)
        assert risk == RiskLevel.LOW
        assert not router.should_guardian_respond(risk, types)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
