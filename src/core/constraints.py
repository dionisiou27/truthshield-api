"""
TruthShield Immutable Constraints & Anti-Gaming Signals
=============================================================================
Single source of truth for the safety boundaries that must NEVER be subject to
learning, optimization, or runtime mutation. Previously these lived inside
``src/ml/learning/bandit.py`` and were never enforced at runtime. They are now
centralized here and hardened so they cannot be silently changed.

LEARNABLE PARAMETERS (stylistic only):
- Tone variant (empathic/witty/firm/spicy) - HOW the message is framed
- Source mix strategy - WHICH source class priority, not WHICH sources
- Response length within constraints

IMMUTABLE PARAMETERS (never optimized, enforced at runtime):
- Factual content and claims
- Source class authority weights (integrity-checked at startup)
- Boundary definitions and rules
- Guardian behavioral constraints
- Source whitelist membership
- Risk level assessments
- Claim type classifications
- IO detection thresholds
- Minimum source authority threshold for citation
- Maximum engagement weight in the reward function
=============================================================================
"""
from typing import Dict, Final
import hashlib
import json
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# Class-attribute immutability via metaclass
# =============================================================================

class _ImmutableMeta(type):
    """Metaclass that blocks reassignment of class attributes at runtime.

    Reads behave normally; any attempt to rebind a class attribute (e.g.
    ``ImmutableConstraints.MIN_SOURCE_AUTHORITY = 0.5``) raises AttributeError.
    This is the runtime enforcement the Defence/EU review requires: the safety
    boundaries cannot be weakened by later code, a misconfiguration, or an
    engagement-driven optimizer.
    """

    def __setattr__(cls, name: str, value) -> None:  # noqa: D401
        raise AttributeError(
            f"{cls.__name__} is immutable; cannot modify attribute '{name}'"
        )

    def __delattr__(cls, name: str) -> None:
        raise AttributeError(
            f"{cls.__name__} is immutable; cannot delete attribute '{name}'"
        )


# =============================================================================
# IMMUTABLE CONSTRAINTS - Never subject to learning/optimization
# =============================================================================

class ImmutableConstraints(metaclass=_ImmutableMeta):
    """
    Parameters that are NEVER subject to bandit optimization.
    These represent epistemic and safety boundaries and cannot be reassigned
    at runtime (see ``_ImmutableMeta``).
    """
    # Source authority weights are fixed
    SOURCE_CLASS_WEIGHTS_FROZEN: Final[bool] = True

    # Guardian behavioral rules are immutable
    GUARDIAN_RULES_FROZEN: Final[bool] = True

    # Claim classifications come from deterministic rules
    CLAIM_CLASSIFICATION_FROZEN: Final[bool] = True

    # Risk levels are policy-defined, not learned
    RISK_LEVELS_FROZEN: Final[bool] = True

    # Boundary definitions cannot be weakened
    BOUNDARY_DEFINITIONS_FROZEN: Final[bool] = True

    # Minimum source authority required for a source to be CITED as evidence.
    # Sources below this float (Wikipedia 0.40, Unknown 0.20) may still be used
    # for retrieval/discovery, but never as cited evidence.
    MIN_SOURCE_AUTHORITY: Final[float] = 0.70  # No citation below REPUTABLE_MEDIA

    # Maximum engagement weight (prevents engagement > accuracy drift)
    MAX_ENGAGEMENT_WEIGHT: Final[float] = 0.50

    # Expected SHA256 of the canonical SOURCE_CLASS_WEIGHTS table. Any change to
    # the authority weights (intentional or not) changes this hash and is caught
    # by verify_source_weights_integrity() at startup.
    SOURCE_WEIGHTS_SHA256: Final[str] = (
        "f82b78d49065669b8137022c59c0013428be94cca1b88622431756515e152e97"
    )

    @classmethod
    def validate_reward_weights(cls, weights: Dict[str, float]) -> bool:
        """Ensure reward weights don't over-prioritize engagement."""
        engagement_weights = weights.get("likes", 0) + weights.get("shares", 0)
        return engagement_weights <= cls.MAX_ENGAGEMENT_WEIGHT


# =============================================================================
# NEGATIVE OPTIMIZATION SIGNALS - Anti-gaming measures
# =============================================================================

class NegativeSignals(metaclass=_ImmutableMeta):
    """
    Signals that REDUCE reward, preventing gaming and drift.
    These are explicitly documented for audit purposes and are immutable.
    """
    # Platform moderation signals
    REPORT_RATE_WEIGHT: Final[float] = -0.30        # Heavy penalty for reports
    CONTENT_REMOVAL_PENALTY: Final[float] = -1.0    # Complete reward nullification
    PLATFORM_FLAG_PENALTY: Final[float] = -0.50     # Moderation flags

    # Toxicity amplification
    TOXICITY_IN_REPLIES_WEIGHT: Final[float] = -0.15
    REPLY_CHAIN_ESCALATION: Final[float] = -0.20    # Prevents provocation optimization

    # Engagement gaming
    BOT_ENGAGEMENT_PENALTY: Final[float] = -0.40    # Suspected inauthentic engagement
    SPAM_PATTERN_PENALTY: Final[float] = -0.30      # Repetitive/spam patterns

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


# =============================================================================
# AI DISCLOSURE - Every intervention is declared as AI-assisted
# =============================================================================

AI_DISCLOSURE_DE: Final[str] = "🤖 KI-gestützt · menschlich geprüft"
AI_DISCLOSURE_EN: Final[str] = "🤖 AI-assisted · human-reviewed"


def get_ai_disclosure(language: str) -> str:
    """Return the AI disclosure string for the given language (DE/EN)."""
    return AI_DISCLOSURE_DE if (language or "en").lower().startswith("de") else AI_DISCLOSURE_EN


def append_ai_disclosure(text: str, language: str, max_chars: int = 0) -> str:
    """Append the AI disclosure to a generated response.

    - Language-aware (DE/EN).
    - Idempotent: never appends twice if the disclosure is already present.
    - Budget-safe: if ``max_chars`` > 0 and the combined length would exceed it,
      the answer BODY is trimmed, never the disclosure.
    """
    disclosure = get_ai_disclosure(language)
    body = (text or "").rstrip()

    # Idempotency: disclosure already present
    if disclosure in body or AI_DISCLOSURE_DE in body or AI_DISCLOSURE_EN in body:
        return body

    separator = "\n\n"
    if max_chars and max_chars > 0:
        budget = max_chars - len(disclosure) - len(separator)
        if budget < 0:
            # Cannot fit even the disclosure alone — disclosure still wins.
            return disclosure
        if len(body) > budget:
            body = body[:budget].rstrip()

    if not body:
        return disclosure
    return f"{body}{separator}{disclosure}"


# =============================================================================
# SOURCE WEIGHTS INTEGRITY CHECK - Startup guard
# =============================================================================

def _canonical_source_weights() -> str:
    """Serialize SOURCE_CLASS_WEIGHTS deterministically for hashing.

    Imported lazily to avoid a circular import between this module and the
    source ranker (the ranker imports ImmutableConstraints for the hard
    authority threshold).
    """
    from src.ml.guardian.source_ranker import SOURCE_CLASS_WEIGHTS

    return json.dumps(
        {k.value: v for k, v in SOURCE_CLASS_WEIGHTS.items()},
        sort_keys=True,
    )


def compute_source_weights_hash() -> str:
    """Return the SHA256 of the canonical SOURCE_CLASS_WEIGHTS table."""
    return hashlib.sha256(_canonical_source_weights().encode("utf-8")).hexdigest()


def verify_source_weights_integrity() -> bool:
    """Verify the source authority weights have not been tampered with.

    Returns True on match. On mismatch logs CRITICAL and raises RuntimeError so
    the application aborts startup rather than running with weakened authority
    weights.
    """
    actual = compute_source_weights_hash()
    expected = ImmutableConstraints.SOURCE_WEIGHTS_SHA256
    if actual != expected:
        logger.critical(
            "SOURCE_CLASS_WEIGHTS integrity check FAILED: expected %s, got %s. "
            "Authority weights may have been altered. Aborting startup.",
            expected,
            actual,
        )
        raise RuntimeError(
            "SOURCE_CLASS_WEIGHTS integrity check failed — authority weights altered."
        )
    logger.info("SOURCE_CLASS_WEIGHTS integrity verified (sha256=%s).", actual)
    return True
