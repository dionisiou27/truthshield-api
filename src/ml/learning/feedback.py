"""
Feedback Collector for Guardian Learning Loop
Collects engagement metrics and stores for learning.

Implements outcome snapshots at 1h/6h/24h as recommended for
proper learning signal development.
"""
from typing import Dict, List, Optional
from pydantic import BaseModel
from datetime import datetime
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class OutcomeSnapshot(BaseModel):
    """
    Snapshot of engagement at a point in time.

    Captured at 1h, 6h, 24h after posting to track
    engagement trajectory over time.
    """
    snapshot_time: datetime
    hours_after_post: float

    # Core metrics at this snapshot
    likes: int = 0
    replies: int = 0
    shares: int = 0
    views: int = 0

    # Quality signals
    top_comment_position: Optional[int] = None
    reply_sentiment_avg: float = 0.0
    constructive_reply_ratio: float = 0.0

    # Negative signals
    reports: int = 0
    hidden: bool = False
    deleted: bool = False
    toxicity_in_replies: float = 0.0
    escalation_detected: bool = False


class EngagementMetrics(BaseModel):
    """
    Engagement metrics from platform with outcome snapshots.

    Log structure per intervention (JSONL):
    - claim_text, language, claim_type, risk_level
    - sources_selected (incl. scores + source_class + domain)
    - variant_id (tone + source_mix + template_id)
    - response_text + char_count + sentence_count
    - outcome snapshots at 1h / 6h / 24h
    """
    response_id: str
    avatar: str
    platform: str = "tiktok"

    # Core metrics (current/latest)
    likes: int = 0
    replies: int = 0
    shares: int = 0
    views: int = 0

    # Position metrics
    top_comment_position: Optional[int] = None  # 1-10 or None
    is_pinned: bool = False

    # Quality signals
    reply_sentiment_avg: float = 0.0  # -1 to 1
    constructive_reply_ratio: float = 0.0  # 0 to 1

    # Negative signals
    reports: int = 0
    hidden: bool = False
    deleted: bool = False

    # Timestamps
    collected_at: datetime
    posted_at: Optional[datetime] = None  # When response was posted

    # Outcome Snapshots (1h / 6h / 24h)
    snapshot_1h: Optional[OutcomeSnapshot] = None
    snapshot_6h: Optional[OutcomeSnapshot] = None
    snapshot_24h: Optional[OutcomeSnapshot] = None

    # Legacy fields for backwards compat
    delta_1h: Optional[Dict] = None
    delta_24h: Optional[Dict] = None


class ResponseLog(BaseModel):
    """Log entry for a Guardian response."""
    response_id: str
    claim_id: str
    timestamp: datetime

    # Input
    claim_text: str
    claim_type: List[str]
    risk_level: str
    language: str

    # Decision
    tone_variant: str
    source_mix: str
    decision_id: Optional[str] = None

    # Output
    response_text: str
    sources_used: List[Dict]

    # Metrics (filled in later)
    metrics: Optional[EngagementMetrics] = None
    reward: Optional[float] = None
    feedback_collected_at: Optional[datetime] = None


class FeedbackCollector:
    """
    Collects and stores feedback for Guardian learning.

    Storage:
    - JSONL format for append-only logging
    - Separate files for responses and metrics
    """

    def __init__(self, data_dir: str = "demo_data/ml"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.responses_file = self.data_dir / "guardian_responses.jsonl"
        self.metrics_file = self.data_dir / "guardian_metrics.jsonl"

        logger.info("FeedbackCollector initialized: %s", self.data_dir)

    def log_response(self, log: ResponseLog) -> str:
        """
        Log a Guardian response for later feedback.

        Args:
            log: ResponseLog entry

        Returns:
            response_id
        """
        with open(self.responses_file, "a", encoding="utf-8") as f:
            f.write(log.model_dump_json() + "\n")

        logger.info("Logged response %s for claim %s", log.response_id[:8], log.claim_id[:8])
        return log.response_id

    def log_metrics(self, metrics: EngagementMetrics) -> None:
        """
        Log engagement metrics for a response.

        Args:
            metrics: EngagementMetrics from platform
        """
        with open(self.metrics_file, "a", encoding="utf-8") as f:
            f.write(metrics.model_dump_json() + "\n")

        logger.info("Logged metrics for response %s: likes=%d, replies=%d",
                   metrics.response_id[:8], metrics.likes, metrics.replies)

    def calculate_derived_metrics(self, metrics: EngagementMetrics) -> Dict:
        """
        Calculate derived metrics for reward calculation.

        Returns:
            Dict with normalized metrics for bandit update
        """
        # Top comment proxy: based on position (1=best)
        if metrics.top_comment_position:
            top_comment_proxy = max(0, 1 - (metrics.top_comment_position - 1) / 10)
        elif metrics.is_pinned:
            top_comment_proxy = 1.0
        else:
            top_comment_proxy = 0.3  # Default if not in top comments

        # Reply quality: constructive ratio + positive sentiment
        reply_quality = (
            0.6 * metrics.constructive_reply_ratio +
            0.4 * (metrics.reply_sentiment_avg + 1) / 2  # Normalize to 0-1
        )

        # Like/reply ratio (engagement balance)
        total_engagement = metrics.likes + metrics.replies
        if total_engagement > 0:
            like_reply_ratio = metrics.likes / total_engagement
        else:
            like_reply_ratio = 0.5

        # Shares proxy (normalized)
        shares_proxy = min(1.0, metrics.shares / 100) if metrics.shares else 0.0

        # Reports rate (normalized, higher is worse)
        total_interactions = metrics.likes + metrics.replies + metrics.shares + 1
        reports_rate = min(1.0, metrics.reports / total_interactions * 10)

        # Toxicity proxy (based on negative sentiment in replies)
        toxicity = max(0, -metrics.reply_sentiment_avg)

        # Deleted/hidden penalty
        if metrics.deleted or metrics.hidden:
            reports_rate = 1.0
            toxicity = 1.0

        return {
            "top_comment_proxy": top_comment_proxy,
            "reply_quality": reply_quality,
            "like_reply_ratio": like_reply_ratio,
            "shares_proxy": shares_proxy,
            "reports_rate": reports_rate,
            "toxicity_in_replies": toxicity
        }

    def get_recent_responses(self, limit: int = 100) -> List[ResponseLog]:
        """Get recent response logs."""
        responses = []

        if not self.responses_file.exists():
            return responses

        with open(self.responses_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        for line in lines[-limit:]:
            try:
                data = json.loads(line)
                responses.append(ResponseLog(**data))
            except Exception as e:
                logger.warning("Failed to parse response log: %s", e)

        return responses

    def get_metrics_for_response(self, response_id: str) -> Optional[EngagementMetrics]:
        """Get the latest metrics for a response."""
        if not self.metrics_file.exists():
            return None

        latest = None
        with open(self.metrics_file, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    data = json.loads(line)
                    if data.get("response_id") == response_id:
                        latest = EngagementMetrics(**data)
                except Exception:
                    continue

        return latest

    def get_training_data(self, min_feedback_age_hours: int = 24) -> List[Dict]:
        """
        Get training data for offline analysis.

        Returns:
            List of dicts with response, metrics, and derived features
        """
        training_data = []
        cutoff = datetime.now().timestamp() - (min_feedback_age_hours * 3600)

        responses = self.get_recent_responses(limit=1000)

        for response in responses:
            # Skip if too recent
            if response.timestamp.timestamp() > cutoff:
                continue

            metrics = self.get_metrics_for_response(response.response_id)
            if not metrics:
                continue

            derived = self.calculate_derived_metrics(metrics)

            training_data.append({
                "response_id": response.response_id,
                "claim_type": response.claim_type,
                "risk_level": response.risk_level,
                "tone_variant": response.tone_variant,
                "source_mix": response.source_mix,
                "metrics": metrics.model_dump(),
                "derived_metrics": derived,
                "timestamp": response.timestamp.isoformat()
            })

        logger.info("Generated %d training examples", len(training_data))
        return training_data


# Singleton instance
_collector_instance: Optional[FeedbackCollector] = None


def get_collector(data_dir: str = "demo_data/ml") -> FeedbackCollector:
    """Get or create the global feedback collector."""
    global _collector_instance
    if _collector_instance is None:
        _collector_instance = FeedbackCollector(data_dir)
    return _collector_instance
