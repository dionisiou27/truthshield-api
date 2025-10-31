from typing import Dict
from dataclasses import dataclass


@dataclass
class PrioritizedItem:
    priority: str  # "high" | "medium" | "low"
    watchlist: bool
    pools: Dict[str, bool]
    score_components: Dict[str, float]
    thresholds: Dict[str, float]


class PrioritizationEngine:
    """
    Implements Reach-first / Risk-first prioritization.

    - Track-Pool: content with views >= threshold OR growth_rate_24h >= threshold
    - Account-Pool: author with followers >= threshold OR follower_spike_24h >= threshold
    - Coordination: gates high priority when above coordination_min_score
    """

    def __init__(
        self,
        track_pool_min_views: int,
        track_pool_min_growth_rate_24h: float,
        account_pool_min_followers: int,
        account_pool_min_follower_spike_24h: float,
        coordination_min_score: float,
    ) -> None:
        self.track_pool_min_views = track_pool_min_views
        self.track_pool_min_growth_rate_24h = track_pool_min_growth_rate_24h
        self.account_pool_min_followers = account_pool_min_followers
        self.account_pool_min_follower_spike_24h = account_pool_min_follower_spike_24h
        self.coordination_min_score = coordination_min_score

    def prioritize(self, item: Dict) -> PrioritizedItem:
        views = float(item.get("views") or 0)
        growth_rate_24h = float(item.get("growth_rate_24h") or 0.0)
        author_followers = float(item.get("author_followers") or 0)
        follower_spike_24h = float(item.get("follower_spike_24h") or 0.0)
        coordination_score = float(item.get("coordination_score") or 0.0)

        in_track_pool = (views >= self.track_pool_min_views) or (
            growth_rate_24h >= self.track_pool_min_growth_rate_24h
        )
        in_account_pool = (author_followers >= self.account_pool_min_followers) or (
            follower_spike_24h >= self.account_pool_min_follower_spike_24h
        )

        # Simple multiplicative-like components (transparent, not a secret score)
        reach_component = max(
            views / max(self.track_pool_min_views, 1),
            growth_rate_24h / max(self.track_pool_min_growth_rate_24h, 1e-6),
        )
        risk_component = max(
            author_followers / max(self.account_pool_min_followers, 1),
            follower_spike_24h / max(self.account_pool_min_follower_spike_24h, 1e-6),
        )
        coordination_component = coordination_score / max(self.coordination_min_score, 1e-6)

        # Priority decision
        watchlist = in_track_pool or in_account_pool
        if watchlist and coordination_score >= self.coordination_min_score:
            priority = "high"
        elif watchlist:
            priority = "medium"
        else:
            priority = "low"

        return PrioritizedItem(
            priority=priority,
            watchlist=watchlist,
            pools={
                "track_pool": in_track_pool,
                "account_pool": in_account_pool,
            },
            score_components={
                "reach": reach_component,
                "risk": risk_component,
                "coordination": coordination_component,
            },
            thresholds={
                "track_pool_min_views": float(self.track_pool_min_views),
                "track_pool_min_growth_rate_24h": float(self.track_pool_min_growth_rate_24h),
                "account_pool_min_followers": float(self.account_pool_min_followers),
                "account_pool_min_follower_spike_24h": float(self.account_pool_min_follower_spike_24h),
                "coordination_min_score": float(self.coordination_min_score),
            },
        )


