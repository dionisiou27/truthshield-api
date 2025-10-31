from typing import Dict, List
from dataclasses import dataclass


@dataclass
class AstroScoreResult:
    score_0_10: float
    category_scores: Dict[str, float]
    signals: Dict[str, float]
    notes: List[str]


class CoordinatedBehaviorDetector:
    """
    Rule+score-based detector for coordinated manipulation / astroturfing.

    Inputs: flat dict of measured signals. Examples:
      - Account/Network: follower_spike_24h, new_accounts_ratio, text_reuse_ratio,
        synchronized_posting_ratio, shared_fingerprint_ratio, account_age_days
      - Content: identical_media_ratio, repeated_phrases_ratio, reply_stacking_ratio
      - Engagement: comment_like_to_view_ratio, author_network_density
      - Temporal: burst_posts_in_window, posting_window_minutes
      - Stylometry: stylometry_similarity, recurring_token_signature, unnatural_punctuation_ratio

    Output: Astro-Score 0–10 with per-category contributions and notes.
    """

    def __init__(self) -> None:
        # Feature-level weights (initial spec) - can be tuned or made configurable
        self.feature_weights = {
            # Account / Network
            "follower_spike_24h": 1.0,  # Δ > 200% / 24h
            "fresh_spawn_activity": 0.5,  # account_age<30 & post_count>5
            "overlapping_hashtags_ratio": 0.8,  # > 0.8
            "cross_post_clip_count_1h": 1.5,  # same clip on >3 accounts <1h (normalized)
            # Content
            "ngram_overlap_ratio": 1.2,  # > 0.7
            "unnatural_punctuation_ratio": 0.3,
            "emotional_extrema_sigma": 0.4,  # > 2σ
            # Network/Temporal
            "reply_cluster_density": 1.5,  # > 0.7
            "posting_time_sync_score": 1.0,  # synchronized windows
            "shared_ip_device_flag": 1.0,  # optional flag (0/1)
            # Engagement anomalies
            "comment_like_over_median_multiplier": 0.5,  # >2x
            "like_view_sigma": 0.5,  # >2σ
            # Meta
            "bad_domain_ratio": 0.8,  # recurring low-cred sources
            "multilingual_copy_flag": 0.7,  # translated duplicates
        }

    def _clip01(self, x: float) -> float:
        return max(0.0, min(1.0, float(x)))

    def _sigmoid(self, x: float) -> float:
        # Stable sigmoid; compress extremes, centered at ~2.5 initial sum
        import math
        return 1.0 / (1.0 + math.exp(-x))

    def score(self, signals: Dict[str, float]) -> AstroScoreResult:
        notes: List[str] = []
        # Feature normalization helpers
        follower_spike_norm = self._clip01((signals.get("follower_spike_24h", 0.0) or 0.0) / 2.0)
        fresh_spawn_activity = 1.0 if (signals.get("account_age_days", 365.0) or 365.0) < 30 and (signals.get("post_count_30d", 0.0) or 0.0) > 5 else 0.0
        overlapping_hashtags_ratio = self._clip01(signals.get("overlapping_hashtags_ratio", 0.0) or 0.0)
        cross_post_clip_count_1h = min(1.0, (signals.get("cross_post_clip_count_1h", 0.0) or 0.0) / 3.0)

        ngram_overlap_ratio = self._clip01(signals.get("ngram_overlap_ratio", 0.0) or 0.0)
        unnatural_punct = self._clip01(signals.get("unnatural_punctuation_ratio", 0.0) or 0.0)
        emotional_extrema_sigma = max(0.0, signals.get("emotional_extrema_sigma", 0.0) or 0.0)

        reply_cluster_density = self._clip01(signals.get("reply_cluster_density", 0.0) or 0.0)
        posting_time_sync_score = self._clip01(signals.get("posting_time_sync_score", 0.0) or 0.0)
        shared_ip_device_flag = 1.0 if (signals.get("shared_ip_device_flag", 0.0) or 0.0) else 0.0

        comment_like_over_median_multiplier = max(0.0, (signals.get("comment_like_over_median_multiplier", 0.0) or 0.0) - 1.0)  # center at 1x
        like_view_sigma = max(0.0, (signals.get("like_view_sigma", 0.0) or 0.0))

        bad_domain_ratio = self._clip01(signals.get("bad_domain_ratio", 0.0) or 0.0)
        multilingual_copy_flag = 1.0 if (signals.get("multilingual_copy_flag", 0.0) or 0.0) else 0.0

        # Sum of weighted features
        feat = {
            "follower_spike_24h": follower_spike_norm,
            "fresh_spawn_activity": fresh_spawn_activity,
            "overlapping_hashtags_ratio": overlapping_hashtags_ratio,
            "cross_post_clip_count_1h": cross_post_clip_count_1h,
            "ngram_overlap_ratio": ngram_overlap_ratio,
            "unnatural_punctuation_ratio": unnatural_punct,
            "emotional_extrema_sigma": emotional_extrema_sigma,
            "reply_cluster_density": reply_cluster_density,
            "posting_time_sync_score": posting_time_sync_score,
            "shared_ip_device_flag": shared_ip_device_flag,
            "comment_like_over_median_multiplier": comment_like_over_median_multiplier,
            "like_view_sigma": like_view_sigma,
            "bad_domain_ratio": bad_domain_ratio,
            "multilingual_copy_flag": multilingual_copy_flag,
        }

        weighted_sum = 0.0
        for k, v in feat.items():
            weighted_sum += (self.feature_weights.get(k, 0.0) or 0.0) * float(v)

        # Notes for high-impact signals
        if follower_spike_norm >= 1.0:
            notes.append("Follower spike >200% in 24h")
        if cross_post_clip_count_1h >= 1.0:
            notes.append("Cross-posting same clip across multiple accounts <1h")
        if reply_cluster_density > 0.7:
            notes.append("High reply/retweet cluster density")
        if ngram_overlap_ratio > 0.7:
            notes.append("High n-gram overlap across posts")
        if overlapping_hashtags_ratio > 0.8:
            notes.append("Overlapping hashtags across new accounts")

        # Map to 0..10 via sigmoid (smooth scaling)
        prob_0_1 = self._clip01(self._sigmoid(weighted_sum) - 0.5) * 2.0  # center around 0.5
        score_0_10 = round(10.0 * prob_0_1, 2)

        return AstroScoreResult(
            score_0_10=score_0_10,
            category_scores={  # expose major contributors for UI
                "account_network": round(
                    follower_spike_norm + fresh_spawn_activity + overlapping_hashtags_ratio + cross_post_clip_count_1h, 3
                ),
                "content": round(ngram_overlap_ratio + unnatural_punct + emotional_extrema_sigma, 3),
                "engagement": round(comment_like_over_median_multiplier + like_view_sigma, 3),
                "temporal_network": round(reply_cluster_density + posting_time_sync_score + shared_ip_device_flag, 3),
                "meta": round(bad_domain_ratio + multilingual_copy_flag, 3),
            },
            signals={k: float(v) for k, v in {**signals, **feat}.items()},
            notes=notes,
        )


