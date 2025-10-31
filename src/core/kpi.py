from typing import Dict, Optional
from dataclasses import dataclass


@dataclass
class KPIDecision:
    action: str  # HITL, SEMI_HITL, PREBUNK
    projected_reach_48h: float
    harm_weight: float
    virality_probability: float
    astro_score: float
    cost_per_reach: Optional[float]
    client_max_cpr: Optional[float]
    reasons: Dict[str, str]


class KPIDecider:
    def __init__(self, harm_weights: Optional[Dict[str, float]] = None):
        # Defaults can be tuned; topics to weights
        self.harm_weights = harm_weights or {
            "elections": 3.0,
            "health": 2.0,
            "safety": 2.0,
            "economy": 1.5,
            "reputation": 1.0,
            "meme": 0.5,
        }

    def set_harm_weight(self, topic: str, weight: float) -> None:
        self.harm_weights[(topic or "").strip().lower()] = float(weight)

    def get_harm_weight(self, topic: Optional[str], fallback: Optional[float] = None) -> float:
        if fallback is not None:
            return float(fallback)
        if not topic:
            return 1.0
        return float(self.harm_weights.get(topic.strip().lower(), 1.0))

    def estimate_projected_reach_48h(self, views: float, growth_rate_24h: float) -> float:
        # Simple exponential-ish projection: next 48h ~ current * (1 + r)^2
        v = max(0.0, float(views))
        r = max(0.0, float(growth_rate_24h))
        return round(v * (1.0 + r) ** 2, 2)

    def virality_probability(self, growth_rate_24h: float) -> float:
        # Map growth rate to probability 0..1 (cap at 1.0)
        r = max(0.0, float(growth_rate_24h))
        return min(1.0, r / 0.5)  # 50% growth ~ prob 1.0

    def cost_per_reach(self, avg_analyst_seconds: float, salary_rate_per_hour: float, projected_reach: float) -> Optional[float]:
        if projected_reach <= 0:
            return None
        hours = max(0.0, float(avg_analyst_seconds)) / 3600.0
        cost = hours * float(salary_rate_per_hour)
        return round(cost / projected_reach, 6)

    def decide(
        self,
        *,
        views: float,
        growth_rate_24h: float,
        harm_topic: Optional[str] = None,
        harm_weight_override: Optional[float] = None,
        astro_score: float = 0.0,
        avg_analyst_seconds: Optional[float] = None,
        salary_rate_per_hour: Optional[float] = None,
        client_max_cpr: Optional[float] = None,
    ) -> KPIDecision:
        projected = self.estimate_projected_reach_48h(views, growth_rate_24h)
        harm_w = self.get_harm_weight(harm_topic, harm_weight_override)
        vir_prob = self.virality_probability(growth_rate_24h)

        # Primary KPI rules
        action = "PREBUNK"
        reasons = {"primary": "did_not_meet_thresholds"}
        if projected > 50000 and harm_w >= 1.5:
            action = "HITL"
            reasons["primary"] = "projected>50k_and_harm>=1.5"
        elif 10000 <= projected <= 50000 and astro_score >= 6.0:
            action = "SEMI_HITL"
            reasons["primary"] = "projected_10_50k_and_astro>=6"

        # Secondary KPI cost-based filter
        cpr = None
        if avg_analyst_seconds is not None and salary_rate_per_hour is not None:
            cpr = self.cost_per_reach(avg_analyst_seconds, salary_rate_per_hour, projected)
            if cpr is not None and client_max_cpr is not None and cpr > client_max_cpr:
                reasons["secondary"] = "cpr_above_client_max"
                action = "PREBUNK"

        return KPIDecision(
            action=action,
            projected_reach_48h=projected,
            harm_weight=harm_w,
            virality_probability=vir_prob,
            astro_score=astro_score,
            cost_per_reach=cpr,
            client_max_cpr=client_max_cpr,
            reasons=reasons,
        )


