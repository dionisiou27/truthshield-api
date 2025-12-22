"""
ML Feedback API Endpoints
Endpoints for updating engagement metrics and retrieving ML insights
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import logging

from src.core.ml_learning import ml_system, update_engagement

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/ml", tags=["ML Learning"])


class EngagementUpdate(BaseModel):
    """Engagement metrics update from social media"""
    interaction_id: str = Field(..., description="The interaction ID returned from fact-check response")
    likes: int = Field(0, ge=0, description="Number of likes/hearts")
    replies: int = Field(0, ge=0, description="Number of replies/comments")
    shares: int = Field(0, ge=0, description="Number of shares/retweets")
    top_comment: bool = Field(False, description="Whether the response achieved top comment status")


class ExpertFeedback(BaseModel):
    """Expert verification/correction feedback"""
    interaction_id: str = Field(..., description="The interaction ID to provide feedback for")
    is_correct: bool = Field(..., description="Whether the fact-check verdict was correct")
    correction: Optional[str] = Field(None, description="Correction text if verdict was wrong")


class EngagementResponse(BaseModel):
    """Response for engagement update"""
    success: bool
    message: str
    engagement_score: Optional[float] = None
    learning_signal: Optional[str] = None


class MLStatsResponse(BaseModel):
    """ML system statistics response"""
    total_interactions: int
    patterns_learned: int
    by_signal: Dict[str, int]
    by_platform: Dict[str, Dict[str, Any]]
    avatar_performance: Dict[str, Dict[str, Any]]


class PatternMatchResponse(BaseModel):
    """Pattern match check response"""
    has_matches: bool
    patterns: List[Dict[str, Any]]
    confidence_boost: float


@router.post("/engagement", response_model=EngagementResponse)
async def update_engagement_metrics(update: EngagementUpdate):
    """
    Update engagement metrics for a fact-check interaction.

    Call this endpoint after posting a fact-check response to social media
    to report the engagement metrics. This data is used to train the ML
    system on what makes effective responses.

    The learning signal is automatically determined:
    - POSITIVE: High engagement (score > 0.7)
    - NEGATIVE: Low engagement with some activity (score < 0.2)
    - NEUTRAL: Moderate engagement or no activity
    """
    try:
        await ml_system.update_with_engagement(
            interaction_id=update.interaction_id,
            likes=update.likes,
            replies=update.replies,
            shares=update.shares,
            top_comment=update.top_comment
        )

        # Calculate engagement score for response
        engagement_score = (update.likes * 1.0 + update.replies * 2.0 +
                          update.shares * 3.0 + (10.0 if update.top_comment else 0)) / 16.0

        # Determine learning signal
        if engagement_score > 0.7:
            learning_signal = "positive"
        elif engagement_score < 0.2 and (update.likes + update.replies + update.shares) > 0:
            learning_signal = "negative"
        else:
            learning_signal = "neutral"

        logger.info(f"📊 Updated engagement for {update.interaction_id}: score={engagement_score:.2f}")

        return EngagementResponse(
            success=True,
            message=f"Engagement metrics updated successfully",
            engagement_score=round(engagement_score, 3),
            learning_signal=learning_signal
        )

    except Exception as e:
        logger.error(f"Failed to update engagement: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update engagement: {str(e)}")


@router.post("/expert-feedback", response_model=EngagementResponse)
async def submit_expert_feedback(feedback: ExpertFeedback):
    """
    Submit expert verification or correction for a fact-check.

    Use this endpoint when a human expert reviews a fact-check result:
    - is_correct=True: Expert confirms the verdict was accurate
    - is_correct=False: Expert provides correction (higher priority learning signal)

    Expert feedback is weighted more heavily than engagement metrics.
    """
    try:
        ml_system.logger.add_expert_feedback(
            interaction_id=feedback.interaction_id,
            is_correct=feedback.is_correct,
            correction=feedback.correction
        )

        signal = "expert_verified" if feedback.is_correct else "expert_corrected"

        logger.info(f"👨‍🔬 Expert feedback for {feedback.interaction_id}: {signal}")

        return EngagementResponse(
            success=True,
            message=f"Expert feedback recorded: {signal}",
            learning_signal=signal
        )

    except Exception as e:
        logger.error(f"Failed to record expert feedback: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to record feedback: {str(e)}")


@router.get("/stats", response_model=MLStatsResponse)
async def get_ml_statistics():
    """
    Get ML learning statistics.

    Returns comprehensive statistics about the ML system including:
    - Total interactions logged
    - Number of patterns learned
    - Breakdown by learning signal (positive, negative, neutral, expert)
    - Performance by platform
    - Performance by avatar
    """
    try:
        stats = ml_system.get_learning_stats()

        return MLStatsResponse(
            total_interactions=stats.get("total_interactions", 0),
            patterns_learned=stats.get("patterns_learned", 0),
            by_signal=stats.get("by_signal", {}),
            by_platform=stats.get("by_platform", {}),
            avatar_performance=stats.get("avatar_performance", {})
        )

    except Exception as e:
        logger.error(f"Failed to get ML stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve stats: {str(e)}")


@router.post("/check-patterns", response_model=PatternMatchResponse)
async def check_claim_patterns(claim: str):
    """
    Check if a claim matches any known patterns.

    Use this to preview what the ML system knows about a claim before
    running a full fact-check. Returns matching patterns and confidence boost.
    """
    try:
        similar_patterns = ml_system.pattern_learner.find_similar_patterns(claim)

        patterns_data = []
        confidence_boost = 0.0

        for pattern in similar_patterns[:5]:
            patterns_data.append({
                "pattern_id": pattern.pattern_id,
                "pattern_type": pattern.pattern_type,
                "keywords_matched": len([kw for kw in pattern.keywords if kw in claim.lower()]),
                "occurrence_count": pattern.occurrence_count,
                "avg_confidence": round(pattern.avg_detection_confidence, 3)
            })

        if similar_patterns:
            best = similar_patterns[0]
            confidence_boost = min(0.15, best.avg_detection_confidence * 0.05 * min(best.occurrence_count, 10))

        return PatternMatchResponse(
            has_matches=len(patterns_data) > 0,
            patterns=patterns_data,
            confidence_boost=round(confidence_boost, 3)
        )

    except Exception as e:
        logger.error(f"Failed to check patterns: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to check patterns: {str(e)}")


@router.get("/training-data")
async def get_training_data(
    signal_filter: Optional[str] = None,
    limit: int = 100
):
    """
    Get labeled training data for ML model development.

    Returns interactions with learning signals (labeled data) that can be
    used for training external ML models or analysis.

    Parameters:
    - signal_filter: Filter by learning signal (positive, negative, expert_verified, expert_corrected)
    - limit: Maximum number of records to return (default 100, max 1000)
    """
    try:
        limit = min(limit, 1000)  # Cap at 1000

        data = ml_system.logger.get_training_data(
            signal_filter=signal_filter,
            limit=limit
        )

        return {
            "count": len(data),
            "signal_filter": signal_filter,
            "data": data
        }

    except Exception as e:
        logger.error(f"Failed to get training data: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve training data: {str(e)}")


@router.get("/optimization/{platform}/{avatar}")
async def get_response_optimization(platform: str, avatar: str):
    """
    Get learned optimal response parameters for a platform/avatar combination.

    Returns learned parameters like optimal response length based on
    historical engagement data.
    """
    try:
        params = ml_system.get_response_optimization(platform, avatar)

        return {
            "platform": platform,
            "avatar": avatar,
            "optimal_params": params
        }

    except Exception as e:
        logger.error(f"Failed to get optimization params: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve params: {str(e)}")
