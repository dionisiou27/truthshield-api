#!/usr/bin/env python3
"""
Test C: Reward Poisoning Simulation

Tests that NegativeSignals properly prevent gaming:
1. High engagement + high report rate → reward goes DOWN
2. Many replies but toxic → reward goes DOWN
3. Bot-like engagement spike → reward goes DOWN

Success criteria:
- Reward decreases when gaming signals present
- Bandit arms do NOT drift toward "provocative wins"
"""
import sys
from pathlib import Path
from typing import Dict, List
from dataclasses import dataclass

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ml.learning.bandit import get_bandit, BanditContext, NegativeSignals
from src.ml.learning.feedback import EngagementMetrics


@dataclass
class PoisonScenario:
    """A gaming/poisoning scenario to test."""
    name: str
    description: str
    metrics: Dict
    expected_reward_direction: str  # "down", "neutral", "up"
    expected_max_reward: float  # Should not exceed this


# =============================================================================
# POISONING SCENARIOS
# =============================================================================

POISON_SCENARIOS = [
    # Scenario 1: High engagement + High reports
    PoisonScenario(
        name="high_engagement_high_reports",
        description="Viral but reported - classic gaming pattern",
        metrics={
            "likes": 5000,
            "replies": 800,
            "shares": 200,
            "views": 50000,
            "comment_position": 1,  # Top comment!
            "reports_count": 150,   # But heavily reported
            "reports_rate": 0.30,   # 30% report rate
            "toxicity_in_replies": 0.1,
            "content_removed": False,
            "platform_flagged": False,
        },
        expected_reward_direction="down",
        expected_max_reward=0.6,  # Reduced from clean engagement (~0.73)
    ),

    # Scenario 2: Content removed
    PoisonScenario(
        name="content_removed",
        description="Content removed by platform - complete nullification",
        metrics={
            "likes": 10000,
            "replies": 2000,
            "shares": 500,
            "views": 100000,
            "comment_position": 1,
            "reports_count": 50,
            "reports_rate": 0.05,
            "toxicity_in_replies": 0.1,
            "content_removed": True,  # REMOVED
            "platform_flagged": True,
        },
        expected_reward_direction="down",
        expected_max_reward=0.0,  # Complete nullification
    ),

    # Scenario 3: Toxic reply chain
    PoisonScenario(
        name="toxic_replies",
        description="High engagement but toxic reactions",
        metrics={
            "likes": 3000,
            "replies": 500,
            "shares": 100,
            "views": 30000,
            "comment_position": 2,
            "reports_count": 20,
            "reports_rate": 0.04,
            "toxicity_in_replies": 0.60,  # 60% toxic replies!
            "content_removed": False,
            "platform_flagged": False,
        },
        expected_reward_direction="down",
        expected_max_reward=0.6,
    ),

    # Scenario 4: Bot-like engagement spike
    PoisonScenario(
        name="bot_engagement_spike",
        description="Suspicious engagement pattern - likely coordinated",
        metrics={
            "likes": 8000,
            "replies": 50,  # Very few replies for this many likes
            "shares": 10,   # Almost no shares
            "views": 10000,
            "comment_position": 1,
            "reports_count": 5,
            "reports_rate": 0.01,
            "toxicity_in_replies": 0.05,
            "content_removed": False,
            "platform_flagged": False,
            "bot_engagement_detected": True,  # Flagged as bot
            "like_velocity_anomaly": True,    # Suspicious spike
        },
        expected_reward_direction="down",
        expected_max_reward=0.4,
    ),

    # Scenario 5: Reply chain escalation
    PoisonScenario(
        name="reply_escalation",
        description="Provocative content causing escalation",
        metrics={
            "likes": 2000,
            "replies": 1000,  # Lots of replies
            "shares": 50,
            "views": 20000,
            "comment_position": 3,
            "reports_count": 30,
            "reports_rate": 0.03,
            "toxicity_in_replies": 0.25,
            "content_removed": False,
            "platform_flagged": False,
            "reply_chain_escalation": 0.70,  # High escalation
        },
        expected_reward_direction="down",
        expected_max_reward=0.5,
    ),

    # Scenario 6: Platform flagged
    PoisonScenario(
        name="platform_flagged",
        description="Content flagged by platform moderation",
        metrics={
            "likes": 4000,
            "replies": 300,
            "shares": 80,
            "views": 40000,
            "comment_position": 2,
            "reports_count": 40,
            "reports_rate": 0.10,
            "toxicity_in_replies": 0.15,
            "content_removed": False,
            "platform_flagged": True,  # FLAGGED
        },
        expected_reward_direction="down",
        expected_max_reward=0.3,
    ),

    # Control: Clean high engagement (should NOT be penalized)
    PoisonScenario(
        name="clean_high_engagement",
        description="Legitimate viral success - no gaming signals",
        metrics={
            "likes": 5000,
            "replies": 400,
            "shares": 150,
            "views": 50000,
            "comment_position": 1,
            "reports_count": 5,
            "reports_rate": 0.001,  # Very low
            "toxicity_in_replies": 0.05,  # Normal
            "content_removed": False,
            "platform_flagged": False,
        },
        expected_reward_direction="up",
        expected_max_reward=1.0,  # Should be high
    ),
]


def calculate_test_reward(metrics: Dict) -> float:
    """
    Calculate reward with NegativeSignals.

    This implements the anti-gaming reward function:

    Positive signals:
    - top_comment_proxy (0.35 weight)
    - reply_quality (0.20 weight)
    - like_reply_ratio (0.15 weight)
    - shares_proxy (0.10 weight)

    Negative signals (NegativeSignals class):
    - reports_rate (-0.30 weight)
    - toxicity_in_replies (-0.15 weight)
    - platform_flag (-0.50 weight)
    - reply_chain_escalation (-0.20 weight)
    - bot_engagement (-0.40 weight)
    - content_removal (-1.0, complete nullification)
    """
    # Content removal = complete nullification
    if metrics.get("content_removed", False):
        return 0.0

    # Positive signals
    likes = metrics.get("likes", 0)
    replies = metrics.get("replies", 0)
    shares = metrics.get("shares", 0)
    views = metrics.get("views", 1)
    position = metrics.get("comment_position", 10)

    # Top comment proxy (position 1 = best)
    top_comment_proxy = max(0, 1 - (position - 1) / 10)

    # Reply quality (simplified - inverse of toxicity)
    toxicity = metrics.get("toxicity_in_replies", 0)
    reply_quality = max(0, 1 - toxicity)

    # Like/reply ratio (healthy engagement)
    if replies > 0:
        like_reply_ratio = min(1.0, likes / (replies * 20))
    else:
        like_reply_ratio = 0.5

    # Shares proxy (normalized)
    shares_proxy = min(1.0, shares / max(views / 500, 1))

    # Positive reward
    positive_reward = (
        0.35 * top_comment_proxy +
        0.20 * reply_quality +
        0.15 * like_reply_ratio +
        0.10 * shares_proxy
    )

    # Negative signals
    reports_rate = metrics.get("reports_rate", 0)
    platform_flagged = metrics.get("platform_flagged", False)
    reply_escalation = metrics.get("reply_chain_escalation", 0)
    bot_detected = metrics.get("bot_engagement_detected", False)

    # Apply NegativeSignals weights
    negative_penalty = (
        NegativeSignals.REPORT_RATE_WEIGHT * reports_rate +
        NegativeSignals.TOXICITY_IN_REPLIES_WEIGHT * toxicity +
        (NegativeSignals.PLATFORM_FLAG_PENALTY if platform_flagged else 0) +
        NegativeSignals.REPLY_CHAIN_ESCALATION * reply_escalation +
        (NegativeSignals.BOT_ENGAGEMENT_PENALTY if bot_detected else 0)
    )

    # Final reward (clamped to 0-1)
    final_reward = max(0.0, min(1.0, positive_reward + negative_penalty))

    return final_reward


def run_poison_tests() -> Dict:
    """Run all poisoning scenarios and check results."""
    print("=" * 70)
    print("TEST C: REWARD POISONING SIMULATION")
    print("=" * 70)
    print("\nTesting NegativeSignals anti-gaming protection...\n")

    results = {
        "passed": 0,
        "failed": 0,
        "scenarios": []
    }

    for scenario in POISON_SCENARIOS:
        reward = calculate_test_reward(scenario.metrics)

        # Check if reward meets expectations
        if scenario.expected_reward_direction == "down":
            passed = reward <= scenario.expected_max_reward
        elif scenario.expected_reward_direction == "up":
            passed = reward >= 0.5  # Should be reasonably high
        else:
            passed = True

        status = "PASS" if passed else "FAIL"

        if passed:
            results["passed"] += 1
        else:
            results["failed"] += 1

        results["scenarios"].append({
            "name": scenario.name,
            "reward": reward,
            "expected_max": scenario.expected_max_reward,
            "passed": passed
        })

        print(f"[{status}] {scenario.name}")
        print(f"       Description: {scenario.description}")
        print(f"       Reward: {reward:.3f} (max expected: {scenario.expected_max_reward})")

        # Show key metrics
        key_metrics = []
        if scenario.metrics.get("reports_rate", 0) > 0.05:
            key_metrics.append(f"reports_rate={scenario.metrics['reports_rate']:.0%}")
        if scenario.metrics.get("toxicity_in_replies", 0) > 0.2:
            key_metrics.append(f"toxicity={scenario.metrics['toxicity_in_replies']:.0%}")
        if scenario.metrics.get("content_removed"):
            key_metrics.append("CONTENT_REMOVED")
        if scenario.metrics.get("platform_flagged"):
            key_metrics.append("PLATFORM_FLAGGED")
        if scenario.metrics.get("bot_engagement_detected"):
            key_metrics.append("BOT_DETECTED")

        if key_metrics:
            print(f"       Signals: {', '.join(key_metrics)}")
        print()

    # Summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Passed: {results['passed']}/{len(POISON_SCENARIOS)}")
    print(f"Failed: {results['failed']}/{len(POISON_SCENARIOS)}")

    if results["failed"] == 0:
        print("\n[OK] All poisoning scenarios correctly penalized!")
        print("[OK] NegativeSignals anti-gaming protection working as expected.")
    else:
        print("\n[WARN] Some scenarios did not behave as expected.")
        print("[WARN] Review NegativeSignals weights and thresholds.")

    return results


def test_bandit_no_drift():
    """
    Test that bandit arms don't drift toward provocative content.

    Simulates multiple rounds where provocative content gets
    high raw engagement but negative signals, vs clean content
    with moderate engagement.
    """
    print("\n" + "=" * 70)
    print("BANDIT DRIFT TEST")
    print("=" * 70)
    print("\nSimulating 50 rounds: provocative vs clean content...\n")

    bandit = get_bandit()

    # Record initial arm distributions
    initial_stats = {}
    for arm_name, arm in bandit.tone_arms.items():
        initial_stats[arm_name] = {
            "alpha": arm.alpha,
            "beta": arm.beta,
            "mean": arm.alpha / (arm.alpha + arm.beta)
        }

    # Simulate rounds
    provocative_arm = "boundary_strict"  # Assume this gets gamed
    clean_arm = "boundary_educational"

    for round_num in range(50):
        # Provocative content: high engagement but toxic/reported
        provocative_metrics = {
            "likes": 3000 + round_num * 100,
            "replies": 500,
            "shares": 50,
            "views": 30000,
            "comment_position": 1,
            "reports_rate": 0.20,  # High reports
            "toxicity_in_replies": 0.40,  # Toxic
            "content_removed": False,
            "platform_flagged": round_num % 5 == 0,  # Sometimes flagged
        }
        provocative_reward = calculate_test_reward(provocative_metrics)

        # Clean content: moderate engagement but healthy
        clean_metrics = {
            "likes": 1000,
            "replies": 200,
            "shares": 80,
            "views": 15000,
            "comment_position": 3,
            "reports_rate": 0.01,
            "toxicity_in_replies": 0.05,
            "content_removed": False,
            "platform_flagged": False,
        }
        clean_reward = calculate_test_reward(clean_metrics)

        # Update bandit (simulated) - use success/failure based on threshold
        if provocative_reward > 0.5:
            bandit.tone_arms[provocative_arm].update_success()
        else:
            bandit.tone_arms[provocative_arm].update_failure()

        if clean_reward > 0.5:
            bandit.tone_arms[clean_arm].update_success()
        else:
            bandit.tone_arms[clean_arm].update_failure()

    # Check final distributions
    print("Arm distributions after 50 rounds:")
    print()

    drift_detected = False
    for arm_name, arm in bandit.tone_arms.items():
        final_mean = arm.alpha / (arm.alpha + arm.beta)
        initial_mean = initial_stats.get(arm_name, {}).get("mean", 0.5)
        drift = final_mean - initial_mean

        status = ""
        if arm_name == provocative_arm:
            if drift > 0.1:
                status = " <- DRIFT DETECTED (should not increase!)"
                drift_detected = True
            else:
                status = " [OK] No upward drift"
        elif arm_name == clean_arm:
            if drift > 0:
                status = " [OK] Clean content preferred"

        print(f"  {arm_name}:")
        print(f"    Initial: {initial_mean:.3f}")
        print(f"    Final:   {final_mean:.3f}")
        print(f"    Drift:   {drift:+.3f}{status}")
        print()

    if drift_detected:
        print("[FAIL] Provocative arm drifted upward despite penalties")
        return False
    else:
        print("[PASS] No drift toward provocative content")
        return True


def main():
    """Run all reward poisoning tests."""
    # Test 1: Poisoning scenarios
    poison_results = run_poison_tests()

    # Test 2: Bandit drift
    drift_passed = test_bandit_no_drift()

    # Final summary
    print("\n" + "=" * 70)
    print("FINAL RESULTS")
    print("=" * 70)

    all_passed = poison_results["failed"] == 0 and drift_passed

    if all_passed:
        print("\n[OK] ALL TESTS PASSED")
        print("  - NegativeSignals correctly penalize gaming")
        print("  - Bandit does not drift toward provocative content")
        return 0
    else:
        print("\n[WARN] SOME TESTS FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
