from typing import Dict
from dataclasses import dataclass


@dataclass
class ThreatScore:
    score_0_10: float
    components: Dict[str, float]
    weights: Dict[str, float]


class ThreatScoringEnsemble:
    """score = weighted sum of normalized components, scaled to 0–10.

    Inputs expected in 0–10 range:
      - virality_score (0–10)
      - harm_potential (0–10)
      - astro_score (0–10)
    """

    def __init__(self, w_virality: float = 0.4, w_harm: float = 0.3, w_astro: float = 0.3) -> None:
        s = max(1e-6, w_virality + w_harm + w_astro)
        self.weights = {
            "virality": w_virality / s,
            "harm": w_harm / s,
            "astro": w_astro / s,
        }

    def score(self, virality_score: float, harm_potential: float, astro_score: float) -> ThreatScore:
        v = max(0.0, min(10.0, float(virality_score)))
        h = max(0.0, min(10.0, float(harm_potential)))
        a = max(0.0, min(10.0, float(astro_score)))
        s = (
            self.weights["virality"] * v
            + self.weights["harm"] * h
            + self.weights["astro"] * a
        )
        return ThreatScore(
            score_0_10=round(s, 2),
            components={"virality": v, "harm": h, "astro": a},
            weights=self.weights,
        )


