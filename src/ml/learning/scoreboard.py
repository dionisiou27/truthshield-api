"""
Guardian LLM Scoreboard
Automatic quality metrics for Guardian response compliance.

Metrics tracked:
- rule_violations_count: Guardian behavioral rule violations
- avg_chars: Average character count
- source_relevance_rate: How often sources match claim
- genericness_rate: Detection of "needs verification" blabla
- unsafe_escalation_rate: Responses that might escalate

This is the "ehrlichste KPI" - honest quality tracking.
"""
from typing import Dict, List, Optional, Set
from pydantic import BaseModel
from datetime import datetime
from enum import Enum
import re
import logging

logger = logging.getLogger(__name__)


class RuleViolationType(str, Enum):
    """Types of Guardian rule violations."""
    ASKED_QUESTION = "asked_question"           # Guardian never asks questions
    USED_IRONY = "used_irony"                   # No irony/sarcasm allowed
    DEBATED_OPINION = "debated_opinion"         # Never debate, just state facts
    EXCEEDED_LENGTH = "exceeded_length"         # Over 450 chars
    INSUFFICIENT_SOURCES = "insufficient_sources"  # Less than 3 sources
    GENERIC_RESPONSE = "generic_response"       # "Needs verification" blabla
    EMOTIONAL_LANGUAGE = "emotional_language"   # Too emotional for Guardian
    MISSING_BOUNDARY = "missing_boundary"       # No clear boundary statement


class SourceRelevanceLabel(str, Enum):
    """Labels for source relevance QA."""
    SUPPORTED = "SUPPORTED"      # Source supports the counter-claim
    REFUTED = "REFUTED"          # Source refutes the misinformation
    UNRELATED = "UNRELATED"      # Source doesn't match claim


class BoundaryType(str, Enum):
    """Type of boundary statement detected."""
    HARD = "hard"    # stop, halt, false, wrong, misinformation
    SOFT = "soft"    # misleading, misconception, distorts, framing
    NONE = "none"    # No boundary detected


class ResponseScore(BaseModel):
    """Score for a single Guardian response."""
    response_id: str
    timestamp: datetime

    # Core metrics
    char_count: int
    sentence_count: int
    source_count: int

    # Rule violations
    violations: List[RuleViolationType] = []
    violation_count: int = 0

    # Quality scores (0-1)
    genericness_score: float = 0.0      # Higher = more generic
    escalation_risk: float = 0.0        # Higher = more risky

    # Boundary detection (risk-aware)
    boundary_detected: bool = False
    boundary_type: BoundaryType = BoundaryType.NONE

    # Source relevance (filled by QA)
    source_labels: Optional[Dict[str, SourceRelevanceLabel]] = None
    source_relevance_rate: Optional[float] = None  # % SUPPORTED or REFUTED


class ScoreboardSummary(BaseModel):
    """Aggregate scoreboard metrics."""
    total_responses: int = 0

    # Averages
    avg_chars: float = 0.0
    avg_sentences: float = 0.0
    avg_sources: float = 0.0
    avg_violations: float = 0.0

    # Rates
    violation_rate: float = 0.0         # % responses with any violation
    genericness_rate: float = 0.0       # % responses flagged as generic
    escalation_rate: float = 0.0        # % responses with escalation risk
    source_relevance_rate: float = 0.0  # % sources that are relevant (QA)

    # Violation breakdown
    violation_counts: Dict[str, int] = {}


class GuardianScoreboard:
    """
    Automatic quality scoring for Guardian responses.

    This scoreboard checks:
    1. Rule compliance (no questions, no irony, no debate)
    2. Format compliance (length, sources)
    3. Quality signals (genericness, escalation risk)
    4. Source relevance (when QA labels available)
    """

    # Question patterns (Guardian never asks questions)
    QUESTION_PATTERNS = [
        r'\?$',                           # Ends with ?
        r'\b(warum|wieso|weshalb|was|wer|wie|wo|wann)\b.*\?',  # DE questions
        r'\b(why|what|who|how|where|when)\b.*\?',              # EN questions
    ]

    # Irony/sarcasm patterns
    IRONY_PATTERNS = [
        r'\b(obviously|clearly|of course|surely|naturally)\b',
        r'\b(natürlich|offensichtlich|klar|sicher)\b',
        r'\.{3,}',                        # Ellipsis often indicates sarcasm
        r'[!]{2,}',                       # Multiple exclamation marks
        r'\b(lol|lmao|haha|rofl)\b',
    ]

    # Generic "needs verification" patterns
    GENERIC_PATTERNS = [
        r'\b(needs? verification|requires? verification)\b',
        r'\b(unverified|not verified|cannot verify)\b',
        r'\b(may or may not|could be true|might be)\b',
        r'\b(do your own research|judge for yourself)\b',
        r'\b(benötigt überprüfung|nicht verifiziert)\b',
        r'\b(könnte wahr sein|möglicherweise)\b',
    ]

    # Escalation risk patterns
    ESCALATION_PATTERNS = [
        r'\b(stupid|idiot|moron|fool|dumb)\b',
        r'\b(dumm|blöd|idiot|depp)\b',
        r'\b(you people|these people|those types)\b',
        r'\b(ihr leute|diese leute|solche typen)\b',
        r'\b(always|never|everyone|nobody)\b.*\b(wrong|right|bad|good)\b',
    ]

    # Emotional language patterns
    EMOTIONAL_PATTERNS = [
        r'\b(absolutely|completely|totally|utterly)\b',
        r'\b(horrible|terrible|disgusting|outrageous)\b',
        r'\b(schrecklich|furchtbar|ekelhaft|empörend)\b',
        r'[!]{3,}',                       # Excessive exclamation
    ]

    # ==========================================================================
    # BOUNDARY PATTERNS - Risk-aware detection
    # ==========================================================================
    # HARD boundaries: Required for HIGH/CRITICAL risk (hate, threats)
    # SOFT boundaries: Acceptable for MEDIUM risk (delegitimization, framing)

    HARD_BOUNDARY_PATTERNS = [
        r'\b(stop|halt)\b',                           # Direct stop
        r'\b(false|wrong|incorrect)\b',               # Factual rejection
        r'\b(misinformation|disinformation)\b',       # Explicit label
        r'\b(threat|harassment|hate)\b',              # Threat/hate naming
        r'\b(stopp|falsch|inkorrekt)\b',              # DE equivalents
        r'\b(fehlinformation|desinformation)\b',      # DE explicit
        r'\b(this is not true|this claim is false)\b',
        r'\b(das stimmt nicht|diese behauptung ist falsch)\b',
        r'\bfactually wrong\b',
    ]

    SOFT_BOUNDARY_PATTERNS = [
        r'\b(misleading|mislead|misleads)\b',         # Soft factual
        r'\b(misconception)\b',                       # Educational
        r'\b(distort|distorts|distortion)\b',         # Framing critique
        r'\b(framing|reframing)\b',                   # Meta-level
        r'\b(oversimplif(ies|y|ied|ying))\b',         # Complexity note
        r'\b(removes crucial context)\b',             # Context critique
        r'\b(blanket claim)\b',                       # Generalization
        r'\b(inverts|inverted)\b',                    # Reversal
        r'\b(repeats a .* narrative)\b',              # Narrative call-out
        r'\b(skips the real question)\b',             # Deflection
        r'\b(oversimplifies|vereinfacht)\b',          # DE soft
        r'\b(irreführend|täuschend)\b',               # DE misleading
        # v2 additions - causal/agency critique
        r'\b(omits)\b',                               # Context omission
        r'\b(misrepresents)\b',                       # Misrepresentation
        r'\b(erases)\b',                              # Agency erasure
        r'\bframes .* as\b',                          # Frame labeling
        r'\b(reverses)\b',                            # Event reversal
        r'\b(removes .* agency)\b',                   # Agency removal
        # China/UK batch additions - factual critique
        r'\b(compresses)\b',                          # Oversimplification
        r'\b(generalises|generalizes)\b',             # Over-generalization
        r'\b(contradicts)\b',                         # Factual contradiction
        r'\bfactually incomplete\b',                  # Incomplete facts
        r'\b(ignores)\b',                             # Ignoring evidence
        r'\b(dismissing)\b',                          # Dismissal
        # China/UK v2 - grey zone handling
        r'\b(conflates)\b',                           # Conflation critique
        r'\b(substitutes)\b',                         # Substitution
        r'\b(assumes)\b',                             # False assumption
        r'\b(narrows)\b',                             # Narrowing scope
        r'\b(dismisses)\b',                           # Dismissal
        r'\b(compares)\b',                            # False comparison
        r'\b(attributes)\b',                          # Attribution without evidence
        r'\b(normalises|normalizes)\b',               # Normalisation critique
        r'\b(critiques)\b',                           # Meta-critique acknowledgment
        r'\b(questions)\b',                           # Questioning framing
        r'\braises a valid\b',                        # Partial acknowledgment
        r'\bdoes not answer\b',                       # Unanswered deflection
        r'\bdoes not make .* fictional\b',            # Both-can-be-true
        r'\bboth can be true\b',                      # Dual validity
        r'\bdoes not cancel\b',                       # Non-cancellation
    ]

    # Claim types that REQUIRE hard boundaries
    HIGH_RISK_CLAIM_TYPES = [
        "hate_or_dehumanization",
        "threat_or_incitement",
    ]

    # ==========================================================================
    # SENTENCE-START BOUNDARY DETECTION
    # ==========================================================================
    # Complements regex patterns - catches structured Guardian openings
    # that might not match keyword patterns but clearly set boundaries
    HARD_BOUNDARY_STARTS = [
        "stop.",
        "this is false",
        "this is factually incorrect",
        "this is misinformation",
        "this is disinformation",
        "this claim is false",
    ]

    SOFT_BOUNDARY_STARTS = [
        "this omits",
        "this reverses",
        "this misrepresents",
        "this oversimplifies",
        "this distorts",
        "this inverts",
        "this compresses",
        "this generalises",
        "this generalizes",
        "this frames",
        "this erases",
        "this removes",
        "this is factually incomplete",
        "that framing",
        "blanket claims",
    ]

    def __init__(self):
        self.scores: List[ResponseScore] = []
        logger.info("GuardianScoreboard initialized")

    def score_response(
        self,
        response_id: str,
        response_text: str,
        sources: List[str],
        max_chars: int = 450,
        risk_level: str = "medium",
        claim_types: Optional[List[str]] = None
    ) -> ResponseScore:
        """
        Score a Guardian response for quality metrics.

        Args:
            response_id: Unique response identifier
            response_text: The Guardian response text
            sources: List of source URLs/names used
            max_chars: Maximum allowed characters
            risk_level: Risk level (low, medium, high, critical)
            claim_types: List of claim type strings

        Returns:
            ResponseScore with all metrics
        """
        text_lower = response_text.lower()
        violations = []
        claim_types = claim_types or []

        # Check character limit
        char_count = len(response_text)
        if char_count > max_chars:
            violations.append(RuleViolationType.EXCEEDED_LENGTH)

        # Count sentences (rough estimate)
        sentence_count = len(re.findall(r'[.!?]+', response_text))

        # Check source count
        source_count = len(sources)
        if source_count < 3:
            violations.append(RuleViolationType.INSUFFICIENT_SOURCES)

        # Check for questions
        for pattern in self.QUESTION_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                violations.append(RuleViolationType.ASKED_QUESTION)
                break

        # Check for irony
        for pattern in self.IRONY_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                violations.append(RuleViolationType.USED_IRONY)
                break

        # Check for emotional language
        for pattern in self.EMOTIONAL_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                violations.append(RuleViolationType.EMOTIONAL_LANGUAGE)
                break

        # =======================================================================
        # RISK-AWARE BOUNDARY CHECK
        # =======================================================================
        # Determine if hard boundary is required
        requires_hard_boundary = (
            risk_level.lower() in ["high", "critical"] or
            any(ct in self.HIGH_RISK_CLAIM_TYPES for ct in claim_types)
        )

        # Check for hard boundary (regex OR sentence-start)
        has_hard_boundary = False
        for pattern in self.HARD_BOUNDARY_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                has_hard_boundary = True
                break

        # Sentence-start hard boundary detection
        if not has_hard_boundary:
            first_sentence = text_lower.split('.')[0].strip() if text_lower else ""
            for start in self.HARD_BOUNDARY_STARTS:
                if first_sentence.startswith(start) or text_lower.startswith(start):
                    has_hard_boundary = True
                    break

        # Check for soft boundary (regex OR sentence-start)
        has_soft_boundary = False
        for pattern in self.SOFT_BOUNDARY_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                has_soft_boundary = True
                break

        # Sentence-start soft boundary detection
        if not has_soft_boundary:
            first_sentence = text_lower.split('.')[0].strip() if text_lower else ""
            for start in self.SOFT_BOUNDARY_STARTS:
                if first_sentence.startswith(start) or text_lower.startswith(start):
                    has_soft_boundary = True
                    break

        # Determine boundary type and violation
        if has_hard_boundary:
            boundary_type = BoundaryType.HARD
            boundary_detected = True
        elif has_soft_boundary:
            boundary_type = BoundaryType.SOFT
            boundary_detected = True
        else:
            boundary_type = BoundaryType.NONE
            boundary_detected = False

        # Apply violation logic based on risk level
        if requires_hard_boundary and not has_hard_boundary:
            # HIGH/CRITICAL risk needs hard boundary
            violations.append(RuleViolationType.MISSING_BOUNDARY)
        elif risk_level.lower() == "medium" and not (has_hard_boundary or has_soft_boundary):
            # MEDIUM risk needs at least soft boundary
            violations.append(RuleViolationType.MISSING_BOUNDARY)
        # LOW risk: boundary optional, no violation

        # Calculate genericness score
        generic_matches = 0
        for pattern in self.GENERIC_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                generic_matches += 1
        genericness_score = min(1.0, generic_matches / 3)

        if genericness_score > 0.3:
            violations.append(RuleViolationType.GENERIC_RESPONSE)

        # Calculate escalation risk
        escalation_matches = 0
        for pattern in self.ESCALATION_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                escalation_matches += 1
        escalation_risk = min(1.0, escalation_matches / 2)

        # Create score
        score = ResponseScore(
            response_id=response_id,
            timestamp=datetime.now(),
            char_count=char_count,
            sentence_count=sentence_count,
            source_count=source_count,
            violations=list(set(violations)),  # Dedupe
            violation_count=len(set(violations)),
            genericness_score=genericness_score,
            escalation_risk=escalation_risk,
            boundary_detected=boundary_detected,
            boundary_type=boundary_type,
        )

        self.scores.append(score)

        logger.info(
            "Scored response %s: %d chars, %d violations, boundary=%s (%s)",
            response_id[:8], char_count, score.violation_count,
            boundary_detected, boundary_type.value
        )

        return score

    def add_source_qa(
        self,
        response_id: str,
        source_labels: Dict[str, SourceRelevanceLabel]
    ) -> Optional[float]:
        """
        Add QA labels for source relevance.

        Args:
            response_id: Response to update
            source_labels: Dict of source URL -> label

        Returns:
            Source relevance rate (% SUPPORTED or REFUTED)
        """
        for score in self.scores:
            if score.response_id == response_id:
                score.source_labels = source_labels

                # Calculate relevance rate
                total = len(source_labels)
                if total > 0:
                    relevant = sum(
                        1 for label in source_labels.values()
                        if label in (SourceRelevanceLabel.SUPPORTED, SourceRelevanceLabel.REFUTED)
                    )
                    score.source_relevance_rate = relevant / total
                else:
                    score.source_relevance_rate = 0.0

                logger.info(
                    "Added QA labels for %s: relevance_rate=%.2f",
                    response_id[:8], score.source_relevance_rate
                )
                return score.source_relevance_rate

        logger.warning("Response not found for QA: %s", response_id)
        return None

    def get_summary(self, last_n: Optional[int] = None) -> ScoreboardSummary:
        """
        Get aggregate scoreboard summary.

        Args:
            last_n: Only consider last N responses

        Returns:
            ScoreboardSummary with aggregate metrics
        """
        scores = self.scores[-last_n:] if last_n else self.scores

        if not scores:
            return ScoreboardSummary()

        total = len(scores)

        # Calculate averages
        avg_chars = sum(s.char_count for s in scores) / total
        avg_sentences = sum(s.sentence_count for s in scores) / total
        avg_sources = sum(s.source_count for s in scores) / total
        avg_violations = sum(s.violation_count for s in scores) / total

        # Calculate rates
        with_violations = sum(1 for s in scores if s.violation_count > 0)
        violation_rate = with_violations / total

        high_generic = sum(1 for s in scores if s.genericness_score > 0.3)
        genericness_rate = high_generic / total

        high_escalation = sum(1 for s in scores if s.escalation_risk > 0.3)
        escalation_rate = high_escalation / total

        # Source relevance (only for scores with QA)
        with_qa = [s for s in scores if s.source_relevance_rate is not None]
        if with_qa:
            source_relevance_rate = sum(s.source_relevance_rate for s in with_qa) / len(with_qa)
        else:
            source_relevance_rate = 0.0

        # Violation breakdown
        violation_counts: Dict[str, int] = {}
        for score in scores:
            for v in score.violations:
                violation_counts[v.value] = violation_counts.get(v.value, 0) + 1

        return ScoreboardSummary(
            total_responses=total,
            avg_chars=round(avg_chars, 1),
            avg_sentences=round(avg_sentences, 1),
            avg_sources=round(avg_sources, 1),
            avg_violations=round(avg_violations, 2),
            violation_rate=round(violation_rate, 3),
            genericness_rate=round(genericness_rate, 3),
            escalation_rate=round(escalation_rate, 3),
            source_relevance_rate=round(source_relevance_rate, 3),
            violation_counts=violation_counts,
        )

    def get_problem_responses(self, min_violations: int = 2) -> List[ResponseScore]:
        """Get responses with multiple violations for review."""
        return [s for s in self.scores if s.violation_count >= min_violations]


# Singleton instance
_scoreboard_instance: Optional[GuardianScoreboard] = None


def get_scoreboard() -> GuardianScoreboard:
    """Get or create the global scoreboard instance."""
    global _scoreboard_instance
    if _scoreboard_instance is None:
        _scoreboard_instance = GuardianScoreboard()
    return _scoreboard_instance
