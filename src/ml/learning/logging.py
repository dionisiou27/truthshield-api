"""
Learning Logger for Guardian ML Pipeline
Structured logging for ML decisions, training, and evaluation.
"""
from typing import Dict, List, Any, Optional
from pydantic import BaseModel
from datetime import datetime
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class MLEvent(BaseModel):
    """Base ML event for logging."""
    event_type: str
    timestamp: datetime
    data: Dict[str, Any]


class LearningLogger:
    """
    Structured logger for ML pipeline events.

    Event types:
    - claim_analysis: Claim typing results
    - source_ranking: Source selection decisions
    - bandit_decision: Tone/source-mix selection
    - bandit_update: Feedback-driven updates
    - training_run: Offline training events
    - evaluation: Model evaluation results
    """

    def __init__(self, log_dir: str = "demo_data/ml/logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.event_file = self.log_dir / "ml_events.jsonl"
        self.decision_file = self.log_dir / "decisions.jsonl"

        logger.info("LearningLogger initialized: %s", self.log_dir)

    def _write_event(self, event: MLEvent, file_path: Path):
        """Write event to JSONL file."""
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(event.model_dump_json() + "\n")

    def log_claim_analysis(
        self,
        claim_id: str,
        claim_text: str,
        claim_types: List[str],
        risk_level: str,
        keywords: List[str],
        requires_guardian: bool
    ):
        """Log claim analysis result."""
        event = MLEvent(
            event_type="claim_analysis",
            timestamp=datetime.now(),
            data={
                "claim_id": claim_id,
                "claim_text": claim_text[:200],  # Truncate for logging
                "claim_types": claim_types,
                "risk_level": risk_level,
                "keyword_count": len(keywords),
                "requires_guardian": requires_guardian
            }
        )
        self._write_event(event, self.event_file)
        logger.debug("Logged claim_analysis: %s", claim_id[:8])

    def log_source_ranking(
        self,
        claim_id: str,
        candidates_count: int,
        selected_sources: List[Dict],
        rejected_top: List[Dict],
        ranking_config: Dict
    ):
        """Log source ranking decision."""
        event = MLEvent(
            event_type="source_ranking",
            timestamp=datetime.now(),
            data={
                "claim_id": claim_id,
                "candidates_count": candidates_count,
                "selected_count": len(selected_sources),
                "selected_sources": [
                    {"url": s["url"], "class": s.get("source_class"), "score": s.get("final_score")}
                    for s in selected_sources
                ],
                "rejected_top": rejected_top[:5],
                "ranking_weights": ranking_config
            }
        )
        self._write_event(event, self.event_file)
        logger.debug("Logged source_ranking: %s (%d/%d selected)",
                     claim_id[:8], len(selected_sources), candidates_count)

    def log_bandit_decision(
        self,
        decision_id: str,
        claim_id: str,
        context: Dict,
        tone_variant: str,
        source_mix: str,
        arm_stats: Dict
    ):
        """Log bandit decision."""
        event = MLEvent(
            event_type="bandit_decision",
            timestamp=datetime.now(),
            data={
                "decision_id": decision_id,
                "claim_id": claim_id,
                "context": context,
                "tone_variant": tone_variant,
                "source_mix": source_mix,
                "arm_means": {
                    "tone": {k: v["mean"] for k, v in arm_stats.get("tone_arms", {}).items()},
                    "source": {k: v["mean"] for k, v in arm_stats.get("source_arms", {}).items()}
                }
            }
        )
        self._write_event(event, self.decision_file)
        logger.debug("Logged bandit_decision: %s", decision_id[:8])

    def log_bandit_update(
        self,
        decision_id: str,
        reward: float,
        metrics: Dict,
        derived_metrics: Dict,
        updated_arms: Dict
    ):
        """Log bandit update after feedback."""
        event = MLEvent(
            event_type="bandit_update",
            timestamp=datetime.now(),
            data={
                "decision_id": decision_id,
                "reward": reward,
                "raw_metrics": {
                    "likes": metrics.get("likes"),
                    "replies": metrics.get("replies"),
                    "shares": metrics.get("shares"),
                    "reports": metrics.get("reports")
                },
                "derived_metrics": derived_metrics,
                "updated_arm_means": updated_arms
            }
        )
        self._write_event(event, self.event_file)
        logger.info("Logged bandit_update: %s (reward=%.3f)", decision_id[:8], reward)

    def log_response_generated(
        self,
        response_id: str,
        claim_id: str,
        decision_id: Optional[str],
        response_length: int,
        sources_count: int,
        generation_time_ms: int
    ):
        """Log response generation."""
        event = MLEvent(
            event_type="response_generated",
            timestamp=datetime.now(),
            data={
                "response_id": response_id,
                "claim_id": claim_id,
                "decision_id": decision_id,
                "response_length": response_length,
                "sources_count": sources_count,
                "generation_time_ms": generation_time_ms
            }
        )
        self._write_event(event, self.event_file)

    def get_recent_events(
        self,
        event_type: Optional[str] = None,
        limit: int = 100
    ) -> List[MLEvent]:
        """Get recent ML events."""
        events = []

        if not self.event_file.exists():
            return events

        with open(self.event_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        for line in lines[-limit * 2:]:  # Read extra for filtering
            try:
                data = json.loads(line)
                event = MLEvent(**data)
                if event_type is None or event.event_type == event_type:
                    events.append(event)
            except Exception:
                continue

        return events[-limit:]

    def get_decision_history(self, limit: int = 100) -> List[Dict]:
        """Get recent bandit decisions with outcomes."""
        decisions = []

        if not self.decision_file.exists():
            return decisions

        with open(self.decision_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        for line in lines[-limit:]:
            try:
                data = json.loads(line)
                decisions.append(data)
            except Exception:
                continue

        return decisions

    def get_learning_summary(self) -> Dict:
        """Get summary statistics for learning pipeline."""
        events = self.get_recent_events(limit=1000)

        summary = {
            "total_events": len(events),
            "event_counts": {},
            "recent_rewards": [],
            "avg_reward": 0.0
        }

        rewards = []
        for event in events:
            event_type = event.event_type
            summary["event_counts"][event_type] = summary["event_counts"].get(event_type, 0) + 1

            if event_type == "bandit_update":
                reward = event.data.get("reward", 0)
                rewards.append(reward)

        if rewards:
            summary["recent_rewards"] = rewards[-20:]
            summary["avg_reward"] = sum(rewards) / len(rewards)

        return summary


# Singleton instance
_logger_instance: Optional[LearningLogger] = None


def get_learning_logger(log_dir: str = "demo_data/ml/logs") -> LearningLogger:
    """Get or create the global learning logger."""
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = LearningLogger(log_dir)
    return _logger_instance
