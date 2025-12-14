"""
Guardian Bandit Controller
Thompson Sampling for tone and source-mix optimization.
"""
from enum import Enum
from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel
from datetime import datetime
import random
import math
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class ToneVariant(str, Enum):
    """Tone variants for Guardian responses."""
    BOUNDARY_STRICT = "boundary_strict"      # "Stop. This is misinformation."
    BOUNDARY_FIRM = "boundary_firm"          # "This claim is demonstrably false."
    BOUNDARY_EDUCATIONAL = "boundary_educational"  # "Let's clarify the facts here."


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

        # Tone variant arms
        self.tone_arms: Dict[ToneVariant, BetaDistribution] = {
            ToneVariant.BOUNDARY_STRICT: BetaDistribution(1, 1),
            ToneVariant.BOUNDARY_FIRM: BetaDistribution(1, 1),
            ToneVariant.BOUNDARY_EDUCATIONAL: BetaDistribution(1, 1),
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

        # Context-based adjustments (optional)
        if context:
            # For high risk, prefer stricter tones
            if context.risk_level in ("high", "critical"):
                samples[ToneVariant.BOUNDARY_STRICT] *= 1.2

            # For educational topics, prefer educational tone
            if context.topic in ("health", "science"):
                samples[ToneVariant.BOUNDARY_EDUCATIONAL] *= 1.1

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
        Calculate reward from engagement metrics.

        Reward formula (from Blueprint):
        reward = 0.35*top_comment_proxy
               + 0.20*reply_quality
               + 0.15*like_reply_ratio
               + 0.10*shares_proxy
               - 0.30*reports_rate
               - 0.15*toxicity_in_replies

        Args:
            metrics: Dict with engagement metrics

        Returns:
            Reward value 0-1 (clamped)
        """
        # Extract metrics with defaults
        top_comment = metrics.get("top_comment_proxy", 0.5)
        reply_quality = metrics.get("reply_quality", 0.5)
        like_ratio = metrics.get("like_reply_ratio", 0.5)
        shares = metrics.get("shares_proxy", 0.0)
        reports = metrics.get("reports_rate", 0.0)
        toxicity = metrics.get("toxicity_in_replies", 0.0)

        # Calculate weighted reward
        reward = (
            0.35 * top_comment +
            0.20 * reply_quality +
            0.15 * like_ratio +
            0.10 * shares -
            0.30 * reports -
            0.15 * toxicity
        )

        # Clamp to [0, 1]
        reward = max(0.0, min(1.0, reward))

        logger.debug("Calculated reward: %.3f (metrics: %s)", reward, metrics)
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
