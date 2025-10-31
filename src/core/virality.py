from typing import Dict


class ViralityPredictor:
    """
    Simple, transparent virality score 0–10 based on:
    - views (scaled by 5k)
    - growth_rate_24h (0..1 mapped to 0..10)
    - author_followers (scaled by 10k)
    """

    def __init__(self, views_scale: float = 5000.0, followers_scale: float = 10000.0) -> None:
        self.views_scale = max(1.0, float(views_scale))
        self.followers_scale = max(1.0, float(followers_scale))

    def predict(self, item: Dict) -> float:
        views = float(item.get("views") or 0.0)
        growth_rate_24h = float(item.get("growth_rate_24h") or 0.0)  # 0..N
        author_followers = float(item.get("author_followers") or 0.0)

        v_views = min(1.5, views / self.views_scale)  # cap 1.5
        v_growth = min(1.5, growth_rate_24h)  # assume already 0..N, cap 1.5
        v_followers = min(1.5, author_followers / self.followers_scale)

        score_0_1 = min(1.0, 0.5 * v_growth + 0.3 * v_views + 0.2 * v_followers)
        return round(score_0_1 * 10.0, 2)


