import random
from typing import Dict, List
from dataclasses import dataclass
from src.core.kpi import KPIDecider
from src.core.config import settings


@dataclass
class QASamplingDecision:
    selected: bool
    projected_reach_48h: float
    astro_score: float
    reason: str


class QASampler:
    def __init__(self, decider: KPIDecider) -> None:
        self.decider = decider

    def evaluate(self, item: Dict, astro_score: float) -> QASamplingDecision:
        views = float(item.get("views") or 0.0)
        growth = float(item.get("growth_rate_24h") or 0.0)
        projected = self.decider.estimate_projected_reach_48h(views, growth)
        eligible = (astro_score < settings.qa_low_score_threshold) and (
            projected >= settings.qa_high_spread_projected_reach
        )
        if not eligible:
            return QASamplingDecision(False, projected, astro_score, "not_eligible")
        pick = random.random() < max(0.0, min(1.0, settings.qa_sample_rate))
        return QASamplingDecision(pick, projected, astro_score, "random_pick" if pick else "random_miss")

    def sample_batch(self, items: List[Dict], astro_scores: List[float]) -> List[QASamplingDecision]:
        out: List[QASamplingDecision] = []
        for it, a in zip(items, astro_scores):
            out.append(self.evaluate(it, a))
        return out


