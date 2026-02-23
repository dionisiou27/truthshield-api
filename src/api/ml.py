"""
ML API Endpoints for Guardian Learning Pipeline
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional
from datetime import datetime
import logging

from src.ml.guardian.claim_router import ClaimRouter, PolicyClaimRouter
from src.ml.guardian.source_ranker import SourceRanker, SourceCandidate
from src.ml.guardian.response_generator import get_generator
from src.ml.learning.bandit import get_bandit
from src.ml.learning.feedback import get_collector, EngagementMetrics
from src.ml.learning.logging import get_learning_logger

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/ml", tags=["ML Learning"])


# === Request/Response Models ===

class ClaimAnalysisRequest(BaseModel):
    """Request for claim analysis."""
    text: str
    language: Optional[str] = None


class SourceRankRequest(BaseModel):
    """Request for source ranking."""
    claim_text: str
    sources: List[Dict]


class FeedbackRequest(BaseModel):
    """Engagement feedback from platform."""
    response_id: str
    decision_id: Optional[str] = None

    # Core metrics
    likes: int = 0
    replies: int = 0
    shares: int = 0
    views: int = 0

    # Position
    top_comment_position: Optional[int] = None
    is_pinned: bool = False

    # Quality
    reply_sentiment_avg: float = 0.0
    constructive_reply_ratio: float = 0.0

    # Negative
    reports: int = 0
    hidden: bool = False
    deleted: bool = False


class GuardianPrepareRequest(BaseModel):
    """Request to prepare a Guardian response with ML pipeline."""
    claim_text: str
    sources: List[Dict] = []


# === Endpoints ===

@router.post("/analyze-claim")
async def analyze_claim(request: ClaimAnalysisRequest):
    """
    Analyze and classify a claim.

    Returns claim types, risk level, entities, and keywords.
    """
    try:
        router_instance = PolicyClaimRouter()
        analysis = router_instance.analyze_claim(request.text)

        return {
            "claim_id": analysis.claim_id,
            "language": analysis.language,
            "claim_types": [ct.value for ct in analysis.claim_types],
            "risk_level": analysis.risk_level.value,
            "confidence": analysis.confidence,
            "reasoning": analysis.reasoning_brief,
            "entities": analysis.entities,
            "keywords": analysis.keywords,
            "requires_guardian": analysis.requires_guardian
        }

    except Exception as e:
        logger.error(f"Claim analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rank-sources")
async def rank_sources(request: SourceRankRequest):
    """
    Rank and select sources for a claim.

    Returns top 3 sources with scores and rejection reasons.
    """
    try:
        ranker = SourceRanker()
        router_instance = ClaimRouter()

        # Analyze claim for keywords
        analysis = router_instance.analyze_claim(request.claim_text)

        # Convert input sources to SourceCandidate
        candidates = []
        for i, src in enumerate(request.sources):
            candidate = SourceCandidate(
                url=src.get("url", ""),
                title=src.get("title", ""),
                snippet=src.get("snippet", ""),
                publisher=src.get("publisher"),
                retrieval_rank=i
            )
            candidates.append(candidate)

        # Rank sources
        selected = ranker.rank_sources(candidates, analysis.keywords)
        rejections = ranker.get_rejection_reasons(candidates, selected)

        return {
            "claim_keywords": analysis.keywords,
            "candidates_count": len(candidates),
            "selected_sources": [
                {
                    "url": s.url,
                    "title": s.title,
                    "source_class": s.source_class.value,
                    "relevance_score": round(s.relevance_score, 3),
                    "authority_score": round(s.authority_score, 3),
                    "final_score": round(s.final_score, 3)
                }
                for s in selected
            ],
            "rejected_top": rejections[:5]
        }

    except Exception as e:
        logger.error(f"Source ranking failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/prepare-guardian")
async def prepare_guardian_response(request: GuardianPrepareRequest):
    """
    Prepare a Guardian response with full ML pipeline.

    1. Analyzes claim
    2. Ranks sources
    3. Makes bandit decision for tone/mix
    4. Returns all metadata for response generation
    """
    try:
        generator = get_generator()

        # Convert sources
        candidates = [
            SourceCandidate(
                url=src.get("url", ""),
                title=src.get("title", ""),
                snippet=src.get("snippet", ""),
                publisher=src.get("publisher"),
                retrieval_rank=i
            )
            for i, src in enumerate(request.sources)
        ]

        # Run ML pipeline
        response = generator.prepare_response(
            claim_text=request.claim_text,
            source_candidates=candidates
        )

        return {
            "response_id": response.response_id,
            "claim_id": response.claim_id,
            "claim_analysis": {
                "types": [ct.value for ct in response.claim_analysis.claim_types],
                "risk_level": response.claim_analysis.risk_level.value,
                "keywords": response.claim_analysis.keywords,
                "requires_guardian": response.claim_analysis.requires_guardian
            },
            "ml_decision": {
                "decision_id": response.decision_id,
                "tone_variant": response.tone_variant,
                "source_mix": response.source_mix,
                "variant_id": response.variant_id
            },
            "selected_sources": response.selected_sources[:3],
            "source_line": response.source_line,
            "constraints": response.constraints,
            "learning_enabled": response.learning_enabled
        }

    except Exception as e:
        logger.error(f"Guardian preparation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/feedback")
async def submit_feedback(request: FeedbackRequest):
    """
    Submit engagement feedback for a Guardian response.

    Updates the bandit with reward signal.
    """
    try:
        collector = get_collector()
        bandit = get_bandit()
        ml_logger = get_learning_logger()

        # Create metrics object
        metrics = EngagementMetrics(
            response_id=request.response_id,
            avatar="GuardianAvatar",
            likes=request.likes,
            replies=request.replies,
            shares=request.shares,
            views=request.views,
            top_comment_position=request.top_comment_position,
            is_pinned=request.is_pinned,
            reply_sentiment_avg=request.reply_sentiment_avg,
            constructive_reply_ratio=request.constructive_reply_ratio,
            reports=request.reports,
            hidden=request.hidden,
            deleted=request.deleted,
            collected_at=datetime.now()
        )

        # Log metrics
        collector.log_metrics(metrics)

        # Calculate derived metrics
        derived = collector.calculate_derived_metrics(metrics)

        # Update bandit if we have a decision_id
        reward = 0.0
        if request.decision_id:
            reward = bandit.update(request.decision_id, derived)

            # Log update
            ml_logger.log_bandit_update(
                decision_id=request.decision_id,
                reward=reward,
                metrics=request.model_dump(),
                derived_metrics=derived,
                updated_arms={
                    "tone": {k.value: v.mean() for k, v in bandit.tone_arms.items()},
                    "source": {k.value: v.mean() for k, v in bandit.source_arms.items()}
                }
            )

        return {
            "response_id": request.response_id,
            "decision_id": request.decision_id,
            "reward": round(reward, 4),
            "derived_metrics": {k: round(v, 4) for k, v in derived.items()},
            "bandit_updated": request.decision_id is not None
        }

    except Exception as e:
        logger.error(f"Feedback submission failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/bandit/stats")
async def get_bandit_stats():
    """
    Get current bandit arm statistics.

    Shows distribution parameters and selection rates for each arm.
    """
    try:
        bandit = get_bandit()
        stats = bandit.get_arm_stats()

        return {
            "tone_arms": {
                arm: {
                    "alpha": data["distribution"]["alpha"],
                    "beta": data["distribution"]["beta"],
                    "mean": round(data["mean"], 4),
                    "pulls": data["stats"]["pulls"],
                    "avg_reward": round(data["stats"]["avg_reward"], 4)
                }
                for arm, data in stats["tone_arms"].items()
            },
            "source_arms": {
                arm: {
                    "alpha": data["distribution"]["alpha"],
                    "beta": data["distribution"]["beta"],
                    "mean": round(data["mean"], 4),
                    "pulls": data["stats"]["pulls"],
                    "avg_reward": round(data["stats"]["avg_reward"], 4)
                }
                for arm, data in stats["source_arms"].items()
            },
            "pending_decisions": stats["pending_decisions"]
        }

    except Exception as e:
        logger.error(f"Failed to get bandit stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/learning/summary")
async def get_learning_summary():
    """
    Get learning pipeline summary statistics.
    """
    try:
        ml_logger = get_learning_logger()
        generator = get_generator()

        return {
            "learning_summary": ml_logger.get_learning_summary(),
            "pipeline_stats": generator.get_pipeline_stats()
        }

    except Exception as e:
        logger.error(f"Failed to get learning summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/source-whitelist")
async def get_source_whitelist():
    """
    Get the current source classification whitelist.
    """
    from src.ml.guardian.source_ranker import DOMAIN_WHITELIST, SOURCE_CLASS_WEIGHTS

    # Group by source class
    by_class = {}
    for domain, source_class in DOMAIN_WHITELIST.items():
        class_name = source_class.value
        if class_name not in by_class:
            by_class[class_name] = {
                "weight": SOURCE_CLASS_WEIGHTS[source_class],
                "domains": []
            }
        by_class[class_name]["domains"].append(domain)

    return {
        "source_classes": by_class,
        "total_domains": len(DOMAIN_WHITELIST)
    }


@router.get("/training-data")
async def get_training_data(limit: int = 100):
    """
    Get training data for offline ML analysis.

    Returns responses with their engagement metrics.
    """
    try:
        collector = get_collector()
        data = collector.get_training_data()

        return {
            "count": len(data),
            "data": data[:limit]
        }

    except Exception as e:
        logger.error(f"Failed to get training data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# SCOREBOARD ENDPOINTS - LLM Quality Metrics
# =============================================================================

class ScoreResponseRequest(BaseModel):
    """Request to score a Guardian response."""
    response_id: str
    response_text: str
    sources: List[str]
    max_chars: int = 450


class SourceQARequest(BaseModel):
    """Request to add source QA labels."""
    response_id: str
    source_labels: Dict[str, str]  # URL -> SUPPORTED/REFUTED/UNRELATED


@router.post("/scoreboard/score")
async def score_response(request: ScoreResponseRequest):
    """
    Score a Guardian response for quality metrics.

    Checks:
    - Rule violations (no questions, no irony, etc.)
    - Format compliance (length, sources)
    - Genericness detection
    - Escalation risk
    """
    try:
        from src.ml.learning.scoreboard import get_scoreboard

        scoreboard = get_scoreboard()
        score = scoreboard.score_response(
            response_id=request.response_id,
            response_text=request.response_text,
            sources=request.sources,
            max_chars=request.max_chars
        )

        return {
            "response_id": score.response_id,
            "char_count": score.char_count,
            "sentence_count": score.sentence_count,
            "source_count": score.source_count,
            "violations": [v.value for v in score.violations],
            "violation_count": score.violation_count,
            "genericness_score": round(score.genericness_score, 3),
            "escalation_risk": round(score.escalation_risk, 3),
            "passed": score.violation_count == 0
        }

    except Exception as e:
        logger.error(f"Response scoring failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scoreboard/source-qa")
async def submit_source_qa(request: SourceQARequest):
    """
    Submit source relevance QA labels.

    Labels: SUPPORTED, REFUTED, UNRELATED

    This is the "ehrlichste KPI" - if UNRELATED > 10-15%,
    the ranker/query expansion needs improvement.
    """
    try:
        from src.ml.learning.scoreboard import get_scoreboard, SourceRelevanceLabel

        scoreboard = get_scoreboard()

        # Convert string labels to enum
        labels = {}
        for url, label_str in request.source_labels.items():
            try:
                labels[url] = SourceRelevanceLabel(label_str.upper())
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid label '{label_str}'. Use: SUPPORTED, REFUTED, UNRELATED"
                )

        relevance_rate = scoreboard.add_source_qa(request.response_id, labels)

        if relevance_rate is None:
            raise HTTPException(status_code=404, detail="Response not found")

        return {
            "response_id": request.response_id,
            "source_relevance_rate": round(relevance_rate, 3),
            "labels_added": len(labels),
            "quality_warning": relevance_rate < 0.85
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Source QA submission failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/scoreboard/summary")
async def get_scoreboard_summary(last_n: Optional[int] = None):
    """
    Get aggregate scoreboard metrics.

    Key metrics:
    - avg_chars: Average response length
    - violation_rate: % responses with any violation
    - genericness_rate: % responses flagged as generic
    - source_relevance_rate: % sources that are relevant (from QA)
    """
    try:
        from src.ml.learning.scoreboard import get_scoreboard

        scoreboard = get_scoreboard()
        summary = scoreboard.get_summary(last_n=last_n)

        return {
            "total_responses": summary.total_responses,
            "averages": {
                "chars": summary.avg_chars,
                "sentences": summary.avg_sentences,
                "sources": summary.avg_sources,
                "violations": summary.avg_violations
            },
            "rates": {
                "violation_rate": summary.violation_rate,
                "genericness_rate": summary.genericness_rate,
                "escalation_rate": summary.escalation_rate,
                "source_relevance_rate": summary.source_relevance_rate
            },
            "violation_breakdown": summary.violation_counts,
            "quality_status": "GOOD" if summary.violation_rate < 0.1 else "NEEDS_REVIEW"
        }

    except Exception as e:
        logger.error(f"Failed to get scoreboard summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/scoreboard/problems")
async def get_problem_responses(min_violations: int = 2):
    """
    Get responses with multiple violations for review.

    Useful for identifying systematic issues.
    """
    try:
        from src.ml.learning.scoreboard import get_scoreboard

        scoreboard = get_scoreboard()
        problems = scoreboard.get_problem_responses(min_violations=min_violations)

        return {
            "count": len(problems),
            "responses": [
                {
                    "response_id": p.response_id,
                    "violations": [v.value for v in p.violations],
                    "violation_count": p.violation_count,
                    "genericness_score": round(p.genericness_score, 3),
                    "escalation_risk": round(p.escalation_risk, 3)
                }
                for p in problems
            ]
        }

    except Exception as e:
        logger.error(f"Failed to get problem responses: {e}")
        raise HTTPException(status_code=500, detail=str(e))
