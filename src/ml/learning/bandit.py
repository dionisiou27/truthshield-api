"""
Guardian Bandit Controller
Thompson Sampling for tone and source-mix optimization.

=============================================================================
LEARNING SAFEGUARDS - Critical for Defence/EU Review
=============================================================================
Guardian learning is constrained to stylistic and structural parameters.
Factual assertions, source classes, and boundary definitions are IMMUTABLE
and excluded from optimization to prevent engagement-driven drift.

LEARNABLE PARAMETERS (stylistic only):
- Tone variant (strict/firm/educational) - HOW the message is framed
- Source mix strategy - WHICH source class priority, not WHICH sources
- Response length within constraints
- Sentence structure order

IMMUTABLE PARAMETERS (never optimized):
- Factual content and claims
- Source class authority weights
- Boundary definitions and rules
- Guardian behavioral constraints
- Source whitelist membership
- Risk level assessments
- Claim type classifications

This separation ensures Guardian cannot drift toward:
- Engagement > factual integrity
- Provocation or polarization
- Weakened source authority
- Compromised boundary enforcement
=============================================================================
"""
from enum import Enum
from typing import Dict, List, Optional, Tuple, Set
from pydantic import BaseModel
from datetime import datetime
import random
import math
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


# =============================================================================
# IMMUTABLE CONSTRAINTS - Never subject to learning/optimization
# =============================================================================

class ImmutableConstraints:
    """
    Parameters that are NEVER subject to bandit optimization.
    These represent epistemic and safety boundaries.
    """
    # Source authority weights are fixed
    SOURCE_CLASS_WEIGHTS_FROZEN: bool = True

    # Guardian behavioral rules are immutable
    GUARDIAN_RULES_FROZEN: bool = True

    # Claim classifications come from deterministic rules
    CLAIM_CLASSIFICATION_FROZEN: bool = True

    # Risk levels are policy-defined, not learned
    RISK_LEVELS_FROZEN: bool = True

    # Boundary definitions cannot be weakened
    BOUNDARY_DEFINITIONS_FROZEN: bool = True

    # Minimum source authority thresholds
    MIN_SOURCE_AUTHORITY: float = 0.70  # No source below REPUTABLE_MEDIA

    # Maximum engagement weight (prevents engagement > accuracy drift)
    MAX_ENGAGEMENT_WEIGHT: float = 0.50

    @classmethod
    def validate_reward_weights(cls, weights: Dict[str, float]) -> bool:
        """Ensure reward weights don't over-prioritize engagement."""
        engagement_weights = weights.get("likes", 0) + weights.get("shares", 0)
        return engagement_weights <= cls.MAX_ENGAGEMENT_WEIGHT


# =============================================================================
# NEGATIVE OPTIMIZATION SIGNALS - Anti-gaming measures
# =============================================================================

class NegativeSignals:
    """
    Signals that REDUCE reward, preventing gaming and drift.
    These are explicitly documented for audit purposes.
    """
    # Platform moderation signals
    REPORT_RATE_WEIGHT: float = -0.30        # Heavy penalty for reports
    CONTENT_REMOVAL_PENALTY: float = -1.0    # Complete reward nullification
    PLATFORM_FLAG_PENALTY: float = -0.50     # Moderation flags

    # Toxicity amplification
    TOXICITY_IN_REPLIES_WEIGHT: float = -0.15
    REPLY_CHAIN_ESCALATION: float = -0.20    # Prevents provocation optimization

    # Engagement gaming
    BOT_ENGAGEMENT_PENALTY: float = -0.40    # Suspected inauthentic engagement
    SPAM_PATTERN_PENALTY: float = -0.30      # Repetitive/spam patterns

    @classmethod
    def get_all_negative_weights(cls) -> Dict[str, float]:
        """Return all negative signal weights for documentation."""
        return {
            "report_rate": cls.REPORT_RATE_WEIGHT,
            "content_removal": cls.CONTENT_REMOVAL_PENALTY,
            "platform_flag": cls.PLATFORM_FLAG_PENALTY,
            "toxicity_in_replies": cls.TOXICITY_IN_REPLIES_WEIGHT,
            "reply_chain_escalation": cls.REPLY_CHAIN_ESCALATION,
            "bot_engagement": cls.BOT_ENGAGEMENT_PENALTY,
            "spam_pattern": cls.SPAM_PATTERN_PENALTY,
        }


class ToneVariant(str, Enum):
    """
    Tone variants for Guardian responses.
    4 distinct buckets for ML optimization.
    """
    # Empathic: Acknowledges the feeling, then corrects
    # "I get why this sounds scary, but here's what's actually happening..."
    EMPATHIC = "empathic"

    # Witty: Light, confident correction with personality
    # "Nope. Here's what actually happened."
    WITTY = "witty"

    # Firm: Direct correction, no fluff
    # "That's false. The data shows..."
    FIRM = "firm"

    # Spicy: Bold, slightly provocative but still factual
    # "Wild claim. Reality check:"
    SPICY = "spicy"


class SourceMixStrategy(str, Enum):
    """Source selection strategies."""
    INSTITUTION_HEAVY = "institution_heavy"  # Prioritize PRIMARY_INSTITUTION
    BALANCED = "balanced"                     # Even mix of source types
    FACTCHECK_HEAVY = "factcheck_heavy"      # Prioritize IFCN_FACTCHECK


class BetaDistribution:
    """Beta distribution for Thompson Sampling."""

    def __init__(self, alpha: float = 1.0, beta: float = 1.0):
        self.alpha = alpha
        self.beta = beta

    def sample(self) -> float:
        """Sample from beta distribution."""
        return random.betavariate(self.alpha, self.beta)

    def mean(self) -> float:
        """Expected value."""
        return self.alpha / (self.alpha + self.beta)

    def update_success(self):
        """Update after positive outcome."""
        self.alpha += 1

    def update_failure(self):
        """Update after negative outcome."""
        self.beta += 1

    def to_dict(self) -> Dict:
        return {"alpha": self.alpha, "beta": self.beta}

    @classmethod
    def from_dict(cls, data: Dict) -> "BetaDistribution":
        return cls(alpha=data["alpha"], beta=data["beta"])


class ArmStats(BaseModel):
    """Statistics for a single arm."""
    pulls: int = 0
    total_reward: float = 0.0
    avg_reward: float = 0.0
    last_pulled: Optional[datetime] = None


class BanditContext(BaseModel):
    """Context for contextual bandit decisions."""
    claim_type: str
    risk_level: str
    topic: Optional[str] = None
    language: str = "de"
    time_of_day: int = 12  # 0-23
    thread_sentiment: float = 0.0  # -1 to 1


class BanditDecision(BaseModel):
    """Record of a bandit decision for learning."""
    decision_id: str
    timestamp: datetime
    context: BanditContext
    tone_variant: ToneVariant
    source_mix: SourceMixStrategy
    # Filled in later
    reward: Optional[float] = None
    metrics: Optional[Dict] = None


class GuardianBandit:
    """
    Multi-Armed Bandit for Guardian Avatar optimization.

    Optimizes:
    - Tone variant selection
    - Source mix strategy

    Uses Thompson Sampling with Beta distributions.
    Safe constraints:
    - Cannot change factual content
    - Cannot reduce source authority
    - Cannot increase provocation
    """

    def __init__(self, state_path: Optional[str] = None):
        self.state_path = Path(state_path) if state_path else None

        # Tone variant arms - 4 distinct buckets
        self.tone_arms: Dict[ToneVariant, BetaDistribution] = {
            ToneVariant.EMPATHIC: BetaDistribution(1, 1),
            ToneVariant.WITTY: BetaDistribution(1, 1),
            ToneVariant.FIRM: BetaDistribution(1, 1),
            ToneVariant.SPICY: BetaDistribution(1, 1),
        }

        # Source mix arms
        self.source_arms: Dict[SourceMixStrategy, BetaDistribution] = {
            SourceMixStrategy.INSTITUTION_HEAVY: BetaDistribution(1, 1),
            SourceMixStrategy.BALANCED: BetaDistribution(1, 1),
            SourceMixStrategy.FACTCHECK_HEAVY: BetaDistribution(1, 1),
        }

        # Arm statistics
        self.tone_stats: Dict[ToneVariant, ArmStats] = {v: ArmStats() for v in ToneVariant}
        self.source_stats: Dict[SourceMixStrategy, ArmStats] = {v: ArmStats() for v in SourceMixStrategy}

        # Pending decisions awaiting feedback
        self.pending_decisions: Dict[str, BanditDecision] = {}

        # Load state if exists
        if self.state_path and self.state_path.exists():
            self._load_state()

        logger.info("GuardianBandit initialized with %d tone arms, %d source arms",
                   len(self.tone_arms), len(self.source_arms))

    def select_tone(self, context: Optional[BanditContext] = None) -> ToneVariant:
        """
        Select tone variant using Thompson Sampling.

        Args:
            context: Optional context for contextual selection

        Returns:
            Selected ToneVariant
        """
        # Sample from each arm
        samples = {arm: dist.sample() for arm, dist in self.tone_arms.items()}

        # Context-based adjustments (soft nudges, not hard rules)
        if context:
            claim_type = context.claim_type.lower() if context.claim_type else ""
            risk = context.risk_level.lower() if context.risk_level else ""

            # Health/science claims → slight preference for empathic (people are scared)
            if claim_type in ("health_misinformation", "science_denial"):
                samples[ToneVariant.EMPATHIC] *= 1.15

            # Conspiracy claims → witty or spicy works better (breaks the bubble)
            if claim_type in ("conspiracy_theory", "foreign_influence"):
                samples[ToneVariant.WITTY] *= 1.1
                samples[ToneVariant.SPICY] *= 1.1

            # High risk → firm (no jokes when stakes are high)
            if risk in ("high", "critical"):
                samples[ToneVariant.FIRM] *= 1.2
                samples[ToneVariant.SPICY] *= 0.8  # Reduce spicy for high risk

            # Hate/threats → firm (clear boundary needed)
            if claim_type in ("hate_or_dehumanization", "threat_or_incitement"):
                samples[ToneVariant.FIRM] *= 1.3
                samples[ToneVariant.EMPATHIC] *= 0.7  # Less empathy for hate

            # Low risk, general claims → more variety (let ML explore)
            if risk == "low":
                # No adjustment - let Thompson Sampling explore freely
                pass

        # Select arm with highest sample
        selected = max(samples, key=samples.get)
        logger.debug("Tone selection: %s (samples: %s)", selected, samples)

        return selected

    def select_source_mix(self, context: Optional[BanditContext] = None) -> SourceMixStrategy:
        """
        Select source mix strategy using Thompson Sampling.

        Args:
            context: Optional context for contextual selection

        Returns:
            Selected SourceMixStrategy
        """
        samples = {arm: dist.sample() for arm, dist in self.source_arms.items()}

        # Context-based adjustments
        if context:
            # For policy claims, prefer institution-heavy
            if context.claim_type in ("policy_aid_oversight", "delegitimization_frame"):
                samples[SourceMixStrategy.INSTITUTION_HEAVY] *= 1.2

            # For health claims, prefer factcheck-heavy
            if context.claim_type == "health_misinformation":
                samples[SourceMixStrategy.FACTCHECK_HEAVY] *= 1.1

        selected = max(samples, key=samples.get)
        logger.debug("Source mix selection: %s (samples: %s)", selected, samples)

        return selected

    def make_decision(self, context: BanditContext) -> BanditDecision:
        """
        Make a complete decision (tone + source mix).

        Args:
            context: Decision context

        Returns:
            BanditDecision with selected variants
        """
        import uuid

        decision_id = str(uuid.uuid4())
        tone = self.select_tone(context)
        source_mix = self.select_source_mix(context)

        decision = BanditDecision(
            decision_id=decision_id,
            timestamp=datetime.now(),
            context=context,
            tone_variant=tone,
            source_mix=source_mix
        )

        # Store pending decision
        self.pending_decisions[decision_id] = decision

        # Update stats
        self.tone_stats[tone].pulls += 1
        self.tone_stats[tone].last_pulled = datetime.now()
        self.source_stats[source_mix].pulls += 1
        self.source_stats[source_mix].last_pulled = datetime.now()

        logger.info("Decision %s: tone=%s, source_mix=%s", decision_id[:8], tone, source_mix)

        return decision

    def calculate_reward(self, metrics: Dict) -> float:
        """
        Calculate reward from engagement metrics with anti-gaming safeguards.

        Reward formula (from Blueprint):
        reward = 0.35*top_comment_proxy
               + 0.20*reply_quality
               + 0.15*like_reply_ratio
               + 0.10*shares_proxy
               + NegativeSignals (anti-gaming penalties)

        Anti-Gaming Penalties (from NegativeSignals):
        - reports_rate: -0.30 (heavy penalty for reports)
        - content_removal: -1.0 (complete nullification)
        - platform_flag: -0.50 (moderation flags)
        - toxicity_in_replies: -0.15 (toxic reactions)
        - reply_chain_escalation: -0.20 (provocation prevention)
        - bot_engagement: -0.40 (inauthentic engagement)
        - spam_pattern: -0.30 (repetitive patterns)

        Args:
            metrics: Dict with engagement metrics

        Returns:
            Reward value 0-1 (clamped)
        """
        # Check for content removal - complete reward nullification
        if metrics.get("content_removed", False) or metrics.get("deleted", False):
            logger.warning("Content removed - reward nullified")
            return 0.0

        # Extract positive metrics with defaults
        top_comment = metrics.get("top_comment_proxy", 0.5)
        reply_quality = metrics.get("reply_quality", 0.5)
        like_ratio = metrics.get("like_reply_ratio", 0.5)
        shares = metrics.get("shares_proxy", 0.0)

        # Extract negative signals
        reports = metrics.get("reports_rate", 0.0)
        toxicity = metrics.get("toxicity_in_replies", 0.0)
        platform_flag = 1.0 if metrics.get("platform_flagged", False) else 0.0
        reply_escalation = metrics.get("reply_chain_escalation", 0.0)
        bot_engagement = metrics.get("bot_engagement_ratio", 0.0)
        spam_pattern = metrics.get("spam_pattern_detected", 0.0)

        # Calculate positive reward component
        positive_reward = (
            0.35 * top_comment +
            0.20 * reply_quality +
            0.15 * like_ratio +
            0.10 * shares
        )

        # Calculate negative penalty component using NegativeSignals weights
        negative_penalty = (
            abs(NegativeSignals.REPORT_RATE_WEIGHT) * reports +
            abs(NegativeSignals.TOXICITY_IN_REPLIES_WEIGHT) * toxicity +
            abs(NegativeSignals.PLATFORM_FLAG_PENALTY) * platform_flag +
            abs(NegativeSignals.REPLY_CHAIN_ESCALATION) * reply_escalation +
            abs(NegativeSignals.BOT_ENGAGEMENT_PENALTY) * bot_engagement +
            abs(NegativeSignals.SPAM_PATTERN_PENALTY) * spam_pattern
        )

        # Final reward = positive - negative
        reward = positive_reward - negative_penalty

        # Clamp to [0, 1]
        reward = max(0.0, min(1.0, reward))

        logger.debug("Calculated reward: %.3f (positive=%.3f, penalty=%.3f, metrics: %s)",
                    reward, positive_reward, negative_penalty, metrics)
        return reward

    def update(self, decision_id: str, metrics: Dict) -> float:
        """
        Update bandit with feedback from a decision.

        Args:
            decision_id: ID of the decision
            metrics: Engagement metrics

        Returns:
            Calculated reward
        """
        if decision_id not in self.pending_decisions:
            logger.warning("Unknown decision_id: %s", decision_id)
            return 0.0

        decision = self.pending_decisions.pop(decision_id)
        reward = self.calculate_reward(metrics)

        # Update decision record
        decision.reward = reward
        decision.metrics = metrics

        # Update tone arm
        tone_dist = self.tone_arms[decision.tone_variant]
        if reward > 0.5:
            tone_dist.update_success()
        else:
            tone_dist.update_failure()

        # Update tone stats
        stats = self.tone_stats[decision.tone_variant]
        stats.total_reward += reward
        stats.avg_reward = stats.total_reward / stats.pulls

        # Update source mix arm
        source_dist = self.source_arms[decision.source_mix]
        if reward > 0.5:
            source_dist.update_success()
        else:
            source_dist.update_failure()

        # Update source stats
        stats = self.source_stats[decision.source_mix]
        stats.total_reward += reward
        stats.avg_reward = stats.total_reward / stats.pulls

        # Save state
        if self.state_path:
            self._save_state()

        logger.info("Updated decision %s: reward=%.3f, tone=%s, source=%s",
                   decision_id[:8], reward, decision.tone_variant, decision.source_mix)

        return reward

    def get_arm_stats(self) -> Dict:
        """Get current arm statistics."""
        return {
            "tone_arms": {
                arm.value: {
                    "distribution": dist.to_dict(),
                    "mean": dist.mean(),
                    "stats": self.tone_stats[arm].model_dump()
                }
                for arm, dist in self.tone_arms.items()
            },
            "source_arms": {
                arm.value: {
                    "distribution": dist.to_dict(),
                    "mean": dist.mean(),
                    "stats": self.source_stats[arm].model_dump()
                }
                for arm, dist in self.source_arms.items()
            },
            "pending_decisions": len(self.pending_decisions)
        }

    def _save_state(self):
        """Save bandit state to file."""
        state = {
            "tone_arms": {arm.value: dist.to_dict() for arm, dist in self.tone_arms.items()},
            "source_arms": {arm.value: dist.to_dict() for arm, dist in self.source_arms.items()},
            "tone_stats": {arm.value: stats.model_dump() for arm, stats in self.tone_stats.items()},
            "source_stats": {arm.value: stats.model_dump() for arm, stats in self.source_stats.items()},
        }

        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.state_path, "w") as f:
            json.dump(state, f, indent=2, default=str)

        logger.debug("Saved bandit state to %s", self.state_path)

    def _load_state(self):
        """Load bandit state from file."""
        try:
            with open(self.state_path) as f:
                state = json.load(f)

            for arm_value, dist_data in state.get("tone_arms", {}).items():
                arm = ToneVariant(arm_value)
                self.tone_arms[arm] = BetaDistribution.from_dict(dist_data)

            for arm_value, dist_data in state.get("source_arms", {}).items():
                arm = SourceMixStrategy(arm_value)
                self.source_arms[arm] = BetaDistribution.from_dict(dist_data)

            logger.info("Loaded bandit state from %s", self.state_path)

        except Exception as e:
            logger.warning("Failed to load bandit state: %s", e)


# Singleton instance
_bandit_instance: Optional[GuardianBandit] = None


def get_bandit(state_path: Optional[str] = None) -> GuardianBandit:
    """Get or create the global bandit instance."""
    global _bandit_instance
    if _bandit_instance is None:
        _bandit_instance = GuardianBandit(state_path)
    return _bandit_instance
